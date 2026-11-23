# Changelog

All notable changes to hyprtk-system-manager are recorded here. The format is
loosely [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions are
independent of the suite tag that carries them.

## [0.1.0] — 2026-11-23

First scaffold: the whole application shape plus eight functional panels.

### Added

- **Quickshell shell**: one window, grouped sidebar with eight categories,
  debounced global search, page header with a capability pill, pending-change
  footer with Apply/Revert, animated accent border, `--overlay` layer-shell mode.
- **Python backend**: JSON-lines RPC (`hello`, `catalog`, `panel`, `apply`,
  `action`, `search`, `fs.list`, `ui.get/set`, `status`), lazy panel registry,
  form-model builders and validation, capability probes, transactional file
  snapshots, `sudo -n`/`pkexec` privilege layer.
- **25 registered panels**, each with real probes:
  - System: About, Date & Time, Region & Language, Users & Groups, Services,
    Updates
  - Hardware: Displays, Graphics, Sound, Input Devices, Power, Bluetooth,
    Printers, Storage
  - Network: Network
  - Personalisation: Appearance, Fonts, Notifications
  - Desktop: Hyprland, Keyboard Shortcuts, Autostart
  - Applications: Default Applications, hyprtk Suite
  - Security: Privacy & Security
  - Accessibility: Accessibility
- **Fully functional panels**:
  - **About** — OS, kernel, CPU/GPU/RAM/disk, compositor, suite versions and a
    copyable diagnostic report.
  - **Date & Time** — timezone list, NTP, local RTC, sync status; writes through
    `timedatectl` under pkexec.
  - **Users & Groups** — account list with badges, create (home, shell, groups,
    admin, password), lock/unlock, delete with typed confirmation, password
    change via `chpasswd` stdin.
  - **Displays** — per-monitor enable/mode/scale/rotation/position, live
    `hyprctl keyword monitor`, and a persistent managed block in `monitors.lua`
    that never touches the rest of the file.
  - **Appearance** — colour source, background/foreground/accent, panel opacity,
    border width/animation, wallpaper through awww + pywal, icon/cursor/GTK
    themes.
  - **Fonts** — interface family and size, monospace resolution, family
    inventory, cache refresh and font installation.
  - **Autostart** — XDG desktop entries, user overrides for system entries,
    enable/disable and open-in-editor.
  - **hyprtk Suite** — version/running state for ten suite apps, settings and
    launch actions, plus inline bar opacity/border/font/animation keys.
- **Generic form renderer** with twelve row types (`info`, `toggle`, `choice`,
  `text`, `number`, `slider`, `color`, `path`, `action`, `list`, `kv`, `note`),
  a custom dropdown/slider/stepper/colour/path control set, inline file picker,
  confirmation and password modals, and a toast.
- **Suite theme**: the bar's exact pywal/config resolution, extended with a
  surface ladder, status colours and a type scale.
- **Tooling**: `hyprtk-settings` launcher, user and `--system` installers,
  desktop entry, v09-style icon, `doctor`, backups CLI, 62 unit tests, QML lint
  pass, off-screen boot check for one page of each kind, installer round-trip,
  and a deterministic off-screen screenshot tool.

### Notes

- The Hyprland configuration stays owned by config-manager; the Hyprland panel
  links to it and Displays writes only its managed block.
- Panels that depend on absent tooling report `Unavailable` instead of failing.
- Known gaps and the roadmap are in [PLAN.md](PLAN.md): network join flow,
  per-app volume, power profiles, accessibility breadth, printer queues, and
  full row-level search.
