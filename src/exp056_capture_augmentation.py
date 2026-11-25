"""Experiment 056: captured facebook/instagram flows in Task 1 training folds (protocol: experiments/056_capture_augmentation.md).

User decision 2026-10-09: run this training test although gates 1-2 failed (055); adoption needs rule v2 on 2026-2030
and the user's approval.
Usage:
  python src/exp056_capture_augmentation.py --extract                 re-extract the sources with --split-merged, gate 1
  python src/exp056_capture_augmentation.py --arm F|FI [--seed N --ref RUN_ID]
  python src/exp056_capture_augmentation.py --production --seed N    production reference on a confirmation seed
Captured rows are appended to training folds only (cv.evaluate `resample`); held-out flows are always original.
"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from cv import TASK_FEATURES, basic_features, evaluate
from models import TASK_MODELS
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
TASK = "task1_static"
PILOT, LONG = "sid-iphone-20261008T233855Z", "sid-iphone-20261009T115620Z-long-cellular"
OUT = ROOT / "data/captures/056-augmentation"
# (group, session, app); frozen in the protocol
SOURCES = [(PILOT, "02-facebook-feed", "facebook"), (PILOT, "03-facebook-reels", "facebook"), (LONG, "02-facebook", "facebook"),
           (PILOT, "04-instagram-feed-cellular", "instagram"), (LONG, "03-instagram", "instagram")]
ARMS = {"F": ("facebook",), "FI": ("facebook", "instagram")}


def src_dir(group, session):
    return OUT / f"{group}__{session}"


def extract():
    if OUT.exists():
        raise SystemExit(f"{OUT.relative_to(ROOT)} exists: evidence is immutable")
    for g, s, _ in SOURCES:
        r = subprocess.run([sys.executable, ROOT / "src/capture_extract.py", "--pcap", ROOT / "data/captures/raw" / g / s / "packets.pcapng",
                            "--phone-ip", "auto", "--sessions", ROOT / "data/captures" / g / "sessions.csv", "--split-merged",
                            "--out", src_dir(g, s)], cwd=ROOT, capture_output=True, text=True, check=True)
        print(f"{g}/{s}: " + " | ".join(l for l in r.stdout.splitlines() if l.startswith(("merged", "labels"))))
    r = subprocess.run([sys.executable, ROOT / "src/capture_checks.py", *[src_dir(g, s) for g, s, _ in SOURCES]],
                       cwd=ROOT, capture_output=True, text=True, check=True)
    (OUT / "gates.txt").write_text(r.stdout)
    print("\n".join(l for l in r.stdout.splitlines() if "Gate" in l or "FAIL" in l))


def captured_rows():
    """Production Task 1 features (basic Task 1 columns + p5_ Task 2 columns) and session labels of every source."""
    rows, labels = [], []
    for g, s, app in SOURCES:
        d = src_dir(g, s)
        T1, T2 = pd.read_csv(d / "task1_features.csv"), pd.read_csv(d / "task2_features.csv")
        L = pd.read_csv(d / "labels.csv")
        assert (T1.flow_id == T2.flow_id).all() and (T1.flow_id == L.flow_id).all() and (L.app == app).all()
        P = basic_features(T2).reset_index(drop=True)
        P.columns = [f"p5_{c}" for c in P.columns]
        rows.append(pd.concat([basic_features(T1).reset_index(drop=True), P], axis=1))
        labels += [app] * len(T1)
    return pd.concat(rows, ignore_index=True), np.array(labels)


def make_resample(arm):
    C, yc = captured_rows()
    keep = np.isin(yc, ARMS[arm])
    C, yc = C[keep], yc[keep]

    def resample(X_tr, y_tr, seed):
        Cx = C[X_tr.columns].copy()
        Cx.index = np.arange(len(Cx)) + int(X_tr.index.max()) + 1
        return pd.concat([X_tr, Cx]), pd.concat([pd.Series(np.asarray(y_tr), index=X_tr.index), pd.Series(yc, index=Cx.index)])
    resample.n_added = {a: int((yc == a).sum()) for a in ARMS[arm]}
    return resample


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--extract" in args:
        extract()
        sys.exit()
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    f, feats = TASK_MODELS[TASK], TASK_FEATURES[TASK]
    t0 = datetime.now(timezone.utc)
    if "--production" in args:
        res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
        rid = record_run("056", f"production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"Task 1 production reference on cv_seed {seed} (for 056 confirmation)",
                         config={"model": "task1_meta_gate", "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        arm = args[args.index("--arm") + 1]
        rs = make_resample(arm)
        res = {TASK: evaluate(TASK, feats, f, resample=rs, cv_seed=seed)}
        rid = record_run("056", f"aug_{arm}" + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f, feature_fn=feats,
                         reference=ref, question=f"Task 1: do captured {'/'.join(ARMS[arm])} flows in training folds beat production? cv_seed {seed}",
                         config={"model": "task1_meta_gate + captured rows (training folds only)", "arm": arm,
                                 "captured_rows": rs.n_added, "sources": [f"{g}/{s}" for g, s, a in SOURCES if a in ARMS[arm]],
                                 "extraction": "capture_extract.py --tcp-start syn --split-merged", "cv_seed": seed,
                                 "features": feats.__name__, "user_decision": "2026-10-09 run despite gates 1-2 failing"},
                         started=t0)
    print(rid)
