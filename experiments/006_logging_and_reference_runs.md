---
title: '006: Local run logging and reference runs'
created: 2026-09-30
creator: sidhantbas
description: Does the new logging system reproduce experiment 004 exactly?
experiment:
  id: '006'
  tasks:
  - task1
  - task2
  lever: tooling
  status: tooling
  verdict: 'Run logging (record_run: manifests, hashes, paired comparison, checks, verify) reproduces 004 exactly; SoftVote becomes champion for both tasks'
---
# 006: Local run logging and reference runs

- **Date:** 2026-09-30
- **Question:** Does the new logging system reproduce experiment 004 exactly?
- **Status:** done
- **Script:** `src/exp006_reference_runs.py`
- **Runs:** `results/20260930T161116Z_006_rf_baseline`, `results/20260930T161714Z_006_softvote`
- **Reference:** none before this experiment; SoftVote is now the champion for both tasks.

## Hypothesis

Charles documents every run with a manifest, hashes, raw predictions and a separate verifier. We adopt the same
idea locally, and add device specs (our machines differ), automatic paired comparison against a champion,
automatic checks, and a `status` digest for starting a session.

## Setup

- `src/cv.py` `evaluate()` now also returns `flow_id`, `fold`, per-fold seconds and the CV settings.
- `src/runlog.py` `record_run()` writes the run folder, compares to the champion, runs the checks.
- `src/runs.py` for status, list, show, compare, verify and champion.
- Features: the 17 default columns. Models: RF (baseline) and SoftVote (submission model).
- Device: Sids-MacBook-Pro-2, Apple M4 Pro (10P + 4E cores), 48 GB, Python 3.13.1.

## Results

| Task | RF | SoftVote | Δ | Wins | Verdict |
|---|---|---|---|---|---|
| task1_static | 0.7326 | 0.7705 | +0.0379 | 34/50 | NEAR-MISS (inconclusive) |
| task2_realtime_prefix5 | 0.6756 | 0.6856 | +0.0100 | 29/50 | INCONCLUSIVE |

These match 004 exactly. `runs.py verify` passes for both runs, and a deliberate edit to one `oof.csv`
was caught (hash mismatch and recomputed fold F1 differs).

Pooled confusion changes, SoftVote vs RF: fewer google → youtube on both tasks (task 2: 177 → 94),
but more youtube/x/mozilla → google. The ensemble shifts errors toward google.

## Caveats

- Both runs were made with an uncommitted tree (flagged `dirty-tree`); the code hashes in each manifest
  still pin the exact source.
- The two runs took 6.5 minutes in total, with most CPU time in the system (thread overhead from `n_jobs=-1`
  on 264-row folds). Worth testing a fixed `n_jobs` if runs get slow.

## Decision

Use `record_run()` for every experiment from 007 on. SoftVote stays the champion for both tasks.

## Next

Test #6 (task 2 without timing) as experiment 007.
