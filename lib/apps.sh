# apps.sh — bundled apps: ant (coding agent) and jtlearn (learning system)

apps::have() { command -v "$1" >/dev/null 2>&1; }

apps::need() {   # apps::need <command> <nebula-package>
  apps::have "$1" && return 0
  ui::confirm "$1 is needed. Install it now?" Y || return 1
  cmd::install "$2" || return 1
  hash -r; apps::have "$1"
}

cmd::ant() {
  local dir="$NEBULA_HOME/apps/ant"
  [[ -f $dir/ant/__main__.py ]] || { ui::say_status ERR "ant is missing from this install. Run: nebula update"; return 1; }
  apps::need python3 python || { ui::say_status ERR "ant needs Python 3"; return 1; }
  PYTHONPATH="$dir" exec python3 -m ant "$@"
}

cmd::jtlearn() {
  local dir="$NEBULA_HOME/apps/jtlearn" keep="$NEBULA_CFG/jtlearn"
  [[ -d $dir/jtlearn ]] || { ui::say_status ERR "jtlearn is missing from this install. Run: nebula update"; return 1; }
  apps::need python3 python || { ui::say_status ERR "jtlearn needs Python 3"; return 1; }
  # keep settings outside apps/ so updates never wipe them
  mkdir -p "$keep/config" "$dir/data"
  if [[ ! -L $dir/data/config ]]; then
    [[ -d $dir/data/config ]] && cp -an "$dir/data/config/." "$keep/config/" 2>/dev/null
    rm -rf "$dir/data/config"; ln -s "$keep/config" "$dir/data/config"
  fi
  PYTHONPATH="$dir" exec python3 -m jtlearn "$@"
}
cmd::learn()   { cmd::jtlearn "$@"; }
