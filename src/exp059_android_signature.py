"""Experiment 059: does an Android capture reproduce the training data's client signatures? (protocol:
experiments/059_android_signature.md, frozen first)

Command: .venv/bin/python src/exp059_android_signature.py [RAW_GROUP_DIR]   (default: latest capture group)
Extracts 01-facebook and 02-instagram (--split-merged), then computes the frozen measurements S1 (QUIC first-packet
size), S2 (first client TCP packet) and S3 (TCP opening-shape TVD) against train+validation, with the iPhone long group
(055) for comparison, applies the frozen decision, and writes summary.json and manifest.json to data/captures/<group>/.
"""
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from cv import DATA, load_task

ROOT = Path(__file__).resolve().parent.parent
SESSIONS = {"01-facebook": "facebook", "02-instagram": "instagram"}
IPHONE = ROOT / "data/captures/sid-iphone-20261009T115620Z-long-cellular"
IPHONE_SESSIONS = {"02-facebook": "facebook", "03-instagram": "instagram"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).relative_to(ROOT))


def quic_sizes(P):
    u = P[(P.transport == "udp") & (P.packet_count_up > 0) & (P.std_pkt_size_up == 0)]
    return u.mean_pkt_size_up.round().astype(int)


def first_tcp(P):
    t = P[(P.transport == "tcp") & (P.packet_count_up == 2)]
    return (t.mean_pkt_size_up - t.std_pkt_size_up).round().astype(int)


def shapes(P):
    c = P[P.transport == "tcp"].groupby(["packet_count_up", "packet_count_down"]).size()
    return c / c.sum() if len(c) else c


def tvd(a, b):
    return float(0.5 * sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in set(a.index) | set(b.index)))


def top(x, n=6):
    return {int(k): int(v) for k, v in x.value_counts().head(n).items()}


def measure(P, Pm, ref_shapes):
    q, f = quic_sizes(Pm), first_tcp(P)
    return {"S1_quic_equal_openings": int(len(q)), "S1_share_1363_1381": round(float(q.between(1363, 1381).mean()), 4) if len(q) else None,
            "S1_top_sizes": top(q),
            "S2_tcp_2up_openings": int(len(f)), "S2_share_133_175": round(float(f.between(133, 175).mean()), 4) if len(f) else None,
            "S2_top_sizes": top(f),
            "S3_tcp_shape_tvd": round(tvd(shapes(P), ref_shapes), 4),
            "S3_tcp_shapes": {f"{k[0]}/{k[1]}": round(float(v), 4) for k, v in shapes(P).items()}}


def main():
    raw = Path(sys.argv[1]) if len(sys.argv) > 1 else Path((ROOT / "data/captures/raw/latest-sid-capture-root.txt").read_text().strip())
    group = raw.name
    out = ROOT / "data/captures" / group
    if (out / "summary.json").exists():
        raise SystemExit(f"{rel(out)}/summary.json exists: evidence is immutable")
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    inputs, log = {}, []
    with open(out / "sessions.csv", "w") as fh:
        fh.write("session_id,app,activity,start_utc,end_utc\n")
        for s, app in SESSIONS.items():
            pcap = raw / s / "packets.pcapng"
            h, rec = sha(pcap), (raw / s / "packets.sha256").read_text().split()[0]
            if h != rec:
                raise SystemExit(f"{s}: hash {h} != recorded {rec}")
            inputs[rel(pcap)] = h
            fh.write(f"{s},{app},Android via Mac shared Wi-Fi,{(raw / s / 'capture-start-request.txt').read_text().strip()},"
                     f"{(raw / s / 'capture-finished.txt').read_text().strip()}\n")
    for s in SESSIONS:
        cmd = [sys.executable, str(ROOT / "src/capture_extract.py"), "--pcap", str(raw / s / "packets.pcapng"), "--phone-ip", "auto",
               "--sessions", str(out / "sessions.csv"), "--split-merged", "--out", str(out / s)]
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
        (out / s / "extract.log").write_text(r.stdout)
        log.append({"command": " ".join(c.replace(str(ROOT) + "/", "") for c in cmd), "exit": r.returncode})
    for sp in ("train", "validation"):
        for k in ("features", "labels"):
            inputs[rel(DATA / "task2_realtime_prefix5" / f"{sp}_{k}.csv")] = sha(DATA / "task2_realtime_prefix5" / f"{sp}_{k}.csv")

    Po, yo = load_task("task2_realtime_prefix5")
    ref_shapes = shapes(Po)
    meta = np.isin(yo.values, ("facebook", "instagram"))
    training = measure(Po, Po[meta], ref_shapes)
    A = pd.concat([pd.read_csv(out / s / "task2_features.csv") for s in SESSIONS], ignore_index=True)
    I = pd.concat([pd.read_csv(IPHONE / s / "task2_features.csv") for s in IPHONE_SESSIONS], ignore_index=True)
    android, iphone = measure(A, A, ref_shapes), measure(I, I, ref_shapes)
    s1 = android["S1_share_1363_1381"] is not None and android["S1_share_1363_1381"] >= 0.5
    s2 = android["S2_share_133_175"] is not None and android["S2_share_133_175"] >= 0.5
    s3 = android["S3_tcp_shape_tvd"] <= 0.25
    decision = ("S1 and S2 match: record a full Android group (PLAN=long), then gates and the 056-style test" if s1 and s2 else
                "one of S1/S2 matches: report; the user decides" if s1 or s2 else
                "neither matches: stop captures (gap is in the organisers' setup, not the phone)")
    flows = {s: int(len(pd.read_csv(out / s / "task1_features.csv"))) for s in SESSIONS}
    summary = {"group": group, "flows": flows, "training": training, "android": android, "iphone_055": iphone,
               "match": {"S1": bool(s1), "S2": bool(s2), "S3": bool(s3)}, "decision": decision}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    outputs = {rel(p): sha(p) for p in sorted(out.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "src/"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    (out / "manifest.json").write_text(json.dumps({
        "experiment": "059", "protocol": "experiments/059_android_signature.md", "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source_commit": commit,
        "source_dirty": bool(dirty), "python": platform.python_version(), "inputs_sha256": inputs,
        "outputs_sha256": outputs, "commands": log}, indent=2))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
