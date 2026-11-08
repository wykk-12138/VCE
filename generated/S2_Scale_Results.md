# S2. Scale and layout results

VCE: Efficient Native Configuration Deployment Recovery Using Validated Completion Evidence

Generated from Research_Artifact/paper/evidence/scale-v18/. The primary v17 experiment is separate; its observations are not pooled with this study.

## S2.1 Design and records

| Factor | Values |
| --- | --- |
| Additional files | 0, 64, 256, 512, 1024, 2048 |
| Size per file | 1 KiB |
| Layout | Nested subdirectory; flat project root |
| Method | J-Q; Full-tree; VCE |
| Inputs | 12 paired repository payloads |
| Batches | 3 serial batches |
| Timing | Cold recovery after caller exit following native completion |
| Per displayed row | 36 observations = 12 inputs x 3 batches |

| Batch | Scored | Warm-ups |
| --- | --- | --- |
| b1 | 432 | 36 |
| b2 | 432 | 36 |
| b3 | 432 | 36 |

Separate smoke run: 12 cases, excluded. Fixture setup, cleanup, artificial edits, and the independent oracle are outside timing. Evidence hits invoke no native process; query recovery invokes version and status. Measured executable SHA-256: b1826c1f2f917af4765b55e7ff52b65926e031df9eeb84700c0665ed74e3a36f.

## S2.2 Complete results

Recovery time, exclusive validation time, and evidence size are medians recomputed from the retained rows. Recovery intervals are copied from the saved 4,000-replicate crossed input/batch bootstrap output. They are pointwise 95% intervals; no new bootstrap is run by this generator. ms = ns / 1,000,000; KiB = bytes / 1,024.

## S2.2.1 Nested files

| Files | Method | Recovery ms | Recorded 95% CI | Validation ms | Evidence KiB |
| --- | --- | --- | --- | --- | --- |
| 0 | J-Q | 335.314 | [332.962, 342.368] | 0.052 | 0.000 |
| 0 | Full-tree | 55.513 | [52.588, 57.412] | 14.414 | 8.588 |
| 0 | VCE | 54.914 | [51.428, 56.973] | 13.129 | 7.273 |
| 64 | J-Q | 335.668 | [327.619, 343.599] | 0.052 | 0.000 |
| 64 | Full-tree | 65.343 | [62.779, 69.756] | 23.003 | 27.401 |
| 64 | VCE | 53.486 | [51.700, 56.585] | 13.058 | 7.273 |
| 256 | J-Q | 332.469 | [328.409, 343.926] | 0.052 | 0.000 |
| 256 | Full-tree | 89.943 | [86.056, 93.642] | 47.720 | 83.838 |
| 256 | VCE | 54.322 | [51.201, 55.940] | 12.922 | 7.273 |
| 512 | J-Q | 334.441 | [327.746, 344.806] | 0.052 | 0.000 |
| 512 | Full-tree | 122.328 | [119.611, 130.108] | 81.050 | 159.088 |
| 512 | VCE | 54.277 | [51.743, 55.279] | 12.951 | 7.273 |
| 1024 | J-Q | 335.695 | [330.380, 344.158] | 0.052 | 0.000 |
| 1024 | Full-tree | 194.345 | [189.507, 201.337] | 151.667 | 309.588 |
| 1024 | VCE | 53.101 | [51.297, 55.523] | 12.929 | 7.273 |
| 2048 | J-Q | 338.882 | [331.236, 344.397] | 0.051 | 0.000 |
| 2048 | Full-tree | 336.119 | [327.225, 346.844] | 294.982 | 610.588 |
| 2048 | VCE | 54.463 | [51.428, 59.069] | 13.113 | 7.273 |

## S2.2.2 Flat files

| Files | Method | Recovery ms | Recorded 95% CI | Validation ms | Evidence KiB |
| --- | --- | --- | --- | --- | --- |
| 0 | J-Q | 333.853 | [328.329, 339.657] | 0.052 | 0.000 |
| 0 | Full-tree | 54.790 | [52.630, 57.804] | 13.472 | 8.468 |
| 0 | VCE | 53.518 | [51.775, 56.796] | 12.916 | 7.273 |
| 64 | J-Q | 333.415 | [324.894, 341.243] | 0.052 | 0.000 |
| 64 | Full-tree | 63.105 | [60.564, 65.160] | 22.282 | 26.218 |
| 64 | VCE | 54.849 | [52.141, 57.284] | 13.240 | 7.273 |
| 256 | J-Q | 337.453 | [331.816, 342.559] | 0.052 | 0.000 |
| 256 | Full-tree | 89.503 | [85.642, 92.193] | 47.041 | 79.468 |
| 256 | VCE | 55.309 | [52.219, 59.147] | 13.450 | 7.273 |
| 512 | J-Q | 339.143 | [332.204, 346.352] | 0.053 | 0.000 |
| 512 | Full-tree | 124.438 | [121.582, 130.199] | 82.107 | 150.468 |
| 512 | VCE | 54.158 | [52.011, 58.116] | 13.567 | 7.273 |
| 1024 | J-Q | 337.294 | [332.014, 345.289] | 0.053 | 0.000 |
| 1024 | Full-tree | 194.846 | [184.943, 211.482] | 152.503 | 292.468 |
| 1024 | VCE | 55.686 | [53.541, 58.332] | 14.184 | 7.273 |
| 2048 | J-Q | 346.687 | [336.598, 352.956] | 0.052 | 0.000 |
| 2048 | Full-tree | 327.273 | [322.430, 342.908] | 285.503 | 576.468 |
| 2048 | VCE | 55.678 | [53.663, 59.193] | 15.519 | 7.273 |

## S2.3 Files and regeneration

| Material | Path from package root |
| --- | --- |
| Raw/spec/summary per batch | Research_Artifact/paper/evidence/scale-v18/b1/ (also b2/, b3/, smoke/) |
| Saved full estimates | Research_Artifact/paper/results_scale_v18/scale-summary.json |
| Generated table | generated/tables/S2_Scale_Results.csv |
| Experiment driver | Research_Artifact/paper/auditstudy/scale_v18.py |
| Original analysis provenance | Research_Artifact/scale-study-provenance/ |
| Source hashes | generated/SOURCE_MANIFEST.csv |

Recreate this file and the CSV: python generate_supplements.py. Verify without writing: python generate_supplements.py --check. Fresh experiment execution is separate and requires the native build/environment documented in Research_Artifact/SCALE-EXTENSION-2026-10-29.md. Use a new output directory for any new measurements.
