# Research — building a Linux system settings application

Scope: what GNOME Settings, KDE System Settings and XFCE Settings Manager do,
what is worth copying, what to reject, and what the hyprtk desktop can actually
control on this stack (Hyprland 0.57 Lua config, Quickshell, pywal16, systemd,
NetworkManager, PipeWire, GTK/Qt).

Status of the reference panel sets checked against GNOME 49, KDE Plasma 6.4 and
XFCE 4.20 (2026).

---

## 1. The three reference apps

### GNOME Settings

**Shape.** One window, a fixed sidebar of ~28 panels, a single page per panel,
no Apply button (changes commit immediately), and a prominent search field at
the top. Panels are flat: no sub-pages, no tabs. Deep configuration is pushed
out to `gsettings`, Tweaks or dconf-editor.

**Strengths**

- Search is first-class and searches *settings*, not just panel names.
- Every change is immediate and reversible while the page is open; no modal
  save step to forget.
- Consistent row language: title, optional subtitle, control on the right.
- Empty/disabled states explain *why* ("No Wi-Fi adapter found").

**Weaknesses**

- Panel list is long and unstructured; no grouping beyond order.
- Power-user settings are deliberately absent.
- No notion of profiles, per-device settings, or "apply to all".

### KDE System Settings

**Shape.** A launcher window with category tiles, and then either an in-window
tree (sidebar) or a separate window per module. Modules are plugins (KCMs) with
their own icons, search metadata and config schemas (KConfigXT). Search is
global and indexes every option via the KCM's `Keywords`.

**Strengths**

- The plugin contract is the important idea: a panel is a self-describing
  module with metadata, a form model and a config backend.
- Global search is excellent because metadata is declared, not scraped.
- Per-module "Defaults" and "Reset" are universally available.
- Handles privileged operations through polkit helpers, not a root GUI.

**Weaknesses**

- Separate windows fragment the workflow; state/apply is inconsistent between
  modules.
- Enormous surface area; many modules are effectively unmaintained.
- Visual language is denser and less consistent than GNOME's.

### XFCE Settings Manager

**Shape.** A grid of category tiles in one window; each tile opens a separate
dialog. Modules are small, single-purpose and often ancient (gtk2-era layouts).

**Strengths**

- Very fast to open and navigate for a known target.
- Small modules are easy to reason about and replace.
- Tiles communicate "this is a toolbox" better than a long list.

**Weaknesses**

- Inconsistent dialogs, no global search, no shared design language.
- No apply model; each dialog invents its own.

---

## 2. What we adopt, adapt and reject

| Idea | Source | Decision |
|---|---|---|
| Sidebar with grouped categories | GNOME + KDE | **Adopt.** Groups: System, Hardware, Network, Personalisation, Desktop, Applications, Privacy, Accessibility. |
| Row language (title / subtitle / control right) | GNOME | **Adopt** as the single form primitive. |
| Declared panel metadata + keywords | KDE KCM | **Adopt.** Every panel declares id, title, group, icon, keywords, status. Powers search. |
| Self-describing form model rendered by one page | KDE KConfigXT | **Adopt, simplified.** Panels return a JSON form model; one `FormPage.qml` renders it. Bespoke QML only where the content is genuinely spatial (monitors, users, appearance). |
| Search across settings, not panels | GNOME/KDE | **Adopt** (v0.1: catalog + declared keywords; v0.2: row index). |
| Immediate apply vs explicit Apply | GNOME vs KDE | **Hybrid.** Safe cosmetic changes stage and apply on **Apply** (Ctrl+S) so a half-typed colour is not written; destructive actions confirm and run immediately. A "pending changes" footer is always visible. |
| Separate window per module | KDE/XFCE | **Reject.** One window, one page stack, one apply model. |
| Category tile grid as the *only* navigation | XFCE | **Reject as primary**, keep as an optional "All settings" view later. |
| Reset to defaults | KDE | **Adopt** per panel (`Reset` clears pending state; `Defaults` action where the panel knows its defaults). |
| polkit helper for root work | KDE | **Adopt.** `pkexec` → one-shot commands; no long-running root daemon. |
| Status/health banner | none | **Add.** Each panel declares `full`, `live`, `read`, `partial`, `link` or `planned`, shown as a pill, so the app never pretends to support something it does not. |

---

## 3. What this machine can actually control

Probed on the target system (Arch, Hyprland 0.57.2 with the Lua config):

| Domain | Source of truth | Tool | Writable |
|---|---|---|---|
| Hostname / OS / kernel | `/etc/hostname`, `/etc/os-release`, `uname` | `hostnamectl` | hostname yes (polkit) |
| Date, time, timezone, NTP | `timedatectl` | `timedatectl` | yes (polkit) |
| Locale / language | `/etc/locale.conf`, `localectl` | `localectl` | yes (polkit, needs locale-gen) |
| Users, groups, shells | `/etc/passwd`, `/etc/group`, `/etc/shells` | `useradd`, `usermod`, `gpasswd`, `chpasswd` | yes (polkit) |
| Displays | `hyprctl monitors -j`, `hypr/monitors.lua` | `hyprctl keyword monitor` | live + managed block |
| GPU | `lspci`, `/sys/class/drm` | read-only | no |
| Audio | PipeWire / WirePlumber | `wpctl`, `pactl` | yes (user session) |
| Input devices | `hyprctl devices -j`, `input.lua` | `hyprctl keyword input:*` | live |
| Power / battery | `/sys/class/power_supply` | read-only here (no battery) | no |
| Bluetooth | BlueZ | `bluetoothctl` | yes (user in `bluetooth` group) |
| Network | NetworkManager | `nmcli` | yes (user in `network` group / polkit) |
| Printers | CUPS | `lpstat` | not installed |
| Storage | udev / udisks2 | `lsblk`, `udisksctl` | mount/unmount yes |
| Services | systemd | `systemctl` | yes (polkit) |
| Updates | pacman + `checkupdates` | `checkupdates`, `paccache` | yes (polkit, terminal) |
| Fonts | fontconfig | `fc-list`, `fc-match`, `fc-cache` | copy to `~/.local/share/fonts` |
| Icons / cursors / GTK | `gtk-3.0/settings.ini`, `~/.icons`, `/usr/share/icons` | files | yes (user) |
| Wallpaper / palette | awww + pywal16 | `awww img`, `wal` | yes (user) |
| Hyprland config | `~/.config/hypr/*.lua` | `hyprctl`, `config-manager` | delegate to config-manager |
| Bar / suite apps | `~/.config/hyprtk-bar-qt/config.json` | JSON patch | yes (user) |
| Autostart | `~/.config/autostart/*.desktop` | files | yes (user) |
| Default apps / MIME | `xdg-mime`, `xdg-settings` | `xdg-mime` | yes (user) |
| Firewall | nftables/ufw | read-only unless configured | read |
| Accessibility | GTK `gsettings`, Hyprland input | `gsettings` | partial |

Notable gaps that shaped the plan:

- `powerprofilesctl` and `ddcutil` are **not installed**, so power and external
  brightness control start read-only.
- `xrandr`/`wlr-randr` are absent: Hyprland is the only display backend.
- `xdg-settings` has **no** `default-terminal-emulator` target on Arch; default
  apps must be set through `xdg-mime` per MIME type plus the suite's own
  `$TERMINAL` contract.
- Hyprland 0.57.2 accepts **Lua dispatchers only** (`hl.dsp.*`), which matters
  for every action this app triggers.
- The Hyprland config is Lua and owned by `config-manager`; writing it from two
  apps would be a correctness bug. The Hyprland panel links out, and Displays
  writes only a clearly marked managed block.

---

## 4. UX principles for this app

1. **One window, one page, one apply model.** Sidebar for navigation, page stack
   for content, footer for pending changes and Apply/Revert.
2. **Say what will happen.** Every writable row names its target
   (`~/.config/hyprtk-bar-qt/config.json`, `timedatectl`, …) in helper text.
3. **Distinguish session changes from persistent ones.** A `live` change says
   "until next login" and offers the persistent path.
4. **Never lie about support.** A panel's status pill is derived from real
   capability probes, not from ambition.
5. **Privilege is visible.** Root actions show an unlock affordance, the exact
   command, and whether the system will prompt. No silent `sudo`.
6. **Search is navigation.** Typing filters groups and panels by title, keyword
   and description; Enter opens the first match.
7. **Destructive actions confirm in place** (inline confirm row, not a modal
   dialog) and require typing the user name for account deletion.
8. **The suite is a first-class citizen.** The Apps group exposes every hyprtk
   app with version, running state and a link to its own settings surface.
9. **Dark, frosted, pywal-driven.** Reuse the bar's exact theme resolution so
   the app follows the wallpaper like every other suite window.
10. **Keyboard complete.** Ctrl+K search, Ctrl+S apply, Ctrl+Z revert, arrow
    navigation in the sidebar, Enter to activate, Escape to close.

---

## 5. Technical constraints discovered

- **Quickshell 0.3.2** is the suite's UI runtime. A `FloatingWindow` is a normal
  toplevel and inherits Hyprland's border, rounding and drop shadow, which
  produced a double border around the app's own rounded border. The standalone
  window is therefore a layer-shell `PanelWindow` (no anchors, so
  wlr-layer-shell centres it) — layer surfaces are not decorated — and
  off-screen QA swaps in a `FloatingWindow` host because `PanelWindow` has no
  backend without Wayland.
- **Quickshell does not receive HTML colours in `property color`**; convert with
  `Qt.rgba()`/`Qt.color()`.
- **A `Process` with `stdinEnabled` and `SplitParser`** is the proven way to run
  a Python backend (config-manager, file manager). One JSON object per line.
- **`QS_APP_ID` must be exported** or every toplevel reports `org.quickshell`
  and loses its desktop entry, icon and window rules.
- **`pkexec` strips the environment.** Root helpers must be self-contained
  commands (or an absolute-path launcher), never "python3 -m" with a
  `PYTHONPATH` only the parent had.
- **Quickshell has no native file dialog.** A directory/file picker is a QML
  popup backed by a backend `fs.list` method (the file manager does the same).
- **`TextInput.text` bindings die on the first keystroke**; every editable field
  needs the reverse sync (`onTextChanged` → local property) and must commit on
  `onAccepted` and on focus loss.
- **`ListModel` for interactive lists**, never a JS array reassigned on click.

---

## 6. Competitive summary

The winning shape for a desktop-agnostic settings app in 2026 is GNOME's
single-window, searchable, consistent-row interface with KDE's declared-module
metadata and polkit privilege model, and none of the separate-window taxonomy.
That is what this application implements, specialised for a Hyprland + Quickshell
+ pywal desktop and extended with a first-class view of the hyprtk suite's own
applications.
