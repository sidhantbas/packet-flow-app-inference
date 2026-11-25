---
title: "NNN: Title as a question or a short claim"
created: YYYY-MM-DD
creator: sidhantbas
description: "One sentence: what is tested and on which task."
source:
  - NNN_previous_related_log.md
experiment:
  id: 'NNN'
  tasks: [task1]          # task1, task2 or both
  lever: model            # evaluation | features | model | imbalance | hierarchy | decision | data | diagnostic | tooling | submission
  status: proposed        # proposed -> adopted | inconclusive | rejected | measured | tooling | submission | unfinished
  verdict: 'One line with the decisive numbers, written when the experiment ends.'
  # production: 'Role in production, only if adopted'
---

# NNN: Title

**Status: protocol frozen YYYY-MM-DD, before any code change or run.** Results are added below the protocol.
Do not edit the frozen sections after execution starts. Who asked for it and why, in one line.

## Question and evidence

What is asked, and which earlier measurement motivates it (experiment numbers, paths).

## Frozen design

Arms, inputs, model, folds (default 5 × 10, cv_seed 2026; confirmation seeds), and anything that differs from production.

## Decision rule

Fixed before running: rule v2 (paired Δ > 0, ≥ 70% of non-tied folds won, ≥ 10 non-tied) on which seeds; what happens on a pass.

## Boundaries

Data used, rules respected (Task 2 reads only its own files; no test labels; no capture time or order).

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| YYYY-MM-DD | Protocol frozen and committed | before any code change or run |

## Results

Verdict lines copied from each run's `report.md`: macro F1, Δ, wins / losses / ties, per-class Δ.

## Verdict

Adopt / reject / inconclusive / measured, and why. Then:

1. fill the `experiment:` block in the front matter (status, verdict, production role if adopted);
2. regenerate the index: `.venv/bin/python src/build_experiments_index.py`;
3. if adopted, change the champion with `src/runs.py champion` and update AGENTS.md ("Current submission model").
