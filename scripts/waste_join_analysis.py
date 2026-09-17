#!/usr/bin/env python3
"""Target-level truth from the ACAS_04 join: saturation, envelope, role."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
JOIN = ROOT / "_inv" / "missile_join.csv"
rows = list(csv.DictReader(JOIN.open(encoding="utf-8")))

def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

for r in rows:
    r["date"] = "0914" if "vs2_" in r["batch"] else "0912"
    r["plus_side"] = "red" if "plus_red" in r["batch"] else "blue"
    r["own_side"] = r["side"]
    r["side_kind"] = "plus" if ((r["plus_side"] == "red" and r["side"] == "Red") or
                                (r["plus_side"] == "blue" and r["side"] == "Blue")) else "yuandi"
    r["role"] = "lead" if r["launcher"] in ("1", "3") else "wing"
    r["hit"] = 1 if r["hit_strict"] == "1" else 0
    sr, rmax = f(r["env_slantRange"]), f(r["env_Rmax"])
    r["range_frac"] = (sr / rmax) if (sr and rmax) else None
    r["aspect"] = f(r["env_aspect"])
    r["lock"] = r["locked_tgt_id"] or None

print(f"rows={len(rows)}")

def rate(sel):
    n = len(sel)
    return (sum(x["hit"] for x in sel) / n, n) if n else (0.0, 0)

print("\n=== A. hit rate of the Nth missile fired at the same target (same case, same side) ===")
for date in ("0912", "0914"):
    groups = defaultdict(list)
    for r in rows:
        if r["date"] == date and r["lock"]:
            groups[(r["batch"], r["case"], r["side_kind"], r["lock"])].append(r)
    ord_hits, ord_tot = defaultdict(int), defaultdict(int)
    for g in groups.values():
        g.sort(key=lambda x: float(x["launch_time"]))
        for i, r in enumerate(g):
            k = min(i + 1, 4)
            ord_tot[k] += 1
            ord_hits[k] += r["hit"]
    print(f"  {date}: " + "  ".join(
        f"{k}th={ord_hits[k]}/{ord_tot[k]} ({ord_hits[k]/ord_tot[k]:.0%})" for k in sorted(ord_tot)))

print("\n=== B. hit rate by range fraction at launch (slantRange / Rmax) ===")
bins = [(0, 0.4), (0.4, 0.55), (0.55, 0.7), (0.7, 0.85), (0.85, 1.01), (1.01, 9)]
for date in ("0912", "0914"):
    out = []
    for lo, hi in bins:
        sel = [r for r in rows if r["date"] == date and r["range_frac"] is not None and lo <= r["range_frac"] < hi]
        rt, n = rate(sel)
        out.append(f"{lo:.2f}-{hi:.2f}:{rt:.0%}(n={n})")
    print(f"  {date}: " + "  ".join(out))

print("\n=== C. role x date (plus side): launches, hit rate, median range frac ===")
for date in ("0912", "0914"):
    for role in ("lead", "wing"):
        sel = [r for r in rows if r["date"] == date and r["side_kind"] == "plus" and r["role"] == role]
        rt, n = rate(sel)
        rf = sorted(x["range_frac"] for x in sel if x["range_frac"] is not None)
        med = rf[len(rf)//2] if rf else float("nan")
        sat = Counter()
        for r in sel:
            if r["lock"]:
                sat[(r["batch"], r["case"], r["lock"])] += 1
        over = sum(1 for v in sat.values() if v >= 3)
        print(f"  {date} {role}: launches={n:4d} rate={rt:6.1%} median_range_frac={med:.3f} targets_with_>=3_shots={over}")

print("\n=== D. aspect at launch (rad) hits vs misses, plus side, 0914 ===")
for role in ("lead", "wing"):
    for hit in (1, 0):
        sel = [r["aspect"] for r in rows if r["date"] == "0914" and r["side_kind"] == "plus"
               and r["role"] == role and r["hit"] == hit and r["aspect"] is not None]
        sel.sort()
        if sel:
            print(f"  {role} hit={hit}: n={len(sel):4d} median_aspect={sel[len(sel)//2]:.3f} rad "
                  f"({sel[len(sel)//2]*57.3:.1f} deg)")

print("\n=== E. 原版 comparison: role x date (opponent side) ===")
for date in ("0912", "0914"):
    for role in ("lead", "wing"):
        sel = [r for r in rows if r["date"] == date and r["side_kind"] == "yuandi" and r["role"] == role]
        rt, n = rate(sel)
        print(f"  {date} 原版 {role}: launches={n:4d} rate={rt:6.1%}")

print("\n=== F. per-scenario: 0914 plus wingman launches with zero hits ===")
scen = defaultdict(lambda: {"lau": 0, "hit": 0, "wing_lau": 0, "wing_hit": 0})
for r in rows:
    if r["date"] != "0914" or r["side_kind"] != "plus":
        continue
    s = ((int(r["case"]) - 1) % 20) + 1
    scen[s]["lau"] += 1; scen[s]["hit"] += r["hit"]
    if r["role"] == "wing":
        scen[s]["wing_lau"] += 1; scen[s]["wing_hit"] += r["hit"]
for s in sorted(scen, key=lambda k: -(scen[k]["wing_lau"] - scen[k]["wing_hit"]))[:8]:
    v = scen[s]
    print(f"  s{s:2d}: plus lau={v['lau']:3d} hit={v['hit']:3d} | wing lau={v['wing_lau']:3d} hit={v['wing_hit']:3d} "
          f"(wing waste={v['wing_lau']-v['wing_hit']})")

# charts
fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
ax = axes[0]
for date, col in (("0912", "#888"), ("0914", "#c0392b")):
    ks, vs = [], []
    for lo, hi in bins:
        sel = [r for r in rows if r["date"] == date and r["range_frac"] is not None and lo <= r["range_frac"] < hi]
        if sel:
            ks.append(f"{lo:.2f}+" if hi > 5 else f"{lo:.2f}-{hi:.2f}")
            vs.append(100 * sum(x["hit"] for x in sel) / len(sel))
    ax.plot(ks, vs, "o-", label=date, color=col)
ax.set_title("hit rate vs slantRange/Rmax at launch"); ax.set_ylabel("%")
ax.tick_params(axis="x", rotation=30); ax.legend()

ax = axes[1]
labels, lv, wv, lr, wr = [], [], [], [], []
for date in ("0912", "0914"):
    for role in ("lead", "wing"):
        sel = [r for r in rows if r["date"] == date and r["side_kind"] == "plus" and r["role"] == role]
        labels.append(f"{date}\n{role}")
        (lv if role == "lead" else wv).append(len(sel))
        (lr if role == "lead" else wr).append(100 * sum(x["hit"] for x in sel) / max(1, len(sel)))
ax.bar(range(4), [lv[0], wv[0], lv[1], wv[1]], color=["#888", "#888", "#c0392b", "#c0392b"])
ax.set_xticks(range(4)); ax.set_xticklabels(labels)
ax.set_title("plus launches: lead vs wingman"); ax.set_ylabel("launches / 200 cases")

ax = axes[2]
ax.bar(range(4), [lr[0], wr[0], lr[1], wr[1]], color=["#888", "#888", "#c0392b", "#c0392b"])
ax.set_xticks(range(4)); ax.set_xticklabels(labels)
ax.set_title("plus strict hit rate: lead vs wingman"); ax.set_ylabel("%")
fig.tight_layout(); fig.savefig(ROOT / "waste_charts2.png", dpi=130)
print("\nwrote waste_charts2.png")
