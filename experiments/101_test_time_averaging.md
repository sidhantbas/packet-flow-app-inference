---
title: "101: Does test-time averaging over small time-scale changes improve Task 1?"
created: 2026-10-12
creator: sidhantbas
description: "Frozen test of test-time averaging for Task 1: production (100) predicts each held-out flow ten more times with all timing columns scaled by fixed factors (about ±15%), and the majority label wins. Never-used cv_seeds 2051-2055; rule v2 on all five."
source:
  - 100_cross_task_meta_rescue.md
  - 093_data_limited_analysis.md
  - 094_variance_reduction.md
experiment:
  id: '101'
  tasks: [task1]
  lever: decision
  status: rejected
  verdict: 'No effect: mean +0.0008 on never-used seeds 2051-2055 (7 W / 3 L / 240 T, no seed BETTER); 10 of 1,650 held-out predictions change; test predictions identical to upload 8'
---

# 101: Test-time averaging for Task 1

**Status: done 2026-10-12. Protocol frozen (`88e01b0`) before any code or run.**
**Verdict: rejected, no effect (10 of 1,650 held-out predictions change; the test file would equal upload 8).** Results are below the protocol. Do not edit the frozen
sections after execution starts. User 2026-10-12, after the brainstorm (BACKLOG ready idea 1): "yes run it".

## Question and evidence

Production's tree experts decide on hard thresholds, and timing is the noisiest part of a flow (network jitter). Does predicting
each flow several times with its timing slightly faster or slower, and taking the majority label, fix close calls?

- **Untried:** 094 averaged over model seeds (no change). Nothing so far averaged over the input.
- **Expected size: small.** Most errors are confident (093 §7: 19 of 162 Task 1 errors are close calls), and timing matters
  mainly for facebook (010/011).
- **Upload condition:** a file is upload-eligible only under the AGENTS.md upload rule: rule v2 on never-used seeds **and** at
  least 3 changed test predictions against every earlier upload.

## Frozen design

- **REF:** production `models.task1_cross_task` (100), features `cv.TASK_FEATURES["task1_static"]`.
- **TTA:** REF fitted identically, then predicted 11 times per flow: once unchanged and once for each of 10 time-scale factors
  $s_k = e^{0.1\,z_k}$, where $z_k$ are the standard normal quantiles at $(k - 0.5)/10$, $k = 1, \dots, 10$ (factors 0.848 to
  1.179). Each copy multiplies all ten timing columns (`duration`, `mean_iat`, `std_iat`, `min_iat`, `max_iat` and their
  `p5_` versions) by $s_k$. The flow's identities and the derived rest-of-flow timing scale consistently. Opening sizes, counts,
  `burst_count`, the exact-opening override and the inner Task 2 model are unchanged.
- **Decision per flow:** the label with the most of the 11 votes. On a tie, the unchanged prediction wins if it is tied;
  otherwise the alphabetically first tied label. Nothing is tuned: σ = 0.1 and 10 copies are fixed here.
- **Folds:** repeated stratified 5 × 10 at cv_seeds 2051, 2052, 2053, 2054, 2055 (0 runs in `index.jsonl`); model seed = fold
  index.
- **Smoke check:** with all factors set to 1, TTA's predictions equal REF's on one fold.

## Decision rule

- **Pass:** TTA is rule v2 BETTER than REF on all five seeds.
- **On a pass:** build the Task 1 test file (test features only) and count the changed test predictions against every earlier
  upload (uploads 1-8). It is upload-eligible only if the upload rule holds. Adoption in production and any upload need the
  user's approval.
- **Otherwise:** not adopted; production is unchanged.

## Boundaries

Train + validation labels only; test features only for the file. Task 2 is unchanged and reads only its own files. No test labels,
no `label_counts`, no capture time or order. Production is unchanged.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-12 | Protocol frozen and committed | before any code or run |
| 2026-10-12 16:25 | Runner committed (`ce19549`); smoke check | factors all 1 reproduce production on fold 0; fold 0 with the real factors: 3 of 66 flows get mixed votes, 0 labels change |
| 16:25-16:31 | REF and TTA on cv_seeds 2051-2055 | runs `…_101_REF_sN`, `…_101_TTA_sN` |
| after the runs | Test predictions built for information, **outside the protocol** (which builds a file only on a pass) | `experiments/101_evidence/test_changes.json` |

No deviation from the frozen protocol.

## Results (TTA vs REF, verdicts from each run's `report.md`)

| Seed | Δ macro F1 | W / L / T | Verdict | Predictions changed (fixed / broken) |
|---|---:|---|---|---|
| 2051 | −0.0002 | 0 / 1 / 49 | INCONCLUSIVE | 1 (0 / 1) |
| 2052 | +0.0029 | 4 / 1 / 45 | INCONCLUSIVE | 5 (3 / 1) |
| 2053 | 0.0000 | 0 / 0 / 50 | INCONCLUSIVE | 0 |
| 2054 | +0.0004 | 2 / 0 / 48 | INCONCLUSIVE | 2 (1 / 0) |
| 2055 | +0.0010 | 1 / 1 / 48 | INCONCLUSIVE | 2 (1 / 1) |

Mean Δ +0.0008; 7 wins, 3 losses, 240 ties. Across the five seeds TTA changes 10 of 1,650 held-out predictions: 5 fixed, 3
broken, 2 wrong either way. **On the test set it changes no prediction** (identical to upload 8), so it could not produce an
upload-eligible file or change the score.

## Verdict

**Rejected: no effect.** No seed is BETTER (the rule needs all five); every seed has fewer than 10 non-tied folds. Production's
labels are stable under ±15% timing changes: its errors are confident, as 093 found. Production is unchanged.
