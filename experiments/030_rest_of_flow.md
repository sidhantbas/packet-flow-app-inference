---
title: '030: Rest-of-flow statistics (Task 1), from the given dataset only'
created: 2026-10-01
creator: sidhantbas
description: Do exact statistics of packets 6..N, derived from the Task 1 and Task 2 rows of the same flow, help Task 1?
experiment:
  id: '030'
  tasks:
  - task1
  lever: features
  status: rejected
  verdict: 'Exact rest-of-flow statistics as columns: -0.0095 added, -0.040 replacing the opening columns (later used as an expert in 065)'
---
# 030: Rest-of-flow statistics (Task 1), from the given dataset only

- **Date:** 2026-10-01
- **Question:** Do exact statistics of packets 6..N, derived from the Task 1 and Task 2 rows of the same flow, help Task 1?
- **Status:** done; rejected
- **Script:** `src/exp030_rest_of_flow.py`; `cv.rest_of_flow`, `cv.task1_prefix_rest_features`, `cv.task1_rest_features`
- **Runs:** `results/*_030_*`

## Derivation (validated on all 411 flows)

Totals, means and population stds subtract exactly between the full flow and its first 5 packets: per direction,
count, bytes, sum of squared sizes -> mean and std of the remaining packets; timing: duration after packet 5 and mean/std
of the remaining gaps. No negative counts, bytes or variances in any flow; transport and start_rel identical in both
files; full min IAT <= prefix min IAT and full max IAT >= prefix max IAT for every flow.

## Results (cv_seed 2026, vs Task 1 champion)

| Variant | Columns | Macro F1 | Δ | W / L / T |
|---|---|---|---|---|
| rest_add | 17 + 17 prefix + 11 rest | 0.797 | -0.0095 | 10 / 29 / 11, WORSE |
| rest_swap | 17 + 11 rest (no raw prefix) | 0.767 | -0.040 | 7 / 43 / 0, WORSE |

## Interpretation

After the opening, a flow is described almost entirely by its full-flow statistics already (for most flows packets
6..N are nearly the whole flow), so the rest columns are redundant and dilute the ensemble. Removing the raw
first-5-packet columns costs 0.040: the opening is where Task 1's extra information is, consistent with 022.

## Decision

Reject both.
