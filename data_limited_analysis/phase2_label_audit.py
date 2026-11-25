"""Phase 2: label-quality audit with confident learning (PROTOCOL.md). Writes OOF probabilities for Phases 3-4."""
import math

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import StratifiedKFold

from common import HERE, LABS, SoftVote, TASKS, data, paired, run, save, splits


def oof_proba(task):
    Xr, X, y = data(task)

    def fold(i, tr, te):
        sv = SoftVote(seed=i).fit(X.iloc[tr], y[tr])
        P = np.zeros((len(te), len(LABS)))
        P[:, [LABS.index(c) for c in sv.classes_]] = sv.predict_proba(X.iloc[te])
        return te, P
    acc, cnt = np.zeros((len(y), len(LABS))), np.zeros(len(y))
    for te, P in Parallel(n_jobs=-1)(delayed(fold)(i, tr, te) for i, (tr, te) in enumerate(splits(task))):
        acc[te] += P
        cnt[te] += 1
    return Xr, X, y, acc / cnt[:, None]


def suspicion(P, y):
    lab = np.array([LABS.index(c) for c in y])
    own = P[np.arange(len(y)), lab]
    Q = P.copy()
    Q[np.arange(len(y)), lab] = -1
    return Q.max(axis=1) - own, lab, own


def cl_flags(P, y):
    s, lab, own = suspicion(P, y)
    t = np.array([P[lab == j, j].mean() if (lab == j).any() else 1.0 for j in range(len(LABS))])
    other = P >= t[None, :]
    other[np.arange(len(y)), lab] = False
    return (own < t[lab]) & other.any(axis=1)


def make_remover(k):
    def remove_top(X_tr, y_tr, seed):
        yv = np.asarray(y_tr, dtype=object)
        P = np.zeros((len(yv), len(LABS)))
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(X_tr, yv):
            sv = SoftVote(seed=seed).fit(X_tr.iloc[tr], yv[tr])
            P[np.ix_(te, [LABS.index(c) for c in sv.classes_])] = sv.predict_proba(X_tr.iloc[te])
        s, _, _ = suspicion(P, yv)
        drop = np.argsort(-s)[:math.ceil(k * len(yv))]
        keep = np.ones(len(yv), bool)
        keep[drop] = False
        return X_tr.loc[keep], y_tr.loc[keep]
    remove_top.__name__ = f"remove_top_{k:g}"
    return remove_top


def main():
    out = {"probability_model": "balanced SoftVote, 5x5 CV OOF, averaged per flow", "tasks": {}}
    for task in TASKS:
        Xr, X, y, P = oof_proba(task)
        s, lab, own = suspicion(P, y)
        flag = cl_flags(P, y)
        pred = np.array(LABS)[P.argmax(axis=1)]
        df = pd.concat([pd.DataFrame({"flow_id": Xr.flow_id.values, "given_label": y, "predicted_label": pred,
                                      "p_given": own.round(4), "p_predicted": P.max(axis=1).round(4),
                                      "suspicion": s.round(4), "cl_flag": flag}),
                        pd.DataFrame(P.round(4), columns=[f"p_{c}" for c in LABS]), X.reset_index(drop=True)], axis=1)
        df.sort_values("suspicion", ascending=False).to_csv(HERE / f"phase2_suspects_{task}.csv", index=False)
        np.save(HERE / f"oof_proba_{task}.npy", P)
        conf_wrong = (pred != y) & (P.max(axis=1) >= 0.6)
        sens = {}
        for k in (0.01, 0.02, 0.05):
            sens[f"top_{int(k * 100)}pct"] = paired(task, run(task, resample=make_remover(k)))
            print(task, k, sens[f"top_{int(k * 100)}pct"], flush=True)
        out["tasks"][task] = {
            "cl_flagged": int(flag.sum()), "cl_flagged_by_class": dict(pd.Series(y[flag]).value_counts()),
            "confidently_wrong_p_ge_0.6": int(conf_wrong.sum()),
            "confidently_wrong_by_pair": dict(pd.Series([f"{a}->{b}" for a, b in zip(y[conf_wrong], pred[conf_wrong])]).value_counts()),
            "oof_accuracy_softvote": float((pred == y).mean()), "sensitivity": sens}
    save("phase2_label_audit.json", out)


if __name__ == "__main__":
    main()
