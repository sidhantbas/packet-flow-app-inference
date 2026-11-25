"""Local run logging: every CV run becomes a self-describing, verifiable folder under results/.

    from runlog import record_run
    res = {task: evaluate(task, feats, factory) for task in TASKS}
    run_id = record_run("006", "drop_timing_t2", res, question="Does dropping timing help task 2?",
                        config={"model": "SoftVote"}, model_factory=factory)

A run folder `results/<UTC stamp>_<exp>_<name>/` holds:
  manifest.json    what ran: experiment, question, git state, device specs, package versions,
                   SHA-256 of every data file read and of every src/*.py, CV settings, features, model
  <task>/folds.csv     per fold: repeat, macro F1, per-class F1, seconds
  <task>/oof.csv       every held-out prediction: fold, flow_id, y_true, y_pred
  <task>/summary.json  means, stds, pooled confusion matrix
  comparison.json  paired comparison with the reference run (champion by default), with a verdict
  checks.json      automatic warnings (rule breaks, noise, reproducibility, missing docs)
  report.md        human-readable digest of all of the above
  checksums.json   SHA-256 of every file above, for `runs.py verify`
and appends one line to results/index.jsonl. Everything runs on this machine; nothing is sent anywhere.
"""
import getpass
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
INDEX = RESULTS / "index.jsonl"
CHAMPIONS = RESULTS / "champions.json"
DATA = ROOT / "data" / "official" / "dataset"
EXPERIMENTS = ROOT / "experiments"

FORBIDDEN_FEATURES = {"flow_id", "split", "start_rel", "app"}  # identifiers, recording time, label
# Rule v2 (2026-09-30, experiment 014): "better" = mean Δ > 0, ≥ 70% of non-tied folds won, ≥ 10 non-tied
# folds, and (procedurally, not checked here) the same verdict on cv_seeds 2027 and 2028. Ties are folds where
# the variant changes no prediction. v1 was "≥ 35/50 wins", which counted ties as non-wins.
RULE_SHARE, RULE_MIN_DECISIVE, NEAR_MISS_SHARE = 0.70, 10, 0.60
RULE_VERSION = "v2: Δ>0, ≥70% of non-tied folds, ≥10 non-tied"
RULE_WINS, RULE_FOLDS = 35, 50  # v1, kept for the default-CV check
PACKAGES = ["numpy", "pandas", "scikit-learn", "lightgbm", "catboost", "xgboost"]


# ---------------------------------------------------------------- environment capture

def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _sh(*cmd):
    try:
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def device_profile():
    """Specs of this machine. Results from different devices are comparable in score, not in time."""
    prof = {
        "label": os.environ.get("MISSION_P_DEVICE") or platform.node().split(".")[0],
        "user": getpass.getuser(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "logical_cores": os.cpu_count(),
        "python": sys.version.split()[0],
        "thread_env": {k: os.environ[k] for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                                  "MKL_NUM_THREADS", "MISSION_P_FOLD_JOBS", "MISSION_P_MODEL_JOBS")
                       if k in os.environ},
    }
    if platform.system() == "Darwin":
        prof["cpu"] = _sh("sysctl", "-n", "machdep.cpu.brand_string")
        mem = _sh("sysctl", "-n", "hw.memsize")
        prof["ram_gb"] = round(int(mem) / 2**30, 1) if mem.isdigit() else None
        p, e = _sh("sysctl", "-n", "hw.perflevel0.physicalcpu"), _sh("sysctl", "-n", "hw.perflevel1.physicalcpu")
        if p.isdigit():
            prof["performance_cores"], prof["efficiency_cores"] = int(p), int(e) if e.isdigit() else 0
    else:
        try:
            import psutil
            prof["ram_gb"] = round(psutil.virtual_memory().total / 2**30, 1)
        except ImportError:
            pass
        prof["cpu"] = platform.processor()
    return prof


def package_versions():
    out = {}
    for p in PACKAGES:
        try:
            out[p] = importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError:
            pass
    return out


def git_state():
    dirty = [l[3:] for l in _sh("git", "status", "--porcelain").splitlines() if l]
    diff = _sh("git", "diff", "HEAD")
    return {
        "commit": _sh("git", "rev-parse", "HEAD"),
        "branch": _sh("git", "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty_files": dirty,
        "diff_sha256": hashlib.sha256(diff.encode()).hexdigest() if diff else None,
    }


def data_hashes(task):
    """Hash the labelled files of ONE task folder (the only files evaluate() reads)."""
    return {f"{task}/{p.name}": sha256_file(p) for p in sorted((DATA / task).glob("*.csv"))
            if p.name.startswith(("train_", "validation_"))}


def code_hashes():
    return {p.name: sha256_file(p) for p in sorted((ROOT / "src").glob("*.py"))}


def fold_signature(res):
    """Hash of (fold, flow_id) pairs: two runs with the same signature used identical folds."""
    s = "|".join(f"{f}:{i}" for f, i in zip(res["fold"], res["flow_id"]))
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def describe_model(model_factory):
    if model_factory is None:
        return None
    m = model_factory(0)
    d = {"repr": repr(m), "class": type(m).__name__}
    if hasattr(m, "get_params"):
        d["params"] = {k: repr(v) for k, v in m.get_params(deep=False).items()}
    if hasattr(m, "member_factories"):  # ensembles list their members' full settings
        d["members"] = [repr(f(0)) for f in m.member_factories]
    return d


# ---------------------------------------------------------------- run index

def load_index():
    if not INDEX.exists():
        return []
    return [json.loads(l) for l in INDEX.read_text().splitlines() if l.strip()]


def run_dir(run_id):
    return RESULTS / run_id


def load_champions():
    return json.loads(CHAMPIONS.read_text()) if CHAMPIONS.exists() else {}


def set_champion(task, run_id, reason):
    champs = load_champions()
    champs[task] = {"run_id": run_id, "since": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "reason": reason}
    CHAMPIONS.write_text(json.dumps(champs, indent=2) + "\n")


def load_folds(run_id, task):
    return pd.read_csv(run_dir(run_id) / task / "folds.csv")


def load_oof(run_id, task):
    return pd.read_csv(run_dir(run_id) / task / "oof.csv")


# ---------------------------------------------------------------- comparison

def compare(run_a, run_b, task):
    """Paired comparison of run_a (candidate) against run_b (reference) on one task."""
    ma = json.loads((run_dir(run_a) / "manifest.json").read_text())
    mb = json.loads((run_dir(run_b) / "manifest.json").read_text())
    if task not in ma["tasks"] or task not in mb["tasks"]:
        return {"comparable": False, "reason": f"{task} missing from one run"}
    if ma["tasks"][task]["fold_signature"] != mb["tasks"][task]["fold_signature"]:
        return {"comparable": False, "reason": "different folds (fold_signature differs); paired Δ is invalid"}
    fa, fb = load_folds(run_a, task), load_folds(run_b, task)
    d = fa["macro_f1"].values - fb["macro_f1"].values
    wins, losses = int((d > 1e-12).sum()), int((d < -1e-12).sum())
    n = len(d)
    decisive = wins + losses
    need = max(RULE_MIN_DECISIVE, int(np.ceil(RULE_SHARE * decisive)))  # wins needed among non-tied folds
    if d.mean() > 0 and decisive >= RULE_MIN_DECISIVE and wins >= RULE_SHARE * decisive:
        verdict = "BETTER"
    elif d.mean() < 0 and decisive >= RULE_MIN_DECISIVE and losses >= RULE_SHARE * decisive:
        verdict = "WORSE"
    elif d.mean() > 0 and decisive >= RULE_MIN_DECISIVE and wins >= NEAR_MISS_SHARE * decisive:
        verdict = "NEAR-MISS (inconclusive)"
    else:
        verdict = "INCONCLUSIVE"
    classes = [c[3:] for c in fa.columns if c.startswith("f1_")]
    per_class = {c: {"delta": float((fa[f"f1_{c}"] - fb[f"f1_{c}"]).mean()),
                     "wins": int((fa[f"f1_{c}"] > fb[f"f1_{c}"]).sum()),
                     "losses": int((fa[f"f1_{c}"] < fb[f"f1_{c}"]).sum())} for c in classes}

    # Flow-level flips: majority vote over repeats, per flow.
    oa, ob = load_oof(run_a, task), load_oof(run_b, task)
    def majority(o):
        return o.groupby("flow_id").agg(y_true=("y_true", "first"),
                                        pred=("y_pred", lambda s: s.value_counts().idxmax()),
                                        acc=("correct", "mean"))
    for o in (oa, ob):
        o["correct"] = o.y_true == o.y_pred
    va, vb = majority(oa), majority(ob)
    fixed = va.index[(va.pred == va.y_true) & (vb.pred != vb.y_true)]
    broken = va.index[(va.pred != va.y_true) & (vb.pred == vb.y_true)]

    # Confusion cells (pooled over folds) that moved most.
    labels = sorted(oa.y_true.unique())
    ca = confusion_matrix(oa.y_true, oa.y_pred, labels=labels)
    cb = confusion_matrix(ob.y_true, ob.y_pred, labels=labels)
    moves = []
    for i, t in enumerate(labels):
        for j, p in enumerate(labels):
            if i != j and ca[i, j] != cb[i, j]:
                moves.append({"true": t, "pred": p, "reference": int(cb[i, j]), "candidate": int(ca[i, j]),
                              "change": int(ca[i, j] - cb[i, j])})
    moves.sort(key=lambda m: m["change"])
    return {
        "comparable": True, "candidate": run_a, "reference": run_b, "n_folds": n,
        "delta_mean": float(d.mean()), "delta_std": float(d.std(ddof=1)) if n > 1 else 0.0,
        "wins": wins, "losses": losses, "ties": n - wins - losses, "wins_needed": need, "rule": RULE_VERSION,
        "delta_over_fold_std": float(d.mean() / fb["macro_f1"].std(ddof=1)) if n > 1 else None,
        "verdict": verdict, "per_class": per_class,
        "flows_fixed": [{"flow_id": f, "app": va.y_true[f], "was": vb.pred[f]} for f in fixed],
        "flows_broken": [{"flow_id": f, "app": va.y_true[f], "now": va.pred[f]} for f in broken],
        "confusion_improved": [m for m in moves if m["change"] < 0][:5],
        "confusion_worsened": [m for m in moves if m["change"] > 0][::-1][:5],
        "same_device": ma["device"].get("label") == mb["device"].get("label"),
    }


# ---------------------------------------------------------------- checks

def run_checks(exp, name, manifest, results, comparisons):
    checks = []
    def add(level, code, msg):
        checks.append({"level": level, "code": code, "message": msg})

    if manifest["git"]["dirty_files"]:
        add("warn", "dirty-tree", f"Uncommitted changes in {len(manifest['git']['dirty_files'])} file(s); "
            "the commit alone does not reproduce this run (code hashes are recorded).")
    for task, res in results.items():
        bad = FORBIDDEN_FEATURES & set(res["features"])
        if bad:
            add("error", "forbidden-feature", f"{task} uses {sorted(bad)} (identifier/leakage column).")
        others = [k for k in manifest["tasks"][task]["data_sha256"] if not k.startswith(task + "/")]
        if others and task == "task2_realtime_prefix5":
            add("error", "task-isolation", f"{task} reads files from another task (condition 2): {others}")
        elif others:
            add("info", "cross-task-input", f"{task} also reads {others}; allowed (condition 2 restricts Task 2 "
                "only) but must be disclosed in the report.")
        fp = res["fold_per_class"]
        for k, c in enumerate(res["labels"]):
            zeros = int((fp[:, k] == 0).sum())
            if zeros >= 5:
                add("info", "zero-f1-folds", f"{task}: {c} has F1 = 0 in {zeros}/{len(fp)} folds.")
        noisy = max(res["per_class_std"], key=res["per_class_std"].get)
        if res["per_class_std"][noisy] > 0.25:
            add("info", "noise-driver", f"{task}: {noisy} fold std {res['per_class_std'][noisy]:.2f} drives "
                "most of the macro F1 noise.")
        if res["cv"]["n_splits"] * res["cv"]["n_repeats"] != RULE_FOLDS:
            add("warn", "non-default-cv", f"{task}: {res['cv']} is not the default 5×10; the 35/50 rule is scaled.")
    for task, c in comparisons.items():
        if not c.get("comparable"):
            add("warn", "not-comparable", f"{task}: {c.get('reason')}")
            continue
        if c["verdict"].startswith("NEAR-MISS"):
            add("warn", "near-miss", f"{task}: Δ {c['delta_mean']:+.4f} with {c['wins']} wins / {c['losses']} losses; "
                "adopting it would override the rule, so justify it in the experiment log.")
        if c["reference"] and not c["same_device"]:
            add("info", "other-device", f"{task}: reference ran on another device; compare scores, not seconds.")
        if abs(c["delta_mean"]) < 1e-12 and c["ties"] == c["n_folds"]:
            add("info", "identical", f"{task}: fold scores identical to {c['reference']}.")
    # Same code + data + config as an earlier run → reproducibility check.
    for prev in load_index():
        if prev.get("fingerprint") == manifest["fingerprint"]:
            same = all(abs(prev["scores"].get(t, {}).get("macro_mean", -1) - r["macro_mean"]) <= 5e-7  # index stores 6 decimals
                       for t, r in results.items())
            add("info" if same else "warn", "reproduction",
                f"Same code/data/config as {prev['run_id']}: scores {'identical' if same else 'DIFFER (nondeterminism)'}"
                f"{'' if prev['device'] == manifest['device']['label'] else ' across devices'}.")
            break
    if not list(EXPERIMENTS.glob(f"{exp}_*.md")):
        add("todo", "missing-log", f"No experiments/{exp}_*.md yet; write it (see experiments/TEMPLATE.md).")
    return checks


# ---------------------------------------------------------------- report

def _fmt_report(run_id, manifest, results, comparisons, checks):
    L = [f"# Run {run_id}", "",
         f"- **Experiment:** {manifest['experiment']} ({manifest['name']})",
         f"- **Question:** {manifest['question'] or '—'}",
         f"- **When:** {manifest['started_utc']} → {manifest['finished_utc']} ({manifest['wall_seconds']:.1f} s)",
         f"- **Device:** {manifest['device'].get('label')} · {manifest['device'].get('cpu')} · "
         f"{manifest['device'].get('logical_cores')} cores · {manifest['device'].get('ram_gb')} GB · "
         f"Python {manifest['device']['python']}",
         f"- **Git:** `{manifest['git']['commit'][:7]}`" + (" (dirty)" if manifest["git"]["dirty_files"] else ""),
         f"- **Config:** `{json.dumps(manifest['config'])}`", ""]
    if manifest["notes"]:
        L += [manifest["notes"], ""]
    L += ["## Scores (repeated stratified CV)", "",
          "| Task | Macro F1 | Fold std | " + " | ".join(results[next(iter(results))]["labels"]) + " |",
          "|---|---|---|" + "---|" * len(results[next(iter(results))]["labels"])]
    for t, r in results.items():
        L.append(f"| {t} | **{r['macro_mean']:.4f}** | {r['macro_std']:.4f} | " +
                 " | ".join(f"{r['per_class_mean'][c]:.3f}" for c in r["labels"]) + " |")
    for t, c in comparisons.items():
        L += ["", f"## {t} vs `{c.get('reference')}`", ""]
        if not c.get("comparable"):
            L.append(f"Not comparable: {c['reason']}")
            continue
        L += [f"**{c['verdict']}**: Δ {c['delta_mean']:+.4f} (paired std {c['delta_std']:.4f}), "
              f"wins {c['wins']}, losses {c['losses']}, ties {c['ties']} (need ≥70% of {c['wins'] + c['losses']} non-tied, "
              f"min 10; rule {c.get('rule', 'v1')}). "
              f"Δ is {c['delta_over_fold_std']:.2f}× the reference fold std.", "",
              "| Class | Δ F1 | Wins | Losses |", "|---|---|---|---|"]
        for k, v in c["per_class"].items():
            L.append(f"| {k} | {v['delta']:+.3f} | {v['wins']} | {v['losses']} |")
        if c["flows_fixed"] or c["flows_broken"]:
            L += ["", f"Flows (majority vote over repeats): fixed {len(c['flows_fixed'])}, "
                  f"broken {len(c['flows_broken'])}."]
            for f in c["flows_fixed"][:8]:
                L.append(f"- fixed `{f['flow_id']}` ({f['app']}, was {f['was']})")
            for f in c["flows_broken"][:8]:
                L.append(f"- broken `{f['flow_id']}` ({f['app']}, now {f['now']})")
        for key, word in (("confusion_improved", "Fewer"), ("confusion_worsened", "More")):
            for m in c[key]:
                L.append(f"- {word} {m['true']} → {m['pred']}: {m['reference']} → {m['candidate']}")
    L += ["", "## Checks", ""]
    L += [f"- **{c['level']}** `{c['code']}`: {c['message']}" for c in checks] or ["- none"]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- main entry

def record_run(exp, name, results, question="", config=None, model_factory=None, feature_fn=None,
               reference="champion", notes="", started=None):
    """Write a run folder for `results` ({task: evaluate(...) output}) and return its run_id.

    reference: "champion" (default: current champion per task), a run_id, or None.
    """
    finished = datetime.now(timezone.utc)
    started = started or finished
    RESULTS.mkdir(exist_ok=True)
    run_id = f"{finished:%Y%m%dT%H%M%SZ}_{exp}_{name}"
    out = run_dir(run_id)
    out.mkdir()

    tasks_meta = {}
    for task, r in results.items():
        (out / task).mkdir()
        cv = r["cv"]
        folds = pd.DataFrame({"fold": range(len(r["fold_macro"])),
                              "repeat": np.arange(len(r["fold_macro"])) // cv["n_splits"],
                              "macro_f1": r["fold_macro"], "seconds": r["fold_seconds"]})
        for k, c in enumerate(r["labels"]):
            folds[f"f1_{c}"] = r["fold_per_class"][:, k]
        folds.to_csv(out / task / "folds.csv", index=False)
        pd.DataFrame({"fold": r["fold"], "flow_id": r["flow_id"], "y_true": r["y_true"],
                      "y_pred": r["y_pred"]}).to_csv(out / task / "oof.csv", index=False)
        cm = confusion_matrix(r["y_true"], r["y_pred"], labels=r["labels"])
        pd.DataFrame(cm, index=r["labels"], columns=r["labels"]).to_csv(out / task / "confusion.csv")
        summary = {k: (float(r[k]) if np.isscalar(r[k]) else r[k]) for k in
                   ("macro_mean", "macro_std", "repeat_std", "per_class_mean", "per_class_std")}
        summary["per_class_mean"] = {k: float(v) for k, v in summary["per_class_mean"].items()}
        summary["per_class_std"] = {k: float(v) for k, v in summary["per_class_std"].items()}
        summary["seconds_total"] = float(r["fold_seconds"].sum())
        (out / task / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        tasks_meta[task] = {"n_flows": r["n_flows"], "features": r["features"], "cv": cv,
                            "fold_signature": fold_signature(r),
                            "data_sha256": {**data_hashes(task),
                                            **{f: sha256_file(DATA / f) for f in r.get("extra_data", [])}}}

    config = config or {}
    config.setdefault("features_fn", getattr(feature_fn, "__name__", None))
    code = code_hashes()
    fp_src = json.dumps({"code": code, "tasks": {t: {k: v for k, v in m.items()} for t, m in tasks_meta.items()},
                         "config": config}, sort_keys=True, default=str)
    manifest = {
        "run_id": run_id, "experiment": exp, "name": name, "question": question, "notes": notes,
        "started_utc": started.isoformat(timespec="seconds"), "finished_utc": finished.isoformat(timespec="seconds"),
        "wall_seconds": (finished - started).total_seconds(),
        "argv": sys.argv, "config": config, "model": describe_model(model_factory),
        "device": device_profile(), "packages": package_versions(), "git": git_state(),
        "code_sha256": code, "tasks": tasks_meta,
        "fingerprint": hashlib.sha256(fp_src.encode()).hexdigest()[:16],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")

    comparisons = {}
    champs = load_champions()
    for task in results:
        ref = champs.get(task, {}).get("run_id") if reference == "champion" else reference
        if ref and ref != run_id and run_dir(ref).exists():
            comparisons[task] = compare(run_id, ref, task)
    (out / "comparison.json").write_text(json.dumps(comparisons, indent=2, default=str) + "\n")
    checks = run_checks(exp, name, manifest, results, comparisons)
    (out / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    (out / "report.md").write_text(_fmt_report(run_id, manifest, results, comparisons, checks))

    sums = {p.relative_to(out).as_posix(): sha256_file(p) for p in sorted(out.rglob("*"))
            if p.is_file() and p.name != "checksums.json"}
    (out / "checksums.json").write_text(json.dumps(sums, indent=2) + "\n")

    entry = {"run_id": run_id, "experiment": exp, "name": name, "question": question,
             "finished_utc": manifest["finished_utc"], "device": manifest["device"]["label"],
             "commit": manifest["git"]["commit"][:7], "dirty": bool(manifest["git"]["dirty_files"]),
             "fingerprint": manifest["fingerprint"],
             "scores": {t: {"macro_mean": round(float(r["macro_mean"]), 6), "macro_std": round(float(r["macro_std"]), 6)}
                        for t, r in results.items()},
             "verdicts": {t: {"vs": c.get("reference"), "verdict": c.get("verdict"),
                              "delta": c.get("delta_mean"), "wins": c.get("wins")} for t, c in comparisons.items()},
             "warnings": [c["code"] for c in checks if c["level"] in ("warn", "error")]}
    with INDEX.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    print((out / "report.md").read_text())
    print(f"→ results/{run_id}/")
    return run_id
