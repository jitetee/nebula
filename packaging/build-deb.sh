#!/usr/bin/env bash
# Build a Termux-compatible .deb of Nebula.
#   bash packaging/build-deb.sh            → dist/nebula_<version>_all.deb
# Works in Termux (pkg install dpkg) and on any Debian/Ubuntu machine/CI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
PREFIX_REL="data/data/com.termux/files/usr"          # where Termux keeps its files
STAGE="$ROOT/dist/stage"; OUT="$ROOT/dist"
APP="$STAGE/$PREFIX_REL/opt/nebula"

rm -rf "$STAGE"; mkdir -p "$APP" "$STAGE/$PREFIX_REL/bin" "$STAGE/DEBIAN" "$OUT"

# 1. the app (never data/, git files, CI or packaging)
( cd "$ROOT" && tar --exclude=./data --exclude=./.git --exclude=./.github --exclude=./dist \
      --exclude=./packaging -cf - . ) | ( cd "$APP" && tar -xf - )
find "$APP" -type d -exec chmod 755 {} +
find "$APP" -type f -exec chmod 644 {} +
chmod 755 "$APP/bin/nebula" "$APP"/lib/*.sh "$APP"/install/*.sh "$APP/motd/init.sh" "$APP"/motd/motd.d/* 2>/dev/null || true
# (data/ is created by postinst, so dpkg never owns or re-permissions your data)
ln -s ../opt/nebula/bin/nebula "$STAGE/$PREFIX_REL/bin/nebula"

# 2. package metadata
SIZE=$(du -sk "$STAGE/$PREFIX_REL" | cut -f1)
cat > "$STAGE/DEBIAN/control" <<EOF
Package: nebula
Version: $VERSION
Architecture: all
Maintainer: ${NEBULA_MAINTAINER:-jitetee <jitetee@users.noreply.github.com>}
Installed-Size: $SIZE
Depends: bash, zsh, curl, tar, gawk, jq, ncurses-utils, coreutils, findutils, grep, sed
Recommends: tgpt, termux-api, openssl-tool
Homepage: https://github.com/jitetee/nebula
Section: utils
Priority: optional
Description: AI-powered terminal helper and shell UI for Termux
 Nebula adds an AI assistant with formatted answers, live crypto/news/sports
 dashboards, a one-command tool installer, a built-in fuzzy picker, a
 music player, a customizable prompt and home screen, and device-aware
 settings. After installing, run: nebula setup
EOF
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
set -e
APP="${PREFIX:-/data/data/com.termux/files/usr}/opt/nebula"
mkdir -p "$APP/data" 2>/dev/null || true
chmod 700 "$APP" "$APP/data" 2>/dev/null || true
if [ ! -f "$APP/data/.setup_done" ]; then
  echo ""
  echo "  ⚡ Nebula installed. Finish setup with:  nebula setup"
  echo ""
fi
exit 0
EOF
cat > "$STAGE/DEBIAN/postrm" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
# Your data (login, notes, backups) lives in opt/nebula/data and is never deleted by the package manager.
case "$1" in
  remove|purge)
    echo "  Nebula removed. Your data was kept in \$PREFIX/opt/nebula/data (delete it by hand to wipe everything)."
    echo "  Also remove the zsh hook:  nebula setup --undo   (run before uninstalling) or edit ~/.zshrc" ;;
esac
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/postrm"

# 3. build
DEB="$OUT/nebula_${VERSION}_all.deb"
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "$DEB" >/dev/null
echo "✔ Built $DEB ($(du -h "$DEB" | cut -f1))"
