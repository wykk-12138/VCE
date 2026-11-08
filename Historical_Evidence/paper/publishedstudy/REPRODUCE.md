# Reproduce the published-system addendum

This addendum supplements the v8 native experiment artifact. It adds actual author DBOS, Netherite and Histrio runtimes. It does not replace the native source, its correctness oracle or the earlier evidence. Restore the v8 source/toolchain/corpus first; `paper.finalstudy.prepare` and its existing documentation build `research-final.exe` from the pinned project. All commands below run from the workspace root. Use new output directories: a run refuses to overwrite retained evidence.

## Local prerequisites and versions

Windows x64, Python 3.12 for published SDK workers, Python 3.14 for the native project's unchanged interpreter selection, Node.js, roughly 32 GiB RAM for the parallel configuration. CPU only; no language-model endpoint, GPU, cloud account or paid API is used. SQLite, Azurite, and DynamoDB Local serve independent per-case databases. Local services are owned by the runner and terminated when it exits. Do not interrupt a timing run with another experiment.

Pinned components: DBOS 3.2.0, Netherite 2.1.0, Azurite 3.35.0, .NET SDK 8.0.425, Go 1.22.12, and the recorded DynamoDB/JRE archives. `requirements.lock.txt` records the complete Python environment. `published_sources_v6.json`, `published_dotnet_v6.json`, and `published_actor_toolchain_v6.json` record download locations, commit IDs and checksums. `restore_sources.py` restores recorded commits; `acquire.py` is the original discovery tool and should not be used to reproduce a pinned run.

```powershell
python -m paper.publishedstudy.restore_sources
py -3.12 -m venv .research-toolchain/published-env
& .research-toolchain/published-env/Scripts/python.exe -m pip install -r paper/publishedstudy/requirements.lock.txt
python -m paper.publishedstudy.bootstrap_dotnet
python -m paper.publishedstudy.bootstrap_actor
python -m paper.publishedstudy.build_histrio
npm install --prefix .research-toolchain/azurite-published --no-audit --no-fund azurite@3.35.0
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE='false'
& .research-toolchain/dotnet-published/dotnet.exe build paper/publishedstudy/netherite/Published.csproj -c Release -o .research-toolchain/netherite-bin
```

Client endpoints use 127.0.0.1 ports 11380–11382 for Azurite and 11400 for DynamoDB Local. Azurite is explicitly bound to loopback. The inspected DynamoDB Local build retains its default wildcard listener despite the Java host property; its test databases contain public fixtures and local dummy credentials, and the runner terminates the process after the run. The runner checks availability and never terminates an existing service to acquire a port. Java/DynamoDB files and Go caches remain under `.research-toolchain`; there is no persistent PATH modification. The first original .NET development build printed creation of an ASP.NET development certificate; subsequent reproduction can suppress this through the environment variable above and does not need certificate trust.

## Experiments

```powershell
python -m paper.publishedstudy.run --out paper/evidence/my-core --split confirmation --methods ReceiptCoordinator NativeJournal OriginalReplan DBOS Histrio --workers 8
python -m paper.publishedstudy.run --out paper/evidence/my-netherite --split confirmation --methods Netherite --workers 8
python -m paper.publishedstudy.run --out paper/evidence/my-compositions --split confirmation --methods DBOS+NativeJournal DBOS+ReceiptCoordinator --workers 4
$env:PUBLISHED_ACTIVITY_PROFILE='replan_on_recovery'
python -m paper.publishedstudy.run --out paper/evidence/my-strong-retry --split confirmation --methods DBOS Netherite Histrio --scenarios after_native --workers 8
Remove-Item Env:PUBLISHED_ACTIVITY_PROFILE
python -m paper.publishedstudy.run --out paper/evidence/my-timing --split confirmation --scenarios normal --repeats 3 --workers 1
python -m paper.publishedstudy.validate --runs paper/evidence/my-core paper/evidence/my-netherite paper/evidence/my-compositions paper/evidence/my-timing
python -m paper.publishedstudy.analyze --runs paper/evidence/my-core paper/evidence/my-netherite paper/evidence/my-compositions --timing paper/evidence/my-timing --out paper/results-v6-reproduction
```

Run the final timing command after all preceding correctness commands have completed. The 12 repositories supply one payload each, three native adapters and six correctness scenarios. This gives 1,296 main comparison cases plus 432 composition cases, followed by 108 stronger-retry cases. The sequential timing run gives 648 normal-deployment measurements. Genuine exits use code 86 and are checked. Netherite's unchanged blob lease can add approximately 45 seconds to a crash recovery; parallel correctness workers overlap these waits, but their timings are never used as performance rankings. The published report uses `published-cold-timing-final-v6`; the earlier `published-cold-timing-v6` is development evidence (see PROTOCOL.md).

Method names remain the authors' system names. Version, backend and task mapping are disclosed once in SELECTION.md. In particular, the executed Histrio code is its public DEBS 2025 polling runtime; the 2026 AmazonMQ extension has not been reproduced. The five-recent-full-baseline requirement remains open until two further distinct eligible systems and a fully executed 2026 method are present. The existing AgentSpec verification experiment is a different task group and is not counted as another crash-recovery engine.
