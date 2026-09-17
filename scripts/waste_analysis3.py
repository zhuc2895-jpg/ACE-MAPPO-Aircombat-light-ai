#!/usr/bin/env python3
"""Corrected: red-side losses per direction, and extra-launches-vs-extra-hits accounting."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
rows = json.loads((ROOT / "waste_acmi_missiles.json").read_text(encoding="utf-8"))
cases = list(csv.DictReader((ROOT / "waste_acmi_cases.csv").open(encoding="utf-8-sig")))

print("=== plus-side record per batch (winner is the SIDE, plus_side tells us who plus was) ===")
for date in ("0912", "0914"):
    for tag in ("plus_red", "plus_blue"):
        sel = [c for c in cases if c["date"] == date and c["tag"] == tag]
        plus_side = sel[0]["plus_side"]
        wins = sum(1 for c in sel if c["winner"] == plus_side)
        loss = sum(1 for c in sel if c["winner"] not in (plus_side, "draw"))
        draw = sum(1 for c in sel if c["winner"] == "draw")
        print(f"  {date} {tag:10} plus={plus_side:4}  plus_wins={wins:3d}  plus_losses={loss:3d}  draws={draw}")

print("\n=== plus RED batch: how the 原版 beat plus (loss reasons x scenario) ===")
for date in ("0912", "0914"):
    sel = [c for c in cases if c["date"] == date and c["tag"] == "plus_red"]
    lost = [c for c in sel if c["winner"] == "blue"]
    c = Counter(x["reason"] for x in lost)
    print(f"  {date}: plus(red) lost {len(lost)} -> " + ", ".join(f"{k}={v}" for k, v in c.most_common()))
    byscen = defaultdict(Counter)
    for x in lost:
        byscen[x["reason"]][int(x["scenario"])] += 1
    for k, v in byscen.items():
        print(f"      {k}: " + ", ".join(f"s{s}x{n}" for s, n in sorted(v.items(), key=lambda t: (-t[1], t[0]))))

print("\n=== extra launches vs extra hits, per scenario, plus side (0914 - 0912) ===")
print("  scen  d_lau  d_hit  extra_launches_per_extra_hit")
acc = []
for s in range(1, 21):
    a = [r for r in rows if r["date"] == "0912" and r["side"] == "plus" and ((r["case"] - 1) % 20) + 1 == s]
    b = [r for r in rows if r["date"] == "0914" and r["side"] == "plus" and ((r["case"] - 1) % 20) + 1 == s]
    dl = len(b) - len(a)
    dh = sum(x["hit_strict"] for x in b) - sum(x["hit_strict"] for x in a)
    ratio = (dl / dh) if dh else float("inf")
    acc.append((s, dl, dh, ratio))
    print(f"  {s:4d}  {dl:+5d}  {dh:+5d}  {'inf' if dh == 0 else f'{ratio:8.1f}'}")
tot_dl = sum(x[1] for x in acc)
tot_dh = sum(x[2] for x in acc)
print(f"  TOTAL {tot_dl:+5d} {tot_dh:+5d}  -> {tot_dl/tot_dh:.1f} extra launches per extra hit" if tot_dh else "")

print("\n=== role accounting (plus side, both dates, both directions) ===")
for date in ("0912", "0914"):
    lead = [r for r in rows if r["date"] == date and r["side"] == "plus"
            and ((r["plus_side"] == "red" and r["launcher"] == 1) or (r["plus_side"] == "blue" and r["launcher"] == 3))]
    wing = [r for r in rows if r["date"] == date and r["side"] == "plus"
            and ((r["plus_side"] == "red" and r["launcher"] == 2) or (r["plus_side"] == "blue" and r["launcher"] == 4))]
    for label, s in (("lead", lead), ("wing", wing)):
        h = sum(x["hit_strict"] for x in s)
        print(f"  {date} {label}: launches={len(s):5d} hits={h:4d} rate={h/len(s) if s else 0:6.1%}")

print("\n=== 原版 side, same view (did the opponent change too?) ===")
for date in ("0912", "0914"):
    for ps in ("red", "blue"):
        own = ((1, 2) if ps == "red" else (3, 4))
        s = [r for r in rows if r["date"] == date and r["side"] == "yuandi"
             and ((r["plus_side"] == "blue" and ps == "red") or (r["plus_side"] == "red" and ps == "blue"))
             and r["launcher"] in own]
        h = sum(x["hit_strict"] for x in s)
        if s:
            print(f"  {date} 原版 as {ps}: launches={len(s):5d} hits={h:4d} rate={h/len(s):6.1%}")
