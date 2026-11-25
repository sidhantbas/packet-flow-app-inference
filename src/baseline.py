"""Reproduce the official baseline: RandomForest per task, scored on the validation split."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, f1_score

DATA = Path(__file__).resolve().parent.parent / "data" / "official" / "dataset"
TASKS = ["task1_static", "task2_realtime_prefix5"]
DROP = ["flow_id", "split", "server_port", "start_rel"]
SEEDS = [0, 1, 2, 3, 4]


def load(task, split):
    X = pd.read_csv(DATA / task / f"{split}_features.csv")
    y = pd.read_csv(DATA / task / f"{split}_labels.csv")
    assert (X.flow_id.values == y.flow_id.values).all()
    X = X.drop(columns=DROP)
    X["transport"] = (X["transport"] == "udp").astype(int)
    return X, y["app"]


def run_task(task):
    X_tr, y_tr = load(task, "train")
    X_va, y_va = load(task, "validation")
    labels = sorted(y_tr.unique())
    scores, per_class = [], []
    for seed in SEEDS:
        model = RandomForestClassifier(n_estimators=500, class_weight="balanced", random_state=seed, n_jobs=-1)
        pred = model.fit(X_tr, y_tr).predict(X_va)
        scores.append(f1_score(y_va, pred, average="macro"))
        per_class.append(f1_score(y_va, pred, average=None, labels=labels))
        if seed == SEEDS[0]:
            report = classification_report(y_va, pred, labels=labels, digits=3, zero_division=0)

    print(f"=== {task} ===")
    print(f"validation macro F1 over {len(SEEDS)} seeds: {np.mean(scores):.4f} ± {np.std(scores):.4f}  {np.round(scores, 4).tolist()}")
    print("mean per-class F1:", dict(zip(labels, np.round(np.mean(per_class, axis=0), 3))))
    print(f"classification report (seed {SEEDS[0]}):\n{report}")
    return np.mean(scores)


if __name__ == "__main__":
    means = {task: run_task(task) for task in TASKS}
    print("Estimated score (50 × macro F1 per task):", {t: round(50 * m, 2) for t, m in means.items()}, "total", round(50 * sum(means.values()), 2))
