"""Experiment 041: feasibility of our own labelled captures (understanding only; no models, production unchanged).

Command: .venv/bin/python src/exp041_capture_feasibility.py
Reads features of all 411 flows (both tasks; no test labels) and train+validation labels.
  1. Flow definition: packets per flow, capture span, timestamp resolution, largest gaps (idle-timeout bound), Task 2 opening.
  2. Feature formulas: each identity checked on all 411 flows in both tasks; Task 2 row vs Task 1 row of the same flow.
  3. Packet sizes: exact sizes recovered where a direction has 1-2 packets (mean ± population std), TCP openings decomposed.
  4. Facebook/Instagram traffic types: rules fixed before running (below), ranges per type, cross-check with clustering.
  5. Labelling clue: how often a labelled flow starts within 60 s of an Instagram flow, per app (understanding only; capture
     order is never used as a model input).
"""
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import adjusted_rand_score

from cv import DATA, load_task

T1, T2 = "task1_static", "task2_realtime_prefix5"
SPLITS = ("train", "validation", "test")


def load_all(task):
    return pd.concat([pd.read_csv(DATA / task / f"{s}_features.csv") for s in SPLITS], ignore_index=True)


def check(name, ok, mask=None):
    ok = np.asarray(ok)
    if mask is not None:
        ok = ok[np.asarray(mask)]
    print(f"  {name:66s} {int(ok.sum())}/{len(ok)}")


def part_flow(A, P):
    print("== 1. flow definition")
    n = A.packet_count_up + A.packet_count_down
    end = A.start_rel + A.duration
    ids = A.flow_id.str[5:].astype(int)
    print(f"  flows {len(A)}; packets per flow min {n.min()}, max {n.max()}; Task 2 packets per flow: {sorted((P.packet_count_up + P.packet_count_down).unique())}")
    print(f"  start_rel 0 .. {A.start_rel.max():.1f} s; last packet at {end.max():.1f} s ({end.max() / 60:.1f} min)")
    print(f"  flow_id numbers {ids.min()} .. {ids.max()} ({len(ids)} kept); Spearman(flow_id, start_rel) = {ids.corr(A.start_rel, method='spearman'):.3f}")
    print(f"  longest flow {A.duration.max():.0f} s; largest gap inside any flow {A.max_iat.max():.1f} s (idle timeout > this)")
    print(f"  ten largest gaps: {np.round(np.sort(A.max_iat.values)[-10:], 1)}")
    print(f"  flows with no upstream / no downstream packet: Task 1 {(A.packet_count_up == 0).sum()} / {(A.packet_count_down == 0).sum()}, "
          f"Task 2 {(P.packet_count_up == 0).sum()} / {(P.packet_count_down == 0).sum()}")
    for X, t in ((A, T1), (P, T2)):
        d = X.duration[X.duration > 0]
        print(f"  {t}: durations on a 1 µs grid {np.isclose(d * 1e6, (d * 1e6).round(), atol=1e-3).mean():.3f}; "
              f"min_iat == 0 in {(X.min_iat == 0).mean():.1%} of flows; smallest non-zero gap {X.min_iat[X.min_iat > 0].min() * 1e6:.1f} µs")
    print("  transport:", A.transport.value_counts().to_dict(), " server_port:", A.server_port.value_counts().to_dict())


def part_formulas(A, P):
    print("\n== 2. feature formulas (all 411 flows)")
    for X, t in ((A, T1), (P, T2)):
        print(f" {t}")
        u, d = X.packet_count_up, X.packet_count_down
        n = u + d
        for dr in ("up", "down"):
            c, b, ms, sd = X[f"packet_count_{dr}"], X[f"bytes_{dr}"], X[f"mean_pkt_size_{dr}"], X[f"std_pkt_size_{dr}"]
            check(f"bytes_{dr} is an integer", np.isclose(b, b.round()))
            check(f"mean_pkt_size_{dr} = bytes_{dr} / packet_count_{dr} (0 if no packets)", np.isclose(ms, np.where(c > 0, b / c.clip(lower=1), 0)))
            check(f"std_pkt_size_{dr} = 0 when <= 1 packet", sd == 0, c <= 1)
            check(f"2 packets: mean ± std are integers (population std, ddof 0)", np.isclose(ms - sd, (ms - sd).round(), atol=1e-5) & np.isclose(ms + sd, (ms + sd).round(), atol=1e-5), c == 2)
            check(f"std_pkt_size_{dr}^2 <= (max size - mean)(mean - 60) with max 1514", sd ** 2 <= (1514 - ms) * (ms - 60) + 1e-6, c > 0)
        check("mean_iat = duration / (packets - 1)", np.isclose(X.mean_iat, X.duration / (n - 1), rtol=1e-6, atol=1e-9))
        check("min_iat <= mean_iat <= max_iat <= duration", (X.min_iat <= X.mean_iat + 1e-9) & (X.mean_iat <= X.max_iat + 1e-9) & (X.max_iat <= X.duration + 1e-9))
        check("min_iat + max_iat <= duration (>= 3 packets)", X.min_iat + X.max_iat <= X.duration + 1e-9, n >= 3)
        check("std_iat^2 <= (max_iat - mean_iat)(mean_iat - min_iat) (population std)", X.std_iat ** 2 <= (X.max_iat - X.mean_iat) * (X.mean_iat - X.min_iat) + 1e-9)
        check("up_down_packet_ratio = up / max(down, 1)", np.isclose(X.up_down_packet_ratio, u / d.clip(lower=1)))
        check("up_down_byte_ratio = bytes_up / max(bytes_down, 1)", np.isclose(X.up_down_byte_ratio, X.bytes_up / X.bytes_down.clip(lower=1)))
        b = X.burst_count
        check("burst_count = 1 when max_iat < 1.0 s", b == 1, X.max_iat < 1.0)
        check("burst_count >= 2 when max_iat >= 1.0 s", b >= 2, X.max_iat >= 1.0)
        check("1 <= burst_count <= packets", (b >= 1) & (b <= n))
        check("(burst_count - 1) gaps of >= 1.0 s fit in duration", (b - 1) * 1.0 <= X.duration + 1e-6)
        print(f"   burst threshold bracket: largest max_iat with 1 burst {X.max_iat[b == 1].max():.4f} s, smallest max_iat with >= 2 bursts {X.max_iat[b >= 2].min():.4f} s")
    print(" Task 2 gaps: population or sample std? (4 gaps: the middle two are fixed by sum, min, max and std)")
    for name, f in (("population std (ddof 0)", 1.0), ("sample std (ddof 1)", 3 / 4)):
        S2 = 4 * (P.std_iat ** 2 * f + P.mean_iat ** 2)
        r, q = P.duration - P.min_iat - P.max_iat, S2 - P.min_iat ** 2 - P.max_iat ** 2
        disc = 2 * q - r ** 2
        x = (r + np.sqrt(disc.clip(lower=0))) / 2
        tol = 1e-5  # values are stored with 9 decimals
        check(f"middle gaps real and within [min_iat, max_iat] under {name}", (disc >= -tol) & (x <= P.max_iat + tol) & (r - x >= P.min_iat - tol))
    print(" Task 2 opening vs Task 1 flow")
    c = {"same flow_id, start_rel, transport, server_port, split": (P.flow_id == A.flow_id) & (P.start_rel == A.start_rel) & (P.transport == A.transport) & (P.server_port == A.server_port) & (P.split == A.split),
         "prefix packets and bytes <= full, per direction": (P.packet_count_up <= A.packet_count_up) & (P.packet_count_down <= A.packet_count_down) & (P.bytes_up <= A.bytes_up) & (P.bytes_down <= A.bytes_down),
         "prefix duration <= full; prefix max_iat <= full; prefix min_iat >= full": (P.duration <= A.duration + 1e-9) & (P.max_iat <= A.max_iat + 1e-9) & (P.min_iat >= A.min_iat - 1e-9),
         "prefix burst_count <= full burst_count": P.burst_count <= A.burst_count}
    for k, v in c.items():
        check(k, v)
    five = (A.packet_count_up + A.packet_count_down) == 5
    num = [c for c in A.columns if c not in ("flow_id", "split", "transport")]
    check("flows with exactly 5 packets: Task 1 row == Task 2 row", np.isclose(A.loc[five, num], P.loc[five, num]).all(1))


def exact_sizes(X, dr, tr):
    cnt = Counter()
    for _, r in X[X.transport == tr].iterrows():
        c, m, s = r[f"packet_count_{dr}"], r[f"mean_pkt_size_{dr}"], r[f"std_pkt_size_{dr}"]
        if c >= 1 and s == 0:
            cnt[round(m)] += c
        elif c == 2:
            cnt[round(m - s)] += 1
            cnt[round(m + s)] += 1
    return cnt


def three_sizes(total, std, known):
    """Integer sizes (known, x, y) with the given sum and population std, or None."""
    r, q = total - known, 3 * (std ** 2 + (total / 3) ** 2) - known ** 2
    disc = 2 * q - r * r
    if disc < 0:
        return None
    x = (r + np.sqrt(disc)) / 2
    return tuple(sorted((known, round(x), round(r - x)))) if abs(x - round(x)) < 1e-3 else None


def part_sizes(A, P):
    print("\n== 3. packet sizes (exactly known from 1-2 packets or std 0)")
    for tr in ("tcp", "udp"):
        for dr in ("up", "down"):
            c = exact_sizes(P, dr, tr)
            print(f"  Task 2 {tr} {dr}: {sum(c.values())} sizes; smallest {sorted(c)[:5]}; most common {c.most_common(8)}")
    print(f"  smallest mean size anywhere: up {min(A.mean_pkt_size_up.min(), P.mean_pkt_size_up[P.packet_count_up > 0].min()):.0f}, "
          f"down {min(A.mean_pkt_size_down.min(), P.mean_pkt_size_down[P.packet_count_down > 0].min()):.0f}; "
          f"largest mean size {max(A.mean_pkt_size_up.max(), A.mean_pkt_size_down.max(), P.mean_pkt_size_up.max(), P.mean_pkt_size_down.max()):.0f}")
    print("  Task 2 TCP openings (up/down packets):", P[P.transport == "tcp"].groupby(["packet_count_up", "packet_count_down"]).size().to_dict())
    print("  Task 2 UDP openings (up/down packets):", P[P.transport == "udp"].groupby(["packet_count_up", "packet_count_down"]).size().to_dict())
    t = P[(P.transport == "tcp") & (P.packet_count_up == 3) & (P.packet_count_down == 2)]
    dec = Counter(next((s for k in (66, 145) if (s := three_sizes(r.bytes_up, r.std_pkt_size_up, k))), None) for _, r in t.iterrows())
    print(f"  TCP 3 up / 2 down: down bytes {Counter(t.bytes_down).most_common(3)}; up sizes {dec.most_common(8)}")
    t = P[(P.transport == "tcp") & (P.packet_count_up == 2) & (P.packet_count_down == 3)]
    print(f"  TCP 2 up / 3 down: up pairs {Counter(zip((t.mean_pkt_size_up - t.std_pkt_size_up).round(), (t.mean_pkt_size_up + t.std_pkt_size_up).round())).most_common(4)}; "
          f"down bytes {Counter(t.bytes_down).most_common(3)}")
    t = P[(P.transport == "tcp") & (P.packet_count_up == 4)]
    print(f"  TCP 4 up / 1 down: down bytes {Counter(t.bytes_down).most_common(2)}; up bytes {t.bytes_up.min()}..{t.bytes_up.max()}")


TYPES = ["TCP keep-alive", "short TCP", "short QUIC fetch", "QUIC burst", "slow QUIC trickle", "QUIC media download", "QUIC upload-heavy"]


def traffic_type(r):
    """Rules fixed before running."""
    if r.transport == "tcp":
        return "TCP keep-alive" if r.duration >= 100 else "short TCP"
    if r.duration < 1:
        return "short QUIC fetch"
    if r.duration < 60:
        return "QUIC burst"
    if r.bytes_down >= 1e6:
        return "QUIC media download"
    if r.bytes_up >= 250e3 and r.bytes_up > r.bytes_down:
        return "QUIC upload-heavy"
    return "slow QUIC trickle"


def part_types(A, P, y):
    print("\n== 4. Facebook/Instagram traffic types (labelled flows)")
    m = y.isin(["facebook", "instagram"]).values
    F = A[m].copy()
    F["app"] = y[m].values
    F["packets"] = F.packet_count_up + F.packet_count_down
    F["type"] = F.apply(traffic_type, axis=1)
    F["p5"] = [f"{r.transport} {r.packet_count_up}/{r.packet_count_down} {r.bytes_up}/{r.bytes_down}" for _, r in P[m].iterrows()]
    for ty in TYPES:
        g = F[F.type == ty]
        if g.empty:
            continue
        rng = lambda s, f="{:.0f}": f"{f.format(s.min())}-{f.format(s.max())}"
        print(f"  {ty}: facebook {int((g.app == 'facebook').sum())}, instagram {int((g.app == 'instagram').sum())}")
        print(f"    duration {rng(g.duration, '{:.2f}')} s | packets {rng(g.packets)} | bytes up {rng(g.bytes_up)} | bytes down {rng(g.bytes_down)} | "
              f"mean size up {rng(g.mean_pkt_size_up)} down {rng(g.mean_pkt_size_down)} | mean_iat {rng(g.mean_iat, '{:.2f}')} s | "
              f"max_iat {rng(g.max_iat, '{:.1f}')} s | bursts {rng(g.burst_count)}")
        print(f"    flows: {', '.join(f'{f[5:]} ({a[:2]})' for f, a in zip(g.flow_id, g.app))}")
        print(f"    openings: {Counter(g.p5).most_common(4)}")
    Z = np.log1p(F[["duration", "packets", "bytes_up", "bytes_down", "mean_pkt_size_up", "mean_pkt_size_down", "mean_iat", "max_iat"]].values)
    Z = np.column_stack([(Z - Z.mean(0)) / Z.std(0), 2 * (F.transport == "udp").values])
    k = F.type.nunique()
    lab = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Z)
    print(f"  cross-check: Ward clustering into {k} groups vs rule types, adjusted Rand {adjusted_rand_score(F.type, lab):.2f}")
    print(pd.crosstab(F.type, lab).to_string())
    return F


def part_labelling(A, y):
    print("\n== 5. labelling clue: share of labelled flows starting within w s of an Instagram flow (understanding only)")
    L = A.assign(app=y.values)
    ig = L.start_rel[L.app == "instagram"].values
    span = A.start_rel.max()
    for w in (10, 60):
        row = []
        for app in sorted(L.app.unique()):
            s = L[L.app == app]
            near = [np.any((np.abs(ig - t) <= w) & (np.abs(ig - t) > 0)) for t in s.start_rel]
            row.append(f"{app} {int(np.sum(near))}/{len(s)} ({np.mean(near):.0%})")
        cover = np.mean([np.any(np.abs(ig - t) <= w) for t in np.linspace(0, span, 4000)])
        print(f"  w = {w:2d} s: " + ", ".join(row) + f"; share of capture time within w of an Instagram flow {cover:.0%}")


def main():
    A, P = load_all(T1), load_all(T2)
    assert (A.flow_id == P.flow_id).all()
    part_flow(A, P)
    part_formulas(A, P)
    part_sizes(A, P)
    LA, y = load_task(T1)
    part_types(LA, load_task(T2)[0], y)
    part_labelling(LA, y)


if __name__ == "__main__":
    main()
