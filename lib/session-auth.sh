#!/data/data/com.termux/files/usr/bin/env bash
# nebula — session lock. Runs auth::login on shell startup.
# Skipped if: stdin is not a tty, no creds set up yet, or the user has
# opted out via `touch $PREFIX/opt/nebula/data/no-lock`.

NEBULA_HOME="${NEBULA_HOME:-${PREFIX:-/data/data/com.termux/files/usr}/opt/nebula}"
NEBULA_CFG="${NEBULA_CFG:-$NEBULA_HOME/data}"

# Don't lock non-interactive shells, scripts, or nebula's own REPL.
[[ -t 0 && -t 1 ]] || exit 0
[[ -n $NEBULA_REPL ]] && exit 0
[[ -f "$NEBULA_CFG/no-lock" ]] && exit 0

# If creds haven't been created yet, run setup so the user has something
# to log in with. Skip silently if the auth lib is missing.
[[ -r "$NEBULA_HOME/lib/ui.sh"       ]] && source "$NEBULA_HOME/lib/ui.sh"
[[ -r "$NEBULA_HOME/lib/auth.sh"     ]] || exit 0
[[ -r "$NEBULA_HOME/lib/commands.sh" ]] && source "$NEBULA_HOME/lib/commands.sh"
[[ -r "$NEBULA_HOME/lib/update.sh"   ]] && source "$NEBULA_HOME/lib/update.sh"

# Check for updates before authentication bypass
if command -v update::check >/dev/null 2>&1; then
  update::check
fi

[[ -n $NEBULA_REPL ]] && exit 0
[[ -f "$NEBULA_CFG/no-lock" ]] && exit 0

[[ -r "$NEBULA_HOME/lib/voice.sh" ]] && source "$NEBULA_HOME/lib/voice.sh"
[[ -r "$NEBULA_HOME/lib/sound.sh" ]] && source "$NEBULA_HOME/lib/sound.sh"
source "$NEBULA_HOME/lib/auth.sh"

# Render a small banner so the lock screen feels intentional.
clear 2>/dev/null
[[ -x "$NEBULA_HOME/motd/motd.d/10-nebula-logo" ]] \
  && "$NEBULA_HOME/motd/motd.d/10-nebula-logo"

if [[ ! -f "$NEBULA_AUTH" ]]; then
  auth::setup
fi
# 3 wrong attempts close the whole Termux session (see auth::kill_session).
# If login can't run at all, still refuse to hand over a usable shell.
auth::login || exit 1
clear 2>/dev/null     # drop the lock screen; the home screen (home edit) draws next
