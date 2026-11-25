"""Experiment 085 stage 1: pair-verifier screen on the base models' out-of-fold predictions (cv_seed 2026)
(protocol: experiments/085_pair_verifier_sweep.md, frozen first). Writes experiments/085_evidence/stage1.json."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASK_FEATURES, load_task
from models import SoftVote

ROOT = Path(__file__).resolve().parent.parent
LABS = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
BASE = {"task1_static": "results/20261009T220447Z_084_ALL/task1_static/oof.csv",
        "task2_realtime_prefix5": "results/20260930T173836Z_014_fi_same_nocw/task2_realtime_prefix5/oof.csv"}
CELLS = {"T1-YI": ("task1_static", "youtube", ("instagram", "youtube")),
         "T1-FG": ("task1_static", "facebook", ("facebook", "google")),
         "T1-XF": ("task1_static", "x", ("facebook", "x")),
         "T2-XF": ("task2_realtime_prefix5", "x", ("facebook", "x")),
         "T2-XM": ("task2_realtime_prefix5", "x", ("mozilla", "x")),
         "T2-XY": ("task2_realtime_prefix5", "x", ("x", "youtube")),
         "T2-YI": ("task2_realtime_prefix5", "youtube", ("instagram", "youtube")),
         "T2-GM": ("task2_realtime_prefix5", "google", ("google", "mozilla")),
         "T2-MG": ("task2_realtime_prefix5", "mozilla", ("google", "mozilla"))}


def screen():
    out = {}
    for task in BASE:
        Xr, y = load_task(task)
        X, yv = TASK_FEATURES[task](Xr), np.asarray(y.values, dtype=object)
        splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2026).split(X, y))
        oof = pd.read_csv(ROOT / BASE[task])
        flows = np.concatenate([Xr.flow_id.values[te] for _, te in splits])
        assert (oof.flow_id.values == flows).all()
        pp, yt, rep = oof.y_pred.values.astype(object), oof.y_true.values.astype(object), oof.fold.values // 5
        macro = lambda p: float(np.mean([f1_score(yt[rep == k], p[rep == k], labels=LABS, average="macro") for k in range(10)]))
        base = macro(pp)
        jobs, pos = [], 0
        for i, (tr, te) in enumerate(splits):
            jobs.append((i, tr, te, slice(pos, pos + len(te))))
            pos += len(te)
        for cid, (t, call, pair) in CELLS.items():
            if t != task:
                continue

            def fold(i, tr, te, sl):
                m = np.isin(yv[tr], pair)
                o = pp[sl].copy()
                c = o == call
                if c.any():
                    o[c] = SoftVote(seed=i).fit(X.iloc[tr[m]], yv[tr[m]]).predict(X.iloc[te[c]])
                return sl, o

            q = pp.copy()
            for sl, o in Parallel(n_jobs=-1)(delayed(fold)(*j) for j in jobs):
                q[sl] = o
            ch = q != pp
            rem, brk, mq = int((ch & (q == yt)).sum()), int((ch & (pp == yt)).sum()), macro(q)
            out[cid] = {"task": task, "base_macro": round(base, 4), "macro": round(mq, 4), "delta": round(mq - base, 4),
                        "changed": int(ch.sum()), "removed": rem, "broken": brk, "gate": bool(mq > base and rem >= 2 * brk)}
            print(cid, out[cid])
    return out


if __name__ == "__main__":
    res = screen()
    d = ROOT / "experiments/085_evidence"
    d.mkdir(exist_ok=True)
    (d / "stage1.json").write_text(json.dumps(res, indent=2) + "\n")
