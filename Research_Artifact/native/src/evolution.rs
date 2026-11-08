// Shared approval and target-authority contract for all strengthened endpoints.
// Resource locks protect one manager store; the unchanged Python native adapter
// runs in a lease-owning process and rechecks its claim before executing.
fn evolution_db(store:&Store)->Result<rusqlite::Connection> {
    let db=rusqlite::Connection::open(&store.paths().db)?;
    crate::db::schema::configure(&db)?;
    db.execute_batch("CREATE TABLE IF NOT EXISTS evolution_heads(target TEXT PRIMARY KEY,generation INTEGER NOT NULL,plan TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS evolution_claims(plan TEXT PRIMARY KEY,target TEXT NOT NULL,generation INTEGER NOT NULL)")?;
    Ok(db)
}
fn evolution_target(tool:ToolKind,scope:Scope,project:Option<&PathBuf>,opts:&AdapterOptions)->Result<String> {
    let p=match tool {
        ToolKind::Claude if scope==Scope::Project=>project.ok_or_else(||Error::invalid("project required"))?.canonicalize()?,
        ToolKind::Codex|ToolKind::Grok=>opts.home.as_ref().ok_or_else(||Error::invalid("home required"))?.canonicalize()?,
        _=>return Err(Error::invalid("unverified resource footprint")),
    };
    let text=p.to_string_lossy().into_owned();
    let text=if cfg!(windows){text.to_lowercase()}else{text};
    Ok(sha256_hex(format!("{}:{text}",tool.as_str())))
}
fn evolution_lock(store:&Store,name:&str)->Result<HomeLock> {
    let mut paths=store.paths().clone();
    let dir=paths.home.join("evolution-locks");std::fs::create_dir_all(&dir)?;
    paths.lock=dir.join(format!("{}.lock",sha256_hex(name)));
    HomeLock::acquire(&paths)
}
fn evolution_lease_path(store:&Store,target:&str)->PathBuf {
    store.paths().home.join("evolution-locks").join(format!("{}.lock",sha256_hex(format!("native:{target}"))))
}
fn evolution_locks(store:&Store,target:&str,prompt:&str)->Result<Vec<HomeLock>> {
    let mut locks=Vec::new();
    if std::env::var("RECEIPTCOORDINATOR_RESEARCH_VARIANT").ok().as_deref()==Some("JournalGuarded") {
        locks.push(HomeLock::acquire(store.paths())?);
    }
    let mut names=vec![format!("target:{target}"),format!("prompt:{prompt}")];names.sort();
    for name in names {locks.push(evolution_lock(store,&name)?);}
    Ok(locks)
}
fn evolution_state(tool:ToolKind,scope:Scope,project:Option<&PathBuf>,opts:&AdapterOptions)->Result<serde_json::Value> {
    let (body,config)=research_targets(tool,scope,project,opts)?;
    Ok(json!({"instruction":research_digest(&body)?,"configuration":research_digest(&config)?}))
}
fn evolution_head(db:&rusqlite::Connection,target:&str)->Result<(i64,String)> {
    use rusqlite::OptionalExtension;
    Ok(db.query_row("SELECT generation,plan FROM evolution_heads WHERE target=?1",[target],|r|Ok((r.get(0)?,r.get(1)?))).optional()?.unwrap_or((0,String::new())))
}
fn evolution_binding(store:&Store,tool:ToolKind,scope:Scope,project:Option<&PathBuf>,opts:&AdapterOptions)->Result<serde_json::Value> {
    let target=evolution_target(tool,scope,project,opts)?;
    let _lease=evolution_lock(store,&format!("native:{target}"))?;
    let db=evolution_db(store)?;let (generation,owner)=evolution_head(&db,&target)?;
    Ok(json!({"target":target,"generation":generation,"owner":owner,"before":evolution_state(tool,scope,project,opts)?}))
}
fn evolution_options(store:&Store,target:&str,opts:&AdapterOptions,claim:Option<(i64,&str)>)->Result<AdapterOptions> {
    let mut next=opts.clone();
    let original=opts.cli_override.as_ref().ok_or_else(||Error::invalid("pinned adapter path required"))?;
    next.cli_override=Some(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("native_gate.py"));
    next.extra_env.insert("EVOLUTION_ORIGINAL_CLI".into(),original.to_string_lossy().into_owned());
    next.extra_env.insert("EVOLUTION_NATIVE_LEASE".into(),evolution_lease_path(store,target).to_string_lossy().into_owned());
    if let Some((generation,plan))=claim {
        next.extra_env.insert("EVOLUTION_DB".into(),store.paths().db.to_string_lossy().into_owned());
        next.extra_env.insert("EVOLUTION_TARGET".into(),target.into());
        next.extra_env.insert("EVOLUTION_GENERATION".into(),generation.to_string());
        next.extra_env.insert("EVOLUTION_EXPECTED_PLAN".into(),plan.into());
    }
    Ok(next)
}
fn evolution_claim(store:&Store,plan:&Operation,opts:&AdapterOptions)->Result<(String,i64)> {
    use rusqlite::{params,OptionalExtension};
    let request:serde_json::Value=serde_json::from_str(&plan.request_json)?;
    let bound=request.get("approvalBinding").ok_or_else(||Error::user_cancel("preview has no target binding"))?;
    let scope=plan.scope.unwrap_or(Scope::User);let project=plan.project_dir.as_ref().map(PathBuf::from);
    let target=evolution_target(plan.tool,scope,project.as_ref(),opts)?;
    if bound["target"].as_str()!=Some(&target) {return Err(Error::drift("approval target changed"));}
    let _lease=evolution_lock(store,&format!("native:{target}"))?;
    let mut db=evolution_db(store)?;
    let tx=db.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let head=evolution_head(&tx,&target)?;
    let prior:Option<i64>=tx.query_row("SELECT generation FROM evolution_claims WHERE plan=?1",[&plan.id],|r|r.get(0)).optional()?;
    let generation=if let Some(g)=prior {
        if head!=(g,plan.id.clone()) {return Err(Error::drift("operation superseded by a later claim"));}
        // Claim can survive a crash before the endpoint intent exists.
        let operation_intent:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM operations WHERE kind='activate' AND parent_id=?1)",[&plan.id],|r|r.get(0))?;
        let journal_table:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='native_journal')",[],|r|r.get(0))?;
        let journal_intent=journal_table && tx.query_row("SELECT EXISTS(SELECT 1 FROM native_journal WHERE plan=?1)",[&plan.id],|r|r.get::<_,bool>(0))?;
        let intent=operation_intent || journal_intent;
        if !intent && bound["before"]!=evolution_state(plan.tool,scope,project.as_ref(),opts)? {
            return Err(Error::drift("target changed before first execution intent"));
        }
        g
    } else {
        if bound["generation"].as_i64()!=Some(head.0) || bound["owner"].as_str()!=Some(&head.1) {
            return Err(Error::drift("approval superseded before execution"));
        }
        if bound["before"]!=evolution_state(plan.tool,scope,project.as_ref(),opts)? {
            return Err(Error::drift("target changed since approved preview"));
        }
        let g=head.0+1;
        tx.execute("INSERT INTO evolution_heads VALUES(?1,?2,?3) ON CONFLICT(target) DO UPDATE SET generation=excluded.generation,plan=excluded.plan",params![target,g,plan.id])?;
        tx.execute("INSERT INTO evolution_claims VALUES(?1,?2,?3)",params![plan.id,target,g])?;
        g
    };
    tx.commit()?;crate::research_fault::checkpoint("after_claim");Ok((target,generation))
}
fn evolution_commit_guard(db:&rusqlite::Connection,plan:&Operation)->Result<()> {
    let request:serde_json::Value=serde_json::from_str(&plan.request_json)?;
    if request.get("approvalBinding").is_none(){return Ok(());}
    let allowed:bool=db.query_row("SELECT EXISTS(SELECT 1 FROM evolution_claims c JOIN evolution_heads h ON c.target=h.target AND c.generation=h.generation AND c.plan=h.plan WHERE c.plan=?1)",[&plan.id],|r|r.get(0))?;
    if !allowed{return Err(Error::drift("superseded management commit"));}Ok(())
}
pub fn evolution_update_prompt(store:&Store,input:UpdatePromptInput)->Result<PromptDetail> {
    let _global=HomeLock::acquire(store.paths())?;
    let _source=evolution_lock(store,&format!("prompt:{}",input.id))?;
    refuse_hidden(store,&input.id)?;
    store.update_prompt(&input.id,input.title.as_deref(),input.content.as_deref(),input.tags.as_deref())
}
