---
title: "053: Where do the organisers' TCP flows start?"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for three TCP flow-start rules in our capture extractor, compared with the released flow shapes.
source:
  - 052_iphone_pilot.md
  - ../reports/exp041_capture_feasibility.md
  - ../src/capture_extract.py
  - ../src/capture_checks.py
  - ../data/captures/sid-iphone-20261008T233855Z/sessions.csv
experiment:
  id: '053'
  tasks:
  - task1
  lever: data
  status: measured
  verdict: 'TCP flow start: dropping the handshake moves openings toward the dataset''s 3 up / 2 down (TVD 0.62 -> 0.26) but misses the frozen 0.15 rule; extractor default unchanged'
---

# 053: Where do the organisers' TCP flows start?

**Status: done 2026-10-09. Protocol frozen before any code change (commit `93f9304`); executed and verified.**
**Verdict: H1 partly supported; no variant meets the frozen rules; extractor default stays `syn`.** Results are below the protocol.
Do not edit the frozen sections after execution starts; record deviations in the execution ledger.
Task states live in TODO.md. The previous step is [052](052_iphone_pilot.md).

## Question

Do the released TCP flows start after the TCP handshake, or count only packets that carry data?
A yes for one rule means our extractor must use that rule before captured flows can resemble the released flows.

## Evidence before this experiment

| Observation | Source |
|---|---|
| Released TCP openings (first 5 packets, up/down): 3/2 in 66%, 4/1 in 23%, 2/3 in 11% | `capture_checks.py` opening report, 052 |
| Our cellular TCP openings: 4/1 in 65%, 3/2 in 12%, 5/0 in 24% | [052](052_iphone_pilot.md), `gates-cellular.txt` |
| Released first client TCP packet (smaller of two up packets): 145-175 B, unexplained | 041, 052 |
| Our first client TCP packet: the SYN, 66 B; then SYN-ACK down, ACK up (66 B), then client data up | 052 packet trace |
| Gate 2 on the cellular session: adversarial AUC 0.914, FAIL | 052 |

Our extractor starts a TCP flow at the client SYN. Three of the first five packets are then handshake packets without data.

## Hypotheses

- **H1, handshake excluded:** the organisers' flows start after the three-way handshake.
- **H2, data packets only:** the organisers' flows count only TCP packets that carry data (no pure ACKs anywhere).
- **H0:** neither rule moves our TCP openings close to the released ones; the difference has another cause
  (phone, operating system, app version or capture point).

H1 and H2 do not obviously explain the 145-175 B first client packet: a TLS ClientHello is normally larger.
This experiment measures that; it does not assume it.

## Frozen variants

The extractor gets one new option, `--tcp-start`. UDP flows are the same in all variants.

| Variant | `--tcp-start` | TCP packets kept |
|---|---|---|
| A (reference) | `syn` (default) | All packets from the client SYN, as now |
| B | `after-handshake` | Drop the client SYN without ACK, the server SYN-ACK, and the first client packet after the SYN-ACK when it has no data |
| C | `data-only` | Drop every TCP packet without data (zero TCP payload) |

Flows that keep fewer than 5 packets after the cut are dropped, as before. All other extractor rules are unchanged.

## Data

- Pilot group `sid-iphone-20261008T233855Z`, raw pcapng in gitignored `data/captures/raw/`. Session hashes are in each
  session's `packets.sha256` and are re-checked at execution.
- Primary data: `04-instagram-feed-cellular` (QUIC works, 052). Secondary: the five Wi-Fi app sessions (02-06), where QUIC
  is blocked; their TCP flows are still valid TCP flows.
- Original data: train+validation features and labels only, through `capture_checks.py` (330 flows). No test labels,
  no metadata label counts, no identifiers.

## Frozen measurements

| ID | Measurement | Computed on |
|---|---|---|
| M0 | Reference reproduction: variant A output files are byte-identical to the 052 CSVs | all sessions |
| M1 | Total variation distance (TVD) between captured and original TCP opening shapes (up/down counts of the first 5 packets) | all app sessions pooled, and cellular alone |
| M2 | Smaller of the two client packets in openings with exactly 2 up packets: distribution, and share in 133-175 B | all app sessions pooled |
| M3 | Gate 1 (identities, opening consistency) | each variant, all sessions |
| M4 | Gate 2 on the cellular session: adversarial AUC, per-app row, nearest original labels | each variant |

TVD = half the sum of absolute differences between the two shape distributions (0 = identical, 1 = disjoint).

## Frozen decision rules

- **Explains the TCP opening gap:** M1 TVD (all app sessions pooled) <= 0.15.
- **Extractor default changes** to a variant only if: it explains the gap, M3 gate 1 passes, and M4 AUC is at least
  0.05 lower than variant A's. If both B and C qualify, choose the one with the lower pooled TVD.
- **Training use** still requires gate 2 to pass (052 rules). Not expected from this experiment alone.
- **Stop:** if no variant lowers the pooled TVD below A's by at least 0.10, record H0 and ask Charles and the organisers
  how flows were cut. Do not try further cut rules in this experiment.

## Boundaries

- Measurement of our own captures and the extractor only. No model is trained; production stays frozen at 5eb9a8b.
- No reading of payload contents, SNI, DNS or addresses. The TCP payload length comes from IP and TCP header length fields.
- Everything runs on this Mac.

## Evidence plan

- Script: `src/exp053_tcp_flow_start.py` (runs all variants and both gates, writes the evidence folder).
- Evidence folder: `data/captures/sid-iphone-20261008T233855Z/053-tcp-flow-start/`: per variant and session the four
  extractor CSVs, gate outputs, `summary.json`, and `manifest.json` with SHA-256 of every input pcapng and output file,
  the source commit and the commands.
- Unit tests for the three cut rules in `src/test_capture_extract.py`.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `93f9304`, before any code change |
| 2026-10-09 | `--tcp-start` option, unit tests, runner committed | `36f6913`; self-test passes (new check: payload length, three rules, split after FIN) |
| 11:38:28-11:38:46 | Attempt 1 (`36f6913`, clean tree) | All 30 commands exit 0 and all files written; the final console print failed on a numpy bool. Kept as `053-tcp-flow-start-attempt1-failed-print/` |
| 2026-10-09 | Fix: cast bools before JSON | `57a5942` |
| 11:39:03-11:39:21 | Attempt 2 (`57a5942`, clean tree) | Complete. Evidence `053-tcp-flow-start/`: 17 input and 103 output SHA-256 in `manifest.json` |
| after attempt 2 | Verification | All 120 manifest hashes re-checked: match. Attempts 1 and 2: 102 of 103 output files identical; only `summary.json` differs (bool formatting) |
| after attempt 2 | Unplanned check (not a frozen measurement) | Count of TCP frames > 1514 B per session, to explain the gate 1 failure of variant C |

No deviation from the frozen variants, data, measurements or decision rules.

## Results

Evidence: `summary.json` and
`manifest.json`.

**M0 reference reproduction: passed.** Variant A reproduces all 052 CSVs byte for byte.

TCP opening shapes (up/down in the first 5 packets), all app sessions pooled:

| Shape | Original (train+val) | A `syn` | B `after-handshake` | C `data-only` |
|---|---:|---:|---:|---:|
| 1/4 | 0 | 0.01 | 0.07 | 0.05 |
| 2/3 | 0.11 | 0.01 | 0.29 | 0.47 |
| 3/2 | **0.66** | 0.15 | **0.45** | 0.07 |
| 4/1 | 0.23 | **0.82** | 0.18 | 0.42 |
| 5/0 | 0 | 0.02 | 0.01 | 0 |

| Measurement | A `syn` | B `after-handshake` | C `data-only` |
|---|---:|---:|---:|
| M1 TVD, all app sessions pooled (rule: <= 0.15) | 0.621 | **0.260** | 0.599 |
| M1 TVD, cellular only | 0.654 | 0.228 | 0.074 |
| M2 openings with 2 up packets | 1 | 50 | 79 |
| M2 smaller client packet, most common (B) | 66 (SYN) | 235, 226, 217, 219 | 235, 217, 226, 219 |
| M2 share in 133-175 B (original 0.94) | 0 | 0 | 0 |
| M3 gate 1 | PASS | PASS | **FAIL** |
| M4 gate 2 cellular, adversarial AUC | 0.914 | 0.881 | 0.920 |
| M4 instagram same-label 5-NN (original 0.41) | 0.09 | 0.11 | 0.12 |
| M4 nearest original labels (cellular instagram) | google 16, x 9, instagram 4 | google 15, x 5, instagram 4, youtube 4 | google 15, x 5, instagram 4 |

Frozen decision rules applied (`summary.json`, `decision`):

| Rule | B | C |
|---|---|---|
| Explains the gap (pooled TVD <= 0.15) | ❌ 0.260 | ❌ 0.599 |
| Gate 1 passes | ✅ | ❌ |
| AUC at least 0.05 below A | ❌ 0.033 lower | ❌ 0.006 higher |
| TVD drop vs A (stop if both < 0.10) | 0.361 | 0.022 |

Outcome: **no new extractor default** (stays `syn`). **No stop under H0**, because B lowers the TVD by 0.36.
**Training use: no** (gate 2 fails for every variant).

### Why variant C fails gate 1 (unplanned check)

Gate 1 fails on "mean down packet size in [60, 1514]" for 6 of 260 flows. Cause: on **cellular**, the phone hands
RVI received TCP segments that are already merged (receive offload): 46 of 815 TCP frames (5.6%) are larger than 1514 B,
up to 4,162 B. The Wi-Fi sessions have none (largest 1,440 B). In variant A the small ACKs keep the flow mean below
1,514 B, so gate 1 passes there but does not see the problem. The original data never exceeds an Ethernet frame.

## Interpretation

- **H1 (handshake excluded) is partly supported.** Dropping the handshake moves the most common opening to 3 up / 2 down,
  as in the original, and cuts the opening distance by more than half. It does not reach the frozen threshold, and the
  model-facing gap (AUC) barely moves.
- **H2 (data packets only) is not supported** on pooled sessions. Its low cellular TVD (0.074) comes from one 26-flow
  session and fails gate 1, so it is not evidence for H2.
- **The 145-175 B first client packet stays unexplained.** After the handshake our first client packet is 217-235 B,
  about 70-90 B larger, in every variant. A different TLS stack, phone or app version could explain this; this experiment
  cannot separate them.
- **The gate 2 gap is not mainly about where TCP flows start.** The cellular Instagram flows are still nearest to
  google and x flows under every rule.

## Decision

Keep `--tcp-start syn` as the default. Keep `after-handshake` as an option for parity work. Captured flows stay out of
training. Production unchanged (frozen at 5eb9a8b).

## Restart point and next

1. Ask Charles and the organisers how TCP flows were cut, and what the 145-175 B first client packet is. Our data says
   the handshake is probably not counted, but that alone does not make our flows match.
2. Cellular captures need a fix for merged segments (> 1514 B): either split them into MTU-sized frames in the extractor,
   or turn the gate 1 size check into a per-packet maximum. Decide before any cellular capture is used.
3. Gate 2 remains the blocker. The next most likely cause is the device and app stack (iOS app versions vs the organisers'
   phone), which only Charles or the organisers can confirm.
