---
title: '034: Hierarchical Meta gate on the Task 1 two-clerks model'
created: 2026-10-01
creator: sidhantbas
description: Does deciding "Meta or not?" first (learned from all 30 Meta flows) and then facebook vs instagram improve
experiment:
  id: '034'
  tasks:
  - task1
  lever: hierarchy
  status: adopted
  verdict: 'Meta gate (Meta vs rest first, then facebook vs instagram by the whole-flow expert): 0.828, facebook 0.59 -> 0.67, instagram -0.029; adopted as a decision-theoretic exception'
  production: Task 1 Meta gate
---
# 034: Hierarchical Meta gate on the Task 1 two-clerks model

- **Date:** 2026-10-01
- **Question:** Does deciding "Meta or not?" first (learned from all 30 Meta flows) and then facebook vs instagram improve
  Task 1, especially facebook?
- **Status:** done; **adopted for Task 1 on 2026-10-01 as a deliberate, decision-theoretic exception (user decision)**
- **Script:** `src/exp034_meta_gate.py`; `models.MetaGate`
- **Runs:** `results/*_034_*`
- **Reference:** Task 1 champion `20261001T163334Z_028_two_clerks_avg_meta_whole` (0.8172)

## Motivation (Meta data-flow analysis, 2026-10-01)

Facebook and Instagram share their QUIC openings; their bodies differ (Instagram heavy, Facebook light/slow or brief). Short
Facebook QUIC fetches are called google over the whole flow (flow_001145 0/10, flow_000799 3/10 correct) although their
opening is Meta-like. A gate learned from all 30 Meta flows uses three times the examples of facebook alone.

## Setup (fixed before running)

Gate: balanced SoftVote, Meta vs rest, all 34 Task 1 columns. Two-clerks probabilities re-weighted to agree with the gate,
p'(c) = g * p(c)/p(Meta) for Meta classes, (1 - g) * p(c)/p(rest) otherwise; if argmax is Meta, the whole-run expert's
facebook vs instagram probability decides; then the unchanged two-clerks rules (whole-run label when it says Meta;
facebook calls of the 17-column SoftVote kept).

## Results (cv_seed 2026)

| | Δ vs champion | W / L / T |
|---|---|---|
| Macro F1 0.8277 | +0.0105 | 15 / 11 / 24, inconclusive (58% of non-tied) |
| facebook | **+0.082** | 14 / 2 |
| instagram | -0.029 | 1 / 16 |
| google, x, youtube, mozilla | +0.001 to +0.005 | |

Majority-vote flows: fixed flow_000799 (facebook, was google); broken flow_000240 (google, now instagram).

## Interpretation

The gate does what it was built for: facebook F1 rises from 0.59 to 0.67 because Meta-looking flows are no longer lost to
google. It costs Instagram: once the gate says Meta, some Instagram flows go to facebook in the facebook/instagram choice.
Net gain +0.01, but with too few winning folds to pass the rule.

## Decision

Not adopted; no confirmation run (planned only after a pass). A variant that protects Instagram would be designed after
seeing these results and would need fresh seeds to be credible.

## 034b: "rescue-only" follow-up (designed after seeing 034; held to cv_seeds 2026-2030)

Intended to stop the gate from re-deciding flows already in Meta. It turned out to be **identical** to 034 at every
fold: the full gate never re-decided those flows, because the two-clerks rule restores the whole-run label whenever the
whole-run expert says facebook/instagram. The earlier diagnosis (Instagram loss from re-deciding Meta flows) was wrong.

What the gate actually changes (cv_seed 2026): 40 held-out predictions, all moved from outside Meta into Meta. True
facebook 23 (14 -> facebook correct, 9 -> instagram), google 10 (4 -> facebook, 6 -> instagram), instagram 4 (1 correct),
youtube 3 (-> instagram). Facebook recall 0.591 -> 0.718 (precision 0.670 -> 0.669); instagram recall 0.747 -> 0.753,
precision 0.811 -> 0.737. The Instagram loss is precision: rescued facebook flows and some google/youtube flows labelled
instagram.

| cv_seed | Δ vs two clerks | W / L / T |
|---|---|---|
| 2026 | +0.0105 | 15 / 11 / 24 |
| 2027 | +0.0095 | 15 / 18 / 17 |
| 2028 | +0.0070 | 13 / 14 / 23 |
| 2029 | +0.0049 | 11 / 16 / 23 |
| 2030 | +0.0006 | 10 / 16 / 24 |

Positive mean on all five seeds but fewer winning than losing folds on four of them. Not adopted. Further tweaks (for
example labelling every rescued flow facebook) would be tuned on these same results; stopped here.

## Adoption (2026-10-01, user decision; deliberate exception)

Reasoning (made before rebuilding the submission and without test labels): with the full model trained on all 330 labelled
flows, the gate changes only 2 of the 81 Task 1 test flows (flow_000826, flow_001187: google -> facebook; short UDP flows,
0.2-0.3 s, 27-35 packets, like the training facebook fetches flow_000809/flow_001168). In CV, flows the gate moves to
facebook are facebook 14 times out of 21; macro F1 weights a facebook flow about 12 times a google flow, so each flip has a
positive expected value. The CV cost (instagram precision) comes from flows moved to instagram, which does not occur on
test. Caveat: fold-level evidence is weak (positive mean on all 5 seeds, more losing than winning folds on 4).

- `models.TASK_MODELS["task1_static"] = task1_meta_gate` (`MetaGate()` on the two-clerks model).
- `034_production_check` reproduces `20261001T173854Z_034_meta_gate` on all 50 folds; Task 2 unchanged.
- Task 1 champion: `20261001T173854Z_034_meta_gate` (0.8277).
- Rebuilt submission: vs the two-clerks file 2 Task 1 changes (above); vs the 84.62 file 8 Task 1 changes; Task 2 identical.
  Not submitted.
- Official-scorer pipeline check (train only -> validation): Task 1 0.852 (two clerks 0.766), total 81.5 (77.2). Single split
  with 3 facebook flows: consistent with the gate's purpose, not used as evidence.
