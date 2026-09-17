#!/usr/bin/env python3
"""Three-way trend: 09-12 / 09-14 / 09-16, strict same-frame hits + role split."""
from __future__ import annotations
import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path

EVAL = (Path(__file__).resolve().parent
        / "龙智杯第四届参赛资料-0810更新高倍速平台"
        / "☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版" / "Evaluation")
POS_RE = re.compile(r"^(?P<id>\d+),T=(?P<lon>-?[0-9.]+)\|(?P<lat>-?[0-9.]+)\|(?P<alt>-?[0-9.]+)(?P<rest>.*)$")
AC = {1001:("Red",1),1002:("Red",2),1003:("Blue",3),1004:("Blue",4)}
BATCHES = [
    ("0912","vs_baseline_plus_red_20260912_214829","red"),
    ("0912","vs_baseline_plus_blue_20260912_215719","blue"),
    ("0914","vs2_baseline_plus_red_20260914_150126","red"),
    ("0914","vs2_baseline_plus_blue_20260914_150904","blue"),
    ("0916","vs3_baseline_plus_red_20260916_134527","red"),
    ("0916","vs3_baseline_plus_blue_20260916_135343","blue"),
]

def parse(p):
    t=0.0; objs={}; first={}; dele={}
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
        oid=int(m.group("id")); o=objs.setdefault(oid,{}); first.setdefault(oid,t)
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

data=defaultdict(list)
for date,name,ps in BATCHES:
    d=EVAL/name
    for acmi in sorted((d/"AcmiRecord").glob("*.acmi")):
        case=int(re.search(r"(\d+)",acmi.stem).group(1))
        for m in parse(acmi):
            m.update({"date":date,"ps":ps,"case":case,
                      "kind":"plus" if m["color"]==("Red" if ps=="red" else "Blue") else "yuandi",
                      "role":"lead" if m["slot"] in (1,3) else "wing"})
            data[date].append(m)

print("=== plus side: launches / strict hits / rate, per direction ===")
print("  date dir        launches hits  rate   lead_lau lead_hit wing_lau wing_hit")
for date in ("0912","0914","0916"):
    for ps in ("red","blue"):
        s=[r for r in data[date] if r["kind"]=="plus" and r["ps"]==ps]
        h=sum(r["hit"] for r in s)
        l=[r for r in s if r["role"]=="lead"]; w=[r for r in s if r["role"]=="wing"]
        print(f"  {date} plus_{ps:4} {len(s):8d} {h:4d} {h/len(s):6.1%}  {len(l):8d} {sum(x['hit'] for x in l):8d} "
              f"{len(w):8d} {sum(x['hit'] for x in w):8d}")
print()
print("=== plus side totals by date ===")
for date in ("0912","0914","0916"):
    s=[r for r in data[date] if r["kind"]=="plus"]
    l=[r for r in s if r["role"]=="lead"]; w=[r for r in s if r["role"]=="wing"]
    h=sum(r["hit"] for r in s)
    print(f"  {date}: launches={len(s):5d} hits={h:4d} rate={h/len(s):6.1%} | "
          f"lead {len(l):4d}/{sum(x['hit'] for x in l):4d} ({sum(x['hit'] for x in l)/len(l):.1%})  "
          f"wing {len(w):4d}/{sum(x['hit'] for x in w):4d} ({sum(x['hit'] for x in w)/len(w):.1%})")
print()
print("=== note: the 0915 edit only touches the BLUE defence-line geometry ===")
print("  -> plus_red batch is a control (red code unchanged); plus_blue is the treatment")
for date in ("0912","0914","0916"):
    s=[r for r in data[date] if r["kind"]=="plus" and r["ps"]=="blue"]
    h=sum(r["hit"] for r in s)
    print(f"  plus as BLUE {date}: launches={len(s):4d} hits={h:4d} rate={h/len(s):.1%}")
