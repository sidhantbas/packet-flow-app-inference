"""Experiment 037: nearest-twin override for Task 1.

Command: .venv/bin/python src/exp037_twin_override.py
Rule: if a held-out flow has a training flow within distance t (17 whole-flow features, log1p, standardised with mean/std of the
training flows only), take the label of the nearest such flow; otherwise keep the model's label.
  1. Test flows with a labelled flow within 0.05 (training = all 330 labelled flows, as for the final model).
  2. Normal CV (post-processing of the logged production predictions; folds regenerated and checked against the logs):
     thresholds 0.03 / 0.05 / 0.08 / 0.12 on cv_seed 2026. The threshold is chosen as the one with the largest mean gain that
     passes rule v2 at 2026, then confirmed on cv_seeds 2027 and 2028.
  3. Order with scoped H1 (exact-opening override outside facebook/instagram), both applied post hoc to the production labels:
     twin last vs H1 last. Twin overrides that touch facebook/instagram (Meta gate territory) are counted.
Every variant is logged with runlog.record_run against the production run on the same folds.
"""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import DATA, TASK_FEATURES, basic_features, load_task
from evaluation_metric import macro_f1
from models import T1_COLS, TASK_MODELS, TwoClerks
from runlog import load_index, load_oof, record_run

T1 = "task1_static"
X_raw, y = load_task(T1)
FID, Y = X_raw.flow_id.values, y.values
LABELS = sorted(set(Y))
L17 = np.log1p(basic_features(X_raw)[list(T1_COLS)].astype(float).clip(lower=0)).values
XF = TASK_FEATURES[T1](X_raw)
OKEY = XF[list(TwoClerks.OPEN_COLS)].astype(str).agg("|".join, axis=1).values
META = ("facebook", "instagram")
THRESHOLDS = (0.03, 0.05, 0.08, 0.12)
PROD = {2026: "034_meta_gate", 2027: "034_meta_rescue_s2027", 2028: "034_meta_rescue_s2028"}


def run_id(suffix):
    return next(e["run_id"] for e in load_index() if e["run_id"].endswith(suffix))


def scaled(tr):
    mu, sd = L17[tr].mean(0), L17[tr].std(0)
    sd = np.where(sd > 0, sd, 1)
    return (L17 - mu) / sd


def production_oof(seed):
    """Logged production labels, aligned to regenerated folds (checked)."""
    splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=seed).split(XF, y))
    o = load_oof(run_id(PROD[seed]), T1)
    o["row"] = o.flow_id.map({f: i for i, f in enumerate(FID)})
    for i, (tr, te) in enumerate(splits):
        assert sorted(o[o.fold == i].row) == sorted(te), "folds do not match the logged run"
    return o.sort_values(["fold", "row"]).reset_index(drop=True), splits


def twin_rule(o, splits, t):
    out = o.copy()
    for i, (tr, te) in enumerate(splits):
        Z = scaled(tr)
        D = np.sqrt(((Z[te][:, None] - Z[tr][None]) ** 2).sum(-1))
        j, dmin = D.argmin(1), D.min(1)
        idx = out.index[out.fold == i]
        rows = out.loc[idx, "row"].values
        pos = {r: k for k, r in enumerate(te)}
        for ix, r in zip(idx, rows):
            k = pos[r]
            if dmin[k] <= t:
                out.at[ix, "y_pred"] = Y[tr][j[k]]
    return out


def scoped_h1(o, splits):
    out = o.copy()
    for i, (tr, te) in enumerate(splits):
        t = pd.DataFrame({"k": OKEY[tr], "y": Y[tr]}).groupby("k").y.agg(lambda v: v.unique())
        table = {k: v[0] for k, v in t.items() if len(v) == 1}
        idx = out.index[out.fold == i]
        for ix in idx:
            lab = table.get(OKEY[out.at[ix, "row"]])
            if lab is not None and lab not in META and out.at[ix, "y_pred"] not in META:
                out.at[ix, "y_pred"] = lab
    return out


def as_result(o, seed):
    """Build an evaluate()-style result from held-out labels so runlog can log and compare it."""
    folds = sorted(o.fold.unique())
    macro = np.array([f1_score(o[o.fold == i].y_true, o[o.fold == i].y_pred, average="macro") for i in folds])
    pc = np.array([f1_score(o[o.fold == i].y_true, o[o.fold == i].y_pred, average=None, labels=LABELS, zero_division=0) for i in folds])
    return {"task": T1, "n_flows": len(Y), "features": list(T1_COLS), "labels": LABELS, "fold_macro": macro, "fold_per_class": pc,
            "y_true": o.y_true.values, "y_pred": o.y_pred.values, "flow_id": o.flow_id.values, "fold": o.fold.values,
            "fold_seconds": np.zeros(len(folds)), "extra_data": [],
            "cv": {"n_splits": 5, "n_repeats": 10, "cv_seed": seed, "resample": None, "fold_jobs": None, "splits": "RepeatedStratifiedKFold"},
            "macro_mean": macro.mean(), "macro_std": macro.std(ddof=1),
            "repeat_std": macro.reshape(10, 5).mean(1).std(ddof=1),
            "per_class_mean": dict(zip(LABELS, pc.mean(0))), "per_class_std": dict(zip(LABELS, pc.std(0, ddof=1)))}


def log(o, seed, name, question):
    t0 = datetime.now(timezone.utc)
    return record_run("037", name + ("" if seed == 2026 else f"_s{seed}"), {T1: as_result(o, seed)},
                      reference=run_id(PROD[seed]), question=question,
                      config={"rule": name, "post_hoc_on": PROD[seed], "cv_seed": seed}, started=t0)


def compare(base, new):
    ch = new.y_pred != base.y_pred
    fixed = (ch & (new.y_pred == new.y_true)).sum()
    broken = (ch & (base.y_pred == base.y_true)).sum()
    fb = base.groupby("fold").apply(lambda g: macro_f1(list(g.y_true), list(g.y_pred)), include_groups=False).values
    fn = new.groupby("fold").apply(lambda g: macro_f1(list(g.y_true), list(g.y_pred)), include_groups=False).values
    d = fn - fb
    return dict(changed=int(ch.sum()), fixed=int(fixed), broken=int(broken), macro=fn.mean(), delta=d.mean(),
                wins=int((d > 1e-12).sum()), losses=int((d < -1e-12).sum()), ties=int((abs(d) <= 1e-12).sum()))


def main():
    # 1. test flows with a labelled twin
    T_raw = pd.read_csv(DATA / T1 / "test_features.csv")
    LT = np.log1p(basic_features(T_raw)[list(T1_COLS)].astype(float).clip(lower=0)).values
    mu, sd = L17.mean(0), np.where(L17.std(0) > 0, L17.std(0), 1)
    D = np.sqrt(((((LT - mu) / sd)[:, None] - ((L17 - mu) / sd)[None]) ** 2).sum(-1))  # Euclidean (bug fixed 2026-10-05)
    prod = TASK_MODELS[T1](0).fit(XF, y)
    tp = np.asarray(prod.predict(TASK_FEATURES[T1](T_raw)))
    print("== 1. test flows with a labelled flow within 0.05")
    for i in np.where(D.min(1) <= 0.05)[0]:
        j = D[i].argmin()
        within = sorted({Y[k] for k in np.where(D[i] <= 0.05)[0]})
        print(f"  {T_raw.flow_id[i][5:]}  twin {FID[j][5:]} ({D[i, j]:.3f})  twin label {Y[j]:9s} production {tp[i]:9s} "
              f"{'DISAGREE' if tp[i] != Y[j] else 'agree'}{'' if len(within) == 1 else '  labels within 0.05: ' + ','.join(within)}")

    # 2. thresholds on cv_seed 2026
    base, splits = production_oof(2026)
    print("\n== 2. twin rule on normal CV, cv_seed 2026 (vs production)")
    res = {}
    for t in THRESHOLDS:
        new = twin_rule(base, splits, t)
        c = compare(base, new)
        res[t] = (c, new)
        print(f"  t={t:<5} changed {c['changed']:3d} fixed {c['fixed']:3d} broken {c['broken']:3d} macro {c['macro']:.4f} "
              f"Δ {c['delta']:+.4f} W/L/T {c['wins']}/{c['losses']}/{c['ties']}")
        log(new, 2026, f"twin_t{str(t).replace('.', '')}", f"Twin override within {t} on top of production, cv_seed 2026")
    ok = [t for t in THRESHOLDS if res[t][0]["delta"] > 0 and res[t][0]["wins"] + res[t][0]["losses"] >= 10
          and res[t][0]["wins"] >= 0.7 * (res[t][0]["wins"] + res[t][0]["losses"])]
    chosen = max(ok, key=lambda t: res[t][0]["delta"]) if ok else None
    print(f"  passing at 2026: {ok}; chosen threshold: {chosen}")
    if chosen is None:
        return

    # confirmation of the chosen threshold
    print("\n== confirmation of the chosen threshold")
    for seed in (2027, 2028):
        b, sp = production_oof(seed)
        new = twin_rule(b, sp, chosen)
        c = compare(b, new)
        print(f"  cv_seed {seed}: changed {c['changed']} fixed {c['fixed']} broken {c['broken']} Δ {c['delta']:+.4f} W/L/T {c['wins']}/{c['losses']}/{c['ties']}")
        log(new, seed, f"twin_t{str(chosen).replace('.', '')}", f"Twin override within {chosen}, cv_seed {seed} (confirmation)")

    # 3. interaction with the Meta gate and scoped H1 (cv_seed 2026)
    print("\n== 3. order with scoped H1 and contact with Meta decisions (cv_seed 2026)")
    tw = res[chosen][1]
    ch = tw.y_pred != base.y_pred
    meta_touch = ch & (base.y_pred.isin(META) | tw.y_pred.isin(META))
    print(f"  twin overrides touching facebook/instagram: {int(meta_touch.sum())} "
          f"(fixed {int((meta_touch & (tw.y_pred == tw.y_true)).sum())}, broken {int((meta_touch & (base.y_pred == base.y_true)).sum())})")
    print("  changes by (true, was -> now):")
    print(tw[ch].assign(was=base.y_pred[ch]).groupby(["y_true", "was", "y_pred"]).size().rename("n").reset_index().to_string(index=False))
    h1 = scoped_h1(base, splits)
    h1_logged = load_oof(run_id("036_scoped_h1_normal_s2026"), T1).sort_values(["fold", "flow_id"]).y_pred.values
    assert (h1.sort_values(["fold", "flow_id"]).y_pred.values == h1_logged).all(), "post-hoc scoped H1 does not match 036"
    combos = {"scoped H1 only": h1, "H1 then twin (twin last)": twin_rule(h1, splits, chosen),
              "twin then H1 (H1 last)": scoped_h1(tw, splits)}
    for name, o in combos.items():
        c = compare(base, o)
        print(f"  {name:26s} changed {c['changed']:3d} fixed {c['fixed']:3d} broken {c['broken']:3d} macro {c['macro']:.4f} Δ {c['delta']:+.4f} W/L/T {c['wins']}/{c['losses']}/{c['ties']}")
    log(combos["H1 then twin (twin last)"], 2026, "h1_then_twin", "Scoped H1 then twin override (twin last), cv_seed 2026")
    log(combos["twin then H1 (H1 last)"], 2026, "twin_then_h1", "Twin override then scoped H1 (H1 last), cv_seed 2026")

    # test impact at the chosen threshold
    tt = tp.copy()
    for i in np.where(D.min(1) <= chosen)[0]:
        tt[i] = Y[D[i].argmin()]
    print(f"\n== test predictions changed at t={chosen}: {int((tt != tp).sum())}")
    for i in np.where(tt != tp)[0]:
        print(f"  {T_raw.flow_id[i][5:]}: {tp[i]} -> {tt[i]}")


if __name__ == "__main__":
    main()
