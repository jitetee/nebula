# apps.sh — bundled apps: ant (coding agent) and kslearn (learning system)

apps::have() { command -v "$1" >/dev/null 2>&1; }

apps::need() {   # apps::need <command> <nebula-package>
  apps::have "$1" && return 0
  ui::confirm "$1 is needed. Install it now?" Y || return 1
  cmd::install "$2" || return 1
  hash -r; apps::have "$1"
}

cmd::ant() {
  local dir="$NEBULA_HOME/apps/ant"
  [[ -f $dir/index.js ]] || { say_status err "ant is missing from this install. Run: nebula update"; return 1; }
  apps::need node nodejs || { say_status err "ant needs Node.js 18 or newer"; return 1; }
  local v; v=$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null)
  (( ${v:-0} >= 18 )) || { say_status err "ant needs Node.js 18+ (found ${v:-none})"; return 1; }
  ANT_HOME_DIR="${ANT_HOME_DIR:-}" exec node "$dir/index.js" "$@"
}

cmd::kslearn() {
  local dir="$NEBULA_HOME/apps/kslearn" keep="$NEBULA_CFG/kslearn"
  [[ -d $dir/kslearn ]] || { say_status err "kslearn is missing from this install. Run: nebula update"; return 1; }
  apps::need python3 python || { say_status err "kslearn needs Python 3"; return 1; }
  if ! python3 -c 'import click, rich' 2>/dev/null; then
    say_status info "Installing click and rich (first run only)…"
    python3 -m pip install -q click rich 2>/dev/null \
      || python3 -m pip install -q --break-system-packages click rich 2>/dev/null \
      || python3 -m pip install -q --user --break-system-packages click rich \
      || { say_status err "Could not install click and rich. Try: pip install click rich"; return 1; }
  fi
  # keep settings outside apps/ so updates never wipe them
  mkdir -p "$keep/config" "$dir/data"
  if [[ ! -L $dir/data/config ]]; then
    [[ -d $dir/data/config ]] && cp -an "$dir/data/config/." "$keep/config/" 2>/dev/null
    rm -rf "$dir/data/config"; ln -s "$keep/config" "$dir/data/config"
  fi
  PYTHONPATH="$dir" exec python3 -m kslearn "$@"
}
cmd::learn() { cmd::kslearn "$@"; }
