---
title: '048: Facebook diagnostics: separability, merged Meta class, features, learning curve (measurement only)'
created: 2026-10-08
creator: sidhantbas
description: Is facebook separable from instagram, does merging them help, which features separate them, and does facebook F1 still rise with more training data?
experiment:
  id: 048
  tasks:
  - task1
  lever: diagnostic
  status: measured
  verdict: Facebook vs instagram separable beyond chance (F1 0.66, p 0.01); merged Meta class F1 0.88-0.91; facebook learning curve still rising
---
# 048: Facebook diagnostics: separability, merged Meta class, features, learning curve (measurement only)

- **Date:** 2026-10-08
- **Question:** Is facebook separable from instagram, does merging them help, which features separate them, and does facebook F1 still rise with more training data?
- **Status:** done
- **Script:** `src/exp048_facebook_diagnostics.py` (steps 1–4; about 3 min in total)
- **Runs:** none recorded: binary, 5-class and partial-data diagnostics do not fit `record_run`'s 6-class format. Numbers below are the script's output.
- **Reference:** Task 1 champion `20261001T173854Z_034_meta_gate` (production unchanged)

## Hypothesis

047 concluded scarcity. These four checks (requested by the user) test it from four sides: signal inside Meta (1),
the cost of the facebook/instagram split (2), where the signal lives (3), and whether more data still helps (4).

## Setup

Production's Task 1 features (17 full-flow + 17 prefix-5 columns). Default folds (5 × 10, cv_seed 2026) unless stated.
Details per step are in the script docstring.

## Results

**1. Facebook vs Instagram only (11 vs 19 flows, 50 folds, facebook = positive):**

| Model | Facebook F1 | Fold std | Pooled F1 | Shuffled labels mean (5th–95th) | p (100 shuffles) |
|---|---|---|---|---|---|
| Random forest | 0.662 | 0.277 | 0.690 | 0.341 (0.145–0.532) | 0.010 |
| Logistic regression | 0.657 | 0.265 | 0.684 | 0.348 (0.160–0.568) | 0.010 |

p = 0.010 is the smallest possible with 100 shuffles: none reached the real score.

**2. Merged Meta class (same 50 folds):**

| Setup | Classes | Macro F1 | Fold std | Meta F1 (std) | Δ macro vs production |
|---|---|---|---|---|---|
| Production | 6 | 0.8277 | 0.0659 | facebook 0.674 (0.259), instagram 0.741 (0.170) | — |
| (a) Production, merged afterwards | 5 | 0.8863 | 0.0396 | 0.881 (0.089) | +0.0586 (39/50 folds) |
| (b) Two clerks retrained on merged labels | 5 | 0.8933 | 0.0387 | 0.907 (0.087) | +0.0656 (40/50 folds) |

**3. Top 10 features, Facebook vs Instagram random forest:**

| Rank | Feature | Importance | Part of the flow |
|---|---|---|---|
| 1 | packet_count_up | 0.102 | full flow |
| 2 | packet_count_down | 0.090 | full flow |
| 3 | bytes_down | 0.082 | full flow |
| 4 | bytes_up | 0.067 | full flow |
| 5 | burst_count | 0.060 | full flow |
| 6 | std_iat | 0.054 | full flow |
| 7 | mean_iat | 0.049 | full flow |
| 8 | p5_std_pkt_size_down | 0.045 | opening (prefix-5) |
| 9 | std_pkt_size_down | 0.030 | full flow |
| 10 | mean_pkt_size_down | 0.030 | full flow |

9 of the top 10 are full-flow columns; full-flow columns hold 73% of the importance.

**4. Learning curve (production refitted on a stratified share of each training fold, 50 folds):**

| Training share | Facebook flows in training | Facebook F1 | Fold std | Macro F1 | Fold std |
|---|---|---|---|---|---|
| 20% | 2.0 | 0.174 | 0.238 | 0.598 | 0.072 |
| 40% | 3.8 | 0.398 | 0.315 | 0.708 | 0.086 |
| 60% | 5.4 | 0.513 | 0.326 | 0.753 | 0.077 |
| 80% | 7.0 | 0.575 | 0.260 | 0.792 | 0.067 |
| 100% | 8.8 | 0.674 | 0.259 | 0.828 | 0.066 |

The 100% row equals the champion run exactly (reproducibility check).

## Caveats

- Step 2's macro F1 averages 5 classes, so it is not directly comparable with the 6-class score, and "meta" is not a valid
  submission label. It measures what the facebook/instagram split costs, not something we can submit.
- Step 1 uses 30 flows; each test fold holds about 2 facebook flows, hence the fold std of 0.27.
- Step 3 is impurity importance on tiny training sets; it ranks columns but does not prove causation.
- Step 4 subsamples every class, so it shows the value of more data overall, with facebook the most sensitive class. It
  says nothing about whether *our own* captured flows would match the organisers' (gate 2 checks that).

## Decision

Measurement only; production unchanged.

- **Separable:** yes, beyond chance (p = 0.01), but only moderately (F1 0.66, std 0.27). The binary score is about
  production's facebook F1 (0.674), so production is already about as good inside Meta as a dedicated pair model.
- **Merging:** finding Meta is mostly solved (Meta F1 0.88–0.91), and splitting it costs about 0.06 macro F1. Not
  submittable: it locates the loss inside Meta.
- **Features:** the separating signal is the whole-flow behaviour (volume, bursts, timing), not the opening, as 022 and 028
  assumed when they let the whole-run expert decide facebook vs instagram.
- **Curve:** rising steeply with no plateau (+0.10 facebook F1 from 80% to 100%). More labelled flows should still pay off.

## Next

The curve supports the capture waypoint: each extra real facebook flow is still worth a lot. The capture should target
whole-flow behaviour (session length, bursts, idle periods), which is where the facebook/instagram signal lives.
