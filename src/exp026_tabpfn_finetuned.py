"""Experiment 026: fine-tuned TabPFN v2 on Task 1 (Charles: tabular foundation models need fine-tuning).

Local CPU, package defaults fixed before running (30 epochs max, lr 1e-5, early stopping on an internal 10% split
of the training fold). Fine-tuning happens inside each CV fold on that fold's training flows only.
  ft_alone    fine-tuned TabPFN on the 34 Task 1 champion columns
  ft_member   022 Task 1 model + fine-tuned TabPFN as a third member (weight 1/3), facebook kept
Confirmation (2027, 2028) only for a variant that passes at 2026.
Usage: python src/exp026_tabpfn_finetuned.py [NAME ...] [--seed N --ref RUN_ID]
"""
import os
import sys
from datetime import datetime, timezone

os.environ.setdefault("TQDM_DISABLE", "1")

from cv import TASK_FEATURES, TASKS, evaluate  # noqa: E402
from models import PlusMember, tabpfn_ft, task1_model  # noqa: E402
from runlog import record_run  # noqa: E402

T1 = TASKS[0]
VARIANTS = {"ft_alone": tabpfn_ft, "ft_member": lambda s: PlusMember(task1_model, tabpfn_ft, seed=s)}


def run(name, cv_seed=2026, reference="champion"):
    t0 = datetime.now(timezone.utc)
    tag = "" if cv_seed == 2026 else f"_s{cv_seed}"
    return record_run("026", name + tag, {T1: evaluate(T1, TASK_FEATURES[T1], VARIANTS[name], cv_seed=cv_seed)},
                      model_factory=VARIANTS[name], reference=reference,
                      question=f"Task 1: {name} (fine-tuned TabPFN v2), cv_seed {cv_seed}?",
                      config={"model": name, "tabpfn": "v2 fine-tuned, package defaults", "cv_seed": cv_seed}, started=t0)


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    names = [a for a in args if a in VARIANTS] or list(VARIANTS)
    for n in names:
        run(n, seed, ref)
