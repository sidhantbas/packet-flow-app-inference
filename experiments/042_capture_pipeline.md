---
title: '042: Own-capture pipeline for Task 1 training (tooling; no capture yet)'
created: 2026-10-05
creator: sidhantbas
description: Can we turn our own pcaps into exactly the organisers' 21 columns (both tasks) and gate them before training use?
experiment:
  id: '042'
  tasks:
  - task1
  lever: tooling
  status: tooling
  verdict: 'Capture pipeline: pcap -> organiser features for both tasks, gates 1 and 2, self-test'
---
# 042: Own-capture pipeline for Task 1 training (tooling; no capture yet)

- **Date:** 2026-10-05
- **Question:** Can we turn our own pcaps into exactly the organisers' 21 columns (both tasks) and gate them before training use?
- **Status:** tooling done; waiting for the first capture
- **Scripts:**
  - `src/capture_extract.py`: pcap/pcapng → features + labels.
  - `src/capture_checks.py`: gates.
  - `src/test_capture_extract.py`: self-test.
- **Runs:** none (no CV yet). Branch `exp042-capture-pipeline` (from `exp041-captures`). Production frozen at 5eb9a8b.
- **Guide:** reports/capture_guide.md

## Decision behind it

User decision on 2026-10-05: train using our own capture. Recorded in CLAUDE.md, scoped to the Task 1 model only, disclosed,
evaluated only on original flows. Task 2 stays on its own files: the official texts say "must use only the task2_realtime_prefix5/ files" (041).

## Setup

- **Extractor** (definitions from 041):
  - pcap (µs/ns) and pcapng.
  - Link types: Ethernet (with VLAN), raw IPv4, SLL, SLL2 and loopback.
  - IPv4 TCP/UDP only, server ports 443/80.
- **Flows:**
  - Flow key: (protocol, phone port, server IP, server port).
  - Split on an idle gap > 300 s (assumed; the organisers' value is > 240 s), or on a new phone SYN after FIN/RST.
  - Keep flows with ≥ 5 packets.
- **Packets:** size = max(60, 14 + IPv4 total length); timestamps rounded to µs.
- **Statistics:** population std; bursts split at gaps > 1.0 s; ratios = x / max(y, 1); Task 2 = the same statistics over the first 5 packets.
- **Privacy:** no IPs or phone ports written, payload never read.
- **Labels:** from `sessions.csv` (UTC windows; first packet inside the window).
- **Gates:**
  - Gate 1: all 041 identities on 100% of flows, and each Task 2 opening consistent with its Task 1 flow.
  - Opening-shape report against the originals.
  - Gate 2: proximity per app; the Facebook/Instagram traffic types are diagnostics only.
    - Median nearest-original distance ≤ the originals' 90th percentile.
    - Same-label 5-NN share ≥ the originals' share.
    - Adversarial AUC ≤ 0.70 with ≥ 30 flows.

## Results

- Self-test passes: the same synthetic packets as pcap (Ethernet, µs), pcap (raw IPv4, ns) and pcapng give identical tables; all columns match hand-computed values; the FIN/SYN split, idle split, port-53 filter, < 5-packet filter, IPv6 skip and session labels all behave as expected.
- End-to-end CLI run on the synthetic capture: Gate 1 PASS, Gate 2 FAIL as it should (4 artificial flows far from the originals, AUC not meaningful below 30 flows).
- Found while testing: `min_iat` is 0 in 98% of original flows (timestamp batching), so any other capture sits hundreds of standard deviations away on that column. It is left out of the proximity distance and reported separately. The training variant should drop `min_iat` (007: no effect on Task 1).

## Update (same day): iPhone path

- The phone is an iPhone connected over USB, so capture runs through `rvictl` / `rvi0` on the Mac.
- Extractor additions:
  - Apple PKTAP link type.
  - IPv6 packets sized as their IPv4 equivalent (14 + 20 + payload length), with the IP version recorded per flow in `flow_meta.csv`.
  - `--phone-ip auto`.
- The self-test covers all three additions, and `--ipv6 skip`.
- `src/capture_session.py` logs sessions with exact UTC times from the tcpdump clock.
- `capture_checks.py` adds an IP-version report and a "label discovery" table: the nearest original label for each captured session app.
- Precise task for the user: reports/meta_capture_task.md. It includes rules fixed before the pilot (stop if Instagram sessions produce most of the facebook-like flows).

## Caveats

- Nothing is known yet about how real captured flows compare.
- The label-definition mismatch (041: labels look destination-based) can only be measured, not fixed.
- The idle timeout and the > vs ≥ burst rule are assumptions.
- Original flows are IPv4. IPv6 flows are sized as their IPv4 equivalent; full-size TCP segments over IPv6 carry 20 B less payload, so the gates report the IP versions.

## Decision

Tooling ready. Next is a half-day pilot capture → gates → decide on the full capture (guide §3–4).

## Next

- Charles asks the organisers the three questions in guide §0.
- Pilot capture.
- If both gates pass: augmentation CV (guide §5).
