#!/usr/bin/env python3
"""Render settings pages off-screen into docs/ images.

Quickshell's off-screen platform still gives a real scene graph, so the QML
side can grab its own window with `Item.grabToImage`. That makes documentation
screenshots deterministic (no compositor, no wallpaper, no window rules).

Usage: python3 scripts/screenshot.py [page ...]
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DEFAULT = [("about", "main.png"), ("users", "users.png"), ("appearance", "appearance.png")]


def capture(page: str, name: str) -> bool:
    target = DOCS / name
    env = dict(os.environ)
    env.update({
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_CONTROLS_STYLE": "Basic",
        "HYPRTK_SM_TEST": "1",
        "HYPRTK_SM_PAGE": page,
        "HYPRTK_SM_SHOT": str(target),
    })
    proc = subprocess.run(
        ["qs", "-p", str(ROOT)], capture_output=True, text=True,
        timeout=60, env=env, cwd=str(ROOT),
    )
    ok = proc.returncode == 0 and target.is_file()
    print(f"{page:<12} -> {target.relative_to(ROOT)}  {'ok' if ok else 'FAILED'}")
    if not ok:
        print((proc.stdout or "")[-1500:])
        print((proc.stderr or "")[-1500:])
    return ok


def main(argv: list[str]) -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    wanted = [(page, f"{page}.png") for page in argv] if argv else DEFAULT
    failures = 0
    for page, name in wanted:
        if not capture(page, name):
            failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
