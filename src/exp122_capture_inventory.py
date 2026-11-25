"""Experiment 122, part 1: inventory of the three raw capture groups (Charles's 20 October handoff, deliverable 1).

Command: .venv/bin/python src/exp122_capture_inventory.py
Writes experiments/122_evidence/raw_inventory.json and raw_inventory.csv: per session, every file with its size and SHA-256,
the packet file checked against its .sha256 sidecar and against tcpdump's own counts (capture.log), packets counted from the
file, whether the session is listed in sessions.csv, missing standard files; per group, the device/app-version record
(environment.md) and the fields still marked FILL IN. Also the shared archive (data/captures/raw.zip and the Desktop zip) if
present. File contents are never copied (header and metadata samples can hold addresses); only names, sizes and hashes.
"""
import csv
import hashlib
import json
import re
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/captures/raw"
OUT = ROOT / "experiments/122_evidence"
GROUPS = ["sid-iphone-20261008T233855Z", "sid-iphone-20261009T115620Z-long-cellular",
          "sid-android-20261009T152334Z-check-macshare"]
STANDARD = ["actions.tsv", "capture-finished.txt", "capture-start-request.txt", "capture.log", "header-sample.txt",
            "metadata-readback.log", "metadata-sample.txt", "packet-file-bytes.txt", "packets.pcapng", "packets.sha256",
            "readback.log"]
ARCHIVES = [ROOT / "data/captures/raw.zip", Path.home() / "Desktop/mission-p-captures-raw-2026-10-19.zip"]


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def count_packets(path):
    """Enhanced (6) and simple (3) packet blocks in a pcapng file, and the link types of its interfaces."""
    data = Path(path).read_bytes()
    off, e, n, links = 0, "<", 0, set()
    while off + 12 <= len(data):
        btype = struct.unpack("<I", data[off:off + 4])[0]
        if btype == 0x0A0D0D0A:
            e = "<" if data[off + 8:off + 12] == b"\x4d\x3c\x2b\x1a" else ">"
        blen = struct.unpack(e + "I", data[off + 4:off + 8])[0]
        if btype in (3, 6):
            n += 1
        elif btype == 1:
            links.add(struct.unpack(e + "H", data[off + 8:off + 10])[0])
        off += blen
    return n, sorted(links)


def tcpdump_counts(log):
    t = log.read_text(errors="replace") if log.exists() else ""
    get = lambda k: int(m.group(1)) if (m := re.search(rf"(\d+) packets {k}", t)) else None
    iface = re.search(r"listening on (\S+), link-type (\S+)", t)
    return {"captured": get("captured"), "received_by_filter": get("received by filter"), "dropped_by_kernel": get("dropped by kernel"),
            "interface": iface.group(1) if iface else None, "link_type": iface.group(2) if iface else None}


def environment(group):
    p = RAW / group / "environment.md"
    if not p.exists():
        return {"file": None, "fill_in_fields": None}
    lines = p.read_text().splitlines()
    missing = []
    for line in lines:
        for part in re.split(r" · |\. (?=[A-Z])", line.lstrip("- ")):
            if "FILL IN" in part:
                missing.append(part.split(":")[0].strip())
    return {"file": str(p.relative_to(ROOT)), "sha256": sha256(p), "fill_in_fields": missing}


def main():
    OUT.mkdir(exist_ok=True)
    inv = {"experiment": "122", "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "repository_root": "~/" + str(ROOT.relative_to(Path.home())), "raw_root": str(RAW.relative_to(ROOT)), "groups": {},
           "archives": []}
    rows = []
    for g in GROUPS:
        listed = {}
        sc = ROOT / "data/captures" / g / "sessions.csv"
        if sc.exists():
            listed = {r["session_id"]: r for r in csv.DictReader(sc.open())}
        group_files = sorted(p for p in (RAW / g).iterdir() if p.is_file())
        gi = {"path": str((RAW / g).relative_to(ROOT)), "environment": environment(g),
              "group_files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in group_files],
              "sessions": {}}
        for d in sorted(p for p in (RAW / g).iterdir() if p.is_dir()):
            files = sorted(p for p in d.rglob("*") if p.is_file())
            fi = [{"name": str(p.relative_to(d)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files]
            pcap = d / "packets.pcapng"
            s = {"path": str(d.relative_to(ROOT)), "listed_in_sessions_csv": d.name in listed,
                 "session_app": listed.get(d.name, {}).get("app"), "start_utc": listed.get(d.name, {}).get("start_utc"),
                 "end_utc": listed.get(d.name, {}).get("end_utc"), "files": fi, "file_count": len(fi),
                 "bytes_total": sum(f["bytes"] for f in fi), "missing_standard_files": [f for f in STANDARD if not (d / f).exists()],
                 "tcpdump": tcpdump_counts(d / "capture.log")}
            if pcap.exists():
                side = (d / "packets.sha256").read_text().split()[0] if (d / "packets.sha256").exists() else None
                h = next(f["sha256"] for f in fi if f["name"] == "packets.pcapng")
                n, links = count_packets(pcap)
                s.update({"pcap_sha256": h, "pcap_matches_sidecar": side == h if side else None, "pcap_packets_in_file": n,
                          "pcap_link_types": links, "pcap_packets_match_tcpdump": n == s["tcpdump"]["captured"]})
            gi["sessions"][d.name] = s
            rows.append({"group": g, "session": d.name, "listed": s["listed_in_sessions_csv"], "app": s["session_app"] or "",
                         "files": s["file_count"], "bytes": s["bytes_total"], "pcap_sha256": s.get("pcap_sha256", ""),
                         "sidecar_match": s.get("pcap_matches_sidecar", ""), "packets_in_file": s.get("pcap_packets_in_file", ""),
                         "tcpdump_captured": s["tcpdump"]["captured"], "tcpdump_dropped": s["tcpdump"]["dropped_by_kernel"],
                         "interface": s["tcpdump"]["interface"], "missing_files": ";".join(s["missing_standard_files"])})
        inv["groups"][g] = gi
    for a in ARCHIVES:
        if a.exists():
            side = a.with_name(a.name + ".sha256")
            h = sha256(a)
            inv["archives"].append({"path": "~/" + str(a.relative_to(Path.home())), "bytes": a.stat().st_size, "sha256": h,
                                    "sidecar": side.exists(), "matches_sidecar": side.read_text().split()[0] == h if side.exists() else None})
    totals = {"sessions": len(rows), "packet_files": sum(1 for r in rows if r["pcap_sha256"]),
              "packets_in_files": sum(r["packets_in_file"] or 0 for r in rows if r["pcap_sha256"]),
              "all_pcaps_match_sidecar": all(r["sidecar_match"] is True for r in rows if r["pcap_sha256"]),
              "all_pcaps_match_tcpdump": all(s.get("pcap_packets_match_tcpdump", True) for g in inv["groups"].values() for s in g["sessions"].values()),
              "kernel_drops": sum(r["tcpdump_dropped"] or 0 for r in rows)}
    inv["totals"] = totals
    (OUT / "raw_inventory.json").write_text(json.dumps(inv, indent=2) + "\n")
    with (OUT / "raw_inventory.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(), w.writerows(rows)
    for r in rows:
        print(f"{r['group'][4:30]:27s} {r['session']:28s} listed {str(r['listed']):5s} files {r['files']:2d} "
              f"packets {r['packets_in_file']!s:>7s} tcpdump {r['tcpdump_captured']!s:>7s} drop {r['tcpdump_dropped']} "
              f"sidecar {r['sidecar_match']} missing {r['missing_files'] or '-'}")
    print("totals:", totals)
    for g, gi in inv["groups"].items():
        print(g, "environment FILL IN:", gi["environment"]["fill_in_fields"])
    print("archives:", inv["archives"])


if __name__ == "__main__":
    main()
