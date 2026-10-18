#!/data/data/com.termux/files/usr/bin/env bash
# Nebula uninstaller — SAFE / NON-DESTRUCTIVE
#
# Removes:
#   • Nebula app dir ($PREFIX/opt/nebula) — but KEEPS its data/ folder
#     (login, notes, todo) unless you pass --purge-config
#   • the `nebula` command in $PREFIX/bin
#   • the Nebula block in ~/.zshrc
#   • restores ~/.termux font/colors/extra-keys from *.nebula-backup
#
# Never removes installed packages (zsh, git, tgpt, …) — other things may use them.
set -u

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
INSTALL_DIR="${NEBULA_INSTALL_DIR:-$PREFIX/opt/nebula}"
DATA_DIR="$INSTALL_DIR/data"
BIN_LINK="$PREFIX/bin/nebula"
TERMUX_DIR="${TERMUX_DIR:-$HOME/.termux}"

say()  { printf "\033[38;5;120m✔\033[0m %s\n" "$*"; }
warn() { printf "\033[38;5;221m⚠\033[0m %s\n" "$*"; }
info() { printf "\033[38;5;75mℹ\033[0m %s\n" "$*"; }

PURGE=0; YES=0; HOOKS_ONLY=0
for a in "$@"; do
  case "$a" in
    --hooks-only) HOOKS_ONLY=1 ;;
    --purge-config|--purge) PURGE=1 ;;
    -y|--yes) YES=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
  esac
done

info "Nebula uninstaller — only Nebula's own files will be removed."
if (( ! YES )); then
  read -r -p "Proceed with uninstall? [y/N] " yn
  [[ ${yn,,} == y* ]] || { warn "Aborted."; exit 0; }
fi

restore_or_keep() {  # remove our link, then put back the user's original (kept in data/backups)
  local f=$1 key; key=$(printf '%s' "$f" | sed 's|/|__|g')
  local bak="$DATA_DIR/backups/files/$key"
  if [[ -L $f ]] && [[ $(readlink "$f") == "$INSTALL_DIR"/* ]]; then rm -f "$f" && say "Removed link $f"; fi
  if [[ -e $bak ]]; then cp -a "$bak" "$f" && say "Restored your original $f"
  elif [[ -e $f.nebula-backup ]]; then mv -f "$f.nebula-backup" "$f" && say "Restored $f"     # old installs
  else info "No original to restore for $f"; fi
}

# 1. command
if (( ! HOOKS_ONLY )) && { [[ -L $BIN_LINK || -f $BIN_LINK ]]; }; then rm -f "$BIN_LINK" && say "Removed $BIN_LINK"; fi

# 2. Termux look + motd hook
restore_or_keep "$TERMUX_DIR/font.ttf"
restore_or_keep "$TERMUX_DIR/colors.properties"
restore_or_keep "$TERMUX_DIR/termux.properties"
restore_or_keep "$PREFIX/etc/zprofile"

# 3. zshrc block
zshrc="$HOME/.zshrc"
if [[ -f $zshrc ]] && grep -q '# nebula-BEGIN' "$zshrc"; then
  awk '
    /^# ─+$/        { hdr[++h]=$0; next }
    /^# nebula block/ { hdr[++h]=$0; next }
    /^# Everything/ { hdr[++h]=$0; next }
    /# nebula-BEGIN/ { in_block=1; h=0; next }
    /# nebula-END/   { in_block=0; next }
    !in_block { if (h) { for (i=1;i<=h;i++) print hdr[i]; h=0 } print }
  ' "$zshrc" > "$zshrc.nebula.tmp" && mv "$zshrc.nebula.tmp" "$zshrc" && say "Removed Nebula block from $zshrc"
fi
# the auto-start snippet we appended to ~/.bashrc
if [[ -f $HOME/.bashrc ]] && grep -q 'Auto-start zsh (only if installed)' "$HOME/.bashrc"; then
  awk '/# Auto-start zsh \(only if installed\)/{s=4} s>0{s--; next} {print}' "$HOME/.bashrc" > "$HOME/.bashrc.nebula.tmp" \
    && mv "$HOME/.bashrc.nebula.tmp" "$HOME/.bashrc" && say "Removed zsh auto-start from ~/.bashrc"
fi
command -v termux-reload-settings >/dev/null 2>&1 && termux-reload-settings 2>/dev/null

# 4. app dir (keep data/ unless --purge-config)
if (( HOOKS_ONLY )); then
  info "Hooks removed. The app and your data are untouched."
elif [[ -d $INSTALL_DIR ]]; then
  if (( PURGE )); then
    rm -rf "$INSTALL_DIR" && say "Removed $INSTALL_DIR (including your data)"
  else
    find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 ! -name data -exec rm -rf {} + 2>/dev/null
    say "Removed Nebula app files"
    [[ -d $DATA_DIR ]] && info "Kept $DATA_DIR (login, notes). Re-run with --purge-config to delete it."
  fi
else
  info "No install dir at $INSTALL_DIR"
fi

echo; if (( HOOKS_ONLY )); then say "Done."; else say "Nebula uninstalled. Packages left untouched."; fi
