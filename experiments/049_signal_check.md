---
title: '049: Is the Facebook vs Instagram full-flow signal app behaviour or session length? (measurement only)'
created: 2026-10-08
creator: sidhantbas
description: Does the facebook vs instagram signal found in 048 survive when session length is removed, and how long must our captured sessions be?
experiment:
  id: 049
  tasks:
  - task1
  lever: diagnostic
  status: measured
  verdict: The facebook vs instagram signal is behaviour (volume, rates), not session length; the opening alone is at chance
---
# 049: Is the Facebook vs Instagram full-flow signal app behaviour or session length? (measurement only)

- **Date:** 2026-10-08
- **Question:** Does the facebook vs instagram signal found in 048 survive when session length is removed, and how long must our captured sessions be?
- **Status:** done
- **Script:** `src/exp049_signal_check.py` (about 9 min, mostly the permutation tests)
- **Runs:** none recorded (binary diagnostics, as in 048). Numbers below are the script's output.
- **Reference:** Task 1 champion `20261001T173854Z_034_meta_gate` (production unchanged)

## Hypothesis

048 found that 9 of the top 10 facebook vs instagram features are full-flow volume and timing columns. That could be app
behaviour, or just longer sessions in one app (a capture artefact). Requested by the user.

## Setup

Task 1 labelled flows only. Rates: packets/s and bytes/s per direction, bursts per minute, duration floored at 1 ms.
Random forest (`models.rf`, balanced), 5 x 10 folds (cv_seed 2026) on the 30 Meta flows, 100-shuffle permutation tests.

**Step 3 changed:** the released files hold only full-flow and first-5-packet aggregates, with no packet timestamps, so
features over the first 10/30/60/120 s cannot be computed. Measured instead: first 5 packets vs full flow, and the duration
distribution of the labelled Meta flows. A real time-truncation curve is possible later on our own pcaps.

## Results

**1. Length vs rate (facebook vs instagram, Mann-Whitney, rank-biserial r):**

| Column | facebook median [IQR] | instagram median [IQR] | r | p |
|---|---|---|---|---|
| duration (s) | 205 [23-378] | 235 [204-710] | -0.22 | 0.344 |
| packet_count_up | 25 [12-42] | 547 [42-1416] | -0.61 | 0.006 |
| packet_count_down | 20 [12-48] | 329 [50-2757] | -0.67 | 0.003 |
| bytes_up | 7,397 | 280,347 | -0.66 | 0.003 |
| bytes_down | 5,079 | 54,216 | -0.70 | 0.002 |
| packets down/s | 0.08 | 1.29 | -0.46 | 0.039 |
| bytes down/s | 19 | 296 | -0.48 | 0.031 |
| packets up/s | 0.09 | 1.17 | -0.39 | 0.085 |
| bytes up/s | 26 | 632 | -0.37 | 0.102 |
| bursts/min | 1.96 | 8.98 | -0.20 | 0.389 |

The script also prints all six classes and the google/youtube and mozilla/x pairs. Neither pair differs in duration
(r +0.02, -0.10), and google/youtube differ in nothing much (|r| <= 0.22).

**2. Facebook vs Instagram random forest, length removed:**

| Column set | Columns | Facebook F1 | Fold std | Shuffled mean | p |
|---|---|---|---|---|---|
| original (048) | 34 | 0.662 | 0.277 | 0.341 | 0.010 |
| rates (duration, counts, bytes, bursts replaced) | 33 | 0.685 | 0.230 | 0.344 | 0.010 |
| length only (duration, counts, bytes, bursts) | 6 | 0.611 | 0.292 | 0.355 | 0.050 |

**3. Truncation proxy and Meta flow durations:**

| Column set | Columns | Facebook F1 | Fold std | Shuffled mean | p |
|---|---|---|---|---|---|
| first 5 packets only | 17 | 0.373 | 0.283 | 0.366 | 0.436 |
| full flow only | 17 | 0.676 | 0.270 | 0.338 | 0.010 |
| both (original) | 34 | 0.662 | 0.277 | 0.341 | 0.010 |

| App | n | min | 25% | median | 75% | 90% | max | share > 60 s | share > 300 s |
|---|---|---|---|---|---|---|---|---|---|
| facebook | 11 | 0 | 23 | 205 | 378 | 1113 | 1122 | 0.55 | 0.27 |
| instagram | 19 | 0 | 204 | 235 | 710 | 1074 | 1125 | 0.79 | 0.37 |

Eight Instagram flows and two Facebook flows last 229-283 s, close to the > 240 s idle timeout found in 041.

**4. Importance stability (folds of 50 with the feature in the fold's top 10):**

| Feature | 048 rank | Folds in top 10 | Part of the flow |
|---|---|---|---|
| packet_count_up | 1 | 50/50 | full flow |
| packet_count_down | 2 | 50/50 | full flow |
| bytes_down | 3 | 50/50 | full flow |
| bytes_up | 4 | 50/50 | full flow |
| burst_count | 5 | 49/50 | full flow |
| std_iat | 6 | 48/50 | full flow |
| mean_iat | 7 | 46/50 | full flow |
| p5_std_pkt_size_down | 8 | 36/50 | opening |
| std_pkt_size_down | 9 | 19/50 | full flow |
| mean_pkt_size_down | 10 | 13/50 | full flow |

## Caveats

- 11 vs 19 flows: the Mann-Whitney tests are not corrected for multiple comparisons; the permutation tests on the models
  are the stronger evidence.
- "Length only" still scores 0.61 because, at similar durations, packet and byte counts are themselves intensity.
- Step 3 is a proxy (opening vs full flow), not the requested time cuts; see Setup.

## Decision

Measurement only; production unchanged.

- **Step 1:** behaviour, not session length. Durations do not differ (p 0.34); volume differs strongly (r about -0.65)
  and rates moderately (r about -0.45). Instagram moves far more data over a similar time.
- **Step 2:** behaviour. Rate features keep the signal (F1 0.685 vs 0.662, p 0.01).
- **Step 3:** the opening carries no facebook vs instagram signal (0.373, at chance); the full flow does (0.676). The
  signal needs the flow to run its course, and half of the Meta flows last over 200 s.
- **Step 4:** stable. The seven full-flow volume and timing columns are in the top 10 in 46-50 of 50 folds.

## Next

Capture protocol: Meta sessions meant to produce long flows (idle-open, trickle, keep-alive) must last at least 20 min
(1,200 s), since the longest labelled Meta flow is 1,125 s and 27-37% exceed 300 s. Burst and cold-start sessions can stay
at 10-15 min, as those flows last under 60 s. The current task (meta_capture_task.md)
already uses 25 min for idle-open sessions, which meets this.
