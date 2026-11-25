"""Generate EXPERIMENTS.md, the central index of every experiment, and src/README.md, the code catalogue, from:
  - the `experiment:` block in each experiments/NNN_*.md front matter (id, tasks, lever, status, verdict, production role),
  - results/ (run folders per experiment), results/champions.json (current reference runs and their CV macro F1),
  - submissions/uploads.csv (leaderboard history), TODO.md (the **Next:** line).
Never edit EXPERIMENTS.md or src/README.md by hand; change the sources and regenerate.

Usage: .venv/bin/python src/build_experiments_index.py          (write EXPERIMENTS.md and src/README.md)
       .venv/bin/python src/build_experiments_index.py --check  (exit 1 if either is out of date)
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "EXPERIMENTS.md"
STATUS = {"adopted": "✅ adopted", "inconclusive": "🟡 inconclusive", "rejected": "❌ rejected", "measured": "📏 measured",
          "tooling": "🛠️ tooling", "submission": "📮 submission", "unfinished": "⏸️ unfinished", "proposed": "🔵 proposed"}
LEVERS = ["evaluation", "features", "model", "imbalance", "hierarchy", "decision", "data", "diagnostic", "tooling", "submission"]
LEVER_TEXT = {"evaluation": "how we measure (CV protocol, noise, twin-aware folds)", "features": "inputs and derived columns",
              "model": "learners, ensembles, experts, settings", "imbalance": "class weights, resampling, synthetic flows",
              "hierarchy": "gates, pair specialists, verifiers, overrides", "decision": "thresholds, multipliers, batch labelling",
              "data": "extra or cleaned training data (captures, public data, self-training)",
              "diagnostic": "audits and measurements, no model change", "tooling": "infrastructure", "submission": "submission files"}
TASKS = {"task1": "T1", "task2": "T2"}
T1, T2 = "task1_static", "task2_realtime_prefix5"


def logs():
    out = []
    for p in sorted((ROOT / "experiments").glob("[0-9][0-9][0-9]_*.md")):
        t = p.read_text()
        fm = yaml.safe_load(t[4:t.index("\n---\n", 4)])
        e = fm["experiment"]
        out.append({**e, "title": re.sub(r"^\d{3}\s*[:—-]\s*", "", str(fm["title"])).strip(),
                    "date": str(fm.get("created") or fm.get("date")), "file": p.name})
    return out


def runs_per_experiment():
    c = Counter()
    for d in (ROOT / "results").iterdir():
        m = re.match(r"\d{8}T\d{6}Z_(\d{3})_", d.name)
        if m and d.is_dir():
            c[m.group(1)] += 1
    return c


def scripts(eid):
    return sorted(p.name for p in (ROOT / "src").glob(f"exp{eid}*.py"))


def evidence(eid):
    return sorted(p.name for p in (ROOT / "experiments").glob(f"{eid}_evidence*"))


def champions():
    ch = json.loads((ROOT / "results/champions.json").read_text())
    rows = {}
    for task, v in ch.items():
        s = json.loads((ROOT / "results" / v["run_id"] / task / "summary.json").read_text())
        rows[task] = (v["run_id"], s["macro_mean"], s.get("macro_std"))
    return rows


def link_list(eid):
    parts = [f"[`{s}`](src/{s})" for s in scripts(eid)] + [f"[evidence](experiments/{e})" for e in evidence(eid)]
    return " · ".join(parts)


def esc(s):
    return str(s).replace("|", "\\|")


def build():
    L = logs()
    ids = [e["id"] for e in L]
    runs = runs_per_experiment()
    ch = champions()
    ups = list(csv.DictReader((ROOT / "submissions/uploads.csv").open()))
    nxt = next((l for l in (ROOT / "TODO.md").read_text().splitlines() if l.startswith("**Next:**")), "")
    st = Counter(e["status"] for e in L)
    by = {e["id"]: e for e in L}
    missing = [f"{n:03d}" for n in range(1, int(max(ids)) + 1) if f"{n:03d}" not in ids]

    o = []
    w = o.append
    w("---")
    w("title: Experiment index")
    w("creator: sidhantbas")
    w("description: Central index of every packet-flow-app-inference experiment, generated from the experiment logs' front matter, the run "
      "folders, the champion runs and the upload history. Do not edit by hand.")
    w("---")
    w("")
    w("# Experiment index")
    w("")
    w("> **Generated file.** Regenerate with `.venv/bin/python src/build_experiments_index.py` after changing an experiment log's")
    w("> front matter, `results/`, `submissions/uploads.csv` or the TODO **Next:** line. Check freshness with `--check`.")
    w("")
    w(f"**{len(L)} experiments** (001-{max(ids)}" + (f"; number{'s' if len(missing) > 1 else ''} {', '.join(missing)} unused" if missing else "")
      + f"), **{sum(runs.values())} logged CV runs** in `results/`. Status: "
      + ", ".join(f"{STATUS[k]} {st[k]}" for k in STATUS if st[k]) + ".")
    w("")
    w("Every experiment follows the same discipline: a protocol committed before any run, paired comparison on identical folds,")
    w("rule v2 for adoption (Δ > 0, ≥ 70% of non-tied folds won, ≥ 10 non-tied, repeated on more seeds), and an immutable,")
    w("hash-verified run folder per CV run (`.venv/bin/python src/runs.py verify`). Rules: [AGENTS.md](AGENTS.md). Findings by")
    w("theme: [FINDINGS.md](FINDINGS.md).")
    w("")
    w("## 1. Current production")
    w("")
    w("| Task | Model (`models.TASK_MODELS`) | Features (`cv.TASK_FEATURES`) | Reference run | CV macro F1 (mean ± fold SD) |")
    w("|---|---|---|---|---|")
    sys.path.insert(0, str(ROOT / "src"))
    from cv import TASK_FEATURES  # noqa: E402
    from models import TASK_MODELS  # noqa: E402
    for task in (T1, T2):
        rid, m, sd = ch[task]
        eid = re.match(r"\d{8}T\d{6}Z_(\d{3})_", rid).group(1)
        w(f"| {task} | `{TASK_MODELS[task].__name__}` (experiment [{eid}](experiments/{by[eid]['file']})) | "
          f"`{TASK_FEATURES[task].__name__}` | [`{rid}`](results/{rid}) | {m:.3f}" + (f" ± {sd:.3f}" if sd else "") + " |")
    w("")
    w("## 2. Leaderboard history (Final Test Phase, 81 test flows)")
    w("")
    w("Recorded as information only: no model or file was ever chosen by these scores.")
    w("")
    w("| Upload | Date | Task 1 model | Task 2 model | Task 1 | Task 2 | Total | Note |")
    w("|---:|---|---|---|---:|---:|---:|---|")
    for u in ups:
        f = u["file"]
        fl = f"[{f.split('/')[-2]}]({f})" if f.startswith("submissions/") else f
        w(f"| {u['upload']} | {u['date']} | {esc(u['task1_model'])} | {u['task2_model']} | {u['task1_macro_f1'] or '—'} | "
          f"{u['task2_macro_f1'] or '—'} | **{u['total']}** | {' · '.join(x for x in (esc(u['note']), fl) if x)} |")
    w("")
    w("## 3. The adopted path")
    w("")
    w("Every component in production, in the order it was adopted. Later experiments build on earlier ones.")
    w("")
    w("| ID | Date | Task | Component in production | Evidence |")
    w("|---|---|---|---|---|")
    for e in L:
        if e["status"] == "adopted":
            w(f"| [{e['id']}](experiments/{e['file']}) | {e['date']} | {'+'.join(TASKS[t] for t in e['tasks'])} | "
              f"{esc(e.get('production', ''))} | {esc(e['verdict'])} |")
    w("")
    w("## 4. All experiments")
    w("")
    w("| ID | Date | Task | Lever | Status | Result | Runs | Code and evidence |")
    w("|---|---|---|---|---|---|---:|---|")
    for e in L:
        w(f"| [{e['id']}](experiments/{e['file']}) | {e['date']} | {'+'.join(TASKS[t] for t in e['tasks'])} | {e['lever']} | "
          f"{STATUS[e['status']]} | **{esc(e['title'])}**: {esc(e['verdict'])} | {runs.get(e['id'], 0) or '—'} | {link_list(e['id'])} |")
    w("")
    w("## 5. By lever")
    w("")
    w("| Lever | What it covers | " + " | ".join(STATUS[k] for k in STATUS) + " |")
    w("|---|---|" + "---|" * len(STATUS))
    grid = defaultdict(list)
    for e in L:
        grid[(e["lever"], e["status"])].append(e["id"])
    for lv in LEVERS:
        cells = [", ".join(f"[{i}](experiments/{by[i]['file']})" for i in grid[(lv, k)]) or "—" for k in STATUS]
        w(f"| **{lv}** | {LEVER_TEXT[lv]} | " + " | ".join(cells) + " |")
    w("")
    w("## 6. Inconclusive, unfinished and proposed")
    w("")
    w("Positive but unconfirmed results, unfinished runs and frozen proposals. Several are closed by later decisions (for example,")
    w("TabPFN is excluded as a pretrained model, and 065/075/077 fed into the 089 bundle); the logs say so.")
    w("")
    for e in L:
        if e["status"] in ("inconclusive", "unfinished", "proposed"):
            w(f"- [{e['id']}](experiments/{e['file']}) **{esc(e['title'])}** ({STATUS[e['status']]}): {e['verdict']}")
    w("")
    if nxt:
        w(f"From [TODO.md](TODO.md): {nxt.replace('**Next:**', '**Next:**', 1)}")
        w("")
    w("Recommended next experiments and unresolved questions: [evidence handoff](docs/evidence-handoff/README.md), sections 8, B")
    w("and C.")
    w("")
    return "\n".join(o)


SRC_OUT = ROOT / "src/README.md"
LIBRARY = {
    "cv.py": "Data loading (`load_task`), feature functions (`TASK_FEATURES`) and repeated stratified CV (`evaluate`); each task reads only its own folder",
    "models.py": "Every model and expert; the production registry `TASK_MODELS`",
    "runlog.py": "`record_run`: immutable, hashed run folders in `results/`, paired comparison with the champion, rule v2 verdict",
    "runs.py": "Command line for runs: `status`, `verify`, `compare`, `champion`, `rejudge`",
    "make_submission.py": "Builds `submissions/submission.json` and `.zip` from the production models",
    "make_final_candidate.py": "Builds and validates a submission package (rebuild check, official loader, comparison with earlier uploads)",
    "make_validation_submissions.py": "Validation Phase files from train-only models, scored with the official `evaluate()`",
    "evaluation_metric.py": "The organisers' macro F1, imported unchanged",
    "baseline.py": "Reproduces the official RandomForest baseline",
    "ceilings.py": "Upper bound on macro F1 when identical feature vectors must share one prediction (experiment 004)",
    "flowcheck.py": "Flow-level paired check for facebook/instagram-targeted Task 1 changes (pre-registered in 067)",
}
CAPTURE = {
    "capture_session.py": "Logs one capture session with exact UTC times (run beside tcpdump)",
    "capture_extract.py": "Builds challenge-style flow features from our own pcap captures",
    "capture_checks.py": "Gates 1 and 2 that captured flows must pass before any training use",
    "test_capture_extract.py": "Self-test of `capture_extract.py` on synthetic captures",
}
TOOLS = {
    "build_experiments_index.py": "Generates `EXPERIMENTS.md` and this file; `--check` fails when either is out of date",
    "check_links.py": "Checks every relative link in tracked Markdown",
    "migrate_experiment_frontmatter.py": "One-time migration (2026-10-12) that added the `experiment:` block to every log",
}


FLOWKIT = {
    "__init__.py": "Package entry: `DecisionPipeline`, `from_spec`",
    "bases.py": "Named base models (`softvote`, `softvote_unweighted`, `task2_production`)",
    "calibration.py": "Calibration on cross-validated probabilities (`none`, `sigmoid`, `isotonic`)",
    "counts.py": "Count-constrained labelling (`quota_assign`, `share_counts`, `label_counts`)",
    "pipeline.py": "`DecisionPipeline` (base, calibration, counts) and spec strings such as `base=softvote,cal=sigmoid,counts=shares`",
    "features.py": "Ratio, rate and coefficient-of-variation features for either task (`ratio_features`)",
    "lookup.py": "Exact-signature lookup: label distribution of identical openings, leave-one-out on training rows (`ExactLookup`)",
    "members.py": "Ensemble members by name (LightGBM, XGBoost, RF, ExtraTrees, kNN-Manhattan) and nested Optuna tuning (`tune`)",
    "postprocess.py": "Prior correction (`prior_correct`) and Gaussian temporal smoothing within a batch (`temporal_smooth`)",
    "swap.py": "Count-preserving consensus pair swap between two views (`consensus_pair_swap`)",
}


def build_src():
    files = sorted(p.name for p in (ROOT / "src").glob("*.py"))
    L = {e["id"]: e for e in logs()}
    importers = defaultdict(list)
    for f in files:
        for m in re.findall(r"^from (exp\d{3}\w*) import|^import (exp\d{3}\w*)", (ROOT / "src" / f).read_text(), re.M):
            importers[(m[0] or m[1]) + ".py"].append(f)
    o = []
    w = o.append
    w("---")
    w("title: Source code catalogue")
    w("creator: sidhantbas")
    w("description: Every Python file in src/ by role, generated by build_experiments_index.py. Do not edit by hand.")
    w("---")
    w("")
    w("# Source code catalogue")
    w("")
    w("> **Generated file** (`.venv/bin/python src/build_experiments_index.py`). All code stays in this one folder on purpose:")
    w("> runners are run as `.venv/bin/python src/<file>.py` from the repository root and import the library and each other")
    w("> by module name, and every run folder in `results/` records these paths.")
    w("")
    for title, table in (("Library (production and evaluation)", LIBRARY), ("Capture pipeline (experiment 042)", CAPTURE),
                         ("Repository tools", TOOLS)):
        w(f"## {title}")
        w("")
        w("| File | Role |")
        w("|---|---|")
        for f, role in table.items():
            if f in files:
                w(f"| [`{f}`]({f}) | {role} |")
        w("")
    w("## Reusable components (`flowkit/`, since experiment 102)")
    w("")
    w("Small composable parts with no experiment logic. Runners import them; a new pipeline is a spec string, not new code.")
    w("")
    w("| File | Role |")
    w("|---|---|")
    for f in sorted(p.name for p in (ROOT / "src/flowkit").glob("*.py")):
        w(f"| [`flowkit/{f}`](flowkit/{f}) | {FLOWKIT.get(f, '')} |")
    w("")
    w("## Experiment runners")
    w("")
    w("One or more runners per experiment, named `expNNN_*.py`. The log holds the frozen protocol and the results.")
    w("")
    w("| Runner | Experiment | Status | Imported by |")
    w("|---|---|---|---|")
    runners = [f for f in files if re.match(r"exp\d{3}", f)]
    for f in runners:
        eid = f[3:6]
        e = L.get(eid)
        exp = f"[{eid}](../experiments/{e['file']})" if e else eid
        st = STATUS[e["status"]] if e else "—"
        w(f"| [`{f}`]({f}) | {exp} | {st} | {', '.join(f'`{x}`' for x in sorted(importers.get(f, []))) or '—'} |")
    w("")
    other = [f for f in files if f not in LIBRARY and f not in CAPTURE and f not in TOOLS and f not in runners]
    if other:
        w("## Other")
        w("")
        for f in other:
            w(f"- [`{f}`]({f})")
        w("")
    return "\n".join(o)


def main():
    outputs = ((OUT, build()), (SRC_OUT, build_src()))
    if "--check" in sys.argv:
        stale = [p.relative_to(ROOT).as_posix() for p, text in outputs if not (p.exists() and p.read_text() == text)]
        print("EXPERIMENTS.md and src/README.md are up to date" if not stale
              else f"OUT OF DATE: {', '.join(stale)}: run src/build_experiments_index.py")
        sys.exit(0 if not stale else 1)
    for p, text in outputs:
        p.write_text(text)
        print(f"wrote {p.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
