#!/data/data/com.termux/files/usr/bin/bash
# Adds the Nebula APT repository to Termux, so you can:   pkg install nebula
#   curl -fsSL https://raw.githubusercontent.com/jitetee/nebula/main/install/add-repo.sh | bash
set -e
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
URL="${NEBULA_REPO_URL:-https://jitetee.github.io/nebula}"
LIST="$PREFIX/etc/apt/sources.list.d/nebula.list"
mkdir -p "$PREFIX/etc/apt/sources.list.d" "$PREFIX/etc/apt/trusted.gpg.d"

if curl -fsSL "$URL/nebula.gpg" -o "$PREFIX/etc/apt/trusted.gpg.d/nebula.gpg" 2>/dev/null && [ -s "$PREFIX/etc/apt/trusted.gpg.d/nebula.gpg" ]; then
  echo "deb $URL stable main" > "$LIST"; echo "✔ Added signed repository"
else
  rm -f "$PREFIX/etc/apt/trusted.gpg.d/nebula.gpg"
  echo "deb [trusted=yes] $URL stable main" > "$LIST"; echo "✔ Added repository (unsigned)"
fi
pkg update -y
echo ""
echo "  Now run:   pkg install nebula  &&  nebula setup"
