---
title: '052: iPhone capture pilot (Charles''s handoff) through gates 1 and 2'
created: 2026-10-09
creator: sidhantbas
description: Do flows from a short iPhone USB RVI pilot pass src/capture_checks.py gates 1 and 2?
experiment:
  id: '052'
  tasks:
  - task1
  lever: data
  status: measured
  verdict: 'iPhone capture pilot: gate 1 pass, gate 2 fail (AUC 0.993); the pilot''s Wi-Fi blocked QUIC for Instagram/YouTube; not usable for training'
---
# 052: iPhone capture pilot (Charles's handoff) through gates 1 and 2

- **Date:** 2026-10-09
- **Question:** Do flows from a short iPhone USB RVI pilot pass `src/capture_checks.py` gates 1 and 2?
- **Status:** done
- **Script:** `src/capture_pilot.sh` (recording), `src/capture_extract.py` (features), `src/capture_checks.py` (gates)
- **Runs:** no CV run. Features and gate output: `data/captures/sid-iphone-20261008T233855Z/` (`sessions.csv`, per-session
  feature CSVs, `gates.txt`). Raw pcapng, `summary.md`, `environment.md`: gitignored `data/captures/raw/sid-iphone-20261008T233855Z/`.
- **Reference:** production frozen at 5eb9a8b (not touched)

## Hypothesis

Charles's 228-fit test (afe-002) shows Facebook F1 rises with the number of real Facebook training rows. If our own captures
look like the released flows (gates 1-2), they could add Task 1 training rows (042 plan, AGENTS.md "Own captures").

## Setup

- iPhone 17 Pro (iOS 26.6.2) over USB RVI on this Mac; `tcpdump -i rvi0 -nn -p -P -s 0` (native pcapng, PKTAP metadata).
  Wi-Fi only, no VPN or Private Relay; Facebook 582.0.0, Instagram 450.1.0, YouTube 21.40.5; apps launched from closed.
- Charles's pilot: 2 preflights, then 7 sessions of 60 s (idle, FB feed, FB Reels, IG feed, IG Reels, YouTube, idle), 30 s gaps.
- Labels: the session's app for every flow whose first packet falls in the recording window (`sessions.csv`); idle
  sessions get label `idle` and are left out of gate 2. 240 flows with >= 5 packets (facebook 28, instagram 128, youtube 79, idle 5).
- RVI first failed with `bootstrap_look_up(): 1102` until `com.apple.rpmuxd` was loaded with `launchctl`.

## Results

Acquisition: every session 0 kernel drops, readback clean, hashes verify. PKTAP process names put 96-99% of each app
session's packets on that app (Facebook, Instagram, YouTube), so per-flow attribution is possible.

| Gate | Result |
|---|---|
| 1 extractor identities | **PASS**: all 041 identities hold; Task 2 opening consistent with Task 1 flow 240/240 |
| 2 proximity | **FAIL**: adversarial AUC 0.993 (gate <= 0.70); every app row FAR |

| App | n | median NN distance (orig 90th pct) | same-label 5-NN (orig) | nearest original label |
|---|---:|---|---|---|
| facebook | 28 | 1.94 (2.15) | 0.01 (0.16) | google 10, youtube 8, instagram 5, x 4, facebook 1 |
| instagram | 128 | 2.17 (2.01) | 0.12 (0.41) | google 64, x 40, youtube 19, mozilla 4, instagram 1 |
| youtube | 79 | 1.42 (1.25) | 0.31 (0.59) | google 38, x 20, youtube 16, mozilla 3, facebook 1, instagram 1 |

Main cause found by tracing flows packet by packet: **QUIC got no reply for Instagram and YouTube on this network.**

| Session | UDP flows | UDP flows with no reply | MB down over TCP / UDP |
|---|---:|---:|---|
| Facebook feed / Reels | 8 / 9 | 2 / 2 | 0.1 / 33.4 · 0.0 / 43.3 |
| Instagram feed / Reels | 20 / 19 | 20 / 19 | 27.9 / 0.0 · 48.7 / 0.0 |
| YouTube | 17 | 17 | 39.9 / 0.0 |

Unanswered QUIC flows repeat the client's first packet with exponential back-off (0.1, 0.2, 0.4, 0.8 ... s; 1294 B) and give
5-up/0-down openings (88% of captured UDP openings vs 1% in the original). The apps then fell back to TCP, which is why
Instagram is mostly TCP here (released train: 13 of 14 Instagram flows UDP). Facebook's own QUIC worked.

QUIC check on cellular (2026-10-09, `04-instagram-feed-cellular`, 60 s Instagram feed, Wi-Fi off; 0 drops, hash OK;
packets on `pdp_ip0`): Instagram QUIC works there, so **the home Wi-Fi blocks QUIC** for Instagram and YouTube.

| Network | Flows | UDP flows | UDP with no reply | MB down UDP / TCP |
|---|---:|---:|---:|---|
| Wi-Fi (`04-instagram-feed`) | 68 | 20 | 20 | 0.0 / 27.9 |
| Cellular (`04-instagram-feed-cellular`) | 32 | 15 | 2 | 29.0 / 0.2 |

Gates on the cellular session alone (32 flows): gate 1 PASS; gate 2 still FAIL but much closer: median NN distance 1.56
(orig 90th pct 2.01, now inside), same-label 5-NN 0.09 (orig 0.41), adversarial AUC 0.914 (Wi-Fi sessions 0.993), nearest
original labels google 16, x 9, instagram 4. UDP openings now mostly 2 up / 3 down (40%, original 70%).

Other differences (for Charles's parity check):

- TCP openings: captured mostly 4 up / 1 down (SYN 66 B, SYN-ACK, ACK, then client data); original mostly 3 up / 2 down with a
  first client packet of 145-175 B (unexplained since 041). The original extraction may not start flows at the SYN.
- UDP Initial sizes: captured 1294/1292/1274 B (Meta mvfst); original 1363-1381 B.
- `min_iat == 0`: captured 69%, original 98%. Not duplicates: the phone timestamps batches of received packets at the same µs.

## Caveats

- One 30-minute pilot on one network and one phone; 60 s sessions are short (049 suggested >= 20 min for Meta sessions).
- Session labels include background flows; PKTAP attribution per flow is not yet applied.
- The QUIC failure may come from this Wi-Fi network (router, ISP or firewall), not from the apps; not yet tested on another network.

## Decision

Captured flows are **not usable for training** (gate 2 fails on both networks). The pilot found an acquisition problem
(the home Wi-Fi blocks QUIC for Instagram and YouTube; cellular works) before any full capture. Production unchanged.

## Next

- Done: QUIC works on cellular. Future captures use cellular (or a Wi-Fi that passes QUIC), never the home Wi-Fi.
- Remaining gap is format, not network: TCP flows here start at the SYN (4 up / 1 down) while the original's first client
  packet is 145-175 B (3 up / 2 down), and QUIC Initial sizes differ (1294 vs 1363-1381 B). Test an extractor variant that
  starts TCP flows after the handshake, and ask Charles/the organisers how flows were cut (parity check).
- Send Charles the pilot archive with this log's findings (TCP opening and Initial-size mismatch belong to his parity check).
- Optional: label flows by PKTAP process name instead of session.
