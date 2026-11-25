---
title: '043: Push borderline flows to Facebook (top-k and pair threshold)'
created: 2026-10-07
creator: sidhantbas
description: Does labelling more borderline flows as facebook, on top of the frozen production models, beat production under rule v2?
experiment:
  id: '043'
  tasks:
  - task1
  - task2
  lever: decision
  status: rejected
  verdict: 'Push borderline flows to facebook (top-k from the training share, pair threshold): Task 2 worse (instagram -0.08), Task 1 inconclusive'
---
# 043: Push borderline flows to Facebook (top-k and pair threshold)

- **Date:** 2026-10-07
- **Question:** Does labelling more borderline flows as facebook, on top of the frozen production models, beat production under rule v2?
- **Status:** done
- **Script:** `src/exp043_topk_facebook.py` (`PushFacebook` wraps `models.TASK_MODELS`; production code unchanged)
- **Runs:** `results/20261007T113956Z_043_topk`, `results/20261007T114012Z_043_pairthr` (cv_seed 2026, both tasks)
- **Reference:** production champions `20261001T173854Z_034_meta_gate` (Task 1), `20260930T173836Z_014_fi_same_nocw` (Task 2)

## Hypothesis

Macro F1 weights Facebook (11 labelled flows) as much as Google (131), so one more Facebook hit is worth far more than one wrong
call on a large class (BACKLOG.md Ready #1). Facebook flows that rank high but are not the top class could be rescued.

Seen before choosing the second variant: a scratchpad diagnostic on 2026-10-06 (pair-only SoftVote on the 30 labelled Meta flows,
not a recorded run) showed 5 Task 1 Facebook flows at P(facebook) 0.3–0.4 and an in-sample best threshold of ~0.25 (+1 point on
Task 1); on Task 2, 3 Facebook flows have identical Instagram twins. The threshold below is set by a class-share rule, not read off
that curve.

## Setup

Settings fixed before running. Both variants only **add** facebook labels; production's own facebook calls stay.
Facebook score $= P(\text{Meta}) \times P(\text{fb} \mid \text{Meta})$ from the parts production already uses:

| | $P(\text{Meta})$ | $P(\text{fb} \mid \text{Meta})$ |
|---|---|---|
| Task 1 (`MetaGate`) | the Meta-vs-rest gate | whole-run expert, facebook / (facebook + instagram) |
| Task 2 (`PairSpecialist`) | base SoftVote, facebook + instagram | facebook/instagram stage |

| Variant | Rule |
|---|---|
| `topk` | $k = \text{round}(\text{training facebook share} \times \text{flows predicted})$ (= 2 per CV fold, would be 3 on test). If production predicts fewer than $k$ facebook flows, the highest-scoring other flows become facebook until there are $k$. |
| `pairthr` | Flows production calls facebook or instagram become facebook if $P(\text{fb} \mid \text{Meta}) \ge t$, with $t$ = facebook share among the training fold's Meta flows (≈ 0.37 instead of production's 0.5). |

Default CV (5 × 10, cv_seed 2026), paired with production on identical folds. Plan: confirm on 2027–2030 only after a pass.
Smoke test on one fold: predictions identical to production except the added facebook labels.

## Results

| Variant | Task | Macro F1 (prod.) | Δ | W / L / T | Facebook F1 Δ | Instagram F1 Δ | Verdict |
|---|---|---|---|---|---|---|---|
| `topk` | 1 | 0.8340 (0.8277) | +0.0063 | 7 / 7 / 36 | +0.034 (7 / 6) | +0.004 | INCONCLUSIVE |
| `topk` | 2 | 0.7436 (0.7544) | −0.0108 | 6 / 19 / 25 | +0.018 (5 / 10) | −0.082 (3 / 21) | WORSE |
| `pairthr` | 1 | 0.8290 (0.8277) | +0.0013 | 4 / 2 / 44 | +0.017 (3 / 3) | −0.009 | INCONCLUSIVE |
| `pairthr` | 2 | 0.7353 (0.7544) | −0.0191 | 0 / 18 / 32 | −0.036 (0 / 14) | −0.079 (0 / 18) | WORSE |

Flows (majority vote over the 10 repeats):

- **Task 1 `topk`:** fixed 1 (flow_001145, facebook, was instagram), broken 0. Facebook → instagram 22 → 16, but instagram →
  facebook 26 → 29, google → facebook 10 → 12, x → facebook 1 → 3.
- **Task 1 `pairthr`:** fixed 2 (flow_001145; flow_000240 by a majority-vote tie shift), broken 0. Changes only 6 of 50 folds.
- **Task 2 `topk`:** broken 2 (flow_000379 instagram, flow_000535 x, both now facebook); instagram → facebook 27 → 53.
- **Task 2 `pairthr`:** broken 3 (flow_000379, 000604, 001323, all instagram, now facebook); instagram → facebook 27 → 47.

## Caveats

- Task 1 `topk` is the only positive result, and it is a coin flip at fold level (7 wins, 7 losses): the mean comes from a few
  folds where one rescued Facebook flow lifts the Facebook F1 a lot. Facebook fold noise (std ~0.28) dominates.
- The diagnostic's ~+1 point on Task 1 does not survive inside production: the Meta gate and the keep-facebook rule already move most
  borderline flows, which matches 031 (decision-rule headroom ≤ 3 errors on Task 1).
- On Task 2 the extra facebook labels land on Instagram flows with the same opening as Facebook flows; the duplicate-vector ceiling
  (004) makes that unavoidable.
- `topk` makes a flow's label depend on the other flows in the batch, which conflicts with Task 2's real-time framing.

## Decision

**Rejected on Task 2** (both variants WORSE, every Instagram fold that changed got worse). **Not adopted on Task 1** (both
INCONCLUSIVE under rule v2: 7/7 and 4/2 non-tied folds). As fixed in advance, no confirmation seeds were run. Production stays
frozen; no test predictions change.

## Next

- Facebook decision rules on the given data look exhausted (031, 034, 043). BACKLOG #4 (expected-macro-F1 labelling) generalises
  `topk` and would face the same noise; lower its chance.
- 044 (Facebook sub-types) and 045 (SMOTE) remain, both with low prior.
- For the report: evidence that Facebook is at its ceiling on the released data.
