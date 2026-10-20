#!/data/data/com.termux/files/usr/bin/env bash
# nebula startup screen — renders the customizable home screen (see: home edit).
# If you turned it off (home off) nothing is printed.

export NEBULA_HOME="${NEBULA_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export NEBULA_CFG="${NEBULA_CFG:-$NEBULA_HOME/data}"
[[ -f $NEBULA_CFG/home.off ]] && exit 0

for _f in ui viz device dash data home; do source "$NEBULA_HOME/lib/$_f.sh" 2>/dev/null; done
source "$NEBULA_HOME/lib/commands.sh" 2>/dev/null
unset _f
home::render
