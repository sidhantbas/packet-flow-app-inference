"""Capture v2 version bisection (docs/captures/capture_guide.md section 7.4 step 2): does a short capture's opening fingerprint
match the organisers'?

Command: .venv/bin/python src/capture_bisect_check.py <session dir or pcap> --app instagram|facebook|youtube|google [--json out.json]
Reads the session's packets.pcapng (or the given pcap) read-only, builds flows with the extractor's settings (src/capture_extract.py:
phone found automatically, SYN start, 300 s idle timeout, merged TCP segments split), and reports:
  - QUIC (UDP 443) flows that start with a QUIC Initial (first upstream packet >= 1242 B; flows already running when the capture
    started are counted but left out): the size of that first upstream packet (Ethernet-frame size as in the challenge data), its
    distribution and how many distinct sizes occur (the organisers' vary per destination; 2026 clients send one fixed size);
  - TCP flows: the first upstream packet size and the up/down shape of the first 5 packets;
  - a verdict against the organisers' targets for the app (from the 330 labelled flows; experiment 122 and capture guide 7.1).
No address, port or payload is printed or written; the raw capture is never modified.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from capture_extract import TCP, UDP, assemble, parse, phone_addresses, read_packets, split_merged

# Organisers' first QUIC upstream packet per app (Ethernet frame bytes) and the accepted window around it.
TARGET = {"instagram": (1367, 1365, 1369), "facebook": (1365, 1363, 1367), "youtube": (1381, 1379, 1383),
          "google": (None, 1351, 1393)}
TCP_FIRST = (145, 175)
INITIAL_MIN = 1242   # a QUIC Initial carries >= 1200 B of UDP payload: 1200 + 8 + 20 + 14 = 1242 B as an Ethernet frame


def flows_of(pcap):
    packets = [p for p in (parse(ts, link, f, ipv6=True) for ts, link, f in read_packets(pcap)) if p is not None]
    packets, _ = split_merged(packets)
    flows, _ = assemble(packets, phone_addresses(packets, "auto"), 300.0, tcp_start="syn")
    return [f for f in flows if len(f["packets"]) >= 5]


def summarise(flows, app):
    quic = [next((s for _, s, up in f["packets"] if up), None) for f in flows if f["proto"] == UDP and f["server_port"] == 443]
    started_mid = sum(1 for s in quic if s is not None and s < INITIAL_MIN)
    quic = [s for s in quic if s is not None and s >= INITIAL_MIN]   # flows that start with a QUIC Initial (handshake seen)
    tcp = [f for f in flows if f["proto"] == TCP]
    tcp_first = [next((s for _, s, up in f["packets"] if up), None) for f in tcp]
    shapes = Counter(f"{sum(up for _, _, up in f['packets'][:5])}/{5 - sum(up for _, _, up in f['packets'][:5])}" for f in tcp)
    target, lo, hi = TARGET[app]
    in_window = sum(lo <= s <= hi for s in quic)
    distinct = len(set(quic))
    if not quic:
        verdict = "NO QUIC FLOWS: check that the network allows QUIC (cellular) and the app was used"
    elif app == "google":
        ok = in_window / len(quic) >= 0.5 and distinct >= 3
        verdict = ("MATCH: varied first packets in the organisers' range" if ok else
                   "NO MATCH: " + ("sizes outside 1351-1393 B" if in_window / len(quic) < 0.5 else "sizes do not vary per destination"))
    else:
        ok = in_window / len(quic) >= 0.5
        verdict = (f"MATCH: most first packets near {target} B" if ok else
                   f"NO MATCH: most first packets are {Counter(quic).most_common(1)[0][0]} B, the organisers' are {target} B")
    return {"app": app, "flows": len(flows), "quic_flows_with_initial": len(quic), "quic_flows_started_mid_connection": started_mid,
            "quic_first_up_sizes": dict(Counter(quic).most_common(8)), "quic_distinct_sizes": distinct,
            "quic_share_in_target_window": round(in_window / len(quic), 3) if quic else None,
            "target_window": [lo, hi], "tcp_flows": len(tcp),
            "tcp_first_up_sizes": dict(Counter(s for s in tcp_first if s is not None).most_common(6)),
            "tcp_first_in_145_175": round(sum(TCP_FIRST[0] <= s <= TCP_FIRST[1] for s in tcp_first if s) / len(tcp), 3) if tcp else None,
            "tcp_opening_shapes_up_down": dict(shapes.most_common(4)), "verdict": verdict}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path", help="session directory holding packets.pcapng, or a pcap/pcapng file")
    ap.add_argument("--app", required=True, choices=sorted(TARGET))
    ap.add_argument("--json", help="optional output file (outside data/captures/raw/)")
    a = ap.parse_args()
    p = Path(a.path)
    pcap = p / "packets.pcapng" if p.is_dir() else p
    res = summarise(flows_of(pcap), a.app)
    print(json.dumps(res, indent=1))
    if a.json:
        assert "captures/raw" not in str(Path(a.json).resolve()), "never write into the raw capture folder"
        Path(a.json).write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
