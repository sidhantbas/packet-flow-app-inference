"""Build challenge-style flow features from our own pcap captures (experiment 042).

Command:
  .venv/bin/python src/capture_extract.py --pcap data/captures/raw/day1.pcap --phone-ip auto \
      --sessions data/captures/sessions.csv --out data/captures/day1

Writes <out>/task1_features.csv, <out>/task2_features.csv (same 21 columns as the released files), <out>/labels.csv and
<out>/flow_meta.csv (IP version per flow).
Definitions follow experiment 041 (docs/captures/exp041_capture_feasibility.md, section 3):
  - flow = TCP/UDP packets between the phone and one server endpoint (protocol, phone port, server IP, server port),
    split after an idle gap > --idle-timeout s (default 300; the organisers' value is unknown, > 240 s);
    a new phone SYN after a FIN/RST on the same key starts a new flow; flows with < 5 packets are dropped;
  - up = sent by the phone; packet size = Ethernet frame length = 14 + IPv4 total length, at least 60 (Ethernet minimum),
    whatever the capture's link type (so on-phone and network-side captures are comparable). The original flows are IPv4;
    IPv6 packets are sized as their IPv4 equivalent (14 + 20 + IPv6 payload length) unless --ipv6 skip;
  - --phone-ip auto (for iPhone rvi0 captures, where every packet is the phone's): phone addresses = addresses talking to
    many distinct peers;
  - timestamps rounded to 1 µs; std = population std; burst = 1 + number of gaps > 1.0 s;
  - ratios = up / max(down, 1); Task 2 = the same statistics over the first 5 packets (both directions, time order).
Only the server port is kept; IP addresses and phone ports are never written. Payload is never read (snaplen 96 is enough).
No SNI/DNS/Host parsing (challenge condition 3).
"""
import argparse
import ipaddress
import struct
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["flow_id", "split", "start_rel", "duration", "transport", "server_port", "packet_count_up", "packet_count_down",
           "bytes_up", "bytes_down", "mean_pkt_size_up", "mean_pkt_size_down", "std_pkt_size_up", "std_pkt_size_down",
           "mean_iat", "std_iat", "min_iat", "max_iat", "burst_count", "up_down_packet_ratio", "up_down_byte_ratio"]
BURST_GAP = 1.0
MIN_PACKETS = 5
PREFIX = 5
TCP, UDP = 6, 17
IP_TYPES = (b"\x08\x00", b"\x86\xdd")
# link type -> function(frame) returning (offset of the IP header, link type of what follows) or None
LINK = {
    0: lambda f: (4, 12),                                            # BSD loopback / null
    1: lambda f: _ether(f, 12),                                      # Ethernet
    12: lambda f: (0, 12), 101: lambda f: (0, 12), 228: lambda f: (0, 12), 229: lambda f: (0, 12),   # raw IP
    113: lambda f: (16, 12) if f[14:16] in IP_TYPES else None,       # Linux cooked (SLL)
    276: lambda f: (20, 12) if f[0:2] in IP_TYPES else None,         # Linux cooked v2 (SLL2)
    149: lambda f: _pktap(f), 258: lambda f: _pktap(f),              # Apple PKTAP (iPhone rvi0 via rvictl)
}


def _ether(f, off):
    et = f[off:off + 2]
    while et in (b"\x81\x00", b"\x88\xa8"):                           # VLAN tags
        off += 4
        et = f[off:off + 2]
    return (off + 2, 12) if et in IP_TYPES else None


def _pktap(f):
    """Apple PKTAP header (pktap.h): pth_length, pth_type_next, pth_dlt, ... (little-endian); the packet follows pth_length."""
    hlen, _, inner = struct.unpack("<III", f[0:12])
    r = LINK.get(inner, lambda g: None)(f[hlen:])
    return None if r is None else (hlen + r[0], 12)


def read_packets(path):
    """Yield (timestamp_s, link_type, frame_bytes) from a pcap or pcapng file (no external libraries)."""
    data = Path(path).read_bytes()
    magic = data[:4]
    if magic in (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d"):
        e = "<" if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1") else ">"
        frac = 1e-9 if magic in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d") else 1e-6
        link = struct.unpack(e + "I", data[20:24])[0] & 0x0FFFFFFF
        off = 24
        while off + 16 <= len(data):
            sec, sub, incl, _ = struct.unpack(e + "IIII", data[off:off + 16])
            yield sec + sub * frac, link, data[off + 16:off + 16 + incl]
            off += 16 + incl
    elif magic == b"\x0a\x0d\x0d\x0a":
        off, e, ifaces = 0, "<", []
        while off + 12 <= len(data):
            btype = struct.unpack("<I", data[off:off + 4])[0]
            if btype == 0x0A0D0D0A:
                e = "<" if data[off + 8:off + 12] == b"\x4d\x3c\x2b\x1a" else ">"
                ifaces = []
            blen = struct.unpack(e + "I", data[off + 4:off + 8])[0]
            body = data[off + 8:off + blen - 4]
            if btype == 1:                                           # interface description
                link = struct.unpack(e + "H", body[0:2])[0]
                res, o = 1e-6, 8
                while o + 4 <= len(body):
                    code, olen = struct.unpack(e + "HH", body[o:o + 4])
                    if code == 0:
                        break
                    if code == 9:                                    # if_tsresol
                        v = body[o + 4]
                        res = 2.0 ** -(v & 0x7F) if v & 0x80 else 10.0 ** -v
                    o += 4 + olen + (-olen % 4)
                ifaces.append((link, res))
            elif btype == 6:                                         # enhanced packet
                iid, hi, lo, cap, _ = struct.unpack(e + "IIIII", body[0:20])
                link, res = ifaces[iid]
                yield ((hi << 32) | lo) * res, link, body[20:20 + cap]
            off += blen
    else:
        raise ValueError(f"{path}: not a pcap/pcapng file")


def parse(ts, link, f, ipv6=True):
    """Return (t, proto, src, dst, sport, dport, frame_size, tcp_flags, ip_version, tcp_payload) for TCP/UDP packets, else None.

    frame_size is the IPv4 Ethernet frame the packet would be: 14 + IPv4 total length (IPv6: 14 + 20 + payload length), >= 60.
    tcp_payload is the TCP data length from the IP and TCP header length fields (never the payload bytes); 0 for UDP.
    """
    if link not in LINK:
        raise ValueError(f"unsupported link type {link}")
    r = LINK[link](f)
    if r is None or len(f) < r[0] + 20:
        return None
    o = r[0]
    v = f[o] >> 4
    if v == 4:
        ihl = (f[o] & 0x0F) * 4
        ip_len = struct.unpack(">H", f[o + 2:o + 4])[0]
        size, l4_len = 14 + ip_len, ip_len - ihl
        frag = struct.unpack(">H", f[o + 6:o + 8])[0] & 0x1FFF
        proto, src, dst, l4 = f[o + 9], f[o + 12:o + 16], f[o + 16:o + 20], o + ihl
    elif v == 6 and ipv6 and len(f) >= o + 40:
        l4_len = struct.unpack(">H", f[o + 4:o + 6])[0]
        size = 14 + 20 + l4_len
        frag, proto, src, dst, l4 = 0, f[o + 6], f[o + 8:o + 24], f[o + 24:o + 40], o + 40   # extension headers: skipped
    else:
        return None
    if proto not in (TCP, UDP) or frag or len(f) < l4 + 4:
        return None
    sport, dport = struct.unpack(">HH", f[l4:l4 + 4])
    flags = f[l4 + 13] if proto == TCP and len(f) > l4 + 13 else 0
    payload = max(0, l4_len - (f[l4 + 12] >> 4) * 4) if proto == TCP and len(f) > l4 + 12 else 0
    return round(ts, 6), proto, src, dst, sport, dport, max(60, size), flags, v, payload


def phone_addresses(packets, spec):
    """Phone addresses: comma-separated IPs, or 'auto' = addresses with >= 25% of the largest number of distinct peers."""
    if spec != "auto":
        return {ipaddress.ip_address(x.strip()).packed for x in spec.split(",")}
    peers = defaultdict(set)
    for p in packets:
        peers[p[2]].add(p[3])
        peers[p[3]].add(p[2])
    top = max(len(v) for v in peers.values())
    return {a for a, v in peers.items() if len(v) >= 0.25 * top}


TCP_START = ("syn", "after-handshake", "data-only")   # experiment 053
MTU_FRAME = 1514


def split_merged(packets):
    """056: split TCP frames larger than an Ethernet frame (receive offload merged them before RVI saw them) into
    MTU-sized frames with the same timestamp. Header size = frame size - TCP payload; FIN/RST stay on the last part."""
    out, n_split = [], 0
    for p in packets:
        size, payload = p[6], p[9] if len(p) > 9 else 0
        if p[1] != TCP or size <= MTU_FRAME or payload <= 0:
            out.append(p)
            continue
        hdr = size - payload
        mss = MTU_FRAME - hdr
        k = -(-payload // mss)
        for i in range(k):
            part = mss if i < k - 1 else payload - mss * (k - 1)
            flags = p[7] if i == k - 1 else p[7] & ~0x05
            out.append(p[:6] + (hdr + part, flags, p[8], part))
        n_split += 1
    return out, n_split


def _handshake(hs, key, up, flags, payload):
    """after-handshake rule (053): True for the client SYN, the server SYN-ACK and the client's first data-less ACK after it."""
    if up and flags & 0x02 and not flags & 0x10:
        hs[key] = 1
        return True
    if not up and flags & 0x12 == 0x12:
        hs[key] = 2
        return True
    if hs.get(key) == 2 and up:
        hs[key] = 3
        return payload == 0 and not flags & 0x07
    return False


def assemble(packets, phone, idle_timeout=300.0, ports=(443, 80), tcp_start="syn"):
    """Group parsed packets into flows. phone = set of packed phone addresses.

    tcp_start (053): "syn" keeps every TCP packet from the client SYN; "after-handshake" drops the SYN, SYN-ACK and the
    client's first data-less ACK; "data-only" drops every TCP packet without data. Dropped packets still close flows
    (FIN/RST) and split them (SYN after FIN), but do not start flows or count for the idle timeout. UDP is unchanged.
    Returns a list of dicts: proto, server_port, ip_version, packets [(t, size, up)].
    """
    if tcp_start not in TCP_START:
        raise ValueError(f"tcp_start must be one of {TCP_START}")
    hs = {}
    if isinstance(phone, str):
        phone = phone_addresses(packets, phone)
    open_flows, done = {}, []
    skipped = defaultdict(int)
    for p in sorted(packets, key=lambda p: p[0]):
        t, proto, src, dst, sport, dport, size, flags, v = p[:9]
        payload = p[9] if len(p) > 9 else 1
        if src in phone and dst in phone:
            skipped["phone to phone"] += 1
            continue
        if src in phone:
            up, key, sp = True, (proto, sport, dst, dport), dport
        elif dst in phone:
            up, key, sp = False, (proto, dport, src, sport), sport
        else:
            skipped["not the phone"] += 1
            continue
        if sp not in ports:
            skipped[f"server port {sp}"] += 1
            continue
        fl = open_flows.get(key)
        syn_only = proto == TCP and up and flags & 0x02 and not flags & 0x10
        if fl is not None and (t - fl["packets"][-1][0] > idle_timeout or (syn_only and fl["closed"])):
            done.append(open_flows.pop(key))
            fl = None
        if proto == TCP and tcp_start != "syn":
            cut = payload == 0 if tcp_start == "data-only" else _handshake(hs, key, up, flags, payload)
            if cut:
                skipped[f"tcp cut ({tcp_start})"] += 1
                if fl is not None and flags & 0x05:
                    fl["closed"] = True
                continue
        if fl is None:
            fl = open_flows[key] = {"proto": proto, "server_port": sp, "ip_version": v, "packets": [], "closed": False}
        fl["packets"].append((t, size, up))
        if proto == TCP and flags & 0x05:                            # FIN or RST
            fl["closed"] = True
    done += open_flows.values()
    return sorted(done, key=lambda f: f["packets"][0][0]), dict(skipped)


def stats(pk, t0):
    """The 19 statistic columns for one packet list [(t, size, up)] in time order."""
    t = np.array([p[0] for p in pk])
    s = np.array([p[1] for p in pk], dtype=float)
    u = np.array([p[2] for p in pk])
    gaps = np.diff(t)
    r = {"start_rel": round(t[0] - t0, 9), "duration": t[-1] - t[0]}
    for name, m in (("up", u), ("down", ~u)):
        r[f"packet_count_{name}"] = int(m.sum())
        r[f"bytes_{name}"] = int(s[m].sum())
    for name, m in (("up", u), ("down", ~u)):
        r[f"mean_pkt_size_{name}"] = s[m].mean() if m.any() else 0.0
    for name, m in (("up", u), ("down", ~u)):
        r[f"std_pkt_size_{name}"] = s[m].std() if m.any() else 0.0       # population std (ddof 0)
    r.update(mean_iat=gaps.mean(), std_iat=gaps.std(), min_iat=gaps.min(), max_iat=gaps.max(),
             burst_count=int(1 + (gaps > BURST_GAP).sum()),
             up_down_packet_ratio=r["packet_count_up"] / max(r["packet_count_down"], 1),
             up_down_byte_ratio=r["bytes_up"] / max(r["bytes_down"], 1))
    return r


def feature_tables(flows, t0, prefix="cap", meta=False):
    rows1, rows2, rows3 = [], [], []
    for i, fl in enumerate(f for f in flows if len(f["packets"]) >= MIN_PACKETS):
        base = {"flow_id": f"{prefix}_{i:06d}", "split": "capture", "transport": "tcp" if fl["proto"] == TCP else "udp",
                "server_port": fl["server_port"]}
        rows1.append({**base, **stats(fl["packets"], t0)})
        rows2.append({**base, **stats(fl["packets"][:PREFIX], t0)})
        rows3.append({"flow_id": base["flow_id"], "ip_version": fl["ip_version"]})
    T1, T2 = pd.DataFrame(rows1, columns=COLUMNS), pd.DataFrame(rows2, columns=COLUMNS)
    return (T1, T2, pd.DataFrame(rows3, columns=["flow_id", "ip_version"])) if meta else (T1, T2)


def label(T, t0, sessions):
    """Label = app of the session containing the flow's first packet (UTC). Flows outside sessions get no label."""
    S = pd.read_csv(sessions)
    start = pd.to_datetime(S.start_utc, utc=True).map(pd.Timestamp.timestamp).values
    end = pd.to_datetime(S.end_utc, utc=True).map(pd.Timestamp.timestamp).values
    abs_start = t0 + T.start_rel.values
    app, sid, act = [], [], []
    for a in abs_start:
        k = np.where((start <= a) & (a < end))[0]
        app.append(S.app.values[k[0]] if len(k) == 1 else "")
        sid.append(S.session_id.values[k[0]] if len(k) == 1 else "")
        act.append(S.activity.values[k[0]] if len(k) == 1 else "")
    return pd.DataFrame({"flow_id": T.flow_id, "app": app, "session_id": sid, "activity": act})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pcap", required=True)
    ap.add_argument("--phone-ip", default="auto", help="phone IPs, comma-separated, or 'auto' (iPhone rvi0 captures)")
    ap.add_argument("--ipv6", choices=("normalise", "skip"), default="normalise")
    ap.add_argument("--sessions", help="CSV: session_id,app,activity,start_utc,end_utc")
    ap.add_argument("--out", required=True)
    ap.add_argument("--idle-timeout", type=float, default=300.0)
    ap.add_argument("--tcp-start", choices=TCP_START, default="syn",
                    help="where TCP flows start (053): syn (default), after-handshake, data-only")
    ap.add_argument("--split-merged", action="store_true",
                    help="split merged TCP frames > 1514 B into MTU-sized frames (056; off by default)")
    a = ap.parse_args()
    packets, other = [], 0
    for ts, link, f in read_packets(a.pcap):
        p = parse(ts, link, f, ipv6=a.ipv6 == "normalise")
        if p is None:
            other += 1
        else:
            packets.append(p)
    if a.split_merged:
        packets, n_split = split_merged(packets)
        print(f"merged TCP frames split: {n_split}")
    phone = phone_addresses(packets, a.phone_ip)
    flows, skipped = assemble(packets, phone, a.idle_timeout, tcp_start=a.tcp_start)
    t0 = min(p[0] for p in packets)
    T1, T2, M = feature_tables(flows, t0, prefix=Path(a.out).name, meta=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    T1.to_csv(out / "task1_features.csv", index=False)
    T2.to_csv(out / "task2_features.csv", index=False)
    M.to_csv(out / "flow_meta.csv", index=False)
    print(f"phone addresses: {len(phone)} ({sum(len(x) == 4 for x in phone)} IPv4, {sum(len(x) == 16 for x in phone)} IPv6)")
    print(f"{len(packets)} TCP/UDP packets ({other} other frames skipped: ARP, ICMP, fragments, ...); skipped {skipped}")
    print(f"IP version of kept flows: {M.ip_version.value_counts().to_dict()} (original data: IPv4 only)")
    print(f"{len(flows)} flows, {len(T1)} with >= {MIN_PACKETS} packets -> {out}")
    if a.sessions:
        L = label(T1, t0, a.sessions)
        L.to_csv(out / "labels.csv", index=False)
        print("labels:", L.app.replace("", "(none)").value_counts().to_dict())


if __name__ == "__main__":
    main()
