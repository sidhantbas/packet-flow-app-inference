"""Experiment 010: permutation importance of each task's champion over the 50 default folds (TODO #11).

For each fold: fit the champion on the training part, score the held-out part, then shuffle one feature
(or one group) in the held-out part 5 times and record the macro F1 drop. Compare with Charles's 4-fold
run (data/charles/automl/results/feature-diagnostics-20260929T222807Z/).
Output: results/<stamp>_010_permutation/<task>/{raw.csv,summary.csv}, manifest.json, checksums.json.
"""
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import CV_SEED, TASK_FEATURES, TASKS, load_task
from models import SoftVote
from runlog import RESULTS, code_hashes, data_hashes, device_profile, git_state, package_versions, sha256_file

SHUFFLES = 5
GROUPS = {
    "volume_direction": ["packet_count_up", "packet_count_down", "bytes_up", "bytes_down",
                         "up_down_packet_ratio", "up_down_byte_ratio"],
    "packet_size": ["mean_pkt_size_up", "mean_pkt_size_down", "std_pkt_size_up", "std_pkt_size_down"],
    "timing": ["duration", "mean_iat", "std_iat", "min_iat", "max_iat"],
    "upstream": ["packet_count_up", "bytes_up", "mean_pkt_size_up", "std_pkt_size_up"],
    "downstream": ["packet_count_down", "bytes_down", "mean_pkt_size_down", "std_pkt_size_down"],
}


def one_fold(i, tr, te, X, y, labels):
    model = SoftVote(seed=i).fit(X.iloc[tr], y.iloc[tr])
    Xte, yte = X.iloc[te], y.iloc[te]
    base_pred = model.predict(Xte)
    base = f1_score(yte, base_pred, average="macro")
    base_pc = f1_score(yte, base_pred, average=None, labels=labels, zero_division=0)
    rng = np.random.default_rng(1000 + i)
    targets = [("feature", c, [c]) for c in X.columns]
    targets += [("group", g, [c for c in cols if c in X.columns]) for g, cols in GROUPS.items()]
    rows = []
    for kind, name, cols in targets:
        if not cols:
            continue
        for r in range(SHUFFLES):
            Xp = Xte.copy()
            perm = rng.permutation(len(Xp))
            Xp[cols] = Xp[cols].values[perm]  # shuffle the group jointly
            p = model.predict(Xp)
            pc = f1_score(yte, p, average=None, labels=labels, zero_division=0)
            rows.append({"fold": i, "kind": kind, "target": name, "shuffle": r,
                         "delta_macro": base - f1_score(yte, p, average="macro"),
                         **{f"delta_{c}": b - v for c, b, v in zip(labels, base_pc, pc)}})
    return rows


def main():
    stamp = datetime.now(timezone.utc)
    out = RESULTS / f"{stamp:%Y%m%dT%H%M%SZ}_010_permutation"
    out.mkdir(parents=True)
    tasks_meta = {}
    for task in TASKS:
        X_raw, y = load_task(task)
        X = TASK_FEATURES[task](X_raw)
        labels = sorted(y.unique())
        cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=CV_SEED)
        rows = Parallel(n_jobs=-1)(delayed(one_fold)(i, tr, te, X, y, labels)
                                   for i, (tr, te) in enumerate(cv.split(X, y)))
        raw = pd.DataFrame([r for fold in rows for r in fold])
        (out / task).mkdir()
        raw.to_csv(out / task / "raw.csv", index=False)
        per_fold = raw.groupby(["kind", "target", "fold"]).mean(numeric_only=True).drop(columns="shuffle")
        summ = per_fold.groupby(["kind", "target"]).agg(
            mean_drop=("delta_macro", "mean"), fold_std=("delta_macro", "std"),
            folds_positive=("delta_macro", lambda s: int((s > 0).sum())),
            **{f"drop_{c}": (f"delta_{c}", "mean") for c in labels})
        summ = summ.sort_values("mean_drop", ascending=False)
        summ.to_csv(out / task / "summary.csv")
        tasks_meta[task] = {"features": list(X.columns), "data_sha256": data_hashes(task)}
        print(f"\n=== {task} (champion features, SoftVote, 50 folds × {SHUFFLES} shuffles)")
        print(summ.round(4).to_string())
    manifest = {"run_id": out.name, "experiment": "010", "started_utc": stamp.isoformat(timespec="seconds"),
                "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "shuffles": SHUFFLES, "groups": GROUPS, "cv_seed": CV_SEED, "device": device_profile(),
                "packages": package_versions(), "git": git_state(), "code_sha256": code_hashes(), "tasks": tasks_meta}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    sums = {p.relative_to(out).as_posix(): sha256_file(p) for p in sorted(out.rglob("*")) if p.is_file()}
    (out / "checksums.json").write_text(json.dumps(sums, indent=2) + "\n")
    print(f"→ results/{out.name}/")


if __name__ == "__main__":
    main()
