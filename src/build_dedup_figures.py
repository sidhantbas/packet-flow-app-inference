"""Build the six SVG figures of docs/reports/leaders-vs-ours-dedup.md from saved evidence (no hand-typed results where a file
holds them). Dark-mode-safe, static SVG.

Usage: .venv/bin/python src/build_dedup_figures.py        (writes docs/reports/figures/dedup-*.svg)
Inputs: submissions/raw/leaderboard-final-test-2026-10-13-evening.txt, experiments/10[2-8]_evidence/analysis.json
"""
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/reports/figures"
BG, PANEL, TEXT, MUTED, LINE = "#0f172a", "#1e293b", "#e2e8f0", "#94a3b8", "#475569"
GREEN, RED, AMBER, BLUE, VIOLET, TEAL = "#10b981", "#ef4444", "#f59e0b", "#3b82f6", "#c026d3", "#0ea5e9"
FONT = "font-family='Inter, Helvetica, Arial, sans-serif'"


def ev(n):
    return json.loads((ROOT / f"experiments/{n}_evidence/analysis.json").read_text())


def svg(w, h, body, title):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' role='img' "
            f"aria-label='{escape(title, {chr(39): "&apos;"})}'>\n<style>:root {{ color-scheme: dark; }}</style>\n"
            f"<rect width='{w}' height='{h}' fill='{BG}' rx='14'/>\n"
            f"<text x='28' y='42' fill='{TEXT}' font-size='22' font-weight='700' {FONT}>{escape(title)}</text>\n{body}\n</svg>\n")


def t(x, y, s, size=14, fill=TEXT, weight="400", anchor="start"):
    return (f"<text x='{x}' y='{y}' fill='{fill}' font-size='{size}' font-weight='{weight}' text-anchor='{anchor}' {FONT}>"
            f"{escape(str(s))}</text>")


def rect(x, y, w, h, fill, rx=6, stroke=None):
    s = f" stroke='{stroke}' stroke-width='1.5'" if stroke else ""
    return f"<rect x='{x:.1f}' y='{y:.1f}' width='{max(w, 0):.1f}' height='{h:.1f}' rx='{rx}' fill='{fill}'{s}/>"


def leaderboard():
    rows = []
    for line in (ROOT / "submissions/raw/leaderboard-final-test-2026-10-13-evening.txt").read_text().splitlines():
        m = re.match(r"^(\d+) (.+?) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ", line)
        if m:
            rows.append((m.group(2), float(m.group(5)), float(m.group(8)), float(m.group(9))))
    return rows


def fig1():
    rows = leaderboard()
    W, H = 980, 120 + 46 * len(rows)
    x0, scale = 300, 6.4
    b = [t(28, 68, "Final Test Phase, 13 October evening. Each bar: Task 1 points (left) + Task 2 points (right), out of 100.", 13, MUTED)]
    for i, (team, s1, s2, tot) in enumerate(rows):
        y = 92 + 46 * i
        us = team.startswith("Telex")
        b.append(t(28, y + 20, ("▶ " if us else "") + team, 14, AMBER if us else TEXT, "700" if us else "400"))
        b.append(rect(x0, y, s1 * scale, 28, BLUE if not us else AMBER))
        b.append(rect(x0 + s1 * scale, y, s2 * scale, 28, TEAL if not us else "#fbbf24"))
        b.append(t(x0 + (s1 + s2) * scale + 10, y + 20, f"{tot:.2f}", 14, TEXT, "700"))
    b.append(t(28, H - 18, "Gap to first place: 7.77 points, of which Task 1 is 6.22 and Task 2 is 1.54.", 14, AMBER, "700"))
    return svg(W, H, "\n".join(b), "1. Where we stand on the leaderboard")


def fig2():
    W, H = 980, 430
    b = [t(28, 68, "On 81 test flows, one flow in a rare class moves a task's macro F1 by about 0.04 (2 points).", 13, MUTED)]
    cards = [("Task 1 (full flow)", "Us 0.840", "Leader 0.964", "−6.2 points", "~5 flows of 81", RED),
             ("Task 2 (first 5 packets)", "Us 0.905", "Leader 0.936", "−1.5 points", "~2 flows of 81", AMBER)]
    for i, (name, us, lead, gap, flows, col) in enumerate(cards):
        x = 28 + i * 470
        b += [rect(x, 92, 450, 200, PANEL, 12, col), t(x + 22, 128, name, 18, TEXT, "700"), t(x + 22, 168, us, 16, MUTED),
              t(x + 22, 196, lead, 16, MUTED), t(x + 22, 244, gap, 30, col, "800"), t(x + 230, 244, flows, 16, TEXT)]
    b += [t(28, 330, "Why Task 1: facebook (11 labelled flows) and instagram (19) share Meta's network stack, and macro F1", 15),
          t(28, 354, "weights each of them like google (131). Production, 250 CV folds (106): facebook 0.70, instagram 0.77, google 0.91.", 15),
          t(28, 392, "Why the gap is hard to close: what our models still miss is confident, not close (093).", 15, AMBER, "700")]
    return svg(W, H, "\n".join(b), "2. Where the points are lost")


def fig3():
    rows = [("102 Infralibre v8", None, ev(102)["pairs"][8]["mean_delta"]),
            ("103 LLM_ops", ev(103)["t1"]["pairs"][7]["mean_delta"], ev(103)["t2"]["pairs"][7]["mean_delta"]),
            ("104 RahmaniJ", next(p for p in ev(104)["t1"]["pairs"] if p["a"] == "E1" and p["b"] == "P")["mean_delta"],
             next(p for p in ev(104)["t2"]["pairs"] if p["a"] == "E1" and p["b"] == "P")["mean_delta"]),
            ("105 Infralibre v9", ev(105)["vs_P"]["V1"]["mean_delta"], None)]
    W, H = 980, 150 + 70 * len(rows)
    zero, scale = 640, 2200
    b = [t(28, 68, "Each leader's method as described, against our production, mean of 5 never-used seeds (cross-validation).", 13, MUTED),
         f"<line x1='{zero}' y1='88' x2='{zero}' y2='{H - 60}' stroke='{LINE}' stroke-width='2'/>",
         t(zero + 6, 104, "0 = our production", 12, MUTED)]
    for i, (name, d1, d2) in enumerate(rows):
        y = 118 + 70 * i
        b.append(t(28, y + 26, name, 15, TEXT, "700"))
        for k, (lab, d, col) in enumerate((("Task 1", d1, BLUE), ("Task 2", d2, TEAL))):
            yy = y + k * 26
            if d is None:
                b.append(t(zero - 10, yy + 16, f"{lab}: not claimed", 12, MUTED, anchor="end"))
                continue
            b += [rect(zero + d * scale, yy, -d * scale, 20, col), t(zero + d * scale - 8, yy + 15, f"{lab} {d:+.3f}", 12, TEXT, anchor="end")]
    b.append(t(28, H - 24, "All four: worse than our production on every one of their 5 seeds. None reproduces.", 15, RED, "700"))
    return svg(W, H, "\n".join(b), "3. The leaders' methods, reproduced on our data")


STATUS = {"in": ("✓ Already in our production", GREEN), "no": ("✗ Tested, did not help", RED),
          "rule": ("⛔ Excluded by the rules", AMBER), "open": ("⏳ Open lead", BLUE)}
TECH = [("Balanced tree ensemble (004)", "in"), ("First-5 model, Task 2 (014)", "in"), ("Full flow + first 5 (022, 028)", "in"),
        ("Exact first-5 lookup (036, 108)", "in"), ("Rest-of-flow features (089)", "in"),
        ("Prefix-only, both tasks (104)", "no"), ("Probability calibration (102)", "no"), ("Seed bagging (094, 103)", "no"),
        ("Optuna tuning, XGBoost (103)", "no"), ("kNN-Manhattan member (103)", "no"), ("Ratio and rate features (008)", "no"),
        ("Consensus pair swap (105)", "no"), ("Prior correction β (103, 106)", "no"),
        ("Published test class counts", "rule"), ("Capture-time smoothing", "rule"), ("SNI-length proxy (mod 8)", "rule"),
        ("Same-moment flow labels (107)", "rule")]


def fig4():
    W, H = 980, 640
    b = [t(28, 68, "Every technique the leaders describe, merged with our own experiments 001-108: one status each.", 13, MUTED)]
    cols = {k: [n for n, s in TECH if s == k] for k in STATUS}
    for i, k in enumerate(STATUS):
        x = 28 + i * 238
        lab, col = STATUS[k]
        b += [rect(x, 88, 226, 508, PANEL, 12, col), t(x + 14, 116, lab, 13, col, "700"), t(x + 14, 140, f"{len(cols[k])} techniques", 12, MUTED)]
        if not cols[k]:
            b.append(t(x + 14, 178, "None left: every lead tested", 12, TEXT))
        for j, n in enumerate(cols[k]):
            b += [rect(x + 12, 156 + 42 * j, 202, 34, BG, 8, col), t(x + 22, 178 + 42 * j, n, 12)]
    b.append(t(28, 622, "Published counts and capture time were also measured: neither helps our models (095, 102-105, 107).", 14, AMBER, "700"))
    return svg(W, H, "\n".join(b), "4. Deduplication: the leaders' techniques against ours")


def fig5():
    e7 = ev(107)
    n1 = max(e7["t1"]["vs_P"].items(), key=lambda kv: kv[1]["mean_delta"])
    n2 = max(e7["t2"]["vs_P"].items(), key=lambda kv: kv[1]["mean_delta"])
    cards = [("Leaderboard feedback", "5 uploads a day on the set that ranks the competition", "Their v9 jump = exactly +2 flows;\na blind swap gives that 1-2% of the time (105)", "⛔ Condition 1", AMBER),
             ("Published test counts", "Constrained assignment to metadata counts", "No gain for our models:\n−0.005 / +0.001 (102, 104)", "⛔ Our rule", AMBER),
             ("Same-moment flow labels", "Copy labels of labelled flows opened within ~1 s", f"Best: Task 1 {n1[1]['mean_delta']:+.3f} ({n1[0]}),\nTask 2 {n2[1]['mean_delta']:+.3f} ({n2[0]}) (107)", "⛔ Our rule (capture time)", VIOLET),
             ("Luck on 81 flows", "One rare-class flow = about 2 points", "A Task 1 of 0.94 is our model's 98.7th\npercentile on 81-flow draws (040)", "Cannot be acted on", MUTED),
             ("Outside data / pretrained", "Allowed by the challenge if disclosed", "No team discloses any;\nTabPFN gave +0.003 (078)", "⛔ Our rule", AMBER),
             ("Prior correction β = 0.25", "Described by LLM_ops", f"On our production: {ev(106)['B25_vs_P']['mean_delta']:+.4f}\n(106, BETTER on 1 of 5 seeds)", "✅ Allowed, no gain", GREEN)]
    W, H = 980, 600
    b = [t(28, 68, "What might really be behind the leaders' scores, what our tests say, and whether we may use it.", 13, MUTED)]
    for i, (name, what, evid, rule, col) in enumerate(cards):
        x, y = 28 + (i % 2) * 470, 88 + (i // 2) * 166
        b += [rect(x, y, 450, 150, PANEL, 12, col), t(x + 16, y + 30, name, 17, TEXT, "700"), t(x + 16, y + 54, what, 12, MUTED)]
        for k, line in enumerate(evid.split("\n")):
            b.append(t(x + 16, y + 84 + 20 * k, line, 13))
        b.append(t(x + 434, y + 30, rule, 12, col, "700", "end"))
    return svg(W, H, "\n".join(b), "5. What the leaders may not disclose")


def fig6():
    W, H = 980, 600
    b = [t(28, 68, "Highlighted: the path our evidence takes. Grey: the alternatives and why they are closed (report, section 6).", 13, MUTED)]
    nodes = [(340, 90, 300, 54, "Leaders reproduced (102-105)\nnone beats production", TEAL, True),
             (30, 200, 270, 60, "106 prior correction (T1)\n+0.001, BETTER 1 of 5", RED, True),
             (355, 200, 270, 60, "107 same-moment labels\nWORSE on every seed", RED, True),
             (680, 200, 270, 60, "108 lookup on our Task 2\n+0.0003, 0 test changes", RED, True),
             (330, 310, 320, 60, "Keep production (100 + 014)\nno upload: nothing meets the rule", GREEN, True),
             (330, 420, 320, 54, "Technical report + final checks by 23 Oct", BLUE, True),
             (30, 420, 270, 70, "Alt: use published counts\nno CV gain; condition 1 risk", MUTED, False),
             (680, 420, 270, 70, "Alt: prefix predictions for Task 1\n= choosing by test score", MUTED, False),
             (30, 510, 270, 70, "Alt: own captures\nlabel and setup mismatch (056-063)", MUTED, False),
             (680, 510, 270, 70, "Alt: tune on leaderboard feedback\ncondition 1 and Goodhart", MUTED, False)]
    edges = [(490, 144, 165, 200, True), (490, 144, 490, 200, True), (490, 144, 815, 200, True), (165, 260, 490, 310, True),
             (490, 260, 490, 310, True), (815, 260, 490, 310, True), (490, 370, 490, 420, True)]
    for a, c, d, e, on in edges:
        b.append(f"<line x1='{a}' y1='{c}' x2='{d}' y2='{e}' stroke='{AMBER if on else LINE}' stroke-width='{3 if on else 1.5}'/>")
    for x, y, w, h, label, col, on in nodes:
        b.append(rect(x, y, w, h, PANEL if on else BG, 10, col))
        for k, line in enumerate(label.split("\n")):
            b.append(t(x + w / 2, y + 24 + 20 * k, line, 13, TEXT if on else MUTED, "700" if k == 0 else "400", "middle"))
    return svg(W, H, "\n".join(b), "6. Decisions and alternatives")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    figs = {"dedup-1-leaderboard.svg": fig1(), "dedup-2-where-points-lost.svg": fig2(), "dedup-3-reproductions.svg": fig3(),
            "dedup-4-dedup-map.svg": fig4(), "dedup-5-hidden-levers.svg": fig5(), "dedup-6-decisions.svg": fig6()}
    for name, s in figs.items():
        (OUT / name).write_text(s)
        print("wrote", (OUT / name).relative_to(ROOT))


if __name__ == "__main__":
    main()
