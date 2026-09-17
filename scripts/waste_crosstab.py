#!/usr/bin/env python3
"""Disentangle: is the low hit rate a RANGE effect or a FOLLOW-UP-SHOT effect?"""
from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
rows = list(csv.DictReader((ROOT / "_inv" / "missile_join.csv").open(encoding="utf-8")))
def f(v):
    try: return float(v)
    except (TypeError, ValueError): return None
for r in rows:
    r["date"] = "0914" if "vs2_" in r["batch"] else "0912"
    r["plus_side"] = "red" if "plus_red" in r["batch"] else "blue"
    r["kind"] = "plus" if ((r["plus_side"]=="red" and r["side"]=="Red") or (r["plus_side"]=="blue" and r["side"]=="Blue")) else "yuandi"
    r["hit"] = 1 if r["hit_strict"]=="1" else 0
    sr, rx = f(r["env_slantRange"]), f(r["env_Rmax"])
    r["rf"] = sr/rx if (sr and rx) else None
    r["lock"] = r["locked_tgt_id"] or None

# ordinal within (batch, case, side, target)
groups = defaultdict(list)
for r in rows:
    if r["lock"]:
        groups[(r["batch"], r["case"], r["side"], r["lock"])].append(r)
for g in groups.values():
    g.sort(key=lambda x: float(x["launch_time"]))
    for i, r in enumerate(g):
        r["ordinal"] = i + 1
for r in rows:
    r.setdefault("ordinal", 1)

band = lambda v: ("<0.55" if v < 0.55 else "0.55-0.70" if v < 0.70 else "0.70+" if v else None)

print("=== hit rate: ordinal x range band (plus side, both dates) ===")
print("  date  ordinal  band        n   rate")
for date in ("0912", "0914"):
    for od in (1, 2, 3):
        for b in ("<0.55", "0.55-0.70", "0.70+"):
            sel = [r for r in rows if r["date"]==date and r["kind"]=="plus"
                   and min(r["ordinal"],3)==od and r["rf"] is not None and band(r["rf"])==b]
            if sel:
                h = sum(x["hit"] for x in sel)
                print(f"  {date}  {od:6d}  {b:10} {len(sel):4d} {h/len(sel):6.1%}")

print("\n=== how much of the +334 extra launches is 3rd-or-later shots? ===")
for date in ("0912", "0914"):
    sel = [r for r in rows if r["date"]==date and r["kind"]=="plus"]
    c = {1:0,2:0,3:0,4:0}
    for r in sel:
        c[min(r["ordinal"],4)] += 1
    print(f"  {date}: " + "  ".join(f"ord{k}={v}" for k,v in c.items()) + f"   >=3 total={c[3]+c[4]}")

print("\n=== hits attributable to 1st shots only ===")
for date in ("0912", "0914"):
    sel = [r for r in rows if r["date"]==date and r["kind"]=="plus" and r["ordinal"]==1]
    h = sum(x["hit"] for x in sel)
    print(f"  {date}: first-shot launches={len(sel):4d} hits={h:4d} rate={h/len(sel):.1%}")

print("\n=== lead vs wing: ordinal mix (plus, 0914) ===")
for role in ("lead","wing"):
    sel = [r for r in rows if r["date"]=="0914" and r["kind"]=="plus"
           and (r["launcher"] in ("1","3")) == (role=="lead")]
    c = {1:0,2:0,3:0,4:0}
    for r in sel: c[min(r["ordinal"],4)] += 1
    print(f"  {role}: " + "  ".join(f"ord{k}={v}" for k,v in c.items()))
