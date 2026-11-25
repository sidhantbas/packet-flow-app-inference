---
title: "054: Independent re-extraction of the pilot and consistency with the training records"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for a clean-room second extractor on the iPhone pilot, and a per-column comparison of captured flows with the released train+validation flows.
source:
  - 052_iphone_pilot.md
  - 053_tcp_flow_start.md
  - ../reports/exp041_capture_feasibility.md
  - ../data/captures/sid-iphone-20261008T233855Z/sessions.csv
experiment:
  id: '054'
  tasks:
  - task1
  lever: data
  status: measured
  verdict: Independent clean-room extraction matches all 11,424 values; captured Meta packet sizes mostly match, durations, gaps and bursts do not
---

# 054: Independent re-extraction and consistency with the training records

**Status: done 2026-10-09. Protocol frozen before any code or agent run (commit `9d5f0b3`); executed and verified.**
**Verdict: A passes (11,424 of 11,424 values match). B: packet sizes mostly match the training records; time and length do not.**
Results are below the protocol.
Do not edit the frozen sections after execution starts; record deviations in the execution ledger.
Previous steps: [052](052_iphone_pilot.md), [053](053_tcp_flow_start.md). Task states: TODO.md.

## Questions

1. **A, verification:** does a second extractor, written without seeing ours, produce the same 21 columns from the
   same pcapng files?
2. **B, consistency:** which feature columns make the captured flows different from the released train+validation
   flows of the same app?

## Why

Gate 2 fails ([052](052_iphone_pilot.md), [053](053_tcp_flow_start.md)). Before we blame the phone or the network, we must
know that our extractor is correct (A), and which columns carry the difference (B).

## A. Clean-room re-extraction

- **Who:** a separate AI agent (Claude Code subagent) with a written specification only.
- **Not allowed to read:** `src/capture_extract.py`, `src/test_capture_extract.py`, `src/exp053_tcp_flow_start.py`, or any
  feature CSV under `data/captures/sid-iphone-20261008T233855Z/`.
- **Input:** the raw session pcapng files in `data/captures/raw/sid-iphone-20261008T233855Z/` (sessions 01-07 and
  `04-instagram-feed-cellular`).
- **Specification:** the experiment 041 flow and column definitions as given in the agent brief (flow key, phone address
  rule, ports, idle timeout, SYN-after-FIN split, minimum 5 packets, frame-size rule, µs timestamps, population std,
  burst gap 1.0 s, ratio rule, first-5-packet Task 2 table, `start_rel` origin, flow order and ids). Flows start at the SYN.
- **Output:** `src/exp054_independent_extract.py` and, per session, `task1_features.csv` and `task2_features.csv` in
  `data/captures/sid-iphone-20261008T233855Z/054-independent-extraction/independent/`.
- **Comparison (by us, after the agent finishes):** against variant A of 053 (identical to the 052 CSVs).

Frozen pass rule for A: in every session the flow count is equal, flows pair up by id, integer columns are equal, and
float columns agree within 1e-6 relative or 1e-9 absolute, for 100% of values. Any mismatch is reported per column and
explained before any other use of the captures.

## B. Consistency with the training records

- Captured flows: 053 variant A (`syn`) Task 1 tables, labelled by session app; three groups reported separately:
  Wi-Fi app sessions (facebook, instagram, youtube), and cellular instagram.
- Original flows: Task 1 train+validation features and labels (330 flows) of the same app. No test data.
- Columns: the 16 Task 1 statistic columns used by gate 2 (without `min_iat`), plus `min_iat` and `transport` reported only.
- Per app and column, frozen measurements:
  - single-column AUC, original vs captured (0.5 = same, 1.0 = fully separable);
  - Kolmogorov-Smirnov statistic;
  - captured median vs original median and original 5th-95th percentile range; share of captured values inside that range.
- A column is **inconsistent** when its single-column AUC is >= 0.80 (descriptive flag, not a gate).

## Boundaries

- IP addresses are used only in memory, to form flow keys and find the phone's address. They are never written,
  printed, logged or looked up (no WHOIS, reverse DNS, SNI, DNS or payload parsing). AGENTS.md condition 3 and
  `.mission.md` OUT OF SCOPE apply.
- Measurement only: no model training, production stays frozen at 5eb9a8b. Everything runs on this Mac.

## Evidence plan

Evidence folder `data/captures/sid-iphone-20261008T233855Z/054-independent-extraction/`: the agent's CSVs, the
comparison table, the consistency tables, `summary.json`, and `manifest.json` with SHA-256 of inputs and outputs.
Scripts: `src/exp054_independent_extract.py` (agent), `src/exp054_consistency.py` (ours).

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `9d5f0b3`, before any code or agent run |
| before 11:48 (about 2.5 min) | Clean-room agent writes and runs `src/exp054_independent_extract.py` | 8 sessions in 0.8 s; agent confirms it did not read the forbidden files and wrote, printed or logged no address |
| 2026-10-09 | Agent script reviewed (prints counts only, writes CSVs only, does not import our extractor) and both scripts committed | `c350294` |
| 11:48:33-11:48:34 | `src/exp054_consistency.py` (Parts A and B) on `c350294`, clean tree | Evidence `054-independent-extraction/`; 67 SHA-256 in `manifest.json`, all re-checked: match |

No deviation from the frozen protocol. Part A includes the two empty tables of `07-idle-after` (0 flows in both extractors).

## Results

Evidence: `summary.json`,
`comparison.csv`,
`consistency_<group>.csv` and `manifest.json`.

### A. Clean-room re-extraction: PASS

| Check | Result |
|---|---|
| Tables compared (8 sessions × Task 1 and Task 2) | 16 |
| Flow counts equal in every session (5, 14, 14, 68, 60, 79, 0, 32) | ✅ |
| Values compared / matching under the frozen tolerance | 11,424 / 11,424 |

Facts the independent agent found that our documents did not record:

- The pcapng files from `tcpdump -P` on `rvi0` hold per-interface blocks: link type 1 (Ethernet) for Wi-Fi and link type
  0 (BSD null) for cellular, not PKTAP records. Both extractors read them the same way.
- Each file has 4-14 Apple-specific blocks of type `0x80000001` (process metadata); both extractors ignore them.
- In `07-idle-after` all 8 addresses have one peer each, so the automatic phone rule marks all of them as the phone and
  the session has 0 flows. Only 3 packets there use port 443, so no flow is lost.

### B. Consistency with the training records

Single-column AUC between captured flows and the train+validation flows of the same app (0.5 = same, 1 = separable).
Flag: >= 0.80. Original group sizes are small: facebook 11, instagram 19, youtube 55.

| Group (captured n) | Inconsistent columns (AUC) | Consistent columns (AUC < 0.65) |
|---|---|---|
| Wi-Fi facebook (28) | mean_iat 0.89, std_iat 0.84, max_iat 0.81 | mean up size, both size stds, packet counts, bytes down, ratios, transport (mean down size 0.70, bytes up 0.68 in between) |
| Wi-Fi instagram (128) | duration 0.93, burst_count 0.92, max_iat 0.86, transport 0.82, packet_count_down 0.81 | mean sizes in both directions, std down size, byte ratio |
| Wi-Fi youtube (79) | std_pkt_size_up 0.81 | packet counts, burst_count, mean down size, packet ratio |
| Cellular instagram (32) | burst_count 0.91, duration 0.90, max_iat 0.85, packet_count_down 0.84, bytes_up 0.81 | packet-size means and stds, byte ratio, mean_iat |

Medians behind the largest differences:

| Group | Column | Training median | Captured median |
|---|---|---:|---:|
| Wi-Fi facebook | mean_iat | 5.75 s | 0.013 s |
| Wi-Fi facebook | duration | 205 s | 1.5 s |
| Wi-Fi instagram | duration | 235 s | 11.5 s |
| Cellular instagram | duration | 235 s | 2.4 s |
| Cellular instagram | burst_count | 35 | 2 |
| Cellular instagram | packet_count_down | 329 | 16.5 |
| Wi-Fi youtube | std_pkt_size_up | 546 B | 314 B |

## Interpretation

- **Our extractor is correct.** An implementation written from the definitions alone reproduces every value. The gate 2
  failure is not an extraction bug.
- **Packet sizes are mostly consistent; time and length are not.** For facebook and instagram most size columns are close
  to the training records (AUC < 0.65; exceptions: facebook mean down size 0.70, Wi-Fi instagram std up size). The inconsistent columns are duration, gaps, bursts and counts. The training Meta flows are
  long-lived (median 205-235 s, 35 bursts); ours last seconds.
- **Likely cause: session design, not the phone.** 60-second sessions with apps launched from closed cannot contain the
  long-lived connections and slow keep-alive traffic that dominate the training Meta flows. [049](049_signal_check.md)
  already found that Meta sessions need >= 20 minutes. Transport (instagram on Wi-Fi) is the QUIC block of 052.
- **YouTube differs mainly in upstream size variation** (std 314 vs 546 B), a smaller effect.

## Decision

Captured flows stay out of training (gate 2 still fails). Keep our extractor; no change. Production unchanged (5eb9a8b).

## Restart point and next

1. Next capture: on cellular (052), with long sessions (>= 20 minutes per app, app left running in normal use) so that
   long-lived flows exist. Then rerun gates 1-2 and this consistency check on the new group.
2. Merged cellular TCP segments (053) still need handling before cellular captures are used for training.
3. The 145-175 B first client packet and the flow-cutting question go to Charles and the organisers (053).
