"""Build and validate a submission package from the production models without touching existing artifacts (written for
experiment 098, stage 4; used again for the 100 adoption).

Usage: .venv/bin/python src/make_final_candidate.py [--out submissions/final-2026-10-12-089-014]
Fits the production models (models.TASK_MODELS with cv.TASK_FEATURES) on train + validation, predicts the test features, builds
the files twice (reproducibility), validates them and compares them with the ranked entry and the best-scoring upload.
"""
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

from cv import DATA, TASK_FEATURES, TASKS, load_task
from exp005_checks import official_module
from make_submission import ALLOWED, fit_predict, load_test, write_submission
from models import TASK_MODELS

ROOT = Path(__file__).resolve().parent.parent
REFERENCES = {"production-089-bundle (ranked entry, 87.24)": "submissions/production-089-bundle/submission.json",
              "best-88.11-production-084 (best score)": "submissions/best-88.11-production-084/submission.json"}
FORBIDDEN_COLUMNS = ("flow_id", "split", "start_rel", "server_port")
CODE = ["src/models.py", "src/cv.py", "src/make_submission.py", "src/make_final_candidate.py", "requirements.txt"]
MODEL_NOTES = {"task1_bundle": "089 B1",
               "task1_cross_task": "100 FB: the 089 bundle plus an inner copy of the 014 Task 2 model on the Task 2 file's 12 no-timing columns",
               "task2_model": "014"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build():
    return {t: fit_predict(t)[0] for t in TASKS}


def main():
    out = ROOT / (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "submissions/final-2026-10-12-089-014")
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_rebuild"
    tmp.mkdir(exist_ok=True)
    preds = build()
    write_submission(preds, out / "submission.json", out / "submission.zip")
    write_submission(build(), tmp / "submission.json", tmp / "submission.zip")
    reproducible = (out / "submission.json").read_bytes() == (tmp / "submission.json").read_bytes()
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()

    checks = {"reproducible_rebuild_json_identical": reproducible}
    mod = official_module()
    for task in TASKS:
        test_ids = list(load_test(task).flow_id)
        sample_ids = list(pd.read_csv(DATA / task / "sample_submission.csv").flow_id)
        p = preds[task]
        Xtr = TASK_FEATURES[task](load_task(task)[0])
        checks[task] = {
            "n_predictions": len(p), "n_test_flows": len(test_ids), "test_ids_unique": len(set(test_ids)) == len(test_ids),
            "ids_equal_test_features": set(p) == set(test_ids), "ids_equal_sample_submission": set(p) == set(sample_ids),
            "missing": len(set(test_ids) - set(p)), "extra": len(set(p) - set(test_ids)),
            "labels_allowed": set(p.values()) <= ALLOWED, "predicted_label_counts": dict(Counter(p.values())),
            "model": TASK_MODELS[task].__name__, "features": TASK_FEATURES[task].__name__, "n_feature_columns": Xtr.shape[1],
            "forbidden_columns_absent": not any(c in Xtr.columns for c in FORBIDDEN_COLUMNS),
            "files_read_outside_task_folder": list(getattr(TASK_FEATURES[task], "extra_data", []))}
    checks["task2_reads_only_task2_files"] = all(f.startswith("task2_realtime_prefix5/") for f in checks[TASKS[1]]["files_read_outside_task_folder"])
    for name in ("submission.json", "submission.zip"):
        sub = mod._load_submission(str(out / name))
        checks[f"official_loader_{name}"] = all(set(sub[t]) == set(load_test(t).flow_id) and set(sub[t].values()) <= ALLOWED for t in TASKS)
    src_hits = subprocess.run(["grep", "-l", "-E", "metadata.json|label_counts", *CODE[:3]], cwd=ROOT, capture_output=True, text=True).stdout.split()
    checks["no_metadata_or_label_counts_in_pipeline_code"] = not src_hits

    comparison = {}
    for name, ref in REFERENCES.items():
        old = json.loads((ROOT / ref).read_text())
        comparison[name] = {"json_byte_identical": (out / "submission.json").read_bytes() == (ROOT / ref).read_bytes()}
        for t in TASKS:
            diff = {k: (old[t][k], v) for k, v in preds[t].items() if old[t][k] != v}
            comparison[name][t] = {"changed": len(diff), "transitions": dict(Counter(f"{a} -> {b}" for a, b in diff.values())),
                                   "flows": sorted(diff)}

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "src", "requirements.txt"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    data_files = sorted(str(p.relative_to(DATA)) for t in TASKS for p in (DATA / t).glob("*.csv"))
    manifest = {"git_head": head, "src_uncommitted_changes": dirty or None,
                "code_sha256": {c: sha(ROOT / c) for c in CODE},
                "data_sha256": {f: sha(DATA / f) for f in data_files},
                "output_sha256": {n: sha(out / n) for n in ("submission.json", "submission.zip")}}
    config = {"task1_static": {"model": f"models.{TASK_MODELS['task1_static'].__name__} ({MODEL_NOTES.get(TASK_MODELS['task1_static'].__name__, '')})",
                               "features": f"cv.{TASK_FEATURES['task1_static'].__name__} (34 columns; derived columns are computed inside the model)",
                               "reads": "task1_static/ and task2_realtime_prefix5/ feature files (Task 2 -> Task 1 is allowed; disclosed)"},
              "task2_realtime_prefix5": {"model": f"models.{TASK_MODELS['task2_realtime_prefix5'].__name__} ({MODEL_NOTES.get(TASK_MODELS['task2_realtime_prefix5'].__name__, '')})",
                                         "features": "cv.no_timing_features (12 columns)", "reads": "task2_realtime_prefix5/ only"},
              "training_data": "train + validation (330 labelled flows)", "seed": 0,
              "excluded": list(FORBIDDEN_COLUMNS) + ["metadata.json label_counts", "test labels"],
              "command": " ".join([".venv/bin/python", "src/make_final_candidate.py", *sys.argv[1:]])}
    for name, obj in (("validation.json", checks), ("comparison.json", comparison), ("manifest.json", manifest), ("config.json", config)):
        (out / name).write_text(json.dumps(obj, indent=2, default=str) + "\n")
    print(json.dumps({"checks": checks, "comparison": {k: {t: v[t]["changed"] for t in TASKS} | {"identical": v["json_byte_identical"]}
                                                        for k, v in comparison.items()}, "outputs": manifest["output_sha256"]}, indent=1, default=str))


if __name__ == "__main__":
    main()
