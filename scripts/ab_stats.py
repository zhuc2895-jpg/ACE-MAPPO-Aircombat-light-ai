#!/usr/bin/env python3
"""Repeated-batch A/B analysis for the guide_msl_cnt fix.

A = today's build WITH the fix, B = today's build WITHOUT it.
Same 100 standard scenarios in the same order for every batch, so scenarios can
be paired; each batch is an independent stochastic realisation of the platform.
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

import numpy as np
from scipy import stats

MAIN = Path(__file__).resolve().parent / "龙智杯第四届参赛资料-0810更新高倍速平台" / "☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版"
EVAL = MAIN / "Evaluation"
CASE_RE = re.compile(r"^(\d{4})(.*)$")
SCENARIOS = list(range(1, 101))

METRICS = [
    ("red_fighters_alive", "红方战斗机存活"),
    ("red_ewa_alive", "红方预警机存活"),
    ("red_launches", "红方导弹发射"),
    ("red_hits", "红方导弹命中"),
    ("red_boundary", "红方越界"),
    ("sim_end_time", "仿真时长(s)"),
]


def load(run_dir: Path):
    text = (run_dir / "Result" / "SimuResultReport.txt").read_bytes().decode("gb18030", "replace")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    totals = (int(lines[0]), int(lines[1]))
    cases = {}
    for line in lines[2:]:
        m = CASE_RE.match(line)
        if m:
            cases[int(m.group(1))] = 1 if "红方获胜" in m.group(2) else 0
    errs = 0
    stdout = run_dir / "Simplat.stdout.txt"
    if stdout.exists():
        with stdout.open("rb") as fh:
            errs = sum(1 for raw in fh if b"UnboundLocalError" in raw)
    metrics = {}
    mp = run_dir / "analysis" / "acmi_metrics.json"
    if mp.exists():
        metrics = {r["case"]: r for r in json.loads(mp.read_text(encoding="utf-8"))["acmi"]
                   if not r.get("failed")}
    return {"dir": run_dir, "totals": totals, "cases": cases, "errs": errs, "metrics": metrics}


# Batches produced before the campaign used a different naming scheme; the
# yesterday archive is an older build and must stay out of this comparison.
EXTRA_A = {"manual_100_20260912_160432"}
EXCLUDE = {"manual_100_20260911_152331"}


def discover():
    a, b = [], []
    for d in sorted(EVAL.iterdir()):
        if not d.is_dir() or not (d / "Result" / "SimuResultReport.txt").exists():
            continue
        if d.name in EXCLUDE:
            continue
        if d.name.startswith(("Afixed", "A_fixed")) or d.name in EXTRA_A:
            a.append(load(d))
        elif d.name.startswith(("Bnofix", "B_nofix")):
            b.append(load(d))
    # sanity: the fix must be the only thing separating the two groups
    assert all(r["errs"] == 0 for r in a), [r["errs"] for r in a]
    assert all(r["errs"] > 0 for r in b), [r["errs"] for r in b]
    return a, b


def scenario_rates(runs, key="cases"):
    """Per-scenario mean over runs -> array of length 100."""
    return np.array([
        np.mean([r[key].get(s, np.nan) for r in runs])
        for s in SCENARIOS
    ])


def metric_rates(runs, metric):
    vals = []
    for s in SCENARIOS:
        per_run = [r["metrics"][s][metric] for r in runs if s in r["metrics"]]
        vals.append(np.mean(per_run) if per_run else np.nan)
    return np.array(vals)


def main():
    A, B = discover()
    L = []
    add = L.append

    add("# `guide_msl_cnt` 顺序修复：重复批次 A/B 判定")
    add("")
    add(f"- A（今日构建 + 修复）：{len(A)} 批 × 100 场")
    add(f"- B（今日构建未修复）：{len(B)} 批 × 100 场")
    add("- 每批场景、出生点、`AreaConfig`、ACMI 上限完全相同（标准 20 场景 × 5，编号 0001-0100）")
    add("- 平台单次运行不可复现，批次按 A/B 交替执行以抵消时间漂移")
    add("")

    add("## 各批次原始比分")
    add("")
    add("| 批次 | 构建 | 红方 | 蓝方 | `UnboundLocalError` |")
    add("|:---|:---|---:|---:|---:|")
    for tag, runs in (("A", A), ("B", B)):
        for r in runs:
            add(f"| `{r['dir'].name}` | {tag} | {r['totals'][0]} | {r['totals'][1]} | {r['errs']} |")
    add("")

    ra = [r["totals"][0] for r in A]
    rb = [r["totals"][0] for r in B]
    add("## 总分对比")
    add("")
    add("| 指标 | A 修复后 | B 未修复 |")
    add("|:---|---:|---:|")
    add(f"| 批次红方获胜数 | {', '.join(map(str, ra))} | {', '.join(map(str, rb))} |")
    add(f"| 均值 | {statistics.mean(ra):.1f} | {statistics.mean(rb):.1f} |")
    if len(ra) > 1 and len(rb) > 1:
        add(f"| 批次间标准差 | {statistics.stdev(ra):.1f} | {statistics.stdev(rb):.1f} |")
    add("")

    add("## 逐场景配对检验（主分析）")
    add("")
    add("每个场景在所有批次上的红方胜率作为一个配对观测（A 组 vs B 组，n=100 场景），")
    add("这样按场景消除了难度差异，剩下的差异才归因于构建。")
    add("")
    pa = scenario_rates(A)
    pb = scenario_rates(B)
    d = pa - pb
    t_stat, p_val = stats.ttest_rel(pa, pb)
    try:
        w_stat, w_p = stats.wilcoxon(pa, pb)
    except ValueError:
        w_stat, w_p = float("nan"), float("nan")
    wins = int((d > 0).sum())
    losses = int((d < 0).sum())
    ties = int((d == 0).sum())
    add("| 量 | 值 |")
    add("|:---|---:|")
    add(f"| 红方胜率 A | {pa.mean():.1%} |")
    add(f"| 红方胜率 B | {pb.mean():.1%} |")
    add(f"| 差值 (A-B) | {d.mean():+.1%} |")
    add(f"| 配对 t 检验 | t={t_stat:.2f}, p={p_val:.3f} |")
    add(f"| Wilcoxon 符号秩 | W={w_stat:.0f}, p={w_p:.3f} |")
    add(f"| 场景符号统计 | A 更好 {wins} / B 更好 {losses} / 相同 {ties} |")
    add("")

    # cluster bootstrap on the per-scenario difference
    rng = np.random.default_rng(20260912)
    boots = []
    for _ in range(5000):
        idx = rng.integers(0, len(d), len(d))
        boots.append(d[idx].mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    add(f"- 场景聚类 bootstrap 95% 置信区间：`[{lo:+.1%}, {hi:+.1%}]`"
        + ("（不含 0，差异显著）" if lo > 0 or hi < 0 else "（含 0，无法排除无差异）"))
    add("")

    add("## 其他指标（同样按场景配对）")
    add("")
    add("| 指标 | A 均值 | B 均值 | 差值 | p 值 |")
    add("|:---|---:|---:|---:|---:|")
    for key, label in METRICS:
        va = metric_rates(A, key)
        vb = metric_rates(B, key)
        if np.all(np.isnan(va)) or np.all(np.isnan(vb)):
            continue
        t, p = stats.ttest_rel(va, vb, nan_policy="omit")
        add(f"| {label} | {np.nanmean(va):.2f} | {np.nanmean(vb):.2f} | "
            f"{np.nanmean(va)-np.nanmean(vb):+.2f} | {p:.3f} |")
    add("")

    add("## 结论")
    add("")
    add(f"1. 修复的效果在**异常次数**上是确定的：A 组全部 {sum(r['errs'] for r in A)} 次，"
        f"B 组 {sum(r['errs'] for r in B)} 次。")
    if lo > 0 or hi < 0:
        add(f"2. 红方胜率差异 {d.mean():+.1%}，95% CI `[{lo:+.1%}, {hi:+.1%}]` 不含 0，"
            "可以认为这行修复对胜率有真实影响。")
    else:
        add(f"2. 红方胜率差异 {d.mean():+.1%}，95% CI `[{lo:+.1%}, {hi:+.1%}]` 含 0，"
            f"配对 p={p_val:.3f}：**在现有批次数量下，这行修复对胜率没有可检出的影响**。"
            "它修的是「受威胁帧整帧丢决策」这一确定性缺陷，胜负层面的收益被平台自身的"
            "随机性淹没了。")
    add("")

    out = EVAL / "AB_repeat_report.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
