#!/usr/bin/env python3
"""AWACS (EWA) loss forensics from ACMI across the 12 gates batches (1200 cases)."""
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
NAME = {1001:"RedF",1002:"RedF",1003:"BlueF",1004:"BlueF",1005:"RedEWA",1006:"BlueEWA"}
RING = {1001:2,1002:2,1003:2,1004:2,1005:255,1006:255}  # ignore for now

def dist(a, b):
    la1, la2 = math.radians(a[1]), math.radians(b[1])
    dx = math.radians(b[0]-a[0])*math.cos((la1+la2)/2)*R
    dy = math.radians(b[1]-a[1])*R
    dz = (b[2]-a[2]) if len(a) > 2 and len(b) > 2 else 0.0
    return math.sqrt(dx*dx+dy*dy+dz*dz)

def parse(path):
    t = 0.0; objs = {}; first = {}; dele = {}
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
        pos = (float(m.group("lon")), float(m.group("lat")), float(m.group("alt")))
        o = objs.setdefault(oid, {"traj": [], "t": []})
        o["traj"].append(pos); o["t"].append(t); o["pos"] = pos
        first.setdefault(oid, t)
        r = m.group("rest").lstrip(",")
        if "=" in r:
            for it in r.split(","):
                if "=" in it:
                    k, v = it.split("=", 1); o[k] = v
    return objs, first, dele, t

def pos_at(o, t):
    ts = o.get("t", [])
    if not ts: return None
    lo, hi = 0, len(ts)-1
    if t <= ts[0]: return o["traj"][0]
    if t >= ts[-1]: return o["traj"][-1]
    while lo < hi:
        mid = (lo+hi)//2
        if ts[mid] < t: lo = mid+1
        else: hi = mid
    return o["traj"][lo]

cases = []
dirs = sorted([d for d in EVAL.iterdir() if d.is_dir() and d.name.startswith("gates_")])
for d in dirs:
    for acmi in sorted((d / "AcmiRecord").glob("*.acmi")):
        case = int(re.search(r"(\d+)", acmi.stem).group(1))
        objs, first, dele, tmax = parse(acmi)
        for ewa, foe_list, title in ((RED_E, BLUE_F, "RedEWA"), (BLUE_E, RED_F, "BlueEWA")):
            if ewa not in dele: continue
            td = dele[ewa]
            epos = pos_at(objs.get(ewa, {}), td)
            if epos is None: continue
            # killer: an enemy missile deleted in the same 0.1 s frame
            killer_slot = None; kill_mid = None
            for oid, o in objs.items():
                if o.get("Name") != "AIM-120C": continue
                if oid not in dele or abs(dele[oid]-td) > 1e-6: continue
                if (o.get("Color") == "Red") != (title == "BlueEWA"): continue
                mm = re.search(r"\((\d+)\)", o.get("ShortName", ""))
                if mm: killer_slot = int(mm.group(1)); kill_mid = oid
            launch_t = first.get(kill_mid) if kill_mid else None
            launch_rng = None
            if kill_mid and launch_t is not None:
                mpos = objs[kill_mid]["traj"][0]
                launch_rng = dist(mpos, pos_at(objs[ewa], launch_t) or epos)
            # own fighters at time of death
            own_f = RED_F if title == "RedEWA" else BLUE_F
            fd = []
            for f in own_f:
                fp = pos_at(objs.get(f, {}), td)
                if fp: fd.append(dist(fp, epos))
            cases.append({
                "batch": d.name, "case": case, "ewa": title, "t_death": td, "t_max": tmax,
                "alt_death": round(epos[2]), "dist_moved": round(dist(objs[ewa]["traj"][0], epos)),
                "killer_slot": killer_slot, "launch_range_m": round(launch_rng) if launch_rng else None,
                "escort_dists_m": [round(x) for x in sorted(fd)],
                "ewas_alive_end": None,
            })

print(f"EWA loss cases found: {len(cases)}")
c = Counter(x["ewa"] for x in cases)
print(f"  Red EWA lost: {c['RedEWA']}   Blue EWA lost: {c['BlueEWA']}   (over {len(dirs)} batches = {len(dirs)*100} cases)")

print("\n=== time of death (sim seconds) ===")
for title in ("RedEWA", "BlueEWA"):
    ts = sorted(x["t_death"] for x in cases if x["ewa"] == title)
    if ts:
        print(f"  {title}: n={len(ts)} min={ts[0]:.0f} p25={ts[len(ts)//4]:.0f} median={ts[len(ts)//2]:.0f} p75={ts[3*len(ts)//4]:.0f} max={ts[-1]:.0f}")
        print(f"      quartiles: <{ts[len(ts)//4]:.0f}s: {sum(1 for x in ts if x< ts[len(ts)//4])} | 90s+: {sum(1 for x in ts if x>=90)} | 150s+: {sum(1 for x in ts if x>=150)}")

print("\n=== kill geometry ===")
for title in ("RedEWA", "BlueEWA"):
    sel = [x for x in cases if x["ewa"] == title]
    if not sel: continue
    lr = sorted(x["launch_range_m"] for x in sel if x["launch_range_m"])
    al = sorted(x["alt_death"] for x in sel)
    mv = sorted(x["dist_moved"] for x in sel)
    if lr:
        print(f"  {title}: launch range median={lr[len(lr)//2]/1000:.1f} km (min {lr[0]/1000:.1f} max {lr[-1]/1000:.1f})")
    print(f"      EWA altitude at death median={al[len(al)//2]:.0f} m | EWA had moved median={mv[len(mv)//2]/1000:.1f} km from start")
    ks = Counter(x["killer_slot"] for x in sel)
    print(f"      killer aircraft slot: {dict(ks)}")

print("\n=== escort position at the moment the EWA dies ===")
for title in ("RedEWA", "BlueEWA"):
    sel = [x for x in cases if x["ewa"] == title and x["escort_dists_m"]]
    if not sel: continue
    near = [x["escort_dists_m"][0] for x in sel]
    far = [x["escort_dists_m"][-1] for x in sel]
    near.sort(); far.sort()
    print(f"  {title}: nearest own fighter  median={near[len(near)//2]/1000:.1f} km")
    print(f"      farthest own fighter  median={far[len(far)//2]/1000:.1f} km")
    print(f"      <=10 km: {sum(1 for x in near if x<=10000)}/{len(near)} | >=30 km: {sum(1 for x in near if x>=30000)}/{len(near)}")

print("\n=== worst batches for EWA loss ===")
bc = Counter(x["batch"] for x in cases)
for b, n in bc.most_common(8):
    print(f"  {b}: {n}")
