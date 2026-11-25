---
title: '002: Repeated stratified CV, with vs without `start_rel`'
created: 2026-09-29
creator: sidhantbas
experiment:
  id: '002'
  tasks:
  - task1
  - task2
  lever: evaluation
  status: measured
  verdict: 'Repeated stratified 5x10 CV introduced (RF: Task 1 0.733, Task 2 0.676); start_rel adds +0.003 / +0.013, treated as recording-time leakage and excluded'
---
# 002: Repeated stratified CV, with vs without `start_rel`

- **Date:** 2026-09-29
- **Scripts:** `src/cv.py` (reusable evaluation), `src/exp002_start_rel.py` (this experiment)
- **Data:** train+validation merged per task (330 flows). Each task reads only its own folder.
- **CV:** `RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2026)` gives 50 folds. The RF seed for fold i is i, so both variants see identical folds and identical model seeds, which makes the comparison paired.
- **Model:** `RandomForestClassifier(n_estimators=500, class_weight="balanced")`, same as 001.
- **Features:**
  - (a) the 17 baseline features: everything except `flow_id`, `split`, `server_port`, `start_rel`; `transport` encoded as udp=1
  - (b) the same features plus `start_rel`
- **Noise measures:** "fold std" is the std of macro F1 across the 50 folds. "Repeat std" is the std of the 10 per-repeat means.

## Results: macro F1 (mean ± fold std)

| Task | (a) without start_rel | (b) with start_rel | Δ (b−a) | Paired fold-Δ std | Folds b>a | Repeats b>a |
|---|---|---|---|---|---|---|
| task1_static | **0.7326 ± 0.0792** (repeat std 0.028) | 0.7353 ± 0.0770 | +0.0026 | 0.0455 | 26/50 | 6/10 |
| task2_realtime_prefix5 | **0.6756 ± 0.0670** (repeat std 0.025) | 0.6883 ± 0.0636 | +0.0127 | 0.0311 | 35/50 | 9/10 |

Estimated score for (a): 36.6 + 33.8 = **70.4**.

### Per-class F1 (mean ± fold std)

| Class | T1 (a) | T1 (b) | T2 (a) | T2 (b) |
|---|---|---|---|---|
| facebook | 0.486 ± 0.293 | 0.481 ± 0.296 | 0.361 ± 0.273 | 0.333 ± 0.284 |
| google | 0.811 ± 0.059 | 0.818 ± 0.057 | 0.823 ± 0.058 | 0.846 ± 0.051 |
| instagram | 0.691 ± 0.198 | 0.692 ± 0.200 | 0.563 ± 0.201 | 0.565 ± 0.184 |
| mozilla | 0.847 ± 0.104 | 0.845 ± 0.107 | 0.780 ± 0.120 | 0.812 ± 0.094 |
| x | 0.876 ± 0.073 | 0.883 ± 0.068 | 0.845 ± 0.061 | 0.901 ± 0.058 |
| youtube | 0.685 ± 0.099 | 0.693 ± 0.103 | 0.682 ± 0.092 | 0.672 ± 0.081 |

## Verdict on `start_rel`

- **Task 1: inconclusive, effectively no effect.** Δ = +0.003, against a fold std of 0.079. Folds split 26/50 and repeats 6/10, which is a coin flip. The +3.8 points on the single validation split in 001 were noise from that split.
- **Task 2: inconclusive by the fold-noise criterion.** Δ = +0.013 is well under the fold std of 0.067 and under the repeat std of 0.025. The paired comparison is more consistent, though: b wins 35/50 folds and 9/10 repeats. The gain comes mostly from x (+0.056), mozilla (+0.032) and google (+0.023), which fits `start_rel` picking up *when* each app was being used during the 44-minute recording rather than anything about the traffic.
- **Decision:** keep `start_rel` excluded. It adds nothing on task 1. On task 2, any gain it does give probably comes from the recording schedule and would not carry over to new traffic. That makes it a leakage risk we would have to defend in the report.

## Other observations

- CV gives a different picture from the single validation split. Task 1 is 0.733, not 0.713. Task 2 is 0.676, *lower* than task 1 and lower than the 0.743 from the validation split. The validation split was flattering to task 2.
- **Facebook is not zero under CV:** 0.49 on task 1 and 0.36 on task 2, but with a std of about 0.29. Each test fold holds only 2–3 Facebook flows, so this class sets most of the macro F1 noise. Instagram is the next weakest class, at 0.56 on task 2.

## The two port-80 flows

| | flow_000535 (validation, label x) | flow_001060 (test, features only) |
|---|---|---|
| start_rel | 976 s (~16 min) | 2119 s (~35 min) |
| T1 duration | 116 s | 160 s |
| T1 packets up / down | 24 / 18 | 25 / 20 |
| T1 bytes up / down | 3158 / 2276 | 2925 / 2192 |
| T1 mean pkt size up / down | 132 / 126 | 117 / 110 |
| T1 mean IAT, max IAT | 2.8 s, 10.5 s | 3.6 s, 10.2 s |
| T1 burst_count | 14 | 18 |
| T2 bytes up / down (first 5 pkts) | 576 / 140 | 576 / 140 (identical) |

- Both are TCP flows on port 80, long-lived, low-volume and chatty. They have small packets of similar size in both directions, many bursts, and gaps of about 10 s. That looks like periodic polling or a keepalive, not content transfer, and is unlike the typical TCP/443 flow (median burst_count 2).
- In task 2 the two flows have **identical first-5-packet sizes**, and in task 1 they are very close. They appear to be the same kind of connection, recurring about 19 minutes apart.
- Port 80 appears in only one train+validation flow, so the `server_port` feature cannot generalise and stays dropped. We have not looked at, and will not look at, anything beyond the given features for these flows.
