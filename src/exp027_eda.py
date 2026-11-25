"""Experiment 027, step 1: field-distribution EDA from Charles's handoff (HANDOFF_sid.md, "Evaluation and constraints" 1).

Training-field EDA per task: field profile, distributions by app, zero/tiny durations, one-direction flows, burst
variation, prefix packet counts, Spearman correlations, algebraic redundancy, and train-vs-validation shifts
(described, never used to pick features). Labels: train/validation only. Test features are not read.
Output: results/<UTC stamp>_027_eda/<task>/*.csv + *.png, summary.md, manifest.json, checksums.json.
"""
import json
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import ks_2samp  # noqa: E402

from cv import TASKS, load_task  # noqa: E402
from runlog import RESULTS, code_hashes, data_hashes, device_profile, git_state, package_versions, sha256_file  # noqa: E402

APPS = ["facebook", "instagram", "mozilla", "x", "youtube", "google"]  # small classes first
GREY, INK, MUTED, GRID = "#8C8C8C", "#1F1F1F", "#6B6B6B", "#E6E6E6"


def numeric(X):
    return X.drop(columns=["flow_id", "split", "transport"]).astype(float)


def profile(X):
    N = numeric(X)
    q = N.quantile([0, 0.25, 0.5, 0.75, 1]).T
    q.columns = ["min", "q25", "median", "q75", "max"]
    out = pd.DataFrame({"distinct": N.nunique(), "zeros": (N == 0).sum(), "missing": N.isna().sum(),
                        "nonfinite": (~np.isfinite(N)).sum(), "skew": N.skew()}).join(q)
    out.loc["transport", ["distinct", "zeros", "missing"]] = [X.transport.nunique(), 0, X.transport.isna().sum()]
    return out.round(4)


def edge_cases(X, y):
    n = X.packet_count_up + X.packet_count_down
    rows = {
        "duration == 0": (X.duration == 0),
        "duration < 0.01 s": (X.duration < 0.01),
        "no upstream packets": (X.packet_count_up == 0),
        "no downstream packets": (X.packet_count_down == 0),
        "min_iat == 0": (X.min_iat == 0),
        "burst_count == 1": (X.burst_count == 1),
        "up/down byte ratio > 10": (X.up_down_byte_ratio > 10),
        "up/down byte ratio < 0.1": (X.up_down_byte_ratio < 0.1),
        "server_port != 443": (X.server_port != 443),
    }
    tab = pd.DataFrame({k: v.groupby(y.values).sum() for k, v in rows.items()}).T.reindex(columns=APPS).fillna(0)
    tab["total"] = tab.sum(axis=1)
    tab.loc["packets per flow (min-max)"] = [f"{n[y == a].min()}-{n[y == a].max()}" for a in APPS] + [f"{n.min()}-{n.max()}"]
    return tab


def redundancy(X):
    n = X.packet_count_up + X.packet_count_down
    checks = {
        "duration = mean_iat * (packets - 1)": X.duration / (X.mean_iat * (n - 1)).replace(0, np.nan),
        "bytes_up = packet_count_up * mean_pkt_size_up": X.bytes_up / (X.packet_count_up * X.mean_pkt_size_up).replace(0, np.nan),
        "bytes_down = packet_count_down * mean_pkt_size_down": X.bytes_down / (X.packet_count_down * X.mean_pkt_size_down).replace(0, np.nan),
        "up_down_byte_ratio = bytes_up / bytes_down": X.up_down_byte_ratio / (X.bytes_up / X.bytes_down.replace(0, np.nan)),
        "up_down_packet_ratio = packet_count_up / packet_count_down": X.up_down_packet_ratio / (X.packet_count_up / X.packet_count_down.replace(0, np.nan)),
    }
    return pd.DataFrame({"share within 1%": {k: float(((v - 1).abs() < 0.01).mean()) for k, v in checks.items()},
                         "undefined": {k: int(v.isna().sum()) for k, v in checks.items()}})


def high_pairs(C, thr=0.9):
    cols = C.columns
    pairs = [(a, b, C.loc[a, b]) for i, a in enumerate(cols) for b in cols[i + 1:] if abs(C.loc[a, b]) >= thr]
    return pd.DataFrame(pairs, columns=["feature_a", "feature_b", "spearman"]).sort_values("spearman", key=abs, ascending=False)


def shifts(Xt, Xv):
    Nt, Nv = numeric(Xt), numeric(Xv)
    rows = []
    for c in Nt.columns:
        ks = ks_2samp(Nt[c], Nv[c])
        rows.append({"feature": c, "ks_stat": round(ks.statistic, 3), "ks_p": round(ks.pvalue, 3),
                     "train_median": Nt[c].median(), "validation_median": Nv[c].median(),
                     "validation_outside_train_range": int(((Nv[c] < Nt[c].min()) | (Nv[c] > Nt[c].max())).sum())})
    rows.append({"feature": "transport (UDP share)", "ks_stat": None, "ks_p": None,
                 "train_median": round((Xt.transport == "udp").mean(), 3),
                 "validation_median": round((Xv.transport == "udp").mean(), 3), "validation_outside_train_range": 0})
    return pd.DataFrame(rows).sort_values("ks_stat", ascending=False, na_position="last")


def boxplots(X, y, task, path):
    N = numeric(X).drop(columns=["server_port", "start_rel"])  # 16 predictors, 16 panels
    cols = list(N.columns)
    fig, axes = plt.subplots(4, 4, figsize=(15, 13), constrained_layout=True)
    for ax, c in zip(axes.flat, cols):
        data = [np.log10(1 + N.loc[(y == a).values, c].values) for a in APPS]
        ax.boxplot(data, vert=False, widths=0.6, patch_artist=True, showfliers=True,
                   boxprops=dict(facecolor="#D9D9D9", edgecolor=GREY, linewidth=1),
                   medianprops=dict(color=INK, linewidth=2), whiskerprops=dict(color=GREY, linewidth=1),
                   capprops=dict(color=GREY, linewidth=1),
                   flierprops=dict(marker="o", markersize=3, markerfacecolor=GREY, markeredgecolor="none", alpha=0.6))
        ax.set_yticks(range(1, len(APPS) + 1), [f"{a} ({(y == a).sum()})" for a in APPS], fontsize=9, color=INK)
        ax.set_title(c, fontsize=10, color=INK, loc="left")
        ax.tick_params(axis="x", labelsize=8, colors=MUTED)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for s in ax.spines.values():
            s.set_visible(False)
    for ax in list(axes.flat)[len(cols):]:
        ax.axis("off")
    fig.suptitle(f"{task}: feature distributions by app, train + validation (x = log10(1 + value); count per app in brackets)",
                 fontsize=13, color=INK, x=0.01, ha="left")
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    stamp = datetime.now(timezone.utc)
    out = RESULTS / f"{stamp:%Y%m%dT%H%M%SZ}_027_eda"
    out.mkdir(parents=True)
    lines = [f"# EDA (experiment 027, step 1), {stamp:%Y-%m-%d}", "",
             "Train + validation labels only; test features not read. Shifts are described, not used for selection.", ""]
    for task in TASKS:
        d = out / task
        d.mkdir()
        X, y = load_task(task)
        Xt, yt = load_task(task, ("train",))
        Xv, _ = load_task(task, ("validation",))
        prof = profile(Xt)
        prof.to_csv(d / "profile_train.csv")
        med = numeric(X).groupby(y.values).median().reindex(APPS).round(3)
        med["udp_share"] = (X.transport == "udp").groupby(y.values).mean().reindex(APPS).round(2)
        med.to_csv(d / "median_by_app.csv")
        edge = edge_cases(X, y)
        edge.to_csv(d / "edge_cases_by_app.csv")
        burst = numeric(X).burst_count.groupby(y.values).describe().reindex(APPS).round(2)
        burst.to_csv(d / "burst_count_by_app.csv")
        C = numeric(Xt).drop(columns=["server_port"]).corr(method="spearman").round(3)
        C.to_csv(d / "spearman_train.csv")
        hp = high_pairs(C)
        hp.to_csv(d / "high_correlation_pairs_train.csv", index=False)
        red = redundancy(X)
        red.to_csv(d / "algebraic_redundancy.csv")
        sh = shifts(Xt, Xv)
        sh.to_csv(d / "train_vs_validation_shift.csv", index=False)
        boxplots(X, y, task, d / "distributions_by_app.png")

        lines += [f"## {task}", "",
                  f"- Constant in train: {[c for c in prof.index if prof.loc[c, 'distinct'] <= 1]}",
                  f"- Columns with zeros (train): " + ", ".join(f"{c} {int(z)}" for c, z in prof["zeros"].items() if z > 0),
                  f"- Most skewed (train): " + ", ".join(f"{c} {s:.1f}" for c, s in prof["skew"].abs().sort_values(ascending=False).head(5).items()),
                  "", "Edge cases (train + validation, flows per app):", "", edge.to_markdown(), "",
                  "Algebraic redundancy:", "", red.to_markdown(), "",
                  f"Spearman |rho| >= 0.9 pairs (train): {len(hp)}", "", hp.head(12).to_markdown(index=False), "",
                  "Largest train vs validation shifts (KS):", "", sh.head(6).to_markdown(index=False), "",
                  "Medians by app (train + validation):", "", med.to_markdown(), ""]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    manifest = {"run_id": out.name, "experiment": "027", "step": "EDA", "created_utc": stamp.isoformat(timespec="seconds"),
                "device": device_profile(), "packages": package_versions(), "git": git_state(), "code_sha256": code_hashes(),
                "data_sha256": {t: data_hashes(t) for t in TASKS}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    sums = {p.relative_to(out).as_posix(): sha256_file(p) for p in sorted(out.rglob("*")) if p.is_file()}
    (out / "checksums.json").write_text(json.dumps(sums, indent=2) + "\n")
    print(f"-> results/{out.name}/")


if __name__ == "__main__":
    main()
