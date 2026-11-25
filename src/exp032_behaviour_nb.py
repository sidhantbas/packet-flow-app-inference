"""Experiment 032: predicting from "probabilities of behaviour" (each app's packet-level habits).

BehaviourNB: per-feature quantile levels (5, fitted in the training fold) + categorical naive Bayes, equal priors.
Variants (both tasks, settings fixed before running):
  nb_alone   BehaviourNB on the task's champion columns (Task 1: 17 full-flow + 12 opening columns without timing)
  nb_member  champion + BehaviourNB as a member with weight 1/3:
             Task 1 = PlusMember(task1_model, BehaviourNB, w=1/3), facebook calls of the 17-column model kept;
             Task 2 = base (2/3 SoftVote + 1/3 BehaviourNB) under the unchanged facebook/instagram stage.
Confirmation on 2027/2028 only after a pass at 2026.
Usage: python src/exp032_behaviour_nb.py [nb_alone|nb_member ...] [--seed N --ref1 RUN --ref2 RUN]
"""
import sys
from datetime import datetime, timezone

from cv import TASKS, TASK_FEATURES, evaluate
from models import BehaviourNB, MultiSpecialist, PlusMember, ProbaMix, SoftVote, task1_model
from runlog import record_run

T1, T2 = TASKS
FI = (("facebook", "instagram"), "base", None)


def factory(name, task):
    if name == "nb_alone":
        return lambda s: BehaviourNB(seed=s)
    if task == T1:
        return lambda s: PlusMember(task1_model, BehaviourNB, seed=s, w=1 / 3)
    return lambda s: MultiSpecialist(None, (FI,), seed=s, base_factory=lambda sd: ProbaMix(
        (lambda q: SoftVote(seed=q), lambda q: BehaviourNB(seed=q)), (2, 1), seed=sd))


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    refs = {T1: args[args.index("--ref1") + 1] if "--ref1" in args else "champion",
            T2: args[args.index("--ref2") + 1] if "--ref2" in args else "champion"}
    for name in [a for a in args if a in ("nb_alone", "nb_member")] or ["nb_alone", "nb_member"]:
        for task in TASKS:
            f = factory(name, task)
            t0 = datetime.now(timezone.utc)
            record_run("032", f"{'t1' if task == T1 else 't2'}_{name}" + ("" if seed == 2026 else f"_s{seed}"),
                       {task: evaluate(task, TASK_FEATURES[task], f, cv_seed=seed)}, model_factory=f,
                       feature_fn=TASK_FEATURES[task], reference=refs[task],
                       question=f"{task}: {name} (behaviour naive Bayes), cv_seed {seed}?",
                       config={"model": name, "n_bins": 5, "alpha": 1.0, "fit_prior": False, "member_weight": "1/3",
                               "cv_seed": seed}, started=t0)
