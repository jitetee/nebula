#!/usr/bin/env bash
# nebula plugin — interactive git: status, commit (AI message), push, pull, branch, merge and force-push with safety checks
_plugin_gitx_dir="$NEBULA_PLUGIN_DIR"

cmd::gitx() {
  command -v git >/dev/null 2>&1 || { ui::say_status ERR "git is needed:  pkg install git"; return 1; }
  NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" PYTHONPATH="$NEBULA_HOME/lib:$_plugin_gitx_dir${PYTHONPATH:+:$PYTHONPATH}" python3 "$_plugin_gitx_dir/gitx.py" "$@"
}
