---
title: "090: The stamp catalogue (exact opening signatures decoded from the summary card)"
created: 2026-10-10
creator: sidhantbas
description: Frozen protocol and results for decoding exact per-packet sizes ("stamps") from the opening statistics, cataloguing which apps carry which stamps, and measuring whether stamps separate the apps at the main confusion points better than the raw columns. Measurement only.
source:
  - 041_capture_feasibility.md
  - 020_exact_sizes.md
  - 035_h1_checks.md
  - 070_largest_up_packet_bounds.md
experiment:
  id: 090
  tasks:
  - task1
  - task2
  lever: features
  status: measured
  verdict: 'Stamp catalogue: TCP opening decode verified 100/102; no Task 1 gain; Task 2 facebook/instagram AUC +0.016; 4 of 11 facebook flows carry a facebook-only stamp'
---

# 090: The stamp catalogue

**Status: done 2026-10-10. Protocol frozen (`0b21060`) before any code or run.**
**Verdict: the decode works (100/102 TCP openings); stamps add nothing in Task 1; small gain for Task 2 facebook/instagram (AUC 0.61 → 0.62). 4 of 11 facebook flows carry a facebook-only stamp.** Results are below.
Do not edit the frozen sections after execution starts. User 2026-10-10: "yes build the stamp catalogue" (the clerk reads
exact postmarks instead of estimated pages). **Measurement only:** no model change, no test features, no submission (none left).

## Inputs

Train + validation rows (330 flows) of the Task 2 file (`task2_realtime_prefix5/`: first 5 packets, both directions) with their
labels; for step 2 also the 34 production Task 1 columns. Test rows are not read.

## Stamps (decoded per direction of the 5-packet opening; sizes are Ethernet frame lengths, 041)

With $n$ packets, mean $m$ and population std $s$, the card gives the sum $S = n m$ and the sum of squares
$Q = n (s^2 + m^2)$ of the sizes.

| Case | Decode | Self-check |
|---|---|---|
| $n = 1$ | the size is $m$ | — |
| $n = 2$ | sizes $m \pm s$ | both integers (041: 177/177) |
| $s = 0$ | $n$ packets of size $m$ | — |
| **TCP up, $n = 3$** (client first packet, ACK, first message; 041) | with the ACK fixed at 66 B: $x + y = S - 66$, $x^2 + y^2 = Q - 66^2$, solved for the two unknowns; smaller = **client first packet**, larger = **first message** | both roots real and within 0.01 of integers; first packet in 140-180 B |
| anything else | not decoded | — |

A decode that fails its self-check counts as not decoded. Stamp names: `shape` (transport, up count, down count of the opening),
`up_sizes`, `down_sizes` (sorted exact sizes where decoded), and for TCP 3-up openings `syn_size` (client first packet) and
`hello_size` (first message), and for TCP openings with an exactly decoded down direction `synack_size` and `reply_size`
(second down packet).

## Step 1: catalogue (description)

- Coverage: share of flows per app with each stamp decoded; share of TCP 3-up openings passing the self-check.
- For each stamp, the label mix of every exact value seen in ≥ 2 flows; **single-app stamps** (values seen only in one app).
- Facebook focus: every facebook flow's stamps, and which of them are shared with other apps.

## Step 2: do stamps separate the choke points better than the raw columns?

Choke points (from 079): facebook vs google, facebook vs instagram, google vs youtube; each task. For each pair: balanced
`SoftVote` on the pair's rows, repeated stratified 5-fold × 10 (cv_seed 2026), mean ROC AUC over folds, for (a) the raw
production columns (Task 1: 34; Task 2: 12) and (b) the same plus the numeric stamps (`syn_size`, `hello_size`, `synack_size`,
`reply_size`, the smallest and largest decoded up and down size; missing = −1). Reading fixed now: **ΔAUC ≥ +0.01 on a choke
point = stamps add separation there** (then a stamp clerk may be proposed under its own frozen protocol and the five-seed
referee); otherwise the direction is closed with this evidence.

## Boundaries

Sizes only: no names, addresses or contents are decoded (challenge rule 3); the first-message size depends partly on the server
name's length and is used only as a number. Task 2 stamps come from Task 2 files only. Train + validation only.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-10 | Protocol frozen and committed | before any code or run |
| 2026-10-10 | Script committed and run | `exp090_stamp_catalogue.py`; evidence in `experiments/090_evidence/` with `MANIFEST.sha256` |
| after the run | Follow-up count (descriptive, not in the frozen plan): Meta QUIC first-packet size 1365 vs 1367 by app, Fisher exact | below |

Implementation note: for TCP openings with two decoded down packets, `synack_size` is the smaller and `reply_size` the larger
(sizes are decoded as a sorted pair; the order in time is not recoverable). No other deviation.

## Results

### The decode works

The TCP three-packet decode (client first packet + 66-B ACK + first message) passes its self-check (integer roots, first packet
140-180 B) on **100 of 102** TCP 3-up openings (facebook 2/2, google 18/19, mozilla 37/38, x 34/34, youtube 9/9). The opening
ritual inferred in 041 is confirmed by arithmetic. Up directions are decoded for 268 of 330 flows, down directions for 214.

### Catalogue highlights (train + validation)

| Stamp | Finding |
|---|---|
| Client first TCP packet (041's "unexplained 145-175 B") | **differs by app family:** 145 B x 34, mozilla 37, google 6, youtube 3; 147 B facebook 2, youtube 4, google 1; 159 B google 8; 175 B google 3 |
| First message (TCP) | mozilla has four sizes of its own (265, 277, 282, 762 B; 30 flows); **facebook 448 B (2 flows, facebook only)**; 583 B is shared (x 30, mozilla 5, youtube 7, google 3) |
| Meta QUIC first packet | largest up packet **1365 B: facebook 4, instagram 1; 1367 B: facebook 3, instagram 16** (Fisher exact p = 0.015 on flows; the four facebook 1365-B flows are two near-identical pairs, 035, so the evidence is weaker than p suggests). Other apps also send 1365-1367 B packets (30 flows), so the stamp only speaks within Meta |
| Opening shapes | none belongs to a single app; `udp 1/4` is Meta only (facebook 3, instagram 4) |
| Facebook flows | 4 of 11 carry a facebook-only stamp: `flow_000610`, `flow_001324` (TCP, first message 448 B), `flow_000809`, `flow_001168` (QUIC up 241 + 1365 B); the other 7 share every stamp with instagram or with x, youtube and google |

### Separability at the choke points (mean ROC AUC, 50 folds; reading fixed: ΔAUC ≥ +0.01)

| Task | Pair | Raw columns | Raw + stamps | Δ | Adds? |
|---|---|---:|---:|---:|---|
| 1 | facebook / google | 0.9838 | 0.9843 | +0.0005 | no |
| 1 | facebook / instagram | 0.8186 | 0.8186 | 0.0000 | no |
| 1 | google / youtube | 0.9375 | 0.9390 | +0.0015 | no |
| 2 | facebook / google | 0.9902 | 0.9903 | +0.0001 | no |
| 2 | facebook / instagram | 0.6082 | 0.6240 | **+0.0158** | yes |
| 2 | google / youtube | 0.9262 | 0.9350 | +0.0088 | no (near) |

## Verdict

- **Task 1: the stamps add nothing** at any choke point. The whole-flow columns already carry what the opening stamps say.
- **Task 2 facebook/instagram: the stamps add a little** (AUC 0.61 → 0.62), through the 1365/1367-B Meta first packet, which the
  raw columns hide inside a mean and a spread when the opening has two up packets. The pair stays close to chance, and the signal
  rests on about two independent facebook observations. By the frozen reading a Task 2 stamp clerk may be proposed under its own
  protocol; no submissions are left, so it could only inform the report or a future round.
- **For the report:** the catalogue explains what the model can and cannot see: 4 of 11 facebook flows carry a facebook-only
  stamp; the other 7 are, at the opening, indistinguishable from instagram or from google/youtube/x.
