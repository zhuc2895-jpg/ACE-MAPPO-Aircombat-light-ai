#!/usr/bin/env python3
"""3x200 interleaved A/B: ACE_SUPPORT/BREAKTHROUGH_AUTHORITY False vs True."""
from __future__ import annotations

import csv, json, re, statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent
EVAL = (ROOT / "龙智杯第四届参赛资料-0810更新高倍速平台"
        / "☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版" / "Evaluation")
CASE_RE = re.compile(r"^(\d{4})(.*)$")
SCEN = list(range(1, 21))

def load(d):
    t = (d / "Result" / "SimuResultReport.txt").read_bytes().decode("gb18030", "replace")
    lines = [l.strip() for l in t.splitlines() if l.strip()]
    totals = (int(lines[0]), int(lines[1]))
    cases = {}
    for line in lines[2:]:
        m = CASE_RE.match(line)
        if m:
            n = int(m.group(1)); txt = m.group(2)
            w = "red" if "红方获胜" in txt else ("blue" if "蓝方获胜" in txt else "draw")
            cases[n] = w
    plus = "red" if "plus_red" in d.name else "blue"
    metrics = {}
    mp = d / "analysis" / "acmi_metrics.json"
    if mp.exists():
        metrics = {r["case"]: r for r in json.loads(mp.read_text(encoding="utf-8"))["acmi"] if not r.get("failed")}
    return {"dir": d, "totals": totals, "cases": cases, "plus": plus, "metrics": metrics}

runs = {"on": [], "off": []}
for d in sorted(EVAL.iterdir()):
    if not d.is_dir() or not d.name.startswith("gates_"):
        continue
    if not (d / "Result" / "SimuResultReport.txt").exists():
        continue
    v = "on" if d.name.startswith("gates_on_") else "off"
    runs[v].append(load(d))

print("=== per-batch scores (red : blue) ===")
for v in ("on", "off"):
    for r in sorted(runs[v], key=lambda x: x["dir"].name):
        print(f"  {r['dir'].name:44} plus={r['plus']:4}  {r['totals'][0]:3d} : {r['totals'][1]:3d}  -> plus wins {r['totals'][0] if r['plus']=='red' else r['totals'][1]}")

print("\n=== per-variant ===")
summary = {}
for v in ("on", "off"):
    rs = runs[v]
    wins = [r["totals"][0] if r["plus"] == "red" else r["totals"][1] for r in rs]
    summary[v] = {"wins": wins, "total": sum(wins), "n": 100 * len(rs)}
    print(f"  gates_{v:3}: batches={len(rs)} plus wins={wins}  total={sum(wins)}/{100*len(rs)} = {sum(wins)/(100*len(rs)):.1%}  mean/batch={statistics.mean(wins):.1f}")

# scenario-paired
def scen_rate(rs):
    out = {}
    for s in SCEN:
        obs = []
        for r in rs:
            for case, w in r["cases"].items():
                if ((case - 1) % 20) + 1 == s:
                    obs.append(1 if w == r["plus"] else 0)
        out[s] = np.mean(obs) if obs else np.nan
    return np.array([out[s] for s in SCEN])

pa, pb = scen_rate(runs["on"]), scen_rate(runs["off"])
d = pa - pb
t, p = stats.ttest_rel(pa, pb)
w, wp = stats.wilcoxon(pa, pb)
rng = np.random.default_rng(20260917)
boot = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)]
lo, hi = np.percentile(boot, [2.5, 97.5])
print("\n=== scenario-paired test (n=20 scenarios, 30 obs each) ===")
print(f"  plus win rate  gates_on={pa.mean():.1%}  gates_off={pb.mean():.1%}  diff={d.mean():+.1%}")
print(f"  paired t: t={t:.2f} p={p:.3f} | Wilcoxon p={wp:.3f} | bootstrap 95% CI [{lo:+.1%}, {hi:+.1%}]")
print(f"  scenarios where on better: {(d>0).sum()}  off better: {(d<0).sum()}  tie: {(d==0).sum()}")

print("\n=== ACMI efficiency (plus side, strict same-frame) ===")
for v in ("on", "off"):
    lau = hit = 0
    lead_l = lead_h = wing_l = wing_h = 0
    for r in runs[v]:
        for case, m in r["metrics"].items():
            ps = r["plus"]
            lau += m[f"{ps}_launches"]; hit += m[f"{ps}_hits"]
    print(f"  gates_{v:3}: launches={lau:5d} hits={hit:4d} rate={hit/lau:.1%}")

print("\n=== win-rate spread across batches (noise check) ===")
for v in ("on", "off"):
    ws = summary[v]["wins"]
    print(f"  gates_{v:3}: {ws}  sd={statistics.stdev(ws):.1f}")
