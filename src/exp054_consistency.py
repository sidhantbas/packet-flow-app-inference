"""Experiment 054 (protocol: experiments/054_independent_extraction_consistency.md, frozen first).

Command: .venv/bin/python src/exp054_consistency.py   (seconds; run after the clean-room extractor has written its CSVs)
Part A: compares the clean-room extractor's tables (054-independent-extraction/independent/) with 053 variant A, value
by value, under the frozen tolerance. Part B: per app and column, compares captured Task 1 flows (053 variant A) with
the released train+validation flows of the same app: single-column AUC, KS statistic, medians, share inside the original
5th-95th percentile range. Writes comparison and consistency tables, summary.json and manifest.json (SHA-256 of inputs
and outputs). No IP addresses are read here (feature tables only). Original data: train+validation only.
"""
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.metrics import roc_auc_score

from capture_checks import PROX_COLS
from cv import DATA, load_task

ROOT = Path(__file__).resolve().parent.parent
GROUP = ROOT / "data/captures/sid-iphone-20261008T233855Z"
REF = GROUP / "053-tcp-flow-start/A"
OUT = GROUP / "054-independent-extraction"
IND = OUT / "independent"
SESSIONS = ["01-idle", "02-facebook-feed", "03-facebook-reels", "04-instagram-feed", "05-instagram-reels",
            "06-youtube-video", "07-idle-after", "04-instagram-feed-cellular"]
GROUPS = {"wifi_facebook": ["02-facebook-feed", "03-facebook-reels"],
          "wifi_instagram": ["04-instagram-feed", "05-instagram-reels"],
          "wifi_youtube": ["06-youtube-video"],
          "cellular_instagram": ["04-instagram-feed-cellular"]}
INT_COLS = ["server_port", "packet_count_up", "packet_count_down", "bytes_up", "bytes_down", "burst_count"]
STR_COLS = ["flow_id", "split", "transport"]
REPORT_COLS = PROX_COLS + ["min_iat"]
FLAG_AUC = 0.80


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).relative_to(ROOT))


def part_a():
    rows, ok_all = [], True
    for s in SESSIONS:
        for table in ("task1_features.csv", "task2_features.csv"):
            r, i = pd.read_csv(REF / s / table), pd.read_csv(IND / s / table)
            same_n = len(r) == len(i)
            ok = same_n and list(r.columns) == list(i.columns)
            mism = {}
            if ok:
                ok = (r.flow_id.values == i.flow_id.values).all()
            if ok:
                for c in r.columns:
                    if c in STR_COLS:
                        bad = int((r[c].astype(str) != i[c].astype(str)).sum())
                    elif c in INT_COLS:
                        bad = int((r[c].astype("int64") != i[c].astype("int64")).sum())
                    else:
                        bad = int((~np.isclose(r[c].astype(float), i[c].astype(float), rtol=1e-6, atol=1e-9)).sum())
                    if bad:
                        mism[c] = bad
                ok = not mism
            ok_all &= bool(ok)
            rows.append({"session": s, "table": table, "flows_ours": len(r), "flows_independent": len(i),
                         "values_compared": int(r.size) if same_n else 0, "mismatching_columns": json.dumps(mism),
                         "match": bool(ok)})
    T = pd.DataFrame(rows)
    T.to_csv(OUT / "comparison.csv", index=False)
    return T, ok_all


def part_b():
    Xo, yo = load_task("task1_static")
    Xo = Xo.assign(transport=(Xo.transport == "tcp").astype(int))
    tables, flagged = {}, {}
    for g, sessions in GROUPS.items():
        C = pd.concat([pd.read_csv(REF / s / "task1_features.csv") for s in sessions], ignore_index=True)
        C = C.assign(transport=(C.transport == "tcp").astype(int))
        app = g.split("_")[1]
        O = Xo[yo.values == app]
        rows = []
        for c in REPORT_COLS:
            o, n = O[c].astype(float).values, C[c].astype(float).values
            y = np.r_[np.zeros(len(o)), np.ones(len(n))]
            auc = roc_auc_score(y, np.r_[o, n])
            lo, hi = np.percentile(o, [5, 95])
            rows.append({"column": c, "gated": c in PROX_COLS, "auc_separability": round(max(auc, 1 - auc), 4),
                         "captured_higher": bool(auc > 0.5), "ks": round(ks_2samp(o, n).statistic, 4),
                         "original_median": float(np.median(o)), "captured_median": float(np.median(n)),
                         "original_p5": float(lo), "original_p95": float(hi),
                         "captured_share_in_original_p5_p95": round(float(((n >= lo) & (n <= hi)).mean()), 4),
                         "inconsistent": bool(max(auc, 1 - auc) >= FLAG_AUC)})
        T = pd.DataFrame(rows).sort_values("auc_separability", ascending=False)
        T.to_csv(OUT / f"consistency_{g}.csv", index=False)
        tables[g] = {"n_captured": len(C), "n_original": int(len(O)), "app": app}
        flagged[g] = T[T.inconsistent & T.gated].column.tolist()
    return tables, flagged


def main():
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not IND.exists():
        raise SystemExit(f"{rel(IND)} missing: run the clean-room extractor first")
    for f in ["comparison.csv", "summary.json", "manifest.json"]:
        if (OUT / f).exists():
            raise SystemExit(f"{rel(OUT / f)} exists: evidence is immutable; remove only with the user's approval")
    A, a_ok = part_a()
    groups, flagged = part_b()
    summary = {"part_a_all_match": a_ok, "part_a_tables": int(len(A)), "part_a_values_compared": int(A.values_compared.sum()),
               "part_a_mismatches": A[~A.match].to_dict("records"),
               "part_b_groups": groups, "part_b_inconsistent_gated_columns": flagged, "flag_rule": f"single-column AUC >= {FLAG_AUC}"}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "src/"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    inputs = {rel(p): sha(p) for s in SESSIONS for p in (GROUP.parent / "raw" / GROUP.name / s / "packets.pcapng",)}
    inputs |= {rel(DATA / "task1_static" / f"{sp}_{k}.csv"): sha(DATA / "task1_static" / f"{sp}_{k}.csv")
               for sp in ("train", "validation") for k in ("features", "labels")}
    inputs |= {rel(p): sha(p) for p in sorted(REF.rglob("*.csv"))}
    inputs[rel(ROOT / "src/exp054_independent_extract.py")] = sha(ROOT / "src/exp054_independent_extract.py")
    outputs = {rel(p): sha(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    manifest = {"experiment": "054", "protocol": "experiments/054_independent_extraction_consistency.md",
                "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_commit": commit, "source_dirty": bool(dirty), "python": platform.python_version(),
                "device": {"machine": platform.machine(), "macos": platform.mac_ver()[0]},
                "commands": [".venv/bin/python src/exp054_independent_extract.py (clean-room agent)",
                             ".venv/bin/python src/exp054_consistency.py"],
                "inputs_sha256": inputs, "outputs_sha256": outputs}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Part A: {'ALL MATCH' if a_ok else 'MISMATCH'} ({len(A)} tables, {int(A.values_compared.sum())} values)")
    if not a_ok:
        print(A[~A.match].to_string(index=False))
    for g, cols in flagged.items():
        print(f"Part B {g} (n={groups[g]['n_captured']} vs {groups[g]['n_original']} original): inconsistent {cols}")


if __name__ == "__main__":
    main()
