---
title: '023: Session context for Task 1'
created: 2026-09-30
creator: sidhantbas
description: Do features of the other flows starting at the same time (±5 s, ±30 s) help Task 1?
experiment:
  id: '023'
  tasks:
  - task1
  lever: features
  status: rejected
  verdict: 'Concurrent-flow context (other flows starting within +-5 / +-30 s): delta -0.010 to +0.002 on 5 seeds; uses capture time, later ruled off-limits (039)'
---
# 023: Session context for Task 1

- **Date:** 2026-09-30
- **Question:** Do features of the other flows starting at the same time (±5 s, ±30 s) help Task 1?
- **Status:** done
- **Script:** `src/exp023_context.py`
- **Runs:** `results/*_023_*`
- **Reference:** Task 1 champion (022 model) on each cv_seed

## Setup

84% of flows start within 5 s of another flow (median gap 1.2 s). For each flow: count of other flows within
±w seconds and their UDP share, median log bytes down/up, median download packet size and median log duration
(all 411 Task 1 flows, feature files only, no labels), for w = 5 and 30 s, added to the 34-column part of the
022 model.

## Results

| cv_seed | Δ | Wins |
|---|---|---|
| 2026 | −0.004 | 22 |
| 2027 | +0.002 | 25 |
| 2028 | −0.002 | 25 |
| 2029 | −0.003 | 21 |
| 2030 | −0.010 | 18 |

## Decision

Reject. Concurrent-flow context adds nothing the per-flow statistics do not already carry.
