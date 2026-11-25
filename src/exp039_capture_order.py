"""Experiment 039: capture-order leakage (measurement only; production and submission unchanged).

Command: .venv/bin/python src/exp039_capture_order.py
  1. Normal CV (cv_seed 2026): predict each held-out flow from the labels of its k nearest training flows by flow_id number and by
     start_rel (k = 1, 3, 5; majority vote, ties to the nearest). Macro F1 and facebook F1.
  2. Runs of same-app consecutive flows among the 330 labelled flows, in flow_id order and in start_rel order.
  3. Production + capture-order kNN, fixed before running: final probabilities = 0.5 x production probabilities (Task 1: gate-
     weighted two-clerks probabilities; Task 2: base SoftVote) + 0.5 x kNN vote shares (k = 5, the ordering that scores higher in
     part 1), then the production rules (Task 1: facebook rule of the 17-column SoftVote; Task 2: facebook/instagram stage).
     Estimated leaderboard = test result (84.62: Task 1 0.787, Task 2 0.905) + 50 x CV gain per task. Not logged as a candidate.
"""
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import CV_SEED, TASK_FEATURES, load_task
from models import TASK_MODELS

T1, T2 = "task1_static", "task2_realtime_prefix5"
LABELS = None


def data(task):
    X_raw, y = load_task(task)
    return X_raw, np.asarray(y.values, dtype=object), TASK_FEATURES[task](X_raw)


def order_key(X_raw, kind):
    return X_raw.flow_id.str[5:].astype(int).values.astype(float) if kind == "flow_id" else X_raw.start_rel.values


def knn_votes(key, Y, tr, te, k, labels):
    d = np.abs(key[te][:, None] - key[tr][None])
    nn = np.argsort(d, 1, kind="stable")[:, :k]
    V = np.zeros((len(te), len(labels)))
    for c, lab in enumerate(labels):
        V[:, c] = (Y[tr][nn] == lab).sum(1)
    V += 1e-3 * (Y[tr][nn[:, :1]] == np.array(labels)[None, :])  # tie -> nearest
    return V / V.sum(1, keepdims=True)


def scores(y_true, y_pred, folds, labels):
    m, fb = [], []
    for i in np.unique(folds):
        s = folds == i
        m.append(f1_score(y_true[s], y_pred[s], average="macro"))
        fb.append(f1_score(y_true[s], y_pred[s], labels=["facebook"], average="macro", zero_division=0))
    return np.array(m), np.array(fb)


def part1():
    X_raw, Y, _ = data(T1)
    labels = sorted(set(Y))
    splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=CV_SEED).split(X_raw, Y))
    print("== 1. capture-order kNN, normal CV (cv_seed 2026), Task 1 labels")
    best = {}
    for kind in ("flow_id", "start_rel"):
        key = order_key(X_raw, kind)
        for k in (1, 3, 5):
            yt, yp, fo = [], [], []
            for i, (tr, te) in enumerate(splits):
                V = knn_votes(key, Y, tr, te, k, labels)
                yt += list(Y[te]); yp += list(np.array(labels)[V.argmax(1)]); fo += [i] * len(te)
            m, fb = scores(np.array(yt), np.array(yp), np.array(fo), labels)
            print(f"  {kind:9s} k={k}: macro F1 {m.mean():.3f} ± {m.std(ddof=1):.3f}   facebook F1 {fb.mean():.3f}")
            best[(kind, k)] = m.mean()
    return max(("flow_id", "start_rel"), key=lambda kind: best[(kind, 5)])


def part2():
    X_raw, Y, _ = data(T1)
    print("\n== 2. runs of same-app consecutive labelled flows")
    for kind in ("flow_id", "start_rel"):
        order = np.argsort(order_key(X_raw, kind), kind="stable")
        apps = Y[order]
        runs, cur = [], [apps[0], 1]
        for a in apps[1:]:
            if a == cur[0]:
                cur[1] += 1
            else:
                runs.append(tuple(cur)); cur = [a, 1]
        runs.append(tuple(cur))
        R = pd.DataFrame(runs, columns=["app", "length"])
        in_runs = int(R[R.length >= 2].length.sum())
        print(f"  {kind} order: {len(R)} runs; {in_runs} of 330 flows ({in_runs / 330:.0%}) sit in runs of length >= 2")
        summ = R.groupby("app").length.agg(runs="size", mean="mean", median="median", longest="max")
        summ["flows_in_runs>=2"] = R[R.length >= 2].groupby("app").length.sum()
        print(summ.round(2).fillna(0).to_string())
    rho = pd.Series(order_key(X_raw, "flow_id")).corr(pd.Series(X_raw.start_rel.values), method="spearman")
    print(f"  Spearman(flow_id number, start_rel) = {rho:.3f}")


def fold_combined(task, i, tr, te, X, Y, key, labels):
    m = TASK_MODELS[task](i).fit(X.iloc[tr], Y[tr])
    Xt = X.iloc[te]
    prod = np.asarray(m.predict(Xt))
    cls = np.asarray(m.classes_)
    assert list(cls) == labels
    if task == T1:
        c = m.clerks_
        p = (c.whole_.predict_proba(Xt) + c.opening_.predict_proba(Xt[list(c.OPEN_COLS)])) / 2
        g = m.gate_.predict_proba(Xt)[:, list(m.gate_.classes_).index("meta")]
        meta = np.isin(cls, m.META)
        p = np.where(meta, g[:, None] * p / p[:, meta].sum(1, keepdims=True), (1 - g[:, None]) * p / p[:, ~meta].sum(1, keepdims=True))
    else:
        p = m.base_.predict_proba(Xt[m.base_cols_])
    V = knn_votes(key, Y, tr, te, 5, labels)
    comb = cls[(0.5 * p + 0.5 * V).argmax(1)]
    if task == T1:
        first = m.clerks_.whole_.models_[0].predict(Xt[m.clerks_.whole_.cols_[0]])
        comb[first == "facebook"] = "facebook"
    else:
        r = np.isin(comb, m.pair)
        if r.any():
            comb[r] = m.spec_.predict(Xt.loc[r, m.spec_cols_])
    return pd.DataFrame({"fold": i, "y_true": Y[te], "prod": prod, "comb": comb})


def part3(kind):
    print(f"\n== 3. production + capture-order kNN (k = 5, {kind}), normal CV cv_seed 2026")
    test = {T1: 0.787393, T2: 0.905055}
    est = 0.0
    for task in (T1, T2):
        X_raw, Y, X = data(task)
        labels = sorted(set(Y))
        key = order_key(X_raw, kind)
        splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=CV_SEED).split(X, Y))
        o = pd.concat(Parallel(n_jobs=-1)(delayed(fold_combined)(task, i, tr, te, X, Y, key, labels) for i, (tr, te) in enumerate(splits)))
        mp, fp = scores(o.y_true.values, o["prod"].values, o.fold.values, labels)
        mc, fc = scores(o.y_true.values, o.comb.values, o.fold.values, labels)
        d = mc - mp
        print(f"  {task}: production {mp.mean():.4f} (facebook {fp.mean():.3f}) -> combined {mc.mean():.4f} (facebook {fc.mean():.3f}); "
              f"Δ {d.mean():+.4f}, folds won {(d > 1e-12).sum()}, lost {(d < -1e-12).sum()}, tied {(abs(d) <= 1e-12).sum()}")
        est += 50 * min(1.0, test[task] + d.mean())
    print(f"  estimated leaderboard (test 84.62 + 50 x CV gain per task): {est:.2f}")


if __name__ == "__main__":
    kind = part1()
    part2()
    part3(kind)
