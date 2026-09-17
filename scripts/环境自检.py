"""龙智杯 Python 策略提交前环境自检。"""

from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path


def check(label: str, passed: bool, detail: str) -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {label}: {detail}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform-root", default=".")
    root = Path(parser.parse_args().platform_root).resolve()
    results = []

    results.append(check("Python版本", sys.version_info[:2] == (3, 8),
                         f"{sys.version.split()[0]}，要求 3.8"))
    results.append(check("输出目录", (root / "Result").is_dir() and (root / "AcmiRecord").is_dir(),
                         f"{root} 下必须存在 Result/ 与 AcmiRecord/"))

    for name in ("numpy", "torch"):
        try:
            module = __import__(name)
            results.append(check(f"依赖 {name}", True, getattr(module, "__version__", "unknown")))
        except Exception as exc:
            results.append(check(f"依赖 {name}", False, repr(exc)))

    for port in (9390, 9490, 9590, 9690, 9790, 9800, 9900):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(("127.0.0.1", port))
            results.append(check(f"UDP端口 {port}", True, "可绑定"))
        except OSError as exc:
            results.append(check(f"UDP端口 {port}", False, str(exc)))
        finally:
            sock.close()

    home = os.environ.get("LONGZHI_PYTHON_HOME")
    results.append(check("Python路径", bool(home),
                         home or r"未设置，将回退到 D:\anaconda\envs\mappo"))
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
