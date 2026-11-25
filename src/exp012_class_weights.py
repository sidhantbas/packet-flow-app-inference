"""Experiment 012: class weighting in SoftVote (lead from 009: unweighted CatBoost was best on task 2).

  check    SoftVote default ("balanced"): must tie the champion on every fold (models.py refactor check)
  none     no class weights in any member
  sqrt     square root of the balanced weights (between none and balanced)
Each on both tasks with the champion features. Variants that pass are re-tested on cv_seeds 2027 and 2028.
"""
from datetime import datetime, timezone

from cv import TASK_FEATURES, TASKS, evaluate
from models import SoftVote
from runlog import record_run


def factory(cw):
    def f(s):
        return SoftVote(seed=s, class_weight=cw)
    return f


def run(name, cw, tasks=TASKS, cv_seed=2026, reference="champion"):
    t0 = datetime.now(timezone.utc)
    res = {t: evaluate(t, TASK_FEATURES[t], factory(cw), cv_seed=cv_seed) for t in tasks}
    return record_run("012", name, res, model_factory=factory(cw), reference=reference,
                      question=f"SoftVote with class_weight={cw!r} vs champion (cv_seed {cv_seed})?",
                      config={"model": "SoftVote", "class_weight": cw, "cv_seed": cv_seed,
                              "features": {t: TASK_FEATURES[t].__name__ for t in tasks}}, started=t0)


if __name__ == "__main__":
    run("check_balanced", "balanced")
    run("cw_none", None)
    run("cw_sqrt", "sqrt")
