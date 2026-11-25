---
title: "114: Is the client's first-packet size an app trait or a per-connection (server-name) effect? (measurement only)"
created: 2026-10-18
creator: sidhantbas
description: "Measurement on our own captures (extracted statistics and session labels only; no packet contents, server names or addresses) of how the decoded first-packet size behaves within each app, to inform the condition 3 decision on s_up_max (109)."
source:
  - 109_task2_first_packet_specialist.md
  - 090_stamp_catalogue.md
  - 055_long_sessions.md
  - 059_android_signature.md
experiment:
  id: '114'
  tasks: [task2]
  lever: diagnostic
  status: measured
  verdict: 'Inconclusive by the frozen reading (QUIC app-trait criteria met in 6 of 10 sessions): QUIC first-packet sizes cluster on a few stack values per app (facebook 1274 B on iPhone and Android; instagram 1294/1242; youtube 1292/1242), but two values coexist within apps and concurrent connections differ more often; in the challenge data both Meta apps use both 1365 and 1367 B; TCP first messages vary per connection. A server-name influence cannot be excluded.'
---

# 114: First-packet size: app trait or per-connection effect?

**Status: done 2026-10-18. Protocol frozen (`84c0279`) before any code or run.**
**Verdict: inconclusive. The QUIC first-packet size behaves mostly like a property of each app's network stack, but not cleanly
enough to rule out a server-name effect; condition 3 stays open.** Results are below the protocol.
Do not edit the frozen sections after execution starts. Sid, 2026-10-18: "go ahead and do the capture analysis" (captures as
insight, not training). **Measurement only:** no model change, no submission. Number 113 stays reserved for 112's follow-up.

## Question and evidence

`s_up_max` (the decoded size of the client's first message in the 5-packet opening) is the only measured facebook/instagram
lever left (109 B: Task 2 +0.0197). Its open question is challenge condition 3: does it work because it reflects the **server
name's length** (a side channel of an identifier), or because it is a property of **each app's network stack** (how its QUIC client
pads the first packet, its TLS settings)? In 055 our iPhone's QUIC first packets differed by app (facebook 1274 B; instagram 1242
and 1294 B; youtube 1242 and 1292 B), all outside the challenge's 1363-1381 B.

- **QUIC** pads the client's first packet (at least 1200 B); a client that pads to a fixed target produces the same size whatever
  the server name. **TLS over TCP** sends the ClientHello unpadded, so its length moves with the server name and extensions.
- An app opens connections to many different servers during a session (feed, media, messaging). Concurrent QUIC connections from
  one app usually go to different servers, because HTTP/3 reuses one connection per server.

## Frozen design

Data: our own captures' extracted 21-column Task 2 statistics (`data/captures/<group>/<session>/task2_features.csv`) and session
labels (`labels.csv`), for three groups: iPhone pilot (Wi-Fi, 60 s sessions), iPhone long (cellular, 20 min), Android (Mac shared
Wi-Fi, 5 min). Comparison: the challenge's labelled Task 2 flows (train + validation). Sizes decoded with
`exp090_stamp_catalogue.stamps` (as 109).

| # | Measurement |
|---|---|
| M1 | QUIC (UDP) first-packet size (`up_max` of the opening) per app and group; the same for the challenge data |
| M2 | Concentration per app session: distinct sizes, and the share of QUIC flows on the most common 1 and 2 sizes |
| M3 | Concurrent-connection check per app session: among pairs of QUIC flows that overlap in time (likely different servers) and pairs that do not, the share with identical first-packet size |
| M4 | TCP first client message (`hello_size`, decoded for 3-packet TCP openings) per app: distinct sizes and spread |
| M5 | Challenge data: which Meta flows carry the 1365 / 1367 B (QUIC) and 448 B (TCP) values |

**Reading, fixed now:**

- **QUIC size = app/stack trait** if, in every group, each app's QUIC first packets put ≥ 80% of flows on ≤ 2 sizes **and** the
  identical-size share among overlapping pairs is at least 0.8 × that among non-overlapping pairs.
- **TCP first message = per-connection** if an app with ≥ 5 decoded TCP openings shows ≥ 3 distinct sizes.
- Otherwise: inconclusive.

This informs the condition 3 decision; it does not make it (Sid and Charles decide).

## Boundaries

Only extracted statistics and session labels of our own captures, and the released Task 2 files (train + validation). No packet
payload, no SNI, no DNS, no IP addresses are read or derived. Captures are not used for training. Session labels include some
background traffic of other apps (055); sessions with fewer than 5 QUIC flows are reported but not used for the reading.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-18 | Protocol frozen and committed | before any code change or run |
| 2026-10-18 | `src/exp114_first_packet_mechanism.py` run | `114_evidence/measurements.json`; no deviation from the protocol |

## Results

**M1-M2: QUIC first-packet size per app** (decoded `up_max` of UDP openings; [`114_evidence/measurements.json`](114_evidence/measurements.json)):

| Group | facebook | instagram | youtube |
|---|---|---|---|
| iPhone pilot (Wi-Fi) | 1274 B ×8, 1294 ×2 | 1294 ×42, 1242 ×3 | 1292 ×15, 1294 ×1 |
| iPhone long (cellular) | 1274 ×9, 1294 ×1, 1242 ×1 | 1242 ×22, 1294 ×15, 1392 ×1 | 1242 ×85, 1292 ×8, 1392 ×1 |
| Android (Mac shared Wi-Fi) | 1274 ×7, 1294 ×3, others ×3 | 1294 ×4, 1292 ×2, others ×2 | — |
| **Challenge (train + validation)** | **1365 ×4, 1367 ×3** | **1367 ×16**, 1294 ×1, 1365 ×1 | 1381 ×28, 1370 ×3 |

The two most common sizes cover 91-100% of each app's QUIC openings on the iPhone and 75-77% on Android (8-13 flows, including a
few tiny non-Initial packets). The values recur across apps (1294 in all three apps, 1242 in instagram and youtube) and across
devices (facebook 1274 on iPhone and Android). For comparison, google's QUIC first packets in the challenge data take 8 distinct
values (1363-1393 B).

**M3: concurrent connections** (sessions with ≥ 5 decoded QUIC flows; share of flow pairs with identical size):

| Session | Overlapping pairs | Non-overlapping pairs | App-trait criteria |
|---|---:|---:|---|
| iPhone pilot facebook reels | 0.64 | 0.75 | ✅ |
| iPhone pilot instagram feed / reels | 1.00 / 1.00 | 1.00 / 1.00 | ✅ ✅ |
| iPhone pilot instagram feed (cellular) | 0.62 | 0.44 | ✅ |
| iPhone pilot youtube | 0.81 | 0.91 | ✅ |
| iPhone long facebook | 0.42 | 0.78 | ❌ |
| iPhone long instagram | 0.36 | 0.56 | ❌ |
| iPhone long youtube | 0.79 | 0.83 | ✅ |
| Android facebook | 0.10 | 0.44 | ❌ (top 2 = 77%) |
| Android instagram | 0.33 | 0.00 | ❌ (top 2 = 75%) |

**M4: TCP first client message:** none of our captured TCP openings decodes (they start with the 66-B SYN; 059), so M4 is not
evaluable on captures. In the challenge data (descriptive) the TCP first message varies per connection: google 7 distinct sizes
(234-1454 B), mozilla 7, x 4; facebook's two TCP openings both carry 448 B.

**M5:** in the challenge data the 1365 / 1367 B values are QUIC first packets; facebook uses both (4 / 3), instagram mostly 1367
(16 of 18), google only 1365 among the two (30).

## Verdict

**Inconclusive by the frozen reading** (app-trait criteria met in 6 of 10 QUIC sessions). What the measurements do and do not show:

1. **Mostly a stack property.** Each app's QUIC first packet takes only a few sizes, the same few across devices and networks, and
   shared between apps that share a QUIC library (1294 B, Meta's library per 041; 1242 B in instagram and youtube). A size set by
   each server name would spread over many values for apps that contact many servers.
2. **But not one value per app.** Apps use two or more values (instagram 1294 and 1242), concurrent connections differ more often in
   the long sessions, and in the challenge data both Meta apps use both 1365 and 1367 B. Two network stacks per app would explain
   this; so would a connection-level factor such as the server name. These data cannot tell them apart without reading
   identifiers, which this experiment does not do.
3. **TCP first messages do vary per connection** in the challenge data, as an unpadded ClientHello would.

**For the condition 3 decision (Sid and Charles):** the QUIC first-packet size is better described as a client-stack statistic
than as a server-name channel, but a server-name influence is not excluded, and the TCP first-message part of the decoded sizes is
more plausibly per connection. Conservative options: keep `s_up_max` out (production unchanged), or, if it is used, restrict the
specialist to QUIC first-packet sizes and disclose this measurement in the report.
