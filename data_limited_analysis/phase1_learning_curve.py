"""Phase 1: learning curve of the production pipeline (PROTOCOL.md)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402
from scipy.optimize import curve_fit  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402
from sklearn.model_selection import StratifiedShuffleSplit  # noqa: E402

from common import FIG, PROD, T1, T2, TASKS, data, save, score, splits  # noqa: E402

FRACS = [0.2, 0.4, 0.6, 0.8, 1.0]
SEEDS = [0, 1, 2]


def subsample(tr, y, frac, seed):
    if frac >= 1.0:
        return np.asarray(tr)
    idx, _ = next(StratifiedShuffleSplit(n_splits=1, train_size=frac, random_state=seed).split(tr, y[tr]))
    sub = list(np.asarray(tr)[idx])
    rng = np.random.default_rng(seed)
    for c in np.unique(y[tr]):
        have = [i for i in sub if y[i] == c]
        if len(have) < 2:
            pool = [i for i in tr if y[i] == c and i not in sub]
            sub += list(rng.choice(pool, size=min(2 - len(have), len(pool)), replace=False))
    return np.array(sub)


def one(task, X, y, i, tr, te, frac, seed):
    sub = subsample(tr, y, frac, seed)
    m = PROD[task](i).fit(X.iloc[sub], y[sub])
    return {"task": task, "fold": i, "frac": frac, "seed": seed, "n": len(sub),
            "val": f1_score(y[te], m.predict(X.iloc[te]), average="macro"),
            "train": f1_score(y[sub], m.predict(X.iloc[sub]), average="macro")}


def power(n, a, b, c):
    return a - b * np.power(n, -c)


def main():
    recs = []
    for task in TASKS:
        _, X, y = data(task)
        jobs = [(task, X, y, i, tr, te, f, s) for i, (tr, te) in enumerate(splits(task)) for f in FRACS
                for s in (SEEDS if f < 1 else [0])]
        recs += Parallel(n_jobs=-1)(delayed(one)(*j) for j in jobs)
    # seed-averaged per fold and fraction, then total score per fold (same subsample indices in both tasks)
    tab = {}
    for r in recs:
        tab.setdefault((r["task"], r["frac"], r["fold"]), []).append(r)
    rows = []
    for f in FRACS:
        n = np.mean([np.mean([r["n"] for r in tab[(T1, f, i)]]) for i in range(25)])
        v1 = np.array([np.mean([r["val"] for r in tab[(T1, f, i)]]) for i in range(25)])
        v2 = np.array([np.mean([r["val"] for r in tab[(T2, f, i)]]) for i in range(25)])
        t1 = np.array([np.mean([r["train"] for r in tab[(T1, f, i)]]) for i in range(25)])
        t2 = np.array([np.mean([r["train"] for r in tab[(T2, f, i)]]) for i in range(25)])
        rows.append({"frac": f, "n": float(n), "val": score(v1, v2), "train": score(t1, t2), "val_t1": 50 * v1,
                     "val_t2": 50 * v2})
    ns = np.array([r["n"] for r in rows])
    out = {"fracs": FRACS, "seeds": SEEDS, "n_per_fold": ns.tolist(), "curves": {}}
    for key in ("val", "val_t1", "val_t2"):
        m = np.array([r[key].mean() for r in rows])
        sd = np.array([r[key].std(ddof=1) for r in rows])
        hi = 100 if key == "val" else 50
        try:
            (a, b, c), _ = curve_fit(power, ns, m, p0=[m[-1] + 2, 50, 0.5], bounds=([0, 0, 1e-3], [hi, 1e6, 3]), maxfev=20000)
            s_now = power(ns[-1], a, b, c)
            need = {}
            for gain in (1, 2):
                tgt = s_now + gain
                need[f"+{gain}"] = None if tgt >= a else float(((a - tgt) / b) ** (-1 / c) - ns[-1])
            fit = {"a_plateau": float(a), "b": float(b), "c": float(c), "fit_at_full": float(s_now),
                   "extra_rows_per_fold_needed": need}
        except Exception as e:  # report, do not hide
            fit = {"error": str(e)}
        out["curves"][key] = {"mean": m.tolist(), "sd": sd.tolist(), "fit": fit}
    out["train_curve"] = {"mean": [float(r["train"].mean()) for r in rows], "sd": [float(r["train"].std(ddof=1)) for r in rows]}
    d = rows[-1]["val"] - rows[-2]["val"]
    out["paired_80_to_100"] = {"delta_mean": float(d.mean()), "delta_sd": float(d.std(ddof=1)),
                               "verdict": "sample-limited (rising)" if d.mean() > d.std(ddof=1) else "flat (tie)"}
    for k in ("val_t1", "val_t2"):
        dd = rows[-1][k] - rows[-2][k]
        out[f"paired_80_to_100_{k}"] = {"delta_mean": float(dd.mean()), "delta_sd": float(dd.std(ddof=1))}
    save("phase1_learning_curve.json", out)
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.5))
    ax[0].errorbar(ns, out["curves"]["val"]["mean"], yerr=out["curves"]["val"]["sd"], marker="o", capsize=3, label="validation")
    ax[0].errorbar(ns, out["train_curve"]["mean"], yerr=out["train_curve"]["sd"], marker="s", capsize=3, label="training")
    for k, axi, ttl in (("val", ax[0], "Total score"), ("val_t1", ax[1], "Task 1 (50 x macro F1)"), ("val_t2", ax[2], "Task 2 (50 x macro F1)")):
        f = out["curves"][k]["fit"]
        if "a_plateau" in f:
            nn = np.linspace(ns[0], ns[-1] * 4, 200)
            axi.plot(nn, power(nn, f["a_plateau"], f["b"], f["c"]), "--", label=f"power law, plateau {f['a_plateau']:.1f}")
        if k != "val":
            axi.errorbar(ns, out["curves"][k]["mean"], yerr=out["curves"][k]["sd"], marker="o", capsize=3, label="validation")
        axi.set_title(ttl); axi.set_xlabel("training rows per fold"); axi.legend(); axi.grid(alpha=.3)
    ax[0].set_ylabel("score (5x5 CV, mean ± SD over folds)")
    fig.tight_layout(); fig.savefig(FIG / "phase1_learning_curve.png", dpi=130)
    print({k: v for k, v in out.items() if k != "curves"}, {k: v["fit"] for k, v in out["curves"].items()})


if __name__ == "__main__":
    main()
