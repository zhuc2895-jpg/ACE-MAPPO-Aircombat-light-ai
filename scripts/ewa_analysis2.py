#!/usr/bin/env python3
"""EWA loss v2: were the escorts dead, or alive and far away? Plus outcome correlation."""
from __future__ import annotations
import math, re
from collections import Counter, defaultdict
from pathlib import Path

EVAL = (Path(__file__).resolve().parent
        / "龙智杯第四届参赛资料-0810更新高倍速平台"
        / "☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版" / "Evaluation")
POS_RE = re.compile(r"^(?P<id>\d+),T=(?P<lon>-?[0-9.]+)\|(?P<lat>-?[0-9.]+)\|(?P<alt>-?[0-9.]+)(?P<rest>.*)$")
R = 6371000.0
RED_F, BLUE_F = (1001, 1002), (1003, 1004)
RED_E, BLUE_E = 1005, 1006

def dist(a, b):
    la1, la2 = math.radians(a[1]), math.radians(b[1])
    dx = math.radians(b[0]-a[0])*math.cos((la1+la2)/2)*R
    dy = math.radians(b[1]-a[1])*R
    return math.hypot(dx, dy)

def parse(path):
    t = 0.0; objs = {}; dele = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s: continue
        if s[0] == "#":
            try: t = float(s[1:])
            except ValueError: pass
            continue
        if s[0] == "-":
            try: dele[int(s[1:])] = t
            except ValueError: pass
            continue
        m = POS_RE.match(s)
        if not m: continue
        oid = int(m.group("id"))
        o = objs.setdefault(oid, {"traj": [], "t": []})
        o["traj"].append((float(m.group("lon")), float(m.group("lat")), float(m.group("alt"))))
        o["t"].append(t)
    return objs, dele

def pos_at(o, t):
    ts = o.get("t", [])
    if not ts: return None
    if t <= ts[0]: return o["traj"][0]
    if t >= ts[-1]: return o["traj"][-1]
    lo, hi = 0, len(ts)-1
    while lo < hi:
        mid = (lo+hi)//2
        if ts[mid] < t: lo = mid+1
        else: hi = mid
    return o["traj"][lo]

def read_report(path):
    txt = path.read_bytes().decode("gb18030", "replace")
    out = {}
    for line in [l.strip() for l in txt.splitlines() if l.strip()][2:]:
        m = re.match(r"^(\d{4})(.*)$", line)
        if not m: continue
        out[int(m.group(1))] = "red" if "红方获胜" in m.group(2) else ("blue" if "蓝方获胜" in m.group(2) else "draw")
    return out

rows = []
for d in sorted([x for x in EVAL.iterdir() if x.is_dir() and x.name.startswith("gates_")]):
    rep = read_report(d / "Result" / "SimuResultReport.txt")
    plus = "red" if "plus_red" in d.name else "blue"
    for acmi in sorted((d / "AcmiRecord").glob("*.acmi")):
        case = int(re.search(r"(\d+)", acmi.stem).group(1))
        objs, dele = parse(acmi)
        for ewa, own_f, enemy_f, title in ((RED_E, RED_F, BLUE_F, "RedEWA"), (BLUE_E, BLUE_F, RED_F, "BlueEWA")):
            if ewa not in dele: continue
            td = dele[ewa]
            epos = pos_at(objs.get(ewa, {}), td)
            if epos is None: continue
            own_alive = [f for f in own_f if f not in dele]
            enemy_alive = [f for f in enemy_f if f not in dele]
            near = None
            for f in own_alive:
                fp = pos_at(objs.get(f, {}), td)
                if fp:
                    dd = dist(fp, epos)
                    near = dd if near is None else min(near, dd)
            winner = rep.get(case)
            rows.append({"batch": d.name, "case": case, "ewa": title, "t": td,
                         "own_alive": len(own_alive), "enemy_alive": len(enemy_alive),
                         "near_m": near, "plus": plus, "winner": winner})

print(f"EWA loss cases: {len(rows)}  (RedEWA {sum(1 for r in rows if r['ewa']=='RedEWA')}, BlueEWA {sum(1 for r in rows if r['ewa']=='BlueEWA')})")

print("\n=== were the escorts still alive when the EWA died? ===")
c = Counter((r["ewa"], r["own_alive"]) for r in rows)
for k in sorted(c):
    print(f"  {k[0]}  own fighters alive = {k[1]} : {c[k]} cases")

print("\n=== if alive, how far was the nearest one? ===")
for title in ("RedEWA", "BlueEWA"):
    for n in (2, 1):
        sel = [r["near_m"] for r in rows if r["ewa"] == title and r["own_alive"] == n and r["near_m"]]
        if sel:
            sel.sort()
            print(f"  {title} (alive={n}): n={len(sel)} nearest-fighter median={sel[len(sel)//2]/1000:.1f} km  "
                  f"min={sel[0]/1000:.1f} max={sel[-1]/1000:.1f}")

print("\n=== enemy fighters still alive at EWA death ===")
c2 = Counter((r["ewa"], r["enemy_alive"]) for r in rows)
for k in sorted(c2):
    print(f"  {k[0]}  enemy fighters alive = {k[1]} : {c2[k]} cases")

print("\n=== does killing the EWA decide the game? (the side that lost its EWA) ===")
for title, side in (("RedEWA", "red"), ("BlueEWA", "blue")):
    sel = [r for r in rows if r["ewa"] == title and r["winner"]]
    w = Counter(r["winner"] for r in sel)
    lost = sum(v for k, v in w.items() if k != side)
    print(f"  {title} (side={side}): n={len(sel)} -> that side WON {w.get(side,0)}, LOST {lost}  {dict(w)}")
