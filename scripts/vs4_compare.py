#!/usr/bin/env python3
"""Control (cap=0) vs Treatment (cap=2): ACMI-only comparison."""
from __future__ import annotations
import re
from collections import defaultdict
from pathlib import Path

EVAL = (Path(__file__).resolve().parent
        / "龙智杯第四届参赛资料-0810更新高倍速平台"
        / "☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版" / "Evaluation")
POS_RE = re.compile(r"^(?P<id>\d+),T=(?P<lon>-?[0-9.]+)\|(?P<lat>-?[0-9.]+)\|(?P<alt>-?[0-9.]+)(?P<rest>.*)$")
AC = {1001:("Red",1),1002:("Red",2),1003:("Blue",3),1004:("Blue",4)}
RUNS = [
    ("control(cap=0)","vs3_baseline_plus_red_20260916_134527","red"),
    ("control(cap=0)","vs3_baseline_plus_blue_20260916_135343","blue"),
    ("treat(cap=2)","vs4_throttle_plus_red_20260916_142906","red"),
    ("treat(cap=2)","vs4_throttle_plus_blue_20260916_143613","blue"),
]

def parse(p):
    t=0.0; objs={}; dele={}
    for raw in p.read_text(encoding="utf-8",errors="replace").splitlines():
        s=raw.strip()
        if not s: continue
        if s[0]=="#":
            try: t=float(s[1:])
            except ValueError: pass
            continue
        if s[0]=="-":
            try: dele[int(s[1:])]=t
            except ValueError: pass
            continue
        m=POS_RE.match(s)
        if not m: continue
        oid=int(m.group("id")); o=objs.setdefault(oid,{})
        r=m.group("rest").lstrip(",")
        if "=" in r:
            for it in r.split(","):
                if "=" in it:
                    k,v=it.split("=",1); o[k]=v
    acdel=defaultdict(list)
    for oid,(c,_) in AC.items():
        if oid in dele: acdel[c].append(dele[oid])
    out=[]
    for oid,o in objs.items():
        if o.get("Name")!="AIM-120C": continue
        c=o.get("Color"); mm=re.search(r"\((\d+)\)",o.get("ShortName",""))
        slot=int(mm.group(1)) if mm else None
        td=dele.get(oid); enemy="Blue" if c=="Red" else "Red"
        hit=1 if (td is not None and any(abs(x-td)<1e-6 for x in acdel.get(enemy,[]))) else 0
        out.append({"color":c,"slot":slot,"hit":hit})
    return out

by=defaultdict(list)
for tag,name,ps in RUNS:
    d=EVAL/name
    for acmi in sorted((d/"AcmiRecord").glob("*.acmi")):
        for m in parse(acmi):
            m.update({"tag":tag,"ps":ps,
                      "kind":"plus" if m["color"]==("Red" if ps=="red" else "Blue") else "yuandi",
                      "role":"lead" if m["slot"] in (1,3) else "wing"})
            by[tag].append(m)

print("=== plus side, ACMI only (strict same-frame hits) ===")
print(f"  {'variant':16} {'dir':5} {'launches':>8} {'hits':>5} {'rate':>7} | lead lau/hit | wing lau/hit")
for tag in ("control(cap=0)","treat(cap=2)"):
    for ps in ("red","blue"):
        s=[r for r in by[tag] if r["kind"]=="plus" and r["ps"]==ps]
        h=sum(r["hit"] for r in s)
        l=[r for r in s if r["role"]=="lead"]; w=[r for r in s if r["role"]=="wing"]
        print(f"  {tag:16} {ps:5} {len(s):8d} {h:5d} {h/len(s):7.1%} | "
              f"{len(l):5d}/{sum(x['hit'] for x in l):3d} | {len(w):5d}/{sum(x['hit'] for x in w):3d}")
print()
print("=== plus side totals ===")
for tag in ("control(cap=0)","treat(cap=2)"):
    s=[r for r in by[tag] if r["kind"]=="plus"]; h=sum(r["hit"] for r in s)
    l=[r for r in s if r["role"]=="lead"]; w=[r for r in s if r["role"]=="wing"]
    print(f"  {tag}: launches={len(s):5d} hits={h:4d} rate={h/len(s):6.1%} | "
          f"lead {len(l):4d}/{sum(x['hit'] for x in l):4d} ({sum(x['hit'] for x in l)/len(l):.1%})  "
          f"wing {len(w):4d}/{sum(x['hit'] for x in w):4d} ({sum(x['hit'] for x in w)/len(w):.1%})")
print()
print("=== 原版 side (opponent) ===")
for tag in ("control(cap=0)","treat(cap=2)"):
    s=[r for r in by[tag] if r["kind"]=="yuandi"]; h=sum(r["hit"] for r in s)
    print(f"  {tag}: launches={len(s):5d} hits={h:4d} rate={h/len(s):6.1%}")
