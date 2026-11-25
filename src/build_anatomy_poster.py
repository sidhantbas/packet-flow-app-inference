"""Build the explainer poster docs/explainers/leaderboard-anatomy.svg: the leaderboard claims (102-105), the levers they may not
disclose (106-108) and what we achieved, told through the Eli Cohen radio story (find the hidden transmitter by silencing
everything else). Numbers come from the saved leaderboard and experiments/10[2-8]_evidence/analysis.json.

Usage: .venv/bin/python src/build_anatomy_poster.py
"""
from build_dedup_figures import AMBER, BG, BLUE, FONT, GREEN, LINE, MUTED, PANEL, RED, TEAL, TEXT, VIOLET, ROOT, ev, rect, t
from xml.sax.saxutils import escape

OUT = ROOT / "docs/explainers/leaderboard-anatomy.svg"
W = 1400
GREY = "#64748b"
KIND = {"in": ("✓ already in our production", GREEN), "no": ("✗ tested on our data: no gain", RED),
        "rule": ("⛔ excluded by our rules (measured anyway)", AMBER), "ban": ("🚫 forbidden: not built", GREY),
        "flat": ("· statement, nothing to test", "#334155")}

# What each leader transmitted (verbatim notes condensed to their ingredients) and what we found for each ingredient.
# Claimed macro F1 per task, copied from the saved leaderboard (v8 from the morning snapshot, the others from the evening one).
CLAIMED = {"102": ("0.94", "0.94"), "103": ("0.94", "0.93"), "104": ("0.92", "0.92"), "105": ("0.96", "0.94")}

CLAIMS = [
    ("Infralibre", "FlowLens-v8-Mozilla", "93.74", "102", [
        ("Balanced first-5 ensemble · ours (014)", "in"),
        ("Probability calibration · −0.003 / +0.004", "no"),
        ("Disclosed test counts · −0.005 (102)", "rule"),
        ("Task 1 unchanged", "flat")]),
    ("LLM_ops", "Lookup-Ensemble-v7", "93.44", "103", [
        ("Exact first-5 lookup · ours (036, 108)", "in"),
        ("Post-prefix delta features · ours (089)", "in"),
        ("Seed bagging · no change (094)", "no"),
        ("Optuna LGBM/XGB/ET/RF · +0.004", "no"),
        ("kNN-Manhattan member · facebook −0.075", "no"),
        ("Ratio / rate / CV features · T2 −0.05", "no"),
        ("Stacked lookup on ours · +0.0003 (108)", "no"),
        ("Prior correction β 0.25 · +0.001 (106)", "no"),
        ("Temporal smoothing · −0.021 / −0.016", "rule"),
        ("Hungarian count matching · +0.024 / −0.006", "rule"),
        ("mod-8 SNI-length proxy", "ban")]),
    ("RahmaniJ", "Early-Flow Ensemble", "92.50", "104", [
        ("First-5 ensemble · ours for Task 2 (014)", "in"),
        ("Same predictions for both tasks · −0.148", "no"),
        ("metadata.json counts · +0.001 (104)", "rule")]),
    ("Infralibre", "FlowLens-v9-PairSwap", "95.01", "105", [
        ("Cross-view ensemble · ours (022, 028, 089)", "in"),
        ("Consensus pair swap · −0.070 (105)", "no"),
        ("Task 2 unchanged since v8", "flat")]),
]


def mast(x, y, col):
    """A small radio mast with three signal arcs; the arcs pulse slowly (static meaning kept without animation)."""
    s = [f"<path d='M{x} {y} L{x - 14} {y + 40} M{x} {y} L{x + 14} {y + 40} M{x - 9} {y + 26} L{x + 9} {y + 26}' "
         f"stroke='{col}' stroke-width='2.5' fill='none'/>", f"<circle cx='{x}' cy='{y}' r='4' fill='{col}'/>"]
    for i, r in enumerate((10, 18, 26)):
        s.append(f"<path d='M{x + r * 0.7:.1f} {y - r * 0.7:.1f} A{r} {r} 0 0 1 {x + r * 0.7:.1f} {y + r * 0.7:.1f}' stroke='{col}' "
                 f"stroke-width='2' fill='none' opacity='0.8'><animate attributeName='opacity' values='0.8;0.2;0.8' dur='6s' "
                 f"begin='{i * 0.6}s' repeatCount='indefinite'/></path>")
    return "".join(s)


def section(y, n, title, sub):
    return [t(40, y, f"{n} · {title}", 24, TEXT, "800"), t(40, y + 26, sub, 14, MUTED)]


def deltas():
    """(label, task 1 delta, task 2 delta, seeds better of 5) for 102-108, as in docs/reports/leaderboard-method-reproduction.md."""
    e4 = ev(104)
    e7 = ev(107)
    b1 = max(e7["t1"]["vs_P"].items(), key=lambda kv: kv[1]["mean_delta"] if kv[0] != "NN" else -9)
    b2 = max(e7["t2"]["vs_P"].items(), key=lambda kv: kv[1]["mean_delta"] if kv[0] != "NN" else -9)
    pick = lambda e, t_: next(p for p in e[t_]["pairs"] if p["a"] == "E1" and p["b"] == "P")["mean_delta"]  # noqa: E731
    return [("102 Infralibre v8", None, ev(102)["pairs"][8]["mean_delta"], 0),
            ("103 LLM_ops v7", ev(103)["t1"]["pairs"][7]["mean_delta"], ev(103)["t2"]["pairs"][7]["mean_delta"], 0),
            ("104 RahmaniJ", pick(e4, "t1"), pick(e4, "t2"), 0),
            ("105 Infralibre v9", ev(105)["vs_P"]["V1"]["mean_delta"], None, 0),
            ("106 prior β inside ours", ev(106)["B25_vs_P"]["mean_delta"], None, 1),
            (f"107 same-moment labels ({b1[0]}/{b2[0]})", b1[1]["mean_delta"], b2[1]["mean_delta"], 0),
            ("108 lookup on our Task 2", None, ev(108)["vs_P"]["H"]["mean_delta"], 0)]


def build():
    b = [f"<defs><linearGradient id='sky' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#1e1b4b'/>"
         f"<stop offset='1' stop-color='{BG}'/></linearGradient>"
         f"<filter id='glow'><feGaussianBlur stdDeviation='2'/></filter></defs>",
         f"<rect width='{W}' height='150' fill='url(#sky)' rx='14'/>",
         t(40, 58, "The intercept room: anatomy of the leaderboard claims", 34, TEXT, "800"),
         t(40, 92, "Damascus, 1965: a hidden transmitter is found by silencing every other signal and listening for the one still on air.", 16, "#c7d2fe"),
         t(40, 116, "We did the same with every leader's method note: silence all but one ingredient, measure on folds it never saw, and listen.", 16, "#c7d2fe"),
         t(40, 140, "Sources: verbatim leaderboard notes (13 Oct) · experiments 102-108 · 265 cross-validation runs · numbers read from the evidence files", 12, MUTED)]

    # 1. The transmissions
    y0 = 196
    b += section(y0, "1", "The transmissions: what each leader claims", "Each mast is one method note. Each chip is one ingredient it names, coloured by what our tests found.")
    lx = 40
    for k, (lab, col) in KIND.items():
        b += [rect(lx, y0 + 42, 14, 14, col, 3), t(lx + 20, y0 + 54, lab, 12, TEXT)]
        lx += 20 + len(lab) * 6.6 + 26
    cw, gap, top = 316, 18, y0 + 76
    for i, (team, method, total, exp, chips) in enumerate(CLAIMS):
        x = 40 + i * (cw + gap)
        h = 150 + 36 * 11 + 70
        b += [rect(x, top, cw, h, PANEL, 14, LINE), mast(x + 34, top + 26, TEAL),
              t(x + 66, top + 36, team, 18, TEXT, "800"), t(x + 66, top + 56, method, 13, MUTED),
              t(x + cw - 16, top + 40, total, 30, AMBER, "800", "end"), t(x + cw - 16, top + 58, "claimed total", 11, MUTED, anchor="end"),
              f"<line x1='{x + 16}' y1='{top + 82}' x2='{x + cw - 16}' y2='{top + 82}' stroke='{LINE}'/>",
              t(x + 16, top + 104, f"Ingredients ({len(chips)})", 12, MUTED, "700")]
        for j, (lab, kind) in enumerate(chips):
            col = KIND[kind][1]
            cy = top + 116 + 36 * j
            b += [rect(x + 14, cy, cw - 28, 28, BG, 7, col), rect(x + 14, cy, 6, 28, col, 3), t(x + 28, cy + 19, lab, 12)]
        sy = top + h - 56
        c1, c2 = CLAIMED[exp]
        b += [t(x + 16, sy - 40, "Claimed on the 81 test flows", 11, MUTED, "700"),
              t(x + 16, sy - 16, f"Task 1 F1 {c1}", 15, TEXT, "700"), t(x + cw / 2 + 4, sy - 16, f"Task 2 F1 {c2}", 15, TEXT, "700")]
        b += [rect(x + 14, sy, cw - 28, 42, "#450a0a", 8, RED),
              t(x + cw / 2, sy + 18, f"Experiment {exp}: NOT REPRODUCED", 13, "#fca5a5", "800", "middle"),
              t(x + cw / 2, sy + 35, "worse than our production on 5 of 5 seeds", 11, "#fecaca", anchor="middle")]

    # 2. The blackout method
    y1 = top + 150 + 36 * 11 + 70 + 70
    b += section(y1, "2", "The blackout method: how a claim is tested", "Same five steps for every claim, so results are comparable and can be re-run by anyone with the repository.")
    steps = [("📡", "Intercept", "copy the note verbatim", "saved before any code"),
             ("🔍", "Decode", "one build per phrase", "unknowns fixed in a frozen protocol"),
             ("🔇", "Blackout", "same folds as production", "one ingredient changes at a time"),
             ("📐", "Triangulate", "5 never-used seeds", "rule v2 must pass on all five"),
             ("⚖️", "Verdict", "+ test-set effect", "predictions changed, no labels")]
    sx, sw, sy = 40, 236, y1 + 56
    wave = " ".join(f"{'M' if i == 0 else 'L'}{40 + i * 6} {sy + 140 + (10 if i % 2 else -10)}" for i in range(0, 221))
    b.append(f"<path id='wire' d='M{sx + sw / 2} {sy + 66} L{sx + 4 * (sw + 30) + sw / 2} {sy + 66}' stroke='{TEAL}' stroke-width='3' stroke-dasharray='6 6'/>")
    for i, (ic, name, l1, l2) in enumerate(steps):
        x = sx + i * (sw + 30)
        b += [rect(x, sy, sw, 132, PANEL, 14, TEAL if i != 2 else VIOLET), t(x + 18, sy + 38, ic, 24),
              t(x + 56, sy + 38, name, 19, TEXT, "800"), t(x + 18, sy + 74, l1, 13), t(x + 18, sy + 96, l2, 12, MUTED)]
    b.append(f"<path d='{wave}' stroke='{LINE}' stroke-width='1.5' fill='none' opacity='0.6'/>")
    b.append(f"<circle r='7' fill='{AMBER}' filter='url(#glow)'><animateMotion dur='8s' repeatCount='indefinite' "
             f"path='M40 {sy + 140} L{W - 40} {sy + 140}'/></circle>")
    b.append(t(40, sy + 176, "Why the blackout matters: on 81 test flows a single facebook flow moves a score by about 2 points, so only paired runs on identical folds can hear a real signal under the noise.", 13, MUTED))

    # 3. Signal strength
    y2 = sy + 236
    rows = deltas()
    b += section(y2, "3", "Signal strength: what each method is worth on our data", "Change in macro F1 against our production on the same folds (mean of 5 never-used seeds). Left of the line = weaker than what we already have.")
    zero, scale, ry = 1000, 3400, y2 + 70
    b += [f"<line x1='{zero}' y1='{ry - 10}' x2='{zero}' y2='{ry + 52 * len(rows) + 6}' stroke='{GREEN}' stroke-width='2.5'/>",
          t(zero + 8, ry - 2, "our production", 12, GREEN, "700")]
    for v in (-0.15, -0.10, -0.05):
        xv = zero + v * scale
        b += [f"<line x1='{xv}' y1='{ry + 4}' x2='{xv}' y2='{ry + 52 * len(rows) + 6}' stroke='{LINE}' stroke-dasharray='3 5'/>",
              t(xv, ry + 52 * len(rows) + 24, f"{v:+.2f}".replace("-", "−"), 12, MUTED, anchor="middle")]
    for i, (name, d1, d2, won) in enumerate(rows):
        y = ry + 12 + 52 * i
        b.append(t(40, y + 16, name, 15, TEXT, "700"))
        b.append(t(40, y + 35, f"seeds better: {won} of 5", 12, GREEN if won else MUTED))
        for k, (lab, d, col) in enumerate((("T1", d1, BLUE), ("T2", d2, TEAL))):
            yy = y + k * 20
            if d is None:
                b.append(t(zero - 12, yy + 14, f"{lab} not part of the claim", 11, MUTED, anchor="end"))
                continue
            w = abs(d) * scale
            x = zero - w if d < 0 else zero
            b += [rect(x, yy, max(w, 3), 16, col if d < 0 else GREEN, 4),
                  t((x - 8) if d < 0 else (zero + w + 8), yy + 13, f"{lab} {d:+.4f}".replace("-", "−"), 11, TEXT, anchor="end" if d < 0 else "start")]

    # 4. Hidden transmitters
    y3 = ry + 52 * len(rows) + 80
    b += section(y3, "4", "Hidden transmitters: what the leaders might not say", "Notes are written for rivals to read. These are the signals that could really be behind a 95, and what our tests say.")
    e7, e6 = ev(107), ev(106)
    cards = [("Leaderboard feedback", "5 uploads a day on the ranking set", "Their v8→v9 jump is exactly +2 flows;\na blind swap gives that in 1-2% of tries (105)", "⛔ condition 1", AMBER),
             ("Published test counts", "force counts to metadata.json", "Over training-share counts:\n−0.005 (102) and +0.001 (104)", "⛔ our rule", AMBER),
             ("Same-moment labels", "the Cohen move: use the context", f"Copying neighbours' labels: Task 1 {e7['t1']['vs_P']['N05']['mean_delta']:+.3f},\nTask 2 {e7['t2']['vs_P']['N10']['mean_delta']:+.3f}; worse on every seed (107)", "⛔ our rule", VIOLET),
             ("Luck on 81 flows", "a strong model drawing well", "A Task 1 of 0.94 is our model's\n98.7th percentile on 81 flows (040)", "cannot be acted on", GREY),
             ("Prior correction", "rescale by class share", f"Inside our production: {e6['B25_vs_P']['mean_delta']:+.4f},\nbetter on 1 of 5 seeds (106)", "✅ allowed, no gain", GREEN),
             ("Exact-opening lookup", "memorise known openings", f"On our Task 2: {ev(108)['vs_P']['H']['mean_delta']:+.4f}, 0 test changes;\nour trees already do it (108)", "✅ allowed, no gain", GREEN)]
    cw2 = (W - 80 - 2 * 20) / 3
    for i, (name, what, evid, rule, col) in enumerate(cards):
        x, y = 40 + (i % 3) * (cw2 + 20), y3 + 50 + (i // 3) * 168
        lamp = f"<circle cx='{x + cw2 - 24}' cy='{y + 26}' r='8' fill='{col}' opacity='0.9'/>"
        b += [rect(x, y, cw2, 152, PANEL, 12, col), lamp, t(x + 18, y + 32, name, 18, TEXT, "800"), t(x + 18, y + 54, what, 12, MUTED)]
        for k, line in enumerate(evid.split("\n")):
            b.append(t(x + 18, y + 86 + 20 * k, line.replace("-0.", "−0."), 13))
        b.append(t(x + 18, y + 138, rule, 12, col, "800"))

    # 5. Fit of the analogy + what we achieved
    y4 = y3 + 50 + 2 * 168 + 40
    b += section(y4, "5", "Where the story fits, and what we have", "The analogy explains the hard part of the data; the evidence explains the decision.")
    pw = (W - 80 - 20) / 2
    fit = [("✅", "Fits: shared transmitter equipment", ["facebook and instagram share Meta's network stack, so their first-5",
                                                      "openings are often identical; google and youtube share QUIC."]),
           ("❌", "Does not fit: context finds the spy", ["In the story the context gave him away. Here the context is capture time:",
                                                       "excluded by our rules, and it makes predictions worse anyway (107)."]),
           ("❌", "Does not fit: most Task 1 errors", ["They are not identical signals but too few examples (facebook 11,",
                                                    "instagram 19 labelled flows); most remaining errors are confident (093)."])]
    b.append(rect(40, y4 + 46, pw, 300, PANEL, 14, VIOLET))
    b.append(t(60, y4 + 78, "The Eli Cohen framing", 18, "#f0abfc", "800"))
    for k, (ic, head, lines) in enumerate(fit):
        yy = y4 + 112 + 74 * k
        b += [t(60, yy, ic, 14), t(86, yy, head, 14, TEXT, "800")]
        b += [t(86, yy + 22 + 20 * n, ln, 13, "#cbd5e1") for n, ln in enumerate(lines)]
    ax = 60 + pw
    stats = [("7", "experiments (102-108)"), ("265", "cross-validation runs"), ("4 / 4", "claims not reproduced"),
             ("17", "techniques deduplicated"), ("0", "open leads left")]
    b += [rect(ax, y4 + 46, pw, 300, PANEL, 14, GREEN), t(ax + 20, y4 + 76, "What we have", 18, "#6ee7b7", "800")]
    for k, (num, lab) in enumerate(stats):
        x = ax + 20 + k * (pw - 40) / 5
        b += [t(x, y4 + 124, num, 28, TEXT, "800"), t(x, y4 + 146, lab.split(" ")[0], 11, MUTED),
              t(x, y4 + 160, " ".join(lab.split(" ")[1:]), 11, MUTED)]
    b += [t(ax + 20, y4 + 206, "Production stays: Task 1 CV 0.85, Task 2 CV 0.76, board 87.24 (rank 8).", 14),
          t(ax + 20, y4 + 234, "Gap to first: 7.77 points ≈ 5 Task 1 flows + 2 Task 2 flows of 81.", 14),
          t(ax + 20, y4 + 262, "Every ingredient is ours already, no gain, or off-limits.", 14),
          t(ax + 20, y4 + 300, "Decision: no upload; finish the technical report.", 15, GREEN, "800")]
    H = y4 + 46 + 300 + 64
    b.append(t(W / 2, H - 22, "Built by src/build_anatomy_poster.py from the evidence files · details: docs/reports/leaderboard-method-reproduction.md", 12, MUTED, anchor="middle"))
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}' role='img' "
            f"aria-label='The intercept room: anatomy of the leaderboard claims'>\n<style>:root {{ color-scheme: dark; }}"
            f" @media (prefers-reduced-motion: reduce) {{ animate, animateMotion {{ display: none; }} }}</style>\n"
            f"<rect width='{W}' height='{H}' fill='{BG}' rx='14'/>\n" + "\n".join(b) + "\n</svg>\n")


if __name__ == "__main__":
    OUT.write_text(build())
    print("wrote", OUT.relative_to(ROOT))
