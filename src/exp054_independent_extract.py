"""Clean-room flow-feature extractor for experiment 054 (independent re-extraction).

Written from the written specification in the experiment 054 agent brief only, without
looking at the project's main extractor. It reads pcapng (or classic pcap) files with its
own parser, assembles bidirectional TCP/UDP flows to server ports 443/80, and writes the
21-column Task 1 (whole flow) and Task 2 (first 5 packets) tables per session.

IP addresses are used only in memory (flow keys, phone address detection); they are never
written or printed. Packet payload bytes are never read (header length fields only).

Run from the project root:

    .venv/bin/python src/exp054_independent_extract.py

Options: --raw-dir, --out-dir, --sessions (defaults to the eight pilot sessions).
"""

from __future__ import annotations

import argparse
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GROUP = "sid-iphone-20261008T233855Z"
RAW_DIR = ROOT / "data" / "captures" / "raw" / GROUP
OUT_DIR = ROOT / "data" / "captures" / GROUP / "054-independent-extraction" / "independent"
SESSIONS = [
    "01-idle",
    "02-facebook-feed",
    "03-facebook-reels",
    "04-instagram-feed",
    "05-instagram-reels",
    "06-youtube-video",
    "07-idle-after",
    "04-instagram-feed-cellular",
]

COLUMNS = [
    "flow_id", "split", "start_rel", "duration", "transport", "server_port",
    "packet_count_up", "packet_count_down", "bytes_up", "bytes_down",
    "mean_pkt_size_up", "mean_pkt_size_down", "std_pkt_size_up", "std_pkt_size_down",
    "mean_iat", "std_iat", "min_iat", "max_iat", "burst_count",
    "up_down_packet_ratio", "up_down_byte_ratio",
]

PKTAP_TYPES = {149, 258}
RAW_IP_TYPES = {12, 101, 228, 229}
SERVER_PORTS = {443, 80}
IDLE_TIMEOUT = 300.0
BURST_GAP = 1.0
MIN_PACKETS = 5
PREFIX = 5

TCP_FIN, TCP_SYN, TCP_RST, TCP_ACK = 0x01, 0x02, 0x04, 0x10


# ---------------------------------------------------------------------------
# Capture file readers: yield (timestamp_seconds, link_type, frame_bytes)
# ---------------------------------------------------------------------------

def _tsresol_factor(value: int) -> tuple[int, int]:
    """Return (base, exponent): resolution = base ** -exponent."""
    if value & 0x80:
        return 2, value & 0x7F
    return 10, value


def read_pcapng(buf: bytes, stats: Counter):
    pos = 0
    n = len(buf)
    endian = "<"
    interfaces: list[tuple[int, tuple[int, int]]] = []
    while pos + 12 <= n:
        btype_le = struct.unpack_from("<I", buf, pos)[0]
        if btype_le == 0x0A0D0D0A:
            magic = buf[pos + 8:pos + 12]
            if magic == b"\x4d\x3c\x2b\x1a":
                endian = "<"
            elif magic == b"\x1a\x2b\x3c\x4d":
                endian = ">"
            else:
                stats["block:bad_shb_magic"] += 1
                return
            interfaces = []
        btype, blen = struct.unpack_from(endian + "II", buf, pos)
        if blen < 12 or pos + blen > n:
            stats["block:truncated_or_bad_length"] += 1
            return
        body = pos + 8
        body_end = pos + blen - 4
        if btype == 0x0A0D0D0A:
            stats["block:SHB"] += 1
        elif btype == 1:
            stats["block:IDB"] += 1
            linktype = struct.unpack_from(endian + "H", buf, body)[0]
            resol = (10, 6)
            opos = body + 8
            while opos + 4 <= body_end:
                code, olen = struct.unpack_from(endian + "HH", buf, opos)
                if code == 0:
                    break
                if code == 9 and olen >= 1:
                    resol = _tsresol_factor(buf[opos + 4])
                opos += 4 + ((olen + 3) & ~3)
            interfaces.append((linktype, resol))
        elif btype == 6:
            stats["block:EPB"] += 1
            if_id, ts_hi, ts_lo, caplen, _origlen = struct.unpack_from(endian + "IIIII", buf, body)
            if if_id >= len(interfaces):
                stats["block:EPB_unknown_interface"] += 1
            else:
                linktype, (base, exp) = interfaces[if_id]
                raw_ts = (ts_hi << 32) | ts_lo
                ts = raw_ts / (base ** exp)
                data = buf[body + 20:body + 20 + caplen]
                yield ts, linktype, data
        else:
            stats[f"block:other_type_0x{btype:08x}"] += 1
        pos += blen


def read_pcap(buf: bytes, stats: Counter):
    magic = buf[:4]
    if magic == b"\xd4\xc3\xb2\xa1":
        endian, nano = "<", False
    elif magic == b"\xa1\xb2\xc3\xd4":
        endian, nano = ">", False
    elif magic == b"\x4d\x3c\xb2\xa1":
        endian, nano = "<", True
    elif magic == b"\xa1\xb2\x3c\x4d":
        endian, nano = ">", True
    else:
        raise ValueError("not a pcap file")
    linktype = struct.unpack_from(endian + "I", buf, 20)[0] & 0x0FFFFFFF
    pos = 24
    n = len(buf)
    while pos + 16 <= n:
        sec, frac, caplen, _orig = struct.unpack_from(endian + "IIII", buf, pos)
        pos += 16
        if pos + caplen > n:
            stats["record:truncated"] += 1
            return
        stats["record:pcap"] += 1
        ts = sec + frac / (1e9 if nano else 1e6)
        yield ts, linktype, buf[pos:pos + caplen]
        pos += caplen


def read_capture(path: Path, stats: Counter):
    buf = path.read_bytes()
    if buf[:4] == b"\x0a\x0d\x0d\x0a":
        yield from read_pcapng(buf, stats)
    else:
        yield from read_pcap(buf, stats)


# ---------------------------------------------------------------------------
# Packet parsing
# ---------------------------------------------------------------------------

def locate_ip(linktype: int, data: bytes, stats: Counter):
    """Return the offset of the IP header inside data, or None (counting the reason)."""
    if linktype in PKTAP_TYPES:
        if len(data) < 12:
            stats["skip:pktap_truncated"] += 1
            return None
        pth_length, _type_next, pth_dlt = struct.unpack_from("<III", data, 0)
        if pth_length > len(data):
            stats["skip:pktap_truncated"] += 1
            return None
        stats[f"inner_linktype:{pth_dlt}"] += 1
        off = locate_inner(pth_dlt, data, pth_length, stats)
        return off
    stats[f"outer_linktype_direct:{linktype}"] += 1
    return locate_inner(linktype, data, 0, stats)


def locate_inner(linktype: int, data: bytes, start: int, stats: Counter):
    if linktype == 1:
        off = start + 12
        if off + 2 > len(data):
            stats["skip:ethernet_truncated"] += 1
            return None
        etype = struct.unpack_from(">H", data, off)[0]
        while etype in (0x8100, 0x88A8):
            off += 4
            if off + 2 > len(data):
                stats["skip:ethernet_truncated"] += 1
                return None
            etype = struct.unpack_from(">H", data, off)[0]
        if etype not in (0x0800, 0x86DD):
            stats[f"skip:ethertype_0x{etype:04x}"] += 1
            return None
        return off + 2
    if linktype == 0:
        return start + 4
    if linktype in RAW_IP_TYPES:
        return start
    stats[f"skip:unsupported_linktype_{linktype}"] += 1
    return None


def parse_packet(linktype: int, data: bytes, stats: Counter):
    """Return (proto, src, dst, sport, dport, size, flags) or None."""
    ip = locate_ip(linktype, data, stats)
    if ip is None:
        return None
    if ip + 1 > len(data):
        stats["skip:ip_truncated"] += 1
        return None
    version = data[ip] >> 4
    if version == 4:
        if ip + 20 > len(data):
            stats["skip:ip_truncated"] += 1
            return None
        ihl = (data[ip] & 0x0F) * 4
        total_len = struct.unpack_from(">H", data, ip + 2)[0]
        frag = struct.unpack_from(">H", data, ip + 6)[0] & 0x1FFF
        proto = data[ip + 9]
        if proto not in (6, 17):
            stats[f"skip:ip_proto_{proto}"] += 1
            return None
        if frag != 0:
            stats["skip:ipv4_fragment"] += 1
            return None
        src = bytes(data[ip + 12:ip + 16])
        dst = bytes(data[ip + 16:ip + 20])
        th = ip + ihl
        size = 14 + total_len
    elif version == 6:
        if ip + 40 > len(data):
            stats["skip:ip_truncated"] += 1
            return None
        payload_len = struct.unpack_from(">H", data, ip + 4)[0]
        proto = data[ip + 6]
        if proto not in (6, 17):
            stats[f"skip:ipv6_next_header_{proto}"] += 1
            return None
        src = bytes(data[ip + 8:ip + 24])
        dst = bytes(data[ip + 24:ip + 40])
        th = ip + 40
        size = 14 + 20 + payload_len
    else:
        stats[f"skip:ip_version_{version}"] += 1
        return None
    if th + 4 > len(data):
        stats["skip:transport_truncated"] += 1
        return None
    sport, dport = struct.unpack_from(">HH", data, th)
    flags = None
    if proto == 6 and th + 13 < len(data):
        flags = data[th + 13]
    size = max(60, size)
    return proto, src, dst, sport, dport, size, flags


# ---------------------------------------------------------------------------
# Flows and features
# ---------------------------------------------------------------------------

def find_phone_addresses(packets) -> set:
    peers: dict[bytes, set] = defaultdict(set)
    for p in packets:
        _ts, _proto, src, dst = p[0], p[1], p[2], p[3]
        peers[src].add(dst)
        peers[dst].add(src)
    if not peers:
        return set()
    top = max(len(v) for v in peers.values())
    return {a for a, v in peers.items() if len(v) >= 0.25 * top}


def assemble_flows(packets, phones: set, stats: Counter):
    order = sorted(range(len(packets)), key=lambda i: packets[i][0])
    open_flows: dict[tuple, dict] = {}
    finished: list[dict] = []
    seq = 0
    for i in order:
        ts, proto, src, dst, sport, dport, size, flags = packets[i]
        src_p, dst_p = src in phones, dst in phones
        if src_p and dst_p:
            stats["flow_skip:both_ends_phone"] += 1
            continue
        if not src_p and not dst_p:
            stats["flow_skip:neither_end_phone"] += 1
            continue
        up = src_p
        if up:
            phone_port, server, server_port = sport, dst, dport
        else:
            phone_port, server, server_port = dport, src, sport
        if server_port not in SERVER_PORTS:
            stats[f"flow_skip:server_port_other"] += 1
            continue
        key = (proto, phone_port, server, server_port)
        flow = open_flows.get(key)
        if flow is not None:
            new_syn = (
                proto == 6 and up and flags is not None
                and (flags & TCP_SYN) and not (flags & TCP_ACK)
                and flow["closed"]
            )
            if ts - flow["pkts"][-1][0] > IDLE_TIMEOUT or new_syn:
                finished.append(flow)
                flow = None
        if flow is None:
            flow = {"seq": seq, "proto": proto, "server_port": server_port,
                    "closed": False, "pkts": []}
            seq += 1
            open_flows[key] = flow
        flow["pkts"].append((ts, size, up))
        if proto == 6 and flags is not None and (flags & (TCP_FIN | TCP_RST)):
            flow["closed"] = True
        stats["flow_packets_used"] += 1
    flows = finished + list(open_flows.values())
    flows.sort(key=lambda f: (f["pkts"][0][0], f["seq"]))
    return flows


def flow_stats(pkts) -> dict:
    ts = np.array([p[0] for p in pkts], dtype=float)
    size = np.array([p[1] for p in pkts], dtype=np.int64)
    up = np.array([p[2] for p in pkts], dtype=bool)
    out: dict = {}
    out["duration"] = float(ts[-1] - ts[0])
    n_up, n_down = int(up.sum()), int((~up).sum())
    b_up, b_down = int(size[up].sum()), int(size[~up].sum())
    out["packet_count_up"] = n_up
    out["packet_count_down"] = n_down
    out["bytes_up"] = b_up
    out["bytes_down"] = b_down
    out["mean_pkt_size_up"] = float(size[up].mean()) if n_up else 0.0
    out["mean_pkt_size_down"] = float(size[~up].mean()) if n_down else 0.0
    out["std_pkt_size_up"] = float(size[up].std(ddof=0)) if n_up else 0.0
    out["std_pkt_size_down"] = float(size[~up].std(ddof=0)) if n_down else 0.0
    gaps = np.diff(ts)
    out["mean_iat"] = float(gaps.mean())
    out["std_iat"] = float(gaps.std(ddof=0))
    out["min_iat"] = float(gaps.min())
    out["max_iat"] = float(gaps.max())
    out["burst_count"] = int(1 + (gaps > BURST_GAP).sum())
    out["up_down_packet_ratio"] = n_up / max(n_down, 1)
    out["up_down_byte_ratio"] = b_up / max(b_down, 1)
    return out


def extract_session(path: Path, session: str):
    stats: Counter = Counter()
    packets = []
    for ts, linktype, data in read_capture(path, stats):
        stats[f"linktype:{linktype}"] += 1
        stats["frames_total"] += 1
        parsed = parse_packet(linktype, data, stats)
        if parsed is None:
            continue
        proto, src, dst, sport, dport, size, flags = parsed
        packets.append((round(ts, 6), proto, src, dst, sport, dport, size, flags))
    stats["parsed_tcp_udp"] = len(packets)
    if not packets:
        return pd.DataFrame(columns=COLUMNS), pd.DataFrame(columns=COLUMNS), stats, 0
    t0 = min(p[0] for p in packets)
    phones = find_phone_addresses(packets)
    stats["phone_addresses_found"] = len(phones)
    flows = assemble_flows(packets, phones, stats)
    stats["flows_all"] = len(flows)
    kept = [f for f in flows if len(f["pkts"]) >= MIN_PACKETS]
    rows1, rows2 = [], []
    for i, f in enumerate(kept):
        base = {
            "flow_id": f"{session}_{i:06d}",
            "split": "capture",
            "start_rel": round(f["pkts"][0][0] - t0, 9),
        }
        tail = {"transport": "tcp" if f["proto"] == 6 else "udp",
                "server_port": int(f["server_port"])}
        s1 = flow_stats(f["pkts"])
        s2 = flow_stats(f["pkts"][:PREFIX])
        rows1.append({**base, "duration": s1.pop("duration"), **tail, **s1})
        rows2.append({**base, "duration": s2.pop("duration"), **tail, **s2})
    t1 = pd.DataFrame(rows1, columns=COLUMNS)
    t2 = pd.DataFrame(rows2, columns=COLUMNS)
    return t1, t2, stats, len(kept)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--sessions", nargs="*", default=SESSIONS)
    args = ap.parse_args(argv)
    for session in args.sessions:
        path = args.raw_dir / session / "packets.pcapng"
        t1, t2, stats, n_kept = extract_session(path, session)
        out = args.out_dir / session
        out.mkdir(parents=True, exist_ok=True)
        t1.to_csv(out / "task1_features.csv", index=False)
        t2.to_csv(out / "task2_features.csv", index=False)
        print(f"== {session}: kept_flows={n_kept}")
        for k in sorted(stats):
            print(f"   {k}: {stats[k]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
