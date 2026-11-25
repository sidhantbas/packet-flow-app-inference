---
title: "058: Captured flows as a never-predicted \"other\" class in Task 1"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for adding captured flows as an extra training class whose predictions fall back to production.
source:
  - 057_capture_meta_pair.md
  - 056_capture_augmentation.md
experiment:
  id: 058
  tasks:
  - task1
  lever: data
  status: rejected
  verdict: 'Captured flows as a never-predicted ''other'' class: -0.0003 / -0.0077; the damage goes but so does any gain'
---

# 058: Captured flows as a never-predicted "other" class in Task 1

**Status: done 2026-10-09. Protocol frozen (`9cec6f4`) before any code change or run.**
**Verdict: both arms INCONCLUSIVE with no gain (O15 −0.0003, O149 −0.0077). Captured flows have no training use (final for this project).** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "yes try the other class test as well";
the user's gate override of 056 applies.

## Origin: post hoc

This idea comes from a side effect seen **after** the 056 and 057 results, not from a frozen measurement: adding
captured rows improved non-Meta classes (057 D10: mozilla +0.023 with 14 wins / 0 losses, youtube +0.013, google +0.004;
056: youtube → google 91 → 68) while the facebook label of those rows destroyed facebook. Because the idea was chosen
after seeing data, the full five-seed rule v2 is required, with no exception.

## Question

If captured flows enter training as a separate class "other" (never output), do the non-Meta gains remain without the
facebook damage, so that Task 1 macro F1 rises?

## Frozen arms

| Arm | Rows labelled `other` in each training fold |
|---|---|
| **O15** | a random 10% of the captured facebook and instagram rows (6 + 9; new draw per fold, seed = fold index), as 057 D10 |
| **O149** | all 149 captured facebook and instagram rows (as 056 FI) |

Captured rows: exactly the 056 rows (`data/captures/056-augmentation/`). Model: production `task1_meta_gate` (all parts
unchanged) fitted on the original rows plus the `other` rows. In MetaGate's Meta-vs-rest gate, `other` counts as rest.
**Fallback:** every held-out flow the augmented model labels `other` gets the prediction of production fitted on the
original rows of the same fold (same seed). So the output is always one of the six apps.

## Frozen decision rules

- Each arm vs the Task 1 champion `20261001T173854Z_034_meta_gate` on cv_seed 2026, rule v2.
- An arm passes only with BETTER on 2026 **and** on 2027, 2028, 2029, 2030 (each against production re-run on the same
  seed). Confirmation seeds only for an arm that passes on 2026.
- Report the share of held-out predictions that fell back, and per-class Δ.
- No arm passes on 2026: captured flows have no training use (final for this project).
- A pass is a candidate only: adoption needs the user's approval and a report entry (outside data, Task 1 only).

## Boundaries

Task 1 only. Original data: train+validation only. Held-out flows always original. Production frozen at 5eb9a8b.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `9cec6f4`, before any code change or run |
| 2026-10-09 | Runner committed; smoke test on one split | `fe532b9`; augmented model has 7 classes, output only the six apps; 1 and 3 of 165 predictions fell back |
| 13:42 | O15 and O149 on cv_seed 2026 | runs `20261009T134225Z_058_O15`, `20261009T134251Z_058_O149` |

No deviation from the frozen protocol. No arm passed on 2026, so no confirmation seeds were run (frozen rule).

## Results

| Arm | Macro F1 | Δ vs production (0.8277) | Wins / losses / ties | Fallback (held-out predictions) | Verdict |
|---|---:|---:|---|---:|---|
| O15 | 0.8274 | −0.0003 | 21 / 17 / 12 | 36 of 3,300 (1.1%) | INCONCLUSIVE |
| O149 | 0.8200 | −0.0077 | 20 / 23 / 7 | 60 of 3,300 (1.8%) | INCONCLUSIVE |

| Class | O15 Δ F1 | O149 Δ F1 | 057 D10 Δ F1 (for comparison) |
|---|---:|---:|---:|
| facebook | −0.033 | −0.047 | −0.171 |
| instagram | +0.025 | +0.024 | −0.024 |
| google | +0.000 | −0.001 | +0.004 |
| mozilla | +0.007 | −0.006 | +0.023 |
| x | +0.001 | −0.010 | −0.002 |
| youtube | −0.002 | −0.006 | +0.013 |

Confusion changes (50 folds summed): google → instagram 19 → 11 (O15) and 19 → 10 (O149); google → facebook 10 → 17 / 15.

## Interpretation

- The `other` label removes almost all of the 056/057 damage (facebook −0.03 to −0.05 instead of −0.17 to −0.38).
- The non-Meta gains that motivated the test do not appear: mozilla +0.007 / −0.006, youtube −0.002 / −0.006. The post-hoc
  side effect in 057 D10 appears tied to the facebook/instagram labels, not to the rows' position alone (not proven).
- Small instagram gain (+0.024, fewer google → instagram), offset by facebook. Net effect about zero.

## Decision

Neither arm passes. By the frozen rule, captured flows have no training use in this project. Production unchanged
(5eb9a8b). The capture work goes into the technical report as an out-of-distribution study and disclosed outside data
that was tested and not used.
