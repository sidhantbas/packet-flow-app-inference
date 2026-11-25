---
title: '021: The Facebook validation gap'
created: 2026-09-30
creator: sidhantbas
description: Why does our validation score (76.1) trail the leaderboard (88–93), and can we close it?
experiment:
  id: '021'
  tasks:
  - task1
  - task2
  lever: diagnostic
  status: measured
  verdict: 'The validation gap is facebook (Task 1 validation facebook F1 0.00: 3 long TCP flows unlike train); a TCP-signature variant hurts facebook (-0.046)'
---
# 021: The Facebook validation gap

- **Date:** 2026-09-30
- **Question:** Why does our validation score (76.1) trail the leaderboard (88–93), and can we close it?
- **Status:** done
- **Script:** `src/exp021_facebook_tcp.py` (variant); diagnostics run inline (numbers below)
- **Runs:** `results/*_021_meta_sig`
- **Reference:** champions

## Diagnostic 1: where validation points go (models trained on train only)

| Task | google | instagram | mozilla | x | youtube | facebook | Macro F1 | If facebook perfect |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.90 | 0.91 | 0.86 | 0.91 | 0.89 | **0.00** | 0.745 | 0.912 |
| 2 | 0.94 | 0.75 | 0.90 | 0.90 | 0.85 | **0.33** | 0.778 | 0.890 |

The five other classes are at leaderboard level. The gap is the 3 validation Facebook flows (task 1 predictions:
mozilla, google, mozilla).

## Diagnostic 2: two kinds of Facebook flow

7 of 8 train Facebook flows are UDP. All 3 validation Facebook flows are TCP, long-lived (235–1122 s), with tiny
packets and 6–10 s between packets. Among TCP flows in train+validation:

| App (TCP flows) | n | Down packet size (median) | Up/down bytes (median) | Bursts (median) |
|---|---|---|---|---|
| facebook | 4 | 87 B | 1.50 | 7.5 |
| instagram | 1 | 74 B | 1.56 | 7 |
| google | 28 | 501 B | 0.45 | 2 |
| mozilla | 39 | 395 B | 0.34 | 2 |
| x | 73 | 382 B | 0.69 | 2 |
| youtube | 13 | 376 B | 0.61 | 2 |

A Meta keep-alive-like signature (more up than down, tiny download packets). It is not exclusive: TCP flows with
up/down > 1.2 and download packets < 120 B are x 13, facebook 4, google 2, instagram 1, youtube 1, mozilla 1.

## Diagnostic 3: does the CV model catch them?

Out-of-fold predictions of the task 1 champion (10 repeats each): the long TCP Facebook flows are predicted
facebook 10/10 (flow_000024), 9/10 (flow_000610) and 5/10 (flow_001324). Once the training data contains this
kind of flow, the model learns it. The remaining Facebook misses are two UDP flows that look like google
(flow_000799, flow_001145) and one short TCP flow (flow_000231).

**So the validation-phase gap is a coverage artefact of the train split. Our submission is trained on
train + validation and has seen this Facebook type.**

## Variant: explicit TCP-conditioned signature features

`tcp_down_pkt`, `tcp_ratio` (value if TCP, else −1) and `down_share`, added to both champions.

| Task | Δ | W / L / T | facebook |
|---|---|---|---|
| 1 | −0.006 | 18 / 30 / 2 | −0.046 |
| 2 | +0.002 | 7 / 9 / 34 | +0.005 |

## Decision

Reject the variant. The main outcome is the diagnosis: the validation score understates the final model, and only
a Final Test Phase submission can tell where it stands (2 test Facebook flows swing each task by up to ~8 points).
