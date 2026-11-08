# VCE: code and experimental data

Research artifact for **VCE: Efficient Native Configuration Deployment Recovery Using Validated Completion Evidence**.

This repository contains the implementation, retained experimental observations,
analysis scripts, and data-oriented supplements S1/S2. It does not contain the
submitted manuscript or author photographs.

## Read the supplements

- [S1: Validation records and primary statistics](generated/S1_Validation_and_Statistics.md)
- [S2: Scale and layout results](generated/S2_Scale_Results.md)
- [Generated numerical and source-audit tables](generated/tables/)

Plain-text copies of S1/S2 are in the same directory.

## Recreate the tables and supplements

Python 3.10 or newer; no additional packages or network required:

```sh
python generate_supplements.py
python generate_supplements.py --check
```

The first command reads retained records and generates the MD, TXT, CSV, and JSON
outputs. The second checks that they agree with the inputs and package manifest.
It does not collect new measurements. Stored bootstrap confidence intervals and
manual source-audit records are identified separately from recomputed statistics.

To build a ZIP with a refreshed file manifest:

```sh
python build_package.py
```

## Contents

| Path | Content |
|---|---|
| `Research_Artifact/native/` | Native coordinator, gates, adapters, and Cargo lockfile |
| `Research_Artifact/paper/evidence/` | Primary observations, safety and lifecycle checks, and scale study |
| `Research_Artifact/paper/auditstudy/` | Experiment and analysis drivers |
| `Research_Artifact/paper/results_v17/` | Frozen primary estimates and sensitivity outputs |
| `Research_Artifact/paper/results_scale_v18/` | Scale-study estimates |
| `Research_Artifact/.research-source/` | Public repository instruction payloads and retained licenses |
| `Research_Artifact/manuscript/` | Historical plotting code and data inputs only |
| `Historical_Evidence/` | Separate earlier runtime records and compatibility notes |
| `generated/` | Rebuildable S1/S2 and tables |

The primary study contains 2,448 scored timing observations and 204 warm-ups.
The separate scale study contains 1,296 scored observations and 108 warm-ups,
plus 12 separate smoke cases. The datasets are not pooled.

## Reproduction scope

The lightweight generator above verifies saved observations on any supported
Python installation. Native experiment reruns require the Windows/Rust/Python
environment described in [Research_Artifact/README.md](Research_Artifact/README.md).
Run new measurements into a fresh output directory.

Recorded timestamps, source hashes, method IDs, and author-workstation paths are
historical provenance; they are not dependencies of the portable generator.
See [source provenance](Research_Artifact/PROVENANCE.md) and
[public-distribution notes](PUBLIC_DISTRIBUTION.md).

## License

The inherited implementation retains the [PolyForm Noncommercial License 1.0.0](LICENSE)
and its required copyright notice. Third-party input payloads retain their own
licenses. No repository-wide relicensing of third-party materials is implied.

## Citation and version

The submission snapshot will be tagged `v1.0-submission`. Use its commit identifier
when identifying the exact data/code version. No DOI is claimed by this repository;
a DOI requires a separate archival deposit.

Contact: Shujuan Tian, sjtianwork@xtu.edu.cn.
