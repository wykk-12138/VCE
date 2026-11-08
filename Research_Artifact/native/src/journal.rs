// Independent conventional intent-log composition. No proposed execution or
// commit helper is called. Shared interfaces: original preparation, disk/status,
// Store/schema, locks, original native invocation and low-level fingerprint.
fn journal_plan(store:&Store,id:&str)->Result<Operation> {
    let value=store.get_operation(id)?.ok_or_else(||Error::user_cancel("preview not present"))?;
    if !value.preview || value.kind!=OperationKind::PlanActivate ||
       !matches!(value.status,OperationStatus::Preview|OperationStatus::Ready|OperationStatus::Succeeded) {
        return Err(Error::user_cancel("invalid journal preview"));
    } Ok(value)
}
async fn journal_execute(store:&Store,plan:&Operation,prompt:&PromptDetail,scope:Scope,project:Option<&PathBuf>,
    command:AdapterCommand,request:serde_json::Value,opts:&AdapterOptions)->Result<OperationResult> {
    use rusqlite::{params,OptionalExtension};
    let mut db=rusqlite::Connection::open(&store.paths().db)?;crate::db::schema::configure(&db)?;
    db.execute_batch("CREATE TABLE IF NOT EXISTS native_journal(plan TEXT PRIMARY KEY,execution TEXT NOT NULL,before_value TEXT NOT NULL,done INTEGER NOT NULL)")?;
    let (body,config)=research_targets(plan.tool,scope,project,opts)?;
    let entry:Option<(String,String,bool)>=db.query_row("SELECT execution,before_value,done FROM native_journal WHERE plan=?1",[&plan.id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
    let (id,before,done)=if let Some(row)=entry {row} else {
        let id=uuid::Uuid::new_v4().to_string();
        let before=json!([research_digest(&body)?,research_digest(&config)?]).to_string();
        db.execute("INSERT INTO native_journal VALUES(?1,?2,?3,0)",params![plan.id,id,before])?;(id,before,false)
    };
    let matches=receipt_disk(plan,prompt,scope,project,opts)?;
    let status=if let Some(cached)=witness_cached(opts){Some(cached)}else if matches {Some(run_adapter_with(plan.tool,AdapterCommand::Status {scope,project_dir:project.cloned(),name:Some(plan.tool.default_name().into())},opts).await?)} else {None};
    let aligned=status.as_ref().is_some_and(|e|e.ok && e.status==ToolStatus::Active && !e.recovery_required && e.blockers.is_empty());
    let mut response=if aligned {crate::research_fault::checkpoint("after_native");status.unwrap()} else {
        let current=json!([research_digest(&body)?,research_digest(&config)?]).to_string();
        if done || before!=current {return Err(Error::drift("journal precondition changed"));}
        crate::research_fault::checkpoint("before_native");
        let response=run_adapter_with(plan.tool,command,opts).await?;
        if !response.ok {return Ok(OperationResult {operation_id:id,envelope:response});}
        crate::research_fault::checkpoint("after_native");
        if receipt_variant("JournalPostStatus") {
            run_adapter_with(plan.tool,AdapterCommand::Status {scope,project_dir:project.cloned(),name:Some(plan.tool.default_name().into())},opts).await?
        } else {response}
    };
    if !receipt_witness(&response) || !receipt_disk(plan,prompt,scope,project,opts)? {
        return Err(Error::drift("journal outcome not established"));
    }
    response.command="activate".into();response.preview=false;response.status=ToolStatus::Active;response.target_fingerprint=Some(prompt.sha256.clone());
    let now=now_rfc3339();let project=project.map(|p|p.to_string_lossy().into_owned()).unwrap_or_default();
    let activation=sha256_hex(format!("{}:{}:{}",plan.tool.as_str(),scope.as_str(),project));
    let _publication_span=crate::research_fault::Span::new("publication");
    let transaction=db.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    evolution_commit_guard(&transaction,plan)?;
    transaction.execute("INSERT INTO operations(id,tool,kind,status,preview,prompt_id,scope,project_dir,request_json,envelope_json,error,parent_id,created_at,updated_at)
      VALUES(?1,?2,'activate','succeeded',0,?3,?4,?5,?6,?7,NULL,?8,?9,?9)
      ON CONFLICT(id) DO UPDATE SET status='succeeded',envelope_json=excluded.envelope_json,error=NULL,updated_at=excluded.updated_at",
      params![id,plan.tool.as_str(),prompt.id,scope.as_str(),project,request.to_string(),crate::redact::redact_text(&serde_json::to_string(&response)?),plan.id,now])?;
    crate::research_fault::checkpoint("after_execute_record");
    transaction.execute("INSERT INTO activations(id,prompt_id,tool,scope,project_dir,status,fingerprint,operation_id,created_at,updated_at)
      VALUES(?1,?2,?3,?4,?5,'active',?6,?7,?8,?8) ON CONFLICT(id) DO UPDATE SET prompt_id=excluded.prompt_id,status=excluded.status,
      fingerprint=excluded.fingerprint,operation_id=excluded.operation_id,updated_at=excluded.updated_at",params![activation,prompt.id,plan.tool.as_str(),scope.as_str(),project,prompt.sha256,id,now])?;
    transaction.execute("INSERT INTO tool_state(tool,scope,project_dir,status,fingerprint,last_operation_id,last_checked_at)
      VALUES(?1,?2,?3,'active',?4,?5,?6) ON CONFLICT(tool,scope,project_dir) DO UPDATE SET status=excluded.status,
      fingerprint=excluded.fingerprint,last_operation_id=excluded.last_operation_id,last_checked_at=excluded.last_checked_at",params![plan.tool.as_str(),scope.as_str(),project,prompt.sha256,id,now])?;
    crate::research_fault::checkpoint("after_activation_record");
    transaction.execute("UPDATE operations SET status='succeeded',error=NULL,updated_at=?1 WHERE id=?2",params![now,plan.id])?;
    transaction.execute("UPDATE native_journal SET done=1 WHERE plan=?1",[&plan.id])?;
    transaction.commit()?;crate::research_fault::checkpoint("after_plan_commit");
    Ok(OperationResult {operation_id:id,envelope:response})
}
