---
title: '035: Facebook/Instagram error checks, H1 test, twin-fold check (Task 1 production model)'
created: 2026-10-05
creator: sidhantbas
experiment:
  id: '035'
  tasks:
  - task1
  lever: hierarchy
  status: rejected
  verdict: 'H1 (trust exact opening twins): -0.0345; twin leakage: the near-identical facebook pair in one fold drops facebook F1 0.674 -> 0.521'
---
# 035: Facebook/Instagram error checks, H1 test, twin-fold check (Task 1 production model)

- **Date:** 2026-10-05
- **Command:** `.venv/bin/python src/exp035_h1_checks.py` (about 30 s)
- **Model:** production Task 1 (`models.task1_meta_gate`), default folds (cv_seed 2026); re-fitted held-out labels equal the
  logged champion `20261001T173854Z_034_meta_gate` (0 mismatches). p = gate-weighted probability of the final label before the
  Facebook rules, averaged over repeats; labels are majority votes over 10 repeats.

## 1. Facebook false positives and Instagram misses

| Flow | True | Predicted | Votes | p | Opening (pkts ↑/↓, bytes ↑/↓) | Nearest flow of the true class (whole-flow distance) |
|---|---|---|---|---|---|---|
| 000379 | instagram | facebook | 10/10 | 0.63 | 2/3, 1494/1657 | 000359 (2.23) |
| 001185 | instagram | facebook | 9/10 | 0.65 | 1/4, 1365/4594 | 000477 (5.28) |
| 000003 | instagram | youtube | 8/10 | 0.57 | 5/0, 6470/0 | 000477 (3.33) |
| 000216 | instagram | youtube | 8/10 | 0.63 | 2/3, 294/222 | 000477 (6.25) |

Only the two Instagram flows are called facebook by majority; 13 non-facebook flows are called facebook in at least one repeat
(39 predictions). Typical nearest-neighbour distance across all flows: 0.47.

## 2. Facebook <-> Instagram errors vs openings

| Flow | True -> predicted | Exact opening twin | Nearest opening, true class | Nearest opening, predicted class |
|---|---|---|---|---|
| 000231 | facebook -> instagram | none | 000024 (4.36) | 000216 (0.78) |
| 000379 | instagram -> facebook | none | 000604 (~0, 1 byte apart) | 000617 (~0, 1 byte apart) |
| 001145 | facebook -> instagram | none | 000799 (~0, 6 bytes apart) | 001185 (~0, 4 bytes apart) |
| 001185 | instagram -> facebook | none | 000359 (0.58) | 000799 (~0) |

None has an exact twin; where near matches exist they point to both apps equally (or to the wrong one). Flips from trusting
the opening: **0 of 4**.

## H1 simulation (rule fixed before running)

Inside each fold, a held-out flow whose exact opening occurs in the training fold with a single label takes that label.
60 of 3,300 predictions change: 27 fixed, 32 broken, 1 wrong -> wrong. Macro F1 0.8277 -> 0.7932 (**-0.0345**), 12 folds won,
23 lost, 15 tied. Main damage: 20 facebook -> instagram and 12 instagram -> facebook (shared Meta openings); gains: youtube 9,
google 13 (from mozilla/instagram/facebook/x). **H1 is rejected.**

## 3. Twin flows forced into the same fold

flow_000809 and flow_001168 (near-identical facebook fetches, whole-flow distance 0.01) placed in the same fold of every repeat
(swap with another facebook flow keeps stratification): facebook F1 **0.674 -> 0.521**, macro F1 0.8277 -> 0.8008. Both twins
then go to google (8/10 and 6/10) instead of facebook (8/10 each). Facebook's CV score is inflated by near-duplicate leakage.

## Conclusions

- H1 would cost about 1.7 Task 1 points (0.0345 x 50), not recover any.
- Cross-validation overstates Facebook (and the 028/034 Facebook gains may partly ride on twin leakage). Near-duplicate
  groups should be kept within one fold when estimating Facebook performance.
