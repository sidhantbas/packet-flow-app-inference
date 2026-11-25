"""Experiment 090: stamp catalogue; exact opening sizes decoded from the Task 2 summary statistics, catalogued per app, and
a separability check at the choke points (protocol: experiments/090_stamp_catalogue.md, frozen first). Measurement only;
train + validation rows only.

Usage: python src/exp090_stamp_catalogue.py   (writes experiments/090_evidence/)
"""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASK_FEATURES, load_task
from models import SoftVote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments/090_evidence"
T1, T2 = "task1_static", "task2_realtime_prefix5"
ACK = 66
CHOKES = [("facebook", "google"), ("facebook", "instagram"), ("google", "youtube")]
NUM = ["syn_size", "hello_size", "synack_size", "reply_size", "up_min", "up_max", "down_min", "down_max"]


def _int(v, tol=0.01):
    return abs(v - round(v)) <= tol


def decode(n, m, s):
    """Exact sorted sizes of one direction, or None (protocol table rows 1-3)."""
    n = int(n)
    if n == 0:
        return []
    if n == 1:
        return [round(m)] if _int(m) else None
    if n == 2:
        a, b = m - s, m + s
        return sorted([round(a), round(b)]) if _int(a) and _int(b) else None
    if abs(s) < 1e-9:
        return [round(m)] * n if _int(m) else None
    return None


def decode_tcp3(m, s):
    """TCP up with 3 packets: client first packet + ACK (66 B) + first message (protocol table row 4)."""
    S, Q = 3 * m, 3 * (s ** 2 + m ** 2)
    a, b = S - ACK, Q - ACK ** 2
    disc = 2 * b - a ** 2
    if disc < -1e-6:
        return None
    r = math.sqrt(max(disc, 0.0))
    x, y = (a - r) / 2, (a + r) / 2
    if not (_int(x) and _int(y) and 140 <= round(x) <= 180):
        return None
    return round(x), round(y)


def stamps(row):
    tcp = row.transport == "tcp"
    st = {"shape": f"{row.transport} {int(row.packet_count_up)}/{int(row.packet_count_down)}"}
    up = decode(row.packet_count_up, row.mean_pkt_size_up, row.std_pkt_size_up)
    dn = decode(row.packet_count_down, row.mean_pkt_size_down, row.std_pkt_size_down)
    st["tcp3_tried"] = bool(tcp and int(row.packet_count_up) == 3 and up is None)
    st["syn_size"] = st["hello_size"] = None
    if st["tcp3_tried"]:
        d = decode_tcp3(row.mean_pkt_size_up, row.std_pkt_size_up)
        if d:
            st["syn_size"], st["hello_size"] = d
            up = sorted([ACK, *d])
    st["up_sizes"] = None if up is None else tuple(up)
    st["down_sizes"] = None if dn is None else tuple(dn)
    st["synack_size"] = st["reply_size"] = None
    if tcp and dn:
        st["synack_size"] = dn[0]
        if len(dn) == 2:
            st["reply_size"] = dn[1]
    for d, v in (("up", up), ("down", dn)):
        st[f"{d}_min"] = min(v) if v else None
        st[f"{d}_max"] = max(v) if v else None
    return st


def catalogue(S, y):
    S = S.assign(app=y)
    apps = sorted(S.app.unique())
    cov = []
    for app, g in S.groupby("app"):
        cov.append({"app": app, "flows": len(g), "up_decoded": int(g.up_sizes.notna().sum()),
                    "down_decoded": int(g.down_sizes.notna().sum()), "tcp3_tried": int(g.tcp3_tried.sum()),
                    "tcp3_decoded": int(g.syn_size.notna().sum())})
    single = {}
    mixes = {}
    for col in ("shape", "up_sizes", "down_sizes", "syn_size", "hello_size", "reply_size"):
        t = S[S[col].notna()].groupby(S[col].astype(str)).app.agg(lambda v: dict(Counter(v)))
        t = t[[sum(v.values()) >= 2 for v in t]]
        mixes[col] = {k: v for k, v in t.items()}
        single[col] = {a: {"values": int(sum(1 for v in t if list(v) == [a])),
                           "flows": int(sum(v[a] for v in t if list(v) == [a]))} for a in apps}
    fb = []
    for fid, r in S[S.app == "facebook"].iterrows():
        e = {"flow_id": r.flow_id}
        for col in ("shape", "up_sizes", "down_sizes", "syn_size", "hello_size", "reply_size"):
            v = r[col]
            e[col] = None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)
            e[col + "_mix"] = None if e[col] is None else dict(Counter(S.app[S[col].astype(str) == e[col]]))
        fb.append(e)
    return {"coverage": cov, "single_app": single, "mixes": mixes, "facebook": fb}


def auc_pair(X, y, pair, seed=2026):
    m = np.isin(y, pair)
    Xp, yp = X[m].reset_index(drop=True), y[m]
    splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=seed).split(Xp, yp))

    def fold(i, tr, te):
        sv = SoftVote(seed=i).fit(Xp.iloc[tr], yp[tr])
        return roc_auc_score(yp[te] == pair[0], sv.predict_proba(Xp.iloc[te])[:, list(sv.classes_).index(pair[0])])
    return float(np.mean(Parallel(n_jobs=-1)(delayed(fold)(i, tr, te) for i, (tr, te) in enumerate(splits))))


def main():
    OUT.mkdir(exist_ok=True)
    X2, y2 = load_task(T2)
    y = np.asarray(y2.values, dtype=object)
    S = pd.DataFrame([stamps(r) for r in X2.itertuples()])
    S.insert(0, "flow_id", X2.flow_id.values)
    cat = catalogue(S.copy(), y)
    Snum = S[NUM].astype(float).fillna(-1).reset_index(drop=True)
    X1, y1 = load_task(T1)
    assert (X1.flow_id.values == X2.flow_id.values).all() and (y1.values == y2.values).all()
    raw = {T1: TASK_FEATURES[T1](X1).reset_index(drop=True), T2: TASK_FEATURES[T2](X2).reset_index(drop=True)}
    sep = []
    for task, R in raw.items():
        for pair in CHOKES:
            a, b = auc_pair(R, y, pair), auc_pair(pd.concat([R, Snum], axis=1), y, pair)
            sep.append({"task": task, "pair": "/".join(pair), "auc_raw": round(a, 4), "auc_stamps": round(b, 4),
                        "delta": round(b - a, 4), "adds": bool(b - a >= 0.01)})
            print(sep[-1], flush=True)
    S.to_csv(OUT / "stamps_trainval.csv", index=False)
    (OUT / "catalogue.json").write_text(json.dumps(cat, indent=2, default=str) + "\n")
    (OUT / "separability.json").write_text(json.dumps(sep, indent=2) + "\n")
    man = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob("*")) if p.name != "MANIFEST.sha256"}
    (OUT / "MANIFEST.sha256").write_text("".join(f"{h}  {n}\n" for n, h in man.items()))
    print(json.dumps(cat["coverage"], indent=1))
    print(json.dumps(cat["single_app"], indent=1))


if __name__ == "__main__":
    main()
