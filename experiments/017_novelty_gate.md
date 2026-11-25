---
title: '017: Novelty gating on task 2'
created: 2026-09-30
creator: sidhantbas
description: Does using smooth members only for flows whose exact vector is new beat adding them everywhere (016)?
experiment:
  id: '017'
  tasks:
  - task2
  lever: model
  status: inconclusive
  verdict: 'Novelty gating (smooth members only for unseen vectors) equals 016 exactly: +0.006, near-miss'
---
# 017: Novelty gating on task 2

- **Date:** 2026-09-30
- **Question:** Does using smooth members only for flows whose exact vector is new beat adding them everywhere (016)?
- **Status:** done
- **Script:** `src/exp017_novelty_gate.py` (`models.NoveltyGate`; `MultiSpecialist(base_factory=...)`)
- **Runs:** `results/*_017_*` (4)
- **Reference:** task 2 champion `20260930T173836Z_014_fi_same_nocw`

## Setup

Task 2 only: task 1 has no repeated vectors (004), so every task 1 flow is new and the gate reduces to 016.
All members are fitted once; seen flows get the trees' mean proba, new flows the mean over trees + smooth members.
The fb/ig specialist stays on top. `check` (no smooth members) ties the champion on every fold.

## Results (task 2, cv_seed 2026)

| Variant | Δ | Verdict | Error: seen / unseen | Same variant ungated (016) |
|---|---|---|---|---|
| check | 0 | identical | 0.063 / 0.415 | — |
| gate_lr_knn | +0.006 | NEAR-MISS | 0.063 / 0.398 | +0.006, 0.062 / 0.398 |
| gate_lr | +0.001 | inconclusive | 0.063 / 0.410 | +0.001, 0.063 / 0.410 |
| gate_knn | −0.001 | inconclusive | 0.063 / 0.408 | −0.000, 0.062 / 0.408 |

## Interpretation

Gating changes nothing. In 016 the trees already dominated the averaged probabilities on seen vectors, so the
smooth members only ever mattered on new ones. The gain from logistic regression + kNN stays at +0.006, short
of rule v2.

## Decision

Reject. Champion unchanged. `NoveltyGate` stays in `models.py`.

## Next

The model-side ideas from round 2 are used up. Take stock: write the findings up for Charles (007, 014 are the
two adopted gains) and plan round 3.
