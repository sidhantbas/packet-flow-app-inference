---
title: "059: Does an Android phone reproduce the training data's network signatures?"
created: 2026-10-09
modified: 2026-10-09
creator: sidhantbas
description: Frozen protocol and results for a short Android capture through the Mac's shared Wi-Fi, checked only for client-stack signatures before any larger capture.
source:
  - 055_long_sessions.md
  - 053_tcp_flow_start.md
  - 058_capture_other_class.md
  - ../reports/capture_guide.md
experiment:
  id: 059
  tasks:
  - task1
  lever: data
  status: measured
  verdict: 'Android through the Mac''s shared Wi-Fi: TCP opening shapes match (TVD 0.11) but QUIC first packets 1274/1294 B vs 1363-1381 B; captures stop'
---

# 059: Does an Android phone reproduce the training data's network signatures?

**Status: done 2026-10-09. Protocol frozen (`fe72ef3`) before any Android capture.**
**Verdict: S1 and S2 do not match (0% each); S3 matches (TVD 0.11). Frozen decision: stop captures.** Results are below.
Do not edit the frozen sections after execution starts. User request 2026-10-09: "yes i have an android, set it up".

## Question

Do Facebook and Instagram flows from an Android phone show the training data's client signatures (QUIC first-packet
sizes 1363-1381 B; first client TCP packet 145-175 B), which our iPhone did not (055)?

## Why this check first

056-058: iPhone captures have no training use; 055 traced the gap to client-stack signatures. Only if Android matches is
a full capture group (about 1 hour) worth doing. This check takes about 30 minutes.

## Setup (frozen)

- Path: iPhone Personal Hotspot over USB (cellular; QUIC works there, 052) → Mac → macOS Internet Sharing to Wi-Fi →
  Android joins the Mac's Wi-Fi with its mobile data off. The home Wi-Fi is not used (it blocks QUIC, 052).
- Capture on the Mac's sharing bridge (`bridge100`, Ethernet link type), `tcpdump -nn -p -P -s 0 'ip or ip6'`, with
  `src/capture_pilot.sh` (`SID_RVI=bridge100 PLAN=check`): `01-facebook` 300 s, `02-instagram` 300 s, apps closed before.
- Extraction: `capture_extract.py` default (`--tcp-start syn`), `--split-merged`, `--phone-ip auto`.
- Confound, stated in advance: both the phone **and** the capture point change (network side instead of on-device RVI).
  A match therefore says "this setup reproduces the signatures", not "the phone alone does".

## Frozen measurements and thresholds

Training reference: train+validation Task 2 tables (first 5 packets), facebook and instagram flows unless stated.

| ID | Measurement | Match if |
|---|---|---|
| S1 | QUIC first-packet size: frame size of UDP openings whose up packets are all equal (captured facebook + instagram) | >= 50% of them in 1363-1381 B (training facebook/instagram: 7 of 8) |
| S2 | First client TCP packet: smaller up packet of TCP openings with exactly 2 up packets (captured, all apps in the check) | >= 50% in 133-175 B (training all apps: 94%) |
| S3 | TCP opening shapes (up/down of the first 5 packets) vs training (all apps), total variation distance | <= 0.25 (iPhone 053 variant A: 0.62) |

For comparison only: the same numbers for the iPhone long group (055).

## Frozen decision

- **S1 and S2 match** → record a full Android group (cellular path, 20 min per app, `PLAN=long`), then gates 1-2 and the
  056-style augmentation test under rule v2 (new protocols).
- **One of S1/S2 matches** → report; the user decides.
- **Neither matches** → stop captures: the gap is in the organisers' setup, not the phone.
- S3 is reported and informs the decision but does not decide alone.

## Boundaries

Measurement only; no training. Addresses only in memory during extraction; the launcher counts connected devices
without printing addresses. Raw files in gitignored `data/captures/raw/`. Production frozen at 5eb9a8b.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-09 | Protocol frozen and committed | `fe72ef3`, before any Android capture |
| 2026-10-09 | Launcher, check plan, analysis committed; dry run on training and iPhone data | `a9e23ab`; training reproduces the reference values (S1 0.875, S2 0.94, S3 0); iPhone matches none |
| 2026-10-09 | Setup problems, fixed before any recording | (1) Internet Sharing first went to a wired adapter, not Wi-Fi: turned off, launcher now refuses this (`45f7ef7`); (2) the Android joined the iPhone's own hotspot Wi-Fi "SidPhone": forgotten, iPhone Wi-Fi turned off so its hotspot is USB-only; (3) macOS refused to share the Mac's Wi-Fi (802.1X network), fixed by sharing from iPhone USB; (4) macOS shares Wi-Fi via `ap1`, not `en0`: launcher check corrected (`6786e00`) |
| 15:23-15:35 | Android check group recorded (`capture_android.sh check`, `6786e00`) | 01-facebook 116,524 and 02-instagram 69,219 packets, 0 drops, hashes OK; upstream iPhone USB; 1 device on the bridge |
| 15:35:32-15:35:33 | `src/exp059_android_signature.py` on `6786e00`, clean tree | Evidence `data/captures/sid-android-20261009T152334Z-check-macshare/`; 18 SHA-256 re-checked: match; no address in any output; 0 merged frames on this path |

No deviation from the frozen measurements or decision rule. Android model and app versions are still to be filled in
(`environment.md`).

## Results

Flows with >= 5 packets: facebook 62, instagram 57.

| Measurement | Training (reference) | Android via Mac Wi-Fi | iPhone RVI (055) | Match |
|---|---|---|---|---|
| S1 QUIC first packet, share 1363-1381 B | 7 of 8 (0.875): 1367 ×4, 1365 ×3, 1294 ×1 | **0 of 18**: 1274 ×8, 1294 ×6, 1292 ×1 | 0 of 47: 1242 ×23, 1294 ×14, 1274 ×9 | ❌ |
| S2 first client TCP packet, share 133-175 B | 16 of 17 (0.94): 145 ×10 | **0 of 7**: 66 ×4, 179, 207, 105 | none of this opening type | ❌ |
| S3 TCP opening-shape TVD | 0 (3/2 0.66, 4/1 0.23, 2/3 0.11) | **0.11** (3/2 0.58, 4/1 0.24, 2/3 0.08) | 0.63 | ✅ |

## Interpretation

- **The QUIC signature belongs to the apps, not the phone.** Android and iPhone produce the same Meta QUIC sizes
  (1274 and 1294 B), so the app's own network library sets them. The training data's 1363-1381 B Meta openings therefore
  point to different (probably older) app versions or settings at the organisers' recording time. The current app
  versions are unlikely to reproduce them (only today's versions were tested).
- **The TCP opening shape changes with the setup.** Android recorded on the network side (Mac Wi-Fi) matches the training
  data (TVD 0.11); iPhone recorded on the device (RVI) did not (0.63). Phone and capture point changed together (the
  confound stated in the protocol), so this suggests, but does not prove, that the organisers captured on the network side.
- **The first client TCP packet still differs.** Most of our network-side TCP flows with two up packets start with the
  66-B SYN; the training flows almost never do (one 66-B case in 17). The organisers' flows may often start after the
  connection began (for example, connections already open when recording started, or flows cut by a timeout).

## Decision

Neither S1 nor S2 matches: by the frozen rule, captures stop. The gap lies in the app versions and the organisers' flow
cutting, which the phones and app versions we have do not reproduce. Production unchanged (5eb9a8b). This closes experiments 052-059.
