"""Experiment 033: hybrid of the production pipelines with the behaviour model (032) as a gated, tempered Bayesian
correction, p_final ∝ p_model * p_behaviour**lam on rows whose model margin < tau.

(lam, tau) are chosen inside every outer training fold by a 3-fold inner CV (official macro F1) from
lam ∈ {0, 0.25, 0.5, 1} x tau ∈ {0.1, 0.2, 0.3}; lam = 0 means "no change" and is always available. The chosen setting
is applied once to the outer held-out fold. Facebook override (Task 1) and facebook/instagram stage (Task 2) unchanged.
Compared with the champions under rule v2; confirmation on 2027/2028 only after a pass. Grid and design fixed before running.
Usage: python src/exp033_behaviour_hybrid.py [--seed N --ref1 RUN --ref2 RUN]
"""
import sys
from collections import Counter
from datetime import datetime, timezone

from joblib import Parallel, delayed
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASKS, TASK_FEATURES, evaluate, load_task
from models import BehaviourHybrid
from runlog import record_run


def chosen_settings(task, cv_seed):
    """Re-fit the selection step on each outer training fold to report which (lam, tau) it picks (diagnostic)."""
    X_raw, y = load_task(task)
    X = TASK_FEATURES[task](X_raw)
    splits = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=cv_seed).split(X, y)
    def one(i, tr):
        m = BehaviourHybrid(task=task, seed=i).fit(X.iloc[tr], y.iloc[tr])
        return (m.lam_, m.tau_)
    return Counter(Parallel(n_jobs=-1)(delayed(one)(i, tr) for i, (tr, _) in enumerate(splits)))


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    refs = {TASKS[0]: args[args.index("--ref1") + 1] if "--ref1" in args else "champion",
            TASKS[1]: args[args.index("--ref2") + 1] if "--ref2" in args else "champion"}
    for task in TASKS:
        f = lambda s, t=task: BehaviourHybrid(task=t, seed=s)
        t0 = datetime.now(timezone.utc)
        settings = chosen_settings(task, seed)
        record_run("033", f"{'t1' if task == TASKS[0] else 't2'}_hybrid" + ("" if seed == 2026 else f"_s{seed}"),
                   {task: evaluate(task, TASK_FEATURES[task], f, cv_seed=seed)}, model_factory=f,
                   feature_fn=TASK_FEATURES[task], reference=refs[task],
                   question=f"{task}: gated behaviour hybrid (nested lam/tau), cv_seed {seed}?",
                   notes=f"Chosen (lam, tau) over the 50 outer training folds: {dict(settings)}",
                   config={"model": "BehaviourHybrid", "lams": [0, 0.25, 0.5, 1], "taus": [0.1, 0.2, 0.3],
                           "inner_folds": 3, "cv_seed": seed}, started=t0)
        print(f"{task}: chosen (lam, tau) counts {dict(settings)}")
