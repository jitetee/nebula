#!/usr/bin/env bash
# nebula — refresh data/.battery (pct|status) in the background for the prompt.
NEBULA_HOME="${NEBULA_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NEBULA_CFG="${NEBULA_CFG:-$NEBULA_HOME/data}"
out="$NEBULA_CFG/.battery"
touch "$out" 2>/dev/null    # stamp first so we don't respawn while this runs
pct=""; st=""
if grep -qx 'api_ok=1' "$NEBULA_CFG/device.conf" 2>/dev/null && command -v termux-battery-status >/dev/null 2>&1; then
  j=$(timeout 6 termux-battery-status 2>/dev/null)
  pct=$(grep -o '"percentage": *[0-9]*' <<<"$j" | grep -o '[0-9]*$')
  st=$(grep -o '"status": *"[A-Z_]*"' <<<"$j" | cut -d'"' -f4); st=${st,,}
fi
if [[ -z $pct && -r /sys/class/power_supply/battery/capacity ]]; then
  pct=$(cat /sys/class/power_supply/battery/capacity); st=$(cat /sys/class/power_supply/battery/status 2>/dev/null); st=${st,,}
fi
[[ -n $pct ]] && printf '%s|%s\n' "$pct" "$st" > "$out"
