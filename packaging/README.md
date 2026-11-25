# Packaging

Every recipe installs through the same path the ISO uses:

```sh
DESTDIR=<staging> ./install.sh --system --prefix /usr
```

That puts the payload in `/usr/share/hyprtk-system-manager`, the launcher in
`/usr/bin/hyprtk-settings`, the desktop entry in
`/usr/share/applications`, the root helper in `/usr/libexec/hyprtk-sm-helper`
and the polkit policy in `/usr/share/polkit-1/actions`. Launchers inside the
package always point at the final prefix, never at the staging directory.

| Family | File | Build |
|---|---|---|
| Arch | `PKGBUILD` | `makepkg -si` |
| Fedora / openSUSE | `hyprtk-system-manager.spec` | `rpmbuild -ba` |
| Debian / Ubuntu | `debian/` | `dpkg-buildpackage -b -us -uc` |
| Alpine | `APKBUILD` | `abuild -r` |
| Void | `xbps/template` | `xbps-src pkg hyprtk-system-manager` |

Runtime dependencies are deliberately soft: the app probes for every tool and
says what is missing, so a minimal install still opens. Recommended extras are
`quickshell` (required), `polkit` (privileged edits), `udisks2`, `ufw` or
`nftables`, `power-profiles-daemon`, `flatpak`, `cups`, `networkmanager`.
