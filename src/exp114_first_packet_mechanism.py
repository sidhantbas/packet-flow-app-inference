"""Experiment 114 (measurement only): is the client's decoded first-packet size an app/stack trait or a per-connection effect?
(protocol: experiments/114_first_packet_mechanism.md). Reads only extracted statistics and session labels of our own captures, and
the released Task 2 train + validation files; no packet contents, server names or addresses.

Usage (from the repository root):
  .venv/bin/python src/exp114_first_packet_mechanism.py
Writes experiments/114_evidence/measurements.json.
"""
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from cv import load_task
from exp090_stamp_catalogue import stamps

ROOT = Path(__file__).resolve().parent.parent
CAP = ROOT / "data/captures"
GROUPS = {"iphone_pilot_wifi": ("sid-iphone-20261008T233855Z",
                                ("02-facebook-feed", "03-facebook-reels", "04-instagram-feed", "05-instagram-reels",
                                 "06-youtube-video", "04-instagram-feed-cellular")),
          "iphone_long_cellular": ("sid-iphone-20261009T115620Z-long-cellular", ("02-facebook", "03-instagram", "04-youtube")),
          "android_macshare": ("sid-android-20261009T152334Z-check-macshare", ("01-facebook", "02-instagram"))}
APPS = ("facebook", "instagram", "youtube")
EVIDENCE = ROOT / "experiments/114_evidence"


def decode(T2):
    S = pd.DataFrame([stamps(r) for r in T2.itertuples()], index=T2.index)
    return T2.assign(up_max=S.up_max, hello=S.hello_size)


def load_session(group_dir, session):
    d = CAP / group_dir / session
    t2 = pd.read_csv(d / "task2_features.csv")
    t1 = pd.read_csv(d / "task1_features.csv")[["flow_id", "start_rel", "duration"]].rename(columns={"duration": "full_duration"})
    lab = pd.read_csv(d / "labels.csv")[["flow_id", "app"]]
    df = decode(t2).merge(t1, on="flow_id", suffixes=("", "_t1")).merge(lab, on="flow_id")
    df["start"] = df["start_rel_t1"] if "start_rel_t1" in df else df["start_rel"]
    df["end"] = df["start"] + df["full_duration"]
    return df


def concentration(sizes):
    c = Counter(sizes)
    n = len(sizes)
    top = [v for _, v in c.most_common(2)]
    return {"n": n, "distinct": len(c), "top1_share": round(top[0] / n, 3) if n else None,
            "top2_share": round(sum(top) / n, 3) if n else None, "sizes": dict(c.most_common(8))}


def overlap_check(q):
    same = {"overlap": [0, 0], "no_overlap": [0, 0]}  # [identical, pairs]
    rows = list(q[["start", "end", "up_max"]].itertuples(index=False))
    for a, b in combinations(rows, 2):
        k = "overlap" if (a.start < b.end and b.start < a.end) else "no_overlap"
        same[k][1] += 1
        same[k][0] += int(a.up_max == b.up_max)
    return {k: {"pairs": v[1], "identical_share": round(v[0] / v[1], 3) if v[1] else None} for k, v in same.items()}


def main():
    out = {"captures": {}, "reading": {}, "challenge": {}}
    trait_ok, checked = [], []
    for g, (gdir, sessions) in GROUPS.items():
        dfs = [load_session(gdir, s).assign(session=s) for s in sessions]
        D = pd.concat(dfs, ignore_index=True)
        D = D[D.app.isin(APPS)]
        out["captures"][g] = {}
        for app in APPS:
            A = D[D.app == app]
            if A.empty:
                continue
            q = A[(A.transport == "udp") & A.up_max.notna()]
            t = A[(A.transport == "tcp") & A.hello.notna()]
            per_session = {}
            for s, qs in q.groupby("session"):
                if len(qs) >= 5:
                    per_session[s] = {**concentration(list(qs.up_max.astype(int))), "pairs": overlap_check(qs)}
            out["captures"][g][app] = {
                "flows": len(A), "quic_decoded": len(q), "quic_undecoded": int(((A.transport == "udp") & A.up_max.isna()).sum()),
                "M1_M2_quic_sizes": concentration(list(q.up_max.astype(int))) if len(q) else None,
                "M3_per_session": per_session,
                "M4_tcp_first_message": {**concentration(list(t.hello.astype(int))),
                                         "spread": [int(t.hello.min()), int(t.hello.max())] if len(t) else None} if len(t) else None}
            for s, v in per_session.items():
                ov, no = v["pairs"]["overlap"]["identical_share"], v["pairs"]["no_overlap"]["identical_share"]
                ok = v["top2_share"] >= 0.8 and (ov is None or no is None or ov >= 0.8 * no)
                checked.append(f"{g}/{app}/{s}")
                trait_ok.append(ok)
                out["reading"][f"{g}/{app}/{s}"] = {"top2_share": v["top2_share"], "overlap_identical": ov,
                                                    "no_overlap_identical": no, "app_trait_criteria_met": bool(ok)}
    tcp_per_conn = {f"{g}/{app}": v["M4_tcp_first_message"]["distinct"] >= 3
                    for g, apps in out["captures"].items() for app, v in apps.items()
                    if v["M4_tcp_first_message"] and v["M4_tcp_first_message"]["n"] >= 5}
    out["reading"]["quic_app_trait_all_sessions"] = bool(trait_ok) and all(trait_ok)
    out["reading"]["quic_sessions_checked"] = len(checked)
    out["reading"]["tcp_first_message_per_connection"] = tcp_per_conn

    Xr, y = load_task("task2_realtime_prefix5")
    C = decode(Xr).assign(app=np.asarray(y))
    for app, A in C.groupby("app"):
        q = A[(A.transport == "udp") & A.up_max.notna()]
        t = A[(A.transport == "tcp") & A.hello.notna()]
        out["challenge"][app] = {"flows": len(A), "quic_sizes": concentration(list(q.up_max.astype(int))) if len(q) else None,
                                 "tcp_first_message": concentration(list(t.hello.astype(int))) if len(t) else None}
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "measurements.json").write_text(json.dumps(out, indent=2) + "\n")

    for g, apps in out["captures"].items():
        for app, v in apps.items():
            m = v["M1_M2_quic_sizes"]
            print(f"{g:22s} {app:9s} flows {v['flows']:3d} | QUIC decoded {v['quic_decoded']:3d} (undecoded {v['quic_undecoded']}) | "
                  f"sizes {m['sizes'] if m else '-'} | top2 {m['top2_share'] if m else '-'} | "
                  f"TCP first msg {v['M4_tcp_first_message']['sizes'] if v['M4_tcp_first_message'] else '-'}")
    print()
    for k, v in out["reading"].items():
        print(k, v)
    print()
    for app, v in out["challenge"].items():
        print(f"challenge {app:9s} QUIC {v['quic_sizes']['sizes'] if v['quic_sizes'] else '-'} | "
              f"TCP first msg {v['tcp_first_message']['sizes'] if v['tcp_first_message'] else '-'}")


if __name__ == "__main__":
    main()
