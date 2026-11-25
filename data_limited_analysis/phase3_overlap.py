"""Phase 3: overlap-region profile (PROTOCOL.md). Uses the Phase 2 OOF probabilities."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import FIG, HERE, LABS, T1, T2, TASKS, data, save  # noqa: E402

MARGIN = 0.25


def region(task):
    Xr, X, y = data(task)
    P = np.load(HERE / f"oof_proba_{task}.npy")
    srt = np.sort(P, axis=1)
    margin = srt[:, -1] - srt[:, -2]
    top = np.array(LABS)[np.argsort(-P, axis=1)[:, :2]]
    inside = (margin < MARGIN) | np.isin(y, ("facebook", "instagram"))
    return Xr, X, y, P, margin, top, inside


def main():
    out = {"margin_threshold": MARGIN, "tasks": {}}
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for ax, task in zip(axes, TASKS):
        Xr, X, y, P, margin, top, inside = region(task)
        shape = (Xr.transport + " " + Xr.packet_count_up.astype(int).astype(str) + "/" + Xr.packet_count_down.astype(int).astype(str)) \
            if task == T2 else None
        L = np.log1p(X.astype(float).clip(lower=0))
        smd = ((L[inside].mean() - L[~inside].mean()) / L.std().replace(0, 1)).sort_values(key=abs, ascending=False)
        near = margin < MARGIN
        pairs = pd.Series(["/".join(sorted(t)) for t in top[near]]).value_counts()
        prof = {"flows_in_region": int(inside.sum()), "low_margin": int(near.sum()),
                "by_class_in_region": dict(pd.Series(y[inside]).value_counts()),
                "share_of_class_in_region": {c: round(float(inside[y == c].mean()), 3) for c in LABS},
                "low_margin_top2_pairs": dict(pairs.head(8)),
                "transport_udp_share": {"inside": round(float(X.transport[inside].mean()), 3), "outside": round(float(X.transport[~inside].mean()), 3)},
                "top_smd_features_log1p": {k: round(float(v), 3) for k, v in smd.head(8).items()},
                "median_inside_vs_outside": {k: [float(X[k][inside].median()), float(X[k][~inside].median())] for k in smd.head(5).index}}
        if shape is not None:
            prof["opening_shape_in_region"] = dict(shape[inside].value_counts().head(6))
        out["tasks"][task] = prof
        frame = pd.DataFrame({"inside": pd.Series(y[inside]).value_counts(), "all": pd.Series(y).value_counts()}).fillna(0).loc[LABS]
        frame.plot.bar(ax=ax)
        ax.set_title(f"{task}: overlap region ({int(inside.sum())} of {len(y)} flows)")
        ax.set_ylabel("flows")
        pd.DataFrame({"flow_id": Xr.flow_id.values, "label": y, "margin": margin.round(4), "top1": top[:, 0], "top2": top[:, 1],
                      "in_region": inside}).to_csv(HERE / f"phase3_region_{task}.csv", index=False)
        print(task, prof, flush=True)
    fig.tight_layout(); fig.savefig(FIG / "phase3_overlap_region.png", dpi=130)
    save("phase3_overlap.json", out)


if __name__ == "__main__":
    main()
