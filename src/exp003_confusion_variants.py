"""Experiment 003: confusion diagnosis (Part A) and paired comparison of small variants (Part B)."""
from functools import partial

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import confusion_matrix, roc_auc_score

from cv import TASKS, basic_features, evaluate, load_task, rf_factory

pd.set_option("display.width", 200)
MINORITY = ["facebook", "instagram"]
LOG_COLS = ["packet_count_up", "packet_count_down", "bytes_up", "bytes_down", "mean_pkt_size_up",
            "mean_pkt_size_down", "std_pkt_size_up", "std_pkt_size_down", "burst_count"]


def log_features(X_raw):
    X = basic_features(X_raw)
    for d in ["up", "down"]:
        X[f"bytes_per_packet_{d}"] = (X[f"bytes_{d}"] / X[f"packet_count_{d}"].replace(0, np.nan)).fillna(0)
    for c in LOG_COLS + ["bytes_per_packet_up", "bytes_per_packet_down"]:
        X[c] = np.log1p(X[c])
    return X


def oversample_minority(X_tr, y_tr, seed):
    """Randomly duplicate facebook/instagram rows in the TRAINING fold up to the mozilla count of that fold."""
    rng = np.random.default_rng(seed)
    target = (y_tr == "mozilla").sum()
    extra = []
    for c in MINORITY:
        idx = np.flatnonzero(y_tr.values == c)
        if len(idx) < target:
            extra.append(rng.choice(idx, target - len(idx), replace=True))
    extra = np.concatenate(extra)
    return pd.concat([X_tr, X_tr.iloc[extra]]), pd.concat([y_tr, y_tr.iloc[extra]])


VARIANTS = {
    "a_rf_balanced": dict(),
    "b_rf_balanced_subsample": dict(model_factory=lambda s: RandomForestClassifier(
        n_estimators=500, class_weight="balanced_subsample", random_state=s, n_jobs=-1)),
    "c_log1p_bpp": dict(features=log_features),
    "d_extratrees": dict(model_factory=lambda s: ExtraTreesClassifier(
        n_estimators=500, class_weight="balanced", random_state=s, n_jobs=-1)),
    "e_lightgbm": dict(model_factory=lambda s: LGBMClassifier(
        n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=5,
        class_weight="balanced", random_state=s, n_jobs=-1, verbose=-1)),
    "f_rf_oversample": dict(resample=oversample_minority),
}


def confusion_report(res):
    labels = res["labels"]
    cm = pd.DataFrame(confusion_matrix(res["y_true"], res["y_pred"], labels=labels),
                      index=[f"true_{l}" for l in labels], columns=[f"pred_{l}" for l in labels])
    print(f"Aggregated confusion matrix over 50 folds ({len(res['y_true'])} predictions, each flow 10x):")
    print(cm.to_string())
    for c in MINORITY:
        i = labels.index(c)
        row, col = cm.iloc[i].drop(cm.columns[i]), cm.iloc[:, i].drop(cm.index[i])
        print(f"  {c}: recall {cm.iloc[i, i] / cm.iloc[i].sum():.2f}, precision {cm.iloc[i, i] / cm.iloc[:, i].sum():.2f}")
        print(f"    true {c} predicted as: {row[row > 0].sort_values(ascending=False).to_dict()}")
        print(f"    predicted {c} but really: {col[col > 0].sort_values(ascending=False).to_dict()}")


def separation_report(task, pair=MINORITY):
    """Compare two classes feature by feature on train+validation. AUC is P(feature of pair[0] > pair[1])."""
    X_raw, y = load_task(task)
    X = basic_features(X_raw)
    a, b = X[y == pair[0]], X[y == pair[1]]
    mask = y.isin(pair)
    q = lambda s: f"{s.median():.4g} [{s.quantile(.25):.4g}–{s.quantile(.75):.4g}]"
    rows = []
    for c in X.columns:
        auc = roc_auc_score((y[mask] == pair[0]).astype(int), X.loc[mask, c])
        rows.append((c, q(a[c]), q(b[c]), auc, abs(auc - 0.5) * 2))
    df = pd.DataFrame(rows, columns=["feature", f"{pair[0]} median [IQR]", f"{pair[1]} median [IQR]",
                                     f"AUC({pair[0]}>{pair[1]})", "separation"])
    print(f"{pair[0]} (n={len(a)}) vs {pair[1]} (n={len(b)}), sorted by separation = |2*AUC-1|:")
    print(df.sort_values("separation", ascending=False).round(3).to_string(index=False))
    return df


if __name__ == "__main__":
    for task in TASKS:
        print(f"\n################ {task}")
        res = {name: evaluate(task, **kw) for name, kw in VARIANTS.items()}
        base = res["a_rf_balanced"]
        print("\n--- Part A")
        confusion_report(base)
        separation_report(task)
        print("\n--- Part B")
        fb, ig = base["labels"].index("facebook"), base["labels"].index("instagram")
        for name, r in res.items():
            diff = r["fold_macro"] - base["fold_macro"]
            wins, losses = int((diff > 0).sum()), int((diff < 0).sum())
            better = diff.mean() > 0 and wins >= 35
            print(f"{name:26s} macro {r['macro_mean']:.4f} ± {r['macro_std']:.4f} | Δ {diff.mean():+.4f} (paired std {diff.std(ddof=1):.4f}) "
                  f"| wins {wins} ties {50 - wins - losses} losses {losses} | fb {r['fold_per_class'][:, fb].mean():.3f} "
                  f"ig {r['fold_per_class'][:, ig].mean():.3f} | per-class {np.round(r['fold_per_class'].mean(0), 3).tolist()} "
                  f"| {'BETTER' if better and name != 'a_rf_balanced' else '-'}")
