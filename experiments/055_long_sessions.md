---
title: "055: Do 20-minute sessions make captured flows consistent with the training records?"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for the second capture group (cellular, 20 minutes per app) through gates 1-2 and the 054 consistency check.
source:
  - 052_iphone_pilot.md
  - 053_tcp_flow_start.md
  - 054_independent_extraction_consistency.md
  - 049_signal_check.md
experiment:
  id: '055'
  tasks:
  - task1
  lever: data
  status: measured
  verdict: '20-minute cellular sessions: closer, but gates 1 and 2 fail (AUC 0.957); QUIC first-packet sizes differ (1242/1274 vs 1363-1381 B)'
---

# 055: Do 20-minute sessions make captured flows consistent with the training records?

**Status: done 2026-10-09. Protocol frozen (`71f8aaa`) after recording and before any feature extraction; executed and verified.**
**Verdict: H1 not supported under the frozen rule (narrowly); gate 1 FAIL (merged segments); gate 2 FAIL (AUC 0.957).**
Longer sessions shrink the time/length gap a lot; the remaining gap points to the phone's protocol stack. Results are below. Do not edit the frozen sections after execution starts.
Previous steps: [052](052_iphone_pilot.md), [053](053_tcp_flow_start.md), [054](054_independent_extraction_consistency.md).

## Question

With 20-minute app sessions on cellular, are the captured facebook and instagram flows consistent with the
train+validation flows in duration, gaps and bursts, and does gate 2 pass?

## Evidence before this experiment

- [054](054_independent_extraction_consistency.md): our extractor is verified; pilot packet sizes mostly match the
  training records, but duration, max_iat, burst_count (and mean_iat for facebook) have single-column AUC >= 0.80.
  Training Meta flows last 205-235 s at the median; pilot flows lasted seconds (60 s sessions).
- [049](049_signal_check.md): Meta sessions need >= 20 minutes.
- [052](052_iphone_pilot.md): the home Wi-Fi blocks QUIC; cellular does not.

## Hypothesis

H1: session length caused the 054 time/length inconsistency. H0: it persists with 20-minute sessions (then the cause is
the device, app versions or the organisers' capture setup).

## Data

- Group `sid-iphone-20261009T115620Z-long-cellular` (gitignored raw folder): `01-idle` (60 s), `02-facebook`,
  `03-instagram`, `04-youtube` (1,200 s each), `05-idle-after` (60 s). Cellular, Wi-Fi off, recorded with
  `src/capture_group.sh long cellular` (commit `0aeb984`). All sessions 0 kernel drops, hashes verified before this protocol.
- Labels: session app for flows whose first packet falls in the session's recording window (`sessions.csv`).
- Original: train+validation Task 1 and Task 2 features and labels only. No test data, no metadata label counts.

## Frozen method

Extractor `src/capture_extract.py` with the default `--tcp-start syn` (053 decision), `--phone-ip auto`.

| ID | Measurement |
|---|---|
| M1 | Gate 1 on all sessions with flows |
| M2 | Gate 2 on the three app sessions: adversarial AUC, per-app rows, nearest original labels |
| M3 | 054 Part B per app: single-column AUC, KS, medians, share inside the original 5th-95th percentile |
| M4 | QUIC check: UDP flows with no reply, per app session |
| M5 | Merged segments: share of TCP frames > 1514 B, per app session |
| M6 | Flow duration distribution per app (median, share > 60 s) |

## Frozen decision rules

- **H1 supported** if, for both facebook and instagram, `duration`, `burst_count`, `max_iat` and `mean_iat` all have
  single-column AUC < 0.80.
- **Gate 2** pass/fail as defined in `capture_checks.py`.
- **Training use** needs gate 1 and gate 2 to pass, merged segments (M5) handled, the organiser questions answered or
  a user decision, and the user's approval. This experiment does not train any model.

## Boundaries

Measurement only. Addresses only in memory for flow keys and phone detection; nothing written, printed or looked up.
Production frozen at 5eb9a8b. Everything runs on this Mac.

## Evidence plan

Script `src/exp055_long_sessions.py`; evidence folder
`data/captures/sid-iphone-20261009T115620Z-long-cellular/` (feature CSVs, gate output, consistency tables,
`summary.json`, `manifest.json` with SHA-256 of inputs and outputs).

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 11:56-13:03 | Group recorded (`capture_group.sh`, `0aeb984`) | 5 sessions, 0 drops, hashes OK, RVI stopped |
| 2026-10-09 | Protocol frozen and committed | `71f8aaa`, before any feature extraction of this group |
| 2026-10-09 | Analysis script committed | `8a5e72b` |
| 13:04:15-13:04:23 | `src/exp055_long_sessions.py` on `8a5e72b`, clean tree | Evidence in the group folder; 40 SHA-256 in `manifest.json`, all re-checked: match. No IPv4-like string in any of the 28 evidence files |

No deviation from the frozen protocol. The user did not skip any session.

## Results

Evidence: `data/captures/sid-iphone-20261009T115620Z-long-cellular/` (`summary.json`,
`gates-*.txt`, `consistency_<app>.csv`, `manifest.json`).

Flows with >= 5 packets: facebook 34, instagram 55, youtube 181 (idle sessions: few or none).

### M3: time and length columns, pilot (054) vs 20-minute sessions (single-column AUC; flag >= 0.80)

| Column | Facebook pilot (Wi-Fi) | Facebook 20 min | Instagram pilot (cellular) | Instagram 20 min | YouTube 20 min |
|---|---:|---:|---:|---:|---:|
| duration | 0.78 | 0.66 | 0.90 | 0.72 | 0.54 |
| burst_count | 0.67 | 0.69 | 0.91 | **0.799** | 0.51 |
| max_iat | 0.81 | 0.69 | 0.85 | 0.75 | 0.57 |
| mean_iat | 0.89 | **0.816** | 0.60 | 0.59 | 0.51 |
| packet_count_down | 0.53 | 0.61 | 0.84 | 0.78 | 0.52 |

Inconsistent gated columns now: facebook `mean_iat` only; instagram none; youtube `up_down_byte_ratio`.
**H1 rule: not met**, because facebook `mean_iat` is 0.816 (>= 0.80); instagram `burst_count` passes at 0.799.

### M6: flow durations

| App | Captured median | Captured share > 60 s | Training median | Training share > 60 s |
|---|---:|---:|---:|---:|
| facebook | 4.1 s | 29% | 205 s | 55% |
| instagram | 2.0 s | 31% | 235 s | 79% |
| youtube | 4.8 s | 45% | 3.9 s | 27% |

Long sessions now produce long-lived Meta flows (about 30% over 60 s), but most Meta flows are still short.

### M1, M2: gates

| Gate | Result |
|---|---|
| Gate 1 | **FAIL**: mean down size > 1514 B in 2 of 270 flows (merged segments, M5) |
| Gate 2 | **FAIL**: adversarial AUC 0.957 |

| App | n | Median NN distance (orig 90th pct) | Same-label 5-NN (orig) | Nearest original labels |
|---|---:|---|---|---|
| facebook | 34 | 0.84 (2.15) | 0.02 (0.16) | google 12, youtube 8, x 5, instagram 5, facebook 2, mozilla 2 |
| instagram | 55 | 1.23 (2.01) | 0.13 (0.41) | google 28, facebook 8, instagram 7, youtube 5, mozilla 4, x 3 |
| youtube | 181 | 1.19 (1.25) | 0.28 (0.59) | google 91, youtube 34, x 21, instagram 20, mozilla 14, facebook 1 |

Captured flows are now close to original flows (distances inside the 90th percentile), but the nearest original flows
mostly carry another label, usually google.

### M4, M5: network and merged segments

| App | UDP flows (no reply) | MB down UDP / TCP | TCP frames > 1514 B | Largest frame |
|---|---|---|---:|---:|
| facebook | 21 (1) | 242.6 / 0.1 | 0.2% | 4,011 B |
| instagram | 40 (3) | 169.1 / 0.3 | 0.9% | 3,990 B |
| youtube | 112 (2) | 262.7 / 3.6 | 6.8% | 13,146 B |

QUIC works on cellular for all three apps. Merged TCP segments are now large enough to fail gate 1.

### Protocol-stack signatures (from the gate report)

| Signature | Captured | Training |
|---|---|---|
| UDP openings, 2 up / 3 down | 69% | 70% |
| QUIC first-packet sizes (openings whose up packets are all equal) | facebook 1274 B (9); instagram 1242 (22), 1294 (14); youtube 1242 (85), 1292 (8) | all apps: 1381 (30), 1366 (20), 1375 (18), 1365 (13), 1377 (9), 1363 (7); facebook/instagram: 1367 (4), 1365 (3), 1294 (1) |
| TCP openings | 4 up / 1 down 77% | 3 up / 2 down 66% |

## Interpretation

- **Session length was a large part of the gap.** Time and length AUCs fall from 0.78-0.91 to 0.66-0.82, and instagram
  has no inconsistent column left. The frozen rule still fails, narrowly, on facebook `mean_iat`.
- **What is left is mainly the client's protocol stack, not behaviour.** Our most common QUIC first-packet sizes,
  1242 B (youtube 85, instagram 22) and 1274 B (facebook 9), never occur in the 111 training openings with equal up
  sizes, which are dominated by 1363-1381 B. Only 1294 B (Meta's QUIC library, 041) appears on both sides: 14 instagram
  openings here, 1 in training. TCP openings differ as in 053. These sizes come from the operating system and the app's
  network library, so the organisers probably used a different phone, OS or app versions. Probable, not proven: the
  training set is small (one 44-minute capture).
- **Label mismatch:** captured facebook/instagram flows sit near original google flows. With a different client stack,
  captured flows of one app can look like another app's training flows; adding them could teach the model wrong
  associations.

## Decision

No training use: gate 1 and gate 2 fail, H1 is not met. Keep the extractor unchanged. Production unchanged (5eb9a8b).

## Restart point and next

1. Ask Charles and the organisers which phone, OS, app versions and capture point produced the dataset (QUIC
   first-packet sizes 1363-1381 B, first client TCP packet 145-175 B). Without a matching client stack, own captures are unlikely to pass gate 2.
2. If a matching device (for example an Android phone) is available, repeat this group on it (cellular, 20 min per app).
3. Merged segments (053) must be handled before any cellular capture is used; YouTube shows 6.8% merged frames.
