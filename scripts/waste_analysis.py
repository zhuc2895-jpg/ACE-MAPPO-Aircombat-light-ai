#!/usr/bin/env python3
"""ACMI-layer waste analysis with the STRICT same-frame hit rule.

Batches compared:
  09-14 (tested build 30913FD36F19) vs 09-12 (build 6B28BB46ADF0), each run
  both directions (plus on red / plus on blue) over the same 100 standard cases.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

EVAL = (Path(__file__).resolve().parent
        / "龙智杯第四届参赛资料-0810更新高倍速平台"
        / "☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版" / "Evaluation")

BATCHES = [
    ("0914", "plus_red",  "vs2_baseline_plus_red_20260914_150126",  "red"),
    ("0914", "plus_blue", "vs2_baseline_plus_blue_20260914_150904", "blue"),
    ("0912", "plus_red",  "vs_baseline_plus_red_20260912_214829",   "red"),
    ("0912", "plus_blue", "vs_baseline_plus_blue_20260912_215719",  "blue"),
]

POS_RE = re.compile(r"^(?P<id>\d+),T=(?P<lon>-?[0-9.]+)\|(?P<lat>-?[0-9.]+)\|(?P<alt>-?[0-9.]+)(?P<rest>.*)$")
MISSILE_NAME = "AIM-120C"
LAUNCHER_RE = re.compile(r"\((\d+)\)")
AIRCRAFT = {1001: ("Red", 1), 1002: ("Red", 2), 1003: ("Blue", 3), 1004: ("Blue", 4)}


def parse_acmi(path):
    """Return one dict per missile with launch/end time and strict-hit flag."""
    t = 0.0
    objs = {}
    first = {}
    deleted_at = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line[0] == "#":
            try:
                t = float(line[1:])
            except ValueError:
                pass
            continue
        if line[0] == "-":
            try:
                deleted_at[int(line[1:])] = t
            except ValueError:
                pass
            continue
        m = POS_RE.match(line)
        if not m:
            continue
        oid = int(m.group("id"))
        o = objs.setdefault(oid, {})
        first.setdefault(oid, t)
        rest = m.group("rest").lstrip(",")
        if "=" in rest:
            for item in rest.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    o[k] = v

    # aircraft deletions, by colour
    ac_del = defaultdict(list)
    for oid, (colour, _slot) in AIRCRAFT.items():
        if oid in deleted_at:
            ac_del[colour].append(deleted_at[oid])

    missiles = []
    for oid, o in objs.items():
        if o.get("Name") != MISSILE_NAME:
            continue
        colour = o.get("Color")
        slot = None
        m = LAUNCHER_RE.search(o.get("ShortName", ""))
        if m:
            slot = int(m.group(1))
        t_launch = first.get(oid)
        t_del = deleted_at.get(oid)
        enemy = "Blue" if colour == "Red" else "Red"
        hit = 0
        if t_del is not None:
            for t_ac in ac_del.get(enemy, []):
                if abs(t_ac - t_del) < 1e-6:
                    hit = 1
                    break
        missiles.append({
            "missile_id": oid, "color": colour, "launcher": slot,
            "launch_time": t_launch, "deleted": int(t_del is not None),
            "end_time": t_del, "hit_strict": hit,
        })
    return missiles


def read_report(path):
    text = path.read_bytes().decode("gb18030", "replace")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out = {}
    for line in lines[2:]:
        m = re.match(r"^(\d{4})(.*)$", line)
        if not m:
            continue
        n, txt = int(m.group(1)), m.group(2)
        if "红方获胜" in txt:
            w = "red"
        elif "蓝方获胜" in txt:
            w = "blue"
        else:
            w = "draw"
        reason = ("全灭蓝方战斗机" if "全灭蓝方战斗机" in txt else
                  "成功突防" if "突防" in txt else
                  "击落蓝方预警机" if "击落蓝方预警机" in txt else
                  "击落红方预警机" if "击落红方预警机" in txt else
                  "全灭红方战斗机" if "全灭红方战斗机" in txt else txt)
        out[n] = {"winner": w, "reason": reason}
    return out


def main():
    rows = []
    per_case = []
    report_state = {}
    for date, tag, name, plus_side in BATCHES:
        d = EVAL / name
        rep = read_report(d / "Result" / "SimuResultReport.txt")
        report_state[(date, tag)] = rep
        for acmi in sorted((d / "AcmiRecord").glob("*.acmi")):
            case = int(re.search(r"(\d+)", acmi.stem).group(1))
            for msl in parse_acmi(acmi):
                msl.update({"date": date, "tag": tag, "batch": name, "case": case,
                            "plus_side": plus_side,
                            "side": "plus" if msl["color"] == ("Red" if plus_side == "red" else "Blue") else "yuandi"})
                rows.append(msl)
            per_case.append({"date": date, "tag": tag, "case": case, "plus_side": plus_side,
                             "scenario": ((case - 1) % 20) + 1,
                             "winner": rep.get(case, {}).get("winner"),
                             "reason": rep.get(case, {}).get("reason")})
        print(f"parsed {name}: missiles so far {len(rows)}")

    outdir = Path(__file__).resolve().parent
    (outdir / "waste_acmi_missiles.json").write_text(
        json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    with (outdir / "waste_acmi_missiles.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with (outdir / "waste_acmi_cases.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(per_case[0].keys()))
        w.writeheader()
        w.writerows(per_case)

    # ---- summary ----
    print("\n=== per date x side (STRICT same-frame hits) ===")
    for date in ("0912", "0914"):
        for side in ("plus", "yuandi"):
            sel = [r for r in rows if r["date"] == date and r["side"] == side]
            n = len(sel)
            h = sum(r["hit_strict"] for r in sel)
            print(f"  {date} {side:7} launches={n:5d} hits={h:4d} hit_rate={h/n if n else 0:.1%}")

    print("\n=== launches by aircraft slot (tests the 'wingman fire' hypothesis) ===")
    for date in ("0912", "0914"):
        for tag in ("plus_red", "plus_blue"):
            sel = [r for r in rows if r["date"] == date and r["tag"] == tag]
            c = Counter(r["launcher"] for r in sel)
            print(f"  {date} {tag:10} " + " ".join(f"slot{k}={c.get(k,0):4d}" for k in (1, 2, 3, 4)))

    print("\n=== per base scenario, plus side ===")
    print("  scen  0912_lau 0912_hit  0914_lau 0914_hit  d_lau")
    for s in range(1, 21):
        a = [r for r in rows if r["date"] == "0912" and r["side"] == "plus" and ((r["case"] - 1) % 20) + 1 == s]
        b = [r for r in rows if r["date"] == "0914" and r["side"] == "plus" and ((r["case"] - 1) % 20) + 1 == s]
        print(f"  {s:4d}  {len(a):8d} {sum(x['hit_strict'] for x in a):8d}  "
              f"{len(b):8d} {sum(x['hit_strict'] for x in b):8d}  {len(b)-len(a):+5d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
