"""Experiment 006: log the RF baseline and the SoftVote submission model with runlog, set champions.

Checks the logging system against experiment 004 (SoftVote vs RF: task 1 +0.038 with 34/50 wins,
task 2 +0.010 with 29/50) and gives every later experiment a champion run to compare against.
"""
from datetime import datetime, timezone

from cv import TASKS, basic_features, evaluate
from models import SoftVote, rf
from runlog import set_champion
from runlog import record_run

CV_DESC = "repeated stratified 5-fold × 10, cv_seed 2026, model seed = fold index"


def run(name, factory, question, reference):
    t0 = datetime.now(timezone.utc)
    res = {t: evaluate(t, basic_features, factory) for t in TASKS}
    return record_run("006", name, res, question=question, model_factory=factory, feature_fn=basic_features,
                      config={"model": name, "cv": CV_DESC}, reference=reference, started=t0)


if __name__ == "__main__":
    rf_run = run("rf_baseline", rf, "Reference: baseline RF (experiment 002).", reference=None)
    sv_run = run("softvote", lambda s: SoftVote(seed=s),
                 "Reference: current submission model; must reproduce 004 vs RF.", reference=rf_run)
    for t in TASKS:
        set_champion(t, sv_run, "current submission model (CLAUDE.md, experiment 005)")
