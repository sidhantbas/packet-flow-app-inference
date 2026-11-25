"""Experiment 018: model settings, part A = exploratory sweep (both tasks, champion structure).

The sweep is only a map of sensitivity: picking the best of several settings on the same folds is biased, so
nothing here is adopted directly. If a setting moves the score clearly, part B tunes it by nested CV
(chosen inside each training fold) and confirms on cv_seeds 2027/2028.

Variants change the base ensemble members (task 2 keeps the fb/ig specialist on top):
  mf05 / mf10      RF + ExtraTrees with max_features 0.5 / 1.0 (default "sqrt" ≈ 0.24 of 17 columns)
  lgb_small        LightGBM num_leaves 7, min_child_samples 10
  lgb_deep         LightGBM num_leaves 31, min_child_samples 2
  trees1000        RF + ExtraTrees with 1000 trees (noise check)
"""
from datetime import datetime, timezone

from lightgbm import LGBMClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier

from cv import TASK_FEATURES, TASKS, evaluate
from models import MODEL_JOBS, Blend, MultiSpecialist, et, lgbm, rf
from runlog import record_run

T1, T2 = TASKS


def trees(max_features="sqrt", n=500):
    def r(seed, class_weight="balanced"):
        return RandomForestClassifier(n_estimators=n, max_features=max_features, class_weight=class_weight,
                                      random_state=seed, n_jobs=MODEL_JOBS)

    def e(seed, class_weight="balanced"):
        return ExtraTreesClassifier(n_estimators=n, max_features=max_features, class_weight=class_weight,
                                    random_state=seed, n_jobs=MODEL_JOBS)
    r.__name__, e.__name__ = f"rf_mf{max_features}_n{n}", f"et_mf{max_features}_n{n}"
    return r, e


def lgb(num_leaves, min_child):
    def f(seed, class_weight="balanced"):
        return LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=num_leaves, min_child_samples=min_child,
                              class_weight=class_weight, random_state=seed, n_jobs=MODEL_JOBS, verbose=-1)
    f.__name__ = f"lgbm_l{num_leaves}_c{min_child}"
    return f


VARIANTS = {
    "mf05": (*trees(0.5), lgbm),
    "mf10": (*trees(1.0), lgbm),
    "lgb_small": (rf, et, lgb(7, 10)),
    "lgb_deep": (rf, et, lgb(31, 2)),
    "trees1000": (*trees("sqrt", 1000), lgbm),
}
FI = (("facebook", "instagram"), "base", None)

if __name__ == "__main__" and __import__("sys").argv[1:] == []:
    for name, members in VARIANTS.items():
        fs = {T1: lambda s, m=members: Blend(m, seed=s),
              T2: lambda s, m=members: MultiSpecialist(None, (FI,), seed=s, base_members=m)}
        t0 = datetime.now(timezone.utc)
        res = {t: evaluate(t, TASK_FEATURES[t], fs[t]) for t in TASKS}
        record_run("018", name, res, model_factory=fs[T1], question=f"Sweep (exploratory): {name}",
                   config={"model": "Blend / MultiSpecialist(base_members)", "members": [m.__name__ for m in members],
                           "sweep": True}, started=t0)


def confirm_trees1000():
    """Task 1 trees1000 was BETTER at cv_seed 2026 (+0.002): re-test on cv_seeds 2027/2028."""
    from models import task1_model
    members = VARIANTS["trees1000"]
    f = lambda s: Blend(members, seed=s)
    for seed in (2027, 2028):
        t0 = datetime.now(timezone.utc)
        ref = record_run("018", f"t1_champion_s{seed}", {T1: evaluate(T1, TASK_FEATURES[T1], task1_model, cv_seed=seed)},
                         reference=None, model_factory=task1_model,
                         question=f"Confirmation reference: task 1 champion, cv_seed {seed}.",
                         config={"model": "task1_model", "cv_seed": seed}, started=t0)
        t0 = datetime.now(timezone.utc)
        record_run("018", f"t1_trees1000_s{seed}", {T1: evaluate(T1, TASK_FEATURES[T1], f, cv_seed=seed)},
                   reference=ref, model_factory=f, question=f"Confirmation: task 1 trees1000, cv_seed {seed}.",
                   config={"model": "Blend", "members": [m.__name__ for m in members], "cv_seed": seed}, started=t0)


if __name__ == "__main__" and __import__("sys").argv[1:] == ["confirm"]:
    confirm_trees1000()
