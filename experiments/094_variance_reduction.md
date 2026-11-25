---
title: "094: Seed-bagging the whole pipeline and nested feature selection (variance reduction)"
created: 2026-10-10
creator: sidhantbas
description: Frozen protocol and results for the last two untried model-side variance-reduction levers, judged on never-used cv_seeds 2041-2045.
source:
  - 018_settings.md
  - 089_near_miss_bundle.md
  - 093_data_limited_analysis.md
experiment:
  id: 094
  tasks:
  - task1
  - task2
  lever: model
  status: rejected
  verdict: 'Seed-bagging the whole pipeline: no change (44-46 of 50 folds identical); nested feature selection -0.016'
---

# 094: Seed-bagging and nested feature selection

**Status: done 2026-10-10. Protocol frozen (`6113194`) before any code change or run.**
**Verdict: both rejected at seed 2041. Seed-bagging changes almost nothing (44-46 of 50 folds tied); nested feature selection −0.016 (instagram −0.035, facebook −0.029).** Results are below.
Do not edit the frozen sections after execution starts. User 2026-10-10: "yes run both on the fresh seeds". No submissions are
left: CV evidence only.

## Frozen arms

- **SB1, SB2 (seed-bagging, Task 1 and Task 2):** five copies of the production model (Task 1 `models.task1_bundle`, Task 2
  `models.task2_model`) with model seeds $s, s+1000, s+2000, s+3000, s+4000$ ($s$ = the fold's model seed), all trained on the same
  training fold; the final label is the majority vote of the five labels, ties going to the seed-$s$ model's label.
- **FS1 (nested feature selection, Task 1):** inside each training fold, the importance of each of the 34 production columns is
  measured by an inner `StratifiedKFold(5, shuffle, random_state = model seed)`: a balanced `SoftVote` per inner fold, each column
  permuted once in the inner held-out rows (seed = inner fold index), drop in accuracy averaged over the inner folds. Columns with
  mean drop ≤ 0 are neutralised: the production model derives its rest-of-flow columns from the raw columns as usual, then the
  neutralised columns are set to 0 for training and prediction (trees cannot split on a constant column, so this equals removal
  without breaking the derived columns).

## Decision rule

- cv_seeds **2041-2045** (never used; checked in `results/index.jsonl`), default CV (5 × 10) through `runlog`; production
  references run first on each seed.
- Stage 1: seed 2041; an arm continues only if Δ > 0. Pass: rule v2 BETTER on all five seeds. Report the columns neutralised on
  the full train + validation set (description).
- A pass can only inform the report or a future round; adoption needs the user's approval.

## Boundaries

Train + validation only; Task 2 reads only Task 2 files; nothing pretrained; no outside data.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-10 | Protocol frozen and committed | before any code change or run; cv_seeds 2041-2045 unused |
| 2026-10-10 | Runner committed; description | FS1 on all train + validation would neutralise 8 of 34 columns: `packet_count_up`, `min_iat`, `p5_transport`, `p5_packet_count_up`, `p5_packet_count_down`, `p5_mean_iat`, `p5_burst_count`, `p5_up_down_packet_ratio` |
| 16:00-16:05 | Production references and SB1, SB2, FS1 on cv_seed 2041 | refs `20261010T160006Z_094_T1_production_s2041`, `20261010T160013Z_094_T2_production_s2041`; Δ ≤ 0 for every arm, so no further seeds |

No deviation from the frozen protocol.

## Results (cv_seed 2041, vs production)

| Arm | Δ macro F1 | W / L / T | Verdict | Largest per-class changes |
|---|---:|---|---|---|
| SB1 seed-bagging, Task 1 | −0.0004 | 2 / 4 / 44 | INCONCLUSIVE | facebook −0.004, mozilla +0.002 |
| SB2 seed-bagging, Task 2 | −0.0012 | 2 / 2 / 46 | INCONCLUSIVE | instagram −0.008 |
| FS1 nested feature selection, Task 1 | −0.0162 | 16 / 23 / 11 | INCONCLUSIVE (negative) | instagram −0.035, facebook −0.029, mozilla −0.011 |

## Verdict

**Both rejected at stage 1.**

- **Seed-bagging changes almost nothing:** 44-46 of 50 folds are identical. The production pipeline's predictions barely depend
  on the model seed, so model-side seed variance is already negligible; there is nothing for bagging to average away.
- **Feature selection hurts**, most on the rare classes: columns that look useless to a single inner SoftVote (opening packet
  counts and shape, which define the opening experts' views and the exact-opening rule) carry information the production
  pipeline uses for facebook and instagram.
- Together with 093: the remaining error is not learner instability but estimation variance from too few examples (learning
  curve still rising) plus identical inputs. Model-side variance reduction is exhausted.
