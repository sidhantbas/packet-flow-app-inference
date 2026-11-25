---
title: '011: Follow-ups: task 2 burst_count, exact-match diagnostic, recording-time diagnostic'
created: 2026-09-30
creator: sidhantbas
experiment:
  id: '011'
  tasks:
  - task2
  lever: diagnostic
  status: measured
  verdict: Task 2 burst_count drop -0.001 (kept); 74% of held-out flows have an exact training twin (96% right); 68% of errors are on never-seen vectors; start_rel alone scores 0.51
---
# 011: Follow-ups: task 2 burst_count, exact-match diagnostic, recording-time diagnostic

- **Date:** 2026-09-30
- **Script:** `src/exp011_followups.py` (A and B); C was run inline (numbers below)
- **Runs:** `results/*_011_t2_drop_burst` (run twice by accident; the second run's reproduction check matches the first)

## A: task 2 without burst_count

Δ −0.001, 5 wins, 9 losses, 36 ties. Inconclusive; kept.

## B: where are the task 2 errors?

Over the 3,300 held-out predictions of the task 2 champion (524 errors, 15.9%):

| Held-out flow's exact 12-column vector | Share | Error rate | Exact-match lookup would fix |
|---|---|---|---|
| seen in the training fold, one label | 54% | 3.9% | 1 |
| seen, several labels | 21% | 14.4% | 7 |
| **never seen** | **26%** | **42.1%** | — |

**68% of task 2 errors are on unseen vectors**, mostly google (117) and youtube (109), then facebook (39),
instagram (32), x (31), mozilla (28). The model already memorises repeated patterns; the gap is
generalisation to new patterns, above all google vs youtube.

## C: how much does recording time explain? (diagnostic only, not adopted)

| | Task 1 | Task 2 |
|---|---|---|
| `start_rel` alone, 1-NN | 0.511 | 0.511 |
| champion + `start_rel` | 0.767 (champion 0.771) | 0.719 (champion 0.736) |

Recording time is not a shortcut to high scores here, and it hurts the task 2 champion.

## Decision

Nothing adopted. Next work targets unseen-pattern generalisation (google vs youtube) and class weighting.
