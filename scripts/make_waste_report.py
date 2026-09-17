#!/usr/bin/env python3
"""Assemble the waste/effectiveness report."""
from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
J = list(csv.DictReader((ROOT / "_inv" / "missile_join.csv").open(encoding="utf-8")))
CASE = list(csv.DictReader((ROOT / "waste_acmi_cases.csv").open(encoding="utf-8-sig")))

def f(v):
    try: return float(v)
    except (TypeError, ValueError): return None
for r in J:
    r["date"] = "0914" if "vs2_" in r["batch"] else "0912"
    r["plus_side"] = "red" if "plus_red" in r["batch"] else "blue"
    r["kind"] = "plus" if ((r["plus_side"]=="red" and r["side"]=="Red") or
                           (r["plus_side"]=="blue" and r["side"]=="Blue")) else "yuandi"
    r["role"] = "lead" if r["launcher"] in ("1","3") else "wing"
    r["hit"] = 1 if r["hit_strict"]=="1" else 0
    sr, rx = f(r["env_slantRange"]), f(r["env_Rmax"])
    r["rf"] = sr/rx if (sr and rx) else None
    r["lock"] = r["locked_tgt_id"] or None
    r["scen"] = ((int(r["case"])-1) % 20) + 1

g = defaultdict(list)
for r in J:
    if r["lock"]: g[(r["batch"], r["case"], r["side"], r["lock"])].append(r)
for grp in g.values():
    grp.sort(key=lambda x: float(x["launch_time"]))
    for i, r in enumerate(grp): r["ordinal"] = i+1
for r in J: r.setdefault("ordinal", 1)

def agg(sel):
    n = len(sel); h = sum(x["hit"] for x in sel)
    return n, h, (h/n if n else 0.0)

L = []
add = L.append
add("# 乐迪plus 发射效率专题：1140 发为什么只有 26% 命中")
add("")
add("**结论（一句话）**：这不是「打得差」，而是**分母被补射灌水**——多出的 334 发里约 86% 是"
    "对同一目标打出的第 3、4 发，而这两档的命中率是 0–2%；首发效率两版几乎没变（51.1% → 47.9%）。")
add("")
add("## 口径")
add("- 对比：**09-12 构建**（`6B28BB46ADF0`）vs **09-14 被测构建**（`30913FD36F19`），"
    "各自 plus 红/plus 蓝两个方向 × 100 场标准场景。")
add("- 命中判定改为**严格同帧规则**（弹与敌机在同一个 0.1 s 帧块内被删除）；"
    "旧的 ±1.5 s / ≤5 km 宽松规则会多造 14 对假命中，已废弃。")
add("- 3021 发导弹来自 `_inv/missile_join.csv`：ACMI 与 `ACAS_04` 调试日志按"
    "（射手, 发射时刻）对齐，锁定目标覆盖 **99.1%**、包线字段覆盖 **95.9%**。"
    "包线数据是发射前最近的 25 帧（≈2.5 s）采样，不是发射瞬间，属近似。")
add("")

add("## 一、多出来的弹都在哪一档")
add("")
add("| 同一目标的第 N 发 | 09-12 发数 | 09-12 命中率 | 09-14 发数 | 09-14 命中率 |")
add("|---:|---:|---:|---:|---:|")
tot = {}
for od in (1,2,3,4):
    a = [r for r in J if r["date"]=="0912" and r["kind"]=="plus" and min(r["ordinal"],4)==od]
    b = [r for r in J if r["date"]=="0914" and r["kind"]=="plus" and min(r["ordinal"],4)==od]
    na, ha, ra = agg(a); nb, hb, rb = agg(b)
    tot[od] = (na, nb)
    add(f"| 第 {od} 发 | {na} | {ra:.1%} | {nb} | {rb:.1%} |")
n3a = tot[3][0]+tot[4][0]; n3b = tot[3][1]+tot[4][1]
add("")
share = (n3b - n3a) / ((tot[1][1] + tot[2][1] + n3b) - (tot[1][0] + tot[2][0] + n3a))
add(f"- 第 3 发及以后：**{n3a} → {n3b}（+{n3b-n3a}）**，"
    f"占全部增量的 **{share:.0%}**。")
add(f"- 首发：{tot[1][0]} → {tot[1][1]}（反而略降），首发贡献的命中 214 → 194。")
add("")

add("![补射边际价值](waste_charts3.png)")
add("")
add("## 二、谁在补射：僚机")
add("")
add("| 日期 | 角色 | 发射 | 命中率 |")
add("|:---|:---|---:|---:|")
for date in ("0912","0914"):
    for role, label in (("lead","长机(1/3)"),("wing","僚机(2/4)")):
        s = [r for r in J if r["date"]==date and r["kind"]=="plus" and r["role"]==role]
        n,h,rt = agg(s)
        add(f"| {date} | {label} | {n} | {rt:.1%} |")
add("")
add("- 增量几乎全部来自僚机：**432 → 744（+312）**，而长机只 374 → 396（+22）。")
add("- 僚机从「最准的射手」变成「最差的射手」：命中率 **45.1% → 25.0%**。")
add("- 对照：原版乐迪的角色分布是平的（长机 33.0%→34.8%，僚机 23.4%→36.5%），"
    "说明这是 plus 特有的结构问题。")
add("")

add("![长机与僚机](waste_charts2.png)")
add("")
add("## 三、按场景：浪费集中在哪")
add("")
add("| 场景 | 09-12 发射 | 09-12 命中率 | 09-14 发射 | 09-14 命中率 | Δ发射 | Δ命中 | 僚机浪费* |")
add("|---:|---:|---:|---:|---:|---:|---:|---:|")
tb = []
for s in range(1,21):
    a = [r for r in J if r["date"]=="0912" and r["kind"]=="plus" and r["scen"]==s]
    b = [r for r in J if r["date"]=="0914" and r["kind"]=="plus" and r["scen"]==s]
    na,ha,ra = agg(a); nb,hb,rb = agg(b)
    w = [r for r in b if r["role"]=="wing"]; nw,hw,_ = agg(w)
    tb.append((s, na, ra, nb, rb, nb-na, hb-ha, nw-hw))
for row in sorted(tb, key=lambda x: -x[7]):
    s,na,ra,nb,rb,dl,dh,waste = row
    add(f"| {s} | {na} | {ra:.1%} | {nb} | {rb:.1%} | {dl:+d} | {dh:+d} | {waste} |")
add("")
add("\\* 僚机浪费 = 09-14 该场景僚机发射数 − 僚机命中数。")
add("")
add("- **浪费不是集中在少数场景**：20 个场景里有 18 个发射增加（+12~+28），"
    "命中率普遍从 27–49% 掉到 21–38%。")
add("- 最差的几个（Δ命中 ≤ 0）：**s12（+16 发，−5 命中）、s7（+28，−3）、s19（+21，−3）、"
    "s5/s10/s18（+21/+17/+16，−1）**；s11/s14/s16 多发 16–17 发，命中零增长。")
add("- 只有 s15 发射下降（−4），s20 增量最小（+5）。")
add("")

add("![逐场景发射与命中率](waste_charts.png)")
add("")
add("## 四、机制定位（这是可改的部分）")
add("")
add("1. **补射没有节流。** `WTA_TARGET_MISSILE_CAP = 2` 的上限只统计**在飞**导弹"
    "（`_team_inflight_missiles_by_target()` 跳过 `remainTime <= 0`），所以一枚打空、"
    "计数归零后，同一目标立刻「解禁」，可以再补一发。第 3/4 发就是这么来的。")
add("2. **分流本身很弱。** 那段饱和分流只在 `len(scored_targets) > 1` 时生效，"
    "且要求替代目标距离不超过最优目标的 1.25 倍；两架敌机都被打饱和后就没有替代目标，"
    "于是继续对着饱和目标打。")
add("3. **距离波段不是独立病因。** 表面看 0.55–0.70×Rmax 这一档命中率只有 4%，"
    "新构建在该档多打了 207 发；但交叉表显示它与「第几发」高度共线——"
    "同一档位里首发能到 48–54%，第 3 发几乎全灭。**真正的自变量是「第几发」，不是距离。**")
add("4. **离轴角无差别**：命中与未命中的发射时刻 aspect 中位数都是 ~3.05 rad（≈175°），"
    "角度门不是问题。")
add("")

add("## 五、和 09-12 的差异来源")
add("")
add("代码层（68 hunk / +501 −68 行）里能改变发射频率的，按证据强度排：")
add("")
add("| 改动 | 状态 | 方向 | 数据支持 |")
add("|:---|:---|:---|:---|")
add("| 新增僚机补射路径 `WINGMAN_FIRE_WHEN_READY=True` | 启用 | 增加 | **强**：增量 312/334 落在僚机 |")
add("| ACE 层不再抢占 support/breakthrough 分支 | 启用 | 增加 | 中：落入发射分支的帧变多 |")
add("| `launchPlaneID` 归属修复（旧版约 75% 帧对 1 号机下清锁指令） | 启用 | 增加 | 中：长机发射 374→396，幅度小 |")
add("| 蓝方防御线几何修正 + 规避后重开传感器 | 启用 | 增加 | 弱：开场提前接触 |")
add("| 删除单条 `envInfos` 兜底 | 启用 | **减少** | 弱：反向，未能量化 |")
add("")
add("**四大发射门（`_can_fire_missile` / `_is_launch_window` / `_record_launch` / "
    "`_should_launch_as_wingman`）两版逐字节相同**，冷却、`0.8×Rmax` 门限、NEZ 设置都没动。"
    "所以这不是「门槛放松」，是**路径变多 + 补射没有节流**。")
add("")

add("## 六、红方 39 场输局（第二部分）")
add("")
add("| 批次 | plus 位置 | 胜 | 负 | 平 |")
add("|:---|:---|---:|---:|---:|")
for date in ("0912","0914"):
    for tag in ("plus_red","plus_blue"):
        sel = [c for c in CASE if c["date"]==date and c["tag"]==tag]
        ps = sel[0]["plus_side"]
        w = sum(1 for c in sel if c["winner"]==ps)
        l = sum(1 for c in sel if c["winner"] not in (ps,"draw"))
        d = sum(1 for c in sel if c["winner"]=="draw")
        add(f"| {date} | {'红方' if ps=='red' else '蓝方'} | {w} | {l} | {d} |")
add("")
add("输局**全部发生在 plus 打红方那一侧**（plus 打蓝方两版都是 100:0）。09-14 的 39 场输局构成：")
add("- **全灭红方战斗机 26 场**：s8、s12、s13、s14、s18、s19 各 3 场，s7、s11 各 2 场")
add("- **击落红方预警机 13 场**：s7、s20 各 2 场（09-12 是 22 场，这项明显改善）")
add("")
add("值得注意：**输局集中的场景（s8/s12/s13/s14/s18/s19）几乎就是补射最浪费的场景**"
    "（见第三节），即红方在那些场景里一边对饱和目标补射、一边被打掉战斗机。")
add("")

add("## 七、建议（按性价比排序）")
add("")
add("1. **给补射加节流（最高性价比、最小改动）**：把 `WTA_TARGET_MISSILE_CAP` 的口径从"
    "「在飞导弹」改成「本次交战中已对该目标发射过的总数」，或在打空后加一个再攻击冷却"
    "（如 30–50 帧）。数据支持：第 3/4 发命中率 0–2%，砍掉它们不会损失命中数，"
    "但能省掉约 286 发/200 场的无效发射。")
add("2. **让分流在单目标时也生效**：现在 `len(scored_targets) > 1` 才启用，"
    "两机饱和后直接失效。")
add("3. **给僚机补射加资格条件**：不只看 `_can_fire_missile`，还要看该目标是否已有过"
    "本方的失败射击（僚机 45.1%→25.0% 的塌陷就发生在这条路径上）。")
add("4. **验证方式**：以上任一条改完后，按本次口径重跑 plus 红/蓝各 100 场，"
    "对比「首发命中率」与「第 3 发及以后占比」两个指标即可判定，不需要看总分"
    "（总分噪声 ±5~7 个百分点，见 `AB_repeat_report.md`）。")
add("")

add("## 产出文件")
add("")
add("- `waste_charts.png`：逐场景发射/命中率 + 各机发射数")
add("- `waste_charts3.png`：补射边际价值（同一目标第 N 发的命中率）")
add("- `waste_charts2.png`：命中率-Rmax 波段曲线 + 长机/僚机发射与命中率")
add("- `waste_by_scenario.csv`、`waste_acmi_missiles.csv`、`waste_acmi_cases.csv`")
add("- `_inv/missile_join.csv`：3021 发导弹的 ACMI×日志联合表（含锁定目标与包线字段）")
add("- 脚本：`waste_analysis.py`、`waste_analysis2.py`、`waste_analysis3.py`、`waste_join_analysis.py`、`waste_crosstab.py`")

(ROOT / "waste_report.md").write_text("\n".join(L), encoding="utf-8")
print("wrote waste_report.md", len("\n".join(L)), "chars")

# ordinal chart
fig, ax = plt.subplots(figsize=(7, 4.2))
ods = [1,2,3,4]
for date, col in (("0912","#888"), ("0914","#c0392b")):
    ns, rs = [], []
    for od in ods:
        s = [r for r in J if r["date"]==date and r["kind"]=="plus" and min(r["ordinal"],4)==od]
        n,h,rt = agg(s); ns.append(n); rs.append(rt*100)
    ax.plot([str(o) for o in ods], rs, "o-", color=col, label=f"{date} hit%")
    for i, n in enumerate(ns):
        ax.annotate(f"n={n}", (i, rs[i]), textcoords="offset points", xytext=(0,8), ha="center", fontsize=8)
ax.set_xlabel("Nth missile on the same target"); ax.set_ylabel("strict hit rate %")
ax.set_title("Marginal value of follow-up shots (plus side)"); ax.legend()
fig.tight_layout(); fig.savefig(ROOT / "waste_charts3.png", dpi=130)
print("wrote waste_charts3.png")
