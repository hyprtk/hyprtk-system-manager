"""Installed hyprtk applications: version, liveness and settings entry points.

Versions are read from the installed payload (never from ``--version``, because
the Quickshell apps forward that flag to ``qs``). Paths cover both the current
layout and the older one where the bar backend lived in the Quickshell config.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from . import util

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local" / "share"))


def _p(rel: str) -> Path:
    return DATA / rel


APPS = [
    {
        "id": "bar-qt", "name": "hyprtk-bar-qt", "title": "Bar",
        "binary": "hyprtk-bar-qt",
        "version_files": [
            HOME / ".config" / "quickshell" / "hyprtk-bar-qt" / "backend" / "hyprtk_bar_qt" / "__init__.py",
            _p("hyprtk-bar-qt/backend/hyprtk_bar_qt/__init__.py"),
        ],
        "settings": ["hyprtk-bar-qt-settings-toggle"],
        "process": r"qs\b.*hyprtk-bar-qt",
    },
    {
        "id": "file-manager", "name": "hyprtk-file-manager", "title": "Files",
        "binary": "hyprtk-fm",
        "version_files": [_p("hyprtk-file-manager/backend/hyprtk_file_manager/__init__.py")],
        "settings": ["hyprtk-fm", "--settings"],
        "process": r"hyprtk-fm|qs\b.*hyprtk-file-manager",
    },
    {
        "id": "term", "name": "hyprtk-term", "title": "Terminal",
        "binary": "hyprtk-term",
        "version_files": [_p("hyprtk-term/hyprtk_term/__init__.py")],
        "settings": ["hyprtk-term", "--settings"],
        "process": r"hyprtk-term",
    },
    {
        "id": "editor", "name": "hyprtk-editor", "title": "Text Editor",
        "binary": "hyprtk-edit",
        "version_files": [_p("hyprtk-editor/hyprtk_editor/__init__.py")],
        "settings": ["hyprtk-edit", "--preferences"],
        "process": r"hyprtk-edit",
    },
    {
        "id": "calc", "name": "hyprtk-calc", "title": "Calculator",
        "binary": "hyprtk-calc",
        "version_files": [_p("hyprtk-calc/hyprtk_calc/__init__.py")],
        "settings": [],
        "process": r"hyprtk-calc",
    },
    {
        "id": "shot", "name": "hyprtk-shot", "title": "Screenshot",
        "binary": "hyprtk-shot",
        "version_files": [_p("hyprtk-shot/hyprtk_shot/__init__.py")],
        "settings": [],
        "process": r"hyprtk-shot",
    },
    {
        "id": "rec", "name": "hyprtk-rec", "title": "Screen Recorder",
        "binary": "hyprtk-rec",
        "version_files": [_p("hyprtk-rec/hyprtk_rec/__init__.py")],
        "settings": [],
        "process": r"hyprtk-rec",
    },
    {
        "id": "config-manager", "name": "hyprtk-config-manager", "title": "Hyprland Settings",
        "binary": "config-manager",
        "version_files": [_p("hyprtk-config-manager/backend/config_manager/__init__.py")],
        "settings": ["config-manager", "open"],
        "process": r"config-manager|qs\b.*hyprtk-config-manager",
    },
    {
        "id": "usb", "name": "hyprtk-usb", "title": "USB Writer",
        "binary": "hyprtk-usb",
        "version_files": [_p("hyprtk-usb/hyprtk_usb/__init__.py")],
        "settings": [],
        "process": r"hyprtk-usb",
    },
    {
        "id": "iso", "name": "hyprtk-iso-creator", "title": "ISO Creator",
        "binary": "hyprtk-iso-creator",
        "version_files": [_p("hyprtk-iso-creator/hyprtk_iso_creator/__init__.py")],
        "settings": [],
        "process": r"hyprtk-iso-creator",
    },
]

_VERSION_RE = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.MULTILINE)


def version_from(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    match = _VERSION_RE.search(text)
    return match.group(1) if match else ""


def version(app: dict) -> str:
    for candidate in app.get("version_files") or []:
        found = version_from(candidate)
        if found:
            return found
    return ""


def running(app: dict) -> bool:
    pattern = app.get("process")
    if not pattern:
        return False
    result = util.run(["pgrep", "-af", pattern], timeout=4)
    if not result.ok:
        return False
    needles = [app.get("binary", ""), app.get("name", "")]
    for line in result.lines():
        if line.split(maxsplit=1)[0] == str(os.getpid()):
            continue
        if any(needle and needle in line for needle in needles):
            return True
    return False


def installed(app: dict) -> bool:
    return bool(version(app)) or util.which(app.get("binary", "")) is not None


def settings_argv(app: dict) -> list[str]:
    argv = list(app.get("settings") or [])
    if not argv:
        return []
    if util.which(argv[0]) is None:
        return []
    return argv


def describe(app: dict) -> dict:
    return {
        "id": app["id"],
        "name": app["name"],
        "title": app["title"],
        "binary": app["binary"],
        "version": version(app),
        "installed": installed(app),
        "running": running(app),
        "settings": settings_argv(app),
    }


def all_apps() -> list[dict]:
    return [describe(app) for app in APPS]
