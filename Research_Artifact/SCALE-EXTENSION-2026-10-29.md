# Scale and layout study

Recorded observations: `paper/evidence/scale-v18/b1/`, `b2/`, `b3/`, and `smoke/`.
Retained statistics: `paper/results_scale_v18/`.
Original analysis and source verification: `scale-study-provenance/`.

For analysis of saved observations, run the repository-root supplement generator.
It recomputes medians while retaining the recorded bootstrap confidence intervals.

To execute new native measurements, build the coordinator first and use the driver
from this directory. Run `python -m paper.auditstudy.scale_v18 --help` for arguments.
Specify a fresh output directory and the verified SHA-256 of the executable via
`--expected-binary-sha256`. The recorded executable hash identifies the original
study; a rebuilt executable has a separate identity and its results must remain
separate from the retained observations. The driver refuses existing batch output.
