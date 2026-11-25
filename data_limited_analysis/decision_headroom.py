"""Decision-headroom audit (PROTOCOL.md addendum 2): how much could any decision rule gain over production's labels?"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402

from common import CV, FIG, LABS, PROD, T1, T2, TASKS, SoftVote, TASK_FEATURES, data, evaluate, save, splits  # noqa: E402

MARGIN = 0.25


def probs(task, X, y):
    def fold(i, tr, te):
        sv = SoftVote(seed=i).fit(X.iloc[tr], y[tr])
        P = np.zeros((len(te), len(LABS)))
        P[:, [LABS.index(c) for c in sv.classes_]] = sv.predict_proba(X.iloc[te])
        return P
    return Parallel(n_jobs=-1)(delayed(fold)(i, tr, te) for i, (tr, te) in enumerate(splits(task)))


def main():
    out = {"margin": MARGIN, "tasks": {}}
    f1s = {}
    for task in TASKS:
        _, X, y = data(task)
        r = evaluate(task, TASK_FEATURES[task], PROD[task], **CV)
        Ps = probs(task, X, y)
        pos = 0
        res = {"B0": [], "B1": [], "B2": []}
        reach1, reach2, unreach, pairs1, pairs2, n_err = [], [], 0, [], [], 0
        for i, (tr, te) in enumerate(splits(task)):
            yt = r["y_true"][pos:pos + len(te)]
            yp = np.asarray(r["y_pred"][pos:pos + len(te)], dtype=object)
            pos += len(te)
            P = Ps[i]
            order = np.argsort(-P, axis=1)
            top2 = np.array(LABS)[order[:, :2]]
            srt = np.sort(P, axis=1)
            close = (srt[:, -1] - srt[:, -2]) < MARGIN
            err = yp != yt
            in2 = (top2[:, 0] == yt) | (top2[:, 1] == yt)
            b1, b2 = yp.copy(), yp.copy()
            b1[err & in2] = yt[err & in2]
            b2[err & in2 & close] = yt[err & in2 & close]
            for k, v in (("B0", yp), ("B1", b1), ("B2", b2)):
                res[k].append(f1_score(yt, v, average="macro"))
            n_err += int(err.sum())
            unreach += int((err & ~in2).sum())
            reach1 += list(yt[err & in2])
            reach2 += list(yt[err & in2 & close])
            pairs1 += [f"{a}->{b}" for a, b in zip(yt[err & in2], yp[err & in2])]
            pairs2 += [f"{a}->{b}" for a, b in zip(yt[err & in2 & close], yp[err & in2 & close])]
        f1s[task] = {k: np.array(v) for k, v in res.items()}
        out["tasks"][task] = {
            "macro_f1": {k: [round(float(np.mean(v)), 4), round(float(np.std(v, ddof=1)), 4)] for k, v in res.items()},
            "errors_total": n_err, "reachable_top2": len(reach1), "reachable_top2_close": len(reach2), "unreachable": unreach,
            "reachable_close_by_true_class": dict(pd.Series(reach2).value_counts()),
            "reachable_close_by_pair": dict(pd.Series(pairs2).value_counts().head(8)),
            "reachable_top2_by_true_class": dict(pd.Series(reach1).value_counts())}
        print(task, out["tasks"][task], flush=True)
    out["total_score"] = {k: [round(float((50 * f1s[T1][k] + 50 * f1s[T2][k]).mean()), 3),
                              round(float((50 * f1s[T1][k] + 50 * f1s[T2][k]).std(ddof=1)), 3)] for k in ("B0", "B1", "B2")}
    gain = out["total_score"]["B2"][0] - out["total_score"]["B0"][0]
    out["reading"] = "decision side closed (B2 - B0 < 1 point)" if gain < 1 else "headroom >= 1 point: propose a rule under its own protocol"
    save("decision_headroom.json", out)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    lab = ["production (B0)", "realistic bound (B2)", "oracle top-2 (B1)"]
    vals = [out["total_score"][k] for k in ("B0", "B2", "B1")]
    ax.bar(lab, [v[0] for v in vals], yerr=[v[1] for v in vals], capsize=4, color=["#0284c7", "#ea580c", "#c026d3"])
    for j, v in enumerate(vals):
        ax.text(j, v[0] + 0.5, f"{v[0]:.1f}", ha="center")
    ax.set_ylabel("total score (5x5 CV, mean ± SD)"); ax.set_ylim(60, 100); ax.grid(alpha=.3, axis="y")
    ax.set_title("Decision headroom (re-ranking the top two classes)")
    fig.tight_layout(); fig.savefig(FIG / "decision_headroom.png", dpi=130)
    print(out["total_score"], out["reading"])


if __name__ == "__main__":
    main()
