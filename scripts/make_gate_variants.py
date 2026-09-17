# -*- coding: utf-8 -*-
"""Rebuild the gate variants byte-preserving (LF kept, only the two constants differ)."""
import hashlib
from pathlib import Path

demo = Path(r"C:\Users\iop\Downloads\Compressed\第四届龙智杯参赛资料\龙智杯第四届参赛资料-0810更新高倍速平台\☆公开☆第四届“龙智杯”智能空战大赛-Python策略开发示例模板\PythonstrategyDemo")
src = demo / "AIStrategy乐迪plus.py"
vdir = demo / "tmp" / "variants_20260917"
vdir.mkdir(parents=True, exist_ok=True)

raw = src.read_bytes()
nl = b"\r\n" if b"\r\n" in raw else b"\n"
print("source bytes", len(raw), "newline", nl)

a = b"ACE_SUPPORT_AUTHORITY = False"
b = b"ACE_BREAKTHROUGH_AUTHORITY = False"
assert raw.count(a) == 1 and raw.count(b) == 1

off = vdir / "AIStrategy_gates_off.py"
on = vdir / "AIStrategy_gates_on.py"
off.write_bytes(raw)
patched = raw.replace(a, b"ACE_SUPPORT_AUTHORITY = True", 1).replace(b, b"ACE_BREAKTHROUGH_AUTHORITY = True", 1)
on.write_bytes(patched)

for p in (off, on):
    d = p.read_bytes()
    print(f"{p.name}: {len(d)} bytes sha12={hashlib.sha256(d).hexdigest()[:12]}")

# byte-level diff proof: only the two switches differ
import difflib
A = off.read_text(encoding="utf-8").splitlines()
B = on.read_text(encoding="utf-8").splitlines()
d = list(difflib.unified_diff(A, B, "gates_off", "gates_on", lineterm="", n=1))
print("diff hunks:", sum(1 for l in d if l.startswith("@@")))
print("\n".join(d))
