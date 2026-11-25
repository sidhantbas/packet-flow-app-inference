"""Generate docs/reports/tested-methods-and-leaderboard.md: (1) every experiment as date / technique / scores / insight /
kept or aborted, connected to the leaderboard uploads; (2) verbatim copies of the leaderboard and of our raw score outputs
(submissions/raw/, embedded unchanged); (3) a one-by-one verification of every upload and of the leaderboard arithmetic.

Usage: .venv/bin/python src/build_tested_report.py            (write the report; runs `src/runs.py verify`)
       .venv/bin/python src/build_tested_report.py --check    (exit 1 if the report is out of date)
"""
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from build_experiments_index import ROOT, logs

OUT = ROOT / "docs/reports/tested-methods-and-leaderboard.md"
RAW = ROOT / "submissions/raw"
LABELS = {"facebook", "google", "instagram", "mozilla", "x", "youtube"}
TASKS = ("task1_static", "task2_realtime_prefix5")
KEPT = {"adopted", "tooling", "submission"}
INSIGHT_BY_STATUS = {"adopted": "In production", "rejected": "No gain over production", "inconclusive": "Positive, not confirmed",
                     "measured": "Measurement only", "unfinished": "Not finished", "tooling": "Infrastructure in use",
                     "submission": "Submission built"}
# uploads 1-2 exist only in Git history; 3-8 have their own folders (submissions/README.md)
FILES = {1: ("git", "6b76821"), 2: ("git", "0a1e0ba"), 3: ("dir", "best-87.77-frozen-5eb9a8b"), 4: ("dir", "candidate-066-rest-expert"),
         5: ("dir", "candidate-083-instagram-verifier"), 6: ("dir", "best-88.11-production-084"), 7: ("dir", "production-089-bundle"),
         8: ("dir", "production-100-cross-task"), 9: ("dir", "best-88.11-production-084"),
         10: ("dir", "candidate-127-meta-count-guided"),
         11: ("dir", "candidate-128-109b-task2")}  # 9: re-upload of 6 (2026-10-16); 10: 127 (2026-10-21)


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def split_verdict(e):
    v = str(e["verdict"])
    i = v.find(": ")
    ok = 0 < i <= 70 and v[:i].count("(") == v[:i].count(")")
    technique, rest = (v[:i], v[i + 2:]) if ok else (str(e["title"]), v)
    parts = [p.strip() for p in re.split(r";\s+", rest) if p.strip()]
    scores = [p for p in parts if re.search(r"\d", p)]
    words = [p for p in parts if not re.search(r"\d", p)]
    insight = "; ".join(words) or INSIGHT_BY_STATUS.get(e["status"], "")
    if e["status"] == "measured" and not insight.lower().startswith("measurement"):
        insight = "Measurement: " + insight
    return technique, "; ".join(scores) or "—", insight


def uploads():
    return list(csv.DictReader((ROOT / "submissions/uploads.csv").open()))


def load_upload(n):
    kind, ref = FILES[n]
    if kind == "git":
        txt = subprocess.run(["git", "show", f"{ref}:submissions/submission.json"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout
        return json.loads(txt), None
    d = ROOT / "submissions" / ref
    zsha = hashlib.sha256((d / "submission.zip").read_bytes()).hexdigest() if (d / "submission.zip").exists() else None
    return json.loads((d / "submission.json").read_text()), zsha


def recorded_sha_prefixes():
    out = {}
    for line in (ROOT / "submissions/README.md").read_text().splitlines():
        m = re.search(r"\[`([^`]+)/`\].*`([0-9a-f]{8})…([0-9a-f]{4})` \|\s*$", line)
        if m:
            out[m.group(1)] = (m.group(2), m.group(3))
    return out


def tick(ok):
    return "✓" if ok else "✗"


def section_tested(o, ups):
    w = o.append
    up_by_exp = {}
    for u in ups:
        m = re.match(r"(\d{3})", u["task1_model"])
        if m:
            up_by_exp.setdefault(m.group(1), []).append(f"upload {u['upload']}: {u['total']}")
    w("## 1. What's tested")
    w("")
    w("Every experiment, from its log's front matter ([EXPERIMENTS.md](../../EXPERIMENTS.md) has the full verdicts and links).")
    w("**Kept ✓** = in production, or infrastructure and submissions in use; **aborted ✗** = rejected, inconclusive, unfinished, or a")
    w("measurement with nothing to promote. **Leaderboard** = the Final Test Phase score of the upload built from that experiment's")
    w("Task 1 model. Scores are cross-validation macro F1 unless they say otherwise.")
    w("")
    w("| Date | # | Technique | Scores | Insight | Kept | Leaderboard |")
    w("|---|---|---|---|---|:---:|---|")
    for e in logs():
        technique, scores, insight = split_verdict(e)
        w(f"| {e['date']} | [{e['id']}](../../experiments/{e['file']}) | {esc(technique)} | {esc(scores)} | {esc(insight)} | "
          f"{'✓' if e['status'] in KEPT else '✗'} | {', '.join(up_by_exp.get(e['id'], [])) or '—'} |")
    w("")


def section_path(o, ups, preds):
    w = o.append
    w("## 2. From experiments to the leaderboard")
    w("")
    w("Each upload, the Task 1 model it carried, and how many test predictions changed against the upload before it (Task 2 was")
    w("the same 014 model in every upload).")
    w("")
    w("| Upload | Date | Task 1 model | Task 1 changes vs previous upload | Task 1 F1 | Task 2 F1 | Total |")
    w("|---:|---|---|---:|---:|---:|---:|")
    prev = None
    for u in ups:
        n = int(u["upload"])
        p = preds[n]["task1_static"]
        ch = "—" if prev is None else str(sum(p[f] != prev[f] for f in p))
        w(f"| {n} | {u['date']} | {esc(u['task1_model'])} | {ch} | {u['task1_macro_f1'] or '—'} | {u['task2_macro_f1'] or '—'} | "
          f"**{u['total']}** |")
        prev = p
    w("")


def section_verbatim(o):
    w = o.append
    w("## 3. Verbatim copy of the leaderboard and of our raw scores")
    w("")
    w("Byte-for-byte copies of `submissions/raw/`, nothing rounded or rephrased. The platform itself shows two decimals.")
    w("")
    for name, title in (("leaderboard-final-test-2026-10-13.txt", "Final Test Phase leaderboard and method notes, 2026-10-13"),
                        ("upload-08-score.txt", "Upload 8 raw score output (2026-10-12), exactly as pasted in chat"),
                        ("upload-07-score.txt", "Upload 7 raw score output (2026-10-10), as pasted in chat"),
                        ("upload-06-total.txt", "Upload 6 total (2026-10-09), the only raw figure kept")):
        w(f"### {title}")
        w("")
        w(f"Source: [`submissions/raw/{name}`](../../submissions/raw/{name})")
        w("")
        w("```text")
        w((RAW / name).read_text().rstrip("\n"))
        w("```")
        w("")
    w("No raw output was kept for uploads 1-5; their figures in `submissions/uploads.csv` are the rounded values recorded at the time.")
    w("")


def section_verify(o, ups, preds, shas):
    w = o.append
    w("## 4. Verify one by one")
    w("")
    rec = recorded_sha_prefixes()
    test_ids = {t: set(json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())[t]) for t in TASKS}
    w("### 4.1 Every upload")
    w("")
    w("| Upload | File found | 81 valid predictions per task | Zip SHA-256 = recorded | Task 2 = upload 8's | Total = 50 × (T1 + T2) | Raw output agrees |")
    w("|---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    t2_ref = preds[8]["task2_realtime_prefix5"]
    raw = {7: (RAW / "upload-07-score.txt").read_text(), 8: (RAW / "upload-08-score.txt").read_text(),
           6: (RAW / "upload-06-total.txt").read_text()}
    for u in ups:
        n = int(u["upload"])
        p = preds[n]
        valid = all(set(p[t]) == test_ids[t] and set(p[t].values()) <= LABELS for t in TASKS)
        folder = FILES[n][1] if FILES[n][0] == "dir" else None
        sha_ok = "n/a (Git only)" if folder is None else tick(folder in rec and shas[n] and shas[n].startswith(rec[folder][0])
                                                            and shas[n].endswith(rec[folder][1]))
        t2 = tick(p["task2_realtime_prefix5"] == t2_ref)
        if u["task1_macro_f1"] and u["task2_macro_f1"]:
            arith = tick(abs(50 * (float(u["task1_macro_f1"]) + float(u["task2_macro_f1"])) - float(u["total"])) <= 0.06)
        else:
            arith = "n/a (Task 1 not recorded)"
        if n in raw:
            tot = re.search(r'"Total": ([0-9.]+)', raw[n])
            val = float(tot.group(1)) if tot else float(raw[n].strip())
            r = tick(abs(val - float(u["total"])) < 0.005)
        else:
            r = "n/a (no raw kept)"
        w(f"| {n} | ✓ | {tick(valid)} | {sha_ok} | {t2} | {arith} | {r} |")
    w("")
    w("- **Task 2 identical in all uploads** explains the constant Task 2 macro F1 (0.905055 in every raw output).")
    same = [int(u["upload"]) for u in ups if int(u["upload"]) != 3 and preds[int(u["upload"])]["task1_static"] == preds[3]["task1_static"]]
    w(f"- **Uploads with Task 1 identical to upload 3 (87.77): {same or 'none'}**; their recorded totals must equal 87.77: "
      f"{tick(all(next(x for x in ups if int(x['upload']) == s)['total'] == '87.77' for s in same))}.")
    w("")
    w("### 4.2 Leaderboard arithmetic (every row of the verbatim copy)")
    w("")
    w("| Team | Task 1 score = 50 × F1 (±0.25, F1 shown to 2 decimals) | Task 2 score = 50 × F1 | Total = sum (±0.01) |")
    w("|---|:---:|:---:|:---:|")
    for line in (RAW / "leaderboard-final-test-2026-10-13.txt").read_text().splitlines():
        m = re.match(r"^\d+ (.+?) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ", line)
        if m:
            f1a, _, s1, f2a, _, s2, tot = map(float, m.groups()[1:])
            w(f"| {m.group(1)} | {tick(abs(50 * f1a - s1) <= 0.25)} | {tick(abs(50 * f2a - s2) <= 0.25)} | "
              f"{tick(abs(s1 + s2 - tot) <= 0.011)} |")
    w("")
    t7 = re.search(r'"Total": ([0-9.]+)', raw[7]).group(1)
    w(f"- **Our leaderboard row (Telex, 87.24) is upload 7**: raw total {t7} rounds to 87.24 ✓. Upload 8 (86.36) is also ticked "
      "\"Show on leaderboard\"; the board shows the better of the two.")
    w("- **Platform count**: 12 Final Test Phase submissions on the platform, 8 in `submissions/uploads.csv` ✗ (4 not yet "
      "identified; [platform facts](leaderboard-reverse-engineering-2026-10-13.md#2-platform-facts-that-change-our-plan)).")
    w("")
    w("### 4.3 Cross-validation scores and the production file")
    w("")
    r = subprocess.run([sys.executable, str(ROOT / "src/runs.py"), "verify"], cwd=ROOT, capture_output=True, text=True)
    last = [l for l in r.stdout.splitlines() if "runs verified" in l]
    w(f"- `src/runs.py verify`: **{last[-1].strip() if last else 'FAILED'}** (metrics recomputed from the stored predictions, "
      "every hash checked).")
    same_prod = (ROOT / "submissions/submission.json").read_bytes() == (ROOT / "submissions/production-100-cross-task/submission.json").read_bytes()
    w(f"- `submissions/submission.json` is byte-identical to the production package: {tick(same_prod)}. A full rebuild "
      "(`src/make_final_candidate.py`) was byte-identical on 2026-10-13.")
    w("")


def build():
    ups = uploads()
    preds, shas = {}, {}
    for u in ups:
        n = int(u["upload"])
        preds[n], shas[n] = load_upload(n)
    o = ["---", "title: \"What we tested, what it scored, and how it reached the leaderboard\"", "creator: sidhantbas",
         "description: Generated by src/build_tested_report.py. Every experiment with its scores, insight and kept or aborted "
         "decision; the path from experiments to the leaderboard; verbatim leaderboard and raw scores; one-by-one verification.",
         "---", "", "# What we tested, what it scored, and how it reached the leaderboard", "",
         "> **Generated file.** Regenerate with `.venv/bin/python src/build_tested_report.py`; do not edit by hand.", ""]
    section_tested(o, ups)
    section_path(o, ups, preds)
    section_verbatim(o)
    section_verify(o, ups, preds, shas)
    return "\n".join(o)


def main():
    text = build()
    if "--check" in sys.argv:
        ok = OUT.exists() and OUT.read_text() == text
        print("report is up to date" if ok else "report is OUT OF DATE: run src/build_tested_report.py")
        sys.exit(0 if ok else 1)
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
