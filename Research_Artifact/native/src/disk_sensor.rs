fn receipt_disk(plan: &Operation, prompt: &PromptDetail, scope: Scope, project: Option<&PathBuf>,opts: &AdapterOptions) -> Result<bool> {
    let _span=crate::research_fault::Span::new("readback");
    let (instruction,configuration)=research_targets(plan.tool,scope,project,opts)?;
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
    Ok(matches && reference)
}
