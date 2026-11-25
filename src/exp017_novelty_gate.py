"""Experiment 017: novelty gating on task 2 (016: memorising is right for seen vectors; logistic regression +
kNN lower the error on unseen ones).

Task 1 is skipped: no two task 1 flows share an exact vector (004), so every flow is "unseen" and the gate
reduces to the 016 variants.
Base = NoveltyGate under the champion's facebook/instagram specialist (MultiSpecialist(base_factory=...)).
  check          NoveltyGate(smooth=()): trees for every flow; must tie the task 2 champion
  gate_lr_knn    unseen flows: trees + logistic regression + kNN
  gate_lr        unseen flows: trees + logistic regression
  gate_knn       unseen flows: trees + kNN
Usage: python src/exp017_novelty_gate.py [confirm NAME ...]
"""
import sys
from datetime import datetime, timezone

from cv import TASK_FEATURES, TASKS, evaluate
from exp016_smooth_models import seen_split
from models import MultiSpecialist, NoveltyGate, knn, logreg, task2_model
from runlog import record_run

T2 = TASKS[1]
FI = (("facebook", "instagram"), "base", None)
SMOOTH = {"check": (), "gate_lr_knn": (logreg, knn), "gate_lr": (logreg,), "gate_knn": (knn,)}


def factory(smooth):
    return lambda s: MultiSpecialist(None, (FI,), seed=s, base_factory=lambda sd: NoveltyGate(smooth=smooth, seed=sd))


def run(name, cv_seed=2026, reference="champion", tag=""):
    t0 = datetime.now(timezone.utc)
    f = factory(SMOOTH[name])
    rid = record_run("017", name + tag, {T2: evaluate(T2, TASK_FEATURES[T2], f, cv_seed=cv_seed)}, model_factory=f,
                     reference=reference, question=f"Task 2 novelty gate {name} vs champion (cv_seed {cv_seed})?",
                     config={"model": "MultiSpecialist(NoveltyGate)", "smooth": [m.__name__ for m in SMOOTH[name]],
                             "cv_seed": cv_seed}, started=t0)
    e = seen_split(rid, cv_seed)
    print(f"SEEN-SPLIT {name}{tag}: task 2 error seen {e.get(True, float('nan')):.3f}, unseen {e.get(False, float('nan')):.3f}")
    return rid


def confirm(names):
    for seed in (2027, 2028):
        t0 = datetime.now(timezone.utc)
        ref = record_run("017", f"champion_s{seed}", {T2: evaluate(T2, TASK_FEATURES[T2], task2_model, cv_seed=seed)},
                         reference=None, model_factory=task2_model,
                         question=f"Confirmation reference: task 2 champion, cv_seed {seed}.",
                         config={"model": "task2_model", "cv_seed": seed}, started=t0)
        for n in names:
            run(n, cv_seed=seed, reference=ref, tag=f"_s{seed}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["confirm"]:
        confirm(sys.argv[2:])
    else:
        for n in SMOOTH:
            run(n)
