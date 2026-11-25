"""Risk-coverage (reject option) analysis of the production pipeline (PROTOCOL.md addendum)."""
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402

from common import CV, FIG, LABS, PROD, T1, T2, TASKS, SoftVote, TASK_FEATURES, data, evaluate, save, splits  # noqa: E402

REJECT = [0.0, 0.05, 0.10, 0.20, 0.30]


def margins(task, X, y):
    def fold(i, tr, te):
        P = SoftVote(seed=i).fit(X.iloc[tr], y[tr]).predict_proba(X.iloc[te])
        s = np.sort(P, axis=1)
        return s[:, -1] - s[:, -2]
    return Parallel(n_jobs=-1)(delayed(fold)(i, tr, te) for i, (tr, te) in enumerate(splits(task)))


def main():
    per = {}
    for task in TASKS:
        _, X, y = data(task)
        r = evaluate(task, TASK_FEATURES[task], PROD[task], **CV)
        sp = splits(task)
        M = margins(task, X, y)
        pos, folds = 0, []
        for i, (tr, te) in enumerate(sp):
            yt, yp = r["y_true"][pos:pos + len(te)], r["y_pred"][pos:pos + len(te)]
            assert (yt == y[te]).all()
            folds.append((yt, yp, M[i]))
            pos += len(te)
        per[task] = folds
    out = {"reject_shares": REJECT, "tasks": {}, "total": {}}
    curves = {}
    for task in TASKS:
        rows = []
        for k in REJECT:
            acc, f1, caught, ab_cls = [], [], [], []
            for yt, yp, m in per[task]:
                n_ab = math.ceil(k * len(yt))
                order = np.argsort(m, kind="stable")
                keep = np.ones(len(yt), bool)
                keep[order[:n_ab]] = False
                acc.append((yt[keep] == yp[keep]).mean())
                f1.append(f1_score(yt[keep], yp[keep], average="macro"))
                err = yt != yp
                caught.append(err[~keep].sum() / max(err.sum(), 1))
                ab_cls += list(yt[~keep])
            rows.append({"reject": k, "accuracy": [float(np.mean(acc)), float(np.std(acc, ddof=1))],
                         "macro_f1": [float(np.mean(f1)), float(np.std(f1, ddof=1))],
                         "share_of_errors_abstained": float(np.mean(caught)),
                         "abstained_by_class": {c: int(v) for c, v in pd.Series(ab_cls).value_counts().items()},
                         "_f1_folds": f1})
        curves[task] = rows
        out["tasks"][task] = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    for j, k in enumerate(REJECT):
        s = 50 * np.array(curves[T1][j]["_f1_folds"]) + 50 * np.array(curves[T2][j]["_f1_folds"])
        out["total"][str(k)] = [float(s.mean()), float(s.std(ddof=1))]
    save("risk_coverage.json", out)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    cov = [100 * (1 - k) for k in REJECT]
    for task, mk in ((T1, "o"), (T2, "s")):
        ax[0].errorbar(cov, [100 * r["accuracy"][0] for r in curves[task]], yerr=[100 * r["accuracy"][1] for r in curves[task]],
                       marker=mk, capsize=3, label=f"{task} accuracy")
        ax[0].errorbar(cov, [100 * r["macro_f1"][0] for r in curves[task]], yerr=[100 * r["macro_f1"][1] for r in curves[task]],
                       marker=mk, capsize=3, ls="--", label=f"{task} macro F1")
        ax[1].plot(cov, [100 * r["share_of_errors_abstained"] for r in curves[task]], marker=mk, label=task)
    ax[0].set_xlabel("coverage (% of flows answered)"); ax[0].set_ylabel("% on answered flows"); ax[0].invert_xaxis()
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.3); ax[0].set_title("Risk-coverage (5x5 CV, mean ± SD)")
    ax[1].plot(cov, [100 * (1 - c / 100) for c in cov], "k:", label="random abstention")
    ax[1].set_xlabel("coverage (% of flows answered)"); ax[1].set_ylabel("% of production's errors abstained on")
    ax[1].invert_xaxis(); ax[1].legend(); ax[1].grid(alpha=.3); ax[1].set_title("Errors caught by abstaining")
    fig.tight_layout(); fig.savefig(FIG / "risk_coverage.png", dpi=130)
    print(out)


if __name__ == "__main__":
    main()
