#!/usr/bin/env bash
# nebula — phone hardware keys for the Termux extra-keys row (needs the Termux:API app + package).
#   hwkey.sh vol up|down|mute     media volume ±1 step / mute (press again to restore)
#   hwkey.sh bright up|down       screen brightness ±1 step
#   hwkey.sh torch                flashlight on/off
# Prints ONE short line (shown by the zsh widgets under the prompt). Never needs a terminal.
NEBULA_HOME="${NEBULA_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NEBULA_CFG="${NEBULA_CFG:-$NEBULA_HOME/data}"
mkdir -p "$NEBULA_CFG" 2>/dev/null

need() { command -v "$1" >/dev/null 2>&1 || { echo "⚠ needs Termux:API (pkg install termux-api + the app)"; exit 1; }; }

vol_state() {  # → "volume max" for the music stream
  local j; j=$(timeout 5 termux-volume 2>/dev/null | tr -d '\n ' | grep -o '{[^}]*"stream":"music"[^}]*}')
  [[ -n $j ]] || return 1
  printf '%s %s\n' "$(sed -n 's/.*"volume":\([0-9]*\).*/\1/p' <<<"$j")" "$(sed -n 's/.*"max_volume":\([0-9]*\).*/\1/p' <<<"$j")"
}

case ${1:-} in
  vol)
    need termux-volume
    read -r v m < <(vol_state) || { echo "⚠ couldn't read the volume"; exit 1; }
    [[ $v =~ ^[0-9]+$ && $m =~ ^[0-9]+$ ]] || { echo "⚠ couldn't read the volume"; exit 1; }
    prev="$NEBULA_CFG/.vol_prev"
    case ${2:-} in
      up)   n=$(( v + 1 )) ;;
      down) n=$(( v - 1 )) ;;
      mute) if (( v > 0 )); then echo "$v" > "$prev"; n=0; else n=$(cat "$prev" 2>/dev/null); [[ $n =~ ^[0-9]+$ ]] || n=$(( m / 2 )); fi ;;
      *)    echo "usage: vol up|down|mute"; exit 1 ;;
    esac
    (( n > m )) && n=$m; (( n < 0 )) && n=0
    termux-volume music "$n" >/dev/null 2>&1
    if (( n == 0 )); then echo "🔇 muted"; else echo "🔊 volume $n/$m"; fi ;;
  bright)
    need termux-brightness
    f="$NEBULA_CFG/.brightness"; b=$(cat "$f" 2>/dev/null); [[ $b =~ ^[0-9]+$ ]] || b=128
    case ${2:-} in up) b=$(( b + 32 )) ;; down) b=$(( b - 32 )) ;; *) echo "usage: bright up|down"; exit 1 ;; esac
    (( b > 255 )) && b=255; (( b < 8 )) && b=8
    echo "$b" > "$f"; termux-brightness "$b" >/dev/null 2>&1
    echo "🔆 brightness $(( b * 100 / 255 ))%" ;;
  torch)
    need termux-torch
    f="$NEBULA_CFG/.torch"
    if [[ -f $f ]]; then rm -f "$f"; termux-torch off >/dev/null 2>&1; echo "🔦 torch off"
    else touch "$f"; termux-torch on >/dev/null 2>&1; echo "🔦 torch on"; fi ;;
  *) echo "usage: hwkey.sh vol up|down|mute · bright up|down · torch"; exit 1 ;;
esac
