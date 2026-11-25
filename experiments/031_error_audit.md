---
title: '031: Out-of-fold error audit of the production pipelines'
created: 2026-10-01
creator: sidhantbas
description: Are the remaining held-out errors fixable with the supplied features, and does the evidence justify one
experiment:
  id: '031'
  tasks:
  - task1
  - task2
  lever: diagnostic
  status: measured
  verdict: 'Error audit: most google/youtube errors have a nearest training row of the predicted app; decision-rule headroom <= 3 (Task 1) and <= 6 (Task 2) errors in 3,300; no candidate'
---
# 031: Out-of-fold error audit of the production pipelines

- **Date:** 2026-10-01
- **Question:** Are the remaining held-out errors fixable with the supplied features, and does the evidence justify one
  targeted change?
- **Status:** done. **No candidate change was justified**; production models unchanged; no submission made.
- **Command:** `.venv/bin/python src/exp031_error_audit.py` (about 15 s on the M4 Pro)
- **Code:** `src/exp031_error_audit.py`
- **Outputs:** `results/20261001T171201Z_031_error_audit/` (`<task>/oof_predictions.csv`, confusion, pairs, margin, stability,
  duplicate and nearest-neighbour tables, `audit.json`, `manifest.json`, `checksums.json`)

## Step 1: baseline established from the code

| | Task 1 | Task 2 |
|---|---|---|
| Features (`cv.TASK_FEATURES`) | 17 full-flow columns (`flow_id`, `split`, `server_port`, `start_rel` dropped; transport udp = 1) + the same 17 from the Task 2 file of the same flow, prefixed `p5_` | the Task 2 file's 12 columns: as above minus duration and the four IAT columns |
| Model (`models.TASK_MODELS`) | `KeepClassBlend`: SoftVote A on the 17 columns, SoftVote B on all 34; argmax of mean(A, B); then every row A alone calls facebook becomes facebook | `PairSpecialist`: balanced SoftVote on 12 columns; rows it calls facebook/instagram are re-decided by an unweighted SoftVote fitted on facebook + instagram rows only |
| SoftVote | mean `predict_proba` of RandomForest (500), ExtraTrees (500), LightGBM (300), balanced class weights | same |
| Labels | strings; `classes_` sorted: facebook, google, instagram, mozilla, x, youtube | same |

- **Splits:** train + validation (330 flows), `RepeatedStratifiedKFold(5, 10, random_state=2026)`, model seed = fold index.
- **Metric:** the organisers' `_macro_f1` (imported from `data/official/evaluation_script/main.py`), per fold.
- **Acceptance rule (CLAUDE.md, rule v2):** mean paired Δ > 0, ≥ 70% of non-tied folds won, ≥ 10 non-tied folds, and
  a pass again on cv_seeds 2027 and 2028.
- **Saved predictions:** the champion runs store labels only (no probabilities), so held-out predictions were regenerated
  by refitting the production classes on each training fold. They reproduce the logged champion runs exactly
  (Task 1: `20260930T215907Z_022_blend_keep_fb`, Task 2: `20260930T173836Z_014_fi_same_nocw`; 0 mismatches in 3,300
  held-out labels each; official-metric fold scores equal the logged ones to 2e-16).
- **Prior reuse of these folds:** cv_seed 2026 selected every change since 004 (007, 014, 022 adopted); seeds 2027-2030 were
  used for confirmations. The pipeline is therefore tuned to this dataset; any nested estimate on the same folds does not
  remove that earlier reuse.
- **Grouping:** the data has no session or group identifier. Flows of one app session (84% of flows start within 5 s of
  another; within ±2 s, 67% of labelled neighbours share the app) can fall on both sides of a fold. CV estimates may be
  optimistic for that reason; recording time is excluded from predictors and was not used to build groups.

## Step 2: held-out errors (3,300 predictions per task; each flow 10 times, not independent)

| | Task 1 | Task 2 |
|---|---|---|
| Official macro F1 (fold mean ± std) | 0.8065 ± 0.0728 | 0.7544 ± 0.0669 |
| Pooled accuracy | 0.859 | 0.847 |
| Mistakes | 465 | 505 |
| Mistakes with the true class ranked 2nd | 266 (57.2%) | 306 (60.6%) |
| Mistakes at margin < 0.1 | 113 (24%) | 29 (6%) |

Per-class precision / recall (pooled):

| Class | Task 1 | Task 2 |
|---|---|---|
| facebook | 0.670 / 0.591 | 0.535 / 0.418 |
| google | 0.881 / 0.850 | 0.888 / 0.887 |
| instagram | 0.811 / 0.747 | 0.711 / 0.753 |
| mozilla | 0.853 / 0.934 | 0.892 / 0.810 |
| x | 0.894 / 0.971 | 0.856 / 0.958 |
| youtube | 0.808 / 0.767 | 0.800 / 0.751 |

Largest confused pairs (errors both ways): Task 1 google/youtube 175 (google→youtube 79, youtube→google 96), google/x 65,
google/mozilla 61, facebook/instagram 36. Task 2 google/youtube 189 (80 / 109), facebook/instagram 77 (fb→ig 50, ig→fb 27),
mozilla/x 66.

Error rate by margin (top-1 minus top-2 probability of the deciding vector; not calibrated):

| Margin | Task 1 rows / error rate | Task 2 rows / error rate |
|---|---|---|
| < 0.05 | 106 / 0.585 | 28 / 0.464 |
| 0.05-0.1 | 110 / 0.464 | 44 / 0.364 |
| 0.1-0.2 | 205 / 0.429 | 53 / 0.321 |
| 0.2-0.3 | 156 / 0.397 | 62 / 0.226 |
| 0.3-0.5 | 345 / 0.278 | 305 / 0.200 |
| ≥ 0.5 | 2378 / 0.045 | 2808 / 0.137 |

Task 2 makes 384 of its 505 mistakes at margin ≥ 0.5: confident errors. Deciding component: Task 1 facebook override 5
errors in 17 rows; Task 2 facebook/instagram stage 98 errors in 287 routed rows (34%), 21 of those rows truly another class.

Stability (flows by number of errors over 10 repeats): Task 1 has 28 flows wrong 10/10 (google 12, youtube 8, instagram 4,
facebook 2) and 16 wrong 5-9/10; Task 2 has 34 wrong 10/10 (google 9, youtube 9, mozilla 7, facebook 5, instagram 3).

## Step 3: errors versus feature overlap (dominant pair google/youtube in both tasks)

**Exact duplicates of the pipeline inputs (no rounding).** Empirical duplicate-conflict bound = sum of the largest class
count in each identical-vector group / rows. It is an accuracy bound for a deterministic classifier on that exact
representation of these 330 rows, not a population Bayes ceiling and not a macro-F1 bound.

| Representation | Distinct vectors / 330 | Conflict groups (rows) | Bound |
|---|---|---|---|
| Task 1 whole-flow 17 | 330 | 0 | 1.000 (vacuous) |
| Task 1 pipeline 34 | 330 | 0 | 1.000 (vacuous) |
| Task 1 opening 12 (inside the 34) | 123 | 7 (80) | 0.958 |
| Task 2 pipeline 12 | 123 | 7 (80) | 0.958; google/youtube rows only 0.984 |

Task 2 conflict groups: x 30 + mozilla 5 + youtube 2; youtube 24 + google 2; youtube 4 + google 1; instagram 4 + facebook 1;
instagram 2 + facebook 1; facebook 1 + instagram 1; instagram 1 + youtube 1.

**Nearest training neighbour** (log1p, scaler fitted on the training fold only; held-out row vs that fold's training rows):

| google/youtube mistakes | Task 1 (175) | Task 2 (189) |
|---|---|---|
| Exact duplicate of a training row with the other label | 0 | 30 |
| Nearest training row has the predicted (wrong) label | 131 | 138 |
| Nearest training row has the true label | 28 | 19 |
| Nearest training row is a third class | 16 | 2 |
| Median distance to nearest training row: mistakes vs correct | 1.51 vs 0.89 | 0.014 vs 0.000 |

So most errors are **nearby, non-identical vectors with the other label** (Task 1) or **exact or near-exact openings shared
across the pair** (Task 2). Task 1 mistakes also sit farther from any training row than correct predictions do.

**Opening vs whole flow (Task 1).** For the 324 held-out mistakes whose true class is google or youtube: whole-flow nearest
neighbour wrong and opening nearest neighbour right in 129; both wrong in 138; whole-flow right, opening wrong in 28;
both right in 29. The opening view separates a large share of these flows. That is exactly what experiment 028 ("two
clerks") exploited: +0.005 to +0.013 on five seeds, below the acceptance rule, because the opening expert breaks about as
many flows as it fixes.

## Step 4: one targeted change? No candidate justified

Upper bounds below are pooled over all held-out rows and chosen after seeing them, so they are optimistic; a nested
procedure can only do worse.

- **Task 1 decision-rule adjustment:** only 24% of mistakes are at margin < 0.1. Of the 72 rows whose top two are
  google/youtube with margin < 0.1, the true class is top-2 in 37 and top-1 in 34: flipping all of them would remove at
  most **3 errors in 3,300**.
- **Task 2 google/youtube:** 145 of 189 pair mistakes are at margin ≥ 0.5 and 30 are exact duplicates with the other label;
  flipping all narrow-margin pair rows would add 6 errors.
- **Task 2 facebook/instagram stage (inspected first, as required):** its facebook probability is bimodal. True facebook
  rows routed to the stage score < 0.3 (50 rows) or ≥ 0.7 (46 rows); none lie in 0.3-0.7. All 50 facebook→instagram
  errors are confident, so no threshold recovers them. Pooled thresholds: lowering below 0.5 only adds instagram→facebook
  errors (0.45: 34, 0.3: 62 vs 27 at 0.5); raising to 0.55-0.7 removes at most **6 errors in 3,300** (27 → 21), within
  noise of the selection itself.
- **Targeted tree on the opening view (Task 1):** the only separation the current model under-uses; already tested as 028
  and below the rule.

No intervention has headroom large enough for rule v2 to detect, so the nested evaluation was not run. Running it anyway
would be a search without a supported hypothesis.

## Verification

- Fold isolation: train and test disjoint in all 50 folds; each flow held out exactly once per repeat (asserted).
- Probability alignment: one class order across folds, equal to the sorted labels; rows sum to 1 (max error 4e-15);
  top-1 equals the pre-rule prediction (asserted).
- Final labels rebuilt from the components (override, stage) equal the pipeline's own predictions (asserted).
- Baseline reproduction: identical held-out labels to the logged champion runs (0 / 3,300 mismatches per task).
- Duplicate bounds and conflict-group counts recomputed independently (exact float keys, crosstab): identical.

## Uncertainty and limitations

- Repeated predictions of the same flow are not independent; counts over 3,300 rows overstate precision.
- No group labels: related flows cross folds; CV may be optimistic.
- The folds were used for model selection before this audit.
- Margins are not calibrated probabilities.
- The duplicate bound is empirical and vacuous for Task 1 (no duplicate vectors); it says nothing about near-duplicates.

## Recommendation

**No candidate was justified. Keep the current models.** The evidence: Task 1 errors are mostly confident-to-moderate
mistakes on vectors that lie next to training flows of the other app (131/175 google/youtube errors), with < 3 errors of
pooled headroom for any decision-rule change; Task 2 errors are mostly confident and partly exact duplicates (bound 0.958
accuracy), and its facebook/instagram stage fails on confidently-wrong facebook rows that no threshold can recover.
Unresolved: the opening view separates many Task 1 google/youtube flows (129), but the one way we found to use it (028)
falls short of the rule; with the supplied features, further gains need information the files do not contain.
