// Receipt-aware coordination. Existing v7 engine remains compiled unchanged.
fn receipt_variant(name:&str)->bool {std::env::var("RECEIPTCOORDINATOR_RESEARCH_VARIANT").ok().as_deref()==Some(name)}
fn receipt_plan(store:&Store,id:&str)->Result<Operation> {
    let plan=store.get_operation(id)?.ok_or_else(||Error::user_cancel("missing approved preview"))?;
    if plan.kind!=OperationKind::PlanActivate || !plan.preview {return Err(Error::user_cancel("not an activation preview"));}
    if !matches!(plan.status,OperationStatus::Preview|OperationStatus::Ready|OperationStatus::Succeeded) {return Err(Error::user_cancel("preview unusable"));}
    if plan.status==OperationStatus::Succeeded && store.get_operation(&format!("receipt:{id}"))?.is_none() {return Err(Error::user_cancel("completed preview lacks this coordinator intent"));}
    Ok(plan)
}
fn receipt_active(envelope:&Envelope)->bool {
    envelope.ok && envelope.status==ToolStatus::Active && !envelope.recovery_required && envelope.blockers.is_empty()
}
fn receipt_witness(envelope:&Envelope)->bool {
    // Upstream activation normalization leaves status at its default inactive;
    // activation success and Status Active are distinct native response types.
    envelope.ok && !envelope.recovery_required && envelope.blockers.is_empty() &&
    if envelope.command=="activate" {envelope.exit_code==0 && !envelope.preview}
    else {envelope.command=="status" && envelope.status==ToolStatus::Active}
}
async fn receipt_execute(store:&Store,plan:&Operation,prompt:&PromptDetail,scope:Scope,
    project:Option<&PathBuf>,command:AdapterCommand,mut request:serde_json::Value,opts:&AdapterOptions)->Result<OperationResult> {
    let stable=format!("receipt:{}",plan.id);
    let prior=store.get_operation(&stable)?;
    let (body,config)=research_targets(plan.tool,scope,project,opts)?;
    if let Some(row)=prior.as_ref() {request=serde_json::from_str(&row.request_json)?;}
    else {
        request["nativeBefore"]=json!({"instruction":research_digest(&body)?,"configuration":research_digest(&config)?});
        let now=now_rfc3339();
        store.insert_operation(&Operation {id:stable.clone(),tool:plan.tool,kind:OperationKind::Activate,status:OperationStatus::Ready,
            preview:false,prompt_id:Some(prompt.id.clone()),scope:Some(scope),project_dir:plan.project_dir.clone(),
            request_json:request.to_string(),envelope_json:None,error:None,parent_id:Some(plan.id.clone()),created_at:now.clone(),updated_at:now})?;
    }
    let disk=receipt_disk(plan,prompt,scope,project,opts)?;
    let mut recovered=witness_cached(opts);
    // A fresh matching disk may predate this operation, so still check native status.
    if disk && recovered.is_none() {
        let status=run_adapter_with(plan.tool,AdapterCommand::Status {scope,project_dir:project.cloned(),name:Some(plan.tool.default_name().into())},opts).await?;
        if receipt_active(&status) {recovered=Some(status);}
    }
    let mut envelope=if recovered.is_some() && !receipt_variant("A_Replay") {
        crate::research_fault::checkpoint("after_native");recovered.unwrap()
    } else {
        if recovered.is_none() {
            if prior.as_ref().is_some_and(|r|r.status==OperationStatus::Succeeded) {return Err(Error::drift("completed receipt no longer matches"));}
            let current=json!({"instruction":research_digest(&body)?,"configuration":research_digest(&config)?});
            if request.get("nativeBefore")!=Some(&current) {return Err(Error::drift("native state changed since intent"));}
        }
        crate::research_fault::checkpoint("before_native");
        let native=run_adapter_with(plan.tool,command,opts).await?;
        if !native.ok {return Ok(OperationResult {operation_id:stable,envelope:native});}
        crate::research_fault::checkpoint("after_native");
        native
    };
    if !receipt_variant("A_NoOutcome") && (!receipt_witness(&envelope) || !receipt_disk(plan,prompt,scope,project,opts)?) {
        return Err(Error::drift("receipt and independent file/reference read disagree"));
    }
    envelope.command="activate".into();envelope.preview=false;envelope.status=ToolStatus::Active;envelope.target_fingerprint=Some(prompt.sha256.clone());
    let execute_id=if receipt_variant("A_Unkeyed") {
        let mut row=store.get_operation(&stable)?.unwrap();
        row.id=format!("{}:{}",stable,uuid::Uuid::new_v4());store.insert_operation(&row)?;row.id
    } else {stable};
    receipt_commit(store,plan,prompt,scope,project,&execute_id,&envelope)?;
    Ok(OperationResult {operation_id:execute_id,envelope})
}

fn receipt_commit(store:&Store,plan:&Operation,prompt:&PromptDetail,scope:Scope,project:Option<&PathBuf>,id:&str,envelope:&Envelope)->Result<()> {
    let _span=crate::research_fault::Span::new("publication");
    use rusqlite::params;
    let db=rusqlite::Connection::open(&store.paths().db)?;crate::db::schema::configure(&db)?;
    let atomic=!receipt_variant("A_NoAtomic");
    if atomic {db.execute_batch("BEGIN IMMEDIATE")?;}
    evolution_commit_guard(&db,plan)?;
    let now=now_rfc3339();let project=project.map(|p|p.to_string_lossy().into_owned()).unwrap_or_default();
    let activation=sha256_hex(format!("{}:{}:{}",plan.tool.as_str(),scope.as_str(),project));
    let serialized=crate::redact::redact_text(&serde_json::to_string(envelope)?);
    db.execute("UPDATE operations SET status='succeeded',envelope_json=?1,error=NULL,updated_at=?2 WHERE id=?3",params![serialized,now,id])?;
    crate::research_fault::checkpoint("after_execute_record");
    db.execute("INSERT INTO activations(id,prompt_id,tool,scope,project_dir,status,fingerprint,operation_id,created_at,updated_at)
      VALUES(?1,?2,?3,?4,?5,'active',?6,?7,?8,?8) ON CONFLICT(id) DO UPDATE SET prompt_id=excluded.prompt_id,status=excluded.status,
      fingerprint=excluded.fingerprint,operation_id=excluded.operation_id,updated_at=excluded.updated_at",params![activation,prompt.id,plan.tool.as_str(),scope.as_str(),project,prompt.sha256,id,now])?;
    db.execute("INSERT INTO tool_state(tool,scope,project_dir,status,fingerprint,last_operation_id,last_checked_at)
      VALUES(?1,?2,?3,'active',?4,?5,?6) ON CONFLICT(tool,scope,project_dir) DO UPDATE SET status=excluded.status,
      fingerprint=excluded.fingerprint,last_operation_id=excluded.last_operation_id,last_checked_at=excluded.last_checked_at",params![plan.tool.as_str(),scope.as_str(),project,prompt.sha256,id,now])?;
    crate::research_fault::checkpoint("after_activation_record");
    db.execute("UPDATE operations SET status='succeeded',error=NULL,updated_at=?1 WHERE id=?2",params![now,plan.id])?;
    if atomic {db.execute_batch("COMMIT")?;}
    crate::research_fault::checkpoint("after_plan_commit");Ok(())
}
