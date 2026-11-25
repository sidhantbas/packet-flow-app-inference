"""Experiment 014: Facebook-vs-Instagram specialist.

Leads: on task 2, 13 Instagram + 2 Facebook flows share one exact first-5 pattern and balanced weights push it
to Facebook (012: unweighted SoftVote gives instagram +0.075). On task 1, timing is the Facebook signal (010:
shuffling timing costs Facebook 0.40).

Same two-stage design as 013 (`PairSpecialist`, pair = facebook/instagram): the champion (balanced) predicts,
flows it calls facebook or instagram are re-decided by a model trained only on those two classes.
  fi_same_cw       specialist on the champion columns, balanced weights
  fi_same_nocw     specialist on the champion columns, no weights
  fi_extra_cw      specialist + extra families (task 1: reltiming, rates, burst; task 2: direction, sizecv), balanced
  fi_extra_nocw    as fi_extra_cw, no weights
Usage: python src/exp014_fb_ig_specialist.py [confirm NAME ... | followup]
"""
import sys
from datetime import datetime, timezone

from cv import TASK_FEATURES, TASKS, evaluate, load_task
from exp013_gy_specialist import PairSpecialist, features_with
from models import SoftVote
from runlog import record_run

PAIR = ("facebook", "instagram")
EXTRA = {"task1_static": ["reltiming", "rates", "burst"], "task2_realtime_prefix5": ["direction", "sizecv"]}
NAMES = ["fi_same_cw", "fi_same_nocw", "fi_extra_cw", "fi_extra_nocw"]


def variant(task, name):
    base_cols = list(TASK_FEATURES[task](load_task(task)[0].head()).columns)
    cw = None if name.endswith("nocw") else "balanced"
    extra = "extra" in name
    feats = features_with(task, EXTRA[task]) if extra else TASK_FEATURES[task]
    return feats, lambda s: PairSpecialist(base_cols, s, spec_class_weight=cw, spec_all_cols=extra, pair=PAIR)


def run(name, cv_seed=2026, reference="champion", tag=""):
    t0 = datetime.now(timezone.utc)
    res, cfg = {}, {}
    for t in TASKS:
        feats, factory = variant(t, name)
        res[t] = evaluate(t, feats, factory, cv_seed=cv_seed)
        cfg[t] = feats.__name__
    return record_run("014", name + tag, res, model_factory=factory, reference=reference,
                      question=f"Does a facebook/instagram specialist ({name}) beat the champion (cv_seed {cv_seed})?",
                      config={"model": f"PairSpecialist:{name}", "features": cfg, "cv_seed": cv_seed}, started=t0)


def confirm(names):
    for seed in (2027, 2028):
        t0 = datetime.now(timezone.utc)
        ref = record_run("014", f"champion_s{seed}",
                         {t: evaluate(t, TASK_FEATURES[t], lambda s: SoftVote(seed=s), cv_seed=seed) for t in TASKS},
                         reference=None, model_factory=lambda s: SoftVote(seed=s),
                         question=f"Confirmation reference: champions, cv_seed {seed}.",
                         config={"model": "SoftVote", "cv_seed": seed}, started=t0)
        for n in names:
            run(n, cv_seed=seed, reference=ref, tag=f"_s{seed}")


if __name__ == "__main__" and sys.argv[1:2] != ["followup"]:
    if sys.argv[1:2] == ["confirm"]:
        confirm(sys.argv[2:])
    else:
        for n in NAMES:
            run(n)


def rule_v2_followup():
    """Under rule v2, 012's unweighted SoftVote also passes on task 2: confirm it on the same fresh folds as
    014 (reference = the 014 champion_s{seed} runs) so the two fixes can be compared head to head."""
    from runlog import load_index
    T2 = "task2_realtime_prefix5"
    refs = {e["name"]: e["run_id"] for e in load_index() if e["experiment"] == "014"}
    for seed in (2027, 2028):
        t0 = datetime.now(timezone.utc)
        f = lambda s: SoftVote(seed=s, class_weight=None)
        record_run("014", f"cw_none_s{seed}", {T2: evaluate(T2, TASK_FEATURES[T2], f, cv_seed=seed)},
                   reference=refs[f"champion_s{seed}"], model_factory=f,
                   question=f"Rule v2 confirmation of 012 cw_none on task 2, cv_seed {seed}.",
                   config={"model": "SoftVote", "class_weight": None, "cv_seed": seed}, started=t0)


if __name__ == "__main__" and sys.argv[1:2] == ["followup"]:
    rule_v2_followup()
