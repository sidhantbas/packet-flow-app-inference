"""Experiment 036: twin-aware CV and scoped H1 (Task 1).

Command: .venv/bin/python src/exp036_twin_aware.py
Twin groups: connected components of labelled flows whose 17 whole-flow features (log1p, standardised over the 330 labelled
flows) lie within 0.05 of each other (threshold from part 1: all 59 labelled pairs within 0.05 share their label; test flows sit
within 0.05 of a labelled flow 18.5% of the time vs 11.8% in normal CV). Twin-aware folds: StratifiedGroupKFold(5, shuffle)
repeated 10 times (random_state = seed + repeat), for seeds 2026, 2027, 2028; every group stays in one fold.
Models: 022 (task1_model), 028 (task1_two_clerks), 034 (task1_meta_gate, production), scoped H1 on top of 034.
Normal-CV runs for 022/028/034 already exist (006/022/023/028/034); scoped H1 is also run on normal folds (seed 2026).
"""
from datetime import datetime, timezone

import numpy as np
from scipy.sparse.csgraph import connected_components
from sklearn.model_selection import StratifiedGroupKFold

from cv import TASK_FEATURES, basic_features, evaluate, load_task
from models import T1_COLS, ScopedH1, task1_meta_gate, task1_model, task1_two_clerks
from runlog import record_run

T1 = "task1_static"
THRESHOLD = 0.05


def twin_groups():
    X_raw, y = load_task(T1)
    B = np.log1p(basic_features(X_raw)[list(T1_COLS)].astype(float).clip(lower=0)).values
    Z = (B - B.mean(0)) / np.where(B.std(0) > 0, B.std(0), 1)
    D = np.sqrt(((Z[:, None] - Z[None]) ** 2).sum(-1))
    n, labels = connected_components(D <= THRESHOLD, directed=False)
    return labels, y


def twin_splits(seed, n_repeats=10):
    groups, y = twin_groups()
    out = []
    for r in range(n_repeats):
        sgk = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed + r)
        out += list(sgk.split(np.zeros(len(y)), y, groups))
    return out


MODELS = {"m022": task1_model, "m028": task1_two_clerks, "m034": task1_meta_gate,
          "scoped_h1": lambda s: ScopedH1(task1_meta_gate, seed=s)}


def run(name, splits, split_name, reference, tag):
    t0 = datetime.now(timezone.utc)
    f = MODELS[name]
    return record_run("036", f"{name}_{tag}", {T1: evaluate(T1, TASK_FEATURES[T1], f, splits=splits, split_name=split_name)},
                      model_factory=f, feature_fn=TASK_FEATURES[T1], reference=reference,
                      question=f"Task 1 {name} under {split_name}",
                      config={"model": name, "splits": split_name, "twin_threshold": THRESHOLD}, started=t0)


if __name__ == "__main__":
    groups, y = twin_groups()
    sizes = np.bincount(groups)
    print(f"twin groups: {len(sizes)} groups for 330 flows; {int((sizes > 1).sum())} groups with >1 flow covering {int(sizes[sizes > 1].sum())} flows; largest {sizes.max()}")
    for seed in (2026, 2027, 2028):
        sp = twin_splits(seed)
        sn = f"twin-aware StratifiedGroupKFold(5) x 10, seed {seed}, threshold {THRESHOLD}"
        r022 = run("m022", sp, sn, None, f"twin_s{seed}")
        r028 = run("m028", sp, sn, r022, f"twin_s{seed}")
        r034 = run("m034", sp, sn, r028, f"twin_s{seed}")
        run("scoped_h1", sp, sn, r034, f"twin_s{seed}")
    # scoped H1 on the normal folds (seed 2026) vs the production champion
    t0 = datetime.now(timezone.utc)
    f = MODELS["scoped_h1"]
    record_run("036", "scoped_h1_normal_s2026", {T1: evaluate(T1, TASK_FEATURES[T1], f)}, model_factory=f,
               feature_fn=TASK_FEATURES[T1], reference="champion", question="Task 1 scoped H1 under normal CV (seed 2026)",
               config={"model": "scoped_h1", "splits": "RepeatedStratifiedKFold seed 2026"}, started=t0)
