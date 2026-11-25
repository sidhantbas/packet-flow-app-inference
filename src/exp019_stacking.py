"""Experiment 019: stacking instead of plain averaging.

A multinomial logistic regression (balanced, C = 1) learns how to combine the members' predicted
probabilities; the probabilities it trains on come from an inner 5-fold CV on the training fold only
(sklearn StackingClassifier). Task 2 keeps the fb/ig specialist on top (MultiSpecialist(base_factory=...)).
  stack3   rf, et, lgbm
  stack5   rf, et, lgbm, logreg, knn
Usage: python src/exp019_stacking.py [confirm NAME ...]
"""
import sys
from datetime import datetime, timezone

from sklearn.ensemble import StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

from cv import TASK_FEATURES, TASKS, evaluate
from models import MultiSpecialist, et, knn, lgbm, logreg, rf, task1_model, task2_model
from runlog import record_run

T1, T2 = TASKS
MEMBERS = {"stack3": (rf, et, lgbm), "stack5": (rf, et, lgbm, logreg, knn)}
FI = (("facebook", "instagram"), "base", None)


def stack(members, seed):
    return StackingClassifier(
        estimators=[(f"m{i}", f(seed)) for i, f in enumerate(members)],
        final_estimator=LogisticRegression(C=1.0, class_weight="balanced", max_iter=5000),
        cv=StratifiedKFold(5, shuffle=True, random_state=seed), stack_method="predict_proba", n_jobs=1)


def factories(name):
    m = MEMBERS[name]
    return {T1: lambda s: stack(m, s),
            T2: lambda s: MultiSpecialist(None, (FI,), seed=s, base_factory=lambda sd: stack(m, sd))}


def run(name, cv_seed=2026, reference="champion", tag=""):
    fs = factories(name)
    t0 = datetime.now(timezone.utc)
    res = {t: evaluate(t, TASK_FEATURES[t], fs[t], cv_seed=cv_seed) for t in TASKS}
    return record_run("019", name + tag, res, model_factory=fs[T1], reference=reference,
                      question=f"Stacking {name} vs champions (cv_seed {cv_seed})?",
                      config={"model": f"StackingClassifier:{name}", "members": [f.__name__ for f in MEMBERS[name]],
                              "final": "LogisticRegression(C=1, balanced)", "cv_seed": cv_seed}, started=t0)


def confirm(names):
    for seed in (2027, 2028):
        t0 = datetime.now(timezone.utc)
        ref = record_run("019", f"champion_s{seed}",
                         {T1: evaluate(T1, TASK_FEATURES[T1], task1_model, cv_seed=seed),
                          T2: evaluate(T2, TASK_FEATURES[T2], task2_model, cv_seed=seed)}, reference=None,
                         model_factory=task1_model, question=f"Confirmation reference: champions, cv_seed {seed}.",
                         config={"model": "TASK_MODELS", "cv_seed": seed}, started=t0)
        for n in names:
            run(n, seed, ref, f"_s{seed}")


if __name__ == "__main__":
    confirm(sys.argv[2:]) if sys.argv[1:2] == ["confirm"] else [run(n) for n in MEMBERS]
