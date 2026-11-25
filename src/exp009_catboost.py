"""Experiment 009: CatBoost (TODO #9, #10), on each task's champion features, vs the champion.

  cb           CatBoost alone, balanced class weights
  cb_plain     CatBoost alone, no class weights (closest to Charles's PyCaret setup)
  cb_cat       CatBoost alone, balanced, `transport` as a native categorical feature (#10)
  softvote4    RF + ExtraTrees + LightGBM + CatBoost, unweighted mean proba
"""
from datetime import datetime, timezone

from cv import TASK_FEATURES, TASKS, evaluate
from models import SoftVote4, catboost
from runlog import record_run

VARIANTS = {
    "cb": lambda s: catboost(s),
    "cb_plain": lambda s: catboost(s, balanced=False),
    "cb_cat": lambda s: catboost(s, cat_transport=True),
    "softvote4": lambda s: SoftVote4(seed=s),
}

if __name__ == "__main__":
    for name, factory in VARIANTS.items():
        t0 = datetime.now(timezone.utc)
        res = {t: evaluate(t, TASK_FEATURES[t], factory) for t in TASKS}
        record_run("009", name, res, question=f"Does {name} beat the champion?", model_factory=factory,
                   config={"model": name, "features": {t: TASK_FEATURES[t].__name__ for t in TASKS}}, started=t0)
