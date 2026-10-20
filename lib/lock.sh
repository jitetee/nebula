#!/usr/bin/env bash
# nebula — lock the current shell (called by the zsh idle timer).
# Exit 0 = unlocked. 3 wrong passwords close the whole session.
NEBULA_HOME="${NEBULA_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NEBULA_CFG="${NEBULA_CFG:-$NEBULA_HOME/data}"
export NEBULA_HOME NEBULA_CFG
[[ -f $NEBULA_CFG/no-lock ]] && exit 0
source "$NEBULA_HOME/lib/ui.sh"
source "$NEBULA_HOME/lib/voice.sh"
source "$NEBULA_HOME/lib/sound.sh"
source "$NEBULA_HOME/lib/auth.sh"
[[ -f $NEBULA_AUTH ]] || exit 0
auth::unlock
