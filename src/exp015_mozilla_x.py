"""Experiment 015: task 2 mozilla -> x errors (33 -> 50 since timing was dropped in 007).

A mozilla-vs-x model trained on those two classes only separates them better WITH timing (AUC 0.976 vs
0.945 without; balanced accuracy 0.914-0.923 vs 0.905-0.912). So: keep the timing-free base model and
the facebook/instagram specialist (champion, 014), and add a mozilla/x specialist that sees timing.
Features given to the model: all 17 basic columns; the base and the fb/ig specialist use only the
12 timing-free champion columns.

  check           MultiSpecialist with only the fb/ig specialist: must tie the task 2 champion
  mx_timing_cw    + mozilla/x specialist on all 17 columns, balanced
  mx_timing_nocw  + mozilla/x specialist on all 17 columns, no weights
  mx_base_cw      + mozilla/x specialist on the 12 champion columns, balanced (control: is it timing or the stage?)
Usage: python src/exp015_mozilla_x.py [confirm NAME ...]
"""
import sys
from datetime import datetime, timezone

from cv import TASK_FEATURES, basic_features, evaluate, load_task
from models import MultiSpecialist, SoftVote, task2_model
from runlog import load_index, record_run

T2 = "task2_realtime_prefix5"
BASE_COLS = list(TASK_FEATURES[T2](load_task(T2)[0].head()).columns)
FI = (("facebook", "instagram"), "base", None)
VARIANTS = {
    "check": (FI,),
    "mx_timing_cw": (FI, (("mozilla", "x"), "all", "balanced")),
    "mx_timing_nocw": (FI, (("mozilla", "x"), "all", None)),
    "mx_base_cw": (FI, (("mozilla", "x"), "base", "balanced")),
}


def factory(specs):
    return lambda s: MultiSpecialist(BASE_COLS, specs, seed=s)


def run(name, cv_seed=2026, reference="champion", tag=""):
    t0 = datetime.now(timezone.utc)
    f = factory(VARIANTS[name])
    res = {T2: evaluate(T2, basic_features, f, cv_seed=cv_seed)}
    return record_run("015", name + tag, res, model_factory=f, feature_fn=basic_features, reference=reference,
                      question=f"Task 2 {name} vs champion (cv_seed {cv_seed})?",
                      config={"model": "MultiSpecialist", "specialists": repr(VARIANTS[name]),
                              "base_cols": BASE_COLS, "cv_seed": cv_seed}, started=t0)


def confirm(names):
    for seed in (2027, 2028):
        t0 = datetime.now(timezone.utc)
        ref = record_run("015", f"champion_s{seed}",
                         {T2: evaluate(T2, TASK_FEATURES[T2], task2_model, cv_seed=seed)}, reference=None,
                         model_factory=task2_model, question=f"Confirmation reference: task 2 champion, cv_seed {seed}.",
                         config={"model": "task2_model", "cv_seed": seed}, started=t0)
        for n in names:
            run(n, cv_seed=seed, reference=ref, tag=f"_s{seed}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["confirm"]:
        confirm(sys.argv[2:])
    else:
        for n in VARIANTS:
            run(n)
