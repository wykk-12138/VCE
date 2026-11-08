# Public distribution notes

This repository is prepared from the submission's retained code/data distribution.
The main manuscript, old article drafts, author photographs, old manuscript
compilation outputs, editing prompts, and redundant recomputed copies are omitted.
The existing source licenses and public input licenses are preserved.

Native source and retained observation files are copied without changing numerical
observations. Plot input paths under `Research_Artifact/manuscript/figure-data/`
are retained for existing script compatibility. That subtree contains data and
plotting sources, not the paper text.

The public README, supplement-generation notes, and archive builder describe this
distribution. The public archive builder excludes `.git/` so that credentials,
repository configuration, and local history are never included in generated ZIPs.

The generated source manifest identifies input bytes. Regeneration reads saved
records; it is not a new native experiment or an independent provenance attestation.
Historical source hashes and local filesystem paths in raw experiment records are
retained as provenance. The recorded environment is not recreated by opening a file.

Codex assisted with preparing the data summaries, generation scripts, and public
package organization. No new experimental observations were created during this
packaging step.
