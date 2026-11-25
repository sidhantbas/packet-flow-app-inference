---
title: "102: Reproducing Infralibre's FlowLens-v8-Mozilla (93.74) on our data"
created: 2026-10-13
creator: sidhantbas
description: "Frozen reproduction of the highest-scoring leaderboard entry that describes its method: a class-balanced first-5-packet ensemble with probability calibration and disclosed-count analysis for Task 2, Task 1 unchanged. Never-used seeds 2101-2105; reusable components in src/flowkit/."
source:
  - ../docs/reports/leaderboard-method-reproduction.md
  - 095_disclosed_count_simulation.md
  - 014_fb_ig_specialist.md
experiment:
  id: '102'
  tasks: [task2]
  lever: decision
  status: rejected
  verdict: 'Not reproduced: the claim as written (balanced first-5 ensemble + sigmoid calibration + disclosed counts) is WORSE than production on 5 of 5 never-used seeds (-0.036); disclosure adds -0.005 over training-share counts; on the test set count assignment would change 6-7 Task 2 predictions, all away from our x surplus'
---

# 102: Reproducing FlowLens-v8-Mozilla

**Status: done 2026-10-13. Protocol frozen (`30c54d6`) before any code or run.**
**Verdict: not reproduced on our data (every arm WORSE than production on all five never-used seeds); the recipe would change 6-7 of our Task 2 test predictions, all away from our x surplus.** Results are below the protocol. Do not edit the frozen
sections after execution starts. Sid and Charles, 2026-10-13: review the leaders one by one, reproduce each claim, document our
results and the claim's verification, then deduplicate and decide.

## The claim (verbatim, leaderboard 2026-10-13)

> **FlowLens-v8-Mozilla** (Infralibre): Class-balanced prefix-five ensemble with probability calibration and disclosed-count
> analysis. Task 2 uses only the released realtime prefix-five features; Task 1 remains unchanged.

Their scores: Task 1 Macro F1 0.94, Task 2 Macro F1 0.94, Total 93.74. HeriTech (94.98) is higher but describes no method.

## Reading of the claim

| Part | Our reading | Unknown |
|---|---|---|
| Class-balanced prefix-five ensemble | Balanced `SoftVote` (RF + ExtraTrees + LightGBM) on the 12 no-timing Task 2 columns: the base of our Task 2 production (014) | Their members and columns |
| Probability calibration | `CalibratedClassifierCV`, sigmoid or isotonic | Method, folds |
| Disclosed-count analysis | Labels assigned so that each class gets its disclosed count (linear assignment on log-probabilities, as 095) | Exact rule |
| Task 1 remains unchanged | Their Task 1 is not described, so there is nothing to reproduce; our Task 1 stays production | Their Task 1 (0.94) |

**What 095 already did:** sigmoid calibration fitted on inner thirds, counts, both tasks, one seed (2026): Task 2 −0.05 vs
production. **What 102 adds:** Task 2 only (as claimed), calibration fitted on cross-validated probabilities (the full training
fold) as well as both methods, five never-used seeds, and the effect on our own test predictions.

## Frozen design (Task 2 only)

| Arm | Base | Calibration | Labels |
|---|---|---|---|
| P | Production `models.task2_model` (014) | — | its own |
| F0 | Balanced `SoftVote`, 12 no-timing columns | none | argmax |
| F1S | F0 | sigmoid, fitted on 5-fold cross-validated probabilities of the training fold, then the base refitted on all of it (`ensemble=False`) | argmax |
| F1I | F0 | isotonic, same scheme | argmax |
| F2S-D | F1S | sigmoid | assignment to the held-out fold's **true** class counts (simulated disclosure: measurement only) |
| F2S-S | F1S | sigmoid | assignment to training-share counts × fold size (compliant) |
| F2I-D | F1I | isotonic | true held-out counts (simulated disclosure) |
| F2I-S | F1I | isotonic | training-share counts (compliant) |

- **Folds:** repeated stratified 5 × 10 at cv_seeds **2101-2105** (0 runs in `results/`); model seed = fold index. Every arm runs
  against P on the same folds.
- **Primary arm (the claim as written):** F2S-D. Sigmoid is `CalibratedClassifierCV`'s default.
- **Test-set effect (no labels):** each arm except the D arms fitted on train + validation and applied to the 81 test flows.
  Reported: predicted class counts and the predictions changed against our submitted Task 2 file. The D arms would need the test
  `label_counts`, which our rule forbids, so they are not built.
- **Smoke checks:** the new quota assignment equals `exp095_disclosed_counts.quota_assign`; F0's predictions equal the 014 base
  `SoftVote` on one fold.
- **Code:** reusable components in `src/flowkit/` (base models, calibration, count assignment, a composable pipeline), and a
  runner `src/exp102_flowlens_reproduction.py` with command-line flags. Commands are listed in this log; runs go to `results/`,
  other evidence to `experiments/102_evidence/`.

## Decision rule

- **Claim reproduced on our data:** F2S-D or F2I-D is rule v2 BETTER than P on all five seeds. Otherwise: not reproduced.
- **Ingredients:** each step reported as a paired Δ (F1 vs F0: calibration; F2-D vs F1: counts with disclosure; F2-S vs F1:
  counts without; D vs S: the disclosure itself).
- **Production:** only a compliant arm (F0, F1, F2-S) could ever be proposed, under its own protocol and the upload rule. A D arm
  cannot be submitted.

## Boundaries

Train + validation labels only. "Disclosed" counts in CV are the held-out fold's own labels; the test `label_counts` in
`metadata.json` are never read. Task 2 reads only Task 2 files. No upload.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-13 | Protocol frozen and committed | before any code or run |
| 2026-10-13 13:25 | Code committed (`2358271`): `src/flowkit/` and the runner; smoke checks | the new count assignment equals 095's; F0 equals the 014 base SoftVote on one fold |
| 13:26-13:34 | All 8 arms on cv_seeds 2101-2105 (`--all`, production first per seed) | 40 runs `…_102_<arm>_s<seed>` |
| after the runs | `--analyse`, `--test-effect` | `experiments/102_evidence/analysis.json`, `test_effect.json` |

No deviation from the frozen protocol.

### Commands

```bash
.venv/bin/python src/exp102_flowlens_reproduction.py --smoke
.venv/bin/python src/exp102_flowlens_reproduction.py --all
.venv/bin/python src/exp102_flowlens_reproduction.py --analyse
.venv/bin/python src/exp102_flowlens_reproduction.py --test-effect
```

## Results

### Every arm against production (Task 2 CV macro F1, mean of five never-used seeds; production P = 0.759)

| Arm | What | Mean macro F1 | Δ vs P | Verdict on each seed |
|---|---|---:|---:|---|
| F0 | Balanced SoftVote (the claimed base) | 0.740 | −0.019 | WORSE ×5 |
| F1S | + sigmoid calibration | 0.737 | −0.022 | WORSE ×3, INCONCLUSIVE ×2 |
| F1I | + isotonic calibration | 0.744 | −0.015 | WORSE ×3, INCONCLUSIVE ×2 |
| **F2S-D** | **+ sigmoid + disclosed counts (the claim as written)** | **0.723** | **−0.036** | **WORSE ×5** (8-9 wins, 41-42 losses each) |
| F2I-D | + isotonic + disclosed counts | 0.733 | −0.026 | WORSE ×5 |
| F2S-S | + sigmoid + share counts (compliant) | 0.728 | −0.031 | WORSE ×5 |
| F2I-S | + isotonic + share counts (compliant) | 0.739 | −0.021 | WORSE ×2, INCONCLUSIVE ×3 |

### What each ingredient adds (paired, mean of five seeds)

| Step | Δ macro F1 |
|---|---:|
| Claimed base instead of production (F0 vs P): loses 014's facebook/instagram stage | −0.019 |
| Sigmoid calibration (F1S vs F0) | −0.003 |
| Isotonic calibration (F1I vs F0) | +0.004 |
| Disclosed counts (F2S-D vs F1S; F2I-D vs F1I) | −0.014; −0.012 |
| Share counts (F2S-S vs F1S; F2I-S vs F1I) | −0.009; −0.006 |
| **The disclosure itself (F2S-D vs F2S-S)** | **−0.005** |

### Effect on our test predictions (no labels; D arms not built)

| Arm | Test predictions changed vs our submitted Task 2 | Predicted counts (x, mozilla, facebook, instagram, youtube, google) |
|---|---:|---|
| P, F0, F1S, F1I | 0 | 24, 7, 2, 4, 12, 32 |
| F2S-S | 6: x → mozilla 3, x → facebook, x → instagram, x → youtube | 18, 10, 3, 5, 13, 32 |
| F2I-S | 7: x → mozilla 3, x → google, x → facebook, x → instagram, google → youtube | 18, 10, 3, 5, 13, 32 |

Expected test counts from the stratified split (validation × 81/83): x 17.6, mozilla 9.8, facebook 2.9, instagram 4.9, youtube 13.7,
google 32.2. Count assignment moves our Task 2 test file exactly onto them, and every move takes a flow away from **x**, the
class our file over-predicts (24, beyond the CV 95th percentile, 099).

## Verdict

- **Not reproduced on our data.** The claim as written (F2S-D) is WORSE than production on all five never-used seeds
  (−0.036); no variant comes close. Status: rejected.
- **The ingredients do not add up to a gain.** The claimed base lacks our facebook/instagram stage (−0.019), calibration is about
  neutral, count assignment costs 0.006-0.014, and **the disclosed counts are worse than counts from the training shares**
  (−0.005): disclosure carries no extra information in stratified folds, as 095 found.
- **What the claim could explain on the test set, and what it cannot.** On the test set the recipe changes 6-7 of our Task 2
  predictions, all away from our x surplus. If about 2-3 of them were right, Task 2 would move from 0.905 towards their 0.94, so
  the claim is *consistent* with their Task 2 score. Cross-validation says such moves are wrong more often than right (count
  assignment won 9-23 of 50 folds), so we cannot tell skill from a lucky test sample, and only an upload would show it. That upload
  fails our rule (rule v2 WORSE), so it is not made.
- **Task 1 is not covered.** "Task 1 remains unchanged" describes no method; their Task 1 0.94 stays unexplained.
- **Reusable outcome:** `src/flowkit/` (bases, calibration, counts, spec-string pipelines) for 103 and 104.
