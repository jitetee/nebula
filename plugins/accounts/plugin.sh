#!/usr/bin/env bash
# nebula plugin — who you are logged in as everywhere: git, GitHub, Firebase, AI, Copilot, Termux, with one-step fixes
_plugin_accounts_dir="$NEBULA_PLUGIN_DIR"

cmd::accounts() {
  command -v python3 >/dev/null 2>&1 || { ui::say_status ERR "python3 is needed:  pkg install python"; return 1; }
  NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" PYTHONPATH="$NEBULA_HOME/lib:$NEBULA_HOME/plugins/fire:$NEBULA_HOME/plugins/repo:$_plugin_accounts_dir${PYTHONPATH:+:$PYTHONPATH}" python3 "$_plugin_accounts_dir/accounts.py" "$@"
}
