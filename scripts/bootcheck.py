#!/usr/bin/env python3
"""Headless boot check: load the shell and one page of each kind, then exit.

Uses Quickshell's off-screen platform so it needs no display. The QML side calls
Qt.exit(0) once the backend has served the requested panel, and Qt.exit(1) if
the backend dies; this script adds a hard timeout and scans stderr for load
errors that would otherwise be swallowed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PAGES = ["about", "displays", "users", "suite", "privacy", "power", "storage", "bar"]
ROOT = Path(__file__).resolve().parents[1]


def run(page: str) -> tuple[int, str]:
    env = dict(os.environ)
    env.update({
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_CONTROLS_STYLE": "Basic",
        "HYPRTK_SM_TEST": "1",
        "HYPRTK_SM_PAGE": page,
    })
    proc = subprocess.run(
        ["qs", "-p", str(ROOT)],
        capture_output=True, text=True, timeout=60, env=env, cwd=str(ROOT),
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    failures = 0
    for page in PAGES:
        try:
            code, output = run(page)
        except subprocess.TimeoutExpired:
            print(f"{page:<10} TIMEOUT")
            failures += 1
            continue
        problems = [
            line for line in output.splitlines()
            if ("Error" in line or "is not a type" in line)
            and "WAYLAND_DISPLAY" not in line
            and "hyprland-toplevel" not in line
            and "host portal" not in line
            and "Failed to register" not in line
        ]
        if code != 0 or problems:
            failures += 1
            print(f"{page:<10} FAIL exit={code}")
            for line in problems[:8]:
                print("   " + line.strip())
        else:
            print(f"{page:<10} ok")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
