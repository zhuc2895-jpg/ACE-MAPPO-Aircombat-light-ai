#!/usr/bin/env python3
"""Per-aircraft vs cross-aircraft repeat shots: which does the throttle need to catch?"""
from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
rows = list(csv.DictReader((ROOT / "_inv" / "missile_join.csv").open(encoding="utf-8")))
for r in rows:
    r["date"] = "0914" if "vs2_" in r["batch"] else ("0916" if "vs3_" in r["batch"] else "0912")
    r["plus_side"] = "red" if "plus_red" in r["batch"] else "blue"
    r["kind"] = "plus" if ((r["plus_side"]=="red" and r["side"]=="Red") or
                           (r["plus_side"]=="blue" and r["side"]=="Blue")) else "yuandi"
    r["hit"] = 1 if r["hit_strict"]=="1" else 0
    r["lock"] = r["locked_tgt_id"] or None
    r["t"] = float(r["launch_time"])
    r["role"] = "lead" if r["launcher"] in ("1","3") else "wing"

J = [r for r in rows if r["date"] == "0914" and r["kind"] == "plus"]
print(f"0914 plus missiles: {len(J)}")

# per-aircraft ordinal (same launcher, same target, same case)
g = defaultdict(list)
for r in J:
    if r["lock"]: g[(r["batch"], r["case"], r["launcher"], r["lock"])].append(r)
for grp in g.values():
    grp.sort(key=lambda x: x["t"])
    for i, r in enumerate(grp): r["ac_ord"] = i+1
for r in J: r.setdefault("ac_ord", 1)

print("\n=== per-AIRCRAFT ordinal (same aircraft, same target): count / hit rate ===")
for od in (1,2,3,4):
    s = [r for r in J if min(r["ac_ord"],4)==od]
    h = sum(r["hit"] for r in s)
    if s: print(f"  own-shot #{od}: n={len(s):4d} hits={h:4d} rate={h/len(s):6.1%}")

# cross-aircraft: was the teammate already shooting this target?
pair_of = {"1":"2","2":"1","3":"4","4":"3"}
prior_same, prior_other, first = 0, 0, 0
for r in J:
    if not r["lock"]:
        continue
    key = (r["batch"], r["case"], r["lock"])
    mate = pair_of[r["launcher"]]
    same_prior = [x for x in J if (x["batch"],x["case"],x["lock"])==key
                  and x["launcher"]==r["launcher"] and x["t"] < r["t"]]
    other_prior = [x for x in J if (x["batch"],x["case"],x["lock"])==key
                   and x["launcher"]==mate and x["t"] < r["t"]]
    if not same_prior and not other_prior: first += 1
    elif same_prior: prior_same += 1
    else: prior_other += 1

tot = first + prior_same + prior_other
print("\n=== what preceded each plus shot at the SAME target (same case) ===")
print(f"  no prior shot at this target (team-first)   : {first:4d} ({first/tot:5.1%})")
print(f"  MY OWN aircraft already shot this target     : {prior_same:4d} ({prior_same/tot:5.1%})")
print(f"  only my TEAMMATE already shot this target    : {prior_other:4d} ({prior_other/tot:5.1%})")

print("\n=== hit rate by that classification ===")
for label, sel in (("team-first", [r for r in J if r["lock"] and not any(
                        (x["batch"],x["case"],x["lock"])==(r["batch"],r["case"],r["lock"]) and x["t"] < r["t"] for x in J)]),
                   ):
    pass
# recompute cleanly
cat = {}
for r in J:
    if not r["lock"]: continue
    key = (r["batch"], r["case"], r["lock"])
    mate = pair_of[r["launcher"]]
    same_prior = any((x["batch"],x["case"],x["lock"])==key and x["launcher"]==r["launcher"] and x["t"] < r["t"] for x in J)
    other_prior = any((x["batch"],x["case"],x["lock"])==key and x["launcher"]==mate and x["t"] < r["t"] for x in J)
    c = "first" if not (same_prior or other_prior) else ("own-repeat" if same_prior else "mate-repeat")
    cat.setdefault(c, []).append(r)
for c, s in cat.items():
    h = sum(r["hit"] for r in s)
    print(f"  {c:12}: n={len(s):4d} hits={h:4d} rate={h/len(s):6.1%}")
