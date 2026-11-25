"""Experiment 122, part 2: per-flow label audit of our captures (Charles's 20 October handoff, deliverable 2).

Command: .venv/bin/python src/exp122_label_audit.py
Reads the clean extraction (data/captures/clean-v2/, experiment 120) and re-reads each iPhone packet file for the full process
breakdown of every flow (Darwin process-information blocks, as src/capture_clean.py). For every flow it records the session label,
the process evidence, a proposed reviewed label with confidence and reason, and two inclusion decisions (strict = 120's rules;
process = attributed to the app, edge trim ignored). Then:
  - population counts per group, session and evidence category (disagreements, exclusions, unknowns);
  - a fixed review sample (seed 2026): 25 flows per app across sessions, every idle-session flow, 15 background flows;
  - an independent cross-check against Charles's 364 provisional candidates (his Charles 003 package, read from the fetched
    upstream commit with git show; flows matched by session and identical feature values).
Writes experiments/122_evidence/label_audit_flows.csv, label_audit_sample.csv, label_audit_summary.json.
No IP addresses, phone ports, server names or payload are read into the outputs; the reviewed label is a proposal for the
human acceptance Charles asks for.
"""
import io
import json
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from capture_clean import APP_OF_PROCESS, GROUPS, RAW, read_packets_meta
from capture_extract import assemble, parse, phone_addresses, split_merged

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data/captures/clean-v2"
OUT = ROOT / "experiments/122_evidence"
UPSTREAM = "d3189ba"
CHARLES = "experiments/charles-003-capture-audit/evidence/20261020-flow-aggregates/observed"
APPS = ["facebook", "instagram", "youtube"]
PURE = 0.9
MATCH_COLS = ["transport", "server_port", "packet_count_up", "packet_count_down", "bytes_up", "bytes_down"]


def process_breakdowns(group, session):
    """Per kept flow (>= 5 packets, extraction order of capture_clean), the Counter of packet processes."""
    packets, by_key = [], {}
    for ts, link, f, proc in read_packets_meta(RAW / group / session / "packets.pcapng"):
        p = parse(ts, link, f, ipv6=True)
        if p is not None:
            packets.append(p)
            by_key.setdefault((p[0], p[6]), []).append(proc)
    if GROUPS[group]["split_merged"]:
        packets, _ = split_merged(packets)
    flows, _ = assemble(packets, phone_addresses(packets, "auto"), 300.0, tcp_start="syn")
    return [Counter(pr for t, size, _ in fl["packets"] for pr in by_key.get((t, size), ["(none)"]))
            for fl in flows if len(fl["packets"]) >= 5]


def classify(r):
    """Evidence category, proposed reviewed label, confidence, reason."""
    if r.label_source == "session":
        return "session only (no process data)", "", "unknown", "network-side capture: no per-packet process; session label kept as uncertain"
    if r.session_app == "idle":
        if r.app:
            return "idle control: app traffic", r.app, "medium", f"{r.process} traffic during an idle session"
        return "idle control: background", "", "background", f"background process ({r.process}) in an idle session"
    if not r.app:
        if r.process == "(none)":
            return "unattributed", "", "unknown", "no process recorded for the flow's packets"
        return "background process", "", "background", f"system/other process {r.process}"
    if r.process_share < PURE:
        return "mixed processes", r.app, "low", f"majority {r.process} on only {r.process_share:.0%} of packets"
    if r.app != r.session_app:
        return "process disagrees with session", r.app, "high", f"{r.process} traffic during the {r.session_app} session"
    return "process agrees with session", r.app, "high", f"{r.process} on {r.process_share:.0%} of packets"


def charles_candidates():
    get = lambda f: pd.read_csv(io.StringIO(subprocess.run(["git", "show", f"{UPSTREAM}:{CHARLES}/{f}"], cwd=ROOT,
                                                            capture_output=True, text=True, check=True).stdout))
    lab, t1 = get("candidate_labels.csv"), get("candidate_task1_features.csv")
    c = t1.merge(lab, on="flow_id")
    parts = c.flow_id.str.split("__", expand=True)
    c["group"], c["session"] = parts[0], parts[1]
    return c


def main():
    rows = []
    for group, cfg in GROUPS.items():
        for sdir in sorted(p for p in (CLEAN / group).iterdir() if p.is_dir()):
            L = pd.read_csv(sdir / "labels.csv", keep_default_na=False)
            if not len(L):
                continue
            T = pd.read_csv(sdir / "task1_features.csv")
            assert (L.flow_id == T.flow_id).all()
            br = process_breakdowns(group, sdir.name) if cfg["process"] else [None] * len(L)
            assert len(br) == len(L), (group, sdir.name, len(br), len(L))
            for (_, l), (_, t), b in zip(L.iterrows(), T.iterrows(), br):
                rows.append({"group": group, "session": sdir.name, "flow_id": l.flow_id, "start_rel": round(t.start_rel, 3),
                             "duration": t.duration, "transport": t.transport, "server_port": t.server_port,
                             "packets": int(t.packet_count_up + t.packet_count_down),
                             **{c: t[c] for c in MATCH_COLS[2:]},
                             "session_app": l.session_app, "label_source": l.label_source, "process": l.process,
                             "process_share": float(l.process_share) if l.process_share != "" else np.nan, "app": l.app,
                             "process_breakdown": json.dumps(dict(b.most_common())) if b else "",
                             "keep_120": str(l.keep) == "True", "drop_reason_120": l.drop_reason})
    F = pd.DataFrame(rows)
    cls = F.apply(classify, axis=1, result_type="expand")
    F["category"], F["reviewed_label"], F["confidence"], F["reason"] = cls[0], cls[1], cls[2], cls[3]
    F["include_strict"] = F.keep_120 & F.confidence.eq("high")
    F["include_process"] = F.confidence.eq("high")
    F["edge_5s"] = F.drop_reason_120.str.startswith("session edge")

    # independent cross-check against Charles's provisional candidates
    C = charles_candidates()
    key = ["group", "session", "dur_key"] + MATCH_COLS
    Fk = F.astype({c: str for c in MATCH_COLS}).assign(dur_key=F.duration.round(3).map("{:.3f}".format))
    Ck = C.astype({c: str for c in MATCH_COLS}).assign(dur_key=C.duration.round(3).map("{:.3f}".format))
    Ck = Ck.rename(columns={"app": "charles_label", "flow_id": "charles_flow_id"})[key + ["charles_label", "charles_flow_id"]]
    dup = Ck.duplicated(key, keep=False).sum()
    M = Fk.merge(Ck.drop_duplicates(key), on=key, how="left")
    assert len(M) == len(F)
    F["charles_label"] = M.charles_label.fillna("").values
    F["charles_flow_id"] = M.charles_flow_id.fillna("").values
    matched = F[F.charles_label != ""]
    cross = {"charles_candidates": len(C), "charles_by_app": C.app.value_counts().to_dict(),
             "matched_to_our_flows": int(len(matched)), "unmatched_charles": int(len(C) - matched.charles_flow_id.nunique()),
             "ambiguous_keys_in_charles": int(dup),
             "label_agreement_with_our_reviewed_label": float((matched.reviewed_label == matched.charles_label).mean()),
             "disagreements": matched[matched.reviewed_label != matched.charles_label][
                 ["group", "session", "flow_id", "category", "reviewed_label", "charles_label"]].to_dict("records"),
             "our_high_confidence_not_in_charles": int((F.include_process & (F.charles_label == "")).sum()),
             "in_charles_by_our_category": matched.category.value_counts().to_dict()}

    # fixed review sample
    rng = np.random.default_rng(2026)
    pick = []
    for app in APPS:
        pool = F[(F.reviewed_label == app) | ((F.session_app == app) & (F.label_source == "session"))]
        sessions = sorted(pool.session.unique())
        take = []
        for i in range(25):                                  # round-robin over sessions, random flow within each
            s = sessions[i % len(sessions)]
            cand = pool[(pool.session == s) & ~pool.index.isin(take)]
            if len(cand):
                take.append(rng.choice(cand.index))
        pick += take
    pick += list(F[F.session_app == "idle"].index)
    bg = F[F.category.eq("background process") & ~F.index.isin(pick)]
    pick += list(rng.choice(bg.index, size=min(15, len(bg)), replace=False))
    S = F.loc[sorted(set(pick))]

    summary = {"experiment": "122", "flows": len(F), "upstream_commit_for_cross_check": UPSTREAM,
               "by_category": F.category.value_counts().to_dict(),
               "by_group_category": {g: d.category.value_counts().to_dict() for g, d in F.groupby("group")},
               "by_session": {f"{g}/{s}": {"flows": len(d), "session_app": d.session_app.iloc[0],
                                           "reviewed": d.reviewed_label.replace("", "(none)").value_counts().to_dict(),
                                           "include_strict": int(d.include_strict.sum()), "include_process": int(d.include_process.sum())}
                              for (g, s), d in F.groupby(["group", "session"])},
               "disagreements_session_vs_process": int(F.category.eq("process disagrees with session").sum()),
               "exclusions": {"background": int(F.confidence.eq("background").sum()), "unknown": int(F.confidence.eq("unknown").sum()),
                              "mixed_low": int(F.confidence.eq("low").sum()), "edge_5s_among_high": int((F.include_process & F.edge_5s).sum())},
               "include_strict_by_app": F[F.include_strict].reviewed_label.value_counts().to_dict(),
               "include_process_by_app": F[F.include_process].reviewed_label.value_counts().to_dict(),
               "sample": {"flows": len(S), "by_category": S.category.value_counts().to_dict(),
                          "by_reviewed_label": S.reviewed_label.replace("", "(none)").value_counts().to_dict()},
               "cross_check_charles": cross}
    cols = ["group", "session", "flow_id", "start_rel", "duration", "transport", "server_port", "packets", "session_app",
            "label_source", "process", "process_share", "process_breakdown", "category", "reviewed_label", "confidence", "reason",
            "include_strict", "include_process", "edge_5s", "drop_reason_120", "charles_label", "charles_flow_id"]
    F["duration"] = F.duration.round(3)
    F[cols].to_csv(OUT / "label_audit_flows.csv", index=False)
    S[cols].assign(human_decision="", human_note="").to_csv(OUT / "label_audit_sample.csv", index=False)
    (OUT / "label_audit_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps({k: summary[k] for k in ("flows", "by_category", "disagreements_session_vs_process", "exclusions",
                                              "include_strict_by_app", "include_process_by_app", "sample")}, indent=1, default=str))
    print(json.dumps({k: v for k, v in cross.items() if k != "disagreements"}, indent=1))
    print("disagreements with Charles:", cross["disagreements"][:20])


if __name__ == "__main__":
    main()
