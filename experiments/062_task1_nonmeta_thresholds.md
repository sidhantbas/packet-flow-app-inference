---
title: "062: Task 1 F/2 thresholds among the non-Meta apps only"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for applying the 061 threshold rule only between google, mozilla, x and youtube, leaving every Meta decision unchanged.
source:
  - 061_task1_f1_threshold_rule.md
experiment:
  id: '062'
  tasks:
  - task1
  lever: decision
  status: inconclusive
  verdict: 'F/2 thresholds among non-Meta apps only: positive on 5/5 seeds (mean +0.003) but BETTER on 3/5; not adopted'
---

# 062: Task 1 F/2 thresholds among the non-Meta apps only

**Status: done 2026-10-09. Protocol frozen (`988e721`) before any code change or run.**
**Verdict: positive on all five seeds (+0.0008 to +0.0047, mean +0.0030) but BETTER on only three (2026, 2029, 2030); the frozen rule needs all five. Not adopted; no submission candidate under the rule.** Results are below.
Do not edit the frozen sections after execution starts. User reply 2026-10-09: "okay" to "run the YouTube-only test".

## Origin: post hoc

This idea comes from the results of [061](061_task1_f1_threshold_rule.md), not from a frozen measurement: with t = F/2
youtube gained +0.013 (14 wins / 2 losses; youtube → google 91 → 82) while facebook lost −0.018 because flows moved into
facebook (google → facebook 10 → 15). Because the idea was chosen after seeing data, it must pass on **all five seeds**.

## Question

If the F/2 rule may only move flows between the four non-Meta apps (google, mozilla, x, youtube), does Task 1 macro F1 rise?

## Frozen method

Production Task 1 (`models.task1_meta_gate`) with one change in `MetaGate.predict`:

1. `base = cls[q.argmax(axis=1)]` as in production.
2. For flows whose `base` is not facebook or instagram: choose among the four non-Meta classes by `argmax(q_c − t_c)`.
   Flows whose `base` is facebook or instagram are not touched, and no flow can move into facebook or instagram.
3. All later production rules unchanged (whole-run expert for facebook vs instagram, whole-run Meta override, kept
   facebook calls).

t_c = F_c / 2, with F_c the per-class F1 of production on an inner 5-fold stratified CV of the training fold
(shuffle, random_state = model seed), exactly as 061 arm T2. Nothing is searched. One arm: **N2**.

## Frozen decision rules

- N2 vs the Task 1 champion `20261001T173854Z_034_meta_gate` on cv_seed 2026, rule v2.
- If BETTER on 2026: production references and N2 runs on 2027, 2028, 2029, 2030 (each against production on the same
  seed). Pass only with **BETTER on all five**.
- A pass is a submission candidate (Task 1 changes, Task 2 stays), decided on CV before any new score is seen, with the
  user's approval.

## Boundaries

Train+validation only; held-out flows never enter threshold estimation. Production frozen at 5eb9a8b until the user approves.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `988e721`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `4ad7e5c`; zero thresholds reproduce production; no change into or out of Meta |
| 17:28 | N2 on cv_seed 2026 vs champion | run `20261009T172800Z_062_N2`: BETTER |
| 17:29-17:34 | Production references and N2 on 2027-2030 | refs `20261009T172902Z/173025Z/173146Z/173307Z_062_production_s<seed>`; runs `20261009T173011Z/173132Z/173253Z/173412Z_062_N2_s<seed>` |

No deviation from the frozen protocol. Runs carry a `dirty-tree` warning for unrelated local files only (runner committed).

## Results (each seed vs production on the same seed)

| Seed | Δ macro F1 | Wins / losses / ties | Verdict | youtube | x | mozilla | google | facebook / instagram |
|---|---:|---|---|---:|---:|---:|---:|---|
| 2026 | +0.0031 | 14 / 3 / 33 | BETTER | +0.011 | +0.004 | +0.001 | +0.002 | 0 / 0 |
| 2027 | +0.0008 | 8 / 6 / 36 | INCONCLUSIVE | +0.004 | −0.000 | +0.001 | +0.000 | 0 / 0 |
| 2028 | +0.0034 | 11 / 5 / 34 | NEAR-MISS (69%) | +0.009 | +0.005 | +0.005 | +0.001 | 0 / 0 |
| 2029 | +0.0031 | 19 / 4 / 27 | BETTER | +0.009 | +0.005 | +0.002 | +0.002 | 0 / 0 |
| 2030 | +0.0047 | 15 / 2 / 33 | BETTER | +0.015 | +0.004 | +0.005 | +0.004 | 0 / 0 |

Over the five seeds: mean Δ +0.0030; 67 wins / 20 losses (77% of non-tied folds); facebook and instagram never change.

## Interpretation

- The effect is consistent but small: every seed is positive, the gain sits in youtube (+0.004 to +0.015) with smaller gains in
  x, mozilla and google, and Meta is untouched, as designed.
- Its size, +0.003 macro F1, is about +0.15 Task 1 points on average, far below the 81-flow test noise (040).
- The frozen rule (BETTER on all five, because the idea is post hoc) is not met: 2027 is inconclusive and 2028 a near miss.

## Decision

Not adopted under the frozen rule; production unchanged. Adoption would be a documented exception like 028 and 034, which
only the user can decide; given an expected +0.15 points, a submission slot is not justified by this alone.
