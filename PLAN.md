# PLAN — hyprtk-system-manager

A single, searchable settings application for the whole Hyprland desktop and the
hyprtk suite. One window, one page stack, one apply model, honest capability
reporting.

Binary: **`hyprtk-settings`** · Desktop id: **`hyprtk-system-manager`** ·
Version: **0.1.0** (scaffold)

---

## 1. Product shape

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ▣ System Settings   dozer-hyprtk                    [ Ctrl+K  Search… ]     │
├──────────────────┬───────────────────────────────────────────────────────────┤
│ SYSTEM           │  ▣  Displays                          [ functional ]     │
│  About           │  Arrange, enable and scale your monitors.                 │
│  Date & Time     │                                                           │
│  Region          │  ┌─ DP-1 ──────────────────────────────────────────────┐  │
│  Users           │  │  Samsung C49J89x · 3840×1080 @ 59.97 Hz · 1.00×      │  │
│  Services        │  │  Resolution [ 3840×1080 @ 59.97 ▾ ]  Scale [ 1.00 ▾ ]│  │
│  Updates         │  │  Rotation   [ Normal ▾ ]            Position [ 0×0 ] │  │
│ HARDWARE         │  └──────────────────────────────────────────────────────┘  │
│  Displays        │                                                           │
│  Graphics        │                                                           │
│  Sound           │                                                           │
│  Input            │                                                          │
│  Power            │                                                          │
│ …                 │                                                          │
├──────────────────┴───────────────────────────────────────────────────────────┤
│ 2 pending changes · writes to ~/.config/hyprtk-bar-qt/config.json            │
│                                  [ Revert ]  [ Apply ]  [ Close ]            │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Sidebar:** grouped navigation (8 groups), search field, live hostname,
  version footer. Collapsible to icons via a future preference.
- **Page:** header (icon, title, description, capability pill) + scrollable
  sections of cards + footer actions.
- **Footer:** pending-change count, target file, Revert, Apply, Close.
- **Search:** filters groups/panels; Ctrl+K focuses; Enter opens the top match.
- **Overlay mode:** `--overlay` opens as a layer-shell panel over the bar, the
  same pattern config-manager uses, so the bar's Settings can hand off.

---

## 2. Architecture

```
                ┌──────────────────────────────────────────────┐
  qs -p .       │  shell.qml → MainWindow.qml                  │
  (Quickshell)  │    └ App.qml                                 │
                │        ├ Sidebar.qml        (catalog+search) │
                │        ├ pages/FormPage.qml (generic renderer)│
                │        ├ pages/AboutPage.qml                 │
                │        ├ pages/DisplaysPage.qml              │
                │        ├ pages/UsersPage.qml                 │
                │        ├ pages/AppearancePage.qml            │
                │        └ pages/SuitePage.qml                 │
                └───────────────┬──────────────────────────────┘
                                │ JSON-lines over stdio
                ┌───────────────▼──────────────────────────────┐
                │  python3 -m system_manager.cli serve          │
                │   rpc.py  ── hello/catalog/panel/apply/action │
                │   catalog.py ── panel registry + metadata      │
                │   form.py  ── form model builders              │
                │   panels/*  ── probe() + apply() + actions()   │
                │   util.py  ── subprocess, files, facts         │
                │   priv.py  ── root → sudo -n → pkexec          │
                │   state.py ── backups, journal, restore        │
                └──────────────────────────────────────────────┘
```

### Why Quickshell + a Python backend

- The bar, file manager and config-manager already use this pair, with the same
  theme tokens, launcher conventions, installer shape and `QS_APP_ID` rule.
- QML gives the pywal-driven frosted look with zero extra dependencies; Python
  does the subprocess/file work where it is testable without a display.
- One long-lived backend process owns capability probes and backups; the QML
  side stays declarative.

### Why a form model and a generic renderer

KDE solves the panel explosion with self-describing modules. We solve it the
same way but simpler: a panel returns JSON rows, `FormPage.qml` renders them.
That means:

- adding a panel = one Python module (`probe` + `apply`) + one catalog entry;
- the eight row types cover ~90 % of settings UIs;
- bespoke QML is reserved for genuinely spatial content (monitors, users,
  colour swatches, the suite app grid).

Row types: `info`, `toggle`, `choice`, `text`, `number`, `slider`, `color`,
`path`, `action`, `list`, `kv`, `note`.

---

## 3. Panel catalog

`status` is what the app can honestly do today, shown as a pill:

| Status | Meaning |
|---|---|
| `full` | probe + apply, persistent, verified |
| `live` | probe + apply, applies to the running session only |
| `partial` | probe + the safe subset of actions; the rest is labelled |
| `read` | probe/diagnostics only |
| `link` | delegates to another app (config-manager) |
| `planned` | registered, shows the roadmap, no writes |

### System

| Panel | Status | What it does |
|---|---|---|
| About | `read` | OS, kernel, Hyprland, CPU/GPU/RAM/disk, session, suite versions; copy report |
| Date & Time | `full` | Timezone, NTP, local RTC, live clock; `timedatectl` via pkexec |
| Region & Language | `partial` | Locale/language/keymap read; set locale needs `locale-gen` |
| Users & Groups | `full` | List, create, delete, lock, password, groups, shell |
| Services | `partial` | List/enable/disable/start/stop a curated systemd set |
| Updates | `partial` | Pending package count (`checkupdates`), last upgrade, refresh |

### Hardware

| Panel | Status | What it does |
|---|---|---|
| Displays | `full` | Enable/mode/scale/rotation/position, live + managed block in `monitors.lua` |
| Graphics | `read` | GPU, driver, DRM nodes, Vulkan/VA-API presence |
| Sound | `partial` | Default sink/source, volume, mute (`wpctl`) |
| Input Devices | `live` | Keyboard layout, repeat, mouse sensitivity, touchpad toggles |
| Power | `read` | Battery/AC, idle inhibit, `hypridle` state; profile tooling absent |
| Bluetooth | `partial` | Adapter state, paired devices, power/rescan |
| Printers | `read` | CUPS queues when CUPS exists |
| Storage | `partial` | Block devices, usage, mount/unmount via `udisksctl` |

### Network

| Panel | Status | What it does |
|---|---|---|
| Network | `partial` | NM devices, Wi-Fi networks, radio on/off, rescan, connect |

### Personalisation

| Panel | Status | What it does |
|---|---|---|
| Appearance | `full` | Theme source, background/foreground/accent, opacity, border, wallpaper, icons, cursor, GTK |
| Fonts | `full` | Families, default UI/mono font, size, install a font file |
| Notifications | `partial` | Bar notification timeout/history; DND via the bar |

### Desktop

| Panel | Status | What it does |
|---|---|---|
| Hyprland | `link` | Opens config-manager (gaps, blur, animations, binds, rules) |
| Keyboard Shortcuts | `read` | Parsed `hl.bind` table, grouped; edit in config-manager |
| Autostart | `full` | List `~/.config/autostart`, enable/disable, open entry |

### Applications

| Panel | Status | What it does |
|---|---|---|
| Default Applications | `partial` | MIME defaults by category, set with `xdg-mime` |
| hyprtk Suite | `full` | Every suite app: version, running, open settings, inline bar keys |

### Privacy & Security

| Panel | Status | What it does |
|---|---|---|
| Privacy & Security | `partial` | Firewall, screen lock, session lock, permissions summary |

### Accessibility

| Panel | Status | What it does |
|---|---|---|
| Accessibility | `partial` | GTK a11y flags, cursor size, keyboard repeat, large text |

25 panels registered. Full implementations in v0.1: **About, Date & Time,
Users & Groups, Displays, Appearance, Fonts, Autostart, Suite**. The rest are
real probes with honestly limited writes.

---

## 4. Data model

### Page (served by `panel`)

```json
{
  "id": "datetime",
  "title": "Date & Time",
  "group": "system",
  "icon": "\uf017",
  "description": "Clock, time zone and automatic synchronisation.",
  "status": "full",
  "keywords": ["time", "timezone", "ntp", "clock"],
  "sections": [
    {"title": "Clock", "description": null, "rows": [
      {"type": "info", "label": "Local time", "value": "Mon 23 Nov 2026 16:16", "mono": true},
      {"type": "choice", "key": "timezone", "label": "Time zone",
       "value": "Europe/London", "choices": [{"value": "Europe/London", "label": "Europe/London"}]},
      {"type": "toggle", "key": "ntp", "label": "Set time automatically", "value": true}
    ]}
  ]
}
```

### Apply

```json
{"id": 7, "method": "apply", "params": {"id": "datetime", "changes": {"timezone": "Europe/Paris"}}}
→ {"id": 7, "result": {"ok": true, "message": "Time zone set to Europe/Paris",
                       "refresh": true, "requires": "root", "details": ["…"]}}
```

### Action

```json
{"id": 8, "method": "action", "params": {"id": "users", "action": "create",
   "args": {"username": "kori", "shell": "/usr/bin/zsh", "admin": true}}}
```

Actions are always explicit. Destructive ones carry `"danger": true` in the
form model so the UI confirms first.

---

## 5. Privilege model

```
euid == 0            → run directly
sudo -n true works   → sudo -n <cmd>       (cached / NOPASSWD)
otherwise            → pkexec <cmd>        (polkit agent prompts)
```

- No root daemon, no setuid helper.
- Every privileged call returns `requires: "root"` and the exact command in
  `details`, so the UI can show what will run.
- Mutations that need stdin (passwords) use `chpasswd` under `pkexec`.
- The app refuses to delete the current user or `root`, and requires the typed
  user name in the UI before an account is removed.

---

## 6. Backups and undo

- Before any file write, `state.py` snapshots the file into
  `~/.config/hyprtk-system-manager/backups/<stamp>/` with a JSON manifest.
- Multi-file applies are transactional: on error, every written file is
  restored from the snapshot.
- `hyprtk-settings backups list|restore <stamp>` recovers by hand.
- The footer's **Revert** discards *pending* changes only; it never touches disk.

---

## 7. Suite integration

| Surface | Integration |
|---|---|
| Bar | `hyprtk-settings` opens from a quick link / keybind; `--overlay` hands off from the bar's Settings; the Suite panel writes the same `config.json` keys as the bar's own Settings |
| config-manager | Hyprland panel links to it; Displays never edits `input.lua`/`decoration.lua` |
| File manager | Directory picker reuses the same backend `fs.list` shape |
| Terminal | "Open update in terminal" and root log commands launch `$TERMINAL` |
| Suite apps | Suite panel reads installed payload versions and running pids |
| Window | the standalone window is a layer-shell `PanelWindow` centred at 1180×800, like the bar's Settings; the compositor does not decorate layer surfaces, so the app's animated accent border is the only edge. Off-screen QA swaps in a `FloatingWindow` host because `PanelWindow` has no backend without Wayland |
| Installer | `install.sh` follows the config-manager shape; merged installer step added after release |
| Brand | `data/hyprtk-system-manager.svg`; add a `system-manager` glyph to the brand kit and regenerate v09 icons before the first public release |
| Keybind | `SUPER+I` → `hyprtk-settings` (planned) |
| Desktop entry | absolute `Icon=`, `Categories=Settings;System;`, `QS_APP_ID` exported |

---

## 8. Milestones

### M0 — scaffold (this cut)

- [x] Research + plan
- [x] Quickshell shell: floating window, grouped sidebar, search, page stack,
      footer apply model, overlay mode
- [x] Python backend: RPC, catalog, form model, 25 panel probes, privilege
      layer, backups, CLI
- [x] Full panels: About, Date & Time, Users, Displays, Appearance, Fonts,
      Autostart, Suite
- [x] Generic `FormPage` renderer for the other 17
- [x] Installer, launcher, desktop entry, icon, tests, QA script, boot check

### M1 — depth

- [ ] Network: connect flow with a password dialog, VPN page
- [x] Sound: input volume/mute + per-app streams (device profiles still open)
- [x] Users: groups and shell dialogs
- [x] Fonts: install picker
- [ ] Power: `powerprofilesctl`/`tlp` when present, lid/battery actions
- [ ] Displays: drag-to-arrange canvas, VRR/HDR/bit-depth, profiles
- [x] Search: row-level index + recents (suggested settings still open)
- [x] Non-blocking RPC: panel probes run on a thread pool so a slow Updates
      probe cannot freeze the UI

### M2 — breadth

- [ ] Accessibility panel: Orca, on-screen keyboard, sticky keys, zoom
- [ ] Printers: add/remove queue
- [ ] Storage: format/mount policies, fstab editor with validation
- [ ] Region: full locale generation, input methods
- [ ] Privacy: firewall rules, per-app permissions

### M3 — suite

- [ ] Replace config-manager's standalone launch with a System Settings
      "Hyprland" host that embeds its pages
- [ ] Suite panel writes bar-qt settings inline (all 10 bar pages)
- [ ] Shared settings bus (`org.hyprtk.Settings`) so apps deep-link to a row

### M4 — hardening

- [ ] Root helper with a polkit policy + action ids
- [ ] Apply dry-run preview (diff) for every file write
- [ ] Session restore, per-host profiles
- [ ] Packaging for Arch/Fedora/Debian/openSUSE/Void/Alpine + ISO inclusion

---

## 9. Testing strategy

- **Unit**: form builders, parsers (monitors, timedatectl, passwd, wpctl,
  nmcli, lsblk, lspci), JSON merge, backup/restore, privilege selection.
- **Panel contract**: every catalog entry resolves, every `probe()` returns a
  valid page even with every tool missing (monkeypatched `which`/`run`).
- **RPC**: request/response, unknown method, exception isolation.
- **QML**: `qmllint` on every file + a headless Quickshell boot check
  (`QT_QPA_PLATFORM=offscreen qs -p .`) that loads the shell, completes
  `hello`, opens one panel of each page kind, and exits with a status.
- **Installer round-trip** in a temp `HOME`, plus `HYPRTK_DRYRUN=1`.
- **No test may depend on host hardware.** Probes are tested with fixtures.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Writing someone else's config (Hyprland Lua) | Never: Displays writes a marked managed block; everything else links to config-manager |
| Privilege prompts in a GUI | pkexec with a running polkit agent; every action reports the command; no silent sudo |
| Partial panels looking complete | status pill per panel, derived from capability probes |
| Quickshell window tiling/misplacement | detached `place` helper via `hyprctl clients`, opaque panel, `QS_APP_ID`; suite window rule |
| Backend crash taking the UI down | one process per window, RPC error isolation, `onExited` status row |
| Package drift across distros | capability probes, never assume a binary exists |
| Two apps writing bar config | one JSON deep-merge contract; last writer wins; backups |
| Security: password handling | `chpasswd` stdin, never argv, never logged |
