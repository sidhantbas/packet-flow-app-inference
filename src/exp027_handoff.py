"""Experiment 027, steps 2-5: Charles's handoff (HANDOFF_sid.md) executed locally.

His baselines, reproduced: Task 1 (static) CatBoost with PyCaret's CPU defaults (border_count 254, no class
weights); Task 2 (prefix-5) ExtraTrees with PyCaret's defaults (100 trees, no class weights). Inputs: the 18
supplied columns (flow_id, split, start_rel excluded; server_port kept as in his run; transport udp = 1).
z-scoring is omitted: it does not change tree models. Folds: our repeated stratified 5 x 10 on train+validation
(his were 4-fold on train only), so variants are compared on identical folds.

Families, each added on its own to the baseline (step 2), compared with that baseline:
  A  size variability + direction balance: std/mean packet size per direction, downstream byte and packet share,
     empty-direction indicators
  B  relative timing: std_iat/mean_iat, max_iat/mean_iat, (max_iat - min_iat)/mean_iat
  C  intensity + burst density: total bytes/duration, total packets/duration, packets/burst, bursts/duration
  D  log1p of the nonnegative byte, count and timing fields (replaces them); also tested with logistic regression,
     the "linear or distance-based" case the handoff names
Separately (step 4): balanced class weights; CatBoost native categorical transport (Task 1).
Undefined ratios (zero denominator) are 0 plus, for A, explicit empty-direction flags; no tiny-epsilon division.
Usage: python src/exp027_handoff.py [--seed N]   (all variants at that cv_seed; references = his baselines at that seed)
"""
import sys
from datetime import datetime, timezone

import numpy as np
from catboost import CatBoostClassifier
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from cv import TASKS, basic_features, evaluate
from runlog import record_run

T1, T2 = TASKS
LOG_COLS = ["duration", "packet_count_up", "packet_count_down", "bytes_up", "bytes_down", "mean_pkt_size_up",
            "mean_pkt_size_down", "std_pkt_size_up", "std_pkt_size_down", "mean_iat", "std_iat", "min_iat", "max_iat",
            "burst_count"]


def div(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return np.where(b > 0, a / np.where(b > 0, b, 1), 0.0)


def charles_base(X):
    """The 18 columns of his run: everything except flow_id, split, start_rel."""
    return basic_features(X, drop=["flow_id", "split", "start_rel"])


def fam_a(X):
    return {"cv_size_up": div(X.std_pkt_size_up, X.mean_pkt_size_up),
            "cv_size_down": div(X.std_pkt_size_down, X.mean_pkt_size_down),
            "down_byte_share": div(X.bytes_down, X.bytes_up + X.bytes_down),
            "down_pkt_share": div(X.packet_count_down, X.packet_count_up + X.packet_count_down),
            "no_up": (X.packet_count_up == 0).astype(int).values, "no_down": (X.packet_count_down == 0).astype(int).values}


def fam_b(X):
    return {"cv_iat": div(X.std_iat, X.mean_iat), "max_over_mean_iat": div(X.max_iat, X.mean_iat),
            "range_over_mean_iat": div(X.max_iat - X.min_iat, X.mean_iat)}


def fam_c(X):
    n = X.packet_count_up + X.packet_count_down
    return {"bytes_per_s": div(X.bytes_up + X.bytes_down, X.duration), "pkts_per_s": div(n, X.duration),
            "pkts_per_burst": div(n, X.burst_count), "bursts_per_s": div(X.burst_count, X.duration)}


def features(family):
    def f(X):
        B = charles_base(X)
        if family == "D":
            B[LOG_COLS] = np.log1p(B[LOG_COLS])
        elif family:
            for k, v in {"A": fam_a, "B": fam_b, "C": fam_c}[family](X).items():
                B[k] = v
        return B
    f.__name__ = f"charles_base{'+' + family if family else ''}"
    return f


def catboost_charles(balanced=False, cat=False):
    def f(seed, class_weight=None):
        kw = {"auto_class_weights": "Balanced"} if balanced else {}
        return CatBoostClassifier(random_state=seed, verbose=False, thread_count=1, task_type="CPU", border_count=254,
                                  allow_writing_files=False, cat_features=["transport"] if cat else None, **kw)
    f.__name__ = f"catboost_charles{'_balanced' if balanced else ''}{'_cat' if cat else ''}"
    return f


def et_charles(balanced=False):
    def f(seed, class_weight=None):
        return ExtraTreesClassifier(n_estimators=100, random_state=seed, n_jobs=1,
                                    class_weight="balanced" if balanced else None)
    f.__name__ = f"et_charles{'_balanced' if balanced else ''}"
    return f


def logreg_plain(seed, class_weight=None):
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=5000, random_state=seed))


MODEL = {T1: catboost_charles(), T2: et_charles()}
SHORT = {T1: "t1", T2: "t2"}


def run(name, task, feats, factory, cv_seed, reference, question):
    t0 = datetime.now(timezone.utc)
    return record_run("027", f"{SHORT[task]}_{name}" + ("" if cv_seed == 2026 else f"_s{cv_seed}"),
                      {task: evaluate(task, feats, factory, cv_seed=cv_seed)}, model_factory=factory, feature_fn=feats,
                      reference=reference, question=question,
                      config={"model": factory.__name__, "features": feats.__name__, "cv_seed": cv_seed,
                              "source": "HANDOFF_sid.md (Charles, 2026-10-01)"}, started=t0)


def main(cv_seed):
    for task in TASKS:
        base = run("base", task, features(None), MODEL[task], cv_seed, None,
                   f"Charles's baseline ({MODEL[task].__name__}, 18 columns), cv_seed {cv_seed}")
        for fam in "ABCD":
            run(f"fam{fam}", task, features(fam), MODEL[task], cv_seed, base,
                f"Handoff family {fam} on Charles's baseline, cv_seed {cv_seed}?")
        bal = catboost_charles(balanced=True) if task == T1 else et_charles(balanced=True)
        run("balanced", task, features(None), bal, cv_seed, base, f"Balanced class weights on Charles's baseline, cv_seed {cv_seed}?")
        if task == T1:
            run("cat_transport", task, features(None), catboost_charles(cat=True), cv_seed, base,
                f"CatBoost native categorical transport, cv_seed {cv_seed}?")
        lr_base = run("lr_base", task, features(None), logreg_plain, cv_seed, None,
                      f"Logistic regression reference (raw, z-scored), cv_seed {cv_seed}")
        run("lr_famD", task, features("D"), logreg_plain, cv_seed, lr_base,
            f"Family D (log1p) for logistic regression, cv_seed {cv_seed}?")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(int(args[args.index("--seed") + 1]) if "--seed" in args else 2026)
