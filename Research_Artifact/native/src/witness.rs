// Completion evidence is shared by RC and the conventional journal endpoint.
fn witness_enabled()->bool {
    matches!(std::env::var("RECEIPTCOORDINATOR_RESEARCH_VARIANT").ok().as_deref(),Some("ReceiptCoordinatorV14"|"JournalWitnessScoped"|"A_NoEvidenceSeal"|"ReceiptCoordinatorV15"|"JournalWitnessV15"|"A_NoResidueWatch"))
}
fn witness_attempt(store:&Store,plan:&Operation,opts:&mut AdapterOptions)->Result<()> {
    let target=opts.extra_env.get("EVOLUTION_TARGET").ok_or_else(||Error::invalid("missing target"))?.clone();
    let _lease=evolution_lock(store,&format!("native:{target}"))?;
    let db=evolution_db(store)?;let token=uuid::Uuid::new_v4().to_string();
    db.execute_batch("CREATE TABLE IF NOT EXISTS native_attempts(target TEXT PRIMARY KEY,plan TEXT NOT NULL,token TEXT NOT NULL)")?;
    db.execute("INSERT INTO native_attempts VALUES(?1,?2,?3) ON CONFLICT(target) DO UPDATE SET plan=excluded.plan,token=excluded.token",rusqlite::params![target,plan.id,token])?;
    opts.extra_env.insert("WITNESS_ATTEMPT".into(),token);Ok(())
}
#[cfg(windows)]
fn witness_file_identity(path:&std::path::Path)->Result<String> {
    use std::os::windows::{fs::OpenOptionsExt,io::AsRawHandle};
    #[repr(C)] struct FileId {volume:u64,id:[u8;16]}
    #[link(name="kernel32")] extern "system" {fn GetFileInformationByHandleEx(handle:*mut core::ffi::c_void,class:i32,info:*mut core::ffi::c_void,size:u32)->i32;}
    let file=std::fs::OpenOptions::new().read(true).custom_flags(0x02000000).open(path)?;
    let mut data=FileId{volume:0,id:[0;16]};
    let ok=unsafe{GetFileInformationByHandleEx(file.as_raw_handle(),18,&mut data as *mut FileId as *mut core::ffi::c_void,std::mem::size_of::<FileId>() as u32)};
    if ok==0{return Err(std::io::Error::last_os_error().into());}
    Ok(format!("{}:{}",data.volume,hex::encode(data.id)))
}
#[cfg(unix)]
fn witness_file_identity(path:&std::path::Path)->Result<String>{use std::os::unix::fs::MetadataExt;let m=std::fs::metadata(path)?;Ok(format!("{}:{}",m.dev(),m.ino()))}
fn witness_roots(plan:&Operation,opts:&AdapterOptions)->Result<Vec<PathBuf>> {
    let home=opts.home.as_ref().ok_or_else(||Error::invalid("missing home"))?;
    let state=match plan.tool {
        ToolKind::Claude=>PathBuf::from(plan.project_dir.as_ref().ok_or_else(||Error::invalid("missing project"))?),
        ToolKind::Codex=>home.join(".codex"),ToolKind::Grok=>home.join(".grok"),_=>return Err(Error::invalid("unverified witness scope")),
    };
    let script=opts.extra_env.get("EVOLUTION_ORIGINAL_CLI").map(PathBuf::from).ok_or_else(||Error::invalid("missing CLI"))?;
    Ok(vec![state,script,PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("native_gate.py"),
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("base_native_gate.py"),crate::adapter::process::resolve_python()?])
}
fn witness_policy(plan:&Operation)->&'static str {
    let method=std::env::var("RECEIPTCOORDINATOR_RESEARCH_VARIANT").unwrap_or_default();
    if plan.tool==ToolKind::Claude {
        if method=="A_NoResidueWatch" {return "claude-project-v1-no-residue";}
        if method=="ReceiptCoordinatorV15" || method=="JournalWitnessV15" {return "claude-project-v1";}
    } "tree-v1"
}
fn witness_child_selected(key:&str,name:&str,policy:&str)->bool {
    if !policy.starts_with("claude-project-v1"){return true;}
    let fixed=if cfg!(windows){name.to_ascii_lowercase()}else{name.to_string()};
    let directory=if cfg!(windows){key.to_ascii_lowercase()}else{key.to_string()};
    let memory=if cfg!(windows){"claude.md"}else{"CLAUDE.md"};
    if key=="0" {return fixed==memory || fixed==".claude" || (policy=="claude-project-v1" && name.starts_with('.') && name.contains(".receiptcoordinator-tmp-") && name.ends_with(".tmp"));}
    if directory=="0/.claude" {return fixed=="receiptcoordinator";}
    true
}
fn witness_prepare(plan:&Operation,prompt:&PromptDetail,opts:&mut AdapterOptions)->Result<()> {
    if !witness_enabled(){return Ok(());}
    opts.extra_env.insert("WITNESS_SEAL_POLICY".into(),witness_policy(plan).into());
    opts.extra_env.insert("WITNESS_ENABLED".into(),"1".into());
    opts.extra_env.insert("WITNESS_TOOL".into(),plan.tool.as_str().into());
    opts.extra_env.insert("WITNESS_SOURCE_SHA".into(),prompt.sha256.clone());
    opts.extra_env.insert("WITNESS_ROOTS".into(),serde_json::to_string(&witness_roots(plan,opts)?)?);
    Ok(())
}
fn witness_scan(path:&std::path::Path,key:&str,result:&mut serde_json::Map<String,serde_json::Value>,work:&mut(u64,u64),policy:&str)->Result<()> {
    let meta=match std::fs::symlink_metadata(path){Ok(m)=>m,Err(e) if e.kind()==std::io::ErrorKind::NotFound=>{result.insert(key.into(),json!({"kind":"missing"}));return Ok(());},Err(e)=>return Err(e.into())};
    #[cfg(windows)] {use std::os::windows::fs::MetadataExt;if meta.file_attributes()&0x400!=0{return Err(Error::drift("reparse node in evidence scope"));}}
    if meta.file_type().is_symlink(){return Err(Error::drift("symbolic link in evidence scope"));}
    work.0+=1;if work.0>4096{return Err(Error::drift("evidence node budget"));}
    if meta.is_dir(){
        result.insert(key.into(),json!({"kind":"directory","identity":witness_file_identity(path)?}));
        let mut children:Vec<_>=std::fs::read_dir(path)?.collect::<std::io::Result<Vec<_>>>()?;children.sort_by_key(|e|e.file_name());
        for entry in children {if witness_child_selected(key,&entry.file_name().to_string_lossy(),policy){witness_scan(&entry.path(),&format!("{key}/{}",entry.file_name().to_string_lossy()),result,work,policy)?;}}
    } else if meta.is_file(){
        work.1+=meta.len();if work.1>64*1024*1024{return Err(Error::drift("evidence byte budget"));}
        let raw=std::fs::read(path)?;let after=std::fs::metadata(path)?;
        if meta.len()!=after.len() || meta.modified()?!=after.modified()? {return Err(Error::drift("unstable evidence scope"));}
        let nanos=meta.modified()?.duration_since(std::time::UNIX_EPOCH).map_err(|_|Error::invalid("pre-epoch timestamp"))?.as_nanos().to_string();
        result.insert(key.into(),json!({"kind":"file","identity":witness_file_identity(path)?,"sha256":sha256_hex(raw),"bytes":meta.len(),"mtime_ns":nanos,"readonly":meta.permissions().readonly()}));
    } else {return Err(Error::drift("unverified evidence node"));}Ok(())
}
fn witness_snapshot(roots:&[PathBuf],policy:&str)->Result<serde_json::Value> {
    let mut values=serde_json::Map::new();let mut work=(0,0);
    for (i,path) in roots.iter().enumerate(){witness_scan(path,&i.to_string(),&mut values,&mut work,policy)?;}
    Ok(serde_json::Value::Object(values))
}
fn witness_event(hit:bool,reason:&str) {
    use std::io::Write;
    if let Ok(path)=std::env::var("WITNESS_TRACE") {if let Ok(mut f)=std::fs::OpenOptions::new().create(true).append(true).open(path){let _=writeln!(f,"{}",json!({"hit":hit,"reason":reason}));}}
}
fn witness_probe(store:&Store,plan:&Operation,prompt:&PromptDetail,opts:&AdapterOptions)->Option<Envelope> {
    let _span=crate::research_fault::Span::new("evidence_validation");
    if !witness_enabled(){return None;}
    match witness_probe_checked(store,plan,prompt,opts){Ok(Some(e))=>{witness_event(true,"validated");Some(e)},Ok(None)=>{witness_event(false,"absent_or_invalid");None},Err(e)=>{witness_event(false,&e.to_string());None}}
}
fn witness_probe_checked(store:&Store,plan:&Operation,prompt:&PromptDetail,opts:&AdapterOptions)->Result<Option<Envelope>> {
    use rusqlite::OptionalExtension;
    let target=opts.extra_env.get("EVOLUTION_TARGET").ok_or_else(||Error::invalid("missing witness target"))?;
    let _lease=evolution_lock(store,&format!("native:{target}"))?;
    let db=evolution_db(store)?;
    let exists:bool=db.query_row("SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='native_completion_evidence')",[],|r|r.get(0))?;
    if !exists{return Ok(None);}
    let raw:Option<String>=db.query_row("SELECT evidence FROM native_completion_evidence WHERE plan=?1",[&plan.id],|r|r.get(0)).optional()?;
    let Some(raw)=raw else{return Ok(None);};if raw.len()>4*1024*1024{return Ok(None);}
    let record:serde_json::Value=serde_json::from_str(&raw)?;
    let payload=record["payload"].as_str().ok_or_else(||Error::drift("missing evidence payload"))?;
    if record["sha256"].as_str()!=Some(&sha256_hex(payload)){return Ok(None);}
    let ev:serde_json::Value=serde_json::from_str(payload)?;let head=evolution_head(&db,target)?;
    if ev["schema"].as_i64()!=Some(1) || ev["plan"].as_str()!=Some(&plan.id) || ev["target"].as_str()!=Some(target) || ev["generation"].as_i64()!=Some(head.0) || head.1!=plan.id || ev["source_sha256"].as_str()!=Some(&prompt.sha256) || ev["tool"].as_str()!=Some(plan.tool.as_str()) || ev["exit_code"].as_i64()!=Some(0) {return Ok(None);}
    let roots=witness_roots(plan,opts)?;
    if ev["roots"]!=serde_json::to_value(&roots)? {return Ok(None);}
    if ev["seal_policy"].as_str()!=Some(witness_policy(plan)){return Ok(None);}
    if !receipt_variant("A_NoEvidenceSeal") && ev["snapshot"]!=witness_snapshot(&roots,witness_policy(plan))? {return Ok(None);}
    let command:AdapterCommand=serde_json::from_value(ev["command"].clone())?;
    if !matches!(command,AdapterCommand::Activate{..}) {return Ok(None);}
    let captured=crate::adapter::process::Captured {stdout:ev["stdout"].as_str().unwrap_or_default().into(),stderr:ev["stderr"].as_str().unwrap_or_default().into(),exit_code:0,timed_out:false,truncated:false,argv:serde_json::from_value(ev["argv"].clone())?};
    let mut initial=Envelope::new(plan.tool,"activate");initial.preview=false;
    let response=crate::adapter::normalize::normalize(plan.tool,&command,&captured,initial);
    let scope=plan.scope.unwrap_or(Scope::User);let project=plan.project_dir.as_ref().map(PathBuf::from);
    if !receipt_witness(&response) || !receipt_disk(plan,prompt,scope,project.as_ref(),opts)? {return Ok(None);}
    Ok(Some(response))
}
fn witness_cached(opts:&AdapterOptions)->Option<Envelope> {
    opts.extra_env.get("WITNESS_REUSED_ENVELOPE").and_then(|s|serde_json::from_str::<Envelope>(s).ok()).map(|mut e|{e.status=ToolStatus::Active;e})
}
