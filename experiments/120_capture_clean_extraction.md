---
title: "120: Clean re-extraction of our captures (process attribution, background removal, edge trim, provenance manifest)"
created: 2026-10-19
creator: sidhantbas
description: "Tooling: a second, cleaner extraction of our own phone captures: labels from the phone's per-packet process names (iPhone), system and background flows removed, session edges trimmed, preflight sessions excluded, one provenance manifest. The existing extractions stay untouched."
source:
  - 052_iphone_pilot.md
  - 055_long_sessions.md
  - 059_android_signature.md
  - 114_first_packet_mechanism.md
  - 115_identifiability_and_artefacts.md
experiment:
  id: '120'
  tasks: [task1, task2]
  lever: tooling
  status: tooling
  verdict: 'Clean extraction v2: 661 flows rebuilt identically to the first extraction; 438 kept (66%): 223 dropped (147 session edge, 60 system/other process, 16 unattributed); iPhone labels from process names (facebook 35, instagram 115, youtube 188), Android session labels marked uncertain (facebook 55, instagram 45); 2 youtube-session flows were instagram; 3 preflight sessions excluded; manifest with hashes'
---

# 120: Clean re-extraction of our captures

**Status: done 2026-10-19. Rules fixed (`ab2d4c5`) before the cleaning code.** Results are below. Sid, 2026-10-19: "go ahead and do
steps 1, 2, 3, 7 and 8" of the capture clean-up, including using the iPhone's per-packet process names as labels (our own device's
operating-system metadata; never challenge data; to be disclosed in the report). **Tooling only:** no model, no training use
(capture training stays closed, 056-063), no submission.

## Why

The first extraction labelled each flow by the session it started in (`capture_extract.label`), so background traffic (iOS services,
other apps' notifications) carried the session's app, flows at session edges were included, and preflight sessions sat next to real
ones. For the research use of our captures (an "other device" test set, 115) labels must name the app that sent the traffic.

## Fixed rules

**Flows** are rebuilt with exactly the first extraction's settings (`src/capture_extract.py`: flow start at SYN, idle timeout
300 s, phone found automatically; merged-segment split for the Android group only, as in 059), so every flow and its 21 columns
must match the first extraction exactly (checked).

1. **Attribution (iPhone groups).** Each packet's process is read from the pcapng Darwin process-information blocks (block type
   `0x80000001`) through the packet's effective-process option (`0x8003`), else its process option (`0x8001`). A flow's process =
   the majority over its packets; its process share is recorded. Mapping: `Facebook` → facebook; `Instagram` and
   `InstagramNotific` (Instagram's notification extension) → instagram; `YouTube` → youtube; every other process (iOS services,
   Safari, other apps' extensions such as `MessengerNotific`) → system/other; no process → unattributed.
2. **Background removal.** Flows whose process maps to system/other, or that are unattributed, are marked `keep = False` with the
   reason. **Android group** (network-side capture, no process information): labels stay session labels, marked
   `label_source = session`, `uncertain = True`.
3. **Edge trim.** Flows starting within the first or last **5 s** of their session are marked `keep = False` ("session edge").
4. **Excluded sessions (step 7).** Raw sessions not listed in a group's `sessions.csv` (the preflight checks `00-preflight`,
   `00b-preflight-web`, `00b-preflight-websudo`) are excluded and recorded as such.
5. **Provenance (step 8).** One `data/captures/clean-v2/extraction_manifest.json`: source commit and script hashes, parameters per
   group, input pcap SHA-256, output SHA-256, row counts, rows kept and dropped by reason, agreement between session and process
   labels, the determinism check against the first extraction.

Outputs go to `data/captures/clean-v2/<group>/<session>/` (`task1_features.csv`, `task2_features.csv`, `labels.csv`,
`flow_meta.csv`); nothing existing is overwritten. No IP addresses, ports of the phone, server names or payload are written.

## Execution ledger

| Time (UTC) | Step | Outcome |
|---|---|---|
| 2026-10-19 | Process names surveyed (names only) and the rules above fixed and committed | before the cleaning code |
| 2026-10-19 | `src/capture_clean.py` written and run | a first run stopped on a session with no flows (empty label table, a code bug); fixed (`labels` built with explicit columns) and rerun from scratch; no rule changed |

## Results

Manifest: `data/captures/clean-v2/extraction_manifest.json` (input and output SHA-256, parameters, per-session counts).

| Group | Session | Flows | Kept | Kept by app | Dropped |
|---|---|---:|---:|---|---|
| iPhone pilot (Wi-Fi, 60 s) | 01-idle | 5 | 0 | — | 5 system |
| | 02-facebook-feed | 14 | 7 | facebook 7 | 7 edge |
| | 03-facebook-reels | 14 | 7 | facebook 7 | 7 edge |
| | 04-instagram-feed | 68 | 55 | instagram 55 | 7 system, 1 unattributed, 5 edge |
| | 04-instagram-feed-cellular | 32 | 4 | instagram 4 | 14 system, 1 unattributed, 13 edge |
| | 05-instagram-reels | 60 | 27 | instagram 27 | 33 edge |
| | 06-youtube-video | 79 | 43 | **youtube 41, instagram 2** | 35 edge, 1 system |
| | 07-idle-after | 0 | 0 | — | — |
| iPhone long (cellular, 20 min) | 01-idle, 05-idle-after | 0 | 0 | — | — |
| | 02-facebook | 34 | 21 | facebook 21 | 7 system, 1 unattributed, 5 edge |
| | 03-instagram | 55 | 27 | instagram 27 | 14 system, 4 unattributed, 10 edge |
| | 04-youtube | 181 | 147 | youtube 147 | 12 system, 9 unattributed, 13 edge |
| Android (5 min, session labels, uncertain) | 01-facebook | 62 | 55 | facebook 55 | 7 edge |
| | 02-instagram | 57 | 45 | instagram 45 | 12 edge |
| **Total** | | **661** | **438 (66%)** | | 147 edge, 60 system, 16 unattributed |

- **Determinism:** every rebuilt flow equals the first extraction in all 21 columns, both tasks (sessions with a first extraction).
- **Attribution changed labels:** among app-attributed iPhone flows, the session label was wrong for 2 (instagram traffic during the
  youtube session). The larger effect is removal: 76 flows (60 system services such as `nsurlsessiond`, `swcd`, `cloudd`,
  `locationd`, `storekitd`, other apps' notification extensions; 16 without a process) had carried an app label before.
- **Process purity:** median process share per iPhone flow 1.0; 63 of 542 flows below 0.9 (packets from more than one process on
  one connection).
- **Excluded sessions:** `00-preflight`, `00b-preflight-web`, `00b-preflight-websudo` (not in `sessions.csv`).
- **Privacy:** no IP-address-like strings in any output (checked); outputs hold flow statistics, app labels and process names.

## Verdict

**Done.** `data/captures/clean-v2/` is the cleaner capture dataset: labels from the app that sent the traffic (iPhone), background
and system flows removed, session edges trimmed, preflight sessions excluded, every file hashed in one manifest. The first
extraction stays as it was, so experiments 052-063 and 114 remain reproducible.

**One rule worked against us:** the 5-second edge trim removed 147 flows, mostly the burst of connections apps open at launch
(up to 55% of a 60-second pilot session). With process attribution, those flows are known to belong to the app, so the trim now
removes real app traffic rather than mislabelled traffic. It was fixed in advance and kept; for future use, process-attributed
flows can ignore it (the `drop_reason` column makes that a filter, not a re-extraction).
