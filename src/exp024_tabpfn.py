"""Experiment 024: TabPFN v2 (local, CPU), a transformer pretrained on synthetic tables, built for small data.

Outside pretrained model -> disclose in the report. Weights: ungated v2 checkpoint, downloaded once to
~/Library/Caches/tabpfn; no data leaves the machine.
  pfn          TabPFN alone on each task's champion features (task 1: 34 columns, task 2: 12 columns)
Usage: python src/exp024_tabpfn.py [NAME ...] [--seed N --ref RUN]
"""
import sys
from datetime import datetime, timezone

from cv import TASK_FEATURES, TASKS, evaluate
from models import tabpfn
from runlog import record_run

if __name__ == "__main__":
    t0 = datetime.now(timezone.utc)
    res = {t: evaluate(t, TASK_FEATURES[t], tabpfn) for t in TASKS}
    record_run("024", "pfn", res, model_factory=tabpfn, question="Does TabPFN v2 alone beat the champions?",
               config={"model": "TabPFN v2 (local CPU, n_estimators auto)", "features": {t: TASK_FEATURES[t].__name__ for t in TASKS}},
               started=t0)
