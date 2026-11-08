// Included inside the production ops module. Validation/preparation is generated
// from the original confirm_activate body; these helpers supply the added layer.

fn research_plan(store: &Store, operation_id: &str) -> Result<Operation> {
    let plan=store.get_operation(operation_id)?.ok_or_else(||Error::user_cancel("plan not found"))?;
    if plan.kind!=OperationKind::PlanActivate || !plan.preview {
        return Err(Error::user_cancel("not an activation preview"));
    }
    let exists=store.get_operation(&format!("verified:{operation_id}"))?.is_some();
    if !matches!(plan.status,OperationStatus::Preview|OperationStatus::Ready) &&
        !(exists && plan.status==OperationStatus::Succeeded) {
        return Err(Error::user_cancel("plan already used"));
    }
    Ok(plan)
}

fn research_targets(tool: ToolKind, scope: Scope, project: Option<&PathBuf>, opts: &AdapterOptions) -> Result<(PathBuf,PathBuf)> {
    let home=opts.home.as_ref().ok_or_else(||Error::invalid("explicit isolated home required"))?;
    match tool {
        ToolKind::Claude if scope==Scope::Project => {
            let root=project.ok_or_else(||Error::invalid("explicit project required"))?;
            Ok((root.join(".claude/receiptcoordinator").join(format!("{}.md",tool.default_name())),root.join("CLAUDE.md")))
        },
        ToolKind::Codex => Ok((home.join(".codex").join(format!("{}.md",tool.default_name())),home.join(".codex/config.toml"))),
        ToolKind::Grok => Ok((home.join(".grok/rules/99-receiptcoordinator.md"),home.join(".grok/config.toml"))),
        _ => Err(Error::invalid("unsupported verified native scope")),
    }
}

fn research_digest(path: &std::path::Path) -> Result<Option<String>> {
    match std::fs::symlink_metadata(path) {
        Ok(meta) if meta.is_file() && !meta.file_type().is_symlink() => Ok(Some(sha256_hex(std::fs::read(path)?))),
        Ok(_) => Err(Error::drift("native path is not a regular file")),
        Err(error) if error.kind()==std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error.into()),
    }
}

async fn research_observe(plan: &Operation, prompt: &PromptDetail, scope: Scope, project: Option<&PathBuf>,opts: &AdapterOptions) -> Result<(bool,Envelope)> {
    let (instruction,configuration)=research_targets(plan.tool,scope,project,opts)?;
    let status=run_adapter_with(plan.tool,AdapterCommand::Status {scope,project_dir:project.cloned(),name:Some(plan.tool.default_name().into())},opts).await?;
    let content=std::fs::read_to_string(&instruction).ok();
    let matches=content.as_ref().is_some_and(|raw|raw.replace("\r\n","\n")==prompt.content.replace("\r\n","\n"));
    let reference=match plan.tool {
        ToolKind::Claude => std::fs::read_to_string(&configuration).ok().is_some_and(|raw|
            raw.lines().any(|line|line.trim()==format!("@.claude/receiptcoordinator/{}.md",plan.tool.default_name()))),
        ToolKind::Codex => std::fs::read_to_string(&configuration).ok().and_then(|raw|raw.parse::<toml_edit::DocumentMut>().ok())
            .and_then(|doc|doc.get("model_instructions_file").and_then(|item|item.as_str()).map(str::to_string))
            .is_some_and(|reference| {
                let path=PathBuf::from(reference);
                let resolved=if path.is_absolute(){path}else{configuration.parent().unwrap().join(path)};
                resolved.canonicalize().ok()==instruction.canonicalize().ok() && instruction.is_file()
            }),
        ToolKind::Grok=>true,
        _=>false,
    };
    Ok((matches && reference && status.ok && status.status==ToolStatus::Active && !status.recovery_required,status))
}

async fn research_execute_verified(store:&Store,plan:&Operation,prompt:&PromptDetail,scope:Scope,
    project:Option<&PathBuf>,command:AdapterCommand,request:serde_json::Value,opts:&AdapterOptions)->Result<OperationResult> {
    let execute_id=format!("verified:{}",plan.id);
    let (instruction,configuration)=research_targets(plan.tool,scope,project,opts)?;
    let existing=store.get_operation(&execute_id)?;
    let mut request=request;
    if existing.is_none() {
        request["nativeBefore"]=json!({"instruction":research_digest(&instruction)?,"configuration":research_digest(&configuration)?});
        let now=now_rfc3339();
        store.insert_operation(&Operation {id:execute_id.clone(),tool:plan.tool,kind:OperationKind::Activate,
            status:OperationStatus::Ready,preview:false,prompt_id:plan.prompt_id.clone(),scope:Some(scope),
            project_dir:plan.project_dir.clone(),request_json:request.to_string(),envelope_json:None,error:None,
            parent_id:Some(plan.id.clone()),created_at:now.clone(),updated_at:now})?;
    } else {
        request=serde_json::from_str(&existing.as_ref().unwrap().request_json)?;
    }
    let (aligned,mut observed)=research_observe(plan,prompt,scope,project,opts).await?;
    if !aligned {
        if existing.as_ref().is_some_and(|row|row.status==OperationStatus::Succeeded) {
            return Err(Error::drift("completed native deployment changed externally"));
        }
        let now=json!({"instruction":research_digest(&instruction)?,"configuration":research_digest(&configuration)?});
        if request.get("nativeBefore")!=Some(&now) {
            return Err(Error::drift("native state changed after confirmed intent"));
        }
        crate::research_fault::checkpoint("before_native");
        let executed=run_adapter_with(plan.tool,command,opts).await?;
        if !executed.ok {return Ok(OperationResult {operation_id:execute_id,envelope:executed});}
        crate::research_fault::checkpoint("after_native");
        let (valid,status)=research_observe(plan,prompt,scope,project,opts).await?;
        if !valid {return Err(Error::drift("native postcondition did not verify"));}
        observed=status;
    } else {
        crate::research_fault::checkpoint("after_native");
    }
    observed.command="activate".into();observed.preview=false;
    observed.target_fingerprint=Some(prompt.sha256.clone());
    research_commit_verified(store,plan,prompt,scope,project,&execute_id,&observed)?;
    Ok(OperationResult {operation_id:execute_id,envelope:observed})
}

fn research_commit_verified(store:&Store,plan:&Operation,prompt:&PromptDetail,scope:Scope,
    project:Option<&PathBuf>,execute_id:&str,envelope:&Envelope)->Result<()> {
    use rusqlite::params;
    // Same underlying database and process-exit durability setting as upstream.
    let mut connection=rusqlite::Connection::open(&store.paths().db)?;
    crate::db::schema::configure(&connection)?;
    let transaction=connection.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let now=now_rfc3339();let project=project.map(|p|p.to_string_lossy().into_owned()).unwrap_or_default();
    let activation=sha256_hex(format!("{}:{}:{}",plan.tool.as_str(),scope.as_str(),project));
    let serialized=crate::redact::redact_text(&serde_json::to_string(envelope)?);
    transaction.execute("UPDATE operations SET status='succeeded',envelope_json=?1,error=NULL,updated_at=?2 WHERE id=?3",params![serialized,now,execute_id])?;
    crate::research_fault::checkpoint("after_execute_record");
    transaction.execute("INSERT INTO activations(id,prompt_id,tool,scope,project_dir,status,fingerprint,operation_id,created_at,updated_at)
        VALUES(?1,?2,?3,?4,?5,'active',?6,?7,?8,?8) ON CONFLICT(id) DO UPDATE SET
        prompt_id=excluded.prompt_id,status=excluded.status,fingerprint=excluded.fingerprint,operation_id=excluded.operation_id,updated_at=excluded.updated_at",
        params![activation,prompt.id,plan.tool.as_str(),scope.as_str(),project,prompt.sha256,execute_id,now])?;
    transaction.execute("INSERT INTO tool_state(tool,scope,project_dir,status,fingerprint,last_operation_id,last_checked_at)
        VALUES(?1,?2,?3,'active',?4,?5,?6) ON CONFLICT(tool,scope,project_dir) DO UPDATE SET
        status=excluded.status,fingerprint=excluded.fingerprint,last_operation_id=excluded.last_operation_id,last_checked_at=excluded.last_checked_at",
        params![plan.tool.as_str(),scope.as_str(),project,prompt.sha256,execute_id,now])?;
    crate::research_fault::checkpoint("after_activation_record");
    transaction.execute("UPDATE operations SET status='succeeded',error=NULL,updated_at=?1 WHERE id=?2",params![now,plan.id])?;
    transaction.commit()?;
    crate::research_fault::checkpoint("after_plan_commit");
    Ok(())
}
