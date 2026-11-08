# Published baseline selection before outcomes

Date: 2026-10-11. Requested window: 2024–2026, including 2025 and 2026. Formal publisher/conference records are required; a preprint alone is not a formally published journal baseline. Re-publications/extensions of one system do not count twice. IEEE journals are preferred when the task matches. Method names in tables retain the authors' names; implementation provenance/version/capability mapping is recorded once in the artifact.

## Fixed matching question

The target is a CPU-executable coordinator that receives an approved deterministic deployment, invokes real external native file effects, records its progress and restarts after process failure. Compare goal completion, external-change preservation, logical duplicate records, repeated external invocations and full operation/resume cost. Database-only exactly-once claims do not automatically transfer to external filesystem effects. A common application activity may supply domain validation, but must not silently implement the proposed entire recovery engine for every baseline.

Eligible task groups: (A) actual durable workflow/actor execution with external activity integration; (B) actual configuration enforcement with independently specified deployment predicates. Group B cannot replace missing group A recovery guarantees. Retain unavailable/incompatible candidates in the selection record. No exclusion uses measured performance, and failed builds are distinguished from theoretical incompatibility.

Traditional comparators: NativeJournal (independent stable intent, conflict guards and atomic completion) and OriginalReplan (native re-preview/re-confirm), with OriginalConfirm and the earlier OCCRecovery evidence retained. NativeJournal is an artifact-defined traditional composition, not a published author system.

## Initial formal candidates

| Author system | Verified publication | Initial task match |
|---|---|---|
| DBOS | The VLDB Journal 34, 37 (2025), DOI 10.1007/s00778-024-00899-0 | Durable steps and transactions; original SDK integration must disclose SDK/backend version versus paper |
| Netherite | The VLDB Journal 34, 25 (2025), DOI 10.1007/s00778-024-00898-1 | Durable workflow replay; local SingleHost transport with persistent FASTER/Azurite storage |
| Histrio | Information Systems 140, 102724 (2026), DOI 10.1016/j.is.2026.102724 | Transactional actor state and delivery; arbitrary external native effects need explicit boundary |
| Styx | Proc. ACM Manag. Data 3(3), 226 (SIGMOD 2025), DOI 10.1145/3725363; VLDB Journal 35, 31 (2026), DOI 10.1007/s00778-026-00971-x | Stateful transactional functions; external side effects and Linux/service requirements must be checked; counts as one system |
| AgentSpec | IEEE/ACM ICSE 2026, DOI 10.1145/3744916.3764546 | Runtime enforcement group; not an independently durable workflow engine |

Additional inspected papers: RTSFaaS (USENIX ATC 2025) depends on RDMA as its central mechanism; CPU availability does not imply RDMA NIC availability. IEEE Transactions on Reliability 2025 "Field-based Security Testing of SDN configuration Updates" evaluates SDN reconfiguration tests, not a deployment recovery controller. IEEE TSE 2026 "Configuration Defects in Kubernetes" is an empirical defect study, not a named recovery algorithm. These distinctions are determined before outcome measurements.

No count of five complete matched comparisons is declared until implementations, semantics and actual executions satisfy the matching question. Corpus and prior experiment results remain unchanged.

## Implementation audit and additional candidate

DBOS uses the authors' published PyPI release 3.2.0 with its supported SQLite backend. Netherite uses the authors' NuGet package 2.1.0 with SingleHost transport and persistent FASTER storage through Azurite 3.35.0. Both run actual original configuration activities. These are identifiable author releases related to the journal systems, not reconstructions of the cloud infrastructure or reproduction of the journals' reported performance numbers.

Histrio's unchanged public worker, actor loader, partition management and DynamoDB transaction implementation run locally against DynamoDB Local. The application actor calls the same external activity used by DBOS and Netherite. The public implementation has polling and local notification logs; its Go source and dependencies contain no AmazonMQ/RabbitMQ/AMQP client. Consequently this executed version is credited to **Histrio, DEBS 2025, DOI 10.1145/3701717.3730541**, not counted as a completed reproduction of the 2026 journal notification extension. The journal's FIFO and transactional-state guarantees do not imply arbitrary external file writes participate in the DynamoDB transaction.

The workstation has 24 logical CPUs and approximately 32 GiB RAM, Windows 11, no installed WSL distribution/subsystem, and no Docker or Podman command. The user confirms there is no available Linux server. Styx's pinned source imports uvloop, uses Kafka and S3-compatible storage, and documents Docker deployment. It remains a selected candidate pending a suitable environment and a validated external-activity integration; absence of a runnable environment is not a performance outcome.

Jointλ is an additional formally published 2026 candidate: Software: Practice and Experience 56(9), 1154–1173, DOI 10.1002/spe.70084, first published 8 June 2026. Author code at https://github.com/lihuahua123/jointlambda is pinned at 8af0f3e997bba6609a526686ab0f23ee59d0cdd6. Its contribution includes decentralized cross-cloud continuations and failover, and its documented deployment requires AWS and Alibaba Cloud accounts. Merely executing its checkpoint class on SQLite or one local function would not validate that system. It is retained as an unexecuted candidate, not renamed as a completed baseline.

DBOS+NativeJournal and DBOS+ReceiptCoordinator are explicitly labeled composition controls. They test whether a domain-aware activity closes the external-effect/checkpoint gap, and do not count as additional publications. All methods, including tied or better baselines, remain in the artifact.

Primary publication records: [DBOS](https://link.springer.com/article/10.1007/s00778-024-00899-0), [Netherite](https://link.springer.com/article/10.1007/s00778-024-00898-1), [Histrio 2025 author manuscript](https://re.public.polimi.it/retrieve/9c679ba5-9be2-44d5-8967-90016c3afae9/3701717.3730541.pdf), [Histrio 2026](https://doi.org/10.1016/j.is.2026.102724), [Styx 2026](https://link.springer.com/article/10.1007/s00778-026-00971-x), [Jointλ 2026](https://onlinelibrary.wiley.com/doi/10.1002/spe.70084).
