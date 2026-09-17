# -*- coding: utf-8 -*-
"""Add a per-aircraft re-attack cap as a single switch (default OFF)."""
import shutil
from pathlib import Path

f = Path(r"C:\Users\iop\Downloads\Compressed\第四届龙智杯参赛资料\龙智杯第四届参赛资料-0810更新高倍速平台\☆公开☆第四届“龙智杯”智能空战大赛-Python策略开发示例模板\PythonstrategyDemo\AIStrategy乐迪plus.py")
bak = f.with_name(f.name + ".before-reattack-cap-20260916.bak")
shutil.copy2(str(f), str(bak))
print("backed up ->", bak.name)

t = f.read_text(encoding="utf-8")

def sub(old, new):
    global t
    assert t.count(old) == 1, f"anchor x{t.count(old)}: {old[:60]!r}"
    t = t.replace(old, new, 1)

# 1) constant
sub("WTA_FOCUS_FIRE = False",
"""WTA_FOCUS_FIRE = False

# Re-attack cap.  The saturation cap above counts only IN-FLIGHT missiles
# (`_team_inflight_missiles_by_target` skips remainTime <= 0), so once a shot is
# deleted the same target looks "free" again and the same aircraft re-shoots it.
# Measured on the 09-14 plus-vs-baseline run (Evaluation/waste_report_20260914):
#   per-aircraft shot at one target  #1 43.5% | #2 28.4% | #3 2.9% | #4 0.8%
#   and 60.8% of all plus launches are this aircraft re-shooting its own target.
# 2 keeps the still-useful 2nd shot and drops the rest.  0 = disabled.
REATTACK_MAX_SHOTS_PER_TARGET = 0""")

# 2) helper, right after _record_launch
sub("""        self.memory.assigned_targets.add(target_id)
""",
"""        self.memory.assigned_targets.add(target_id)

    def _own_shots_at(self, target_id):
        \"\"\"本机本局已经对该目标发射过的次数（帧序判断可排除跨局残留）。\"\"\"
        if not target_id:
            return 0
        count = 0
        for shot in self.memory.missiles_fired:
            try:
                if shot.get('target_id') != target_id:
                    continue
                frame = int(shot.get('frame', 0))
            except (AttributeError, TypeError, ValueError):
                continue
            if self.frame - frame >= 0:
                count += 1
        return count
""")

# 3) the gate itself
sub("""        if not isinstance(target, dict) or not isinstance(fs, dict):
            return False
""",
"""        if not isinstance(target, dict) or not isinstance(fs, dict):
            return False

        if (REATTACK_MAX_SHOTS_PER_TARGET > 0
                and self._own_shots_at(target.get('tgtID', 0)) >= REATTACK_MAX_SHOTS_PER_TARGET):
            return False
""")

f.write_text(t, encoding="utf-8")
print("patched", f.name, len(t), "chars")
