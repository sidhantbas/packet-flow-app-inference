"""Experiment 055: long-session cellular group (protocol: experiments/055_long_sessions.md, frozen first).

Command: .venv/bin/python src/exp055_long_sessions.py   (about 1-2 min)
Extracts every session (capture_extract.py, default --tcp-start syn), runs gate 1 on all sessions with flows and gate 2
on the three app sessions (capture_checks.py), the 054 Part B per-app consistency check, the QUIC no-reply count (M4),
merged TCP segments > 1514 B (M5) and flow durations (M6). Writes feature CSVs, gate output, consistency tables,
summary.json and manifest.json (SHA-256 of inputs and outputs) to data/captures/<group>/. Addresses stay in memory.
"""
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.metrics import roc_auc_score

import capture_extract as ce
from capture_checks import PROX_COLS
from cv import DATA, load_task

ROOT = Path(__file__).resolve().parent.parent
GROUP = "sid-iphone-20261009T115620Z-long-cellular"
RAW = ROOT / "data/captures/raw" / GROUP
OUT = ROOT / "data/captures" / GROUP
SESSIONS = {"01-idle": "idle", "02-facebook": "facebook", "03-instagram": "instagram", "04-youtube": "youtube",
            "05-idle-after": "idle"}
APPS = ["02-facebook", "03-instagram", "04-youtube"]
H1_COLS = ["duration", "burst_count", "max_iat", "mean_iat"]
FLAG_AUC = 0.80
PY = sys.executable


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).relative_to(ROOT))


def run(cmd, log):
    r = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True)
    log.append({"command": " ".join(rel(c) if str(c).startswith(str(ROOT)) else str(c) for c in cmd), "exit": r.returncode})
    if r.returncode:
        raise SystemExit(f"failed: {cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def gate2_numbers(text):
    auc = float(re.search(r"adversarial AUC original vs captured: ([0-9.]+)", text).group(1))
    rows = {m.group(1): {"n": int(m.group(2)), "median_nn": float(m.group(3)), "orig_p90": float(m.group(4)),
                         "same_label_5nn": float(m.group(5)), "orig_same_label": float(m.group(6)), "verdict": m.group(7)}
            for m in re.finditer(r"app (\w+)\s+n=\s*(\d+)\s+median NN distance ([0-9.]+) \(orig 90th pct ([0-9.]+)\)\s+"
                                 r"same-label 5-NN ([0-9.]+) \(orig ([0-9.]+)\)\s+(ok|FAR)", text)}
    nearest = dict(re.findall(r"^\s+(\w+)\s+-> (.+)$", text, re.M))
    return {"auc": auc, "apps": rows, "nearest_original_labels": nearest, "pass": "Gate 2 PASS" in text}


def consistency(C, Xo, yo, app):
    O = Xo[yo.values == app]
    rows = []
    for c in PROX_COLS + ["min_iat"]:
        o, n = O[c].astype(float).values, C[c].astype(float).values
        auc = roc_auc_score(np.r_[np.zeros(len(o)), np.ones(len(n))], np.r_[o, n])
        lo, hi = np.percentile(o, [5, 95])
        rows.append({"column": c, "gated": c in PROX_COLS, "auc_separability": round(max(auc, 1 - auc), 4),
                     "captured_higher": bool(auc > 0.5), "ks": round(float(ks_2samp(o, n).statistic), 4),
                     "original_median": float(np.median(o)), "captured_median": float(np.median(n)),
                     "original_p5": float(lo), "original_p95": float(hi),
                     "captured_share_in_original_p5_p95": round(float(((n >= lo) & (n <= hi)).mean()), 4),
                     "inconsistent": bool(max(auc, 1 - auc) >= FLAG_AUC)})
    return pd.DataFrame(rows).sort_values("auc_separability", ascending=False)


def merged_segments(pcap):
    tcp = [p for p in (ce.parse(*r) for r in ce.read_packets(pcap)) if p is not None and p[1] == ce.TCP]
    big = sum(p[6] > 1514 for p in tcp)
    return {"tcp_frames": len(tcp), "over_1514": int(big), "share": round(big / max(len(tcp), 1), 4),
            "max_frame": int(max((p[6] for p in tcp), default=0))}


def main():
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "src/"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if (OUT / "summary.json").exists():
        raise SystemExit(f"{rel(OUT)}/summary.json exists: evidence is immutable; remove only with the user's approval")
    OUT.mkdir(parents=True, exist_ok=True)
    log, inputs = [], {}
    for s in SESSIONS:
        pcap = RAW / s / "packets.pcapng"
        h, rec = sha(pcap), (RAW / s / "packets.sha256").read_text().split()[0]
        if h != rec:
            raise SystemExit(f"{s}: pcapng hash {h} != recorded {rec}")
        inputs[rel(pcap)] = h
    with open(OUT / "sessions.csv", "w") as f:
        f.write("session_id,app,activity,start_utc,end_utc\n")
        for s, app in SESSIONS.items():
            f.write(f"{s},{app},20 min normal use (cellular),{(RAW / s / 'capture-start-request.txt').read_text().strip()},"
                    f"{(RAW / s / 'capture-finished.txt').read_text().strip()}\n")
    for task in ("task1_static", "task2_realtime_prefix5"):
        for sp in ("train", "validation"):
            for k in ("features", "labels"):
                inputs[rel(DATA / task / f"{sp}_{k}.csv")] = sha(DATA / task / f"{sp}_{k}.csv")

    for s in SESSIONS:
        run([PY, ROOT / "src/capture_extract.py", "--pcap", RAW / s / "packets.pcapng", "--phone-ip", "auto",
             "--sessions", OUT / "sessions.csv", "--out", OUT / s], log)
    with_flows = [s for s in SESSIONS if len(pd.read_csv(OUT / s / "task1_features.csv"))]
    g_all = run([PY, ROOT / "src/capture_checks.py", *[OUT / s for s in with_flows]], log)
    (OUT / "gates-all-sessions.txt").write_text(g_all)
    g_app = run([PY, ROOT / "src/capture_checks.py", *[OUT / s for s in APPS]], log)
    (OUT / "gates-app-sessions.txt").write_text(g_app)

    Xo, yo = load_task("task1_static")
    Xo = Xo.assign(transport=(Xo.transport == "tcp").astype(int))
    summary = {"group": GROUP, "M1_gate1_pass": "Gate 1 PASS" in g_all, "M2_gate2": gate2_numbers(g_app),
               "M3_inconsistent_gated_columns": {}, "M3_h1_columns_auc": {}, "M4_quic": {}, "M5_merged_segments": {},
               "M6_durations": {}, "flows": {}}
    for s in APPS:
        app = SESSIONS[s]
        C = pd.read_csv(OUT / s / "task1_features.csv")
        summary["flows"][s] = int(len(C))
        T = consistency(C.assign(transport=(C.transport == "tcp").astype(int)), Xo, yo, app)
        T.to_csv(OUT / f"consistency_{app}.csv", index=False)
        summary["M3_inconsistent_gated_columns"][app] = T[T.inconsistent & T.gated].column.tolist()
        summary["M3_h1_columns_auc"][app] = {c: float(T.set_index("column").auc_separability[c]) for c in H1_COLS}
        u = C[C.transport == "udp"]
        summary["M4_quic"][app] = {"udp_flows": int(len(u)), "udp_no_reply": int((u.packet_count_down == 0).sum()),
                                   "mb_down_udp": round(u.bytes_down.sum() / 1e6, 1),
                                   "mb_down_tcp": round(C[C.transport == "tcp"].bytes_down.sum() / 1e6, 1)}
        summary["M5_merged_segments"][app] = merged_segments(RAW / s / "packets.pcapng")
        O = Xo[yo.values == app]
        summary["M6_durations"][app] = {"captured_median_s": round(float(C.duration.median()), 2),
                                        "captured_share_over_60s": round(float((C.duration > 60).mean()), 3),
                                        "original_median_s": round(float(O.duration.median()), 2),
                                        "original_share_over_60s": round(float((O.duration > 60).mean()), 3)}
    h1 = all(summary["M3_h1_columns_auc"][a][c] < FLAG_AUC for a in ("facebook", "instagram") for c in H1_COLS)
    summary["decision"] = {"H1_supported": bool(h1), "gate2_pass": summary["M2_gate2"]["pass"],
                           "training_use": "no" if not (summary["M1_gate1_pass"] and summary["M2_gate2"]["pass"])
                           else "gates pass: still needs merged-segment handling, organiser answers or user decision, and approval"}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    outputs = {rel(p): sha(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    manifest = {"experiment": "055", "protocol": "experiments/055_long_sessions.md", "started_utc": started,
                "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source_commit": commit,
                "source_dirty": bool(dirty), "python": platform.python_version(),
                "device": {"machine": platform.machine(), "macos": platform.mac_ver()[0]},
                "inputs_sha256": inputs, "outputs_sha256": outputs, "commands": log}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
