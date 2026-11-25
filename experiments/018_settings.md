---
title: '018: Model settings (sweep; nested tuning not run)'
created: 2026-09-30
creator: sidhantbas
description: Do the main ensemble settings move the score enough to be worth tuning by nested CV?
experiment:
  id: 018
  tasks:
  - task1
  - task2
  lever: model
  status: rejected
  verdict: 'Ensemble settings sweep (max_features, LightGBM leaves, 1000 trees): all within +-0.011; 1000 trees failed confirmation'
---
# 018: Model settings (sweep; nested tuning not run)

- **Date:** 2026-09-30
- **Question:** Do the main ensemble settings move the score enough to be worth tuning by nested CV?
- **Status:** done
- **Script:** `src/exp018_settings.py` (sweep), `src/exp018_settings.py confirm` (trees1000 re-test)
- **Runs:** `results/*_018_*` (5 sweep + 4 confirmation)
- **Reference:** champions (task 2 keeps the fb/ig specialist on top)

## Part A: exploratory sweep (cv_seed 2026)

| Variant | Task 1 Δ | Task 2 Δ |
|---|---|---|
| mf05: RF + ExtraTrees max_features 0.5 | +0.001 | −0.003 |
| mf10: max_features 1.0 | −0.007 | −0.004 |
| lgb_small: LightGBM 7 leaves, min_child 10 | −0.006 | +0.001 |
| lgb_deep: LightGBM 31 leaves, min_child 2 | −0.011 | −0.002 |
| trees1000: 1000 trees instead of 500 | +0.002 (7/3/40, BETTER) | −0.000 |

Everything is within ±0.011. The settings are not a lever here.

## trees1000 confirmation (task 1)

| cv_seed | Δ | W / L / T |
|---|---|---|
| 2026 | +0.002 | 7 / 3 / 40 |
| 2027 | −0.002 | 4 / 4 / 42 |
| 2028 | −0.001 | 3 / 4 / 43 |

It fails confirmation. The first result was Monte-Carlo noise from the trees; this is what the confirmation step is for.

## Part B: nested tuning

Not run: the sweep shows no setting with a clear effect, so nested tuning would only fit noise.

## Decision

Nothing adopted. Keep the current settings.
