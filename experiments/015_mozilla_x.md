---
title: '015: Task 2 mozilla → x errors'
created: 2026-09-30
creator: sidhantbas
description: Can a mozilla/x specialist that sees timing undo the mozilla → x increase (33 → 50) from dropping timing in 007?
experiment:
  id: '015'
  tasks:
  - task2
  lever: hierarchy
  status: rejected
  verdict: 'Timing-aware mozilla/x specialist: pair AUC 0.945 -> 0.976 but delta ~0; it only swaps errors inside the pair'
---
# 015: Task 2 mozilla → x errors

- **Date:** 2026-09-30
- **Question:** Can a mozilla/x specialist that sees timing undo the mozilla → x increase (33 → 50) from dropping timing in 007?
- **Status:** done
- **Script:** `src/exp015_mozilla_x.py` (`models.MultiSpecialist`: base + several pair specialists)
- **Runs:** `results/*_015_*` (4)
- **Reference:** task 2 champion `20260930T173836Z_014_fi_same_nocw`

## Hypothesis

A mozilla-vs-x model trained on those two classes only separates them better with timing:

| Columns | Weights | AUC | Balanced accuracy |
|---|---|---|---|
| 12 champion (no timing) | balanced / none | 0.945 / 0.943 | 0.905 / 0.912 |
| all 17 (with timing) | balanced / none | 0.976 / 0.976 | 0.914 / 0.923 |

(41 mozilla, 73 x; 5-fold × 3.) So keep the timing-free base and the fb/ig specialist, and add a mozilla/x
specialist on all 17 columns.

## Results (task 2, vs champion, cv_seed 2026)

| Variant | Δ | W / L / T | mozilla → x | x → mozilla |
|---|---|---|---|---|
| check (fb/ig only, `MultiSpecialist`) | 0 | 0/0/50, identical | 50 | 16 |
| mx_timing_cw | −0.002 | 17/17/16 | 38 | 36 |
| mx_timing_nocw | −0.001 | 18/18/14 | 39 | 34 |
| mx_base_cw (no timing, control) | 0 | 0/0/50 | 50 | 16 |

Flows fixed: flow_000517, flow_000833, flow_000976 (mozilla, were x), exactly the three 007 broke. An equal
number of x flows break the other way.

## Interpretation

Timing raises the pair's AUC but hardly its balanced accuracy (+0.01). At the decision boundary it moves errors
from one side of the pair to the other instead of removing them. The mozilla → x increase after 007 was a shift
inside the pair, not a net loss. The control shows that a second stage on the same columns adds nothing: the
base model already makes the same pairwise decision.

## Decision

Reject. Task 2 champion unchanged. `MultiSpecialist` stays in `models.py` (reproduces the champion exactly)
for future multi-pair tests.

## Next

Smoother models for never-seen patterns (TODO round 2).
