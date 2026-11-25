---
title: '041: Own labelled captures, feasibility (understanding only)'
created: 2026-10-05
creator: sidhantbas
description: Could our own labelled captures be made rule-compliant and close enough to the organisers' flows to help? (No models trained.)
experiment:
  id: '041'
  tasks:
  - task1
  - task2
  lever: data
  status: measured
  verdict: 'Own captures feasibility: no-go at the time; all 21 feature formulas decoded; 7 facebook/instagram traffic types; labels look destination-based'
---
# 041: Own labelled captures, feasibility (understanding only)

- **Date:** 2026-10-05
- **Question:** Could our own labelled captures be made rule-compliant and close enough to the organisers' flows to help? (No models trained.)
- **Status:** done
- **Script:** `src/exp041_capture_feasibility.py` (reads features of all 411 flows in both tasks, train+validation labels only)
- **Runs:** none (no CV, no model). Branch `exp041-captures`; production and `submission.json` unchanged (frozen at 5eb9a8b).
- **Reference:** champions unchanged (`20261001T173854Z_034_meta_gate`, `20260930T173836Z_014_fi_same_nocw`)
- **Report:** reports/exp041_capture_feasibility.md

## Hypothesis

Facebook is the main loss (11 labelled flows). New labelled Facebook/Instagram flows might help, but only if the rules allow it,
the features can be rebuilt exactly, and the labels mean the same thing.

## Setup

- Read every official text: READMEs, dataset README (EN/JA), metadata.json ×2, templates ×6, evaluation script.
- Checked every formula identity on all 411 flows in both tasks.
- Recovered exact packet sizes where a direction has 1–2 packets or std 0.
- Typed the labelled Facebook/Instagram flows with rules fixed before running, cross-checked by Ward clustering.
- Measured co-occurrence of labelled flows with Instagram flows in time. This is for understanding only; capture order stays off-limits as a model input.

## Results

- **Rules:** no official text names external data, own captures, pretraining or augmentation.
  - Task 1: allowed with disclosure ("information other than the provided feature files … must be clearly described").
  - Task 2: banned on the literal reading ("must use only the task2_realtime_prefix5/ files").
  - Our own team rule (2026-10-01) bans it for both tasks.
- **Flow definition:**
  - Bidirectional, one transport and server port; `up` = from the phone.
  - ≥ 5 packets; cut at capture boundaries; µs timestamps.
  - Idle timeout > 239.9 s (largest gap); no active timeout ≤ 1304 s.
  - About 1405 flows numbered in start order, 411 kept.
  - Task 2 = first 5 packets of the flow, both directions in time order, all columns recomputed. Confirmed: prefix ≤ full on every bound (411/411), and the one 5-packet flow has identical rows.
- **Formulas (all 411 flows, both tasks):**
  - mean size = bytes/count; mean_iat = duration/(n−1); ratios = x/max(y,1): exact, 411/411.
  - Size std is population std (2-packet directions: mean ± std are integers, 177/177 and 175/175).
  - Gap std is population std (Task 2 middle gaps feasible 411/411; sample std only 72/411).
  - burst_count = 1 + number of gaps above ~1.0 s (bracket 0.915–1.003 s; > vs ≥ unknown).
  - Sizes are **Ethernet frame lengths over IPv4**: 60-B padded minimum; 66/74-B TCP control frames; 583 = 66 + 517-B ClientHello; 1294 = 42 + 1252 (Meta mvfst); 1292 = 42 + 1250 (Chrome).
  - min_iat = 0 in 97% of flows (batched timestamps).
  - Unexplained: the client's first TCP packet is 145–175 B (a stock SYN is 74 B).
- **Facebook/Instagram types:** rules reproduced exactly by Ward clustering (adjusted Rand 1.00).

  | Type | FB | IG |
  |---|---:|---:|
  | TCP keep-alive | 3 | 0 |
  | Short TCP (stalled handshake) | 1 | 1 |
  | Short QUIC fetch | 2 | 1 |
  | QUIC burst | 2 | 2 |
  | Slow QUIC trickle | 3 | 5 |
  | QUIC media download | 0 | 6 |
  | QUIC upload-heavy | 0 | 4 |

  Ranges are in the report.
- **Labelling clue:** 6/11 facebook flows start within 10 s of an Instagram flow, vs 5–11% for other apps and 8% of capture time; 11/11 are within 60 s. No YouTube flow exceeds 0.4 MB (no video streams). Labels look destination-based, not foreground-app based (undocumented).

## Caveats

- The frame-length and population-std conclusions are inferences: consistent on every flow, but not documented.
- The labelling clue is circumstantial. Facebook and Instagram could simply have been used in alternation.
- No pcap was available, so the protocol and timeout are untested.

## Decision

**No-go.** Any later pilot needs all three: the user reverses the "only the given dataset" decision; the organisers confirm in
writing (Task 1; and whether Task 2 is allowed); and a one-day pilot passes the extractor and proximity gates.

Main blockers:
- Labels are probably destination-based, which breaks session labelling exactly for facebook/instagram.
- Task 2 is literally restricted to its own files.
- Unexplained opening sizes.
- Payoff is below the leaderboard noise (2 test facebook flows).

## Next

None. If the conditions are met: write to the organisers (labelling method, Task 2, use of own SNI for labelling), then run the pilot from report §5–6.

## Script output

```
== 1. flow definition
  flows 411; packets per flow min 5, max 59290; Task 2 packets per flow: [np.int64(5)]
  start_rel 0 .. 2675.5 s; last packet at 2677.8 s (44.6 min)
  flow_id numbers 3 .. 1405 (411 kept); Spearman(flow_id, start_rel) = 1.000
  longest flow 1304 s; largest gap inside any flow 239.9 s (idle timeout > this)
  ten largest gaps: [194.3 195.3 199.3 205.  209.2 213.4 213.4 214.2 223.  239.9]
  flows with no upstream / no downstream packet: Task 1 0 / 0, Task 2 0 / 1
  task1_static: durations on a 1 µs grid 1.000; min_iat == 0 in 97.3% of flows; smallest non-zero gap 9.1 µs
  task2_realtime_prefix5: durations on a 1 µs grid 0.990; min_iat == 0 in 36.3% of flows; smallest non-zero gap 25.0 µs
  transport: {'udp': 214, 'tcp': 197}  server_port: {443: 409, 80: 2}

== 2. feature formulas (all 411 flows)
 task1_static
  bytes_up is an integer                                             411/411
  mean_pkt_size_up = bytes_up / packet_count_up (0 if no packets)    411/411
  std_pkt_size_up = 0 when <= 1 packet                               0/0
  2 packets: mean ± std are integers (population std, ddof 0)        1/1
  std_pkt_size_up^2 <= (max size - mean)(mean - 60) with max 1514    411/411
  bytes_down is an integer                                           411/411
  mean_pkt_size_down = bytes_down / packet_count_down (0 if no packets) 411/411
  std_pkt_size_down = 0 when <= 1 packet                             0/0
  2 packets: mean ± std are integers (population std, ddof 0)        2/2
  std_pkt_size_down^2 <= (max size - mean)(mean - 60) with max 1514  411/411
  mean_iat = duration / (packets - 1)                                411/411
  min_iat <= mean_iat <= max_iat <= duration                         411/411
  min_iat + max_iat <= duration (>= 3 packets)                       411/411
  std_iat^2 <= (max_iat - mean_iat)(mean_iat - min_iat) (population std) 411/411
  up_down_packet_ratio = up / max(down, 1)                           411/411
  up_down_byte_ratio = bytes_up / max(bytes_down, 1)                 411/411
  burst_count = 1 when max_iat < 1.0 s                               166/166
  burst_count >= 2 when max_iat >= 1.0 s                             245/245
  1 <= burst_count <= packets                                        411/411
  (burst_count - 1) gaps of >= 1.0 s fit in duration                 411/411
   burst threshold bracket: largest max_iat with 1 burst 0.9146 s, smallest max_iat with >= 2 bursts 1.0302 s
 task2_realtime_prefix5
  bytes_up is an integer                                             411/411
  mean_pkt_size_up = bytes_up / packet_count_up (0 if no packets)    411/411
  std_pkt_size_up = 0 when <= 1 packet                               9/9
  2 packets: mean ± std are integers (population std, ddof 0)        177/177
  std_pkt_size_up^2 <= (max size - mean)(mean - 60) with max 1514    411/411
  bytes_down is an integer                                           411/411
  mean_pkt_size_down = bytes_down / packet_count_down (0 if no packets) 411/411
  std_pkt_size_down = 0 when <= 1 packet                             50/50
  2 packets: mean ± std are integers (population std, ddof 0)        175/175
  std_pkt_size_down^2 <= (max size - mean)(mean - 60) with max 1514  410/410
  mean_iat = duration / (packets - 1)                                411/411
  min_iat <= mean_iat <= max_iat <= duration                         411/411
  min_iat + max_iat <= duration (>= 3 packets)                       411/411
  std_iat^2 <= (max_iat - mean_iat)(mean_iat - min_iat) (population std) 411/411
  up_down_packet_ratio = up / max(down, 1)                           411/411
  up_down_byte_ratio = bytes_up / max(bytes_down, 1)                 411/411
  burst_count = 1 when max_iat < 1.0 s                               385/385
  burst_count >= 2 when max_iat >= 1.0 s                             26/26
  1 <= burst_count <= packets                                        411/411
  (burst_count - 1) gaps of >= 1.0 s fit in duration                 411/411
   burst threshold bracket: largest max_iat with 1 burst 0.7818 s, smallest max_iat with >= 2 bursts 1.0030 s
 Task 2 gaps: population or sample std? (4 gaps: the middle two are fixed by sum, min, max and std)
  middle gaps real and within [min_iat, max_iat] under population std (ddof 0) 411/411
  middle gaps real and within [min_iat, max_iat] under sample std (ddof 1) 72/411
 Task 2 opening vs Task 1 flow
  same flow_id, start_rel, transport, server_port, split             411/411
  prefix packets and bytes <= full, per direction                    411/411
  prefix duration <= full; prefix max_iat <= full; prefix min_iat >= full 411/411
  prefix burst_count <= full burst_count                             411/411
  flows with exactly 5 packets: Task 1 row == Task 2 row             1/1

== 3. packet sizes (exactly known from 1-2 packets or std 0)
  Task 2 tcp up: 66 sizes; smallest [66, 133, 145, 147, 148]; most common [(145, 48), (147, 9), (148, 4), (156, 2), (133, 1), (66, 1), (150, 1)]
  Task 2 tcp down: 375 sizes; smallest [60, 66, 74]; most common [(74, 255), (66, 118), (60, 2)]
  Task 2 udp up: 380 sizes; smallest [126, 127, 128, 142, 143]; most common [(1381, 72), (1365, 61), (1366, 57), (1375, 54), (1294, 41), (1377, 21), (1367, 20), (1363, 18)]
  Task 2 udp down: 168 sizes; smallest [66, 68, 69, 73, 82]; most common [(82, 69), (1294, 67), (1292, 16), (84, 6), (85, 3), (109, 2), (68, 1), (73, 1)]
  smallest mean size anywhere: up 74, down 60; largest mean size 1421
  Task 2 TCP openings (up/down packets): {(2, 3): 27, (3, 2): 127, (4, 1): 43}
  Task 2 UDP openings (up/down packets): {(1, 4): 9, (2, 3): 150, (3, 2): 48, (4, 1): 6, (5, 0): 1}
  TCP 3 up / 2 down: down bytes [(140, 118), (148, 8), (120, 1)]; up sizes [((66, 145, 583), 46), ((66, 145, 277), 11), ((66, 145, 265), 11), ((66, 145, 282), 8), ((66, 145, 762), 5), ((66, 147, 583), 5), ((145, 145, 145), 4), ((66, 159, 626), 4)]
  TCP 2 up / 3 down: up pairs [((145.0, 145.0), 18), ((147.0, 147.0), 4), ((148.0, 148.0), 2), ((133.0, 147.0), 1)]; down bytes [(222, 26), (250, 1)]
  TCP 4 up / 1 down: down bytes [(74, 43)]; up bytes 1763..2647

== 4. Facebook/Instagram traffic types (labelled flows)
  TCP keep-alive: facebook 3, instagram 0
    duration 235.75-1122.16 s | packets 42-107 | bytes up 1925-7397 | bytes down 1468-4735 | mean size up 77-182 down 82-104 | mean_iat 5.75-10.59 s | max_iat 75.2-165.2 s | bursts 6-19
    flows: 000024 (fa), 000610 (fa), 001324 (fa)
    openings: [('tcp 3/2 661/140', 2), ('tcp 2/3 216/250', 1)]
  short TCP: facebook 1, instagram 1
    duration 24.62-39.10 s | packets 14-19 | bytes up 640-921 | bytes down 444-592 | mean size up 80-84 down 74-74 | mean_iat 1.89-2.17 s | max_iat 8.8-16.4 s | bursts 6-7
    flows: 000216 (in), 000231 (fa)
    openings: [('tcp 2/3 294/222', 1), ('tcp 2/3 280/222', 1)]
  short QUIC fetch: facebook 2, instagram 1
    duration 0.12-0.17 s | packets 16-16 | bytes up 2210-2250 | bytes down 5079-5128 | mean size up 321-369 down 508-570 | mean_iat 0.01-0.01 s | max_iat 0.0-0.1 s | bursts 1-1
    flows: 000809 (fa), 001168 (fa), 001185 (in)
    openings: [('udp 2/3 1606/2365', 1), ('udp 2/3 1606/2366', 1), ('udp 1/4 1365/4594', 1)]
  QUIC burst: facebook 2, instagram 2
    duration 20.88-39.78 s | packets 40-148 | bytes up 9131-38520 | bytes down 15845-99015 | mean size up 529-1304 down 360-900 | mean_iat 0.14-0.66 s | max_iat 12.8-15.2 s | bursts 5-5
    flows: 000210 (in), 000215 (in), 000799 (fa), 001145 (fa)
    openings: [('udp 2/3 2661/1657', 1), ('udp 2/3 2661/1656', 1), ('udp 1/4 1365/4596', 1), ('udp 1/4 1365/4590', 1)]
  slow QUIC trickle: facebook 3, instagram 5
    duration 178.60-1113.40 s | packets 30-263 | bytes up 8268-54252 | bytes down 4779-54216 | mean size up 161-553 down 93-532 | mean_iat 0.92-9.85 s | max_iat 15.0-51.8 s | bursts 5-25
    flows: 000003 (in), 000368 (fa), 000379 (in), 000477 (in), 000617 (fa), 001331 (fa), 000359 (in), 000360 (in)
    openings: [('udp 2/3 2661/1657', 2), ('udp 1/4 1367/2931', 2), ('udp 5/0 6470/0', 1), ('udp 1/4 1367/2930', 1)]
  QUIC media download: facebook 0, instagram 6
    duration 230.81-1125.19 s | packets 2842-59290 | bytes up 280347-711567 | bytes down 2278856-69489795 | mean size up 191-540 down 831-1247 | mean_iat 0.01-0.25 s | max_iat 15.0-51.3 s | bursts 39-75
    flows: 000604 (in), 000837 (in), 000838 (in), 001321 (in), 001328 (in), 001325 (in)
    openings: [('udp 2/3 1509/1656', 2), ('udp 2/3 1510/1656', 2), ('udp 2/3 1494/1656', 1), ('udp 1/4 1367/2930', 1)]
  QUIC upload-heavy: facebook 0, instagram 4
    duration 228.52-1122.66 s | packets 972-2920 | bytes up 600748-986497 | bytes down 46899-150428 | mean size up 651-934 down 107-144 | mean_iat 0.17-0.78 s | max_iat 9.5-51.1 s | bursts 35-168
    flows: 000813 (in), 001323 (in), 000609 (in), 001327 (in)
    openings: [('udp 2/3 2661/1657', 2), ('udp 2/3 1494/1656', 1), ('udp 2/3 1493/1656', 1)]
  cross-check: Ward clustering into 7 groups vs rule types, adjusted Rand 1.00
col_0                0  1  2  3  4  5  6
type                                    
QUIC burst           0  0  0  4  0  0  0
QUIC media download  0  6  0  0  0  0  0
QUIC upload-heavy    0  0  0  0  4  0  0
TCP keep-alive       0  0  3  0  0  0  0
short QUIC fetch     0  0  0  0  0  3  0
short TCP            0  0  0  0  0  0  2
slow QUIC trickle    8  0  0  0  0  0  0

== 5. labelling clue: share of labelled flows starting within w s of an Instagram flow (understanding only)
  w = 10 s: facebook 6/11 (55%), google 15/131 (11%), instagram 14/19 (74%), mozilla 2/41 (5%), x 5/73 (7%), youtube 5/55 (9%); share of capture time within w of an Instagram flow 8%
  w = 60 s: facebook 11/11 (100%), google 72/131 (55%), instagram 14/19 (74%), mozilla 30/41 (73%), x 56/73 (77%), youtube 26/55 (47%); share of capture time within w of an Instagram flow 38%
```
