#!/usr/bin/env bash
# Build a distro package for hyprtk-system-manager.
#
#   ./packaging/build.sh arch     real Arch package (makepkg, no root needed)
#   ./packaging/build.sh deb      real .deb (debian:bookworm container)
#   ./packaging/build.sh rpm      real .rpm (fedora container)
#   ./packaging/build.sh stage <image>
#                                 staged DESTDIR install inside an image
#                                 (how the Alpine and Void recipes are checked)
#
# Output goes to packaging/out/.
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=$(cd "$ROOT" && PYTHONPATH=backend python3 -c \
    'import system_manager; print(system_manager.__version__)')
NAME=hyprtk-system-manager
TARBALL="$NAME-$VERSION.tar.gz"
OUT="$ROOT/packaging/out"
WD=$(mktemp -d "${TMPDIR:-/tmp}/hyprtk-pkg.XXXXXX")
trap 'rm -rf "$WD"' EXIT

mkdir -p "$OUT"
git -C "$ROOT" archive --format=tar.gz --prefix="$NAME-$VERSION/" \
    -o "$WD/$TARBALL" HEAD

shim() {
    # install.sh checks for quickshell at install time; a container only needs
    # the payload written, so a no-op qs on PATH is enough.
    cat > /usr/local/bin/qs <<'INNER'
#!/bin/sh
exit 0
INNER
    chmod +x /usr/local/bin/qs
}

case "${1:-arch}" in
    arch)
        cp "$ROOT/packaging/PKGBUILD" "$WD/PKGBUILD"
        ( cd "$WD" && SRCDEST="$WD" makepkg -f --noconfirm >/dev/null )
        cp "$WD"/*.pkg.tar.* "$OUT/"
        echo "built: $(ls "$OUT"/*.pkg.tar.* | tail -1)"
        ;;
    deb)
        ( cd "$WD" && tar xzf "$TARBALL" )
        cp -a "$ROOT/packaging/debian" "$WD/$NAME-$VERSION/debian"
        podman run --rm -v "$WD/$NAME-$VERSION:/src:Z" -w /src debian:bookworm \
            bash -euc '
                apt-get update -qq >/dev/null
                apt-get install -y -qq debhelper dpkg-dev python3 >/dev/null
                chmod +x install.sh packaging/build.sh 2>/dev/null || true
                printf "#!/bin/sh\nexit 0\n" > /usr/local/bin/qs
                chmod +x /usr/local/bin/qs
                dpkg-buildpackage -b -us -uc >/tmp/build.log 2>&1 || { tail -40 /tmp/build.log; exit 1; }
                cp ../*.deb /src/
            '
        cp "$WD/$NAME-$VERSION"/*.deb "$OUT/"
        echo "built: $(ls "$OUT"/*.deb | tail -1)"
        ;;
    rpm)
        SPEC="$WD/$NAME.spec"
        cp "$ROOT/packaging/$NAME.spec" "$SPEC"
        podman run --rm -v "$WD:/w:Z" -w /w fedora:latest \
            bash -euc '
                dnf install -y -q rpm-build python3 tar >/dev/null
                rpmbuild -ba --define "_srcdir /w" --define "_topdir /w/rpmbuild" \
                    --define "debug_package %{nil}" \
                    --define "_sourcedir /w" /w/'"$NAME"'.spec >/tmp/rpm.log 2>&1 \
                    || { tail -40 /tmp/rpm.log; exit 1; }
            '
        cp "$WD"/rpmbuild/RPMS/noarch/*.rpm "$OUT/" 2>/dev/null || \
            cp "$WD"/rpmbuild/RPMS/*/*.rpm "$OUT/"
        echo "built: $(ls "$OUT"/*.rpm | tail -1)"
        ;;
    stage)
        IMAGE="${2:?usage: build.sh stage <image>}"
        ( cd "$WD" && tar xzf "$TARBALL" )
        podman run --rm -v "$WD/$NAME-$VERSION:/src:Z" -w /src "$IMAGE" \
            bash -euc '
                if ! command -v python3 >/dev/null; then
                    case "'"$IMAGE"'" in
                        *alpine*) apk add --no-cache python3 >/dev/null ;;
                        *void*)
                            echo repository=https://repo-default.voidlinux.org/current \
                                > /etc/xbps.d/00-repository-main.conf
                            xbps-install -Suy xbps >/dev/null
                            xbps-install -y python3 >/dev/null ;;
                        *debian*|*ubuntu*)
                            apt-get update -qq >/dev/null
                            apt-get install -y -qq python3 >/dev/null ;;
                        *fedora*|*opensuse*|*tumbleweed*)
                            dnf install -y -q python3 >/dev/null ;;
                        *arch*) pacman -Sy --noconfirm python >/dev/null ;;
                    esac
                fi
                printf "#!/bin/sh\nexit 0\n" > /usr/local/bin/qs
                chmod +x /usr/local/bin/qs
                mkdir -p /tmp/root
                DESTDIR=/tmp/root ./install.sh --system --prefix /usr
                test -f /tmp/root/usr/share/'"$NAME"'/backend/system_manager/cli.py
                test -x /tmp/root/usr/libexec/hyprtk-sm-helper
                test -f /tmp/root/usr/share/polkit-1/actions/org.hyprtk.system-manager.policy
                echo "staged install OK on '"$IMAGE"'"
            '
        ;;
    *)
        echo "usage: build.sh {arch|deb|rpm|stage <image>}" >&2
        exit 2
        ;;
esac
