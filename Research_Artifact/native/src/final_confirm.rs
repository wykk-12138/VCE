pub async fn confirm_activate_receipt(
    store: &Store,
    operation_id: &str,
    opts: &AdapterOptions,
) -> Result<OperationResult> {
    let _lock = HomeLock::acquire(store.paths())?;
    let plan = receipt_plan(store, operation_id)?;
    let request: serde_json::Value = serde_json::from_str(&plan.request_json)?;
    let prompt_id = request
        .get("promptId")
        .and_then(|value| value.as_str())
        .ok_or_else(|| Error::user_cancel("activate without confirmed plan"))?;
    let prompt = store.get_prompt(prompt_id)?;
    if prompt.deleted_at.is_some() {
        return Err(Error::user_cancel(
            "prompt deleted since preview; preview again",
        ));
    }
    let planned_sha = request
        .get("fileSha256")
        .and_then(|value| value.as_str())
        .unwrap_or_default();
    if planned_sha != prompt.sha256
        || request
            .get("promptVersion")
            .and_then(|value| value.as_i64())
            .is_some_and(|version| version != prompt.version)
    {
        return Err(Error::user_cancel(
            "prompt changed since preview; run plan-activate again",
        ));
    }
    let mut preview_token = None;
    if let Some(plan_env) = plan.envelope_json.as_deref() {
        if let Ok(preview) = serde_json::from_str::<Envelope>(plan_env) {
            if !preview.ok || !preview.blockers.is_empty() {
                return Err(Error::command_failed(
                    preview
                        .error
                        .unwrap_or_else(|| "preview reported blockers".into()),
                ));
            }
            if plan.tool == ToolKind::Grok {
                preview_token = preview.confirmation_token.clone();
                if preview_token.is_none() {
                    return Err(Error::command_failed(
                        "grok preview did not include a confirmation token",
                    ));
                }
            }
        }
    }
    if let Err(error) = check_adapter_version(plan.tool, opts).await {
        store.update_operation(
            operation_id,
            OperationStatus::Failed,
            None,
            Some(&error.to_string()),
        )?;
        return Err(error);
    }
    let scope = plan.scope.unwrap_or(Scope::User);
    let project_dir = plan.project_dir.as_ref().map(PathBuf::from);
    let name = request
        .get("name")
        .and_then(|value| value.as_str())
        .map(str::to_string)
        .unwrap_or_else(|| cli_name(&prompt));
    ensure_codex_config(prompt.tool, opts);
    let adapter_file = write_adapter_prompt(&prompt)?;
    let command = AdapterCommand::Activate {
        file: adapter_file.0.clone(),
        scope,
        project_dir: project_dir.clone(),
        name: Some(name),
        runtime: request
            .get("runtime")
            .and_then(|value| value.as_bool())
            .unwrap_or(false),
        append_file: request.get("appendFile").and_then(|value| {
            value
                .as_str()
                .filter(|path| !path.is_empty())
                .map(PathBuf::from)
        }),
        max_tokens: request
            .get("maxTokens")
            .and_then(|value| value.as_u64())
            .filter(|tokens| *tokens > 0),
        expected_preview_token: preview_token,
    };
    receipt_execute(store, &plan, &prompt, scope, project_dir.as_ref(), command, request, opts).await
}

pub async fn confirm_activate_journal(
    store: &Store,
    operation_id: &str,
    opts: &AdapterOptions,
) -> Result<OperationResult> {
    let _lock = HomeLock::acquire(store.paths())?;
    let plan = journal_plan(store, operation_id)?;
    let request: serde_json::Value = serde_json::from_str(&plan.request_json)?;
    let prompt_id = request
        .get("promptId")
        .and_then(|value| value.as_str())
        .ok_or_else(|| Error::user_cancel("activate without confirmed plan"))?;
    let prompt = store.get_prompt(prompt_id)?;
    if prompt.deleted_at.is_some() {
        return Err(Error::user_cancel(
            "prompt deleted since preview; preview again",
        ));
    }
    let planned_sha = request
        .get("fileSha256")
        .and_then(|value| value.as_str())
        .unwrap_or_default();
    if planned_sha != prompt.sha256
        || request
            .get("promptVersion")
            .and_then(|value| value.as_i64())
            .is_some_and(|version| version != prompt.version)
    {
        return Err(Error::user_cancel(
            "prompt changed since preview; run plan-activate again",
        ));
    }
    let mut preview_token = None;
    if let Some(plan_env) = plan.envelope_json.as_deref() {
        if let Ok(preview) = serde_json::from_str::<Envelope>(plan_env) {
            if !preview.ok || !preview.blockers.is_empty() {
                return Err(Error::command_failed(
                    preview
                        .error
                        .unwrap_or_else(|| "preview reported blockers".into()),
                ));
            }
            if plan.tool == ToolKind::Grok {
                preview_token = preview.confirmation_token.clone();
                if preview_token.is_none() {
                    return Err(Error::command_failed(
                        "grok preview did not include a confirmation token",
                    ));
                }
            }
        }
    }
    if let Err(error) = check_adapter_version(plan.tool, opts).await {
        store.update_operation(
            operation_id,
            OperationStatus::Failed,
            None,
            Some(&error.to_string()),
        )?;
        return Err(error);
    }
    let scope = plan.scope.unwrap_or(Scope::User);
    let project_dir = plan.project_dir.as_ref().map(PathBuf::from);
    let name = request
        .get("name")
        .and_then(|value| value.as_str())
        .map(str::to_string)
        .unwrap_or_else(|| cli_name(&prompt));
    ensure_codex_config(prompt.tool, opts);
    let adapter_file = write_adapter_prompt(&prompt)?;
    let command = AdapterCommand::Activate {
        file: adapter_file.0.clone(),
        scope,
        project_dir: project_dir.clone(),
        name: Some(name),
        runtime: request
            .get("runtime")
            .and_then(|value| value.as_bool())
            .unwrap_or(false),
        append_file: request.get("appendFile").and_then(|value| {
            value
                .as_str()
                .filter(|path| !path.is_empty())
                .map(PathBuf::from)
        }),
        max_tokens: request
            .get("maxTokens")
            .and_then(|value| value.as_u64())
            .filter(|tokens| *tokens > 0),
        expected_preview_token: preview_token,
    };
    journal_execute(store, &plan, &prompt, scope, project_dir.as_ref(), command, request, opts).await
}
