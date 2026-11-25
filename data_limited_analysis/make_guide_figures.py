"""Figures for decision-making-guide.md, drawn from logged results only (no new model runs)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIG = HERE / "figures"
C = {"facebook": "#c026d3", "google": "#0284c7", "instagram": "#ea580c", "mozilla": "#16a34a", "x": "#78716c", "youtube": "#ef4444"}

# 1. Share of flows vs share of the macro-F1 mark (train + validation counts, AGENTS.md / metadata of the labelled splits)
counts = {"facebook": 11, "google": 131, "instagram": 19, "mozilla": 41, "x": 73, "youtube": 55}
n = sum(counts.values())
apps = list(counts)
fig, ax = plt.subplots(figsize=(8, 4.2))
x = np.arange(len(apps))
ax.bar(x - 0.2, [100 * counts[a] / n for a in apps], 0.4, label="share of flows", color="#94a3b8")
ax.bar(x + 0.2, [100 / 6] * 6, 0.4, label="share of the macro-F1 mark", color=[C[a] for a in apps])
for i, a in enumerate(apps):
    ax.text(i, max(100 * counts[a] / n, 100 / 6) + 1.5, f"1 flow weighs\n{counts['google'] / counts[a]:.1f}x a google flow", ha="center", fontsize=7)
ax.set_xticks(x, apps); ax.set_ylabel("%"); ax.set_ylim(0, 50); ax.legend()
ax.set_title("Macro F1: every app gets the same weight")
fig.tight_layout(); fig.savefig(FIG / "guide_metric_weight.png", dpi=130)

# 2. Winner's curse: the facebook/instagram cutoff chosen in each of 50 folds (experiment 067)
th = json.loads((ROOT / "experiments/067_evidence/thresholds.json").read_text())["cv_seed_2026_fold_thetas"]
vals = np.array([float(v) for v in (th.values() if isinstance(th, dict) else th)])
fig, ax = plt.subplots(figsize=(7.5, 3.8))
bins = np.arange(0.175, 0.85, 0.05)
ax.hist(vals, bins=bins, color="#c026d3", edgecolor="#4a044e")
ax.axvline(0.5, color="#0f172a", ls="--", label="production cutoff (0.50)")
ax.set_xlabel("cutoff chosen by inner cross-validation (facebook vs instagram)"); ax.set_ylabel("folds (of 50)")
ax.set_title("Same data, 50 folds: the 'best' cutoff jumps from 0.20 to 0.80 (winner's curse)")
ax.legend(); fig.tight_layout(); fig.savefig(FIG / "guide_winners_curse.png", dpi=130)

# 3. Leader-style decision pipeline (experiment 095) vs our production, macro F1 on cv_seed 2026
prod = {"Task 1": 0.849, "Task 2": 0.7544}
arms = {"Task 1": [0.7811, 0.7549, 0.7715, 0.7666], "Task 2": [0.7362, 0.6921, 0.6985, 0.7026]}
labels = ["A0 balanced\nensemble", "A1 + calibration", "A2 + disclosed\ncounts", "A3 + training-share\ncounts"]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
for ax, t in zip(axes, ("Task 1", "Task 2")):
    ax.bar(range(4), arms[t], color=["#94a3b8", "#ea580c", "#c026d3", "#16a34a"])
    ax.axhline(prod[t], color="#0284c7", lw=2, label=f"our production ({prod[t]:.3f})")
    for i, v in enumerate(arms[t]):
        ax.text(i, v + 0.005, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_xticks(range(4), labels, fontsize=8); ax.set_ylim(0.6, 0.9); ax.set_title(t); ax.legend(loc="lower right")
axes[0].set_ylabel("macro F1 (5x10 CV, seed 2026)")
fig.suptitle("The leader's described method, simulated: every version stays below our production")
fig.tight_layout(); fig.savefig(FIG / "guide_leader_style.png", dpi=130)
print("ok", sorted(vals)[:3], sorted(vals)[-3:], len(vals))
