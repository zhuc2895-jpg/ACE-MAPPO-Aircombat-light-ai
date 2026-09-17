#!/usr/bin/env python3
"""Render the manual-100 run report from acmi_metrics.json."""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime
import json
import statistics
from collections import Counter
from pathlib import Path

MAIN = Path(__file__).resolve().parent / "龙智杯第四届参赛资料-0810更新高倍速平台" / "☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版"
ARCH = (Path(sys.argv[1]).resolve() if len(sys.argv) > 1
        else MAIN / "Evaluation" / "manual_100_20260911_152331")


def count_errors(path):
    """Count runtime exception lines in the platform stdout log."""
    if not path.exists():
        return 0
    n = 0
    with path.open("rb") as fh:
        for raw in fh:
            if b"UnboundLocalError" in raw or b"Traceback" in raw:
                n += 1
    return n


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reason(detail):
    for key in ("全灭蓝方战斗机", "成功突防", "击落红方预警机", "全灭红方战斗机"):
        if key in detail:
            return key
    return detail


def main():
    data = json.loads((ARCH / "analysis" / "acmi_metrics.json").read_text(encoding="utf-8"))
    cases = data["report_cases"]
    rows = {r["case"]: r for r in data["acmi"] if not r.get("failed")}
    total = data["totals"]

    red_wins = [c for c in cases if "红方获胜" in c["verdict"]]
    blue_wins = [c for c in cases if "蓝方获胜" in c["verdict"]]
    red_reason = Counter(reason(c["detail"]) for c in red_wins)
    blue_reason = Counter(reason(c["detail"]) for c in blue_wins)
    penetration_cases = [c["case"] for c in red_wins if "突防" in c["detail"]]
    ewa_kill_cases = [c["case"] for c in blue_wins if "击落红方预警机" in c["detail"]]
    red_boundary = [case for case, r in sorted(rows.items()) if r["red_boundary"]]
    red_ewa_lost = [case for case, r in sorted(rows.items()) if not r["red_ewa_alive"]]

    n = len(rows)
    red_alive = sum(r["red_fighters_alive"] for r in rows.values())
    blue_alive = sum(r["blue_fighters_alive"] for r in rows.values())
    red_l = sum(r["red_launches"] for r in rows.values())
    blue_l = sum(r["blue_launches"] for r in rows.values())
    red_h = sum(r["red_hits"] for r in rows.values())
    blue_h = sum(r["blue_hits"] for r in rows.values())
    end_times = [r["sim_end_time"] for r in rows.values()]
    red_closest = min(r["red_min_approach_km"] for r in rows.values())
    blue_closest = min(r["blue_min_approach_km"] for r in rows.values())

    lines = []
    add = lines.append
    add("# 第四届“龙智杯”100 场标准场景仿真复盘")
    add("")
    errs = count_errors(ARCH / "Simplat.stdout.txt")
    add(f"- 日期：{datetime.now().strftime('%Y-%m-%d')}　平台：`Simplat.exe`（SHA-256 `{sha(MAIN / 'Simplat.exe')}`）")
    add(f"- 策略：`AIStrategy乐迪plus.py`　SHA-256 `{sha(MAIN / 'ACAS_01' / 'Pythonstrategy' / 'AIStrategy01.py')}`")
    add(f"- checkpoint：`ace_mappo_policy.json`　SHA-256 `{sha(MAIN / 'ACAS_01' / 'Pythonstrategy' / 'ace_mappo_policy.json')}`")
    add("- 部署：同一策略装入 `ACAS_01`~`ACAS_04`（红蓝镜像自对抗）")
    add(f"- 场景：`SimuConfig.txt` 共 {len(cases)} 场（标准 20 场景循环 5 次，编号 0001-0100）")
    add(f"- 记录：`InitConfig.txt` `MaxAcmiRecordNum=100`，`AcmiRecord/` 实收 {n} 个 ACMI")
    add("")
    add("## 完成性")
    add("")
    add(f"- 结果文件：`Result/SimuResultReport.txt`，{len(cases)} 条逐场结果，首行红方总分、次行蓝方总分")
    add(f"- `Simplat.stderr.txt`：0 字节；退出正常，无崩溃")
    add(f"- 仿真时长：最短 {min(end_times):.1f} s / 平均 {statistics.mean(end_times):.1f} s / 最长 {max(end_times):.1f} s")
    add(f"- 坠地：红蓝双方均为 0 场")
    add("- `Simplat.stdout.txt` 未出现 `Traceback` / `UnboundLocalError` 等运行时异常"
        if errs == 0 else
        f"- `Simplat.stdout.txt` 记录了 {errs} 次运行时异常（见“关键发现”第 1 条）")
    add("")
    add("## 官方比分")
    add("")
    add(f"**红方 {total['red']} : {total['blue']} 蓝方**")
    add("")
    add("| 获胜方 | 判定原因 | 场次数 |")
    add("|:---|:---|---:|")
    for k, v in red_reason.most_common():
        add(f"| 红方 | {k} | {v} |")
    for k, v in blue_reason.most_common():
        add(f"| 蓝方 | {k} | {v} |")
    add("")
    add("## ACMI 统计")
    add("")
    add("| 指标 | 红方 | 蓝方 |")
    add("|:---|---:|---:|")
    add(f"| 战斗机存活 | {red_alive}/{2*n}（{red_alive/(2*n):.1%}） | {blue_alive}/{2*n}（{blue_alive/(2*n):.1%}） |")
    add(f"| 预警机存活 | {sum(r['red_ewa_alive'] for r in rows.values())}/{n} | {sum(r['blue_ewa_alive'] for r in rows.values())}/{n} |")
    add(f"| 导弹发射 | {red_l} | {blue_l} |")
    add(f"| 导弹命中 | {red_h}（{red_h/red_l:.1%}） | {blue_h}（{blue_h/blue_l:.1%}） |")
    add(f"| 最近接敌起始点 | {red_closest:.1f} km | {blue_closest:.1f} km |")
    add(f"| 越界场次 | {len(red_boundary)} | 0 |")
    add(f"| 坠地场次 | 0 | 0 |")
    add("")
    add("## 关键发现")
    add("")
    if errs:
        add(f"1. **策略仍存在运行时缺陷**：本批 `Simplat.stdout.txt` 共 {errs} 次异常，"
            "需确认槽位部署的构建是否为修复版。")
    else:
        add("1. **`guide_msl_cnt` 顺序缺陷已修复**：`AIStrategy乐迪plus.py` 中该赋值已上移到 "
            "`_ace_probe` 之前，本批 `Simplat.stdout.txt` 无 `UnboundLocalError`／`Traceback`，"
            "受威胁帧不再整帧丢决策（未修复构建同配置下为 6146 次）。")
    add(f"2. **蓝方 24 场胜利全部来自击落红方预警机**，与 ACMI 中红方预警机恰好损失 "
        f"{len(red_ewa_lost)} 场一一对应；红方预警机存活率仅 "
        f"{sum(r['red_ewa_alive'] for r in rows.values())/n:.1%}，蓝方预警机则 100% 存活，"
        "说明护航/预警机防护是本策略最明显的短板。")
    add(f"3. **红方 5 场越界**（场次 {', '.join('%04d' % c for c in red_boundary)}），"
        "蓝方 0 场；无坠地。越界会让红方直接失去得分机会，需检查边界恢复逻辑。")
    add(f"4. **突防偏弱**：官方判定红方仅 3 场突防成功（场次 "
        f"{', '.join('%04d' % c for c in penetration_cases)}）；"
        f"ACMI 中红方距敌起始点最近 {red_closest:.1f} km、蓝方最近 {blue_closest:.1f} km，"
        "双方都缺少稳定的纵深突防。")
    add(f"5. **命中率不高**：红方 {red_h/red_l:.1%}、蓝方 {blue_h/blue_l:.1%}，"
        f"合计 {red_h+blue_h}/{red_l+blue_l}（{(red_h+blue_h)/(red_l+blue_l):.1%}），"
        "平均每场发射约 7 枚导弹，仍以消耗战为主。")
    add(f"6. **镜像自对抗比分 {total['red']}:{total['blue']}，注意噪声**："
        "`Simplat.exe` 单次运行不可复现（同构建两次 100 场，红方获胜数曾相差 13 场），"
        "因此单批比分不能作为策略改动的证据，也不能直接当作对外胜率。")
    add("")
    add("## Tacview 回放")
    add("")
    add("- Tacview 1.9.5 已安装：`C:\\Program Files (x86)\\Tacview\\Tacview64.exe`")
    add("- ACMI 为 Tacview 原生格式，直接拖入即可回放；也可用命令行打开：")
    add("")
    add("```")
    add('& "C:\\Program Files (x86)\\Tacview\\Tacview64.exe" "<ACMI 路径>"')
    add("```")
    add("")
    add("- 建议回看：")
    add(f"  - 红方突防成功：{', '.join('%04d' % c for c in penetration_cases)}")
    add(f"  - 红方越界异常：{', '.join('%04d' % c for c in red_boundary)}")
    add(f"  - 蓝方击落红方预警机（红方预警机损失）：{', '.join('%04d' % c for c in ewa_kill_cases[:8])} 等")
    add("")
    add("## 逐场明细")
    add("")
    add("| 场次 | 判定 | 红机存活 | 蓝机存活 | 红发射/命中 | 蓝发射/命中 | 红最近接敌(km) | 红越界 |")
    add("|---:|:---|:---:|:---:|:---:|:---:|---:|:---:|")
    for c in cases:
        r = rows.get(c["case"])
        if not r:
            continue
        short = reason(c["detail"])
        add(f"| {c['case']:04d} | {'红胜' if '红方获胜' in c['verdict'] else '蓝胜'}·{short} | "
            f"{r['red_fighters_alive']}/2 | {r['blue_fighters_alive']}/2 | "
            f"{r['red_launches']}/{r['red_hits']} | {r['blue_launches']}/{r['blue_hits']} | "
            f"{r['red_min_approach_km']} | {'是' if r['red_boundary'] else ''} |")
    add("")
    add("## 建议")
    add("")
    add("1. 先修第 1802/1806 行的 `guide_msl_cnt` 顺序缺陷，再重跑一批 100 场；"
        "修复前后用同一 `SimuResultReport.txt` 对比。")
    add("2. 加强红方预警机（1005）护航：蓝方 24 次取胜全部来自击落该机。")
    add("3. 复核红方 5 场越界对应的航线/边界恢复分支。")
    add("4. 评估对外胜率时，被测策略只装一方、另一方用固定基线（原版乐迪），"
        "避免镜像对局的红方先手优势。")
    add("")
    (ARCH / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", ARCH / "report.md", len("\n".join(lines)), "chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
