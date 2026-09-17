#!/usr/bin/env python3
"""Structured analysis of a manual Simplat 100-case ACMI run (self-play mirror).

Reads Result/SimuResultReport.txt and every AcmiRecord/*.acmi, reconstructs the
engagement, and writes report.md + acmi_metrics.json + acmi_metrics.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

EARTH = 6371000.0
HALF_EW_M = 80000.0
HALF_SN_M = 40000.0
MISSION_M = 70000.0
PENETRATION_M = 10000.0

POS_RE = re.compile(
    r"^(?P<id>\d+),T=(?P<lon>-?[0-9.]+)\|(?P<lat>-?[0-9.]+)\|(?P<alt>-?[0-9.]+)(?P<rest>.*)$"
)
CASE_RE = re.compile(r"^(?P<case>\d+)(?P<verdict>[^:]*):(?P<detail>.*)$")
ALIVE_RE = re.compile(r"(\d+)\s*-\s*(\d+)")

RED_FIGHTERS = (1001, 1002)
BLUE_FIGHTERS = (1003, 1004)
RED_EWA, BLUE_EWA = 1005, 1006
FIGHTERS = RED_FIGHTERS + BLUE_FIGHTERS
SIDE = {1001: "red", 1002: "red", 1003: "blue", 1004: "blue", 1005: "red", 1006: "blue"}
COLOR = {"red": "Red", "blue": "Blue"}


def distance_m(a, b):
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dx = (lon2 - lon1) * math.cos((lat1 + lat2) / 2.0) * EARTH
    dy = (lat2 - lat1) * EARTH
    dz = (b[2] - a[2]) if len(a) > 2 and len(b) > 2 else 0.0
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def dist2d(a, b):
    """Horizontal separation only: the platform's penetration zone is 2D."""
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dx = (lon2 - lon1) * math.cos((lat1 + lat2) / 2.0) * EARTH
    dy = (lat2 - lat1) * EARTH
    return math.sqrt(dx * dx + dy * dy)


def read_report(path):
    text = path.read_bytes().decode("gb18030", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    totals = {"red": int(lines[0]), "blue": int(lines[1])}
    cases = []
    for line in lines[2:]:
        m = CASE_RE.match(line)
        if not m:
            continue
        alive = ALIVE_RE.search(m.group("detail"))
        cases.append(
            {
                "case": int(m.group("case")),
                "verdict": m.group("verdict").strip(),
                "detail": m.group("detail").strip(),
                "red_alive": int(alive.group(1)) if alive else None,
                "blue_alive": int(alive.group(2)) if alive else None,
            }
        )
    return totals, cases


def parse_acmi(path):
    objects, positions, deletions, first_pos, times = {}, {}, {}, {}, []
    current = 0.0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            try:
                current = float(line[1:])
                times.append(current)
            except ValueError:
                pass
            continue
        if line.startswith("-"):
            try:
                oid = int(line[1:])
            except ValueError:
                continue
            if oid in objects:
                deletions[oid] = {"time": current, "position": objects[oid].get("position")}
            continue
        m = POS_RE.match(line)
        if not m:
            continue
        try:
            pos = (float(m.group("lon")), float(m.group("lat")), float(m.group("alt")))
        except ValueError:
            continue
        oid = int(m.group("id"))
        obj = objects.setdefault(oid, {})
        obj["position"] = pos
        obj["last_time"] = current
        rest = m.group("rest").lstrip(",")
        if "=" in rest:
            for item in rest.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    obj[k] = v
            sn = obj.get("ShortName", "")
            launch = re.search(r"\((\d+)\)", sn)
            if launch:
                obj["launcher"] = int(launch.group(1))
                obj["launch_time"] = current
        if oid in FIGHTERS:
            positions.setdefault(oid, []).append(pos)
            first_pos.setdefault(oid, pos)

    missiles = {i: o for i, o in objects.items() if o.get("Name", "").startswith("AIM-")}
    matched, kills = set(), {}
    for ac in (1001, 1002, 1003, 1004, 1005, 1006):
        dele = deletions.get(ac)
        if not dele or not dele.get("position"):
            continue
        best = None
        for mid, msl in missiles.items():
            if mid in matched or msl.get("Color") == objects.get(ac, {}).get("Color"):
                continue
            md = deletions.get(mid)
            mtime = md["time"] if md else msl.get("last_time", -999)
            mpos = md.get("position") if md else msl.get("position")
            if not mpos or abs(mtime - dele["time"]) > 1.5:
                continue
            sep = distance_m(mpos, dele["position"])
            if sep <= 5000.0 and (best is None or sep < best[0]):
                best = (sep, mid)
        if best:
            matched.add(best[1])
            kills[ac] = {"missile": best[1], "time": dele["time"], "separation_m": round(best[0], 1)}

    start = {ac: first_pos.get(ac) for ac in FIGHTERS if ac in first_pos}
    lats = [p[1] for p in start.values()]
    lons = [p[0] for p in start.values()]
    if not lats:
        return None
    center = (sum(lons) / len(lons), sum(lats) / len(lats))
    half_lon = math.degrees(HALF_EW_M / (EARTH * math.cos(math.radians(center[1]))))
    half_lat = math.degrees(HALF_SN_M / EARTH)

    metrics = {
        "sim_end_time": max(times) if times else None,
        "center": [round(center[0], 9), round(center[1], 9)],
        "missiles": {"total": len(missiles), "matched_hits": len(matched)},
        "kills": {},
        "sides": {},
    }
    for side in ("red", "blue"):
        own = RED_FIGHTERS if side == "red" else BLUE_FIGHTERS
        foe = BLUE_FIGHTERS if side == "red" else RED_FIGHTERS
        own_ewa = RED_EWA if side == "red" else BLUE_EWA
        launches = [
            mid for mid, msl in missiles.items()
            if msl.get("Color") == COLOR[side]
        ]
        hits = [mid for mid in matched if missiles[mid].get("Color") == COLOR[side]]
        kills_by_side = [ac for ac in foe if ac in kills]
        outside, ground, min_alt = [], [], {}
        for ac in own:
            for pos in positions.get(ac, []):
                if not (
                    center[0] - half_lon <= pos[0] <= center[0] + half_lon
                    and center[1] - half_lat <= pos[1] <= center[1] + half_lat
                ):
                    outside.append(ac)
                    break
        for ac in own:
            alts = [p[2] for p in positions.get(ac, [])]
            min_alt[str(ac)] = round(min(alts), 1) if alts else None
            dele = deletions.get(ac)
            if dele and ac not in kills and dele.get("position") and dele["position"][2] <= 500.0:
                ground.append(ac)
        foe_start = [start[ac] for ac in foe if ac in start]
        penetrated = False
        closest = None
        if foe_start:
            ref = (sum(p[0] for p in foe_start) / len(foe_start),
                   sum(p[1] for p in foe_start) / len(foe_start))
            for ac in own:
                for pos in positions.get(ac, []):
                    d = dist2d(pos, ref)
                    if closest is None or d < closest:
                        closest = d
                    if d <= PENETRATION_M:
                        penetrated = True
        first_launch = min(
            [missiles[mid].get("launch_time") for mid in launches
             if missiles[mid].get("launch_time") is not None] or [None]
        )
        metrics["sides"][side] = {
            "fighters_alive": sum(ac not in deletions for ac in own),
            "ewa_alive": int(own_ewa not in deletions),
            "fighters_lost": [ac for ac in own if ac in deletions],
            "kills": kills_by_side,
            "missiles_launched": len(launches),
            "missile_hits": len(hits),
            "hit_rate": round(len(hits) / len(launches), 3) if launches else None,
            "first_launch_time": round(first_launch, 1) if first_launch else None,
            "boundary_violation": sorted(set(outside)),
            "ground_crash": ground,
            "penetration_success": penetrated,
            "min_approach_to_enemy_start_m": round(closest) if closest is not None else None,
            "min_altitude_m": min_alt,
        }
    metrics["kills"] = {str(k): v for k, v in sorted(kills.items())}
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=Path, help="run archive directory (contains Result/ and AcmiRecord/)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    arch = args.archive.resolve()
    out = args.out or (arch / "analysis")
    out.mkdir(parents=True, exist_ok=True)

    totals, cases = read_report(arch / "Result" / "SimuResultReport.txt")
    acmi_files = sorted((arch / "AcmiRecord").glob("*.acmi"))
    rows = []
    for path in acmi_files:
        idx = int(re.search(r"(\d+)", path.stem).group(1))
        m = parse_acmi(path)
        if m is None:
            rows.append({"case": idx, "file": path.name, "failed": True})
            continue
        r, b = m["sides"]["red"], m["sides"]["blue"]
        rows.append({
            "case": idx, "file": path.name, "bytes": path.stat().st_size,
            "sim_end_time": m["sim_end_time"],
            "red_fighters_alive": r["fighters_alive"], "blue_fighters_alive": b["fighters_alive"],
            "red_ewa_alive": r["ewa_alive"], "blue_ewa_alive": b["ewa_alive"],
            "red_kills": len(r["kills"]), "blue_kills": len(b["kills"]),
            "red_launches": r["missiles_launched"], "blue_launches": b["missiles_launched"],
            "red_hits": r["missile_hits"], "blue_hits": b["missile_hits"],
            "red_first_launch": r["first_launch_time"], "blue_first_launch": b["first_launch_time"],
            "red_penetration": r["penetration_success"], "blue_penetration": b["penetration_success"],
            "red_min_approach_km": round(r["min_approach_to_enemy_start_m"] / 1000.0, 1),
            "blue_min_approach_km": round(b["min_approach_to_enemy_start_m"] / 1000.0, 1),
            "red_boundary": len(r["boundary_violation"]), "blue_boundary": len(b["boundary_violation"]),
            "red_ground": len(r["ground_crash"]), "blue_ground": len(b["ground_crash"]),
        })

    (out / "acmi_metrics.json").write_text(
        json.dumps({"totals": totals, "report_cases": cases, "acmi": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    if rows:
        with (out / "acmi_metrics.csv").open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    ok = [r for r in rows if not r.get("failed")]
    print(f"archive          : {arch}")
    print(f"report totals    : red={totals['red']} blue={totals['blue']} cases={len(cases)}")
    print(f"acmi files       : {len(acmi_files)} parsed={len(ok)}")
    if ok:
        red_surv = sum(r["red_fighters_alive"] for r in ok)
        blue_surv = sum(r["blue_fighters_alive"] for r in ok)
        rl = sum(r["red_launches"] for r in ok)
        bl = sum(r["blue_launches"] for r in ok)
        rh = sum(r["red_hits"] for r in ok)
        bh = sum(r["blue_hits"] for r in ok)
        print(f"red  fighters alive {red_surv}/{2*len(ok)}  launches {rl} hits {rh}")
        print(f"blue fighters alive {blue_surv}/{2*len(ok)}  launches {bl} hits {bh}")
        print(f"red  boundary cases {sum(1 for r in ok if r['red_boundary'])}  "
              f"ground {sum(1 for r in ok if r['red_ground'])}  "
              f"penetrations {sum(1 for r in ok if r['red_penetration'])}")
        print(f"blue boundary cases {sum(1 for r in ok if r['blue_boundary'])}  "
              f"ground {sum(1 for r in ok if r['blue_ground'])}  "
              f"penetrations {sum(1 for r in ok if r['blue_penetration'])}")
        print(f"red  EWA alive {sum(r['red_ewa_alive'] for r in ok)}/{len(ok)}  "
              f"blue EWA alive {sum(r['blue_ewa_alive'] for r in ok)}/{len(ok)}")
        print(f"sim end time min/avg/max: "
              f"{min(r['sim_end_time'] for r in ok):.1f}/"
              f"{sum(r['sim_end_time'] for r in ok)/len(ok):.1f}/"
              f"{max(r['sim_end_time'] for r in ok):.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
