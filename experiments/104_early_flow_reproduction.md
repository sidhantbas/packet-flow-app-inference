---
title: "104: Reproducing RahmaniJ's Early-Flow Ensemble (92.50) on our data"
created: 2026-10-13
creator: sidhantbas
description: "Frozen reproduction of the third leaderboard entry that describes its method: one ensemble on the first-5-packet features only, the same predictions for both tasks, and constrained assignment to the published class counts. Never-used seeds 2111-2115; components from src/flowkit/."
source:
  - ../docs/reports/leaderboard-method-reproduction.md
  - 102_flowlens_reproduction.md
  - 103_lookup_ensemble_reproduction.md
experiment:
  id: '104'
  tasks: [task1, task2]
  lever: decision
  status: rejected
  verdict: 'Not reproduced: first-5 features only, the same predictions for both tasks and count assignment are WORSE than production on 5 of 5 never-used seeds (Task 1 -0.148, Task 2 -0.064); published counts add +0.001 over training shares; without timing it reproduces our Task 2 test file exactly'
---

# 104: Reproducing Early-Flow Ensemble

**Status: done 2026-10-13. Protocol frozen (`0df473f`) before any code or run.**
**Verdict: not reproduced (WORSE than production on all five never-used seeds in both tasks); the published counts add nothing.** Results are below the protocol. Do not edit the frozen
sections after execution starts. Sid and Charles, 2026-10-13: the last of the three described leaders (102 and 103: not
reproduced).

## The claim (verbatim, leaderboard 2026-10-13)

> **Early-Flow Ensemble** (RahmaniJ): Ensemble classifier using only the released first-5-packet features for early
> application inference. The same early-flow predictions are used for both tasks. Published metadata.json class counts are used
> for constrained assignment. No private labels, external datasets, DNS, SNI, IP addresses, URLs, domains, payloads, or
> prohibited features are used.

Their scores: Task 1 Macro F1 0.92, Task 2 Macro F1 0.92, Total 92.50. Identical Task 1 and Task 2 scores fit one prediction set
for both tasks: the two tasks have the same flows in the same order with the same labels (checked).

## Reading of the claim (unknown details fixed now)

| Part | Our implementation | Assumed because the note does not say |
|---|---|---|
| Ensemble | Balanced `SoftVote` (RF + ExtraTrees + LightGBM), our standard ensemble | Their members and class weights |
| First-5-packet features only | All 17 released first-5-packet columns (timing included); a second arm without timing (12 columns, our Task 2 production's input) | Which columns |
| Same predictions for both tasks | The Task 2 file's features for each flow, also for Task 1 (allowed: Task 2 data may feed Task 1) | — |
| Constrained assignment with published counts | Linear assignment to the batch's class counts, as 102 and 103 | Exact method |

## Frozen design (each task)

| Arm | Features | Labels | Usable in a submission |
|---|---|---|:---:|
| P | Production (Task 1 `task1_cross_task`, Task 2 `task2_model`) | its own | — |
| E0 | 17 first-5 columns | argmax | ✅ |
| E0N | 12 first-5 columns without timing | argmax | ✅ |
| E1 | 17 first-5 columns | assignment to the held-out fold's **true** counts (the claim; simulated disclosure, measurement only) | ❌ |
| E1S | 17 first-5 columns | assignment to training-share counts (compliant) | ✅ |

- **Folds:** repeated stratified 5 × 10 at cv_seeds **2111-2115** (0 runs in `results/`); model seed = fold index. Each arm runs on
  Task 2 and on Task 1. Because the folds and the inputs are the same, each E arm must score identically in both tasks; this is
  checked, and it tests "the same predictions for both tasks".
- **Test-set effect (no labels):** E0, E0N and E1S fitted on train + validation and applied to the 81 test flows; changed
  predictions against our submitted Task 1 and Task 2 files. E1 needs the test `label_counts` and is not built.
- **Smoke check:** on one fold, E0's Task 1 and Task 2 predictions are identical.

## Decision rule

- **Claim reproduced on our data (per task):** E1 is rule v2 BETTER than P on all five seeds.
- **Compliant candidate (per task):** E0, E0N or E1S rule v2 BETTER than P on all five seeds, then proposed separately (user
  decision and the upload rule).
- **Ingredients:** timing (E0 − E0N), counts with disclosure (E1 − E0), counts without (E1S − E0), disclosure itself (E1 − E1S).

## Boundaries

Train + validation labels only; "disclosed" counts are the held-out fold's own labels; the test `label_counts` are never read.
The Task 2 arms read only Task 2 files; the Task 1 arms read the Task 2 file (allowed and disclosed, as 022). No upload.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-13 | Protocol frozen and committed | before any code or run |
| 2026-10-13 17:48 | Runner committed (`623d696`); smoke checks | Task 1 arms see exactly the Task 2 file's columns; E0 predictions identical for both tasks on one fold |
| 17:49-17:53 | All 5 arms × 2 tasks × cv_seeds 2111-2115 (`--all`) | 50 runs `…_104_<T1|T2>_<arm>_s<seed>`, no errors |
| after the runs | `--analyse`, `--test-effect` | `experiments/104_evidence/analysis.json`, `test_effect.json` |

No deviation from the frozen protocol.

### Commands

```bash
.venv/bin/python src/exp104_early_flow_reproduction.py --smoke
.venv/bin/python src/exp104_early_flow_reproduction.py --all
.venv/bin/python src/exp104_early_flow_reproduction.py --analyse
.venv/bin/python src/exp104_early_flow_reproduction.py --test-effect
```

## Results

### Every arm (CV macro F1, mean of five never-used seeds)

| Arm | Task 1 | Δ vs P | Task 2 | Δ vs P |
|---|---:|---:|---:|---:|
| P production | **0.849** | — | **0.765** | — |
| E0 first-5, 17 columns | 0.699 | −0.150 | 0.699 | −0.065 |
| E0N first-5, 12 columns without timing | 0.746 | −0.103 | 0.746 | −0.019 |
| **E1 17 columns + true held-out counts (the claim)** | 0.701 | **−0.148** | 0.701 | **−0.064** |
| E1S 17 columns + training-share counts (compliant) | 0.700 | −0.149 | 0.700 | −0.064 |

Every E arm is WORSE than production on all five seeds in both tasks. **Each E arm scores identically in Task 1 and Task 2 on every
fold** (checked), confirming that one prediction set serves both tasks.

### What each step adds (paired, mean of five seeds; identical in both tasks)

| Step | Δ macro F1 |
|---|---:|
| Timing columns in the opening (E0 − E0N) | −0.046 (as 007 found) |
| Count assignment, true counts (E1 − E0) | +0.002 |
| Count assignment, training shares (E1S − E0) | +0.001 |
| The disclosure itself (E1 − E1S) | +0.001 |

### Effect on our test predictions (no labels)

| Arm | Changes vs our Task 1 file | Changes vs our Task 2 file |
|---|---:|---:|
| E0 | 11 | 4 |
| E0N | 7 | **0** (its predictions are our Task 2 file, the 014 base already agreeing with its stage on the test set) |
| E1S | 14 | 11 (x → mozilla 3, x → google, x → youtube, x → instagram, google ↔ youtube 3, youtube → instagram, instagram → facebook) |

## Verdict

- **Not reproduced on our data.** The claim (E1) is WORSE than production on all five never-used seeds: Task 1 −0.148, Task 2
  −0.064. Status: rejected.
- **The structure checks out; the numbers do not.** One prediction set for both tasks behaves exactly as described. But
  first-5-packet features alone lose 0.10-0.15 in Task 1 against our full-flow model, and the published counts add almost nothing
  (+0.001 over training-share counts).
- **What their 0.92 / 0.92 suggests about the test set.** Without timing, their method reproduces our own Task 2 test file
  exactly, and that file scored 0.905 on the test labels, which both tasks share. So a prefix-only set scores about 0.905 on
  Task 1's test too, above our Task 1 model's 0.840, although cross-validation ranks the full-flow model 0.10 higher. Their extra
  +0.015 would then come from count assignment, which moves 11 of our test predictions, mostly off our x surplus. Acting on this
  (prefix predictions for Task 1, or counts) would mean choosing by test score; CV says the opposite.
- **All three described leaders are now reproduced** (102, 103, 104): none beats our production in cross-validation. Next: the
  deduplication of their techniques and ours, and the decision.
