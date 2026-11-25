"""Upper bound on train+validation macro F1 when identical feature vectors must share one prediction.

Pure groups always get their own label (any other choice only adds errors). Each mixed group
chooses one of its labels; the best assignment is found by exhaustive search over mixed groups.
"""
import itertools

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from cv import TASKS, basic_features, load_task

TIMING = ["duration", "mean_iat", "std_iat", "min_iat", "max_iat"]


def size_count_features(X_raw):
    """Model columns minus the continuous timing columns: transport, counts, bytes, sizes, bursts, ratios."""
    return basic_features(X_raw).drop(columns=TIMING)


def identical_groups(task, features=basic_features):
    X_raw, y = load_task(task)
    X = features(X_raw)
    key = pd.util.hash_pandas_object(X.round(9), index=False)
    groups = pd.DataFrame({"flow_id": X_raw.flow_id, "key": key.values, "app": y.values})
    return groups, list(X.columns)


def ceiling(task, features=basic_features, max_mixed=20):
    groups, cols = identical_groups(task, features)
    labels = sorted(groups.app.unique())
    counts = groups.groupby("key").app.value_counts().unstack(fill_value=0)
    mixed = counts[(counts > 0).sum(axis=1) > 1]
    assert len(mixed) <= max_mixed, f"{len(mixed)} mixed groups: too many for exhaustive search"
    y_true = groups.app.values
    base_pred = groups.key.map(counts.idxmax(axis=1)).values  # pure groups: own label
    options = [list(row[row > 0].index) for _, row in mixed.iterrows()]

    best = {"macro": (-1, None), **{c: (-1, None) for c in labels}}
    for choice in itertools.product(*options):
        pred = base_pred.copy()
        for key, lab in zip(mixed.index, choice):
            pred[groups.key.values == key] = lab
        pc = f1_score(y_true, pred, labels=labels, average=None, zero_division=0)
        cand = {"macro": pc.mean(), **dict(zip(labels, pc))}
        for k, v in cand.items():
            if v > best[k][0]:
                best[k] = (v, pc)
    return {
        "task": task, "n_features": len(cols), "n_flows": len(groups), "n_groups": len(counts),
        "n_dup_groups": int((counts.sum(axis=1) > 1).sum()),
        "mixed": mixed.loc[:, (mixed > 0).any()], "labels": labels,
        "mixed_flow_ids": {k: groups.flow_id[groups.key == k].tolist() for k in mixed.index},
        "macro_ceiling": best["macro"][0],
        "per_class_at_macro_ceiling": dict(zip(labels, best["macro"][1])),
        "per_class_best_alone": {c: best[c][0] for c in labels},
    }


if __name__ == "__main__":
    for (mode, feats), task in itertools.product([("all 17 model columns", basic_features),
                                                  ("size/count columns only, no timing", size_count_features)], TASKS):
        r = ceiling(task, feats)
        print(f"=== [{mode}] {task}: {r['n_features']} columns, {r['n_flows']} flows, {r['n_groups']} distinct vectors, "
              f"{r['n_dup_groups']} duplicate groups, {len(r['mixed'])} mixed")
        print(r["mixed"].reset_index(drop=True).to_string() if len(r["mixed"]) else "no mixed groups")
        print(f"macro F1 ceiling {r['macro_ceiling']:.4f}")
        print("per-class F1 at that ceiling:", {k: round(v, 3) for k, v in r["per_class_at_macro_ceiling"].items()})
        print("per-class F1 best achievable alone:", {k: round(v, 3) for k, v in r["per_class_best_alone"].items()})
