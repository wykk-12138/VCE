# Published-system CPU comparison v6

The experiment tests one approved deployment per independent filesystem/database fixture. All methods run the original Rust/adapter path and the same original public project bytes. The 12-project corpus is reused from v8; it is an existing regression corpus, not a newly unseen test set. Within each repository/tool/scenario/repetition block, method order uses a fixed random seed. Three adapters are Claude, Codex and Grok; none invokes an LLM.

## Execution and faults

1. **normal:** original preview followed by one deployment.
2. **after_native:** the original adapter has returned after modifying files, but its manager completion has not committed. Rust and its enclosing workflow process exit with code 86.
3. **after_external:** the original manager returns, but the external activity result has not been checkpointed by the workflow engine. The enclosing process exits with code 86.
4. **after_step:** the engine has observed a completed activity; DBOS has saved its step result, Histrio's actor state is durably committed, and Netherite has delivered the activity result to the orchestration. Netherite pipelines commits, so this hook alone is not asserted to be a forced storage flush. The process exits with code 86.
5. **completed_retry:** restart and request the same operation identity after an acknowledged completion.
6. **external_after_step:** edit the managed file after the preceding engine-specific completion boundary, then restart. This is a contract-characterization case, not a comparison that labels historical workflow receipts as fresh state validation.

Engines retain their normal checkpoint/replay implementations. All three published engines invoke `activity.py`, which uses the original native confirm API and obtains a new original preview when an earlier preview has already been consumed. It contains no ReceiptCoordinator or NativeJournal recovery logic. Traditional comparisons are the independent NativeJournal implementation and original re-preview/re-confirm. The composition control explicitly supplies NativeJournal or ReceiptCoordinator as a DBOS activity.

## Independent measurements

After execution, the oracle independently reads managed files, native references, original adapter status, operation records, activation records, and unrelated context. Report state coherence, unique logical completion, number of successful native execute records, number of external activation invocations on resume, preservation of edits, and genuine process exits. More than one successful record within a logical episode is called a duplicate native completion record, not a double financial charge or a violation of an engine's internal database transaction guarantee.

Historical workflow results and current-state validation have different meanings. In the externally edited-file case, report whether the file edit was preserved, whether the returned value was historical, and whether current state matches. Do not relabel a cached history response as a newly verified current success. The regular fresh-completion cases continue to use the full state oracle.

Parallel runs measure correctness and counts only. Their elapsed times are retained diagnostically and are ineligible for speed rankings. A separate sequential run measures cold invocation latency (including workflow imports, host startup, local service clients and teardown), and loaded-controller latency. Resident storage services start outside individual invocations. These times characterize the selected local configurations, not distributed scalability or the original journals' cloud results. Netherite's default 45-second blob lease following an abrupt process exit is a configuration fact; it must not be presented as an intrinsic algorithmic slowdown.

## Frozen artifacts and reporting

Every run saves its input list, method/scenario set, random seed implementation, source hashes, source snapshot, relevant binary hashes, raw observations and completion report. Failed development runs remain under separate names and are excluded from confirmation estimates. Confirmation infrastructure errors remain reported; successful methods are not selected after observing rankings. Histrio's 2025 public polling implementation and the unverified 2026 journal extension are not interchangeable.

For paired latency comparisons, first aggregate repetitions within repository/tool/method/scenario, then compute ratios over matched repository blocks. Bootstrap repositories, not individual repeated measurements, for 95% confidence intervals. Report raw counts and equalities directly; absence of observed errors does not establish universal correctness. The earlier v8 formal arguments, native-fault tests, ablations and performance evidence remain separate artifacts.

## Declared post-matrix stronger retry follow-up

After inspecting the initial matrix, a stronger application retry configuration is evaluated for all three author engines in the after_native scenario. Set `PUBLISHED_ACTIVITY_PROFILE=replan_on_recovery`: on restart, the common original-native activity obtains a fresh original preview even if the previous operation has not reached `succeeded`. This uses the same existing original re-preview/re-confirm policy available to OriginalReplan. It introduces no receipt reconciliation and no proposed controller. The additional 12 projects × 3 adapters × 3 engines = 108 cases are retained separately; they are not merged into the frozen initial matrix. Report completion and repeated activation counts, including improved baseline results.

The first serial cost run `published-cold-timing-v6` overlapped development of the retry-profile option in `activity.py`. The option was inactive for normal deployment, but the source tree changed during collection. It is therefore retained as development evidence. The reported cost run is `published-cold-timing-final-v6`, collected after the stronger-retry experiment with the completed worker source frozen; the two cost runs are never pooled. This is a collection-integrity distinction, not an outcome-based exclusion.
