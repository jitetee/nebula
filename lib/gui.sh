#!/usr/bin/env bash
# nebula — graphical terminal apps: files, monitor, player, gui (tile launcher), svn (media saver). Built on nebula_core.tui.
# Mouse/touch and keyboard. They run as `python3 -m nebula_gui.<name>` with apps/gui and lib on the path.

gui::run() {   # gui::run <module> [args…]
  command -v python3 >/dev/null 2>&1 || { ui::say_status ERR "python3 is needed:  pkg install python"; return 1; }
  [[ -t 0 && -t 1 ]] || { ui::say_status ERR "$1 needs a real terminal (it is a full-screen app)."; return 1; }
  local mod=$1; shift
  NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" PYTHONPATH="$NEBULA_HOME/apps/gui:$NEBULA_HOME/lib${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m "nebula_gui.$mod" "$@"
}

cmd::files()   { gui::run files "$@"; }
cmd::monitor() { gui::run monitor "$@"; }
cmd::player()  { gui::run player "$@"; }
cmd::gui()     { gui::run launcher "$@"; }
cmd::svn() {
  command -v python3 >/dev/null 2>&1 || { ui::say_status ERR "python3 is needed:  pkg install python"; return 1; }
  NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" PYTHONPATH="$NEBULA_HOME/apps/gui:$NEBULA_HOME/lib${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m nebula_gui.svn "$@"
}
