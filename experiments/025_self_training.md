---
title: '025: Self-training with unlabelled flows'
created: 2026-10-01
creator: sidhantbas
description: Does one round of self-training on unlabelled flows (held-out fold + test features) help either task?
experiment:
  id: '025'
  tasks:
  - task1
  - task2
  lever: data
  status: rejected
  verdict: 'Self-training on held-out + test features (p >= 0.9): Task 1 -0.006, Task 2 0.000; confident pseudo-labels were already right'
---
# 025: Self-training with unlabelled flows

- **Date:** 2026-10-01
- **Question:** Does one round of self-training on unlabelled flows (held-out fold + test features) help either task?
- **Status:** done
- **Script:** `src/exp025_self_training.py`; `models.SelfTrain`
- **Runs:** `results/*_025_*`
- **Reference:** champions (Task 1 022 model, Task 2 014 model)

## Design (fixed in TODO.md on 2026-09-30, before running)

Fit the champion; predict the unlabelled pool = the fold's held-out flows + the 81 test flows (features only, each
task from its own feature function); add predictions with confidence ≥ 0.9, never facebook/instagram; refit once;
score only the held-out flows. Confirmation on 2027/2028 only if seed 2026 passes.

## Results (cv_seed 2026)

| Task | Δ | W / L / T | Note |
|---|---|---|---|
| 1 | −0.006 | 17 / 24 / 9 | facebook −0.026 |
| 2 | −0.000 | 9 / 8 / 33 | |

In one fold the pool of 147 flows yields 54 (Task 1) and 90 (Task 2) pseudo-labels added to 264 labelled flows.
They are flows the model is already confident about, so they reinforce the existing decision boundaries and add no
information about the hard cases.

## Decision

Reject; no confirmation run (fails at seed 2026, as planned).
