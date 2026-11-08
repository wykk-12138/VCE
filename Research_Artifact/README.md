# Native research artifact

## Saved-data analysis

From the repository root, run `python generate_supplements.py` and
`python generate_supplements.py --check` to reproduce and verify S1/S2.

From this `Research_Artifact/` directory, `python -m paper.auditstudy.analyze`
recomputes the primary bootstrap analysis into `recomputed/results_v17/` and
`recomputed/tables/`. Its Python dependencies are recorded in
`requirements-analysis.lock.txt`. Those are historical versions; use a separate
environment when reproducing the original analysis.

## Native build and new experiments

The native path was evaluated on Windows with Python 3.14, Rust MSVC, and Visual
Studio C++ build tools. Rebuild after relocating the checkout because native gate
paths are embedded in the executable:

```sh
python build_native.py
python -m paper.auditstudy.benchmark --out validation/my-batch --batch local-batch --order-seed 18011
python -m paper.auditstudy.branches --out validation/my-branches
python -m paper.auditstudy.lifecycle --out validation/my-lifecycle
```

Use fresh output directories and run timing experiments serially. New measurements
must not replace the frozen observations supplied with the paper. Optional DBOS
reruns require the separate environment in `requirements-dbos.lock.txt` and
`RC_DBOS_PYTHON` pointing to its interpreter.

For the separate scale driver, see `SCALE-EXTENSION-2026-10-29.md`.
Historical plotting inputs remain under `manuscript/figure-data/`; that directory
name is retained for compatibility and contains no submitted article text.
`python tools/replot.py` regenerates the historical ten-figure set, not the latest
submission's complete figure layout.

Earlier release-verification reports and old manuscript validation utilities are
excluded from this public package. The repository-root generator and manifest
describe this distribution. Native implementation and recorded data preserve their
original source lineage and license; see `PROVENANCE.md`.
