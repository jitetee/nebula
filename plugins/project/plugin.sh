#!/usr/bin/env bash
# nebula plugin — ask your project: what to do next, review changes, whether to merge or deploy, explain the repo
_plugin_project_dir="$NEBULA_PLUGIN_DIR"

cmd::project() {
  command -v python3 >/dev/null 2>&1 || { ui::say_status ERR "python3 is needed:  pkg install python"; return 1; }
  NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" PYTHONPATH="$NEBULA_HOME/lib:$NEBULA_HOME/plugins/gitx:$NEBULA_HOME/plugins/fire:$_plugin_project_dir${PYTHONPATH:+:$PYTHONPATH}" python3 "$_plugin_project_dir/project.py" "$@"
}
