---
title: "119: How much of the leaders' facebook/instagram advantage comes from each lever they describe? (measurement only)"
created: 2026-10-19
creator: sidhantbas
description: "Frozen Meta-specific decomposition, on production's folds, of the levers the top leaderboard entries describe (count-constrained assignment, cross-task joint decoding, capture-time smoothing, calibration, a server-name proxy), with an allowed count variant from training proportions; each lever classified as allowed or excluded."
source:
  - 095_disclosed_count_simulation.md
  - 099_class_count_deficit.md
  - 102_flowlens_reproduction.md
  - 103_lookup_ensemble_reproduction.md
  - 105_pairswap_reproduction.md
  - 107_temporal_label_neighbours.md
  - ../docs/reports/leaders-vs-ours-dedup.md
experiment:
  id: '119'
  tasks: [task1, task2]
  lever: diagnostic
  status: measured
  verdict: 'No described lever explains the leaders'' facebook/instagram advantage on our data: none raises facebook or instagram F1 over production by ≥ 0.05; even oracle test-style counts lower Task 1 facebook F1 (−0.12 to −0.19); smoothing is worst (−0.08 to −0.12 macro). The only gain is cross-task joint decoding for Task 2 (+0.0135), which condition 2 excludes. No allowed lever qualifies'
---

# 119: Meta-specific decomposition of the leaders' levers

**Status: done 2026-10-19. Protocol frozen (`74e5a63`) before any code or run.**
**Verdict: none of the levers the leaders describe reproduces a facebook/instagram gain on our data; production's Meta handling
beats all of them, including oracle counts.** Results are below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-19: decode how the top entries handle facebook vs instagram,
measure each lever on our data, classify it, and name the one allowed lever (if any) worth a frozen experiment. **Measurement only:**
no model change, no test labels, test `label_counts` values never read.

## Raw material

- Leaderboard API records (`submissions/raw/leaderboard-final-test-2026-10-16.json`) and the leaders' verbatim method notes
  (`submissions/raw/leaderboard-final-test-2026-10-13*.txt`): errors per task from accuracy × 81, price per error from macro F1.
- Production's per-flow out-of-fold labels (champion runs, cv_seed 2026) and, on the same folds, out-of-fold class probabilities
  of a balanced `SoftVote` per task (model seed = fold index; Task 1: 34 production columns; Task 2: 12).

## Frozen design

All levers act on the same 50 folds (5 × 10, cv_seed 2026). "Oracle counts" = the held-out fold's own true class counts: the
cross-validation stand-in for published test counts.

| # | Lever (leader source) | Implementation | Status for us |
|---|---|---|---|
| A0 | Plain probabilities | argmax of SoftVote | reference |
| P | Production | champion labels | reference |
| L1 | Count-constrained assignment, all classes (Infralibre v8/v9, LLM_ops, RahmaniJ) | Hungarian assignment (`linear_sum_assignment`, cost −log p) of the fold's flows to class slots = oracle counts | excluded: our condition 1 reading (test counts) |
| L1m | Count fix inside Meta only, on production | among flows production calls facebook/instagram, the top-k by p(fb)/(p(fb)+p(ig)) become facebook, k = oracle facebook count (capped), the rest instagram | excluded (test counts) |
| L1b | Count constraint from **training proportions** (allowed variant) | as L1 and L1m, with counts = training share × fold size (largest-remainder rounding) | allowed |
| L2 | Cross-task joint decoding (Infralibre v9, RahmaniJ) | geometric mean of the two tasks' SoftVote probabilities → one label for both tasks | Task 1: allowed (as 022/100); Task 2: excluded by condition 2 |
| L3 | Capture-time smoothing (LLM_ops), σ = 1 s | each flow's probabilities replaced by the Gaussian-weighted mean over all 330 flows' out-of-fold probabilities by `start_rel` (predictions only, no labels) | excluded: our rule (capture time) |
| L3m | Smoothing inside Meta only, on production | production's facebook/instagram calls re-decided by the smoothed p(fb) vs p(ig) | excluded (capture time) |
| L1+L3 | Leader-like stack | oracle-count assignment on smoothed probabilities | excluded |
| L4 | Calibration (Infralibre v8) | not re-run: 095 measured calibrated SoftVote + quotas | allowed; 095 result cited |
| L5 | Packet sizes mod 8 as an SNI-length proxy (LLM_ops) | not computed | excluded: challenge condition 3 |

**Reported per lever and task:** macro F1 (mean of 50 folds), facebook and instagram F1 (pooled per repeat, mean of 10), Δ against
production.

**Reading, fixed now:** a lever "explains part of the leaders' Meta advantage" if it raises facebook or instagram F1 by ≥ 0.05
over production. The one allowed lever worth a frozen experiment is the allowed lever (L1b, L2 Task 1) with the largest macro-F1
gain over production, if that gain is ≥ +0.005; otherwise none.

## Boundaries

No test labels or test `label_counts` values; Task 2 levers use only Task 2 files, except L2 Task 2, which is measured only to
size an excluded lever. Capture time is measured, never adopted. No production or submission change.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-19 | Protocol frozen and committed | before any code change or run |
| 2026-10-19 | `src/exp119_leader_meta_decomposition.py` run (9 s) | `119_evidence/decomposition.json`; production's out-of-fold labels matched the recomputed folds exactly (asserted) |

No deviation from the frozen protocol.

## Results

Evidence: [`119_evidence/decomposition.json`](119_evidence/decomposition.json). Macro F1 is the mean of 50 folds (Δ vs production in
brackets); facebook / instagram F1 pooled per repeat, mean of 10.

| # | Lever | Task 1 macro | Task 1 fb / ig F1 | Task 2 macro | Task 2 fb / ig F1 | Status |
|---|---|---|---|---|---|---|
| A0 | Plain SoftVote probabilities | 0.7811 (-0.0762) | 0.561 / 0.737 | 0.7362 (-0.0182) | 0.440 / 0.656 | reference |
| P | Production | 0.8573 (+0.0000) | 0.726 / 0.784 | 0.7544 (+0.0000) | 0.469 / 0.731 | **production** |
| L1 | Oracle-count assignment, all classes | 0.7840 (-0.0733) | 0.536 / 0.726 | 0.7247 (-0.0297) | 0.445 / 0.637 | excluded (test counts) |
| L1m | Oracle facebook count inside production's Meta calls | 0.8283 (-0.0290) | 0.609 / 0.725 | 0.7488 (-0.0056) | 0.473 / 0.637 | excluded (test counts) |
| L1b | Training-proportion counts, all classes | 0.7797 (-0.0776) | 0.514 / 0.718 | 0.7260 (-0.0284) | 0.419 / 0.636 | allowed |
| L1b-m | Training-proportion facebook count inside Meta | 0.8279 (-0.0294) | 0.590 / 0.733 | 0.7439 (-0.0105) | 0.429 / 0.636 | allowed |
| L2 | Cross-task joint decoding | 0.7679 (-0.0894) | 0.469 / 0.721 | 0.7679 (+0.0135) | 0.469 / 0.721 | Task 1 allowed; Task 2 excluded (condition 2) |
| L3 | Capture-time smoothing (σ 1 s) | 0.7329 (-0.1244) | 0.433 / 0.716 | 0.6735 (-0.0809) | 0.331 / 0.580 | excluded (capture time) |
| L3m | Smoothing inside production's Meta calls | 0.8066 (-0.0507) | 0.511 / 0.729 | 0.7262 (-0.0282) | 0.397 / 0.616 | excluded (capture time) |
| L1+L3 | Oracle counts on smoothed probabilities | 0.7417 (-0.1156) | 0.464 / 0.700 | 0.6725 (-0.0819) | 0.309 / 0.579 | excluded |

**Leaderboard error budget** (16 October; errors = 81 − accuracy × 81; points per error = 50 × (1 − macro F1) / errors):

| Team | Task 1 errors | Points per error | Task 2 errors | Points per error |
|---|---:|---:|---:|---:|
| Infralibre | 4 | 0.45 | 7 | 0.46 |
| HeriTech | 4 | 0.54 | 6 | 0.48 |
| LLM_ops | 6 | 0.51 | 7 | 0.5 |
| RahmaniJ | 8 | 0.47 | 8 | 0.47 |
| Telex | 7 | 1.02 | 9 | 0.53 |

**Method notes** (verbatim, 13 October snapshots): Infralibre v9 "count-preserving Task 1 consensus swap" and v8 "disclosed-count
analysis"; LLM_ops "Hungarian count-matching uses published metadata class counts for both tasks", "temporal Gaussian smoothing
(σ=0.5 s for T1, 1.0 s for T2)", "mod-8 byte features as SNI-length proxy", prior correction β = 0.25; RahmaniJ "published
metadata.json class counts are used for constrained assignment"; HeriTech gives no method.

## Verdict

**No described lever reproduces a facebook/instagram gain on our data** (none raises facebook or instagram F1 over production by
≥ 0.05, the frozen threshold), and no allowed lever gains ≥ +0.005 macro F1, so no frozen experiment follows.

1. **Counts do not fix Meta for us, even oracle counts.** Assigning each fold's *true* class counts (L1) is 0.073 below production in
   Task 1 and only +0.003 above plain SoftVote; forcing the true facebook count inside production's Meta calls (L1m) costs facebook
   0.12 and instagram 0.06 in Task 1, and trades facebook +0.004 for instagram −0.094 in Task 2. Knowing *how many* facebook flows
   there are does not tell *which* ones, when their probabilities collide.
2. **Capture-time smoothing hurts most** (−0.08 to −0.12 macro, facebook −0.14 to −0.29) on our 330 flows, though the session signal is
   strong (115). With predicted (not true) neighbours, smoothing spreads the dominant classes into the rare ones.
3. **Joint decoding helps only where it is forbidden:** +0.0135 for Task 2 (facebook unchanged, instagram −0.010, gains in other
   classes), using Task 1 information, which condition 2 excludes; for Task 1 it is −0.089 below production (production already
   uses Task 2 information in a better way, 022/100).
4. **The leaders' Meta advantage therefore remains unexplained by their described methods on our data.** Their errors cost about 0.45
   points each against our 1.02, so they avoid facebook/instagram mistakes on the test set. Possible sources, none measurable here:
   their own base models, repeated uploads against the 81 scored flows (5 a day), and test-specific effects of the published counts
   (the test holds only about 3 facebook flows, so an exact count with the right ranking removes most facebook errors at once).

**Outside evidence that would settle it:** the organisers' post-review final ranking (whether count-using entries stand), the
leaders' required technical reports, and an independent re-run by Charles or Temi from the shared repository.
