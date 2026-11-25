---
title: Experiments folder
created: 2026-10-13
creator: sidhantbas
description: How the experiments folder is organised and where each experiment's code, runs and evidence live.
---

# Experiments

One Markdown log per experiment, `NNN_name.md`, numbered in the order the experiments were run. The full index, with every
result, status and decision, is [EXPERIMENTS.md](../EXPERIMENTS.md).

| What | Where |
|---|---|
| Protocol and results | `NNN_name.md` here. The protocol is committed before any run; results are added below it |
| Status and verdict | The `experiment:` block in each log's front matter (read by the index) |
| Code | `src/expNNN_*.py`, catalogued in [src/README.md](../src/README.md) |
| CV runs | `results/<UTC stamp>_NNN_<name>/`, immutable and hash-verified (`src/runs.py verify`) |
| Small evidence files | `NNN_evidence/` here, next to the log |
| New experiment | Copy [TEMPLATE.md](TEMPLATE.md); after the runs, fill the `experiment:` block and regenerate the index |

Rules for a valid experiment (frozen protocol, paired folds, rule v2, never-used seeds, upload rule) are in
AGENTS.md.
