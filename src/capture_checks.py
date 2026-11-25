"""Gates for our own captures before any training use (experiment 042; plan in docs/captures/exp041_capture_feasibility.md §6).

Command: .venv/bin/python src/capture_checks.py data/captures/s01 [data/captures/s02 ...]
  Gate 1  extractor identities: every formula identity of experiment 041 holds on 100% of captured flows (both tasks),
          and the Task 2 opening of each flow is consistent with its Task 1 flow.
  Report  opening shapes vs the original flows (TCP up/down patterns, exact first-packet sizes).
  Gate 2  proximity (labelled captured flows, per app and per Facebook/Instagram traffic type; 16 Task 1 columns, min_iat left out):
          median distance to the nearest original labelled flow <= 90th percentile of original leave-one-out distances;
          same-label share among the 5 nearest original flows >= the originals' own share;
          adversarial AUC (original vs captured, RF, 5-fold) <= 0.70.
Original data: train+validation features and labels only (no test labels).
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from cv import basic_features, load_task
from exp041_capture_feasibility import traffic_type
from models import T1_COLS

T1, T2 = "task1_static", "task2_realtime_prefix5"


def identities(X):
    """Experiment 041 identities for one feature table. Returns {name: (passed, total)}."""
    u, d = X.packet_count_up, X.packet_count_down
    n = u + d
    c = {}
    for dr, cnt in (("up", u), ("down", d)):
        b, ms, sd = X[f"bytes_{dr}"], X[f"mean_pkt_size_{dr}"], X[f"std_pkt_size_{dr}"]
        c[f"bytes_{dr} integer"] = np.isclose(b, b.round())
        c[f"mean_pkt_size_{dr} = bytes/count"] = np.isclose(ms, np.where(cnt > 0, b / cnt.clip(lower=1), 0))
        c[f"std_pkt_size_{dr} = 0 for <= 1 packet"] = (sd == 0) | (cnt > 1)
        c[f"sizes in [60, 1514] ({dr})"] = ((ms >= 60) & (ms <= 1514)) | (cnt == 0)
    c["mean_iat = duration/(n-1)"] = np.isclose(X.mean_iat, X.duration / (n - 1), rtol=1e-6, atol=1e-9)
    c["min <= mean <= max <= duration"] = (X.min_iat <= X.mean_iat + 1e-9) & (X.mean_iat <= X.max_iat + 1e-9) & (X.max_iat <= X.duration + 1e-9)
    c["std_iat Bhatia-Davis"] = X.std_iat ** 2 <= (X.max_iat - X.mean_iat) * (X.mean_iat - X.min_iat) + 1e-9
    c["packet ratio = up/max(down,1)"] = np.isclose(X.up_down_packet_ratio, u / d.clip(lower=1))
    c["byte ratio = bytes_up/max(bytes_down,1)"] = np.isclose(X.up_down_byte_ratio, X.bytes_up / X.bytes_down.clip(lower=1))
    c["burst = 1 iff max_iat <= 1.0 s"] = (X.burst_count == 1) == (X.max_iat <= 1.0)
    c[">= 5 packets"] = n >= 5
    return {k: (int(np.sum(v)), len(X)) for k, v in c.items()}


def prefix_consistency(A, P):
    ok = ((P.packet_count_up + P.packet_count_down == 5) & (P.packet_count_up <= A.packet_count_up) & (P.packet_count_down <= A.packet_count_down)
          & (P.bytes_up <= A.bytes_up) & (P.bytes_down <= A.bytes_down) & (P.duration <= A.duration + 1e-9)
          & (P.max_iat <= A.max_iat + 1e-9) & (P.min_iat >= A.min_iat - 1e-9) & (P.burst_count <= A.burst_count)
          & (P.start_rel == A.start_rel) & (P.transport == A.transport))
    return int(ok.sum()), len(A)


def gate1(A, P):
    print("== Gate 1: extractor identities")
    fails = 0
    for name, X in (("task1", A), ("task2", P)):
        for k, (p, t) in identities(X).items():
            if p != t:
                fails += 1
                print(f"  FAIL {name}: {k} {p}/{t}")
    p, t = prefix_consistency(A, P)
    fails += p != t
    print(f"  Task 2 opening consistent with Task 1 flow: {p}/{t}")
    print(f"  Gate 1 {'PASS' if fails == 0 else 'FAIL'}")
    return fails == 0


def opening_report(P, Po):
    print("\n== Opening shapes (Task 2), captured vs original")
    for tr in ("tcp", "udp"):
        a = P[P.transport == tr].groupby(["packet_count_up", "packet_count_down"]).size()
        b = Po[Po.transport == tr].groupby(["packet_count_up", "packet_count_down"]).size()
        print(f"  {tr} up/down: captured {(a / a.sum()).round(2).to_dict()} | original {(b / b.sum()).round(2).to_dict()}")
    for name, X in (("captured", P), ("original", Po)):
        t = X[(X.transport == "tcp") & (X.packet_count_up == 2)]
        lo = (t.mean_pkt_size_up - t.std_pkt_size_up).round().astype(int)
        print(f"  {name}: smaller of 2 TCP up packets {Counter(lo).most_common(5)} (original first TCP packet 145-175 B)")
        q = X[(X.transport == "udp") & (X.std_pkt_size_up == 0) & (X.packet_count_up > 0)]
        print(f"  {name}: UDP up sizes (all equal) {Counter(q.mean_pkt_size_up.round().astype(int)).most_common(6)}")


# min_iat is left out of the distance: it is 0 in 97% of original flows because of timestamp batching at the organisers'
# capture point (041), so any other capture tool sits hundreds of standard deviations away on that column alone.
PROX_COLS = [c for c in T1_COLS if c != "min_iat"]


def scaled(Xo, Xn):
    L = lambda X: np.log1p(basic_features(X)[PROX_COLS].astype(float).clip(lower=0)).values
    Lo, Ln = L(Xo), L(Xn)
    mu, sd = Lo.mean(0), np.where(Lo.std(0) > 0, Lo.std(0), 1)
    return (Lo - mu) / sd, (Ln - mu) / sd


def gate2(A, labels, Ao, yo):
    print("\n== Gate 2: proximity to the original labelled flows (16 Task 1 columns without min_iat, log1p, standardised on originals)")
    print(f"  min_iat == 0: captured {(A.min_iat == 0).mean():.0%} vs original {(Ao.min_iat == 0).mean():.0%} (timestamp batching; reported, not gated)")
    m = labels.app.isin(sorted(set(yo))).values
    A, lab = A[m].reset_index(drop=True), labels.app[m].values
    if len(A) == 0:
        print("  no labelled captured flows with a challenge app label")
        return False
    Zo, Zn = scaled(Ao, A)
    Doo = np.sqrt(((Zo[:, None] - Zo[None]) ** 2).sum(-1))
    np.fill_diagonal(Doo, np.inf)
    Dno = np.sqrt(((Zn[:, None] - Zo[None]) ** 2).sum(-1))
    yo = np.asarray(yo)
    nn_o = np.argsort(Doo, 1)[:, :5]
    nn_n = np.argsort(Dno, 1)[:, :5]
    groups = [(f"app {a}", lab == a, yo == a) for a in sorted(set(lab))]
    tt = A.apply(traffic_type, axis=1).values
    for a in ("facebook", "instagram"):
        for ty in sorted(set(tt[lab == a])):
            groups.append((f"{a} / {ty}", (lab == a) & (tt == ty), yo == a))
    ok_all = True
    for name, mn, mo in groups:
        thr = np.percentile(Doo[mo].min(1), 90)
        med = np.median(Dno[mn].min(1))
        app = name.split()[1] if name.startswith("app") else name.split(" / ")[0]
        same_n = (yo[nn_n[mn]] == app).mean()
        same_o = (yo[nn_o[mo]] == app).mean()
        ok = med <= thr and same_n >= same_o
        ok_all &= ok if name.startswith("app") else True
        print(f"  {name:38s} n={int(mn.sum()):3d}  median NN distance {med:.2f} (orig 90th pct {thr:.2f})  "
              f"same-label 5-NN {same_n:.2f} (orig {same_o:.2f})  {'ok' if ok else 'FAR'}")
    print("  label discovery: label of the nearest original flow, per captured session app (which app makes 'facebook'-like flows?)")
    nearest = yo[Dno.argmin(1)]
    for a in sorted(set(lab)):
        c = pd.Series(nearest[lab == a]).value_counts()
        print(f"    {a:9s} -> " + ", ".join(f"{k} {v}" for k, v in c.items()))
    X = np.vstack([Zo, Zn])
    t = np.r_[np.zeros(len(Zo)), np.ones(len(Zn))]
    p = cross_val_predict(RandomForestClassifier(300, random_state=0, class_weight="balanced"), X, t,
                          cv=StratifiedKFold(5, shuffle=True, random_state=0), method="predict_proba")[:, 1]
    auc = roc_auc_score(t, p)
    if len(Zn) < 30:
        print(f"  (only {len(Zn)} captured flows: the AUC is not meaningful below 30)")
        ok_all = False
    ok_all &= auc <= 0.70
    print(f"  adversarial AUC original vs captured: {auc:.3f} (gate <= 0.70)")
    print(f"  Gate 2 {'PASS' if ok_all else 'FAIL'} (per-app rows and AUC decide; type rows are diagnostics)")
    return ok_all


def ip_report(dirs):
    meta = [Path(d) / "flow_meta.csv" for d in dirs]
    if all(f.exists() for f in meta):
        M = pd.concat([pd.read_csv(f) for f in meta])
        print(f"IP version of captured flows: {M.ip_version.value_counts().to_dict()} (original: IPv4 only; IPv6 sized as IPv4)")


def load_captures(dirs):
    A = pd.concat([pd.read_csv(Path(d) / "task1_features.csv") for d in dirs], ignore_index=True)
    P = pd.concat([pd.read_csv(Path(d) / "task2_features.csv") for d in dirs], ignore_index=True)
    lab = [Path(d) / "labels.csv" for d in dirs]
    L = pd.concat([pd.read_csv(f).fillna("") for f in lab], ignore_index=True) if all(f.exists() for f in lab) else None
    assert (A.flow_id == P.flow_id).all()
    return A, P, L


def main(dirs):
    A, P, L = load_captures(dirs)
    Ao, yo = load_task(T1)
    Po, _ = load_task(T2)
    print(f"captured flows: {len(A)} from {len(dirs)} folder(s); original labelled flows: {len(Ao)}")
    ip_report(dirs)
    g1 = gate1(A, P)
    opening_report(P, Po)
    g2 = gate2(A, L, Ao, yo.values) if L is not None else False
    print(f"\nGates: 1 {'PASS' if g1 else 'FAIL'}, 2 {'PASS' if g2 else 'FAIL'}. Training use only if both pass.")


if __name__ == "__main__":
    main(sys.argv[1:])
