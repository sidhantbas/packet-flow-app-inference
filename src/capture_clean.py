"""Experiment 120: clean re-extraction of our own captures (rules: experiments/120_capture_clean_extraction.md).

Command: .venv/bin/python src/capture_clean.py
Rebuilds every listed session with exactly the first extraction's settings (src/capture_extract.py), then adds:
  1. process attribution (iPhone): each packet's process from the pcapng Darwin process-information blocks; flow label = majority;
  2. background removal: system/other/unattributed flows marked keep = False (Android: session labels, marked uncertain);
  3. edge trim: flows starting within 5 s of a session's start or end marked keep = False;
  7. sessions not listed in sessions.csv (preflight checks) excluded and recorded;
  8. data/captures/clean-v2/extraction_manifest.json (hashes, parameters, counts, agreement, determinism check).
Writes data/captures/clean-v2/<group>/<session>/{task1_features,task2_features,labels,flow_meta}.csv; overwrites nothing else.
No IP addresses, phone ports, server names or payload are written.
"""
import hashlib
import json
import struct
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from capture_extract import assemble, feature_tables, label, parse, phone_addresses, split_merged

ROOT = Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data/captures/raw", ROOT / "data/captures/clean-v2"
GROUPS = {"sid-iphone-20261008T233855Z": {"process": True, "split_merged": False},
          "sid-iphone-20261009T115620Z-long-cellular": {"process": True, "split_merged": False},
          "sid-android-20261009T152334Z-check-macshare": {"process": False, "split_merged": True}}
PARAMS = {"idle_timeout_s": 300.0, "tcp_start": "syn", "phone_ip": "auto", "ipv6": "normalise", "edge_trim_s": 5.0}
APP_OF_PROCESS = {"Facebook": "facebook", "Instagram": "instagram", "InstagramNotific": "instagram", "YouTube": "youtube"}
PIB, EPB, SHB = 0x80000001, 6, 0x0A0D0D0A
OPT_PROC, OPT_EPROC = 0x8001, 0x8003


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def read_packets_meta(path):
    """Yield (timestamp_s, link_type, frame, process_name) from a pcapng file; process_name from the Darwin process-information
    block that the packet's effective-process option (0x8003) or process option (0x8001) points to; '(none)' if absent."""
    data = Path(path).read_bytes()
    off, e, ifaces, names = 0, "<", [], []
    while off + 12 <= len(data):
        btype = struct.unpack("<I", data[off:off + 4])[0]
        if btype == SHB:
            e = "<" if data[off + 8:off + 12] == b"\x4d\x3c\x2b\x1a" else ">"
            ifaces, names = [], []
        blen = struct.unpack(e + "I", data[off + 4:off + 8])[0]
        body = data[off + 8:off + blen - 4]
        if btype == 1:
            link, res, o = struct.unpack(e + "H", body[0:2])[0], 1e-6, 8
            while o + 4 <= len(body):
                code, olen = struct.unpack(e + "HH", body[o:o + 4])
                if code == 0:
                    break
                if code == 9:
                    v = body[o + 4]
                    res = 2.0 ** -(v & 0x7F) if v & 0x80 else 10.0 ** -v
                o += 4 + olen + (-olen % 4)
            ifaces.append((link, res))
        elif btype == PIB:
            name, o = "?", 4
            while o + 4 <= len(body):
                code, olen = struct.unpack(e + "HH", body[o:o + 4])
                if code == 0:
                    break
                if code == 2:
                    name = body[o + 4:o + 4 + olen].split(b"\0")[0].decode("utf-8", "replace")
                o += 4 + olen + (-olen % 4)
            names.append(name)
        elif btype == EPB:
            iid, hi, lo, cap, _ = struct.unpack(e + "IIIII", body[0:20])
            link, res = ifaces[iid]
            o, proc, eproc = 20 + cap + (-cap % 4), None, None
            while o + 4 <= len(body):
                code, olen = struct.unpack(e + "HH", body[o:o + 4])
                if code == 0:
                    break
                if code in (OPT_PROC, OPT_EPROC) and olen >= 4:
                    idx = struct.unpack(e + "I", body[o + 4:o + 8])[0]
                    if code == OPT_PROC:
                        proc = idx
                    else:
                        eproc = idx
                o += 4 + olen + (-olen % 4)
            k = eproc if eproc is not None else proc
            yield ((hi << 32) | lo) * res, link, body[20:20 + cap], names[k] if k is not None and k < len(names) else "(none)"
        off += blen


def clean_session(group, session, srow, cfg):
    pcap = RAW / group / session / "packets.pcapng"
    packets, by_key = [], defaultdict(list)
    for ts, link, f, proc in read_packets_meta(pcap):
        p = parse(ts, link, f, ipv6=True)
        if p is not None:
            packets.append(p)
            by_key[(p[0], p[6])].append(proc)
    if cfg["split_merged"]:
        packets, _ = split_merged(packets)
    phone = phone_addresses(packets, PARAMS["phone_ip"])
    flows, _ = assemble(packets, phone, PARAMS["idle_timeout_s"], tcp_start=PARAMS["tcp_start"])
    t0 = min(p[0] for p in packets)
    T1, T2, M = feature_tables(flows, t0, prefix=session, meta=True)
    sessions_csv = ROOT / "data/captures" / group / "sessions.csv"
    L = label(T1, t0, sessions_csv)
    kept_flows = [f for f in flows if len(f["packets"]) >= 5]
    s_start = pd.Timestamp(srow.start_utc).timestamp()
    s_end = pd.Timestamp(srow.end_utc).timestamp()
    rows = []
    for (_, r1), fl, (_, l1) in zip(T1.iterrows(), kept_flows, L.iterrows()):
        procs = Counter(pr for t, size, _ in fl["packets"] for pr in by_key.get((t, size), ["(none)"]))
        name, n = procs.most_common(1)[0]
        share = n / sum(procs.values())
        start = t0 + r1.start_rel
        if cfg["process"]:
            app = APP_OF_PROCESS.get(name, "")
            src, uncertain = "process", False
            reason = "" if app else ("unattributed (no process)" if name == "(none)" else f"system/other process ({name})")
        else:
            app, src, uncertain, reason, name, share = l1.app, "session", True, "", "", np.nan
        if not reason and (start < s_start + PARAMS["edge_trim_s"] or start > s_end - PARAMS["edge_trim_s"]):
            reason = "session edge (5 s)"
        if not reason and not l1.session_id:
            reason = "outside session"
        rows.append({"flow_id": r1.flow_id, "app": app, "label_source": src, "uncertain": uncertain, "process": name,
                     "process_share": round(share, 3) if share == share else np.nan, "session_id": l1.session_id,
                     "session_app": l1.app, "keep": reason == "", "drop_reason": reason})
    labels = pd.DataFrame(rows, columns=["flow_id", "app", "label_source", "uncertain", "process", "process_share", "session_id",
                                         "session_app", "keep", "drop_reason"]).astype({"keep": bool})
    out = OUT / group / session
    out.mkdir(parents=True, exist_ok=True)
    T1.to_csv(out / "task1_features.csv", index=False)
    T2.to_csv(out / "task2_features.csv", index=False)
    M.to_csv(out / "flow_meta.csv", index=False)
    labels.to_csv(out / "labels.csv", index=False)
    v1 = ROOT / "data/captures" / group / session
    same = None
    if (v1 / "task1_features.csv").exists():
        same = all(pd.read_csv(v1 / f).equals(pd.read_csv(out / f)) for f in ("task1_features.csv", "task2_features.csv"))
    k = labels[labels.keep]
    agree = labels[(labels.label_source == "process") & (labels.app != "")]
    return {"input_pcap": str(pcap.relative_to(ROOT)), "input_sha256": sha256(pcap), "flows": len(labels), "kept": int(labels.keep.sum()),
            "dropped_by_reason": dict(Counter(labels.drop_reason[~labels.keep].map(lambda r: r.split(" (")[0] if r.startswith("system") else r))),
            "kept_by_app": dict(Counter(k.app)),
            "session_vs_process_label_agreement": round(float((agree.app == agree.session_app).mean()), 3) if len(agree) else None,
            "process_label_differs_from_session": dict(Counter(f"{a} (session {b})" for a, b in zip(agree.app, agree.session_app) if a != b)),
            "median_process_share": float(labels.process_share.median()) if cfg["process"] else None,
            "features_identical_to_first_extraction": same,
            "outputs_sha256": {f: sha256(out / f) for f in ("task1_features.csv", "task2_features.csv", "labels.csv", "flow_meta.csv")}}


def main():
    manifest = {"experiment": "120", "rules": "experiments/120_capture_clean_extraction.md",
                "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
                "scripts_sha256": {s: sha256(ROOT / "src" / s) for s in ("capture_clean.py", "capture_extract.py")},
                "parameters": PARAMS, "process_to_app": APP_OF_PROCESS, "groups": {}, "excluded_sessions": []}
    for group, cfg in GROUPS.items():
        S = pd.read_csv(ROOT / "data/captures" / group / "sessions.csv")
        listed = set(S.session_id)
        for d in sorted(p.name for p in (RAW / group).iterdir() if p.is_dir()):
            if d not in listed:
                manifest["excluded_sessions"].append({"group": group, "session": d, "reason": "not in sessions.csv (preflight check)"})
        manifest["groups"][group] = {"config": cfg, "sessions": {}}
        for srow in S.itertuples():
            if not (RAW / group / srow.session_id / "packets.pcapng").exists():
                continue
            r = clean_session(group, srow.session_id, srow, cfg)
            manifest["groups"][group]["sessions"][srow.session_id] = r
            print(f"{group[4:30]:27s} {srow.session_id:28s} flows {r['flows']:4d} kept {r['kept']:4d} {r['kept_by_app']} | "
                  f"dropped {r['dropped_by_reason']} | agree {r['session_vs_process_label_agreement']} | identical {r['features_identical_to_first_extraction']}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "extraction_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("excluded sessions:", [x["session"] for x in manifest["excluded_sessions"]])


if __name__ == "__main__":
    main()
