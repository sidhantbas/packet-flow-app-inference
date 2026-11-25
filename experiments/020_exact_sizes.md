---
title: '020: Exact packet sizes on task 2'
created: 2026-09-30
creator: sidhantbas
description: Does giving the model the exact individual packet sizes (where they are determined) help task 2?
experiment:
  id: '020'
  tasks:
  - task2
  lever: features
  status: rejected
  verdict: 'Exact individual packet sizes where determined: no change; every Task 2 flow has exactly 5 packets'
---
# 020: Exact packet sizes on task 2

- **Date:** 2026-09-30
- **Question:** Does giving the model the exact individual packet sizes (where they are determined) help task 2?
- **Status:** done
- **Script:** `src/exp020_exact_sizes.py`
- **Runs:** `results/*_020_sizes`
- **Reference:** task 2 champion

## Facts established

- Every task 2 flow has exactly 5 packets (330/330). Up-packet counts: 1: 7, 2: 137, 3: 145, 4: 40, 5: 1.
- `std_pkt_size` is the population std (ddof 0): mean ± std gives integer sizes for all 282 two-packet directions
  (ddof 1 does not).
- So in a direction with 1 or 2 packets the sizes are exactly known, and that holds for at least one direction in
  329 of 330 flows.

## Setup

Added `size_{up,down}_{min,max}` = mean ∓ std for directions with ≤ 2 packets (−1 otherwise) to the 12 champion
columns; model = `task2_model`.

## Results (cv_seed 2026)

Δ −0.0005, 8 wins / 4 losses / 38 ties: inconclusive, effectively nothing.

## Interpretation

Most task 2 vectors repeat exactly and are memorised already; for the others, splits on mean and std already
carry the same information.

## Decision

Reject. The packet-count and std facts are recorded in CLAUDE.md for the technical report.
