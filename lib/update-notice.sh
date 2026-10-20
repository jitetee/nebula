#!/usr/bin/env bash
# nebula — prints the "update available" notice (if any). Called by zsh after the home screen.
# Reads a cached answer; refreshes it in the background. Silent when you're up to date.
NEBULA_HOME="${NEBULA_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NEBULA_CFG="${NEBULA_CFG:-$NEBULA_HOME/data}"
source "$NEBULA_HOME/lib/ui.sh"
source "$NEBULA_HOME/lib/viz.sh" 2>/dev/null
source "$NEBULA_HOME/lib/update.sh"
update::check
