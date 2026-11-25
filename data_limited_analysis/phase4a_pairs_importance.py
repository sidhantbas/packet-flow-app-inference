"""Phase 4a: confusable pairs and permutation importance on the overlap region vs globally (PROTOCOL.md)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402

from common import FIG, HERE, PROD, TASKS, data, save, splits  # noqa: E402

PERM_SEEDS = [0, 1, 2]


def mutual_pairs(X, y):
    L = np.log1p(X.astype(float).clip(lower=0))
    Z = ((L - L.mean()) / L.std().replace(0, 1)).values
    D = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(D, np.inf)
    nn = D.argmin(axis=1)
    pairs = [(i, j) for i, j in enumerate(nn) if nn[j] == i and i < j and y[i] != y[j]]
    diffs = np.array([np.abs(Z[i] - Z[j]) for i, j in pairs]) if pairs else np.zeros((0, Z.shape[1]))
    return pairs, D, diffs


def perm_fold(task, X, y, inside, i, tr, te):
    m = PROD[task](i).fit(X.iloc[tr], y[tr])
    Xte = X.iloc[te]
    ov = inside[te]
    base = m.predict(Xte) == y[te]
    out = {}
    for c in X.columns:
        d_ov, d_all = [], []
        for s in PERM_SEEDS:
            Xp = Xte.copy()
            Xp[c] = np.random.default_rng(s * 1000 + i).permutation(Xp[c].values)
            ok = m.predict(Xp) == y[te]
            d_all.append(base.mean() - ok.mean())
            if ov.any():
                d_ov.append(base[ov].mean() - ok[ov].mean())
        out[c] = (float(np.mean(d_ov)) if d_ov else np.nan, float(np.mean(d_all)))
    return out


def main():
    res = {"perm_seeds": PERM_SEEDS, "tasks": {}}
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, task in zip(axes, TASKS):
        Xr, X, y = data(task)
        reg = pd.read_csv(HERE / f"phase3_region_{task}.csv")
        assert (reg.flow_id.values == Xr.flow_id.values).all()
        inside = reg.in_region.values.astype(bool)
        pairs, D, diffs = mutual_pairs(X, y)
        cols = list(X.columns)
        md = diffs.mean(axis=0) if len(diffs) else np.zeros(len(cols))
        pr = {"mutual_nn_pairs_with_different_labels": len(pairs),
              "exact_duplicates": int(sum(D[i, j] == 0 for i, j in pairs)),
              "by_class_pair": dict(pd.Series(["/".join(sorted((y[i], y[j]))) for i, j in pairs]).value_counts()),
              "same_transport_share": round(float(np.mean([X.transport.iloc[i] == X.transport.iloc[j] for i, j in pairs])), 3) if pairs else None,
              "median_pair_distance": float(np.median([D[i, j] for i, j in pairs])) if pairs else None,
              "median_any_nn_distance": float(np.median(D.min(axis=1))),
              "columns_most_similar_in_pairs": [cols[k] for k in np.argsort(md)[:6]],
              "columns_most_different_in_pairs": [cols[k] for k in np.argsort(-md)[:6]],
              "pairs": [{"a": Xr.flow_id.iloc[i], "label_a": y[i], "b": Xr.flow_id.iloc[j], "label_b": y[j],
                         "distance": round(float(D[i, j]), 4)} for i, j in pairs]}
        jobs = [(task, X, y, inside, i, tr, te) for i, (tr, te) in enumerate(splits(task))]
        R = Parallel(n_jobs=-1)(delayed(perm_fold)(*j) for j in jobs)
        imp = pd.DataFrame({c: {"overlap": np.nanmean([r[c][0] for r in R]), "global": np.mean([r[c][1] for r in R])} for c in cols}).T
        imp = imp.sort_values("overlap", ascending=False)
        res["tasks"][task] = {"confusable_pairs": pr, "permutation_importance": imp.round(5).to_dict(orient="index"),
                              "top_overlap": list(imp.index[:8]), "top_global": list(imp.sort_values("global", ascending=False).index[:8])}
        imp.head(12)[::-1].plot.barh(ax=ax)
        ax.set_title(f"{task}: permutation importance (accuracy drop)")
        ax.set_xlabel("mean drop over 25 folds x 3 permutations")
        print(task, {k: v for k, v in pr.items() if k != "pairs"}, "\n top overlap:", res["tasks"][task]["top_overlap"],
              "\n top global:", res["tasks"][task]["top_global"], flush=True)
    fig.tight_layout(); fig.savefig(FIG / "phase4_permutation_importance.png", dpi=130)
    save("phase4a_pairs_importance.json", res)


if __name__ == "__main__":
    main()
