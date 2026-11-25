---
title: '036: Test-to-train twin rate, twin-aware CV, scoped H1 (Task 1)'
created: 2026-10-05
creator: sidhantbas
experiment:
  id: '036'
  tasks:
  - task1
  lever: evaluation
  status: adopted
  verdict: Test flows meet near-twins more often than CV held-out flows (18.5% vs 11.8%), so normal CV mirrors the test; twin-aware CV costs ~0.05 for all models; scoped H1 passes rule v2 on 6 split sets
  production: Scoped exact-opening override (via 089)
---
# 036: Test-to-train twin rate, twin-aware CV, scoped H1 (Task 1)

- **Date:** 2026-10-05
- **Command:** `.venv/bin/python src/exp036_twin_aware.py` (part 1 run inline; numbers below); scoped-H1 normal-CV confirmations on
  cv_seeds 2027/2028 run inline against the 034 runs at those seeds
- **Code:** `cv.evaluate(splits=, split_name=)` (custom folds), `models.ScopedH1`
- **Runs:** `results/*_036_*`

## Part 1: twin rate (17 whole-flow features, log1p + standardised over the 330 labelled flows)

| Nearest-neighbour distance | <= 0.02 | <= 0.05 | <= 0.1 | <= 0.2 | <= 0.47 | Median |
|---|---|---|---|---|---|---|
| Test flow -> nearest of the 330 labelled | 8.6% | **18.5%** | 21.0% | 30.9% | 51.9% | 0.37 |
| Labelled flow -> nearest other labelled | 9.1% | 13.0% | 20.3% | 28.8% | 50.0% | 0.47 |
| Normal CV: held-out -> nearest in training fold | 8.0% | 11.8% | 18.1% | 26.5% | 46.8% | 0.53 |

The test split is random from the same capture and the final model trains on all 330 flows, so test flows meet near-twins at
least as often as CV held-out flows. **Normal CV mirrors the test better; twin-aware CV is a pessimistic stress test.**
Threshold 0.05: near-twin distances cluster below ~0.04 and all 59 labelled pairs within 0.05 share their label.

## Part 2: twin-aware CV

Connected components within 0.05 -> 303 groups (16 groups with more than one flow, covering 43 flows; largest 8).
StratifiedGroupKFold(5, shuffle) x 10 repeats, seeds 2026/2027/2028.

| Model | Normal CV (seed 2026): macro / facebook | Twin-aware 2026 | Twin-aware 2027 | Twin-aware 2028 |
|---|---|---|---|---|
| 022 (whole-flow model) | 0.807 / 0.592 | 0.747 / 0.383 | 0.756 / 0.420 | 0.755 / 0.419 |
| 028 (+ opening expert) | 0.817 / 0.592 | 0.757 / 0.383 | 0.763 / 0.420 | 0.764 / 0.419 |
| 034 (+ Meta gate, production) | 0.828 / 0.674 | 0.766 / 0.431 | 0.770 / 0.462 | 0.775 / 0.485 |
| 034 + scoped H1 | 0.832 / 0.674 | 0.771 / 0.431 | 0.776 / 0.462 | 0.780 / 0.485 |

Paired, twin-aware: 028 vs 022 +0.008 to +0.010 (56-62% wins, as on normal folds); 034 vs 028 +0.007 to +0.011, facebook +0.048
to +0.066 (fewer winning folds than ties, as on normal folds). Both exceptions keep their gains; no exception stops helping.
All models lose ~0.05-0.06 macro and ~0.19 facebook F1 under twin-aware folds.

## Part 3: scoped H1

Exact-opening override only when neither the prediction nor the matched label is facebook/instagram. Rule v2 BETTER on every
split set: normal 2026 +0.0041 (14/0/36), 2027 +0.0047 (18/0/32), 2028 +0.0032 (11/0/39); twin-aware +0.0052 (19/0/31),
+0.0052 (19/0/31), +0.0055 (20/0/30). No fold lost. Gains: google, mozilla, youtube (+0.005 to +0.010), x small. With the full
model, it changes **0 of the 81 test predictions**.

## Decision (recommendation)

Keep 028 and 034 (gains survive twin-aware CV). Scoped H1 passes the acceptance rule outright; adopting it changes no current
test prediction.
