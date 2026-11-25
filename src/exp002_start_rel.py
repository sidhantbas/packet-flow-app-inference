"""Experiment 002: does start_rel help under repeated stratified CV?"""
from functools import partial

import numpy as np

from cv import DEFAULT_DROP, TASKS, basic_features, evaluate, summarize

VARIANTS = {
    "a_without_start_rel": DEFAULT_DROP,
    "b_with_start_rel": [c for c in DEFAULT_DROP if c != "start_rel"],
}

if __name__ == "__main__":
    for task in TASKS:
        res = {name: evaluate(task, features=partial(basic_features, drop=drop)) for name, drop in VARIANTS.items()}
        for name, r in res.items():
            print(f"[{name}] " + summarize(r))
        a, b = res["a_without_start_rel"], res["b_with_start_rel"]
        diff = b["fold_macro"] - a["fold_macro"]  # paired: same folds, same model seeds
        rep_diff = diff.reshape(10, 5).mean(axis=1)
        print(f"[{task}] with - without: mean {diff.mean():+.4f}, fold std of scores ~{a['macro_std']:.4f}, "
              f"paired fold-diff std {diff.std(ddof=1):.4f}, folds where with>without {int((diff > 0).sum())}/{len(diff)}, "
              f"repeat-level diffs {np.round(rep_diff, 4).tolist()} (positive in {int((rep_diff > 0).sum())}/10)")
        for c in a["labels"]:
            print(f"    {c:10s} {b['per_class_mean'][c] - a['per_class_mean'][c]:+.3f}")
        print()
