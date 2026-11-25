---
title: '037: Nearest-twin override (Task 1)'
created: 2026-10-05
creator: sidhantbas
experiment:
  id: '037'
  tasks:
  - task1
  lever: hierarchy
  status: rejected
  verdict: 'Nearest-twin override: production already predicts every near-twin''s label; 0 test changes; dropped'
---
# 037: Nearest-twin override (Task 1)

- **Date:** 2026-10-05
- **Command:** `.venv/bin/python src/exp037_twin_override.py` (post-processing of the logged production labels; folds regenerated
  and checked against the logs). Part 3 at t = 0.08 and the test counts were run inline with the same functions.
- **Rule:** if a held-out flow has a training flow within t (17 whole-flow features, log1p, standardised on the training flows
  only), take the nearest such flow's label.
- **Runs:** `results/*_037_twin_t*` (cv_seed 2026)
- **Bug note:** the first run listed 8 test twins because part 1 used a mis-parenthesised (L1-like) distance; fixed to Euclidean.
  The CV part always used the Euclidean distance. Corrected list below.

## 1. Test flows with a labelled flow within 0.05 (training = all 330 labelled)

15 test flows: 000218, 000219, 000251, 000262, 000268, 000373 (x twins); 000222 (instagram); 000382, 000864, 000887 (youtube);
000384, 000899, 001345 (google); 000679, 000688 (mozilla). **Production agrees with the twin's label in all 15.** No test flow has
twins of different labels within 0.05.

## 2. Normal CV, cv_seed 2026 (vs production)

| t | Changed | Fixed | Broken | Macro F1 | Δ | W / L / T |
|---|---|---|---|---|---|---|
| 0.03 | 0 | 0 | 0 | 0.8277 | 0 | 0 / 0 / 50 |
| 0.05 | 0 | 0 | 0 | 0.8277 | 0 | 0 / 0 / 50 |
| 0.08 | 5 | 5 | 0 | 0.8287 | +0.0010 | 5 / 0 / 45 |
| 0.12 | 5 | 5 | 0 | 0.8287 | +0.0010 | 5 / 0 / 45 |

No threshold passes rule v2 (fewer than 10 non-tied folds), so no threshold is chosen and no confirmation is run. Within 0.05 the
production model already predicts every twin's label; the 5 changes at 0.08 are a single google flow that production calls youtube, fixed in 5 of its 10 repeats.

## 3. Interaction (t = 0.08, cv_seed 2026, illustration only)

Twin overrides touch facebook/instagram 0 times (Meta gate decisions untouched). Twin rule and scoped H1 change disjoint rows and
give identical predictions in either order: scoped H1 alone +0.0041 (17 fixed, 0 broken, 14/0/36); both +0.0051 (22 fixed,
0 broken, 16/0/34). Order does not matter; if both were used, the twin rule last is the safer default.

## Test impact and decision

Test predictions changed: 0 at 0.05, 0 at 0.08, 0 at 0.12. **Drop**: the production model already agrees with every near-twin,
so the rule adds nothing on test and does not pass the acceptance rule in CV.
