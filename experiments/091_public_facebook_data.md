---
title: "091: Public 2026 Android traffic as extra facebook training data (feasibility check)"
created: 2026-10-10
creator: sidhantbas
description: Feasibility check of a public, CC BY 4.0, August 2026 Android social-media traffic dataset as extra Task 1 facebook/instagram training data; stopped at the opening-signature criterion that stopped our own captures (059).
source:
  - 059_android_signature.md
  - 090_stamp_catalogue.md
  - 063_capture_android_filtered.md
experiment:
  id: 091
  tasks:
  - task1
  lever: data
  status: rejected
  verdict: 'Public 2026 Android dataset: 0% of its Meta QUIC first packets match the challenge signature; stopped before training'
---

# 091: Public 2026 Android traffic as extra facebook training data

**Status: done 2026-10-10. Feasibility check only; no training use.**
**Verdict: stopped. 0% of the public Meta QUIC first packets (1,025) and 0% of its TCP first packets match the challenge's opening
signatures; the data looks like our own captures, not like the challenge data.**

## Context and rules

User 2026-10-10: "try the public datasets for facebook". This reopens the user's own 2026-10-01 rule ("only the given dataset")
and the `.mission.md` OUT OF SCOPE line "Outside datasets or pretrained models"; both were flagged to the user before starting.
Scope: **Task 1 only** (Task 2 reads only its own files); any training use would need a report disclosure (challenge condition 4)
and the user's decision. No challenge data was sent anywhere; the public files were only downloaded.

## Candidate chosen

| Dataset | Why considered | Why not the others |
|---|---|---|
| **Social Media Application Traffic Dataset** (Mendeley Data `6v3zcxysh7`, v1, published 2026-08-04, CC BY 4.0): 10 Android apps incl. facebook, instagram, youtube, twitter; 25,116 NFStream flows from 50 Wireshark captures over 5 days; first-packet sequences (`splt_*`) included | Same year as the challenge, same apps, packet-level opening data | MIRAGE-2019 (2019 apps, CC BY-NC-ND), UTMobileNet2021 (2019-2020 apps, bot-driven): older app versions than our own captures, which already did not match |

Downloaded `facebook.csv` and `instagram.csv` (SHA-256 equal to the repository's) into `data/external/mendeley-6v3zcxysh7-v1/`
(gitignored: third-party IP addresses and server names). Only sizes, directions, protocol and packet counts were read; server
names, nDPI application labels and fingerprints were not used.

## Decision criterion (fixed earlier, 059 S1)

The criterion that stopped our own captures: at least 50% of Meta QUIC first packets (≥ 1200 B) in 1363-1381 B, the challenge's
Meta signature (090: facebook 1365/1367 B). Also checked: TCP client first packet 145-175 B (041; 090: 145/147/159/175 B by app).

## Results (flows with ≥ 5 packets, as in the challenge)

| App | Flows | QUIC first packets ≥ 1200 B | in 1363-1381 B | Most common | TCP first packets in 145-175 B | Most common |
|---|---:|---:|---:|---|---|---|
| facebook | 1,652 | 878 | **0 (0%)** | 1274 ×524, 1292 ×198, 1294 ×155 | 1 of 645 | 74 B ×562 (stock SYN) |
| instagram | 542 | 147 | **0 (0%)** | 1294 ×83, 1274 ×52, 1292 ×12 | 0 of 218 | 74 B ×207 |

Session labels are by capture file: every flow seen during a facebook session (including DNS, IGMP and ICMPv6 flows) is labelled
facebook, as with our own captures.

## Verdict

**Stopped; no training use.** The public 2026 Android data has the same opening signatures as our own iPhone and Android captures
(1274/1292/1294-B QUIC, 74-B SYN) and none of the challenge's (1365/1367-B Meta QUIC, 145-175-B first TCP packet). Training on
it would repeat 056-063 (facebook F1 −0.07 to −0.38).

**Finding for the report:** three independent 2026 references (our iPhone, our Android, a public Android dataset) agree with each
other and disagree with the challenge data in the same way: the client's **first** packet of a connection is about 70-100 B larger
in the challenge data (TCP 74 → 145-175 B; Meta QUIC 1274 → 1365/1367 B; Google QUIC 1292 → 1363-1381 B), while later packets
(e.g. 66-B ACKs) match. The cause is unknown (device or network setup of the organisers); it is why no outside traffic transfers.
The offset differs by app family, so it cannot be corrected by shifting sizes.
