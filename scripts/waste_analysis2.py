#!/usr/bin/env python3
"""Second pass: per-slot efficiency, per-scenario waste ranking, red-side losses, charts."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
rows = json.loads((ROOT / "waste_acmi_missiles.json").read_text(encoding="utf-8"))
cases = list(csv.DictReader((ROOT / "waste_acmi_cases.csv").open(encoding="utf-8-sig")))

SIDE_OF_SLOT = {1: "Red", 2: "Red", 3: "Blue", 4: "Blue"}
ROLE = {1: "长机", 2: "僚机", 3: "长机", 4: "僚机"}


def sel(date, side=None, slot=None, scenario=None):
    out = []
    for r in rows:
        if r["date"] != date:
            continue
        if side and r["side"] != side:
            continue
        if slot and r["launcher"] != slot:
            continue
        if scenario and ((r["case"] - 1) % 20) + 1 != scenario:
            continue
        out.append(r)
    return out


print("=== per-slot launches and strict hit rate (plus side only) ===")
print("  date  dir        slot role   launches  hits  hit_rate")
for date in ("0912", "0914"):
    for tag, ps in (("plus_red", "red"), ("plus_blue", "blue")):
        own = (1, 2) if ps == "red" else (3, 4)
        for slot in own:
            s = [r for r in rows if r["date"] == date and r["tag"] == tag and r["launcher"] == slot]
            h = sum(r["hit_strict"] for r in s)
            print(f"  {date}  {tag:10} {slot:4d} {ROLE[slot]}  {len(s):8d} {h:5d}  {h/len(s) if s else 0:7.1%}")

print("\n=== plus side: launches & hit rate by role (lead vs wingman), both dates ===")
for date in ("0912", "0914"):
    for role, slots in (("长机(1/3)", None), ("僚机(2/4)", None)):
        pass
    lead = [r for r in rows if r["date"] == date and r["side"] == "plus"
            and ((r["plus_side"] == "red" and r["launcher"] == 1) or (r["plus_side"] == "blue" and r["launcher"] == 3))]
    wing = [r for r in rows if r["date"] == date and r["side"] == "plus"
            and ((r["plus_side"] == "red" and r["launcher"] == 2) or (r["plus_side"] == "blue" and r["launcher"] == 4))]
    for label, s in (("长机", lead), ("僚机", wing)):
        h = sum(r["hit_strict"] for r in s)
        print(f"  {date} {label}: launches={len(s):5d} hits={h:4d} hit_rate={h/len(s) if s else 0:6.1%}")

print("\n=== per-scenario: plus launches, strict hits, hit rate, ranked by worst hit rate (0914) ===")
print("  scen  0912_lau 0912_rate  0914_lau 0914_hit 0914_rate  d_lau")
scen_rows = []
for s in range(1, 21):
    a = sel("0912", "plus", scenario=s)
    b = sel("0914", "plus", scenario=s)
    ah, bh = sum(x["hit_strict"] for x in a), sum(x["hit_strict"] for x in b)
    ra = ah / len(a) if a else 0
    rb = bh / len(b) if b else 0
    scen_rows.append({"scenario": s, "lau0912": len(a), "hit0912": ah, "rate0912": ra,
                      "lau0914": len(b), "hit0914": bh, "rate0914": rb, "d_lau": len(b) - len(a)})
for r in sorted(scen_rows, key=lambda x: x["rate0914"]):
    print(f"  {r['scenario']:4d}  {r['lau0912']:8d} {r['rate0912']:9.1%}  "
          f"{r['lau0914']:8d} {r['hit0914']:8d} {r['rate0914']:9.1%}  {r['d_lau']:+5d}")

print("\n=== red-side losses (原版 wins) ===")
for date in ("0912", "0914"):
    c = Counter()
    byscen = defaultdict(Counter)
    for r in cases:
        if r["date"] != date:
            continue
        if r["winner"] == "red":
            pass
        else:
            pass
    # the report 'winner' is the SIDE that won, not plus
    for r in cases:
        if r["date"] != date:
            continue
        if r["winner"] == "blue":
            c[r["reason"]] += 1
            byscen[r["reason"]][int(r["scenario"])] += 1
    tot = sum(c.values())
    print(f"  {date}: blue(=原版) won {tot} -> " + ", ".join(f"{k}={v}" for k, v in c.most_common()))
    for k, v in byscen.items():
        worst = ", ".join(f"s{s}x{n}" for s, n in sorted(v.items(), key=lambda x: -x[1])[:6])
        print(f"      {k}: {worst}")

# ---- charts ----
fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
ax = axes[0]
x = [r["scenario"] for r in scen_rows]
ax.bar([i - 0.2 for i in x], [r["lau0912"] for r in scen_rows], width=0.4, label="09-12", color="#888")
ax.bar([i + 0.2 for i in x], [r["lau0914"] for r in scen_rows], width=0.4, label="09-14", color="#c0392b")
ax.set_title("plus launches per scenario (5 repeats x 2 dirs)")
ax.set_xlabel("base scenario"); ax.set_ylabel("launches / 10 cases"); ax.legend()

ax = axes[1]
ax.bar([i - 0.2 for i in x], [r["rate0912"] * 100 for r in scen_rows], width=0.4, label="09-12", color="#888")
ax.bar([i + 0.2 for i in x], [r["rate0914"] * 100 for r in scen_rows], width=0.4, label="09-14", color="#c0392b")
ax.set_title("plus strict hit rate per scenario")
ax.set_xlabel("base scenario"); ax.set_ylabel("hit rate %"); ax.legend()

ax = axes[2]
labels, v12, v14 = [], [], []
for ps, own in (("red", (1, 2)), ("blue", (3, 4))):
    for slot in own:
        labels.append(f"{ps[:1]}{slot}")
        a = [r for r in rows if r["date"] == "0912" and r["side"] == "plus" and r["launcher"] == slot and r["plus_side"] == ps]
        b = [r for r in rows if r["date"] == "0914" and r["side"] == "plus" and r["launcher"] == slot and r["plus_side"] == ps]
        v12.append(len(a)); v14.append(len(b))
ax.bar([i - 0.2 for i in range(len(labels))], v12, width=0.4, label="09-12", color="#888")
ax.bar([i + 0.2 for i in range(len(labels))], v14, width=0.4, label="09-14", color="#c0392b")
ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels)
ax.set_title("plus launches per aircraft (2 dirs combined)")
ax.set_ylabel("launches / 200 cases"); ax.legend()

fig.tight_layout()
fig.savefig(ROOT / "waste_charts.png", dpi=130)

with (ROOT / "waste_by_scenario.csv").open("w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(scen_rows[0].keys()))
    w.writeheader(); w.writerows(scen_rows)
print("\nwrote waste_by_scenario.csv + waste_charts.png")
