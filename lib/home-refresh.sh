#!/usr/bin/env bash
# nebula — background refresher for home-screen network widgets.
NEBULA_HOME="${NEBULA_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NEBULA_CFG="${NEBULA_CFG:-$NEBULA_HOME/data}"
export NEBULA_HOME NEBULA_CFG
for f in ui viz device dash data home; do source "$NEBULA_HOME/lib/$f.sh" 2>/dev/null; done
source "$NEBULA_HOME/lib/commands.sh" 2>/dev/null
home::refresh "$@" >/dev/null 2>&1
