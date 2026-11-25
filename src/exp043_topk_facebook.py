"""Experiment 043: push borderline flows to facebook, on top of the frozen production models (both tasks).

Settings fixed before running (2026-10-07). Both variants only ADD facebook labels; production's facebook calls stay.
Facebook score per flow: P(fb) = P(Meta) x P(fb | Meta), from the parts production already uses:
  Task 1 (MetaGate): P(Meta) = gate-weighted two-clerks probability of facebook + instagram; P(fb | Meta) from the
          whole-run expert (it decides facebook vs instagram in production).
  Task 2 (PairSpecialist): P(Meta) = base SoftVote probability of facebook + instagram; P(fb | Meta) from the
          facebook/instagram stage.
Variants:
  topk     k = round(training facebook share x number of flows predicted); if production predicts fewer than k
           facebook flows, the highest-scoring other flows become facebook until there are k. Never uses test labels.
  pairthr  flows production calls facebook or instagram: facebook if P(fb | Meta) >= t, t = facebook share among the
           training fold's Meta flows (~0.37, instead of production's 0.5).
Seen before choosing pairthr: the scratchpad diagnostic of 2026-10-06 (a pair-only SoftVote on the 30 Meta flows
favoured a threshold below 0.5 on Task 1). t is set by the class-share rule above, not read off that curve.
Decision: rule v2 vs the production champion on cv_seed 2026; only a pass is confirmed on 2027-2030.
Usage: python src/exp043_topk_facebook.py [topk|pairthr ...] [--seed N --ref RUN_ID]
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

from cv import TASK_FEATURES, TASKS, evaluate
from models import TASK_MODELS
from runlog import record_run

META = ("facebook", "instagram")


def facebook_scores(model, X):
    """(P(Meta), P(fb | Meta)) per flow from a fitted production model of either task."""
    cls = list(model.classes_)
    fb, ig = cls.index("facebook"), cls.index("instagram")
    if hasattr(model, "gate_"):  # Task 1 MetaGate: same probabilities as MetaGate.predict
        c = model.clerks_
        pw = c.whole_.predict_proba(X)
        g = model.gate_.predict_proba(X)[:, list(model.gate_.classes_).index("meta")]
        # MetaGate re-weights p so that the Meta classes together get the gate's probability g
        p_fb_meta = pw[:, fb] / np.clip(pw[:, fb] + pw[:, ig], 1e-12, None)
        return g, p_fb_meta
    # Task 2 PairSpecialist
    pb = model.base_.predict_proba(X[model.base_cols_])
    spec = model.spec_.predict_proba(X[model.spec_cols_])[:, list(model.spec_.classes_).index("facebook")]
    return pb[:, fb] + pb[:, ig], spec


class PushFacebook(BaseEstimator, ClassifierMixin):
    def __init__(self, task="task1_static", mode="topk", seed=0):
        self.task, self.mode, self.seed = task, mode, seed

    def fit(self, X, y):
        y = np.asarray(y)
        self.model_ = TASK_MODELS[self.task](self.seed).fit(X, y)
        self.classes_ = self.model_.classes_
        self.share_ = np.mean(y == "facebook")
        self.meta_share_ = np.mean(y[np.isin(y, META)] == "facebook")
        return self

    def predict(self, X):
        pred = np.asarray(self.model_.predict(X)).astype(object).copy()
        p_meta, p_fb_meta = facebook_scores(self.model_, X)
        if self.mode == "topk":
            k = int(round(self.share_ * len(X)))
            need = k - int(np.sum(pred == "facebook"))
            if need > 0:
                cand = np.flatnonzero(pred != "facebook")
                top = cand[np.argsort(-(p_meta * p_fb_meta)[cand], kind="stable")[:need]]
                pred[top] = "facebook"
        elif self.mode == "pairthr":
            m = np.isin(pred, META) & (p_fb_meta >= self.meta_share_)
            pred[m] = "facebook"
        else:
            raise ValueError(self.mode)
        return pred.astype(str)


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    modes = [a for a in args if a in ("topk", "pairthr")] or ["topk", "pairthr"]
    for mode in modes:
        t0 = datetime.now(timezone.utc)
        res = {}
        for t in TASKS:
            f = lambda s, t=t, m=mode: PushFacebook(task=t, mode=m, seed=s)
            res[t] = evaluate(t, TASK_FEATURES[t], f, cv_seed=seed)
        record_run("043", mode + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f, reference=ref,
                   question=f"Does pushing borderline flows to facebook ({mode}) beat production? cv_seed {seed}",
                   config={"model": f"PushFacebook(production, mode={mode})", "cv_seed": seed,
                           "features": {t: TASK_FEATURES[t].__name__ for t in TASKS}}, started=t0)
