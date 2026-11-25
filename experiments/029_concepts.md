---
title: '029: Teach concepts first (Task 1)'
created: 2026-10-01
creator: sidhantbas
description: Do behaviour concepts shared across apps ("kinds of run") help Task 1, especially rare apps?
experiment:
  id: 029
  tasks:
  - task1
  lever: features
  status: rejected
  verdict: 'Behaviour concepts (flags -0.000; KMeans kinds of run -0.008): every app makes every kind of run'
---
# 029: Teach concepts first (Task 1)

- **Date:** 2026-10-01
- **Question:** Do behaviour concepts shared across apps ("kinds of run") help Task 1, especially rare apps?
- **Status:** done; rejected
- **Script:** `src/exp029_concepts.py`; `models.concept_flags`, `models.ConceptAugment`
- **Runs:** `results/*_029_*`
- **Reference:** Task 1 champion (022 model)

## Setup (fixed before running)

- **rules:** 6 flags from first principles on the 17 full-flow columns: keep-alive (duration > 60 s, mean IAT > 2 s,
  mean packet down < 200 B, up < 300 B), quick (duration < 2 s, <= 40 packets), bulk download (> 100 kB down,
  up/down bytes < 0.2), upload-heavy (up/down bytes > 1.2), streaming (> 30 s, > 50 kB/s down), bursty (>= 10 bursts).
- **clusters:** KMeans k = 8 on log1p + standardised full-flow columns, fitted without labels inside each training fold;
  features = distance to each centroid.
Both added to the input of `task1_model` (facebook rule kept).

## Results (cv_seed 2026)

| Variant | Macro F1 | Δ | W / L / T | Notes |
|---|---|---|---|---|
| rules | 0.806 | -0.000 | 10 / 7 / 33 | ignored by the model |
| clusters | 0.799 | -0.008 | 16 / 25 / 9 | facebook -0.030, instagram -0.022 |

Concept flags by app (train + validation):

| App (flows) | keep-alive | quick | bulk down | upload-heavy | streaming | bursty |
|---|---|---|---|---|---|---|
| facebook (11) | 3 | 2 | 0 | 8 | 0 | 3 |
| google (131) | 0 | 35 | 3 | 32 | 0 | 4 |
| instagram (19) | 0 | 1 | 5 | 7 | 4 | 14 |
| mozilla (41) | 3 | 16 | 0 | 7 | 0 | 1 |
| x (73) | 1 | 25 | 6 | 23 | 0 | 13 |
| youtube (55) | 0 | 24 | 0 | 21 | 0 | 4 |

## Interpretation

The kinds of run are shared across apps: every app makes quick exchanges, several send keep-alives and uploads. A
concept says *what the connection does*, not *who made it*, so it does not separate the apps that get confused (google
vs youtube make the same kinds of run). What separates apps is finer: infrastructure fingerprints within a kind (packet
sizes, ratios), which the trees already use. Attribute-style zero-shot learning needs app-specific attributes; this
feature set does not contain them.

## Decision

Reject both.
