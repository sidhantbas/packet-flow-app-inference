---
title: "095: The leader's 'disclosed-count analysis', simulated in cross-validation"
created: 2026-10-10
creator: sidhantbas
description: Frozen protocol and results for measuring, in CV only, what calibration plus count-matching (quota) labelling is worth when the class counts of the batch are known (simulated with the held-out fold's own counts) versus estimated from training shares. The test label counts are never read.
source:
  - 043_topk_facebook.md
  - 088_exam_savvy_clerk.md
  - 004_ceilings_ensemble_thresholds.md
experiment:
  id: 095
  tasks:
  - task1
  - task2
  lever: decision
  status: rejected
  verdict: 'The leader''s described method simulated (calibration + count matching; test counts never read): every version below production'
---

# 095: Disclosed-count analysis, simulated in CV

**Status: done 2026-10-10. Protocol frozen (`477685a`) before any code change or run.**
**Verdict: every leader-style arm is WORSE than production (Task 1 −0.07 to −0.09, Task 2 −0.02 to −0.06); calibration hurts facebook; the disclosed counts add almost nothing over training-share counts (+0.005 / −0.004).** Results are below.
Do not edit the frozen sections after execution starts. User 2026-10-10: "can you run an experiment on this style", after the
Final Test Phase leader's method attributes ("Class-balanced prefix-five ensemble with probability calibration and
disclosed-count analysis").

⚠️ **Rules:** the test `label_counts` in `metadata.json` are **never read** (AGENTS.md; `.mission.md` OUT OF SCOPE). In CV the
"disclosed counts" are simulated by the held-out fold's own label counts (train + validation labels only). Arm A2 can therefore
never be applied to the test set under our rules; it only measures what the technique is worth. No submissions are left.

## Frozen arms (each task, its production columns; batch = the held-out fold, about 66 flows)

| Arm | Decision |
|---|---|
| A0 | balanced `SoftVote`, argmax |
| A1 | A0 calibrated: `CalibratedClassifierCV(SoftVote, method="sigmoid", cv=3)`, argmax |
| A2 | A1 probabilities; labels by **quota matching to the held-out fold's true class counts** (simulated disclosure) |
| A3 | A1 probabilities; quota matching to counts **estimated from the training class shares** × batch size (largest remainder) |

Quota matching: choose labels maximising $\sum_i \log p_{i,\hat y_i}$ subject to the class counts, solved exactly as a linear
assignment (`scipy.optimize.linear_sum_assignment`, one slot per expected flow of each class). Nothing tuned.

## Runs and reading

Default CV (5 × 10), cv_seed 2026, through `runlog`, each arm vs the Task 1 / Task 2 production champions. Reported: Δ vs
production, verdict, per-class changes; and A2 vs A1 (value of the counts) and A3 vs A1 (value of quota matching without
disclosure) with `runs.py compare`. Measurement only: no arm is adopted (A2 cannot be; A3 would need its own five-seed protocol).

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-10 | Protocol frozen and committed | before any code change or run |
| 2026-10-10 | Runner committed; smoke test of the quota assignment and prior counts | `exp095_disclosed_counts.py` |
| 2026-10-10 | A0-A3 for both tasks on cv_seed 2026 vs the production champions | runs `…_095_T1_A0` … `…_095_T2_A3` |

No deviation from the frozen protocol. The test label counts were not read.

## Results (cv_seed 2026)

### Against production

| Arm | Task 1 Δ macro F1 | Verdict | Task 2 Δ macro F1 | Verdict |
|---|---:|---|---:|---|
| A0 balanced SoftVote | −0.0679 | WORSE | −0.0182 | WORSE |
| A1 + sigmoid calibration | −0.0941 | WORSE | −0.0622 | WORSE |
| A2 + quota to disclosed (true fold) counts | −0.0775 | WORSE | −0.0558 | WORSE |
| A3 + quota to training-share counts | −0.0824 | WORSE | −0.0517 | WORSE |

### What each ingredient is worth (paired, same folds)

| Comparison | Task 1 Δ | facebook | instagram | Task 2 Δ | facebook | instagram |
|---|---:|---:|---:|---:|---:|---:|
| Calibration (A1 vs A0) | −0.0262 | **−0.137** | +0.001 | −0.0440 (WORSE) | **−0.337** | +0.109 |
| Quota, disclosed counts (A2 vs A1) | +0.0166 | +0.151 | −0.031 | +0.0064 | +0.287 | −0.103 |
| Quota, training shares (A3 vs A1) | +0.0117 | +0.131 | −0.041 | +0.0105 | +0.275 | −0.090 |
| **Disclosure itself (A2 vs A3)** | **+0.0049** (near-miss) | +0.021 | +0.010 | **−0.0041** | +0.011 | −0.013 |

## Verdict

- **The leader-style pipeline, as described, is far weaker than our production in CV** (Task 1 −0.08, Task 2 −0.05 macro F1).
- **Sigmoid calibration hurts the rare class badly** (facebook −0.14 / −0.34): fitted on 2/3 of a fold with about 6 facebook rows,
  it squeezes facebook's probabilities.
- **Count matching repairs facebook** (+0.13 to +0.29) at the cost of the other classes; net +0.006 to +0.017 over the calibrated
  base, never above production.
- **The disclosed counts add almost nothing over counts estimated from the training shares** (+0.005 Task 1, −0.004 Task 2). The
  splits are stratified, so a batch's class counts are already close to the training shares × batch size; the disclosure is
  nearly redundant. The compliant version (A3) is open to us, but it does not beat production; applied on top of production it
  is experiment 043's top-k idea (Task 1 inconclusive, Task 2 worse).
- By this simulation, the "disclosed-count analysis" does not explain a large advantage. The leader's edge, if it is skill and
  not 81-flow luck, must come from something the description does not say.
