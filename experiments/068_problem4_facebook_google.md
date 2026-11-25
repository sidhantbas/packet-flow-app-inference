---
title: "068: Problem 4, facebook vs google (measurement only; closed)"
created: 2026-10-09
creator: sidhantbas
description: Where Task 1 production confuses facebook and google, which production stage makes those calls, and why the remaining errors are irreducible with the released features.
source:
  - 034_meta_gate.md
  - 067_meta_twins_threshold.md
experiment:
  id: 068
  tasks:
  - task1
  lever: diagnostic
  status: measured
  verdict: 'Facebook vs google: identical opening fingerprints, 3 vs 62 flows; closed as irreducible'
---

# 068: Problem 4, facebook vs google (measurement only; closed)

- **Date:** 2026-10-09 · **Status:** closed (irreducible with the released features) · **Script:** inline analysis, cross-validation only
- **Data:** production Task 1 out-of-fold predictions (`20261001T173854Z_034_meta_gate`) and a stage-by-stage re-run of the
  50 folds of cv_seed 2026 (same folds and seeds); training labels only.

## Size of the problem (production, 10 repeats)

| Error | Count | Flows |
|---|---:|---|
| google predicted facebook | 10 | google `flow_000120` (4), `flow_000559` (3), `flow_000239` (2), `flow_001398` (1) |
| facebook predicted google | 3 | facebook `flow_000809` (2), `flow_001168` (1) |

Upper bound of a perfect fix: facebook precision 0.67 → about 0.75, about +0.04 facebook F1, +0.007 macro F1 (≈ +0.35 points).

## Which production stage makes the wrong facebook calls (cv_seed 2026)

Wrong facebook calls by true class: instagram 26, google 10, youtube 2, x 1. For google: 6 come from the whole-flow Meta
override while the gate said "not Meta" (gate probability 0.02-0.31), 4 from the gate itself. The "keep facebook" rule adds
no facebook call of its own. Requiring gate agreement for the override removes about as many right as wrong facebook calls
at every cutoff (g ≥ 0.2: 4 wrong / 5 right; 0.3: 6 / 6; 0.4: 7 / 7; 0.5: 8 / 9), so it was not tested.

## Why the rest is irreducible

| Traffic type (041) | google flows | facebook flows |
|---|---:|---:|
| short QUIC fetch | 48 | 2 (`flow_000809`, `flow_001168`) |
| short TCP | 14 | 1 (`flow_000231`) |

Both facebook fetches open with 241 B + **1365 B**; google fetches use the same 1365-B first QUIC packet (`flow_000559`:
128 B + 1365 B; `flow_001398`: 1365 B + 1365 B). Facebook `flow_000231` (2 up ~133/147 B, 3 × 74 B down) matches google
`flow_000239` (2 × 148 B up, 3 × 74 B down).

Visibility check (user request; report only, no rule from 3 flows): the differences are visible in the first-5-packet
columns (with two up packets, mean and std give both sizes exactly). The facebook fetches sit at the edge of the 48 google
fetches (mean up size 803 B below 98% of them; std 562 above 98%); the only google flow beyond them is `flow_000559`, the
one confused with facebook. Facebook `flow_000231` sits at the low edge of the 14 google short-TCP flows (7th percentile on
up size and bytes). No google flow has identical up-packet sizes and counts.

## Verdict

Closed: identical fingerprints (same first QUIC packet, same TCP opening sizes), 3 facebook flows against 62 google flows of
the same types; the cutoff check fixes as many as it breaks. The remaining loss (≤ about 0.35 points) is treated as
irreducible with the released features. No rule is built from these flows.
