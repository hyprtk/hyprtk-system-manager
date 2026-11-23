#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

echo "== unit tests =="
PYTHONPATH=backend python3 -m unittest discover -s tests

echo "== python syntax =="
python3 -m compileall -q backend tests scripts

echo "== qml type check =="
QMLLINT=""
for candidate in /usr/lib/qt6/bin/qmllint qmllint; do
    if command -v "$candidate" >/dev/null 2>&1; then QMLLINT="$candidate"; break; fi
done
if [ -n "$QMLLINT" ]; then
    if "$QMLLINT" shell.qml >/tmp/sm-qmllint.log 2>&1; then :; fi
    # Quickshell ships its QML types inside the qs binary, so the linter cannot
    # resolve them. Fail only on real language errors, not import noise.
    if grep -E '(^|: )(error|Error):' /tmp/sm-qmllint.log \
        | grep -vE 'Failed to import|is not a type|not found' | grep -q .; then
        cat /tmp/sm-qmllint.log
        echo "qmllint reported errors" >&2
        exit 1
    fi
    echo "qmllint: no language errors"
else
    echo "qmllint not installed — skipped"
fi

echo "== shell syntax =="
bash -n install.sh
sh -n bin/hyprtk-settings

echo "== headless boot =="
timeout 180 python3 scripts/bootcheck.py

echo "== cli =="
PYTHONPATH=backend python3 -m system_manager.cli version | grep -q '^hyprtk-system-manager '
PYTHONPATH=backend python3 -m system_manager.cli panels >/dev/null
PYTHONPATH=backend timeout 240 python3 -m system_manager.cli doctor | tail -3 | grep -q 'suite apps'

echo "== installer round-trip =="
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
HOME="$TMP" XDG_DATA_HOME="$TMP/.local/share" ./install.sh >/dev/null
test -x "$TMP/.local/bin/hyprtk-settings"
test -f "$TMP/.local/share/applications/hyprtk-system-manager.desktop"
test -f "$TMP/.local/share/hyprtk-system-manager/hyprtk-system-manager.svg"
grep -q "Exec=\"$TMP/.local/bin/hyprtk-settings\" open" \
    "$TMP/.local/share/applications/hyprtk-system-manager.desktop"
HOME="$TMP" XDG_DATA_HOME="$TMP/.local/share" \
    "$TMP/.local/share/hyprtk-system-manager/bin/hyprtk-settings" version >/dev/null
HYPRTK_DRYRUN=1 ./install.sh --system | grep -q 'would install'
HOME="$TMP" XDG_DATA_HOME="$TMP/.local/share" ./install.sh --uninstall >/dev/null
test ! -e "$TMP/.local/share/hyprtk-system-manager"

echo "QA PASS"
