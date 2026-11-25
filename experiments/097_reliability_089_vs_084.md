---
title: "097: Reliability of Task 1 model 089 versus 084, with component ablations, on ordinary and twin-aware folds"
created: 2026-10-12
creator: sidhantbas
description: Frozen protocol and results for checking whether 089's advantage over 084 and each of its three added components hold on ordinary stratified folds and on the documented twin-aware grouped folds.
source:
  - 084_pair_verifiers.md
  - 089_near_miss_bundle.md
  - 036_twin_aware.md
  - 096_task2_timing_tiebreaker.md
experiment:
  id: 097
  tasks:
  - task1
  lever: evaluation
  status: measured
  verdict: 089 beats 084 on ordinary and twin-aware folds (+0.014 to +0.017); exact-opening override consistently useful; rest-of-flow expert and facebook-only rescue inconclusive by rule
---

# 097: Reliability of 089 versus 084

**Status: done 2026-10-12. Protocol frozen (`024b133`) before any code change or run.**
**Verdict: 089 beats 084 on ordinary and twin-aware folds (Δ +0.014 to +0.017, positive in 59 of 60 repeats). Consistent component benefit: exact-opening override only; rest-of-flow expert inconclusive by the rule (same direction everywhere); facebook-only gate rescue inconclusive. No ablation is more robust.** Results are below.
Do not edit the frozen sections after execution starts. User brief 2026-10-12 (pasted): "Experiment 096 failed. Retain Task 2
production 014. Next, investigate the reliability of Task 1 model 089 versus 084."

## Variants (checked against `src/models.py`)

089 (`models.task1_bundle`) = 084 (`models.task1_pair_verifiers`: 034 Meta gate + google-vs-instagram and google-vs-x verifiers)
plus three components:

| Component | Where it lives | Removable alone? |
|---|---|---|
| **R** rest-of-flow expert (third expert in the averaged probabilities, 11 derived columns) | `RestIGMetaGate.fit/predict` | Yes: average the two experts instead of three |
| **IG** facebook-only gate rescue (a gate call of instagram reverts to the two-clerks label when that label is non-Meta) | last step of `RestIGMetaGate.predict` | Yes: skip the revert |
| **H1** exact-opening override outside Meta | `ScopedH1` wrapper around `BundleVerifiers` | Yes: leave the wrapper out |

The two verifiers, the Meta gate and every other rule are unchanged in all variants. Variants are built by one parameterised class
in `src/exp097_reliability.py`; with all three components off it must reproduce 084 and with all on 089 (checked on one fold
before any run).

| Arm | Model |
|---|---|
| V084 | 084 |
| V089 | 089 |
| V089-R | 089 without the rest-of-flow expert |
| V089-IG | 089 without the facebook-only gate-rescue restriction |
| V089-H1 | 089 without the exact-opening override |

Inputs: the 34 production columns (17 Task 1 statistics + the 17 disclosed first-five-packet statistics of the same flow); the 11
rest-of-flow columns are derived inside the model from them. No `start_rel`, no capture order, no test labels, no leaderboard.

## Folds (identical for every arm)

- **Ordinary:** `RepeatedStratifiedKFold(5, 10)` with cv_seeds **2026, 2027, 2028** (model seed = fold index). Saved runs reused
  where the code and folds are identical: V084 = `20261009T220447Z_084_ALL`, `…220504Z…_ALL_s2027`, `…220522Z…_ALL_s2028`;
  V089 seed 2026 = `20261010T004051Z_089_production_check_s2026`. All other arm × seed cells are run.
- **Twin-aware grouped** (036's documented definition): groups = connected components of the 330 labelled flows whose **17 Task 1
  whole-flow statistical columns** (`models.T1_COLS`: duration, transport, packet_count_up/down, bytes_up/down,
  mean_pkt_size_up/down, std_pkt_size_up/down, mean_iat, std_iat, min_iat, max_iat, burst_count, up_down_packet_ratio,
  up_down_byte_ratio), log1p and standardised over the 330 flows, lie within Euclidean distance **0.05** (303 groups; 16 with more
  than one flow, covering 43 flows). `StratifiedGroupKFold(5, shuffle)` × 10 with `random_state = seed + repeat`, seeds 2026, 2027,
  2028 (`exp036_twin_aware.twin_splits`). All five arms are run.

All fitting (experts, gate, verifiers, rest columns, exact-opening table) happens inside each training fold.

## Reported

Macro F1 and paired Δ (rule v2 verdicts via `runlog`); per-class F1; errors corrected and introduced (pooled out-of-fold
predictions); results for held-out flows **with** vs **without** an exact 12-column opening match (`TwoClerks.OPEN_COLS`) in the
training fold; the Δ per CV repeat (10 values per seed, described, not treated as independent).

Comparisons: V089 vs V084 (does the bundle beat its base?), and each ablation vs V089 (what does removing the component do?).

## Decision rules (fixed now)

- **Component with consistent evidence of benefit:** V089 beats the ablation under rule v2 (BETTER) on all three ordinary seeds
  **and** with Δ > 0 on all three grouped seeds. Otherwise inconclusive or no benefit.
- **089's advantage survives grouped evaluation:** V089 − V084 Δ > 0 on all three grouped seeds (rule v2 verdicts reported).
- **Removing a component improves robustness:** the ablation beats V089 (Δ > 0) on all three grouped seeds.
- If neither holds, the result is reported as inconclusive; no winner is chosen. No other combinations are run after seeing the
  results. Production is not changed and nothing is submitted.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-12 | Protocol frozen and committed | before any code change or run |
| 2026-10-12 | Runner committed; smoke test | with all components off the variant reproduces `task1_pair_verifiers` (084), with all on `task1_bundle` (089), on fold 0 |
| 23:06-23:15 | 26 runs: ordinary ablations × 3 seeds, V089 ordinary 2027/2028, all 5 arms grouped × 3 seeds | runs `…_097_<arm>_<folds>_s<seed>`; saved V084 (×3) and V089 (2026) reused as frozen |
| after the runs | Analysis | `experiments/097_evidence/analysis.json` |

No deviation from the frozen protocol. No combinations beyond the five arms were run.

## Results

### Macro F1 (mean over 50 folds)

| Arm | ord. 2026 | ord. 2027 | ord. 2028 | grouped 2026 | grouped 2027 | grouped 2028 |
|---|---:|---:|---:|---:|---:|---:|
| V084 | 0.8321 | 0.8336 | 0.8061 | 0.7719 | 0.7770 | 0.7814 |
| **V089** | **0.8490** | **0.8490** | **0.8205** | **0.7874** | **0.7916** | **0.7972** |
| V089-R (no rest-of-flow expert) | 0.8401 | 0.8410 | 0.8093 | 0.7787 | 0.7839 | 0.7895 |
| V089-IG (no facebook-only gate rescue) | 0.8458 | 0.8467 | 0.8215 | 0.7863 | 0.7897 | 0.7949 |
| V089-H1 (no exact-opening override) | 0.8393 | 0.8411 | 0.8108 | 0.7772 | 0.7822 | 0.7874 |

### Paired comparisons (Δ = first − second; W / L / T over 50 folds; rule v2 verdict from `runlog`)

| Comparison | ord. 2026 | ord. 2027 | ord. 2028 | grouped 2026 | grouped 2027 | grouped 2028 |
|---|---|---|---|---|---|---|
| **V089 − V084** | +0.0169, 42/8/0, BETTER | +0.0154, 37/11/2, BETTER | +0.0144, 33/10/7, BETTER | +0.0154, 28/16/6, near-miss | +0.0146, 32/13/5, BETTER | +0.0157, 33/13/4, BETTER |
| V089-R − V089 | −0.0089, 15/31/4 | −0.0080, 13/29/8 | −0.0112, 11/26/13 (V089 BETTER) | −0.0087, 15/25/10 | −0.0077, 14/27/9 | −0.0077, 16/24/10 |
| V089-IG − V089 | −0.0032, 1/13/36 (V089 BETTER) | −0.0023, 3/16/31 (V089 BETTER) | **+0.0011**, 7/10/33 | −0.0011, 6/15/29 | −0.0019, 6/16/28 | −0.0023, 4/16/30 |
| V089-H1 − V089 | −0.0097, 0/28/22 (V089 BETTER) | −0.0079, 0/27/23 (V089 BETTER) | −0.0096, 0/31/19 (V089 BETTER) | −0.0101, 0/31/19 | −0.0093, 0/29/21 | −0.0098, 0/31/19 |

Per CV repeat (10 per cell; repeats share flows and are not independent): V089 − V084 is positive in 59 of 60 repeats (one at
−0.0004); removing H1 is negative in 60 of 60; removing R is negative in 58 of 60; removing IG is positive in 19 of 60.

### Errors corrected and introduced (pooled out-of-fold predictions, 10 repeats)

| Comparison | ord. 2026 | ord. 2027 | ord. 2028 | grouped 2026 | grouped 2027 | grouped 2028 |
|---|---|---|---|---|---|---|
| V089 vs V084: corrected / introduced | 87 / 29 | 79 / 35 | 83 / 33 | 91 / 39 | 88 / 40 | 91 / 38 |
| Removing R: corrected / introduced | 28 / 62 | 32 / 57 | 27 / 60 | 34 / 60 | 35 / 58 | 34 / 58 |
| Removing IG: corrected / introduced | 1 / 4 | 3 / 2 | 6 / 4 | 5 / 4 | 5 / 5 | 4 / 5 |
| Removing H1: corrected / introduced | 0 / 43 | 0 / 34 | 0 / 44 | 0 / 45 | 0 / 42 | 0 / 44 |

### Flows with vs without an exact training-set opening match

72-75% of held-out flows have an exact 12-column opening match in their training fold. Accuracy (with match / without match):

| Arm | ord. 2026 | grouped 2026 | grouped 2028 |
|---|---|---|---|
| V084 | 0.956 / 0.662 | 0.941 / 0.637 | 0.944 / 0.634 |
| V089 | 0.967 / 0.701 | 0.954 / 0.660 | 0.960 / 0.651 |
| V089-R | 0.966 / **0.663** | 0.952 / **0.637** | 0.956 / **0.634** |
| V089-H1 | **0.949** / 0.701 | **0.935** / 0.660 | **0.941** / 0.651 |

The rest-of-flow expert accounts for 089's whole gain on flows **without** an opening match (removing it returns them to the 084
level); the exact-opening override acts only on flows **with** a match (by design), and removing it drops them below 084.

### Per-class F1 (V084 → V089)

Ordinary 2026: facebook 0.693 → 0.690, instagram 0.759 → 0.785, google 0.896 → 0.911, youtube 0.809 → 0.832, mozilla 0.919 →
0.944, x 0.944 → 0.957. Grouped 2026: facebook 0.486 → 0.488, instagram 0.710 → 0.725, google 0.877 → 0.887, youtube 0.777 →
0.795, mozilla 0.915 → 0.943, x 0.932 → 0.952. The gain is in the non-Meta classes and instagram; facebook is unchanged.

## Verdict (decision rules fixed in advance)

- **089's advantage survives grouped evaluation:** V089 − V084 > 0 on all three grouped seeds (+0.0146 to +0.0157; rule v2
  BETTER on 2027 and 2028, near-miss on 2026), about the same size as on ordinary folds (+0.0144 to +0.0169).
- **Consistent evidence of benefit: H1 (exact-opening override) only.** V089 is BETTER than the ablation on all three ordinary seeds
  and Δ > 0 on all three grouped seeds; removing it corrects nothing and introduces 34-45 errors in every cell.
- **R (rest-of-flow expert): inconclusive by the rule**, though every cell points the same way: BETTER on only one ordinary seed
  (the other two win 67% and 69% of non-tied folds, below 70%), Δ > 0 on all three grouped seeds.
- **IG (facebook-only gate rescue): inconclusive.** BETTER on two ordinary seeds but slightly negative on 2028; small positive Δ
  on all grouped seeds; it changes only 16-26 predictions per cell.
- **Removing any component does not improve robustness:** every ablation is below V089 on all three grouped seeds.
- Production unchanged; nothing submitted; no further combinations run.
