"""Experiment 053: where do the organisers' TCP flows start? (protocol: experiments/053_tcp_flow_start.md, frozen first)

Command: .venv/bin/python src/exp053_tcp_flow_start.py   (about 1 min)
Runs capture_extract.py with --tcp-start syn (A), after-handshake (B) and data-only (C) on every pilot session, then
capture_checks.py: gate 1 on all sessions with flows, gate 2 on the cellular session. Computes M0-M4 and the frozen
decision, and writes the evidence folder data/captures/<group>/053-tcp-flow-start/ with summary.json and manifest.json
(SHA-256 of every input and output, source commit, commands). Original data: train+validation only.
"""
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cv import DATA, load_task

ROOT = Path(__file__).resolve().parent.parent
GROUP = "sid-iphone-20261008T233855Z"
RAW = ROOT / "data/captures/raw" / GROUP
FEAT = ROOT / "data/captures" / GROUP
OUT = FEAT / "053-tcp-flow-start"
SESSIONS = ["01-idle", "02-facebook-feed", "03-facebook-reels", "04-instagram-feed", "05-instagram-reels",
            "06-youtube-video", "07-idle-after", "04-instagram-feed-cellular"]
APP_SESSIONS = [s for s in SESSIONS if "idle" not in s]
CELLULAR = "04-instagram-feed-cellular"
VARIANTS = {"A": "syn", "B": "after-handshake", "C": "data-only"}
CSVS = ["task1_features.csv", "task2_features.csv", "labels.csv", "flow_meta.csv"]
PY = sys.executable


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).relative_to(ROOT))


def run(cmd, log):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    log.append({"command": " ".join(rel(c) if str(c).startswith(str(ROOT)) else str(c) for c in cmd), "exit": r.returncode})
    if r.returncode:
        raise SystemExit(f"failed: {cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def shapes(P):
    t = P[P.transport == "tcp"]
    c = t.groupby(["packet_count_up", "packet_count_down"]).size()
    return (c / c.sum()) if len(c) else c


def tvd(a, b):
    keys = set(a.index) | set(b.index)
    return float(0.5 * sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys))


def first_client_packet(P):
    t = P[(P.transport == "tcp") & (P.packet_count_up == 2)]
    lo = (t.mean_pkt_size_up - t.std_pkt_size_up).round().astype(int)
    return lo


def top(x, n=6):
    return {int(k): int(v) for k, v in x.value_counts().head(n).items()}


def gate2_numbers(text):
    auc = float(re.search(r"adversarial AUC original vs captured: ([0-9.]+)", text).group(1))
    rows = {m.group(1): {"n": int(m.group(2)), "median_nn": float(m.group(3)), "orig_p90": float(m.group(4)),
                         "same_label_5nn": float(m.group(5)), "orig_same_label": float(m.group(6)), "verdict": m.group(7)}
            for m in re.finditer(r"app (\w+)\s+n=\s*(\d+)\s+median NN distance ([0-9.]+) \(orig 90th pct ([0-9.]+)\)\s+"
                                 r"same-label 5-NN ([0-9.]+) \(orig ([0-9.]+)\)\s+(ok|FAR)", text)}
    nearest = re.findall(r"^\s+(\w+)\s+-> (.+)$", text, re.M)
    return {"auc": auc, "apps": rows, "nearest_original_labels": dict(nearest), "pass": "Gate 2 PASS" in text}


def main():
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "src/"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if OUT.exists():
        raise SystemExit(f"{rel(OUT)} exists: evidence folders are immutable; remove only with the user's approval")
    log, inputs = [], {}

    for s in SESSIONS:                                   # input integrity: recorded hash must match
        pcap = RAW / s / "packets.pcapng"
        recorded = (RAW / s / "packets.sha256").read_text().split()[0]
        h = sha(pcap)
        if h != recorded:
            raise SystemExit(f"{s}: pcapng hash {h} != recorded {recorded}")
        inputs[rel(pcap)] = h
    inputs[rel(FEAT / "sessions.csv")] = sha(FEAT / "sessions.csv")
    for task in ("task1_static", "task2_realtime_prefix5"):
        for split in ("train", "validation"):
            for kind in ("features", "labels"):
                f = DATA / task / f"{split}_{kind}.csv"
                inputs[rel(f)] = sha(f)

    Po, _ = load_task("task2_realtime_prefix5")
    orig_shapes, orig_first = shapes(Po), first_client_packet(Po)
    summary = {"original": {"tcp_opening_shapes": {f"{k[0]}/{k[1]}": round(v, 4) for k, v in orig_shapes.items()},
                            "first_client_packet_top": top(orig_first),
                            "first_client_packet_share_133_175": round(float(orig_first.between(133, 175).mean()), 4)},
               "variants": {}}

    for v, rule in VARIANTS.items():
        vd = OUT / v
        for s in SESSIONS:
            run([PY, ROOT / "src/capture_extract.py", "--pcap", RAW / s / "packets.pcapng", "--phone-ip", "auto",
                 "--sessions", FEAT / "sessions.csv", "--tcp-start", rule, "--out", vd / s], log)
        with_flows = [s for s in SESSIONS if len(pd.read_csv(vd / s / "task1_features.csv"))]
        g_all = run([PY, ROOT / "src/capture_checks.py", *[vd / s for s in with_flows]], log)
        (vd / "gates-all-sessions.txt").write_text(g_all)
        g_cell = run([PY, ROOT / "src/capture_checks.py", vd / CELLULAR], log)
        (vd / "gates-cellular.txt").write_text(g_cell)

        P_app = pd.concat([pd.read_csv(vd / s / "task2_features.csv") for s in APP_SESSIONS], ignore_index=True)
        P_cell = pd.read_csv(vd / CELLULAR / "task2_features.csv")
        first = first_client_packet(P_app)
        A_app = pd.concat([pd.read_csv(vd / s / "task1_features.csv") for s in APP_SESSIONS], ignore_index=True)
        summary["variants"][v] = {
            "tcp_start": rule,
            "flows": {s: int(len(pd.read_csv(vd / s / "task1_features.csv"))) for s in SESSIONS},
            "tcp_flows_app_sessions": int((A_app.transport == "tcp").sum()),
            "M1_tvd_pooled": round(tvd(shapes(P_app), orig_shapes), 4),
            "M1_tvd_cellular": round(tvd(shapes(P_cell), orig_shapes), 4),
            "tcp_opening_shapes_pooled": {f"{k[0]}/{k[1]}": round(x, 4) for k, x in shapes(P_app).items()},
            "M2_first_client_packet_top": top(first),
            "M2_n_openings_with_2_up": int(len(first)),
            "M2_share_133_175": round(float(first.between(133, 175).mean()), 4) if len(first) else None,
            "M3_gate1_pass": "Gate 1 PASS" in g_all,
            "M4_gate2_cellular": gate2_numbers(g_cell),
        }

    # M0: variant A reproduces the 052 CSVs byte for byte
    m0 = {}
    for s in SESSIONS:
        for c in CSVS:
            ref, new = FEAT / s / c, OUT / "A" / s / c
            if ref.exists():
                m0[f"{s}/{c}"] = sha(ref) == sha(new)
    summary["M0_reference_reproduced"] = bool(all(m0.values()))
    summary["M0_files_compared"] = len(m0)

    # frozen decision rules (053 protocol)
    a = summary["variants"]["A"]
    qual = {}
    for v in ("B", "C"):
        r = summary["variants"][v]
        explains = bool(r["M1_tvd_pooled"] <= 0.15)
        qual[v] = {"explains_gap": explains,
                   "tvd_drop_vs_A": round(a["M1_tvd_pooled"] - r["M1_tvd_pooled"], 4),
                   "auc_drop_vs_A": round(a["M4_gate2_cellular"]["auc"] - r["M4_gate2_cellular"]["auc"], 4),
                   "default_candidate": bool(explains and r["M3_gate1_pass"]
                                             and a["M4_gate2_cellular"]["auc"] - r["M4_gate2_cellular"]["auc"] >= 0.05)}
    cands = [v for v in qual if qual[v]["default_candidate"]]
    best = min(cands, key=lambda v: summary["variants"][v]["M1_tvd_pooled"]) if cands else None
    stop = bool(all(q["tvd_drop_vs_A"] < 0.10 for q in qual.values()))
    summary["decision"] = {"per_variant": qual, "new_extractor_default": VARIANTS[best] if best else "syn (unchanged)",
                           "stop_H0": stop,
                           "training_use": "no (needs gate 2 PASS)" if not any(
                               summary["variants"][v]["M4_gate2_cellular"]["pass"] for v in VARIANTS) else "gate 2 passed: see protocol"}

    outputs = {rel(p): sha(p) for p in sorted(OUT.rglob("*")) if p.is_file()}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    manifest = {"experiment": "053", "protocol": "experiments/053_tcp_flow_start.md", "started_utc": started,
                "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_commit": commit, "source_dirty": bool(dirty), "python": platform.python_version(),
                "device": {"machine": platform.machine(), "macos": platform.mac_ver()[0],
                           "model": subprocess.run(["sysctl", "-n", "hw.model"], capture_output=True, text=True).stdout.strip()},
                "inputs_sha256": inputs, "outputs_sha256": outputs | {rel(OUT / "summary.json"): sha(OUT / "summary.json")},
                "commands": log}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: summary[k] for k in ("M0_reference_reproduced", "decision")}, indent=2, default=str))
    for v, r in summary["variants"].items():
        print(f"{v} {r['tcp_start']:15s} TVD pooled {r['M1_tvd_pooled']:.3f} cellular {r['M1_tvd_cellular']:.3f}  "
              f"2-up openings {r['M2_n_openings_with_2_up']} share 133-175 {r['M2_share_133_175']}  "
              f"gate1 {'PASS' if r['M3_gate1_pass'] else 'FAIL'}  cellular AUC {r['M4_gate2_cellular']['auc']:.3f}")


if __name__ == "__main__":
    main()
