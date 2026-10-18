#!/usr/bin/env bash
# nebula — background reminder worker. Usage: remind-fire.sh <id>
# Sleeps until the reminder is due, then notifies. Cancelled reminders
# (removed from data/reminders) wake up and exit silently.
NEBULA_HOME="${NEBULA_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NEBULA_CFG="${NEBULA_CFG:-$NEBULA_HOME/data}"
export NEBULA_HOME NEBULA_CFG
id=${1:-}; f="$NEBULA_CFG/reminders"
[[ $id =~ ^[0-9]+$ && -f $f ]] || exit 0

line=$(grep -m1 "^${id}|" "$f") || exit 0
IFS='|' read -r _ epoch _ text <<<"$line"
now=$(date +%s)
(( epoch > now )) && sleep $(( epoch - now ))

grep -q "^${id}|" "$f" 2>/dev/null || exit 0      # cancelled while sleeping
source "$NEBULA_HOME/lib/voice.sh" 2>/dev/null

api_ok=0; grep -qx 'api_ok=1' "$NEBULA_CFG/device.conf" 2>/dev/null && api_ok=1
if (( api_ok )) && command -v termux-notification >/dev/null 2>&1; then
  termux-notification --id "nebula-remind-$id" --title "⏰ Nebula reminder" \
    --content "$text" --priority high --vibrate 400,200,400 2>/dev/null
  command -v termux-vibrate >/dev/null 2>&1 && termux-vibrate -d 500 2>/dev/null
else
  # No Termux:API → shown at your next prompt (and spoken if a voice engine exists)
  printf '%s|%s\n' "$(date +%s)" "$text" >> "$NEBULA_CFG/reminders.due"
fi
command -v voice::say >/dev/null 2>&1 && voice::say "Reminder. $text"

grep -v "^${id}|" "$f" > "$f.tmp"; mv "$f.tmp" "$f"
