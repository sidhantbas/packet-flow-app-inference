---
title: "080: Chance that each CV-supported candidate beats production on an 81-flow test set (measurement, CV only)"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Paired resampling of out-of-fold predictions to estimate, for each candidate with five-seed evidence, the probability of a higher Task 1 score than production on a test set of the released test size; used to choose one submission before upload.
source:
  - 040_test_noise.md
  - 062_task1_nonmeta_thresholds.md
  - 066_rest_expert_five_seeds.md
  - 075_rest_expert_plus_nonmeta_thresholds.md
  - 077_fingerprint_expert.md
experiment:
  id: 080
  tasks:
  - task1
  lever: evaluation
  status: measured
  verdict: All CV-supported models agree on 78 of 81 test flows; no new submission justified
---

# 080: Chance to beat production on an 81-flow test set (CV only)

**Status: done 2026-10-09. Method frozen (`72a3577`) before any run.**
**Result: no submittable candidate. All CV-supported models agree on 78 of 81 test flows; the only file that differs from both uploads (062 N2) changes a single flow, which would act as a label probe. Not prepared for upload.** Results are below.
User request 2026-10-09: prepare a submission with a real chance of a higher score, the way 034 produced +3.15.

## Method (frozen)

- Candidates (Task 1; Task 2 unchanged): 062 N2, 065 R (= 066 file), 075 RN2, 077 FR; each has out-of-fold predictions on
  cv_seeds 2026-2030 with production on the same folds (034 champion and the 062 production references).
- One draw: pick a seed and a repeat at random; sample an 81-flow test set from the 330 held-out predictions of that repeat,
  stratified by class with the training class shares × 81 (facebook 3, google 32, instagram 5, mozilla 10, x 18, youtube 13;
  rounded so the total is 81); compute Task 1 macro F1 of candidate and production on the same flows. 20,000 draws, seed 0.
- Reported per candidate: P(candidate > production), mean Δ, P(Δ ≥ +0.02) (a visible jump, about +1 point), P(Δ ≤ −0.02).
- Also, without labels: how many test predictions the candidate's file changes vs the 87.77 file and vs the 066 file.
- Choice rule (frozen): the candidate with the highest P(candidate > production) among those whose test file differs from
  both uploaded files. Before upload, the user confirms that this file becomes the ranked entry on this CV evidence,
  whatever it scores. No test labels, test scores or metadata label counts are used.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Method frozen and committed | `72a3577`, before any run |
| 2026-10-09 | 20,000 paired draws per candidate; test-file comparison for 075 and 062 (test features only) | `experiments/080_evidence_chance.csv` |

Deviation: the per-class draw sizes in the frozen text (google 32, youtube 13) were a hand estimate; the frozen rule
(training share × 81, rounded, total 81) gives google 31, x 18, youtube 14, mozilla 10, instagram 5, facebook 3, which was used.

## Results

| Candidate | P(beat production) | P(tie) | Mean Δ | P(Δ ≥ +0.02) | P(Δ ≤ −0.02) | Test file vs 87.77 | Test file vs 066 |
|---|---:|---:|---:|---:|---:|---|---|
| 065 R (the 066 file) | 0.608 | 0.041 | +0.0059 | 0.195 | 0.056 | 3 flows | identical |
| 075 RN2 | 0.597 | 0.041 | +0.0055 | 0.187 | 0.056 | 3 flows | **identical** |
| 077 FR | 0.540 | 0.312 | +0.0060 | 0.109 | 0.008 | **identical** | 3 flows |
| 062 N2 | 0.335 | 0.568 | +0.0032 | 0.040 | 0.003 | **1 flow** (`flow_000095`) | 2 flows |

All four CV-supported models agree with production on 78 of the 81 test flows; their differences are confined to
`flow_000095`, `flow_000884` and `flow_000906`, the same three flows that separate the two uploaded files.

## Decision

By the frozen choice rule only 062 N2 differs from both uploads, but it changes a single flow relative to the ranked file:
its score change would reveal that flow's label (challenge condition 1; `.mission.md` out of scope: probing the leaderboard).
It is not prepared for upload. No new submission is made; the ranked entry stays the 87.77 file. The remaining room for a
lucky draw among our CV-supported models is three test flows, already covered by the two uploads.
