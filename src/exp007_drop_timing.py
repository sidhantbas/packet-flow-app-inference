"""Experiment 007: faster CV (step 0), then removing timing features.

Usage: python src/exp007_drop_timing.py [confirm]

Step 0: re-run the champion with fold-parallel CV and single-threaded models; scores must be identical.
Variants (each against the champion, on its own task only):
  A  task 2 without duration, mean_iat, std_iat, max_iat  (all shuffle-negative in Charles's run)
  B  task 2 without all five timing columns (A + min_iat)  (secondary)
  C  task 1 without min_iat  (0 in 98% of task 1 flows; zero importance in Charles's run)
"""
from datetime import datetime, timezone

from cv import TASKS, basic_features, evaluate
from models import SoftVote
from runlog import record_run

T1, T2 = TASKS
TIMING4 = ["duration", "mean_iat", "std_iat", "max_iat"]


def softvote(seed):
    return SoftVote(seed=seed)


def drop(cols):
    def feats(X):
        return basic_features(X).drop(columns=cols)
    feats.__name__ = "basic_minus_" + "_".join(cols)
    return feats


def run(name, tasks, feats, question):
    t0 = datetime.now(timezone.utc)
    res = {t: evaluate(t, feats, softvote) for t in tasks}
    return record_run("007", name, res, question=question, model_factory=softvote, feature_fn=feats,
                      config={"model": "SoftVote", "features": feats.__name__}, started=t0)


if __name__ == "__main__" and __import__("sys").argv[1:] == []:
    run("softvote_fastcv", TASKS, basic_features,
        "Step 0: does fold-parallel CV with single-threaded models reproduce the champion exactly?")
    run("t2_drop_timing4", [T2], drop(TIMING4), "Does task 2 improve without duration/mean/std/max IAT?")
    run("t2_drop_timing5", [T2], drop(TIMING4 + ["min_iat"]), "Does task 2 improve without all five timing columns?")
    run("t1_drop_min_iat", [T1], drop(["min_iat"]), "Does task 1 improve without min_iat?")


def confirm():
    """Confirmation on fresh folds (cv_seeds 2027, 2028) and with RF: is the task 2 gain robust?"""
    from models import rf
    for seed in (2027, 2028):
        for model_name, factory in (("softvote", softvote), ("rf", rf)):
            base = {T2: evaluate(T2, basic_features, factory, cv_seed=seed)}
            ref = record_run("007", f"confirm_s{seed}_{model_name}_full", base, reference=None,
                             question=f"Confirmation reference: {model_name}, all features, cv_seed {seed}.",
                             model_factory=factory, feature_fn=basic_features,
                             config={"model": model_name, "cv_seed": seed})
            for cols in (TIMING4, TIMING4 + ["min_iat"]):
                f = drop(cols)
                res = {T2: evaluate(T2, f, factory, cv_seed=seed)}
                record_run("007", f"confirm_s{seed}_{model_name}_drop{len(cols)}", res, reference=ref,
                           question=f"Confirmation: task 2 without {len(cols)} timing columns, {model_name}, cv_seed {seed}.",
                           model_factory=factory, feature_fn=f,
                           config={"model": model_name, "features": f.__name__, "cv_seed": seed})


if __name__ == "__main__" and __import__("sys").argv[1:] == ["confirm"]:
    confirm()
