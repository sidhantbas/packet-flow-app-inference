"""Query and audit logged runs (all local).

    .venv/bin/python src/runs.py status               session digest: champions, recent runs, open TODOs, warnings
    .venv/bin/python src/runs.py list [N]             last N runs (default 15)
    .venv/bin/python src/runs.py show RUN             print a run's report.md
    .venv/bin/python src/runs.py compare RUN_A RUN_B  paired comparison of A (candidate) vs B (reference)
    .venv/bin/python src/runs.py verify [RUN|all]     recompute metrics from oof.csv and check every hash
    .venv/bin/python src/runs.py champion TASK RUN "reason"   set the reference run for a task
    .venv/bin/python src/runs.py device               show this machine's profile
    .venv/bin/python src/runs.py rejudge              re-evaluate every logged comparison under the current rule

RUN may be a full run_id or any unique substring of one (e.g. "006_drop_timing").
"""
import json
import re
import sys
from datetime import date

import numpy as np
from sklearn.metrics import f1_score

import runlog
from runlog import (CHAMPIONS, ROOT, compare, data_hashes, device_profile, load_champions, load_folds,
                    load_index, load_oof, run_dir, set_champion, sha256_file)

DEADLINE = date(2026, 10, 23)
TASKS = ["task1_static", "task2_realtime_prefix5"]


def resolve(q):
    ids = [e["run_id"] for e in load_index()]
    if q in ids:
        return q
    hits = [i for i in ids if q in i]
    if len(hits) != 1:
        sys.exit(f"'{q}' matches {len(hits)} runs: {hits[:5]}")
    return hits[0]


def cmd_list(n="15"):
    rows = load_index()[-int(n):]
    print(f"{'run_id':52s} {'task1':>7s} {'task2':>7s}  verdicts / warnings")
    for e in rows:
        s = e["scores"]
        v = "; ".join(f"{t[:5]} {x['verdict']} {x['delta']:+.3f} ({x['wins']})" for t, x in e["verdicts"].items()
                      if x.get("verdict"))
        w = (" ⚠ " + ",".join(e["warnings"])) if e["warnings"] else ""
        print(f"{e['run_id']:52s} {s.get(TASKS[0], {}).get('macro_mean', float('nan')):7.4f} "
              f"{s.get(TASKS[1], {}).get('macro_mean', float('nan')):7.4f}  {v}{w}")


def cmd_show(q):
    print((run_dir(resolve(q)) / "report.md").read_text())


def cmd_compare(a, b):
    a, b = resolve(a), resolve(b)
    for t in TASKS:
        c = compare(a, b, t)
        if not c.get("comparable"):
            print(f"{t}: not comparable ({c.get('reason')})")
            continue
        print(f"{t}: {c['verdict']}  Δ {c['delta_mean']:+.4f}  wins {c['wins']}/{c['n_folds']} "
              f"(need {c['wins_needed']})  losses {c['losses']}")
        print("   per class: " + ", ".join(f"{k} {v['delta']:+.3f}" for k, v in c["per_class"].items()))
        print(f"   flows fixed {len(c['flows_fixed'])}, broken {len(c['flows_broken'])}")


def verify_run(run_id):
    """Return a list of problems (empty = verified)."""
    out, problems = run_dir(run_id), []
    sums = json.loads((out / "checksums.json").read_text())
    for rel, h in sums.items():
        p = out / rel
        if not p.exists():
            problems.append(f"missing {rel}")
        elif sha256_file(p) != h:
            problems.append(f"hash mismatch {rel}")
    manifest = json.loads((out / "manifest.json").read_text())
    for task, meta in manifest["tasks"].items():
        folds, oof = load_folds(run_id, task), load_oof(run_id, task)
        labels = sorted(oof.y_true.unique())
        for i, g in oof.groupby("fold"):
            m = f1_score(g.y_true, g.y_pred, average="macro")
            if abs(m - folds.macro_f1[i]) > 1e-9:
                problems.append(f"{task} fold {i}: recomputed {m:.6f} ≠ logged {folds.macro_f1[i]:.6f}")
                break
        summ = json.loads((out / task / "summary.json").read_text())
        if abs(folds.macro_f1.mean() - summ["macro_mean"]) > 1e-9:
            problems.append(f"{task}: summary mean does not match folds.csv")
        if len(oof) != meta["n_flows"] * meta["cv"]["n_repeats"]:
            problems.append(f"{task}: oof has {len(oof)} rows, expected {meta['n_flows'] * meta['cv']['n_repeats']}")
        changed = [k for k, h in meta["data_sha256"].items() if sha256_file(runlog.DATA / k) != h]
        if changed:
            problems.append(f"{task}: data files changed since this run: {changed}")
    return problems


def cmd_verify(q="all"):
    ids = [e["run_id"] for e in load_index()] if q == "all" else [resolve(q)]
    bad = 0
    for r in ids:
        p = verify_run(r)
        bad += bool(p)
        print(f"{'OK  ' if not p else 'FAIL'} {r}" + "".join(f"\n     - {x}" for x in p))
    print(f"{len(ids) - bad}/{len(ids)} runs verified")


def cmd_champion(task, q, reason):
    r = resolve(q)
    set_champion(task, r, reason)
    print(f"{task} champion → {r}")


def cmd_rejudge():
    """Recompute each logged comparison with the current rule and list verdicts that change."""
    changed = 0
    for e in load_index():
        for t, v in e["verdicts"].items():
            if not v.get("vs"):
                continue
            c = compare(e["run_id"], v["vs"], t)
            if c.get("comparable") and c["verdict"] != v["verdict"]:
                changed += 1
                print(f"{e['run_id']} {t}: {v['verdict']} → {c['verdict']}  "
                      f"(Δ {c['delta_mean']:+.4f}, W/L/T {c['wins']}/{c['losses']}/{c['ties']})")
    print(f"{changed} verdict(s) change under {runlog.RULE_VERSION}")


def cmd_device():
    print(json.dumps(device_profile(), indent=2))


def cmd_status():
    idx = load_index()
    print(f"packet-flow-app-inference — {date.today()} — {(DEADLINE - date.today()).days} days to the {DEADLINE} deadline")
    print(f"Device: {device_profile()['label']}")
    dirty = runlog.git_state()["dirty_files"]
    print(f"Git: {runlog.git_state()['commit'][:7]}" + (f", {len(dirty)} uncommitted file(s)" if dirty else ", clean"))
    print("\nChampions (reference runs for comparisons):")
    champs = load_champions()
    for t in TASKS:
        c = champs.get(t)
        if not c:
            print(f"  {t}: none set")
            continue
        s = next((e["scores"][t] for e in idx if e["run_id"] == c["run_id"]), {})
        print(f"  {t}: {s.get('macro_mean', float('nan')):.4f} ± {s.get('macro_std', float('nan')):.4f}  "
              f"{c['run_id']}  ({c['reason']})")
    print("\nRecent runs:")
    for e in idx[-5:]:
        v = "; ".join(f"{t[:5]} {x['verdict']}" for t, x in e["verdicts"].items() if x.get("verdict")) or "no reference"
        print(f"  {e['run_id']}: {v}" + (f"  ⚠ {','.join(e['warnings'])}" if e["warnings"] else ""))
    todo = ROOT / "TODO.md"
    if todo.exists():
        text = todo.read_text()
        nxt = re.search(r"^\*\*Next:\*\*(.*)$", text, re.M)
        open_items = re.findall(r"^\s*- \[[ .]\] (.*)$", text, re.M)
        print(f"\nNext: {nxt.group(1).strip() if nxt else '—'}")
        print(f"Open TODO items: {len(open_items)}")
        for item in open_items[:6]:
            print(f"  - {item[:110]}")
    missing = sorted({e["experiment"] for e in idx} - {p.name[:3] for p in (ROOT / "experiments").glob("*.md")})
    if missing:
        print(f"\n⚠ Runs without an experiments/*.md log: {', '.join(missing)}")
    log = ROOT / "CHANGELOG.md"
    if log.exists():
        heads = re.findall(r"^## (.*)$", log.read_text(), re.M)
        if heads:
            print(f"Last changelog entry: {heads[-1]}")


if __name__ == "__main__":
    cmds = {"status": cmd_status, "list": cmd_list, "show": cmd_show, "compare": cmd_compare,
            "verify": cmd_verify, "champion": cmd_champion, "device": cmd_device,
            "rejudge": cmd_rejudge}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](*sys.argv[2:])
