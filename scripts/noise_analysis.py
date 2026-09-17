# -*- coding: utf-8 -*-
"""Run-to-run noise analysis for a fixed strategy build (archived data only)."""
import json, os, sys, statistics as st
sys.stdout.reconfigure(encoding="utf-8")

EVAL = r"C:\Users\iop\Downloads\Compressed\第四届龙智杯参赛资料\龙智杯第四届参赛资料-0810更新高倍速平台\☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版\Evaluation"
BATCHES = ["A_fixed_20260912_152901", "manual_100_20260912_160432",
           "Afixed_20260912_163129", "Afixed_20260912_165400"]
N_BASE = 20
REPEATS = 5

def load(b):
    with open(os.path.join(EVAL, b, "analysis", "acmi_metrics.json"), encoding="utf-8") as fh:
        return json.load(fh)["acmi"]

rows = {b: load(b) for b in BATCHES}
for b in BATCHES:
    assert len(rows[b]) == 100, (b, len(rows[b]))
    assert [r["case"] for r in rows[b]] == list(range(1, 101)), b

L = "=" * 78
print(L); print("1) PER-BATCH TOTALS (100 cases each; red+blue = both sides)"); print(L)
print(f"{'batch':<32}{'R_lau':>7}{'R_hit':>7}{'B_lau':>7}{'B_hit':>7}{'Lau':>7}{'Hit':>7}{'Rate':>8}")
per = {}
for b in BATCHES:
    r = rows[b]
    rl = sum(x["red_launches"] for x in r); rh = sum(x["red_hits"] for x in r)
    bl = sum(x["blue_launches"] for x in r); bh = sum(x["blue_hits"] for x in r)
    tl, th = rl + bl, rh + bh
    hr = th / tl
    per[b] = dict(rl=rl, rh=rh, bl=bl, bh=bh, tl=tl, th=th, hr=hr)
    print(f"{b:<32}{rl:>7}{rh:>7}{bl:>7}{bh:>7}{tl:>7}{th:>7}{hr:>7.1%}")

print()
print(L); print("2) ACROSS THE 4 BATCHES: mean / sample SD (ddof=1)"); print(L)
tl = [per[b]["tl"] for b in BATCHES]
hr = [per[b]["hr"] for b in BATCHES]
m_tl, s_tl = st.mean(tl), st.stdev(tl)
m_hr, s_hr = st.mean(hr), st.stdev(hr)
print("total launches per batch : {0}  mean={1:.2f}  SD={2:.2f}  range={3}..{4}  CV={5:.2%}".format(tl, m_tl, s_tl, min(tl), max(tl), s_tl/m_tl))
print("hit rate per batch       : {0}  mean={1:.4f}  SD={2:.4f}  range={3:.2%}..{4:.2%}".format(
    ["{:.2%}".format(x) for x in hr], m_hr, s_hr, min(hr), max(hr)))
# 95% CI on the mean (t, df=3) and on the SD scale
t_crit = 3.182446305  # t(0.975, df=3)
print("mean total launches 95% CI (t,df=3): [{0:.1f}, {1:.1f}]  +/-{2:.1f}".format(
    m_tl - t_crit*s_tl/2, m_tl + t_crit*s_tl/2, t_crit*s_tl/2))
print("SD of total launches 95% CI (chi2, df=3): [{0:.1f}, {1:.1f}]".format(
    s_tl*((3)/11.3453)**0.5, s_tl*((3)/0.351846)**0.5))
print("per-case launches (n=400) : mean={0:.3f}  SD={1:.3f}".format(
    st.mean([x for b in BATCHES for x in [r["red_launches"]+r["blue_launches"] for r in rows[b]]]),
    st.stdev([x for b in BATCHES for x in [r["red_launches"]+r["blue_launches"] for r in rows[b]]])))
# spread of batch launches in relative terms
print("max-min spread of batch totals: {0} ({1:.2%} of mean)".format(max(tl)-min(tl), (max(tl)-min(tl))/m_tl))
print("max-min spread of batch hit rate: {0:.2%} (pp: {1:.2f})".format(max(hr)-min(hr), (max(hr)-min(hr))*100))

print()
print(L); print("3) PER BASE SCENARIO (20 base x 4 batches x 5 repeats = 20 obs each)"); print(L)
base = {}
for bi in range(1, N_BASE + 1):
    vals = []
    for b in BATCHES:
        for r in rows[b]:
            if (r["case"] - 1) % N_BASE + 1 == bi:
                vals.append(r["red_launches"] + r["blue_launches"])
    assert len(vals) == 20, (bi, len(vals))
    base[bi] = (st.mean(vals), st.stdev(vals), vals)
grand = st.mean([base[i][0] for i in range(1, N_BASE+1)])
print("grand mean launches/case over 20 base scenarios: {0:.2f}  (SD across the 20 scenario means: {1:.2f})".format(
    grand, st.stdev([base[i][0] for i in range(1, N_BASE+1)])))
print("mean within-scenario SD (across 20 base scenarios): {0:.2f}  range {1:.2f}..{2:.2f}".format(
    st.mean([base[i][1] for i in range(1, N_BASE+1)]),
    min(base[i][1] for i in range(1, N_BASE+1)), max(base[i][1] for i in range(1, N_BASE+1))))
print()
ordered = sorted(range(1, N_BASE+1), key=lambda i: base[i][0], reverse=True)
print("TOP 5 base scenarios by launches/case:")
for i in ordered[:5]:
    print("   base {0:>2}: mean={1:6.2f}  SD={2:5.2f}  obs={3}".format(i, base[i][0], base[i][1], base[i][2]))
print("BOTTOM 5 base scenarios by launches/case:")
for i in ordered[-5:]:
    print("   base {0:>2}: mean={1:6.2f}  SD={2:5.2f}  obs={3}".format(i, base[i][0], base[i][1], base[i][2]))
print()
print("full table (base: mean +/- SD):")
for i in range(1, N_BASE+1):
    print("   base {0:>2}: {1:6.2f} +/- {2:5.2f}".format(i, base[i][0], base[i][1]))

print()
print(L); print("4) VERDICT INPUTS"); print(L)
a200, b200 = 806, 1140
print("observed plus-side launches over 200 cases: 2026-09-12 = {0}, 2026-09-14 = {1}".format(a200, b200))
print("change = +{0} ({1:+.1%})".format(b200-a200, b200/a200 - 1))
print("per-case: {0:.3f} -> {1:.3f} launches/case".format(a200/200, b200/200))
# noise floor, expressed on a 200-case basis
s200 = s_tl * (2 ** 0.5)
print("batch-total SD (100 cases, both sides) = {0:.1f}".format(s_tl))
print("implied SD for a 200-case total (x sqrt2) = {0:.1f}".format(s200))
print("SD of the DIFFERENCE between two independent 200-case totals = sqrt(2)*s200 = {0:.1f}".format(s200*(2**0.5)))
print("z of the observed +{0} change  = {1:.2f}".format(b200-a200, (b200-a200)/(s200*(2**0.5))))
print("as multiples of the 100-case batch SD: {0:.1f} x SD".format((b200-a200)/s_tl))
print("change relative to mean batch total ({0:.1f}): {1:+.1%}".format(m_tl, (b200-a200)/m_tl))
tot = sum(tl)
print("AB-campaign 4-batch pooled: {0} launches over 400 cases = {1:.3f}/case".format(tot, tot/400))
