"""Experiment 031: out-of-fold error audit of the production pipelines (steps 1-3).

Command (from the project root):
    .venv/bin/python src/exp031_error_audit.py

What it does, per task, on the default folds (repeated stratified 5 x 10, cv_seed 2026, model seed = fold index):
  1. Refits the production pipeline (models.TASK_MODELS / cv.TASK_FEATURES) on each training fold and records, for every
     held-out row, the probability vector the pipeline decides from, the final label and which component decided it.
     Verifies: fold isolation, probability-column alignment, reconstruction of the final label, and exact reproduction
     of the logged champion run's held-out labels.
  2. Error audit: official macro F1 (the organisers' _macro_f1), per-class precision/recall, confusion, confused pairs,
     true-label-ranked-second share, error rate by probability-margin bin, error stability across repeats.
  3. Feature overlap for each task's dominant confused pair: exact duplicate vectors of the pipeline inputs (no
     rounding) and the empirical duplicate-conflict accuracy bound; nearest training neighbour of every held-out row
     (log1p fixed transform + StandardScaler fitted on the training fold only); for Task 1, whether the opening columns
     separate flows the whole-flow columns do not.
Decision probability vector: Task 1 = mean of the two SoftVotes (before the facebook override); Task 2 = base SoftVote
(before the facebook/instagram stage, whose own two-class probabilities are stored separately). Margins are not
calibrated probabilities.
Outputs: results/<UTC stamp>_031_error_audit/<task>/*.csv, audit.json, manifest.json, checksums.json.
"""
import importlib.util
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.preprocessing import StandardScaler

from cv import CV_SEED, TASKS, TASK_FEATURES, load_task
from models import T1_COLS, TASK_MODELS
from runlog import RESULTS, ROOT, code_hashes, data_hashes, device_profile, git_state, load_champions, load_oof, \
    package_versions, sha256_file

T1, T2 = TASKS
OPEN_COLS = ["p5_transport", "p5_packet_count_up", "p5_packet_count_down", "p5_bytes_up", "p5_bytes_down",
             "p5_mean_pkt_size_up", "p5_mean_pkt_size_down", "p5_std_pkt_size_up", "p5_std_pkt_size_down",
             "p5_burst_count", "p5_up_down_packet_ratio", "p5_up_down_byte_ratio"]
MARGIN_BINS = [0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0001]


def official_macro_f1():
    spec = importlib.util.spec_from_file_location("official", ROOT / "data/official/evaluation_script/main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._macro_f1


MACRO_F1 = official_macro_f1()


# ---------------------------------------------------------------- step 1: held-out predictions with probabilities

def fold_rows(task, i, tr, te, X, y, fid, n_splits):
    model = TASK_MODELS[task](i).fit(X.iloc[tr], y.iloc[tr])
    Xte = X.iloc[te]
    final = np.asarray(model.predict(Xte))
    classes = list(model.classes_)
    rows = pd.DataFrame({"flow_id": fid[te], "repeat": i // n_splits, "fold": i, "y_true": y.iloc[te].values,
                         "y_pred": final})
    if task == T1:
        p = model.predict_proba(Xte)                          # mean of the two SoftVotes (ColumnBlend)
        argmax = np.asarray(classes)[p.argmax(axis=1)]
        first = model.models_[0].predict(Xte[model.cols_[0]])
        rebuilt = np.where(first == "facebook", "facebook", argmax)
        rows["decided_by"] = np.where((first == "facebook") & (argmax != "facebook"), "facebook_override", "blend")
        rows["pre_rule_pred"] = argmax
    else:
        p = model.base_.predict_proba(Xte[model.base_cols_])  # base SoftVote
        argmax = np.asarray(classes)[p.argmax(axis=1)]
        routed = np.isin(argmax, model.pair)
        rebuilt = argmax.copy()
        sp = np.full((len(te), 2), np.nan)
        if routed.any():
            spec_classes = list(model.spec_.classes_)
            sp_r = model.spec_.predict_proba(Xte.loc[routed, model.spec_cols_])
            sp[routed] = sp_r[:, [spec_classes.index(c) for c in ("facebook", "instagram")]]
            rebuilt[routed] = model.spec_.predict(Xte.loc[routed, model.spec_cols_])
        rows["decided_by"] = np.where(routed, "fb_ig_stage", "base")
        rows["pre_rule_pred"] = argmax
        rows["stage_p_facebook"], rows["stage_p_instagram"] = sp[:, 0], sp[:, 1]
    assert (rebuilt == final).all(), f"{task} fold {i}: final label not reconstructed"
    for k, c in enumerate(classes):
        rows[f"p_{c}"] = p[:, k]
    return rows, classes


def held_out(task, cv_seed=CV_SEED, n_splits=5, n_repeats=10):
    X_raw, y = load_task(task)
    X = TASK_FEATURES[task](X_raw)
    fid = X_raw.flow_id.values
    splits = list(RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=cv_seed).split(X, y))
    # fold isolation: train/test disjoint; each flow held out exactly once per repeat
    for i, (tr, te) in enumerate(splits):
        assert not set(tr) & set(te)
    for r in range(n_repeats):
        held = np.concatenate([splits[r * n_splits + k][1] for k in range(n_splits)])
        assert sorted(held) == list(range(len(y)))
    out = Parallel(n_jobs=-1)(delayed(fold_rows)(task, i, tr, te, X, y, fid, n_splits) for i, (tr, te) in enumerate(splits))
    classes = out[0][1]
    assert all(c == classes for _, c in out) and classes == sorted(y.unique()), "class order differs between folds"
    oof = pd.concat([o[0] for o in out], ignore_index=True)
    P = oof[[f"p_{c}" for c in classes]].values
    assert np.allclose(P.sum(axis=1), 1, atol=1e-6), "probabilities do not sum to 1"
    order = np.argsort(-P, axis=1)
    cls = np.asarray(classes)
    oof["top1"], oof["top2"] = cls[order[:, 0]], cls[order[:, 1]]
    oof["margin"] = P[np.arange(len(P)), order[:, 0]] - P[np.arange(len(P)), order[:, 1]]
    oof["true_rank"] = 1 + (order == np.searchsorted(cls, oof.y_true.values)[:, None]).argmax(axis=1)
    assert (oof.top1 == oof.pre_rule_pred).all()
    return oof, X, y, X_raw, splits, classes


def reproduction_check(task, oof):
    saved = load_oof(load_champions()[task]["run_id"], task)
    a = oof.sort_values(["fold", "flow_id"]).reset_index(drop=True)
    b = saved.sort_values(["fold", "flow_id"]).reset_index(drop=True)
    same = (a.flow_id.values == b.flow_id.values).all() and (a.y_pred.values == b.y_pred.values).all()
    return {"champion_run": load_champions()[task]["run_id"], "rows": len(a), "identical_labels": bool(same),
            "mismatches": int((a.y_pred.values != b.y_pred.values).sum())}


# ---------------------------------------------------------------- step 2: error audit

def error_audit(oof, classes):
    fold_scores = oof.groupby("fold").apply(lambda g: MACRO_F1(list(g.y_true), list(g.y_pred)), include_groups=False)
    pooled = pd.crosstab(oof.y_true, oof.y_pred).reindex(index=classes, columns=classes, fill_value=0)
    tp = np.diag(pooled.values)
    prec = tp / np.maximum(pooled.sum(axis=0).values, 1)
    rec = tp / np.maximum(pooled.sum(axis=1).values, 1)
    per_class = pd.DataFrame({"precision_pooled": prec, "recall_pooled": rec, "support_per_repeat": pooled.sum(axis=1).values / 10},
                             index=classes).round(3)
    pairs = []
    for a in range(len(classes)):
        for b in range(a + 1, len(classes)):
            n = pooled.iloc[a, b] + pooled.iloc[b, a]
            if n:
                pairs.append({"pair": f"{classes[a]} / {classes[b]}", "errors": int(n),
                              "true_first_pred_second": int(pooled.iloc[a, b]),
                              "true_second_pred_first": int(pooled.iloc[b, a])})
    pairs = pd.DataFrame(pairs).sort_values("errors", ascending=False)
    err = oof[oof.y_true != oof.y_pred]
    by_rule = oof.assign(err=oof.y_true != oof.y_pred).groupby("decided_by").err.agg(["size", "sum"])
    bins = pd.cut(oof.margin, MARGIN_BINS, right=False)
    by_margin = oof.assign(err=oof.y_true != oof.y_pred).groupby(bins, observed=False).err.agg(["size", "sum", "mean"]).round(3)
    by_margin.index = by_margin.index.astype(str)
    per_flow = oof.assign(err=oof.y_true != oof.y_pred).groupby("flow_id").agg(app=("y_true", "first"), errors=("err", "sum"))
    stab = pd.cut(per_flow.errors, [-1, 0, 4, 9, 10], labels=["0/10", "1-4/10", "5-9/10", "10/10"])
    stability = pd.crosstab(per_flow.app, stab).reindex(index=classes, fill_value=0)
    return {
        "macro_f1_mean": float(fold_scores.mean()), "macro_f1_std": float(fold_scores.std(ddof=1)),
        "fold_scores": fold_scores, "per_class": per_class, "confusion": pooled, "pairs": pairs,
        "n_predictions": len(oof), "n_mistakes": len(err),
        "true_rank_counts_among_mistakes": err.true_rank.value_counts().sort_index().to_dict(),
        "share_mistakes_true_second": float((err.true_rank == 2).mean()),
        "by_rule": by_rule, "by_margin": by_margin, "stability": stability, "per_flow": per_flow,
    }


# ---------------------------------------------------------------- step 3: feature overlap

def duplicate_bound(V, y):
    """Empirical duplicate-conflict bound: sum over identical-vector groups of the largest class count / rows.
    Exact equality on the given values (no rounding)."""
    key = pd.Series([tuple(r) for r in V.itertuples(index=False, name=None)])
    df = pd.DataFrame({"key": key, "y": np.asarray(y)})
    g = df.groupby("key").y
    sizes, majority, n_labels = g.size(), g.agg(lambda s: s.value_counts().iloc[0]), g.nunique()
    conflict = n_labels > 1
    return {"rows": len(df), "distinct_vectors": int(len(sizes)), "groups_with_duplicates": int((sizes > 1).sum()),
            "conflict_groups": int(conflict.sum()), "rows_in_conflict_groups": int(sizes[conflict].sum()),
            "bound_accuracy": float(majority.sum() / len(df)),
            "conflict_group_labels": [dict(df[df.key == k].y.value_counts()) for k in sizes[conflict].index]}


def nearest_training_neighbours(V, y, splits, oof):
    """Nearest training row (Euclidean) for each held-out row; log1p is a fixed transform, the scaler is fitted on the
    training fold only. Returns one row per held-out prediction, aligned with oof by (fold, flow_id)."""
    L = np.log1p(np.clip(V.values.astype(float), 0, None))
    yv = np.asarray(y)
    rows = []
    for i, (tr, te) in enumerate(splits):
        sc = StandardScaler().fit(L[tr])
        A, B = sc.transform(L[tr]), sc.transform(L[te])
        D = np.sqrt(((B[:, None, :] - A[None, :, :]) ** 2).sum(-1))
        j = D.argmin(axis=1)
        exact = (V.values[te][:, None, :] == V.values[tr][None, :, :]).all(-1)
        rows.append(pd.DataFrame({"fold": i, "row": te, "nn_label": yv[tr][j], "nn_dist": D[np.arange(len(te)), j],
                                  "exact_dup_in_train": exact.any(axis=1),
                                  "exact_dup_other_label": [bool((yv[tr][exact[k]] != yv[te][k]).any()) for k in range(len(te))]}))
    return pd.concat(rows, ignore_index=True)


def overlap(task, oof, X, y, X_raw, splits, pair):
    inputs = {T1: {"whole_17": list(T1_COLS), "pipeline_34": list(X.columns), "opening_12": OPEN_COLS},
              T2: {"pipeline_12": list(X.columns)}}[task]
    fid_index = {f: k for k, f in enumerate(X_raw.flow_id.values)}
    o = oof.assign(row=oof.flow_id.map(fid_index))
    dup = {name: duplicate_bound(X[cols], y) for name, cols in inputs.items()}
    in_pair = y.isin(pair).values
    dup_pair = {name: duplicate_bound(X.loc[in_pair, cols], y[in_pair]) for name, cols in inputs.items()}
    nn = {}
    for name, cols in inputs.items():
        n = nearest_training_neighbours(X[cols], y, splits, oof)
        nn[name] = o[["fold", "row", "y_true", "y_pred"]].merge(n, on=["fold", "row"])
    main = "pipeline_34" if task == T1 else "pipeline_12"
    m = nn[main]
    pair_err = m[(m.y_true != m.y_pred) & m.y_true.isin(pair) & m.y_pred.isin(pair)]
    cat = np.select([pair_err.exact_dup_other_label, pair_err.nn_label == pair_err.y_pred, pair_err.nn_label == pair_err.y_true],
                    ["exact duplicate of a training row with another label", "nearest training row has the predicted label",
                     "nearest training row has the true label"], "nearest training row: a third class")
    categories = pd.Series(cat).value_counts()
    ok = m[(m.y_true == m.y_pred) & m.y_true.isin(pair)]
    dist = pd.DataFrame({"pair mistakes": pair_err.nn_dist.describe(), "pair correct": ok.nn_dist.describe()}).round(3)
    result = {"dup_all_classes": dup, "dup_pair_only": dup_pair, "pair_mistake_categories": categories,
              "nn_distance": dist, "n_pair_mistakes": len(pair_err), "nn_tables": nn}
    if task == T1:
        w, op = nn["whole_17"], nn["opening_12"]
        j = w.merge(op, on=["fold", "row", "y_true", "y_pred"], suffixes=("_whole", "_open"))
        jp = j[j.y_true.isin(pair)]
        e = jp[jp.y_true != jp.y_pred]
        result["views_on_pair_mistakes"] = pd.crosstab(
            np.where(e.nn_label_whole == e.y_true, "whole-flow NN: true class", "whole-flow NN: other class"),
            np.where(e.nn_label_open == e.y_true, "opening NN: true class", "opening NN: other class"))
        result["views_on_pair_all"] = pd.crosstab(
            np.where(jp.nn_label_whole == jp.y_true, "whole-flow NN: true class", "whole-flow NN: other class"),
            np.where(jp.nn_label_open == jp.y_true, "opening NN: true class", "opening NN: other class"))
    return result


# ---------------------------------------------------------------- step 4 evidence: headroom of a decision-rule change

def decision_headroom(task, oof, pair):
    """Upper bounds (pooled, computed after seeing all held-out rows, so optimistic) on what a decision-rule change could
    fix. A nested procedure can only do worse."""
    out = {}
    narrow = oof[(oof.margin < 0.1) & oof.top1.isin(pair) & oof.top2.isin(pair)]
    out["pair_narrow_margin"] = {"rows": len(narrow), "errors": int((narrow.y_true != narrow.y_pred).sum()),
                                 "true_is_top2": int((narrow.y_true == narrow.top2).sum()),
                                 "true_is_top1": int((narrow.y_true == narrow.top1).sum()),
                                 "errors_removed_if_all_flipped": int((narrow.y_true == narrow.top2).sum() - (narrow.y_true == narrow.top1).sum())}
    e = oof[oof.y_true != oof.y_pred]
    pe = e[e.y_true.isin(pair) & e.y_pred.isin(pair)]
    out["mistake_margins"] = {"all_mistakes": len(e), "mistakes_margin_lt_0.1": int((e.margin < 0.1).sum()),
                              "pair_mistakes": len(pe), "pair_mistakes_margin_lt_0.1": int((pe.margin < 0.1).sum()),
                              "pair_mistakes_margin_ge_0.5": int((pe.margin >= 0.5).sum())}
    if task == T2:
        r = oof[oof.decided_by == "fb_ig_stage"]
        fi = r[r.y_true.isin(["facebook", "instagram"])]
        bins = pd.cut(fi.stage_p_facebook, [0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0001], right=False)
        out["stage_p_facebook_by_true_class"] = pd.crosstab(bins, fi.y_true)
        out["stage_routed"] = {"rows": len(r), "errors": int((r.y_true != r.y_pred).sum()),
                               "fb_ig_errors": int((fi.y_true != fi.y_pred).sum()),
                               "routed_true_outside_pair": int((~r.y_true.isin(["facebook", "instagram"])).sum())}
        rows = []
        for th in (0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7):
            pred = np.where(fi.stage_p_facebook >= th, "facebook", "instagram")
            rows.append({"threshold": th, "true_fb_pred_ig": int(((fi.y_true == "facebook") & (pred == "instagram")).sum()),
                         "true_ig_pred_fb": int(((fi.y_true == "instagram") & (pred == "facebook")).sum())})
        out["stage_threshold_table_pooled"] = pd.DataFrame(rows)
    return out


# ---------------------------------------------------------------- main

def main():
    stamp = datetime.now(timezone.utc)
    out = RESULTS / f"{stamp:%Y%m%dT%H%M%SZ}_031_error_audit"
    out.mkdir(parents=True)
    summary = {}
    for task in TASKS:
        d = out / task
        d.mkdir()
        oof, X, y, X_raw, splits, classes = held_out(task)
        oof.to_csv(d / "oof_predictions.csv", index=False)
        rep = reproduction_check(task, oof)
        a = error_audit(oof, classes)
        pair = tuple(a["pairs"].iloc[0]["pair"].split(" / "))
        ov = overlap(task, oof, X, y, X_raw, splits, pair)
        h = decision_headroom(task, oof, pair)
        a["fold_scores"].rename("macro_f1_official").to_csv(d / "fold_scores.csv")
        a["per_class"].to_csv(d / "per_class_precision_recall.csv")
        a["confusion"].to_csv(d / "confusion_pooled.csv")
        a["pairs"].to_csv(d / "confused_pairs.csv", index=False)
        a["by_margin"].to_csv(d / "error_by_margin.csv")
        a["by_rule"].to_csv(d / "error_by_deciding_component.csv")
        a["stability"].to_csv(d / "error_stability_by_flow.csv")
        a["per_flow"].to_csv(d / "errors_per_flow.csv")
        ov["pair_mistake_categories"].to_csv(d / "pair_mistake_categories.csv")
        ov["nn_distance"].to_csv(d / "pair_nn_distance.csv")
        for name, t in ov["nn_tables"].items():
            t.to_csv(d / f"nearest_neighbours_{name}.csv", index=False)
        if task == T1:
            ov["views_on_pair_mistakes"].to_csv(d / "pair_views_on_mistakes.csv")
            ov["views_on_pair_all"].to_csv(d / "pair_views_all.csv")
        if task == T2:
            h["stage_p_facebook_by_true_class"].to_csv(d / "stage_p_facebook_by_true_class.csv")
            h["stage_threshold_table_pooled"].to_csv(d / "stage_threshold_table_pooled.csv", index=False)
        summary[task] = {
            "reproduction": rep, "macro_f1_mean": a["macro_f1_mean"], "macro_f1_std": a["macro_f1_std"],
            "n_predictions": a["n_predictions"], "n_mistakes": a["n_mistakes"],
            "true_rank_counts_among_mistakes": {int(k): int(v) for k, v in a["true_rank_counts_among_mistakes"].items()},
            "share_mistakes_true_second": a["share_mistakes_true_second"], "dominant_pair": list(pair),
            "duplicates_all_classes": ov["dup_all_classes"], "duplicates_pair_only": ov["dup_pair_only"],
            "n_pair_mistakes": ov["n_pair_mistakes"],
            "pair_mistake_categories": ov["pair_mistake_categories"].to_dict(),
            "headroom": {k: v for k, v in h.items() if not isinstance(v, pd.DataFrame)},
            "accuracy_pooled": float((oof.y_true == oof.y_pred).mean()),
        }
        print(f"\n=== {task}: reproduction {rep}")
        print(f"official macro F1 {a['macro_f1_mean']:.4f} ± {a['macro_f1_std']:.4f}; mistakes {a['n_mistakes']}/{a['n_predictions']}")
        print("per class:\n" + a["per_class"].to_string())
        print("confused pairs:\n" + a["pairs"].head(5).to_string(index=False))
        print("mistakes by true-label rank:", summary[task]["true_rank_counts_among_mistakes"],
              f"(true ranked 2nd: {a['share_mistakes_true_second']:.1%})")
        print("errors by deciding component:\n" + a["by_rule"].to_string())
        print("error rate by margin bin:\n" + a["by_margin"].to_string())
        print("error stability (flows by #errors over 10 repeats):\n" + a["stability"].to_string())
        print(f"dominant pair {pair}: {ov['n_pair_mistakes']} pair mistakes; categories:\n" + ov["pair_mistake_categories"].to_string())
        print("nearest-neighbour distance:\n" + ov["nn_distance"].to_string())
        for name, dd in ov["dup_all_classes"].items():
            print(f"duplicates [{name}] all classes: {({k: v for k, v in dd.items() if k != 'conflict_group_labels'})}")
            print(f"   conflict groups: {dd['conflict_group_labels']}")
        for name, dd in ov["dup_pair_only"].items():
            print(f"duplicates [{name}] pair rows only: {({k: v for k, v in dd.items() if k != 'conflict_group_labels'})}")
        print("decision-rule headroom (pooled upper bounds):", {k: v for k, v in h.items() if not isinstance(v, pd.DataFrame)})
        if task == T2:
            print("fb/ig stage: p_facebook by true class:\n" + h["stage_p_facebook_by_true_class"].to_string())
            print("fb/ig stage thresholds (pooled):\n" + h["stage_threshold_table_pooled"].to_string(index=False))
        if task == T1:
            print("rows with true class in the pair, mistakes of any kind; nearest training neighbour by view:\n"
                  + ov["views_on_pair_mistakes"].to_string())
            print("all pair rows, nearest neighbour by view:\n" + ov["views_on_pair_all"].to_string())
    (out / "audit.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    manifest = {"run_id": out.name, "experiment": "031", "created_utc": stamp.isoformat(timespec="seconds"),
                "command": ".venv/bin/python src/exp031_error_audit.py", "cv_seed": CV_SEED,
                "device": device_profile(), "packages": package_versions(), "git": git_state(),
                "code_sha256": code_hashes(), "data_sha256": {t: data_hashes(t) for t in TASKS}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    sums = {p.relative_to(out).as_posix(): sha256_file(p) for p in sorted(out.rglob("*")) if p.is_file()}
    (out / "checksums.json").write_text(json.dumps(sums, indent=2) + "\n")
    print(f"\n-> results/{out.name}/")


if __name__ == "__main__":
    main()
