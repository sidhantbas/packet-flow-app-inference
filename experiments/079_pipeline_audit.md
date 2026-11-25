---
title: "079: Pipeline audit: where points are lost, and which losses are fixable (diagnostic only)"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Eight pre-declared checks on the production models' out-of-fold predictions (point map, irreducible floor, fixability, learning curves, CV reliability, label consistency, Task 1 vs Task 2, ceiling).
source:
  - 074_error_floor.md
  - 040_test_noise.md
  - 038_unused_information.md
experiment:
  id: 079
  tasks:
  - task1
  - task2
  lever: diagnostic
  status: measured
  verdict: 'Pipeline audit: Task 2''s loss is mostly irreducible (floor 9.19 of 11.38 points); Task 1 is data-starved; all model-limited cells together are about +1 CV point'
---

# 079: Pipeline audit (diagnostic only)

**Status: done 2026-10-09. Definitions frozen (`d7ac086`) before any run.** Results are below.
User brief 2026-10-09: diagnostic only; no new models or candidates; no leaderboard input; no start-time, order, flow_id,
DNS, SNI or IP signals; no Task 1 features in Task 2; at least 3 seeds; flag any check that needs unlabelled test features.

## Data

Production out-of-fold predictions. Task 1 (`models.task1_meta_gate`): cv_seeds 2026-2030 (`20261001T173854Z_034_meta_gate`,
`20261009T172902Z_062_production_s2027`, `…173025Z…s2028`, `…173146Z…s2029`, `…173307Z…s2030`). Task 2 (`models.task2_model`):
cv_seeds 2026-2028 (`20260930T173836Z_014_fi_same_nocw`, `…173928Z…_s2027`, `…173952Z…_s2028`; no production runs exist for
2029-2030). Train+validation labels only. **No check uses test features**, so none needs a rules check.

## Pre-declared definitions

- **Feature space for distances:** Task 1: the 16 gate-2 columns (`capture_checks.PROX_COLS`); Task 2: the 12 production
  no-timing columns (`cv.no_timing_features`). log1p, standardised on all 330 labelled flows, Euclidean.
- **Near-identical:** distance ≤ 0.10; exact duplicate: distance 0. Groups = connected components at ≤ 0.10. A group is
  **mixed** if it holds more than one label. Floor: the best any classifier can do on a mixed group is its majority label,
  so its minority members are counted as unavoidable errors.
- **Point map:** for each directional off-diagonal cell (true a → predicted b), macro F1 (mean over repeats, then seeds)
  if only that cell's errors were corrected, minus the actual; × 50. Shares are of the task's total points lost; cells
  overlap, so shares do not add to 100%.
- **Separability sanity check** (step 3): for each top pair, binary 5-fold stratified CV (cv_seed 2026) on the two classes'
  flows only, kNN (k = 5, distance-weighted, log1p + standardised) and the balanced SoftVote; ROC AUC. Separable if
  SoftVote AUC ≥ 0.90.
- **Categories** (step 3): irreducible if ≥ 50% of the cell's errors fall on flows in mixed near-identical groups;
  data-starved if either class's F1 rises by ≥ 0.03 from 75% to 100% training size (step 4); model-limited if separable and
  neither of the above; otherwise "can't tell".
- **Learning curves:** production model, cv_seed 2026 folds; each training fold subsampled per class to 25 / 50 / 75 / 100%
  (at least one flow per class; subsample seed = fold index); pooled per-class F1 over the 50 folds.
- **CV reliability:** per-class F1 spread across folds and across seeds; smallest true per-fold gain rule v2 can reliably
  see, approximated as δ ≈ 0.52 σ (70% expected wins under normal paired noise σ), σ = paired fold-level SD observed in the
  day's production comparisons (macro) and per-class fold SD (per class). Labelled as an approximation.
- **Label consistency:** flows whose 5 nearest labelled neighbours carry a different label in at least 4 of 5 cases.
- **Task 1 vs Task 2:** same seeds (2026-2028); flows Task 2 gets right and Task 1 gets wrong, per class.
- **Ceiling:** CV macro F1 if (a) every error not on a mixed near-identical flow were fixed, and (b) only model-limited cells
  were fixed; in points, next to 84.62, 87.77 and 93.19 (leaderboard numbers shown for comparison only, not used to decide).

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Definitions frozen and committed | `d7ac086`, before any run |
| 2026-10-09 | Script `src/exp079_pipeline_audit.py` (`0523c1e`); step-6 label array fix (next commit) | tables in `experiments/079_evidence/` |

No deviation from the frozen definitions. No check used test features; no leaderboard number was used to decide anything.

## 1. Point map (CV, × 50)

Task 1 (5 seeds): macro F1 0.8273 = 41.37 points; 8.63 lost. Top cells: facebook → instagram 1.50 (17%), instagram → facebook
1.36 (16%), youtube → google 1.07 (12%), google → youtube 0.65 (7%), instagram → youtube 0.45, google → x 0.40,
google → facebook 0.40, facebook → x 0.39, google → instagram 0.38, mozilla → google 0.31.
Task 2 (3 seeds): 0.7724 = 38.62 points; 11.38 lost. Top: facebook → instagram 3.54 (31%), youtube → google 1.25 (11%),
instagram → facebook 1.21 (11%), facebook → x 0.88, mozilla → x 0.86, google → youtube 0.77, instagram → youtube 0.45,
mozilla → google 0.36, google → mozilla 0.33, youtube → x 0.29.
**Reading:** facebook ↔ instagram alone is a third of Task 1's loss and 42% of Task 2's; youtube ↔ google is next (19-18%).

## 2. Irreducible error (near-identical ≤ 0.10, majority label)

Task 1: 22 near-identical groups, **none mixed**: no Task 1 error comes from flows that are near-identical with different
labels; the strict floor is 0 points. Task 2: 26 groups, **17 mixed** (20 with exact duplicates), 280 flows in mixed groups, 80
unavoidable minority flows; **floor: 9.19 points lost** (best possible Task 2 CV macro F1 0.816 = 40.81 points); 78% of Task 2
errors fall on mixed groups.
**Reading:** Task 2's loss is mostly irreducible (identical first five packets, different labels). Task 1's loss is not of this
kind; it comes from overlap at larger distances (074: 65% of errors have another app as nearest neighbour).

## 3. Fixable vs unfixable (top 10 cells)

| Task | Cell | Points | On mixed groups | AUC kNN / SoftVote | F1 rise 75 → 100% | Category |
|---|---|---:|---:|---|---|---|
| 1 | facebook → instagram | 1.50 | 0% | 0.78 / 0.76 | fb +0.186, ig +0.068 | data-starved |
| 1 | instagram → facebook | 1.36 | 0% | 0.78 / 0.76 | same | data-starved |
| 1 | youtube → google | 1.07 | 0% | 0.79 / 0.94 | yt +0.038, go +0.024 | data-starved |
| 1 | google → youtube | 0.65 | 0% | 0.79 / 0.94 | same | data-starved |
| 1 | instagram → youtube | 0.45 | 0% | 0.90 / 0.96 | ig +0.068 | data-starved |
| 1 | google → x | 0.40 | 0% | 0.96 / 0.99 | x +0.038 | data-starved |
| 1 | google → facebook | 0.40 | 0% | 0.83 / 0.99 | fb +0.186 | data-starved |
| 1 | facebook → x | 0.39 | 0% | 0.95 / 0.98 | fb +0.186 | data-starved |
| 1 | google → instagram | 0.38 | 0% | 0.89 / 0.99 | ig +0.068 | data-starved |
| 1 | mozilla → google | 0.31 | 0% | 0.97 / 0.99 | mo +0.020, go +0.024 | model-limited |
| 2 | facebook → instagram | 3.54 | 92% | 0.61 / 0.57 | fb +0.095 | irreducible |
| 2 | youtube → google | 1.25 | 84% | 0.94 / 0.92 | +0.024 | irreducible |
| 2 | instagram → facebook | 1.21 | 100% | 0.61 / 0.57 | | irreducible |
| 2 | facebook → x | 0.88 | 0% | 0.95 / 0.98 | fb +0.095 | data-starved |
| 2 | mozilla → x | 0.86 | 96% | 0.93 / 0.95 | | irreducible |
| 2 | google → youtube | 0.77 | 100% | 0.94 / 0.92 | | irreducible |
| 2 | instagram → youtube | 0.45 | 57% | 0.93 / 0.97 | | irreducible |
| 2 | mozilla → google | 0.36 | 41% | 0.98 / 0.99 | +0.019 / +0.024 | model-limited |
| 2 | google → mozilla | 0.33 | 33% | 0.98 / 0.99 | | model-limited |
| 2 | youtube → x | 0.29 | 100% | 0.97 / 0.97 | | irreducible |

Caveat (frozen order): a cell is called data-starved before model-limited, so separable pairs whose classes still rise are
listed as data-starved. Pair AUCs are for the two classes in isolation and overstate what a six-class model can achieve.

## 4. Per-class learning curves (pooled F1, cv_seed 2026)

| Task | Fraction | facebook | google | instagram | mozilla | x | youtube | macro |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 25% | 0.161 | 0.776 | 0.615 | 0.745 | 0.784 | 0.631 | 0.619 |
| 1 | 50% | 0.437 | 0.827 | 0.672 | 0.823 | 0.858 | 0.723 | 0.723 |
| 1 | 75% | 0.507 | 0.865 | 0.677 | 0.899 | 0.898 | 0.771 | 0.769 |
| 1 | 100% | 0.693 | 0.889 | 0.745 | 0.919 | 0.936 | 0.809 | 0.832 |
| 2 | 25% | 0.099 | 0.772 | 0.658 | 0.716 | 0.774 | 0.630 | 0.608 |
| 2 | 50% | 0.324 | 0.823 | 0.705 | 0.777 | 0.841 | 0.702 | 0.695 |
| 2 | 75% | 0.374 | 0.864 | 0.713 | 0.830 | 0.874 | 0.751 | 0.734 |
| 2 | 100% | 0.469 | 0.888 | 0.731 | 0.849 | 0.904 | 0.775 | 0.769 |

**Reading:** no class has plateaued in Task 1; facebook rises most (+0.186 from 75% to 100%), then instagram (+0.068); google
and mozilla flatten (+0.02). Task 2 rises less (facebook +0.095), consistent with its large irreducible part.

## 5. CV reliability (Task 1, 5 seeds × 50 folds)

| Class | Flows per fold | Fold SD of F1 | Seed means (min-max) | Per-fold gain rule v2 can reliably see (≈ 0.52 SD) |
|---|---:|---:|---|---:|
| facebook | 2.2 | 0.264 | 0.558-0.674 | ≈ 0.14 |
| instagram | 3.8 | 0.153 | 0.728-0.754 | ≈ 0.08 |
| youtube | 11.0 | 0.099 | 0.805-0.816 | ≈ 0.05 |
| mozilla | 8.2 | 0.083 | 0.902-0.926 | ≈ 0.04 |
| x | 14.6 | 0.052 | 0.930-0.939 | ≈ 0.03 |
| google | 26.2 | 0.043 | 0.888-0.894 | ≈ 0.02 |

Macro: paired fold SD of the day's 57 production comparisons, median 0.019 (0.002-0.073) → rule v2 reliably sees macro gains of
about **+0.010** or more. **Reading:** the day's candidates (+0.003 to +0.007) sit below that line, which explains the many near
misses; a facebook-only change must move facebook F1 by about 0.14 per fold to be seen.

## 6. Label consistency (≥ 4 of 5 nearest neighbours carry another label)

Task 1: 69 flows (21%): google 27, youtube 12, instagram 9, **facebook 9 of 11**, mozilla 7, x 5. Task 2: 58 flows: youtube 18,
google 15, facebook 10, mozilla 9, x 4, instagram 2. Full lists with features: `step6_label_consistency_<task>.csv`. Nothing
relabelled. **Reading:** 9 of 11 facebook flows sit among other apps' flows in Task 1; whether this is label noise or real overlap
cannot be told from the features.

## 7. Task 1 vs Task 2 (seeds 2026-2028)

CV: Task 1 0.8248 > Task 2 0.7724. Over 30 repeats: Task 2 right / Task 1 wrong 168 predictions (google 88, instagram 36,
youtube 30, facebook 13); Task 1 right / Task 2 wrong 395; both wrong 1,082. An oracle that always picks the right one of the
two (not usable) would reach 0.8545. **Reading:** Task 1 is not throwing away the first five packets (it already uses them, 022,
028); the test-set gap quoted in the brief (Task 2 0.905 vs Task 1 0.787) is not reproduced in CV, where Task 1 is clearly
better. Adding Task 2 outputs to Task 1 hurt before (038).

## 8. Ceiling (CV points)

| Task | CV now | Fix model-limited cells only | Theoretical best |
|---|---:|---:|---|
| Task 1 | 41.37 | 41.67 (+0.30) | no near-identical floor (50 by definition); the rest needs more same-distribution data |
| Task 2 | 38.62 | 39.31 (+0.69) | 40.81 (floor from step 2) |
| Total | 79.99 | 80.98 (+0.99) | — |

Leaderboard for comparison only: 84.62 (old), 87.77 (current), leader 93.19. The leaderboard numbers are above CV mainly because
Task 2 scored 0.905 on test vs 0.77 in CV.

## Summary

| Problem | Points lost (CV) | Category | Recommended action |
|---|---:|---|---|
| Task 2 facebook ↔ instagram | 4.75 | irreducible (92-100% on identical openings) | none |
| Task 1 facebook ↔ instagram | 2.86 | data-starved (facebook F1 +0.186 from 75% to 100%) | only more same-distribution labelled data; own captures do not qualify (056-063) |
| Task 1 youtube ↔ google | 1.72 | data-starved (separable at AUC 0.94 in isolation) | small consistent gains exist (065, 077) but are below CV's detection limit (+0.010) |
| Task 2 youtube ↔ google | 2.02 | irreducible (84-100%) | none |
| Task 2 mozilla → x | 0.86 | irreducible (96%) | none |
| Task 2 facebook → x | 0.88 | data-starved | none available |
| Task 2 mozilla ↔ google | 0.69 | model-limited | the one fixable cell; ≤ 0.7 CV points |
| Task 1 mozilla → google | 0.31 | model-limited | ≤ 0.3 CV points |

Most promising next problem: Task 2 mozilla ↔ google (model-limited, separable at AUC 0.99, 0.69 CV points), but it is small and
Task 2 is already at the leader's level on test. Is 93 reachable? Not by modelling this data: fixing every model-limited cell is
worth about +1 CV point; the large losses are irreducible (Task 2) or data-starved with no matching data available (Task 1). A
leaderboard jump of that size would need luck on 81 flows or information we do not have.
