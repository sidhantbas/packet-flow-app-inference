---
title: "103: Reproducing LLM_ops's Lookup-Ensemble-v7 (93.44) on our data"
created: 2026-10-13
creator: sidhantbas
description: "Frozen reproduction of the second leaderboard entry that describes its method: exact first-5-packet lookup stacked into seed-bagged, Optuna-tuned tree ensembles, ratio and post-prefix features, prior correction, and (measured only) capture-time smoothing and count matching. Both tasks; never-used seeds 2106-2110; components in src/flowkit/."
source:
  - ../docs/reports/leaderboard-method-reproduction.md
  - 102_flowlens_reproduction.md
  - 036_twin_aware.md
  - 039_capture_order.md
experiment:
  id: '103'
  tasks: [task1, task2]
  lever: model
  status: rejected
  verdict: 'Not reproduced: the claim (minus the SNI proxy) is WORSE than production on 5 of 5 never-used seeds in both tasks (Task 1 -0.065, Task 2 -0.065); compliant L3 WORSE too; their base starts 0.07-0.10 lower; capture-time smoothing hurts both tasks; prior correction +0.006 on Task 1 only'
---

# 103: Reproducing Lookup-Ensemble-v7

**Status: done 2026-10-13. Protocol frozen (`f664196`) before any code or run.**
**Verdict: not reproduced in either task (every arm WORSE than production on all five never-used seeds); capture-time smoothing hurts.** Results are below the protocol. Do not edit the frozen
sections after execution starts. Sid and Charles, 2026-10-13: reproduce the leaders one by one (102 done: not reproduced).

## The claim (verbatim, leaderboard 2026-10-13)

> **Lookup-Ensemble-v7** (LLM_ops): Task-specific exact-signature lookup (first-5-packet fingerprint) blended with a seed-bagged
> ensemble of Optuna-tuned LightGBM, XGBoost, ExtraTrees, and RandomForest (Task 1) / LightGBM×2 + ExtraTrees + KNN-Manhattan
> (Task 2). Features: raw header statistics + ratio/rate/CV features; Task 1 adds post-prefix delta features; Task 2 adds mod-8
> byte features as SNI-length proxy. Stacked lookup probabilities feed the tree ensemble. Temporal Gaussian smoothing (σ=0.5 s
> for T1, 1.0 s for T2) blends flow predictions across same-session neighbours. Mild prior correction (β=0.25) guards macro-F1
> on rare classes. Hungarian count-matching uses published metadata class counts for both tasks. No IPs, DNS, SNI, payload, or
> test labels used.

Their scores: Task 1 Macro F1 0.94, Task 2 Macro F1 0.93, Total 93.44.

## Reading of the claim (unknown details fixed now, before any run)

| Part | Our implementation | Assumed because the note does not say |
|---|---|---|
| Features, Task 1 | The 17 Task 1 columns + ratio/rate/CV features + the 11 post-prefix (rest-of-flow) columns | Exact ratio set: size CV per direction, bytes/s and packets/s per direction, IAT CV, bursts/s |
| Features, Task 2 | The 17 Task 2 columns (timing included) + the same ratio/rate/CV features | — |
| SNI-length proxy (mod-8 byte features) | **Not built** | Condition 3: no attempt to recover TLS SNI, its length included |
| Exact first-5 lookup | Class distribution of training flows with the identical 12-column opening (sizes, counts, transport; no timing); training rows use leave-one-out counts | — |
| Stacked lookup probabilities | The 6 lookup fractions + the match count added as features | — |
| Blended with the ensemble | Where the opening was seen in training: mean of the ensemble's and the lookup's probabilities | Equal weights |
| Ensemble, Task 1 | LightGBM + XGBoost + ExtraTrees + RandomForest, mean probability, no class weights | No class weights (rare classes are handled by the prior correction) |
| Ensemble, Task 2 | LightGBM ×2 (two seeds) + ExtraTrees + kNN (Manhattan, distance-weighted, k = 7, log1p + standardised) | k = 7 (as 016) |
| Optuna tuning | Each member tuned inside each outer training fold: 15 TPE trials, 3-fold inner CV, macro F1 | Budget and search spaces (listed in the runner) |
| Seed bagging | Each member averaged over 3 seeds | 3 bags |
| Prior correction, β = 0.25 | p ∝ p_c / π_c^0.25, π = training class shares | The formula |
| Temporal smoothing | Within each batch (held-out fold), p_i ← Σ_j w_ij p_j / Σ_j w_ij, w_ij = exp(−(t_i − t_j)² / 2σ²), t = `start_rel`, σ = 0.5 s (Task 1), 1.0 s (Task 2) | Batch-only, predictions only |
| Hungarian count matching | Linear assignment to the batch's class counts (as 102) | — |

**Rule status.** Capture time (`start_rel`) and the published test counts are excluded from our submissions by our rules. They
are measured here on train + validation only: "disclosed" counts are the held-out fold's own labels, as in 095 and 102.

## Frozen design (each task separately)

| Arm | Adds | Usable in a submission |
|---|---|:---:|
| P | Production (Task 1 `task1_cross_task`, Task 2 `task2_model`) | — |
| L0 | Their base ensemble on their features, default settings, argmax | ✅ |
| L1 | L0 + stacked and blended lookup | ✅ |
| L2 | L1 with Optuna tuning and 3-seed bagging | ✅ |
| L3 | L2 + prior correction β = 0.25 | ✅ |
| L4 | L3 + temporal smoothing | ❌ measurement only |
| L5 | L4 + Hungarian matching to the true held-out counts (the claim minus the SNI proxy) | ❌ measurement only |

- **Folds:** repeated stratified 5 × 10 at cv_seeds **2106-2110** (0 runs in `results/`); model seed = fold index; every arm
  against P on the same folds.
- **Cost control:** L3-L5 reuse L2's fitted fold models through a disk cache keyed by task, seed, fold and training rows.
- **Test-set effect (no labels):** L0-L3 fitted on train + validation and applied to the 81 test flows; changed predictions
  against our submitted files. L4 and L5 are not built for the test set.
- **Smoke checks:** the lookup's leave-one-out counts on a toy table; prior correction with β = 0 returns the input; temporal
  smoothing with σ → 0 returns the input; the cached and uncached L2 give identical predictions on one fold.

## Decision rule

- **Claim reproduced on our data (per task):** L5 is rule v2 BETTER than P on all five seeds.
- **Compliant candidate (per task):** L3 is rule v2 BETTER than P on all five seeds. It could then be proposed for production
  (user decision) and an upload only under the upload rule.
- **Ingredients:** each step reported as a paired Δ (L1 − L0 lookup, L2 − L1 tuning and bagging, L3 − L2 prior correction,
  L4 − L3 smoothing, L5 − L4 counts), with per-class changes.

## Boundaries

Train + validation labels only; test features only for the test-effect check. Task 2 reads only Task 2 files (the Task 2 arm's
`start_rel` comes from the Task 2 file). No test labels or `label_counts`; no upload.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-13 | Protocol frozen and committed | before any code or run |
| 2026-10-13 15:43 | Code committed (`b382259`): `src/flowkit/` features, lookup, members (Optuna), postprocess; runner; smoke checks | lookup leave-one-out, β = 0 and σ → 0 identities, cached L3 = uncached L3 on one fold for both tasks |
| 15:43-16:22 | All 7 arms × 2 tasks × cv_seeds 2106-2110 (`--all`) | 70 runs `…_103_<T1|T2>_<arm>_s<seed>`, no errors |
| after the runs | `--analyse`, `--test-effect` | `experiments/103_evidence/analysis.json`, `test_effect.json` |

No deviation from the frozen protocol.

### Commands

```bash
.venv/bin/python src/exp103_lookup_ensemble_reproduction.py --smoke
.venv/bin/python src/exp103_lookup_ensemble_reproduction.py --all
.venv/bin/python src/exp103_lookup_ensemble_reproduction.py --analyse
.venv/bin/python src/exp103_lookup_ensemble_reproduction.py --test-effect
```

## Results

### Every arm (CV macro F1, mean of five never-used seeds)

| Arm | Task 1 | Δ vs P | Task 2 | Δ vs P |
|---|---:|---:|---:|---:|
| P production | **0.849** | — | **0.766** | — |
| L0 their base ensemble and features | 0.774 | −0.074 | 0.667 | −0.099 |
| L1 + stacked and blended lookup | 0.770 | −0.079 | 0.724 | −0.042 |
| L2 + Optuna tuning, 3-seed bagging | 0.774 | −0.075 | 0.729 | −0.037 |
| L3 + prior correction β = 0.25 (compliant end of the ladder) | 0.780 | **−0.068** | 0.723 | **−0.043** |
| L4 + temporal smoothing (measured only) | 0.760 | −0.089 | 0.706 | −0.060 |
| L5 + count matching to true held-out counts (the claim, measured only) | 0.784 | **−0.065** | 0.701 | **−0.065** |

Every arm is WORSE than production on all five seeds in both tasks (L3 and L5 win 4-12 of 50 folds per seed).

### What each step adds (paired, mean of five seeds; wins / losses summed)

| Step | Task 1 | Task 2 |
|---|---:|---:|
| Their base instead of production (L0 − P) | −0.074 | −0.099 |
| Lookup, stacked and blended (L1 − L0) | −0.005 | **+0.057** (219 W / 31 L) |
| Optuna tuning and bagging (L2 − L1) | +0.004 | +0.004 |
| Prior correction β = 0.25 (L3 − L2) | **+0.006** (113 W / 58 L) | −0.006 |
| Temporal smoothing over capture time (L4 − L3) | **−0.021** | **−0.016** |
| Count matching, true counts (L5 − L4) | +0.024 | −0.006 |

### Effect on our test predictions (L0-L3, no labels)

| Arm | Task 1 changes vs submitted | Task 2 changes vs submitted |
|---|---:|---:|
| L0 | 10 | 7 |
| L1 | 11 | 3 |
| L2 | 10 | 4 |
| L3 | 8 (facebook 4 → 1 call; youtube → x 2, facebook → youtube 2) | 4 |

## Verdict

- **Not reproduced on our data, in either task.** The claim as written (L5, minus the SNI proxy) is WORSE than production on all
  five never-used seeds: Task 1 −0.065, Task 2 −0.065. The compliant ladder end (L3) is also WORSE ×5 (−0.068, −0.043). Status:
  rejected.
- **The gap is the base, not the extras.** Their ensemble on their features starts 0.07-0.10 below our production, and no
  ingredient recovers that. Our production already contains what helps here: exact-opening memory (the lookup's +0.057 in Task
  2 is what our trees and 014 already get from memorising openings) and post-prefix features (089).
- **Ingredients worth noting:** prior correction β = 0.25 helped Task 1 on every seed (+0.006, 113 W / 58 L) but hurt Task 2.
  On top of production it would be a new, separate idea (BACKLOG). **Capture-time smoothing hurts both tasks** (−0.021,
  −0.016), so the excluded signal does not explain their score either. Count matching helps their weaker Task 1 base (+0.024)
  but not Task 2.
- **Their 93.44 stays unexplained** by the parts of the note we can test.
