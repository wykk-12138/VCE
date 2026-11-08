# CPU reproduction: published runtimes and native deployment endpoints

This supplement accompanies `manuscript_v10.md`. The native implementation and its v8 measurements remain unchanged. Run names and hashes identify experiments; installation and development logs are artifact metadata.

## Implementations and evaluated contracts

| System | Publication | Executed implementation | Evaluated boundary |
|---|---|---|---|
| DBOS | VLDB Journal, 2025 | Author Python SDK 3.2.0; SQLite | Original native activity, strengthened re-preview activity, domain-aware compositions |
| Netherite | VLDB Journal, 2025 | Author NuGet 2.1.0; SingleHost FASTER/Azurite | Activity replay and native effects |
| Histrio | DEBS, 2025 | Pinned public polling runtime; DynamoDB Local | Actor processing and external native activity |
| Styx | SIGMOD, 2025; VLDB Journal, 2026 | Author commit `e1c76b2378ab89e9c5c80f116a637d7220444a48`; one snapshot-executor repair | Worker loss; snapshot replay; 2→1→2 state migration |
| Halfmoon | TOCS, 2025; public SOSP artifact | Runtime `bc7e0aee47923b4648041a38b61c44fb9f81bddf`; client `0112558a6430e66b7a07ef3b2b41b219117f2582`; one result-encoding repair | Public asymmetric WRITELOG core, actual shared log and function calls, external endpoint termination |

These are five distinct published systems with concrete executed versions. Styx's two publications count once. Halfmoon's public artifact supplies the asymmetric logging core; the experiment does not claim every extension or original paper benchmark. Histrio is credited to the executed 2025 version. NativeJournal and OriginalReplan are the principal traditional controls; compositions do not create additional independent systems. Paper publication years are not treated as release-version identity.

Halfmoon has three sequencers, three persistent storage services, one execution engine, one gateway and two Go function launchers on one CPU host. Its function wrapper and conditional log are author code. DynamoDB Local implements the state-store API. On injected external process exit, the application uses the author's `EXIT` response, then retries the same function-instance identity. This is a real external process failure; whole Halfmoon execution-engine failure is a different boundary. Styx actually terminates and restores workers. No cross-system latency ranking is derived from these distinct boundaries or the WSL transport.

## Common endpoint

`native_endpoint.py` calls the same original Rust binary used in the native study, choosing NativeJournal or ReceiptCoordinator. Both receive the same durable endpoint-result cache. The first condition has normal execution; `after_native` terminates after the native effect before manager completion; `after_external` terminates after the endpoint result is persistent; `completed_retry` invokes the same completed logical operation again. All endpoints use isolated homes and the same public project bytes.

The result cache represents a historical endpoint response. It is not a fresh-state observation after arbitrary later edits. Fresh-state edit-preservation evidence is in the native and published-activity matrices. Oracle checks are outside the measured execution traces.

## Compatibility repairs and regression evidence

1. Styx `worker/async_snapshotting.py`: replace a one-second queue timeout with `await queue.get()` in the snapshot executor. A timeout previously returned the same sentinel used for stream termination, ending the executor during slow external calls. The existing stream-end sentinel remains supported. `validate_runtime.py` runs the real executor after 1.2 seconds of idle time and checks delivery plus sentinel shutdown. Audit: 307 Python files, exactly this file differs from the pinned archive. Patch and before/after hashes: `styx_snapshot_idle.patch` and `evidence/linux_styx_compatibility_v7.json`.
2. Halfmoon `pkg/cayonlib/loglib.go`: serialize a caller-result overwrite using the `IntentLogEntry` envelope already expected by `IntentFsm.Catch`. The callee's result remains in `Data`. Without that envelope the reader interprets the callee ID as the caller ID. The author archive is unchanged; `build_halfmoon.py` patches an isolated build copy, records hashes and cross-compiles the application. `halfmoonapp/logencoding_test.go` verifies caller identity, step, callee payload and stream position against the actual library.

Each repair is shared by both endpoint arms. Source repairs, rather than method substitutions, are explicitly included in the implementation provenance.

## Workstation and storage

Windows 11 host; imported Ubuntu 24.04 distribution `KeysmithResearch`; Microsoft WSL 3.0.1. The guest is capped at eight CPUs, 8 GiB RAM and 2 GiB swap. Guest virtual disk, swap, Docker layers, downloads and experiment fixtures live on D:. WSL system components occupy a small C: installation. The measured C: free space is recorded separately; maintain a 25 GiB reserve.

The D: fixture subtree `.research-toolchain/s7` grants the current user inheritable FullControl. Codex's native transaction hardening requires changing ACLs; an inherited Modify-only grant is insufficient. This is limited to synthetic experiment fixtures. Windows paths are kept short enough for the original native temporary-file names.

Kafka 3.4.1 uses a single local KRaft broker. RustFS 1.0.1 supplies Styx's S3 API. Python 3.14.8 executes the pinned Styx code and author Cython extensions. Halfmoon uses the author's `shengqipku/halfmoon:sosp-ae` image, whose registry manifest and blobs are SHA-verified, and Go 1.22.12 for the application. The author image predates the journal article; its executed core and version scope are explicit. All services bind to local/guest interfaces. No paid cloud accounts, model service or GPU is used.

## Reproduce with the existing D: environment

Use a fresh output directory each time. Paths below are the actual workstation paths; adapt the workspace root when restoring elsewhere. `prepare_cases.py` refuses to overwrite a previous run, fixes fixtures and freezes runtime source hashes before acquisition.

```powershell
. paper/linuxstudy/disk_env.ps1
.research-toolchain/published-env/Scripts/python.exe -m paper.linuxstudy.prepare_cases --split confirmation --out paper/evidence/styx-replay-v7
& 'C:/Program Files/WSL/wsl.exe' -d KeysmithResearch --exec env KEYSMITH_STYX_RUN=/opt/keysmith/run-replay-v7 /opt/keysmith/styx-env/bin/python /mnt/d/Users/star_/Documents/ChatGPT/keysmith-switch/paper/linuxstudy/cluster.py start
& 'C:/Program Files/WSL/wsl.exe' -d KeysmithResearch --exec env KEYSMITH_STYX_RUN=/opt/keysmith/run-replay-v7 /opt/keysmith/styx-env/bin/python /mnt/d/Users/star_/Documents/ChatGPT/keysmith-switch/paper/linuxstudy/run_styx.py --out /mnt/d/Users/star_/Documents/ChatGPT/keysmith-switch/paper/evidence/styx-replay-v7
.research-toolchain/published-env/Scripts/python.exe -m paper.linuxstudy.analyze_styx --run paper/evidence/styx-replay-v7 --out paper/results_v7/styx-replay
& 'C:/Program Files/WSL/wsl.exe' -d KeysmithResearch --exec env KEYSMITH_STYX_RUN=/opt/keysmith/run-replay-v7 /opt/keysmith/styx-env/bin/python /mnt/d/Users/star_/Documents/ChatGPT/keysmith-switch/paper/linuxstudy/cluster.py stop
```

Styx's harness waits for a completed author-engine snapshot between independent failure trials. It restarts only the terminated worker's port and leaves the author's coordinator to restore and replay. Migration uses `styx_migration.py` against a fresh cluster and completed cases; keep its results distinct from the fault matrix.

For Halfmoon, build with `python -m paper.linuxstudy.build_halfmoon`. The initial deployment scripts are `halfmoon_cluster.py start` and `halfmoon_application.py`; named containers are retained after stop. For another run on the retained healthy deployment, start its existing containers and the owned ZooKeeper, DynamoDB and bridge processes, or allocate a fresh prefix/base/ports using the same topology. Prepare with `python -m paper.linuxstudy.prepare_halfmoon --split confirmation --out <fresh-directory>`; execute `run_halfmoon.py --out <Linux-path>`; validate with `analyze_styx.py --run <Windows-path> --out <results-path>`. The shared analyzer selects the engine and failure boundary from the frozen specification. Runtime sources must still match the freeze; analysis source has a separately recorded hash.

`launch_halfmoon_fresh.py --label <new-label>` is an optional fresh-deployment helper. It writes copies of those deployment scripts with a new directory/container prefix and records their hashes, preserving previous runs. Run it after stopping the existing Halfmoon services so ports 18808–18810 are free. This helper was syntax-checked; the reported experiments were executed with the explicit deployment scripts above.

Fresh-machine installation is provided by `acquire_wsl.py`, `install_wsl_system.ps1`, `acquire_ubuntu.py`, `bootstrap.sh`, `acquire_services.py`, `install_styx.sh` and `fetch_halfmoon_image.py`. System installation is separate from experiment execution. Acquisition manifests preserve signatures and digests. Apply the recorded Styx compatibility repair once after source extraction. Kafka was fetched through a mirror and matched against Apache's official SHA-512; the digest is the authoritative identity.

## Evidence layout

- `evidence/styx-confirmation2-v7`: 288 frozen raw cases; 144 worker exits.
- `evidence/halfmoon-confirmation-v7`: 288 frozen raw cases; 144 external endpoint exits.
- `results_v7/styx` and `results_v7/halfmoon`: independent oracle outputs, per-scenario tables and validation.
- `evidence/styx-migration-v7`: 144 response-preservation checks with migration logs.
- `evidence/linux_runtime_audit_v7`: executed-source audit, regression result, dependency versions, image identity and service logs.
- `results_v5`: native safety, ablations and controlled latency. `results_v6`: DBOS, Netherite and Histrio matrices, strengthened activities, compositions and serial cold invocation.
- Development attempts are retained under separately named evidence directories. They are neither merged into confirmation samples nor used for performance selection.

The v10 deliverable is additive to the v8 native-source/corpus package and v9 published-system package. Its manifest validates every included file; large toolchains, images and virtual disks remain outside the archive.
