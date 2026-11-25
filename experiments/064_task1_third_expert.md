---
title: "064: A third, different expert inside the Task 1 production model"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for adding a kNN and/or logistic-regression expert to the two-expert Meta-gate model, following the mechanism behind the 022 → 034 gain.
source:
  - 028_two_clerks.md
  - 034_meta_gate.md
  - 016_smooth_models.md
experiment:
  id: '064'
  tasks:
  - task1
  lever: model
  status: rejected
  verdict: 'Third expert (kNN, logistic regression, both): -0.006 / -0.015 / -0.019; weak learners on the same columns add noise'
---

# 064: A third, different expert inside the Task 1 production model

**Status: done 2026-10-09. Protocol frozen (`c83496e`) before any code change or run.**
**Verdict: KNN INCONCLUSIVE (−0.0060), LR WORSE (−0.0147), KL WORSE (−0.0193). Not adopted.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: find what increased the score and
follow that direction; prepare submissions for models that earn them.

## What drove the last increase (cross-validation only, no test labels)

| Step | Δ macro F1 | Per class |
|---|---:|---|
| 022 → 028: add the opening expert (prefix-5 view), averaged with the whole-flow expert | +0.0107 | google +0.019, mozilla +0.024, youtube +0.020 |
| 028 → 034: add the Meta gate | +0.0105 | facebook +0.082, instagram −0.029 |

Over 3,300 out-of-fold predictions 034 fixes 174 errors of 022 and breaks 121; most fixes are google ↔ youtube (87) and
google ↔ mozilla / x (55). Mechanism 1: a second, different view makes different mistakes, and averaging cancels some.
Mechanism 2: a protected route for facebook (Meta gate; whole-flow expert decides facebook vs instagram).

## Hypothesis

[016](016_smooth_models.md) found kNN and logistic regression lower the error on unfamiliar flows (0.415 → 0.398) but cost
facebook when mixed into the vote. Inside 034, the whole-flow expert decides every facebook/instagram call, so a third,
smooth expert can only act through the class probabilities, mostly between non-Meta apps, where mechanism 1 worked.

## Frozen arms

In `MetaGate.predict`, `p = (pw + po) / 2` becomes the mean of the expert probability vectors. Everything else unchanged
(gate, Meta re-weighting, whole-flow expert for facebook vs instagram, whole-flow Meta override, kept facebook calls).
Experts use all 34 production columns (`cv.task1_with_prefix_features`).

| Arm | Experts averaged |
|---|---|
| **KNN** | whole-flow, opening, `models.knn` (k = 7, distance-weighted, log1p + standardised) |
| **LR** | whole-flow, opening, `models.logreg` (balanced, log1p + standardised) |
| **KL** | whole-flow, opening, kNN, logistic regression |

## Frozen decision rules

- Each arm vs the Task 1 champion `20261001T173854Z_034_meta_gate` on cv_seed 2026 (rule v2). Arms passing 2026 are run on
  2027-2030 against the production references made in 062 (`20261009T172902Z_062_production_s2027`, `…173025Z…s2028`,
  `…173146Z…s2029`, `…173307Z…s2030`; same model, same folds).
- **Pass:** BETTER on 2026, 2027 and 2028 (rule v2) **and** Δ > 0 on 2029 and 2030. If several pass, the largest mean Δ over
  five seeds wins.
- A pass is a submission candidate (Task 1 changes, Task 2 stays): built and checked, then the user uploads it. Which file
  is our ranked entry is decided on CV before any new score is seen; scores never steer later experiments.

## Boundaries

Train+validation only. Production frozen at 5eb9a8b until the user approves a change.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `c83496e`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `55d3b9d`; without an extra expert it reproduces production; extra experts change 5-13 of 165 predictions, 0-2 touching Meta |
| 17:53 | KNN, LR, KL on cv_seed 2026 | runs `20261009T175302Z_064_KNN`, `20261009T175316Z_064_LR`, `20261009T175330Z_064_KL` |

No deviation from the frozen protocol. No arm passed on 2026, so no confirmation seeds were run.

## Results (vs production Task 1, 0.8277)

| Arm | Macro F1 | Δ | Wins / losses / ties | Verdict | facebook | google | mozilla | x | youtube |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|
| KNN | 0.8217 | −0.0060 | 15 / 30 / 5 | INCONCLUSIVE | −0.006 | −0.008 | +0.007 | −0.004 | −0.023 |
| LR | 0.8130 | −0.0147 | 9 / 40 / 1 | WORSE | −0.006 | −0.022 | −0.015 | −0.009 | −0.035 |
| KL | 0.8084 | −0.0193 | 10 / 39 / 1 | WORSE | −0.005 | −0.018 | −0.024 | −0.023 | −0.046 |

## Interpretation

- The Meta protection works as intended: facebook moves by at most −0.006 and instagram by ≤ 0.001.
- The losses are in the non-Meta apps, youtube most. kNN and logistic regression are weaker learners on the **same**
  columns, so they add noise to the average instead of a second opinion.
- Refined mechanism: the opening expert helped because it is a **strong learner on new information** (the first five
  packets), not merely a different model. A next expert should be a strong tree ensemble on information the whole-flow
  expert does not see directly.

## Decision

Not adopted; production unchanged.
