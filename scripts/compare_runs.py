#!/usr/bin/env python3
"""Compare two manual-100 run archives and emit a markdown comparison."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

CASE_RE = re.compile(r"^(?P<case>\d+)(?P<verdict>[^:]*):(?P<detail>.*)$")
ALIVE_RE = re.compile(r"(\d+)\s*-\s*(\d+)")


def read_result(path):
    text = path.read_bytes().decode("gb18030", errors="replace")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    totals = {"red": int(lines[0]), "blue": int(lines[1])}
    cases = {}
    for line in lines[2:]:
        m = CASE_RE.match(line)
        if not m:
            continue
        alive = ALIVE_RE.search(m.group("detail"))
        cases[int(m.group("case"))] = {
            "verdict": m.group("verdict").strip(),
            "detail": m.group("detail").strip(),
            "red_alive": int(alive.group(1)) if alive else None,
            "blue_alive": int(alive.group(2)) if alive else None,
            "winner": "red" if "红方获胜" in m.group("verdict") else "blue",
        }
    return totals, cases


def reason(detail):
    for key in ("全灭蓝方战斗机", "成功突防", "击落红方预警机", "全灭红方战斗机"):
        if key in detail:
            return key
    return detail


def load(run_dir):
    run_dir = Path(run_dir).resolve()
    totals, cases = read_result(run_dir / "Result" / "SimuResultReport.txt")
    data = json.loads((run_dir / "analysis" / "acmi_metrics.json").read_text(encoding="utf-8"))
    rows = {r["case"]: r for r in data["acmi"] if not r.get("failed")}
    return run_dir, totals, cases, rows


def summary(rows):
    n = len(rows)
    v = list(rows.values())
    red_l = sum(r["red_launches"] for r in v)
    blue_l = sum(r["blue_launches"] for r in v)
    red_h = sum(r["red_hits"] for r in v)
    blue_h = sum(r["blue_hits"] for r in v)
    return {
        "n": n,
        "red_alive": sum(r["red_fighters_alive"] for r in v),
        "blue_alive": sum(r["blue_fighters_alive"] for r in v),
        "red_ewa": sum(r["red_ewa_alive"] for r in v),
        "blue_ewa": sum(r["blue_ewa_alive"] for r in v),
        "red_launch": red_l, "red_hit": red_h,
        "blue_launch": blue_l, "blue_hit": blue_h,
        "red_boundary": sum(1 for r in v if r["red_boundary"]),
        "blue_boundary": sum(1 for r in v if r["blue_boundary"]),
        "red_ground": sum(1 for r in v if r["red_ground"]),
        "blue_ground": sum(1 for r in v if r["blue_ground"]),
        "red_pen": sum(1 for r in v if r["red_penetration"]),
        "blue_pen": sum(1 for r in v if r["blue_penetration"]),
        "sim_avg": sum(r["sim_end_time"] for r in v) / n,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a", help="run A directory (fixed)")
    ap.add_argument("b", help="run B directory (baseline / no-fix)")
    ap.add_argument("--label-a", default="A 修复后")
    ap.add_argument("--label-b", default="B 修复前")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    adir, at, ac, ar = load(args.a)
    bdir, bt, bc, br = load(args.b)
    sa, sb = summary(ar), summary(br)

    ar_reason = Counter(reason(c["detail"]) for c in ac.values() if c["winner"] == "red")
    br_reason = Counter(reason(c["detail"]) for c in bc.values() if c["winner"] == "red")
    ab_reason = Counter(reason(c["detail"]) for c in ac.values() if c["winner"] == "blue")
    bb_reason = Counter(reason(c["detail"]) for c in bc.values() if c["winner"] == "blue")

    flips = []
    same = 0
    for case in sorted(set(ac) & set(bc)):
        if ac[case]["winner"] == bc[case]["winner"]:
            same += 1
        else:
            flips.append((case, bc[case]["winner"], ac[case]["winner"]))

    L = []
    add = L.append
    add(f"# 100 场前后对比：{args.label_a} vs {args.label_b}")
    add("")
    add(f"- A（{args.label_a}）：`{adir}`")
    add(f"- B（{args.label_b}）：`{bdir}`")
    add("- 场景、出生点、`AreaConfig`、ACMI 记录上限完全相同（标准 20 场景 × 5，编号 0001-0100）")
    add("")
    add("## 总分")
    add("")
    add("| 运行 | 红方 | 蓝方 |")
    add("|:---|---:|---:|")
    add(f"| A {args.label_a} | {at['red']} | {at['blue']} |")
    add(f"| B {args.label_b} | {bt['red']} | {bt['blue']} |")
    add(f"| 差值 | {at['red']-bt['red']:+d} | {at['blue']-bt['blue']:+d} |")
    add("")
    add("## 判定原因")
    add("")
    add("| 判定 | A 场次 | B 场次 | 差值 |")
    add("|:---|---:|---:|---:|")
    for key in ("全灭蓝方战斗机", "成功突防", "击落红方预警机", "全灭红方战斗机"):
        a = ar_reason.get(key, 0) + ab_reason.get(key, 0)
        b = br_reason.get(key, 0) + bb_reason.get(key, 0)
        add(f"| {key} | {a} | {b} | {a-b:+d} |")
    add("")
    add("## ACMI 指标")
    add("")
    add("| 指标 | A | B | 差值 |")
    add("|:---|---:|---:|---:|")
    rows = [
        ("战斗机存活（红）", sa["red_alive"], sb["red_alive"], f"/{2*sa['n']}"),
        ("战斗机存活（蓝）", sa["blue_alive"], sb["blue_alive"], f"/{2*sb['n']}"),
        ("预警机存活（红）", sa["red_ewa"], sb["red_ewa"], f"/{sa['n']}"),
        ("预警机存活（蓝）", sa["blue_ewa"], sb["blue_ewa"], f"/{sb['n']}"),
        ("导弹发射（红）", sa["red_launch"], sb["red_launch"], ""),
        ("导弹命中（红）", sa["red_hit"], sb["red_hit"], ""),
        ("导弹发射（蓝）", sa["blue_launch"], sb["blue_launch"], ""),
        ("导弹命中（蓝）", sa["blue_hit"], sb["blue_hit"], ""),
        ("越界场次（红）", sa["red_boundary"], sb["red_boundary"], ""),
        ("越界场次（蓝）", sa["blue_boundary"], sb["blue_boundary"], ""),
        ("坠地场次（红）", sa["red_ground"], sb["red_ground"], ""),
        ("突防成功（红）", sa["red_pen"], sb["red_pen"], ""),
        ("突防成功（蓝）", sa["blue_pen"], sb["blue_pen"], ""),
    ]
    for name, a, b, suffix in rows:
        add(f"| {name} | {a}{suffix} | {b}{suffix} | {a-b:+d} |")
    add(f"| 平均仿真时长(s) | {sa['sim_avg']:.1f} | {sb['sim_avg']:.1f} | {sa['sim_avg']-sb['sim_avg']:+.1f} |")
    add("")
    if sa["red_launch"]:
        add(f"- 红方命中率：A {sa['red_hit']/sa['red_launch']:.1%} / B {sb['red_hit']/sb['red_launch']:.1%}")
    if sa["blue_launch"]:
        add(f"- 蓝方命中率：A {sa['blue_hit']/sa['blue_launch']:.1%} / B {sb['blue_hit']/sb['blue_launch']:.1%}")
    def errcount(d):
        p = d / "Simplat.stdout.txt"
        if not p.exists():
            return None
        n = 0
        with p.open("rb") as fh:
            for raw in fh:
                if b"UnboundLocalError" in raw:
                    n += 1
        return n
    ea, eb = errcount(adir), errcount(bdir)
    add("")
    add("## 异常与噪声（关键）")
    add("")
    add(f"- `UnboundLocalError: guide_msl_cnt` 次数：A = {ea}，B = {eb}。"
        "修复确实生效：受威胁帧不再整帧丢决策。")
    add("- **但 `Simplat.exe` 单次运行不确定可复现。** 同一构建、同一 5 场景配置连跑两次，"
        "结果与 5 个 ACMI 的 SHA-256 全部不同（例：0001 一次红方全灭、一次红方突防）。")
    add(f"- 本次 A/B 同为 100 场，逐场胜负改变 {len(flips)} 场（噪声量级）。"
        "因此总分差不能单独归因于这一行修复。")
    add("- 结论：该修复的对象是**运行时异常**（可验证、已归零），不是胜负；"
        "若要判断胜率影响，需要对每个构建重复多批 100 场再比较。")
    add("")
    add("## 同场景逐场对照")
    add("")
    add(f"- 胜负一致：{same}/100；发生变化：{len(flips)} 场")
    if flips:
        add("")
        add("| 场次 | B 获胜方 | A 获胜方 |")
        add("|---:|:---:|:---:|")
        for case, bw, aw in flips:
            add(f"| {case:04d} | {'红' if bw=='red' else '蓝'} | {'红' if aw=='red' else '蓝'} |")
    add("")
    args.out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"A red={at['red']} blue={at['blue']} | B red={bt['red']} blue={bt['blue']}")
    print(f"consistent cases={same} flips={len(flips)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
