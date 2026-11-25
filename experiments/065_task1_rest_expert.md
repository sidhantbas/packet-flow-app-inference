---
title: "065: A rest-of-flow expert inside the Task 1 production model"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for adding a strong tree expert on packets 6..N (the part of each flow after the opening) to the two-expert Meta-gate model.
source:
  - 064_task1_third_expert.md
  - 030_rest_of_flow.md
  - 028_two_clerks.md
experiment:
  id: '065'
  tasks:
  - task1
  lever: model
  status: adopted
  verdict: 'Rest-of-flow expert as a third expert in the Meta-gate model: +0.0054 at seed 2026 (near-miss); later part of the 089 bundle'
  production: Rest-of-flow expert (via 089)
---

# 065: A rest-of-flow expert inside the Task 1 production model

**Status: done 2026-10-09. Protocol frozen (`f52f22c`) before any code change or run.**
**Verdict: R NEAR-MISS (+0.0054, 31/17), RT NEAR-MISS (+0.0019, 31/19). Neither passes rule v2 on 2026; by the frozen rule no confirmation runs. Followed up as a pre-registered five-seed check in [066](066_rest_expert_five_seeds.md).** Results are below.
Do not edit the frozen sections after execution starts. Follows the refined mechanism of [064](064_task1_third_expert.md).

## Hypothesis

The 028 opening expert helped (google +0.019, mozilla +0.024, youtube +0.020) because it is a strong learner on information
the whole-flow expert does not see directly. 064 showed weaker learners on the same columns hurt. The rest of the flow
(packets 6..N, experiment 030: exact statistics from the Task 1 and Task 2 rows of the same flow) is the remaining view of
that kind. 030 tested these columns only as extra features (−0.0095), never as a separate expert.

## Frozen arms

Production MetaGate; its experts and gate keep exactly the 34 production columns. One extra expert, a balanced
`models.SoftVote` (RF + ExtraTrees + LightGBM), on:

| Arm | Columns of the extra expert |
|---|---|
| **R** | the 11 rest-of-flow columns (`cv.rest_of_flow`) |
| **RT** | the 11 rest-of-flow columns + `transport` |

In `MetaGate.predict`, `p = (pw + po) / 2` becomes `(pw + po + pr) / 3`; all later rules unchanged.

## Frozen decision rules

Same as 064: vs the champion `20261001T173854Z_034_meta_gate` on 2026 (rule v2); arms passing 2026 run on 2027-2030 against
the 062 production references. **Pass:** BETTER on 2026, 2027, 2028 and Δ > 0 on 2029, 2030. A pass is a submission
candidate; the ranked file is chosen on CV before any new score is seen.

## Boundaries

Task 1 may read Task 2 files (022, disclosed). Train+validation only. Production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `f52f22c`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `478d019`; production experts keep the 34 production columns; a neutral rest expert reproduces production; R/RT change 9 of 165 predictions, 0-1 touching Meta |
| 17:55 | R and RT on cv_seed 2026 | runs `20261009T175524Z_065_R`, `20261009T175543Z_065_RT` |

No deviation from the frozen protocol. No arm passed rule v2 on 2026, so no confirmation seeds were run under this protocol.

## Results (vs production Task 1, 0.8277)

| Arm | Macro F1 | Δ | Wins / losses / ties | Verdict | facebook | instagram | google | mozilla | x | youtube |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|
| R | **0.8331** | **+0.0054** | 31 / 17 / 2 (65%) | NEAR-MISS | +0.000 | +0.002 | +0.002 | +0.010 | +0.009 | +0.009 |
| RT | 0.8296 | +0.0019 | 31 / 19 / 0 (62%) | NEAR-MISS | −0.004 | −0.001 | +0.001 | +0.007 | −0.004 | +0.013 |

## Interpretation

- R is the best Task 1 CV result of the day and follows the mechanism found in 064: a strong learner on information the
  other experts do not see directly. Every non-Meta app gains and facebook is unchanged.
- It misses rule v2 on 2026 (65% of non-tied folds, 70% needed). Adding `transport` (RT) weakens it.
- One seed cannot tell a consistent small gain from luck; a separate, pre-registered five-seed check follows (066).

## Decision

Not adopted under this protocol. Follow-up: [066](066_rest_expert_five_seeds.md).
