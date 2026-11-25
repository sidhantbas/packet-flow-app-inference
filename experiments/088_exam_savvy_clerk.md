---
title: "088: The exam-savvy clerk (batch labelling that maximises expected macro F1)"
created: 2026-10-10
creator: sidhantbas
description: Frozen protocol and results for choosing the labels of a whole batch jointly to maximise expected macro F1 from production's probabilities, starting from production's labels, in both tasks.
source:
  - 043_topk_facebook.md
  - 087_doorman_protects_instagram.md
experiment:
  id: 088
  tasks:
  - task1
  - task2
  lever: decision
  status: rejected
  verdict: 'Expected-macro-F1 batch labelling: Task 1 -0.0015 (23 W / 23 L), Task 2 -0.0051'
---

# 088: The exam-savvy clerk

**Status: done 2026-10-10. Protocol frozen (`f786f5e`) before any code change or run.**
**Verdict: rejected at seed 2026 (Task 1 −0.0015, 23 wins / 23 losses; Task 2 −0.0051, WORSE).** Results are below.
Do not edit the frozen sections after execution starts. User 2026-10-10: "try the exam-savvy clerk" (BACKLOG ready idea 1).

⚠️ **Rules flag (user requirement, 067 amendment):** at test time this method uses the 81 test feature rows **jointly** (no
labels). It must get the user's explicit rules check before any test file is built for submission.

## Idea

Macro F1 is marked per class and does not split into per-flow decisions, so per-flow argmax is not always the best answer for
a whole batch (Lipton et al. 2014; Nan et al. 2012). 043 tried the facebook-only special case (top-k): inconclusive (Task 1),
worse (Task 2). This generalises it to all classes.

## Frozen arm ES (each task)

1. **Probabilities** (as in 043): Task 1, the production 034 base's gate-weighted two-clerks vector $q$; its Meta mass
   $q_\text{fb} + q_\text{ig}$ is split by the whole-run expert's facebook / (facebook + instagram). Task 2, the base SoftVote of
   `models.task2_model`; its Meta mass is split by the facebook/instagram stage's probabilities.
2. **Objective** for labels $\hat y$ of a batch: expected macro F1 by the ratio of expectations,
   $$\text{E-F1}_k = \frac{2\sum_{i:\hat y_i = k} P_{ik}}{\#\{i:\hat y_i = k\} + \sum_i P_{ik}}, \qquad \text{objective} = \tfrac{1}{6}\textstyle\sum_k \text{E-F1}_k .$$
3. **Search:** start from production's labels (Task 1 `models.task1_pair_verifiers`, Task 2 `models.task2_model`); pass over the
   batch in row order, give each flow the label that most increases the objective (only if it rises by more than $10^{-9}$);
   repeat until a pass changes nothing (at most 20 passes). Nothing tuned.
4. **Batch:** in CV the held-out fold (about 66 flows); at test time the 81 test flows.

## Decision rule

- cv_seed 2026 vs production through `runlog` (Task 1 champion `20261009T220447Z_084_ALL`, Task 2 champion); continue only if
  Δ > 0. Then cv_seeds 2027-2030 vs production of the same seed (Task 1 084 ALL runs; Task 2 `014_fi_same_nocw_s2027/_s2028`,
  `085_t2_production_s2029/_s2030`). Pass: rule v2 BETTER on all five seeds.
- A pass becomes a submission candidate only after the rules check above, then the usual file checks and user approval
  (one submission left).

## Boundaries

Train+validation only for model choice; nothing pretrained; Task 2 reads only Task 2 files. Production changes need the user's
approval.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-10 | Protocol frozen and committed | before any code change or run |
| 2026-10-10 | Runner committed; smoke test (a 4-flow, 2-class toy batch keeps its labels) | `exp088_exam_savvy.py` |
| 2026-10-10 | cv_seed 2026, both tasks | `20261010T002217Z_088_T1_ES`, `20261010T002224Z_088_T2_ES`; Δ ≤ 0 in both, so no confirmation seeds |

No deviation from the frozen protocol. No test file was built, so the rules question never arose.

## Results (cv_seed 2026, vs production)

| Task | Δ macro F1 | W / L / T | Verdict | facebook | instagram | google | x | youtube | Flows fixed / broken |
|---|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | −0.0015 | 23 / 23 / 4 | INCONCLUSIVE | −0.028 | +0.025 | −0.007 | −0.008 | +0.008 | 5 / 4 |
| 2 | −0.0051 | 8 / 23 / 19 | WORSE | +0.008 | −0.035 | −0.001 | −0.003 | 0.000 | 1 / 4 |

## Verdict

**Rejected at seed 2026.** The clerk changes many answers (Task 1: 46 of 50 folds differ), but the changes are coin flips:
it wins as many folds as it loses. Expected-F1 reasoning needs well-calibrated probabilities, and ours come from tree ensembles
trained on 264 flows with 9 facebook flows per fold, plus rules (gate, verifiers, facebook keep) that the probabilities do not
describe. In Task 2 the shared Meta openings make it move instagram flows to facebook (instagram −0.035). Same lesson as 004
(multipliers) and 043 (top-k): decision tricks on these probabilities do not beat production. BACKLOG ready idea 1 is closed.
