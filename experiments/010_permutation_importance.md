---
title: '010: Permutation importance of the champions over 50 folds (TODO #11)'
created: 2026-09-30
creator: sidhantbas
description: Which features and groups do the champions rely on, and does it match Charles's 4-fold run?
experiment:
  id: '010'
  tasks:
  - task1
  - task2
  lever: diagnostic
  status: measured
  verdict: 'Permutation importance over 50 folds: timing is Task 1''s facebook signal; Task 2 relies mostly on upstream columns'
---
# 010: Permutation importance of the champions over 50 folds (TODO #11)

- **Date:** 2026-09-30
- **Question:** Which features and groups do the champions rely on, and does it match Charles's 4-fold run?
- **Status:** done
- **Script:** `src/exp010_permutation.py` (5 shuffles per fold; groups shuffled jointly)
- **Output:** `results/20260930T172154Z_010_permutation/<task>/{raw,summary}.csv`

## Results (mean macro F1 drop when shuffled; folds positive out of 50)

| Task 1 | Drop | Pos. | Task 2 | Drop | Pos. |
|---|---|---|---|---|---|
| packet_size group | 0.234 | 50 | upstream group | 0.453 | 50 |
| upstream group | 0.202 | 50 | volume_direction group | 0.408 | 50 |
| volume_direction group | 0.180 | 50 | packet_size group | 0.315 | 50 |
| timing group | 0.148 | 50 | bytes_up | 0.164 | 50 |
| transport | 0.144 | 50 | mean_pkt_size_up | 0.104 | 49 |
| downstream group | 0.120 | 50 | std_pkt_size_up | 0.093 | 50 |
| mean_iat | 0.060 | 43 | downstream group | 0.065 | 42 |
| min_iat | 0.000 | 2 | burst_count | −0.003 | 5 |

Per class: on task 1, timing mostly carries **Facebook** (timing group costs Facebook 0.40, `mean_iat` alone
0.32); packet size carries mozilla (0.58); transport carries instagram (0.32) and x (0.37).
On task 2, the signal is overwhelmingly upstream.

Matches Charles in direction (packet size and volume first, timing matters only on task 1), with 50
folds instead of 4.

## Decision

Keep timing in task 1 (it is the Facebook signal). `burst_count` on task 2 → tested in 011.
