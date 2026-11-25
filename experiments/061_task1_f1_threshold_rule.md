---
title: "061: Task 1 decision rule aimed at macro F1 (F/2 thresholds)"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for replacing the final argmax of the Task 1 production model with an F1-optimal threshold rule estimated by inner cross-validation.
source:
  - 004_ceilings_ensemble_thresholds.md
  - 033_behaviour_hybrid.md
  - 034_meta_gate.md
experiment:
  id: '061'
  tasks:
  - task1
  lever: decision
  status: rejected
  verdict: 'F1-optimal thresholds (t = F/2 and F/4 from inner CV): -0.0011 / +0.0008, inconclusive'
---

# 061: Task 1 decision rule aimed at macro F1 (F/2 thresholds)

**Status: done 2026-10-09. Protocol frozen (`515e7d4`) before any code change or run.**
**Verdict: both arms INCONCLUSIVE (T2 −0.0011, T4 +0.0008 with only 9 non-tied folds). No confirmation runs; no submission candidate.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "yes start the task 1 experiment".

## Question

Does choosing each flow's class by an F1-optimal threshold rule, instead of the most probable class, raise Task 1 macro F1?

## Why

Macro F1 weights every app equally, so a decision rule that favours hard, small classes can pay off; the 034 Meta gate
gained by this kind of reasoning. Lipton, Elkan and Naryanaswamy (2014, "Optimal thresholding of classifiers to maximize
F1 measure") show that for calibrated probabilities the F1-optimal threshold for a class is half the best F1 reachable
for that class (F*/2).

## Warning from earlier experiments

- 004: per-class probability multipliers **searched** by nested CV hurt in all four settings (down to −0.039).
- 033: a gated hybrid with two parameters chosen by inner CV picked up luck in about 60% of folds.

This experiment therefore searches nothing: the rule comes from theory, and its only inputs (per-class F1) are estimated
on inner folds of each training fold. Tree-ensemble probabilities are not calibrated, so the theory may not hold here.

## Frozen method

Production Task 1 (`models.task1_meta_gate`, features `cv.task1_with_prefix_features`), unchanged except one step: in
`MetaGate.predict`, `pred = cls[q.argmax(axis=1)]` becomes `pred = cls[(q − t).argmax(axis=1)]`. All later rules (whole-run
expert for facebook vs instagram, whole-run Meta override, kept facebook calls) are unchanged.

Thresholds per class, inside every outer training fold:

1. Inner 5-fold stratified CV (shuffle, random_state = model seed) of the unchanged production model on the training fold.
2. F_c = per-class F1 of the inner out-of-fold predictions (zero_division = 0).
3. Then fit production on the whole training fold.

| Arm | Threshold t_c |
|---|---|
| **T2** | F_c / 2 (the theoretical rule) |
| **T4** | F_c / 4 (half strength, fixed before running) |

## Frozen decision rules

- Each arm vs the Task 1 champion `20261001T173854Z_034_meta_gate` on cv_seed 2026, rule v2.
- Pass only with BETTER on 2026 **and** on 2027-2030, each against production re-run on the same seed (created here).
  Confirmation seeds only for an arm that passes on 2026. If both pass, the larger mean Δ over five seeds wins.
- A pass is a submission candidate (Task 1 changes, Task 2 stays), decided on CV before any new score is seen, with the
  user's approval.

## Boundaries

Train+validation only; held-out flows never enter threshold estimation. Production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `515e7d4`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `47b512f`; zero thresholds reproduce production exactly; example inner thresholds facebook 0.18, youtube 0.32, instagram 0.29, google 0.42, x 0.43, mozilla 0.45 |
| 17:22-17:24 | T2 and T4 on cv_seed 2026 (about 67 s each) | runs `20261009T172209Z_061_T2`, `20261009T172315Z_061_T4` |

No deviation from the frozen protocol. Both runs carry a `dirty-tree` warning for unrelated local files (`.gitignore`,
`.mission*`, (unrelated local folder)) and the not yet committed run folders; the runner itself was committed (`47b512f`) and runlog
records the code hashes. No arm was BETTER on 2026, so no confirmation seeds were run.

## Results (vs production Task 1, 0.8277)

| Arm | Macro F1 | Δ | Wins / losses / ties | Verdict |
|---|---:|---:|---|---|
| T2 (t = F/2) | 0.8266 | −0.0011 | 12 / 11 / 27 | INCONCLUSIVE |
| T4 (t = F/4) | 0.8285 | +0.0008 | 7 / 2 / 41 (9 non-tied, fewer than the 10 required) | INCONCLUSIVE |

| Class | T2 Δ F1 (wins/losses) | T4 Δ F1 (wins/losses) |
|---|---|---|
| facebook | −0.018 (0 / 7) | −0.004 (0 / 1) |
| instagram | −0.006 (0 / 4) | +0.000 |
| google | +0.000 (9 / 6) | +0.001 (3 / 1) |
| mozilla | +0.003 (4 / 1) | +0.001 (3 / 1) |
| x | +0.001 (6 / 4) | +0.002 (4 / 1) |
| youtube | **+0.013 (14 / 2)** | +0.005 (5 / 0) |

Confusion changes (50 folds summed), T2: youtube → google 91 → 82, youtube → x 12 → 7; google → facebook 10 → 15.
Flows fixed / broken (majority over repeats): T2 3 / 0, T4 2 / 0.

## Interpretation

- The rule moves the right flows in the non-Meta classes: youtube gains (+0.013, 14 wins / 2 losses in T2) because
  borderline youtube flows no longer fall to google. That is the intended macro-F1 effect.
- It costs facebook in T2 (−0.018, 0 / 7): the lower facebook threshold pulls a few google flows into facebook
  (10 → 15), and facebook precision drops. Net effect about zero.
- T4 changes too few predictions to judge (41 of 50 folds tied).
- Only the youtube part looks real. A youtube-only threshold would be a new idea chosen after seeing these results
  (post hoc); it would need its own frozen protocol and the full five-seed rule.

## Decision

No change; production Task 1 stays. No new submission from this experiment.
