#!/usr/bin/env bash
# Turn dist/*.deb into a static APT repository you can host on GitHub Pages.
#   bash packaging/make-repo.sh [outdir]      default: dist/repo
# Needs: dpkg-scanpackages (package dpkg-dev; in Termux: pkg install dpkg-dev), gzip, optional gpg.
#   GPG_KEY=<key id>  → also signs the repository (InRelease + Release.gpg)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${1:-$ROOT/dist/repo}"
SUITE=stable; COMP=main
ARCHES="aarch64 arm i686 x86_64"            # Termux architectures; an "all" package is listed in each

rm -rf "$REPO"; mkdir -p "$REPO/pool/$COMP"
cp "$ROOT"/dist/*.deb "$REPO/pool/$COMP/"
for a in $ARCHES; do
  d="$REPO/dists/$SUITE/$COMP/binary-$a"; mkdir -p "$d"
  ( cd "$REPO" && dpkg-scanpackages --multiversion "pool/$COMP" /dev/null 2>/dev/null ) > "$d/Packages"
  gzip -9kf "$d/Packages"
done
{
  echo "Origin: Nebula"; echo "Label: Nebula"; echo "Suite: $SUITE"; echo "Codename: $SUITE"
  echo "Architectures: $ARCHES all"; echo "Components: $COMP"; echo "Description: Nebula for Termux"
  echo "Date: $(date -Ru)"; echo "MD5Sum:"
  ( cd "$REPO/dists/$SUITE" && find "$COMP" -type f | while read -r f; do printf ' %s %s %s\n' "$(md5sum "$f" | cut -d' ' -f1)" "$(stat -c %s "$f")" "$f"; done )
  echo "SHA256:"
  ( cd "$REPO/dists/$SUITE" && find "$COMP" -type f | while read -r f; do printf ' %s %s %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "$(stat -c %s "$f")" "$f"; done )
} > "$REPO/dists/$SUITE/Release"
if [[ -n ${GPG_KEY:-} ]]; then
  gpg --batch --yes --default-key "$GPG_KEY" -abs -o "$REPO/dists/$SUITE/Release.gpg" "$REPO/dists/$SUITE/Release"
  gpg --batch --yes --default-key "$GPG_KEY" --clearsign -o "$REPO/dists/$SUITE/InRelease" "$REPO/dists/$SUITE/Release"
  gpg --export "$GPG_KEY" > "$REPO/nebula.gpg"
  echo "✔ Signed with $GPG_KEY (public key: nebula.gpg)"
fi
touch "$REPO/.nojekyll"
echo "✔ Repository ready in $REPO"
