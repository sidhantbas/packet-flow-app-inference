---
title: "072: Where instagram and youtube are confused (measurement only; closed)"
created: 2026-10-09
creator: sidhantbas
description: Production Task 1 instagram-youtube errors traced to four flows; three are one-offs or a cross-label triplet, so the pair is closed as irreducible.
source:
  - 069_google_youtube_measurement.md
  - 068_problem4_facebook_google.md
experiment:
  id: '072'
  tasks:
  - task1
  lever: diagnostic
  status: measured
  verdict: Instagram vs youtube errors come from 4 flows; closed as irreducible
---

# 072: Where instagram and youtube are confused (measurement only; closed)

- **Date:** 2026-10-09 · **Status:** closed (irreducible with the released features) · **Data:** production Task 1
  out-of-fold predictions (`20261001T173854Z_034_meta_gate`, 10 repeats), Task 2 columns for openings; training labels only.
- **Why:** third-largest confusion, about 0.78 Task 1 points if fixed perfectly (ranking of 2026-10-09).

## All errors come from four flows (26 errors in 10 repeats: instagram → youtube 16, youtube → instagram 10)

| Flow | True | Errors | Traffic type | Opening | Nearest same-app flow | Nearest other flow |
|---|---|---:|---|---|---:|---|
| `flow_000216` | instagram | 8 | short TCP | TCP | 6.25 | youtube `flow_000229` (0.49) |
| `flow_000003` | instagram | 8 | slow QUIC trickle | clean QUIC, 1294 B | 3.33 | youtube `flow_001337` (2.67) |
| `flow_000229` | youtube | 7 | short TCP | TCP | 5.96 | facebook `flow_000231` (0.49) |
| `flow_000044` | youtube | 3 | slow QUIC trickle | mixed QUIC, 3 up | 1.05 | instagram `flow_000359` (1.20) |

Distances: 16 gate-2 columns, log1p, standardised.

## Reading

- `flow_000216` (instagram), `flow_000229` (youtube) and `flow_000231` (facebook) are near-identical short TCP flows with three
  different labels (pairwise distances about 0.49): a cross-label triplet; whichever two are in training, the third is
  called after one of them.
- `flow_000003` is the only training flow with a 1294-B first QUIC packet (Meta's QUIC library): a one-off.
- `flow_000044` is borderline (nearest youtube 1.05 vs nearest instagram 1.20).
- Elsewhere the opening already separates the two apps with no errors: clean QUIC first packets instagram 1294/1365/1367 B
  vs youtube 1370/1381 B; mixed openings instagram 2 up packets (13 flows) vs youtube 3-4 (11 flows).

## Verdict

Closed: three of the four flows are one-offs or a cross-label triplet, and the fourth is a coin flip. Almost none of the
0.78 points is recoverable with the released features. No rule is built from these flows.
