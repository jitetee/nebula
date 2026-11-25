#!/usr/bin/env bash
# nebula — palette: one colour scheme for the shell, ant, jtlearn and Neovim (nebula_core/theme.py)
cmd::palette() {
  local arg=${1:-}
  local run=(env PYTHONPATH="$NEBULA_HOME/lib" NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" python3 -m nebula_core.theme)
  case $arg in
    ""|list|ls) "${run[@]}" list; ui::hint "palette <name> switches the shell, ant, jtlearn and Neovim at once" ;;
    reset)      "${run[@]}" nebula ;;
    *)          "${run[@]}" "$arg" && { source "$NEBULA_CFG/palette.sh" 2>/dev/null; true; } ;;
  esac
}
