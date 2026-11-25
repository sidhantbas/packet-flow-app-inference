"""Self-test for capture_extract.py on synthetic captures with hand-computed answers (experiment 042).

Command: .venv/bin/python src/test_capture_extract.py
Builds the same packets as pcap (Ethernet, µs), pcap (raw IPv4, ns) and pcapng (Ethernet), then checks every column,
flow splitting (idle timeout, SYN after FIN), filtering (DNS port, < 5 packets, non-TCP/UDP) and the capture_checks identities.
A second capture tests the iPhone path: Apple PKTAP link type (rvi0), IPv6 sized as its IPv4 equivalent, --phone-ip auto.
A third check covers the 053 --tcp-start rules (syn, after-handshake, data-only) and the parsed TCP payload length.
"""
import struct
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import capture_extract as ce
from capture_checks import identities, prefix_consistency

PHONE, SERVER, OTHER = bytes([192, 168, 2, 2]), bytes([142, 250, 1, 1]), bytes([31, 13, 1, 1])
T0 = 1_760_000_000.0


def ipv4(src, dst, proto, sport, dport, payload, flags=0):
    if proto == ce.TCP:
        l4 = struct.pack(">HHIIBBHHH", sport, dport, 0, 0, 5 << 4, flags, 65535, 0, 0) + payload
    else:
        l4 = struct.pack(">HHHH", sport, dport, 8 + len(payload), 0) + payload
    hdr = struct.pack(">BBHHHBBH4s4s", 0x45, 0, 20 + len(l4), 0, 0x4000, 64, proto, 0, src, dst)
    return hdr + l4


def ether(ip):
    return b"\x02" * 6 + b"\x04" * 6 + b"\x08\x00" + ip


IPV6_FRAME = b"\x02" * 6 + b"\x04" * 6 + b"\x86\xdd" + bytes(60)

# (time offset s, up?, proto, server, server port, phone port, payload bytes, tcp flags)
SPEC = [
    # flow A: TCP 443, 7 packets, gaps 0.01, 0.02, 1.5, 0.0, 2.0, 0.5 -> bursts 3
    (0.00, True, ce.TCP, SERVER, 443, 50000, 0, 0x02),
    (0.01, False, ce.TCP, SERVER, 443, 50000, 0, 0x12),
    (0.03, True, ce.TCP, SERVER, 443, 50000, 0, 0x10),
    (1.53, True, ce.TCP, SERVER, 443, 50000, 517, 0x18),
    (1.53, False, ce.TCP, SERVER, 443, 50000, 1400, 0x18),
    (3.53, False, ce.TCP, SERVER, 443, 50000, 100, 0x18),
    (4.03, True, ce.TCP, SERVER, 443, 50000, 0, 0x11),       # FIN
    # same key again after FIN: new SYN -> new flow B (5 packets, all 0.1 s apart)
    (5.00, True, ce.TCP, SERVER, 443, 50000, 0, 0x02),
    (5.10, False, ce.TCP, SERVER, 443, 50000, 0, 0x12),
    (5.20, True, ce.TCP, SERVER, 443, 50000, 0, 0x10),
    (5.30, True, ce.TCP, SERVER, 443, 50000, 200, 0x18),
    (5.40, False, ce.TCP, SERVER, 443, 50000, 300, 0x18),
    # flow C: UDP 443, 6 packets, then idle 400 s, then 5 more -> flow D
    (10.0, True, ce.UDP, OTHER, 443, 40000, 1252, 0),
    (10.1, True, ce.UDP, OTHER, 443, 40000, 1252, 0),
    (10.2, False, ce.UDP, OTHER, 443, 40000, 1250, 0),
    (10.3, False, ce.UDP, OTHER, 443, 40000, 40, 0),
    (10.4, False, ce.UDP, OTHER, 443, 40000, 30, 0),
    (12.4, True, ce.UDP, OTHER, 443, 40000, 30, 0),
    (412.4, True, ce.UDP, OTHER, 443, 40000, 100, 0),
    (412.5, False, ce.UDP, OTHER, 443, 40000, 100, 0),
    (412.6, True, ce.UDP, OTHER, 443, 40000, 100, 0),
    (412.7, False, ce.UDP, OTHER, 443, 40000, 100, 0),
    (412.8, True, ce.UDP, OTHER, 443, 40000, 100, 0),
    # DNS (port 53) and a 3-packet flow: both dropped
    (20.0, True, ce.UDP, OTHER, 53, 40001, 40, 0),
    (20.1, False, ce.UDP, OTHER, 53, 40001, 80, 0),
    (30.0, True, ce.TCP, OTHER, 443, 50001, 0, 0x02),
    (30.1, False, ce.TCP, OTHER, 443, 50001, 0, 0x12),
    (30.2, True, ce.TCP, OTHER, 443, 50001, 0, 0x10),
]


def frames():
    out = []
    for dt, up, proto, srv, port, pport, pay, fl in SPEC:
        src, dst, sp, dp = (PHONE, srv, pport, port) if up else (srv, PHONE, port, pport)
        out.append((T0 + dt, ipv4(src, dst, proto, sp, dp, bytes(pay), fl)))
    out.append((T0 + 0.5, None))                                 # IPv6 frame
    return out


def write_pcap(path, link, ns=False):
    magic = 0xA1B23C4D if ns else 0xA1B2C3D4
    b = struct.pack("<IHHiIII", magic, 2, 4, 0, 0, 65535, link)
    for t, ip in frames():
        f = IPV6_FRAME if ip is None else (ether(ip) if link == 1 else ip)
        if ip is None and link != 1:
            f = bytes([0x60]) + bytes(39)
        sec = int(t)
        sub = round((t - sec) * (1e9 if ns else 1e6))
        b += struct.pack("<IIII", sec, sub, len(f), len(f)) + f
    Path(path).write_bytes(b)


def write_pcapng(path):
    def block(btype, body):
        body += bytes(-len(body) % 4)
        n = len(body) + 12
        return struct.pack("<II", btype, n) + body + struct.pack("<I", n)
    b = block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1))
    b += block(1, struct.pack("<HHI", 1, 0, 65535) + struct.pack("<HHB", 9, 1, 6) + bytes(3) + struct.pack("<HH", 0, 0))
    for t, ip in frames():
        f = IPV6_FRAME if ip is None else ether(ip)
        us = round(t * 1e6)
        b += block(6, struct.pack("<IIIII", 0, us >> 32, us & 0xFFFFFFFF, len(f), len(f)) + f)
    Path(path).write_bytes(b)


def extract(path):
    pk = [p for p in (ce.parse(*r) for r in ce.read_packets(path)) if p is not None]
    flows, skipped = ce.assemble(pk, "192.168.2.2")
    t0 = min(p[0] for p in pk)
    return ce.feature_tables(flows, t0), skipped, t0


def expected_flow_a():
    # frame sizes: TCP header 20 -> 14 + 20 + 20 + payload, at least 60
    s = [60, 60, 60, 571, 1454, 154, 60]
    up = [True, False, True, True, False, False, True]
    t = [0.00, 0.01, 0.03, 1.53, 1.53, 3.53, 4.03]
    su = np.array([x for x, u in zip(s, up) if u], float)
    sd = np.array([x for x, u in zip(s, up) if not u], float)
    g = np.diff(t)
    return dict(start_rel=0.0, duration=4.03, transport="tcp", server_port=443, packet_count_up=4, packet_count_down=3,
                bytes_up=int(su.sum()), bytes_down=int(sd.sum()), mean_pkt_size_up=su.mean(), mean_pkt_size_down=sd.mean(),
                std_pkt_size_up=su.std(), std_pkt_size_down=sd.std(), mean_iat=g.mean(), std_iat=g.std(), min_iat=0.0,
                max_iat=2.0, burst_count=3, up_down_packet_ratio=4 / 3, up_down_byte_ratio=su.sum() / sd.sum())


def compare(row, exp, name):
    for k, v in exp.items():
        got = row[k]
        ok = got == v if isinstance(v, str) else np.isclose(float(got), float(v), atol=2e-6)
        assert ok, f"{name}: {k} = {got}, expected {v}"


def ipv6(src, dst, proto, sport, dport, payload):
    l4 = struct.pack(">HHHH", sport, dport, 8 + len(payload), 0) + payload if proto == ce.UDP else \
        struct.pack(">HHIIBBHHH", sport, dport, 0, 0, 8 << 4, 0x10, 65535, 0, 0) + bytes(12) + payload
    return struct.pack(">IHBB16s16s", 6 << 28, len(l4), proto, 64, src, dst) + l4


def pktap(frame, dlt):
    hdr = struct.pack("<III", 108, 1, dlt) + b"rvi0".ljust(24, b"\0")
    return hdr + bytes(108 - len(hdr)) + frame


def test_iphone_path(d):
    """8 IPv6 servers (UDP 443, 1232-B payload) + 6 IPv4 servers (TCP 443), wrapped in PKTAP, phone found automatically."""
    p6, p4 = bytes.fromhex("20010db8000000000000000000000002"), PHONE
    frames = []
    for k in range(8):
        srv = bytes.fromhex("20010db8ffff00000000000000000%03x" % (k + 1))
        for j in range(5):
            up = j % 2 == 0
            ip = ipv6(p6 if up else srv, srv if up else p6, ce.UDP, 41000 + k if up else 443, 443 if up else 41000 + k, bytes(1232))
            frames.append((T0 + k + j * 0.01, pktap(ip, 12)))
    for k in range(6):
        srv = bytes([31, 13, 2, k + 1])
        for j in range(5):
            up = j % 2 == 0
            ip = ipv4(p4 if up else srv, srv if up else p4, ce.TCP, 51000 + k if up else 443, 443 if up else 51000 + k, bytes(100), 0x18)
            frames.append((T0 + 20 + k + j * 0.01, pktap(ether(ip), 1)))
    path = Path(d) / "iphone.pcap"
    b = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 149)
    for t, f in frames:
        sec = int(t)
        b += struct.pack("<IIII", sec, round((t - sec) * 1e6), len(f), len(f)) + f
    path.write_bytes(b)
    pk = [p for p in (ce.parse(*r) for r in ce.read_packets(path)) if p is not None]
    phone = ce.phone_addresses(pk, "auto")
    assert phone == {p6, p4}, f"auto phone detection found {len(phone)} addresses"
    flows, _ = ce.assemble(pk, phone)
    A, P, M = ce.feature_tables(flows, min(p[0] for p in pk), meta=True)
    assert len(A) == 14 and M.ip_version.tolist() == [6] * 8 + [4] * 6, M.ip_version.tolist()
    assert (A.mean_pkt_size_up[:8] == 14 + 20 + 8 + 1232).all(), "IPv6 UDP not sized as its IPv4 equivalent"
    assert (A.mean_pkt_size_up[8:] == 14 + 20 + 20 + 100).all() and (A.packet_count_up == 3).all()
    for X in (A, P):
        bad = {k: v for k, v in identities(X).items() if v[0] != v[1]}
        assert not bad, f"iPhone path: identities fail {bad}"
    pk4 = [p for p in (ce.parse(*r, ipv6=False) for r in ce.read_packets(path)) if p is not None]
    assert len(ce.feature_tables(ce.assemble(pk4, "192.168.2.2")[0], 0)[0]) == 6, "--ipv6 skip should keep only IPv4 flows"


def test_tcp_start():
    """053: --tcp-start rules on one TCP connection, then a second connection on the same key after FIN."""
    conn = [  # (time, up?, payload, flags)
        (0.00, True, 0, 0x02), (0.01, False, 0, 0x12), (0.02, True, 0, 0x10),        # handshake
        (0.03, True, 517, 0x18), (0.04, False, 0, 0x10), (0.05, False, 1400, 0x18),
        (0.06, False, 100, 0x18), (0.07, True, 0, 0x10), (0.08, True, 0, 0x11),       # ACK, FIN
        (1.00, True, 0, 0x02), (1.01, False, 0, 0x12), (1.02, True, 0, 0x10),         # new SYN after FIN
        (1.03, True, 300, 0x18), (1.04, False, 900, 0x18), (1.05, True, 0, 0x10),
    ]
    frames_ = [ipv4(PHONE, SERVER, ce.TCP, 50000, 443, bytes(n), fl) if up else ipv4(SERVER, PHONE, ce.TCP, 443, 50000, bytes(n), fl)
               for _, up, n, fl in conn]
    pk = [ce.parse(T0 + t, 101, f) for (t, *_), f in zip(conn, frames_)]
    assert [x[9] for x in pk] == [n for _, _, n, _ in conn], "parse: TCP payload length"
    size = lambda n: max(60, 54 + n)
    want = {
        "syn": [[(size(n), up) for _, up, n, _ in conn[:9]], [(size(n), up) for _, up, n, _ in conn[9:]]],
        "after-handshake": [[(size(n), up) for _, up, n, _ in conn[3:9]], [(size(n), up) for _, up, n, _ in conn[12:]]],
        "data-only": [[(size(n), up) for _, up, n, _ in conn[:9] if n], [(size(n), up) for _, up, n, _ in conn[9:] if n]],
    }
    for rule, exp in want.items():
        flows, skipped = ce.assemble(pk, "192.168.2.2", tcp_start=rule)
        got = [[(s_, u) for _, s_, u in f["packets"]] for f in flows]
        assert got == exp, f"--tcp-start {rule}: {got} != {exp}"
        cut = sum(len(c) for c in want["syn"]) - sum(len(c) for c in exp)
        assert skipped.get(f"tcp cut ({rule})", 0) == cut, f"--tcp-start {rule}: skipped {skipped}"
    try:
        ce.assemble(pk, "192.168.2.2", tcp_start="bad")
        raise AssertionError("unknown tcp_start accepted")
    except ValueError:
        pass


def test_split_merged():
    """056: a 4,000-B merged TCP frame becomes 1514 + 1514 + rest, same time; FIN only on the last part."""
    big = ipv4(SERVER, PHONE, ce.TCP, 443, 50000, bytes(4000 - 54), 0x19)       # 54 B headers, FIN+ACK+PSH
    small = ipv4(SERVER, PHONE, ce.TCP, 443, 50000, bytes(100), 0x18)
    pk = [ce.parse(T0, 101, big), ce.parse(T0 + 1, 101, small)]
    out, n = ce.split_merged(pk)
    assert n == 1 and [x[6] for x in out] == [1514, 1514, 4000 - 2 * 1460, 154], [x[6] for x in out]
    assert [x[9] for x in out[:3]] == [1460, 1460, 4000 - 54 - 2 * 1460] and all(x[0] == T0 for x in out[:3])
    assert [x[7] & 0x01 for x in out[:3]] == [0, 0, 1], "FIN must stay on the last part only"
    assert sum(x[9] for x in out[:3]) == 4000 - 54, "payload preserved"


def main():
    with tempfile.TemporaryDirectory() as d:
        files = {"pcap ethernet µs": Path(d) / "a.pcap", "pcap raw ns": Path(d) / "b.pcap", "pcapng ethernet": Path(d) / "c.pcapng"}
        write_pcap(files["pcap ethernet µs"], 1)
        write_pcap(files["pcap raw ns"], 101, ns=True)
        write_pcapng(files["pcapng ethernet"])
        results = {}
        for name, f in files.items():
            (A, P), skipped, t0 = extract(f)
            assert len(A) == 4, f"{name}: {len(A)} flows, expected 4 (A, B after FIN, C, D after idle)"
            assert skipped == {"server port 53": 2}, f"{name}: skipped {skipped}"
            compare(A.iloc[0], expected_flow_a(), name)
            # Task 2 of flow A = first 5 packets
            compare(P.iloc[0], dict(packet_count_up=3, packet_count_down=2, bytes_up=60 + 60 + 571, bytes_down=60 + 1454,
                                    duration=1.53, max_iat=1.5, burst_count=2, min_iat=0.0), name + " prefix")
            assert A.packet_count_up.tolist() == [4, 3, 3, 3] and (A.packet_count_up + A.packet_count_down).tolist() == [7, 5, 6, 5], name
            assert np.isclose(A.start_rel.iloc[3], 412.4), name
            assert (A.mean_pkt_size_up.iloc[2] == (1294 * 2 + 72) / 3), name    # 1252 B UDP payload -> 1294 B frame
            for X in (A, P):
                bad = {k: v for k, v in identities(X).items() if v[0] != v[1]}
                assert not bad, f"{name}: identities fail {bad}"
            assert prefix_consistency(A, P) == (4, 4), name
            results[name] = A.drop(columns="flow_id")
        ref = results["pcap ethernet µs"]
        for name, A in results.items():
            pd.testing.assert_frame_equal(A, ref, check_exact=False, atol=2e-6)
        # session labelling
        S = Path(d) / "sessions.csv"
        iso = lambda x: pd.Timestamp(T0 + x, unit="s", tz="UTC").isoformat()
        pd.DataFrame({"session_id": ["s1", "s2"], "app": ["instagram", "facebook"], "activity": ["burst", "trickle"],
                      "start_utc": [iso(-1), iso(9)], "end_utc": [iso(6), iso(100)]}).to_csv(S, index=False)
        (A, _), _, t0 = extract(files["pcap ethernet µs"])
        L = ce.label(A, t0, S)
        assert L.app.tolist() == ["instagram", "instagram", "facebook", ""], L.app.tolist()
        test_iphone_path(d)
    test_tcp_start()
    test_split_merged()
    print("capture_extract self-test: all checks passed (3 file formats, 4 flows, all columns, splits, filters, labels; "
          "iPhone path: PKTAP, IPv6 sizing, auto phone address, --ipv6 skip; --tcp-start rules; --split-merged)")


if __name__ == "__main__":
    main()
