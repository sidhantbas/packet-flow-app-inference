---
title: "073: Where google and mozilla are confused (measurement only; closed)"
created: 2026-10-09
creator: sidhantbas
description: Production Task 1 google-mozilla errors traced to ten mostly-TCP flows; most are flows whose nearest neighbour belongs to another app.
source:
  - 072_instagram_youtube_measurement.md
  - 064_task1_third_expert.md
experiment:
  id: '073'
  tasks:
  - task1
  lever: diagnostic
  status: measured
  verdict: Google vs mozilla errors come from 10 mostly-TCP flows; at most about 0.2 points recoverable; closed
---

# 073: Where google and mozilla are confused (measurement only; closed)

- **Date:** 2026-10-09 · **Status:** closed (mostly irreducible) · **Data:** production Task 1 out-of-fold predictions
  (`20261001T173854Z_034_meta_gate`, 10 repeats), Task 2 columns for openings; training labels only.
- **Why:** fourth-largest confusion, about 0.55 Task 1 points if fixed perfectly (ranking of 2026-10-09).

## Errors (41 in 10 repeats: google → mozilla 15, mozilla → google 26; 10 flows)

| Flow | True | Errors | Traffic type | Opening | Nearest same-app | Nearest other |
|---|---|---:|---|---|---:|---|
| `flow_000524` | mozilla | 10 | TCP keep-alive | TCP 4/1 | 0.73 | google `flow_001265` (0.93) |
| `flow_000685` | mozilla | 10 | short TCP | TCP 3/2 | 0.88 | x `flow_000015` (0.62) |
| `flow_000671` | google | 7 | short TCP | TCP 3/2 | 1.09 | mozilla `flow_000048` (0.89) |
| `flow_000120` | google | 4 | short TCP | TCP 3/2 | 6.60 | facebook `flow_000231` (3.45) |
| `flow_000144` | google | 2 | short TCP | TCP 3/2 | 0.35 | x `flow_000487` (0.58) |
| `flow_000324` | mozilla | 2 | short QUIC fetch | clean QUIC 1366 B | 0.43 | google `flow_000569` (0.99) |
| `flow_000055` | mozilla | 2 | short QUIC fetch | clean QUIC 1366 B | 0.43 | google `flow_000568` (1.04) |
| `flow_000137` | mozilla | 2 | TCP keep-alive | TCP 3/2 | 1.07 | x `flow_000156` (0.81) |
| `flow_000265` | google | 1 | short TCP | TCP 3/2 | 0.35 | x `flow_000487` (0.79) |
| `flow_000672` | google | 1 | short TCP | TCP 3/2 | 1.19 | x `flow_000011` (0.40) |

Distances: 16 gate-2 columns, log1p, standardised.

## Reading

- Mozilla is 95% TCP (39 of 41 flows); its TCP openings (mostly 3 up / 2 down) look like google's TCP openings. Its two
  QUIC flows open with 1366 B, the same first packet as 18 google flows, so the fingerprint cannot separate them.
- 24 of the 41 errors (59%) are on flows whose nearest neighbour belongs to another app (often x): the irreducible pattern of
  068 and 072.
- 17 errors are on flows with a closer same-app neighbour; 10 of them are one flow, mozilla `flow_000524` (TCP keep-alive),
  the only case found where the model ignores a closer same-app look-alike. One flow does not support a rule, and a
  nearest-neighbour expert hurt other classes in 064.

## Verdict

Closed as mostly irreducible: at most about 0.2 of the 0.55 points looks recoverable, through essentially one flow. No rule
is built from these flows.
