use std::io::{self, BufRead};
use std::path::PathBuf;
use std::str::FromStr;
use receiptcoordinator_lib::{adapter::AdapterOptions, db::Store, models::*, ops, paths::AppPaths};
use serde_json::{json, Value};

async fn handle(input: Value) -> receiptcoordinator_lib::error::Result<Value> {
    let root=PathBuf::from(input["root"].as_str().unwrap());
    let source=PathBuf::from(input["source_root"].as_str().unwrap());
    let tool=ToolKind::from_str(input["tool"].as_str().unwrap())?;
    let paths=AppPaths::from_home(root.join("switch"));
    let store=Store::open(&paths)?;
    let home=root.join("home");
    let scope=if tool==ToolKind::Claude {Scope::Project} else {Scope::User};
    let project=if tool==ToolKind::Claude {Some(input["project_dir"].as_str().map(PathBuf::from).unwrap_or(root.join("project")))} else {None};
    std::env::set_var("RECEIPTCOORDINATOR_RESEARCH_VARIANT",input["method"].as_str().unwrap_or(""));
    let mut options=AdapterOptions {home:Some(home.clone()),cli_override:Some(source.join("adapters").join(tool.vendored_rel())),..Default::default()};
    options.extra_env.insert("CODEX_HOME".into(),home.join(".codex").to_string_lossy().into_owned());
    options.extra_env.insert("CLAUDE_CONFIG_DIR".into(),home.join(".claude").to_string_lossy().into_owned());
    options.extra_env.insert("APPDATA".into(),home.join("AppData/Roaming").to_string_lossy().into_owned());
    options.extra_env.insert("LOCALAPPDATA".into(),home.join("AppData/Local").to_string_lossy().into_owned());
    let start=std::time::Instant::now();
    let result=match input["command"].as_str().unwrap() {
        "plan" => {
            let content=std::fs::read_to_string(root.join("candidate.md"))?;
            let prompt=ops::create_prompt(&store,CreatePromptInput {tool,title:"public-corpus-research".into(),content,tags:vec![]})?;
            let plan=ops::plan_activate_evolution(&store,PlanActivateInput {prompt_id:prompt.id.clone(),scope,project_dir:project,
                runtime:false,append_file:None,max_tokens:None},&options).await?;
            json!({"plan":plan,"prompt_id":prompt.id})
        },
        "confirm" => {
            let operation=input["operation_id"].as_str().unwrap();
            std::env::set_var("RECEIPTCOORDINATOR_RESEARCH_VARIANT",input["method"].as_str().unwrap_or(""));
            let result=if input["method"].as_str().is_some_and(|m|m=="ReceiptCoordinatorV13" || m=="ReceiptCoordinatorV14" || m=="A_NoEvidenceSeal" || m=="ReceiptCoordinatorV15" || m=="A_NoResidueWatch") {
                ops::confirm_activate_receipt_evolution(&store,operation,&options).await?
            } else if input["method"].as_str().is_some_and(|m|m=="JournalGuarded" || m=="JournalGuardedScoped" || m=="JournalWitnessScoped" || m=="JournalWitnessV15" || m=="JournalPostStatus") {
                ops::confirm_activate_journal_evolution(&store,operation,&options).await?
            } else if input["method"].as_str()==Some("VerifiedCoordinator") {
                ops::confirm_activate_verified(&store,operation,&options).await?
            } else if input["method"].as_str()==Some("NativeJournal") {
                ops::confirm_activate_journal(&store,operation,&options).await?
            } else if input["method"].as_str().is_some_and(|m|m=="ReceiptCoordinator" || m.starts_with("A_")) {
                ops::confirm_activate_receipt(&store,operation,&options).await?
            } else if input["method"].as_str()==Some("OriginalReplan") && input["retry"].as_bool()==Some(true) {
                let plan=ops::plan_activate(&store,PlanActivateInput {prompt_id:input["prompt_id"].as_str().unwrap().into(),scope,
                    project_dir:project,runtime:false,append_file:None,max_tokens:None},&options).await?;
                if !plan.envelope.ok {return Ok(json!({"ok":true,"elapsed_ns":start.elapsed().as_nanos(),"data":{"result":plan}}));}
                ops::confirm_activate(&store,&plan.operation_id,&options).await?
            } else {ops::confirm_activate(&store,operation,&options).await?};
            json!({"result":result})
        },
        "status" => json!({"envelope":receiptcoordinator_lib::adapter::run_adapter_with(tool,
            receiptcoordinator_lib::adapter::AdapterCommand::Status {scope,project_dir:project,name:Some(tool.default_name().into())},&options).await?}),
        "change_source" => {
            let prompt=ops::evolution_update_prompt(&store,UpdatePromptInput {id:input["prompt_id"].as_str().unwrap().into(),title:None,
                content:Some("CHANGED LIBRARY SOURCE AFTER PREVIEW\n".into()),tags:None})?;
            json!({"prompt":prompt})
        },
        "records" => json!({"operations":store.list_operations(Some(tool))?,"activations":store.list_activations(tool)?}),
        _ => return Err(receiptcoordinator_lib::error::Error::invalid("unknown research command")),
    };
    Ok(json!({"ok":true,"elapsed_ns":start.elapsed().as_nanos(),"data":result}))
}

#[tokio::main]
async fn main() {
    for line in io::stdin().lock().lines() {
        let line=line.unwrap();
        let response=match handle(serde_json::from_str(&line).unwrap()).await {
            Ok(value)=>value,
            Err(error)=>json!({"ok":false,"kind":error.kind(),"error":error.to_string()}),
        };
        println!("{}",response);
    }
}
