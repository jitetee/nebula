#!/usr/bin/env bash
# nebula plugin — GitHub repos with full create / edit / delete, branches, pull requests and issues
_plugin_repo_dir="$NEBULA_PLUGIN_DIR"

cmd::repo() {
  command -v python3 >/dev/null 2>&1 || { ui::say_status ERR "python3 is needed:  pkg install python"; return 1; }
  NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" PYTHONPATH="$NEBULA_HOME/lib:$_plugin_repo_dir${PYTHONPATH:+:$PYTHONPATH}" python3 "$_plugin_repo_dir/repo.py" "$@"
}
