"""Experiment 126: Task 1 Meta-leak audit and volume rescue (protocol: experiments/126_task1_meta_leak_rescue.md, frozen first).

Usage:
  .venv/bin/python src/exp126_meta_leak_rescue.py --audit            Part A -> experiments/126_evidence/audit.json
  .venv/bin/python src/exp126_meta_leak_rescue.py --arms             Part B: 6 arms at cv_seed 2026 vs the champion
  .venv/bin/python src/exp126_meta_leak_rescue.py --confirm ARM      Part C: production + ARM on cv_seeds 2186-2190
  .venv/bin/python src/exp126_meta_leak_rescue.py --test ARM         Part D -> experiments/126_evidence/test_reach.json
ARM = IG_0.5 | IG_0.7 | IG_0.9 | PAIR_0.5 | PAIR_0.7 | PAIR_0.9
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import DATA, TASK_FEATURES, evaluate, load_task
from models import TASK_MODELS, SoftVote
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
TASK = "task1_static"
META = ("facebook", "instagram")
VOLUME = ["bytes_down", "packet_count_down", "bytes_up", "burst_count", "packet_count_up"]
CHAMPION = "20261012T154049Z_100_production_check_s2026"
ARMS = {f"{k}_{t}": (k, t) for k in ("IG", "PAIR") for t in (0.5, 0.7, 0.9)}
FRESH = [2186, 2187, 2188, 2189, 2190]
OUT = ROOT / "experiments/126_evidence"


class VolumeRescue(BaseEstimator, ClassifierMixin):
    """Production Task 1 model; a flow it calls non-Meta whose volume-Meta score >= threshold becomes instagram (IG) or the
    pair decider's facebook/instagram label (PAIR)."""

    def __init__(self, kind="IG", threshold=0.5, seed=0):
        self.kind, self.threshold, self.seed = kind, threshold, seed

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.base_ = TASK_MODELS[TASK](self.seed).fit(X, y)
        self.vol_ = SoftVote(seed=self.seed).fit(X[VOLUME], np.where(np.isin(y, META), "meta", "rest"))
        m = np.isin(y, META)
        self.pair_ = SoftVote(seed=self.seed).fit(X[m], y[m]) if self.kind == "PAIR" else None
        self.classes_ = self.base_.classes_
        return self

    def meta_score(self, X):
        return self.vol_.predict_proba(X[VOLUME])[:, list(self.vol_.classes_).index("meta")]

    def predict(self, X):
        p = np.asarray(self.base_.predict(X), dtype=object)
        move = ~np.isin(p, META) & (self.meta_score(X) >= self.threshold)
        if move.any():
            p[move] = "instagram" if self.kind == "IG" else self.pair_.predict(X[move])
        return p


def factory(arm):
    kind, t = ARMS[arm]
    return lambda seed: VolumeRescue(kind=kind, threshold=t, seed=seed)


def audit():
    X_raw, y = load_task(TASK)
    X = TASK_FEATURES[TASK](X_raw)
    oof = pd.read_csv(ROOT / "results" / CHAMPION / TASK / "oof.csv")
    splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2026).split(X, y))
    score = []
    for k, (tr, te) in enumerate(splits):
        v = SoftVote(seed=k).fit(X.iloc[tr][VOLUME], np.where(np.isin(y.iloc[tr], META), "meta", "rest"))
        s = v.predict_proba(X.iloc[te][VOLUME])[:, list(v.classes_).index("meta")]
        score.append(pd.DataFrame({"fold": k, "flow_id": X_raw.flow_id.iloc[te].values, "vol_meta": s}))
    S = oof.merge(pd.concat(score), on=["fold", "flow_id"], how="left")
    assert S.vol_meta.notna().all() and len(S) == 3300
    leak = S[S.y_true.isin(META) & ~S.y_pred.isin(META)]
    per_flow = (S[S.y_true.isin(META)].groupby("flow_id")
                .agg(y_true=("y_true", "first"), leaked=("y_pred", lambda s: int((~s.isin(META)).sum())),
                     called=("y_pred", lambda s: s[~s.isin(META)].value_counts().to_dict()), vol_meta=("vol_meta", "mean")))
    V = X.assign(flow_id=X_raw.flow_id.values, y=y.values)[["flow_id", "y"] + VOLUME]
    leaked_ids = per_flow.index[per_flow.leaked >= 5]
    ok_ids = per_flow.index[per_flow.leaked < 5]
    prof = lambda d: {c: float(d[c].median()) for c in VOLUME}
    nonmeta = S[~S.y_true.isin(META)]
    res = {"champion": CHAMPION,
           "leak_predictions": int(len(leak)), "leak_per_repeat": len(leak) / 10,
           "leak_by_class_called": leak.y_pred.value_counts().to_dict(),
           "leak_by_true_class": leak.y_true.value_counts().to_dict(),
           "meta_predictions_total": int(S.y_true.isin(META).sum()),
           "flows_leaked_majority": per_flow[per_flow.leaked >= 5].reset_index().to_dict("records"),
           "flows_leaked_sometimes": per_flow[(per_flow.leaked > 0) & (per_flow.leaked < 5)].reset_index().to_dict("records"),
           "volume_median_leaked_flows": prof(V[V.flow_id.isin(leaked_ids)]) if len(leaked_ids) else None,
           "volume_median_meta_called_meta": prof(V[V.flow_id.isin(ok_ids)]),
           "volume_median_by_true_nonmeta_class": {a: prof(V[V.y == a]) for a in ("google", "mozilla", "x", "youtube")},
           "vol_meta_score_leaked_predictions_median": float(leak.vol_meta.median()) if len(leak) else None,
           "vol_meta_score_true_nonmeta_called_nonmeta": {f"q{q}": float(nonmeta[~nonmeta.y_pred.isin(META)].vol_meta.quantile(q / 100))
                                                          for q in (50, 90, 95, 99)},
           "true_nonmeta_called_nonmeta_above": {str(t): int((nonmeta[~nonmeta.y_pred.isin(META)].vol_meta >= t).sum()) for t in (0.5, 0.7, 0.9)},
           "leaked_predictions_above": {str(t): int((leak.vol_meta >= t).sum()) for t in (0.5, 0.7, 0.9)}}
    OUT.mkdir(exist_ok=True)
    (OUT / "audit.json").write_text(json.dumps(res, indent=2, default=str) + "\n")
    print(json.dumps(res, indent=1, default=str))


def run_arms():
    feats = TASK_FEATURES[TASK]
    for arm in ARMS:
        t0 = datetime.now(timezone.utc)
        f = factory(arm)
        res = {TASK: evaluate(TASK, feats, f, cv_seed=2026)}
        rid = record_run("126", f"{arm}_s2026", res, model_factory=f, feature_fn=feats, reference="champion",
                         question=f"Task 1 126 arm {arm}: production + volume rescue of non-Meta calls into Meta; cv_seed 2026",
                         config={"arm": arm, "kind": ARMS[arm][0], "threshold": ARMS[arm][1], "volume_columns": VOLUME,
                                 "cv_seed": 2026, "features": feats.__name__}, started=t0)
        print(arm, rid)


def confirm(arm):
    feats, f0, f = TASK_FEATURES[TASK], TASK_MODELS[TASK], factory(arm)
    for seed in FRESH:
        t0 = datetime.now(timezone.utc)
        ref = record_run("126", f"P_s{seed}", {TASK: evaluate(TASK, feats, f0, cv_seed=seed)}, model_factory=f0, feature_fn=feats,
                         reference=None, question=f"Task 1 production reference on never-used cv_seed {seed} (126)",
                         config={"arm": "P", "cv_seed": seed, "features": feats.__name__}, started=t0)
        t0 = datetime.now(timezone.utc)
        rid = record_run("126", f"{arm}_s{seed}", {TASK: evaluate(TASK, feats, f, cv_seed=seed)}, model_factory=f, feature_fn=feats,
                         reference=ref, question=f"Task 1 126 confirmation of {arm} on never-used cv_seed {seed}",
                         config={"arm": arm, "kind": ARMS[arm][0], "threshold": ARMS[arm][1], "volume_columns": VOLUME,
                                 "cv_seed": seed, "features": feats.__name__}, started=t0)
        print(seed, ref, rid)


def upload_files():
    U = pd.read_csv(ROOT / "submissions/uploads.csv")
    out = {}
    for r in U.itertuples():
        f = str(r.file)
        if f.startswith("submissions/"):
            p = ROOT / f.split(" ")[0] / "submission.json"
            if p.exists():
                out[int(r.upload)] = json.loads(p.read_text())["task1_static"]
        elif f.startswith("commit "):
            c = f.split()[1]
            s = subprocess.run(["git", "show", f"{c}:submissions/submission.json"], cwd=ROOT, capture_output=True, text=True)
            if s.returncode == 0:
                out[int(r.upload)] = json.loads(s.stdout)["task1_static"]
    return out


def test_reach(arm):
    feats = TASK_FEATURES[TASK]
    X_raw, y = load_task(TASK)
    Xt_raw = pd.read_csv(DATA / TASK / "test_features.csv")
    X, Xt = feats(X_raw), feats(Xt_raw)
    kind, t = ARMS[arm]
    m = VolumeRescue(kind=kind, threshold=t, seed=0).fit(X, y)
    base = np.asarray(m.base_.predict(Xt), dtype=object)
    new = m.predict(Xt)
    ids = Xt_raw.flow_id.values
    changed = [{"flow_id": i, "production": b, "arm": n, "vol_meta": round(float(s), 3)}
               for i, b, n, s in zip(ids, base, new, m.meta_score(Xt)) if b != n]
    ups = upload_files()
    vs_up = {u: int(sum(p.get(i) != n for i, n in zip(ids, new))) for u, p in ups.items()}
    res = {"arm": arm, "changed_vs_production": len(changed), "changes": changed,
           "predicted_counts_production": pd.Series(base).value_counts().to_dict(),
           "predicted_counts_arm": pd.Series(new).value_counts().to_dict(),
           "differs_from_uploads": vs_up, "uploads_missing": sorted(set(range(1, 10)) - set(ups)),
           "min_difference_vs_any_upload": min(vs_up.values()) if vs_up else None}
    OUT.mkdir(exist_ok=True)
    (OUT / "test_reach.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--audit" in a:
        audit()
    elif "--arms" in a:
        run_arms()
    elif "--confirm" in a:
        confirm(a[a.index("--confirm") + 1])
    elif "--test" in a:
        test_reach(a[a.index("--test") + 1])
