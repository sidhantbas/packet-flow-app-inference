---
title: '047: Is Task 1''s Facebook weakness a model problem or a data problem? (measurement only)'
created: 2026-10-08
creator: sidhantbas
description: Does a 9-item "evidence it's a model problem" checklist (supplied by the user) point to the model or to the data for Task 1 Facebook?
experiment:
  id: '047'
  tasks:
  - task1
  lever: diagnostic
  status: measured
  verdict: 'Model or data? 5 of 9 checklist items point to the data: verdict scarcity (11 facebook flows, 5 traffic types, no cluster of their own)'
---
# 047: Is Task 1's Facebook weakness a model problem or a data problem? (measurement only)

- **Date:** 2026-10-08
- **Question:** Does a 9-item "evidence it's a model problem" checklist (supplied by the user) point to the model or to the data for Task 1 Facebook?
- **Status:** done
- **Script:** `src/exp047_model_or_data.py` (items 1, 2, 5; items 3, 4, 6–9 from earlier runs)
- **Runs:** `results/20261008T005611Z_047_knn1`, `results/20261008T005611Z_047_knn5`, `results/20261008T005611Z_047_logreg` (probes, no reference)
- **Reference:** Task 1 champion `20261001T173854Z_034_meta_gate`

## Hypothesis

046 and the rejections of 044/045 led to the verdict "scarcity" (11 labelled facebook flows). The checklist tests the
alternative: that a better model could find a signal that is already in the data.

## Setup

- Item 1: production fitted on the 11 facebook flows + 40 random others, scored on those rows.
- Item 2: production on the first 2 repeats of the default folds (10 folds); facebook F1 on training vs held-out rows.
  Held-out mean 0.827 equals the champion run's first 10 folds exactly (reproducibility check).
- Item 5: 1-NN, 5-NN and balanced logistic regression on the 17 Task 1 columns (log1p + standardised), 50-fold CV; and
  the share of facebook among each facebook flow's 5 nearest flows (all 330).
- Items 3, 4, 6–9: earlier runs (006, 012, 016, 018, 024, 026, 034, 043, 004).

## Results

| # | Check | Measurement | Points to |
|---|---|---|---|
| 1 | Can it memorise facebook? | Recall 1.000, accuracy 1.000 on the 51 training rows | No pipeline bug |
| 2 | Train F1 low too? | Train 1.000 in all 10 folds; held-out 0.827 (std 0.158) on these folds, 0.674 on all 50 | Data (high train, low held-out) |
| 3 | Models disagree (> 0.15)? | Facebook F1: production 0.674, SoftVote 0.584, RF 0.486, fine-tuned TabPFN 0.394, TabPFN 0.380, 5-NN 0.314, 1-NN 0.257, logreg 0.204 | Model, but already used: production is the best of them |
| 4 | Simple beats fine-tuned? | RF 0.486 > fine-tuned TabPFN 0.394 (026) | Not relevant: production is not fine-tuned |
| 5 | Separable in feature space? | kNN facebook recall 0.24–0.26 (logreg 0.31); 5 of 11 facebook flows have no facebook flow among their 5 nearest; same-class share 0.15 vs google 0.69, mozilla 0.72, x 0.77, instagram 0.41 | Data: no facebook cluster |
| 6 | Hyperparameters move it (> 0.1)? | 018: max_features, LightGBM leaves, 1000 trees all within ±0.011 macro (at most ~0.07 facebook if it all came from facebook) | Data |
| 7 | Thresholds/weights fix recall? | Balanced weights needed (012: facebook −0.090 without); Meta gate raised recall 0.59 → 0.72 at an Instagram cost (034, adopted); further thresholds and multipliers inconclusive or harmful (043, 004) | The cheap calibration gain is already in production |
| 8 | Stable across seeds (std < 0.1)? | Facebook fold std 0.26 (production), 0.29–0.32 for the others; F1 = 0 in 3–17 of 50 folds; first 10 folds 0.827 vs all 50 0.674 | Data (scarcity) |
| 9 | Errors systematic? | Production: facebook → instagram 22, x 6, google 3 (71% instagram) | Model features, but 041: facebook and instagram share traffic types and openings |

## Caveats

- The probes use the 17 Task 1 columns; production also uses the 17 prefix columns.
- Item 9 is the one model-side signal. 041 shows the two apps share traffic types (slow trickle 3 facebook / 5 instagram)
  and exact openings, so new features from the same 17 + 17 columns have little to work with (021, 029, 030, 032–035).

## Decision

Measurement only. 5 of 9 items point to the data (1, 2, 5, 6, 8). Two point to the model but are already used up: the
best model is in production (3), and the cheap recall fixes are adopted (7). Item 4 does not apply. Item 9 points to
features that separate facebook from instagram, which the released columns do not seem to hold. Verdict:
**scarcity**. Facebook is 11 flows of 5 traffic types with no cluster of their own, and the held-out score swings by 0.15
between repeats.

## Next

More real facebook and instagram flows (captures, waypoint 2) are the only check that can move items 5, 8 and 9.
