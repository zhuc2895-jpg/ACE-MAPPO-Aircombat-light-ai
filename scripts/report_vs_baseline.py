#!/usr/bin/env python3
"""Summarise a plus-vs-baseline manual run (winner placement + reason + ACMI)."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

MAIN = Path(__file__).resolve().parent / "龙智杯第四届参赛资料-0810更新高倍速平台" / "☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版"
EVAL = MAIN / "Evaluation"
CASE_RE = re.compile(r"^(\d{4})(.*)$")

REASONS = ("全灭蓝方战斗机", "成功突防", "击落蓝方预警机",
           "击落红方预警机", "全灭红方战斗机")


def reason(text):
    for key in REASONS:
        if key in text:
            return key
    return text.strip()


def read_run(d):
    text = (d / "Result" / "SimuResultReport.txt").read_bytes().decode("gb18030", "replace")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    totals = (int(lines[0]), int(lines[1]))
    cases = {}
    for line in lines[2:]:
        m = CASE_RE.match(line)
        if m:
            cases[int(m.group(1))] = {
                "winner": ("red" if "红方获胜" in m.group(2)
                           else "blue" if "蓝方获胜" in m.group(2)
                           else "draw"),
                "reason": reason(m.group(2)),
                "raw": m.group(2).strip(),
            }
    metrics = {}
    mp = d / "analysis" / "acmi_metrics.json"
    if mp.exists():
        metrics = {r["case"]: r for r in json.loads(mp.read_text(encoding="utf-8"))["acmi"]
                   if not r.get("failed")}
    return totals, cases, metrics


def main():
    if len(sys.argv) < 3:
        print("usage: report_vs_baseline.py <plus_red_dir> <plus_blue_dir>", file=sys.stderr)
        return 2
    runs = [("plus 红方 / 原版 蓝方", Path(sys.argv[1]).resolve(), "red"),
            ("plus 蓝方 / 原版 红方", Path(sys.argv[2]).resolve(), "blue")]

    L = []
    add = L.append
    add("# 乐迪plus vs 原版乐迪：标准 100 场景双方向评测")
    add("")
    add("- 每批 100 场（标准 20 场景 × 5，编号 0001-0100），同一份 `SimuConfig.txt` / `AreaConfig.txt`")
    add("- 两批互为镜像部署，用于抵消红方先手/出生位置的结构性优势")
    add("")

    add("## 部署与比分")
    add("")
    add("| 批次 | plus 部署 | 原版部署 | plus 胜 | 原版胜 | 归档 |")
    add("|:---|:---|:---|---:|---:|:---|")
    loaded = []
    for label, d, plus_side in runs:
        totals, cases, metrics = read_run(d)
        plus_label = "ACAS_01/02(红)" if plus_side == "red" else "ACAS_03/04(蓝)"
        base_label = "ACAS_03/04(蓝)" if plus_side == "red" else "ACAS_01/02(红)"
        plus_wins = totals[0] if plus_side == "red" else totals[1]
        base_wins = totals[1] if plus_side == "red" else totals[0]
        add(f"| {label} | {plus_label} | {base_label} | {plus_wins} | {base_wins} | `{d.name}` |")
        loaded.append((label, d, plus_side, totals, cases, metrics, plus_wins, base_wins))
    add("")

    tot_plus = sum(x[6] for x in loaded)
    tot_base = sum(x[7] for x in loaded)
    n = tot_plus + tot_base
    draws = sum(1 for item in loaded for c in item[4].values() if c["winner"] == "draw")
    draw_note = f"，另有 {draws} 场平局" if draws else ""
    add(f"**合计：plus {tot_plus} : {tot_base} 原版（{tot_plus/(n-draws):.1%} 胜率，{n-draws} 场有胜负）{draw_note}**")
    add("")
    for label, d, plus_side, totals, cases, metrics, pw, bw in loaded:
        add(f"- {label}：plus {pw/100:.0%}")
    add("")

    add("## 判定原因")
    add("")
    add("平台的原因文本按**阵营**描述（「全灭蓝方战斗机」=红方胜，「击落红方预警机」=蓝方胜），下表已换算成取胜方。")
    add("")
    add("| 取胜方 | 判定原因 | 场次 |")
    add("|:---|:---|---:|")
    c_plus, c_base = Counter(), Counter()
    for label, d, plus_side, totals, cases, metrics, pw, bw in loaded:
        for case, c in cases.items():
            if c["winner"] == "draw":
                continue
            (c_plus if c["winner"] == plus_side else c_base)[c["reason"]] += 1
    for key in REASONS:
        if c_plus.get(key):
            add(f"| plus | {key} | {c_plus[key]} |")
        if c_base.get(key):
            add(f"| 原版 | {key} | {c_base[key]} |")
    add("")
    red_wins = sum(t[0] for _, _, _, t, _, _, _, _ in loaded)
    blue_wins = sum(t[1] for _, _, _, t, _, _, _, _ in loaded)
    add(f"- 红方合计胜 {red_wins}；蓝方合计胜 {blue_wins}；平局 {draws}")
    add("")

    add("## ACMI 指标（plus 侧 vs 原版侧）")
    add("")
    add("| 指标 | plus | 原版 |")
    add("|:---|---:|---:|")
    agg = {"plus": Counter(), "base": Counter()}
    keys = ["fighters_alive", "ewa_alive", "launches", "hits", "boundary", "ground", "penetration"]
    acc = {"plus": {k: 0 for k in keys}, "base": {k: 0 for k in keys}}
    cases_total = 0
    for label, d, plus_side, totals, cases, metrics, pw, bw in loaded:
        other = "blue" if plus_side == "red" else "red"
        for case, m in metrics.items():
            cases_total += 1
            acc["plus"]["fighters_alive"] += m[f"{plus_side}_fighters_alive"]
            acc["base"]["fighters_alive"] += m[f"{other}_fighters_alive"]
            acc["plus"]["ewa_alive"] += m[f"{plus_side}_ewa_alive"]
            acc["base"]["ewa_alive"] += m[f"{other}_ewa_alive"]
            acc["plus"]["launches"] += m[f"{plus_side}_launches"]
            acc["base"]["launches"] += m[f"{other}_launches"]
            acc["plus"]["hits"] += m[f"{plus_side}_hits"]
            acc["base"]["hits"] += m[f"{other}_hits"]
            acc["plus"]["boundary"] += m[f"{plus_side}_boundary"]
            acc["base"]["boundary"] += m[f"{other}_boundary"]
            acc["plus"]["ground"] += m[f"{plus_side}_ground"]
            acc["base"]["ground"] += m[f"{other}_ground"]
            acc["plus"]["penetration"] += int(m[f"{plus_side}_penetration"])
            acc["base"]["penetration"] += int(m[f"{other}_penetration"])
    add(f"| 战斗机存活 | {acc['plus']['fighters_alive']}/{2*cases_total} | {acc['base']['fighters_alive']}/{2*cases_total} |")
    add(f"| 预警机存活 | {acc['plus']['ewa_alive']}/{cases_total} | {acc['base']['ewa_alive']}/{cases_total} |")
    add(f"| 导弹发射 | {acc['plus']['launches']} | {acc['base']['launches']} |")
    add(f"| 导弹命中 | {acc['plus']['hits']}（{acc['plus']['hits']/max(1,acc['plus']['launches']):.1%}） | "
        f"{acc['base']['hits']}（{acc['base']['hits']/max(1,acc['base']['launches']):.1%}） |")
    add(f"| 越界场次 | {acc['plus']['boundary']} | {acc['base']['boundary']} |")
    add(f"| 坠地场次 | {acc['plus']['ground']} | {acc['base']['ground']} |")
    add(f"| 突防成功（ACMI 判定） | {acc['plus']['penetration']} | {acc['base']['penetration']} |")
    add("")
    add("> 提醒：平台单次运行不可复现，单批 100 场的比分带有 ±5~7 个百分点的噪声（见 `AB_repeat_report.md`）。")
    add("")

    add("## Tacview 回放建议")
    add("")
    for label, d, plus_side, totals, cases, metrics, pw, bw in loaded:
        other = "blue" if plus_side == "red" else "red"
        plus_pen = sorted(c for c, m in metrics.items() if m[f"{plus_side}_penetration"])
        base_pen = sorted(c for c, m in metrics.items() if m[f"{other}_penetration"])
        add(f"- {label}（`{d.name}`）：plus 突防 {', '.join('%04d' % c for c in plus_pen[:8]) or '无'}；"
            f"原版突防 {', '.join('%04d' % c for c in base_pen[:8]) or '无'}")
    add("")

    out = EVAL / "vs_baseline_report.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
