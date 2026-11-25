---
title: "092: Cleaning the training pile (confident learning, Meta rows protected)"
created: 2026-10-10
creator: sidhantbas
description: Frozen protocol and results for removing confusing non-Meta training rows, flagged by the confident-learning rule on inner out-of-fold probabilities, before training the production models; judged on never-used cv_seeds 2036-2040.
source:
  - 089_near_miss_bundle.md
  - 079_pipeline_audit.md
experiment:
  id: 092
  tasks:
  - task1
  - task2
  lever: data
  status: rejected
  verdict: 'Confident-learning cleaning of training folds: -0.027 / -0.038; the removed rows are hard real examples'
---

# 092: Cleaning the training pile

**Status: done 2026-10-10. Protocol frozen (`155337e`) before any code change or run.**
**Verdict: rejected at seed 2036 (Task 1 −0.0265, Task 2 −0.0382, both WORSE): the flagged rows are hard real examples, not label noise.** Results are below.
Do not edit the frozen sections after execution starts. User 2026-10-10: "ok" (to the confident-learning idea; Charles's afe-002
found that removing one confusing facebook TCP row helped on train only). No submissions are left: CV evidence only.

## Frozen rule (inside every outer training fold only; held-out flows are never cleaned)

1. Inner out-of-fold probabilities for the training rows: balanced `SoftVote` (seed = model seed), `StratifiedKFold(5, shuffle,
   random_state = model seed)`, on the task's production columns (Task 1: 34; Task 2: 12).
2. Per class $j$: threshold $t_j$ = mean inner probability of class $j$ over rows labelled $j$ (confident learning, Northcutt et
   al. 2021).
3. A row labelled $i$ is **flagged** if $p_i < t_i$ and some other class $k$ has $p_k \ge t_k$.
4. Flagged rows are removed, **except rows labelled facebook or instagram** (never removed). Nothing tuned.
5. The production model is trained on the cleaned fold: Task 1 `models.task1_bundle` (arm C1), Task 2 `models.task2_model` (C2).

## Decision rule

- cv_seeds **2036-2040** (never used; checked in `results/index.jsonl`); production references run first on each seed.
- Stage 1: seed 2036; continue only if Δ > 0. Pass: rule v2 BETTER on all five seeds vs production.
- Report the rows removed per class (on the full train + validation set, for description).
- A pass can only change the report or a future round (no submissions left); adoption needs the user's approval.

## Boundaries

Train + validation only; nothing pretrained; no outside data; Task 2 reads only Task 2 files.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-10 | Protocol frozen and committed | before any code change or run; cv_seeds 2036-2040 unused |
| 2026-10-10 | Runner committed; description on full train + validation | Task 1 flags 13 of 330 (google 9, youtube 4); Task 2 flags 18 (google 10, youtube 6, mozilla 1, x 1) |
| 01:11-01:13 | Production references and C1, C2 on cv_seed 2036 | `20261010T011156Z_092_T1_production_s2036`, `20261010T011238Z_092_T2_production_s2036` and the C1/C2 runs; Δ < 0 in both, so no further seeds |
| after the runs | Sanity check (first 3 folds per task) | 10-25 rows removed per training fold, almost all google/youtube; rows and labels aligned: the result is not a bug |

No deviation from the frozen protocol.

## Results (cv_seed 2036, vs production)

| Arm | Δ macro F1 | W / L / T | Verdict | facebook | google | instagram | mozilla | x | youtube | Flows fixed / broken |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| C1 (Task 1) | −0.0265 | 8 / 39 / 3 | WORSE | −0.025 | −0.034 | 0.000 | −0.053 | −0.006 | −0.041 | 0 / 12 |
| C2 (Task 2) | −0.0382 | 3 / 47 / 0 | WORSE | −0.009 | −0.044 | −0.012 | −0.053 | −0.032 | −0.078 | 3 / 19 |

## Verdict

**Rejected at stage 1.** The flagged rows are not mislabelled: they are real google and youtube flows that sit in the border
regions next to other apps. Removing them leaves the clerk with no examples of those regions, so held-out border flows go wrong
(google, youtube and mozilla all fall). Our training labels behave as clean labels with hard examples, consistent with 079's label
check. Charles's single-row result (afe-002) does not generalise into a cleaning rule.
