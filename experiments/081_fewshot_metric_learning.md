---
title: "081: Few-shot metric learning for facebook (NCA neighbours)"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for learning a distance (Neighbourhood Components Analysis) in which same-app flows are neighbours, as a few-shot method for the 11 facebook flows; diagnostic stage first, model test only if it passes.
source:
  - 079_pipeline_audit.md
  - 074_error_floor.md
  - 064_task1_third_expert.md
  - 034_meta_gate.md
experiment:
  id: 081
  tasks:
  - task1
  lever: imbalance
  status: rejected
  verdict: 'Few-shot metric learning (NCA + kNN) for facebook: facebook F1 0.24 vs 0.69; gate failed'
---

# 081: Few-shot metric learning for facebook

**Status: done 2026-10-09. Protocol frozen (`7a782c3`) before any code change or run.**
**Result: stage-1 gate fails (NCA-kNN facebook F1 0.242 vs production 0.693; 0 facebook flows fixed). Stage 2 not run.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "can we try few-shot learning for facebook".

## Why

Facebook is a few-shot class (11 labelled flows, about 9 per training fold). In the plain standardised feature space 9 of 11
facebook flows have mostly other apps as neighbours (079), and 100% of facebook errors have another app as nearest training
flow (074). Few-shot methods (prototypical / siamese networks) learn a distance in which a handful of same-class examples are
close. Tabular equivalent, small and nothing pretrained: Neighbourhood Components Analysis (NCA, Goldberger et al. 2004),
`sklearn.neighbors.NeighborhoodComponentsAnalysis`.

## Stage 1: diagnostic (cv_seed 2026, production folds)

Inside each training fold: the 34 production columns, log1p, standardised on the fold; NCA fitted on the fold
(`n_components` = all, `random_state` = fold index, `max_iter` = 200); then kNN (k = 3, distance-weighted) in the NCA space.
Same for kNN in the plain standardised space (control).

Measured: facebook precision / recall / F1 (pooled over the 50 folds) for NCA-kNN and plain kNN; facebook flows NCA-kNN gets
right that production gets wrong (majority over repeats); macro F1 of NCA-kNN alone.

**Gate to stage 2 (frozen):** NCA-kNN facebook F1 ≥ 0.60 **and** NCA-kNN gets at least 2 facebook flows right (majority over
repeats) that production gets wrong. Otherwise stop; record the result.

## Stage 2: facebook rescue (only if the gate passes)

Production prediction; a flow production does not call facebook becomes facebook when NCA-kNN (same construction, fitted on
the training fold) calls it facebook. Judged against production on cv_seeds 2026, 2027, 2028 (references: champion and the 062
production runs). **Pass:** rule v2 BETTER on all three. Evidence: facebook/instagram flow-level check. A pass is a submission
candidate (user approval; ranked file chosen on CV before any score).

## Boundaries

Train+validation only; no test features; no pretrained model; production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `7a782c3`, before any code change or run |
| 2026-10-09 | Stage 1 run inline (50 folds of cv_seed 2026, NCA fitted per training fold, 2 s) | per-prediction table kept in the session scratchpad |

No deviation from the frozen protocol.

## Stage 1 results (pooled over 50 folds)

| Method | Facebook precision | Facebook recall | Facebook F1 | Macro F1 |
|---|---:|---:|---:|---:|
| Production | 0.669 | 0.718 | 0.693 | 0.8323 |
| Plain kNN (k = 3, standardised log1p) | 0.500 | 0.164 | 0.247 | 0.6716 |
| NCA + kNN | 0.364 | 0.182 | 0.242 | 0.6555 |

Per facebook flow (share of repeats right, production / NCA-kNN): `flow_000024` 1.0 / 0.0, `flow_000231` 0.0 / 0.0,
`flow_000368` 0.5 / 0.2, `flow_000610` 1.0 / 0.0, `flow_000617` 0.8 / 0.2, `flow_000799` 0.9 / 0.0, `flow_000809` 0.8 / 0.8,
`flow_001145` 0.5 / 0.0, `flow_001168` 0.8 / 0.8, `flow_001324` 0.7 / 0.0, `flow_001331` 0.9 / 0.0. Facebook flows NCA-kNN gets
right and production wrong: **0**.

## Interpretation

The learned distance finds only the near-identical pair `flow_000809` / `flow_001168`, which production already handles. The
other nine facebook flows are about seven different traffic types (041), mostly one flow each; no single distance makes them
each other's neighbours without also pulling in google and instagram flows. Few-shot metric learning needs the few examples to
share a pattern, and these do not.

## Decision

Gate failed; stage 2 not run; no model change. Few-shot metric learning for facebook is closed.
