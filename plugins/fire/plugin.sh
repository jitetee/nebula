#!/usr/bin/env bash
# nebula plugin — Firebase: check login, see what changed, choose what to deploy (hosting, functions, rules) safely
_plugin_fire_dir="$NEBULA_PLUGIN_DIR"

cmd::fire() {
  command -v python3 >/dev/null 2>&1 || { ui::say_status ERR "python3 is needed:  pkg install python"; return 1; }
  NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" PYTHONPATH="$NEBULA_HOME/lib:$_plugin_fire_dir${PYTHONPATH:+:$PYTHONPATH}" python3 "$_plugin_fire_dir/fire.py" "$@"
}
