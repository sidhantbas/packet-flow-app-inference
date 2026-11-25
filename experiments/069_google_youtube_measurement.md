---
title: "069: Where google and youtube are confused (measurement only)"
created: 2026-10-09
creator: sidhantbas
description: Production Task 1 google-youtube errors split by opening type (clean QUIC, mixed QUIC, TCP), with the first-QUIC-packet fingerprint and single-column separability.
source:
  - 068_problem4_facebook_google.md
  - 013_gy_specialist.md
experiment:
  id: 069
  tasks:
  - task1
  lever: diagnostic
  status: measured
  verdict: 'Google vs youtube errors by opening type: TCP 43%, mixed QUIC 32%, clean QUIC 25%'
---

# 069: Where google and youtube are confused (measurement only)

- **Date:** 2026-10-09 · **Status:** done · **Data:** production Task 1 out-of-fold predictions
  (`20261001T173854Z_034_meta_gate`, 10 repeats) and the Task 2 (first-5-packet) columns; training labels only.
- **Why:** google ↔ youtube is the largest open confusion: about 1.77 Task 1 points if fixed perfectly (ranking of
  2026-10-09; facebook ↔ instagram is larger but closed for the day).

## Errors by opening type (google ↔ youtube errors only; 161 in 10 repeats, 16.1 per repeat)

| Opening type | google flows | youtube flows | google error rate | youtube error rate | Share of errors |
|---|---:|---:|---:|---:|---:|
| TCP | 28 | 13 | 8.6% | 34.6% | 43% |
| Mixed QUIC (up packets of different sizes) | 33 | 11 | 7.9% | 22.7% | 32% |
| Clean QUIC (all up packets the same size) | 70 | 31 | 2.9% | 6.8% | 25% |

## Clean QUIC openings: the first-packet fingerprint is already used

First QUIC packet size (clean openings): youtube 1381 B (28 flows) and 1370 B (3); google 1363-1377 B and others (68), plus
2 google flows at 1381 B. Errors in the google size band: **0**. All 41 clean-opening errors are in the youtube band:
google `flow_000905` and `flow_000907` (1381 B, called youtube 10/10; the fingerprint itself points the wrong way) and
youtube flows at 1370 B (`flow_001341` 10/10, `flow_000886` 8/10; 1370 lies between google's 1366 and 1372-1375 and has
only three youtube examples).

## Mixed QUIC openings: fingerprint partly hidden

With exactly two up packets, mean + std gives the larger packet exactly: all 20 such flows are google with 1365 B and have
0 errors. All mixed-opening errors are in openings with three or four up packets (google 13 flows, youtube 11), where the
individual sizes cannot be recovered exactly from count, mean and std.

## TCP: no opening fingerprint, weak whole-flow signal

TCP openings look alike (3 up / 2 down, about 70 B down; two-packet cases 148/148 google vs 147/147 and 156/156 youtube).
Best single Task 1 column for youtube vs google within TCP: `up_down_byte_ratio` AUC 0.73, `mean_pkt_size_down` 0.70
(13 youtube vs 28 google flows). Within UDP: `mean_pkt_size_up` AUC 0.81.

## Reading

The model already exploits the clean-opening fingerprint; the remaining clean errors are fingerprint-contradicting or rare
sizes. The only place where available information may be under-used is mixed QUIC openings with three or four up packets
(32% of the errors): the largest up packet is bounded by count, mean and std (for n values, max ≥ mean + std / √(n − 1) and
max ≤ mean + std · √(n − 1)), which trees do not compute. TCP errors (43%) have little signal in either view.
