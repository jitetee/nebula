#!/data/data/com.termux/files/usr/bin/env bash
# nebula — system dashboard: CPU, memory, storage, battery, network, temps,
# processes and a trend history. Every section checks what Android lets Termux
# read and quietly skips what it can't. Used by `status` and the home screen.


dash::cols()  { ui::cols; }
dash::w()     { printf '%s' "${UI_W:-$(ui::cols)}"; }
dash::cores() { nproc 2>/dev/null || grep -c '^processor' /proc/cpuinfo 2>/dev/null || echo 1; }

# section heading
dash::h() { printf '\n  %s%s%s%s\n' "$C_BOLD" "$1" "$C_RESET" "${2:+  $C_DIM$2$C_RESET}"; }
# bar row:  dash::row <pct> [invert]
dash::row() { printf '     '; ui::bar "$1" "$(ui::bw "$(dash::w)")" "${2:-}"; printf ' %s%3d%%%s\n' "$C_DIM" "$1" "$C_RESET"; }

# ── CPU ─────────────────────────────────────────────────────────────────
# fills DASH_CPU (overall %) and DASH_CORES (array of per-core %); returns 1 if unreadable
dash::cpu_sample() {
  DASH_CPU=""; DASH_CORES=()
  local a b
  if [[ -r /proc/stat ]] && a=$(awk '/^cpu[0-9]* /{print $1, $2+$3+$4+$7+$8+$9, $5+$6}' /proc/stat 2>/dev/null) && [[ -n $a ]]; then
    sleep "${DASH_SAMPLE:-0.35}"
    b=$(awk '/^cpu[0-9]* /{print $1, $2+$3+$4+$7+$8+$9, $5+$6}' /proc/stat 2>/dev/null)
    local out; out=$(join <(echo "$a") <(echo "$b") 2>/dev/null | awk '{ db=$4-$2; di=$5-$3; t=db+di; printf "%s %d\n", $1, (t>0)? db*100/t : 0 }')
    [[ -n $out ]] || return 1
    DASH_CPU=$(awk '$1=="cpu"{print $2}' <<<"$out")
    mapfile -t DASH_CORES < <(awk '$1!="cpu"{print $2}' <<<"$out")
    [[ -n $DASH_CPU ]] && return 0
  fi
  # fallback: 1-minute load average relative to core count
  if [[ -r /proc/loadavg ]]; then
    DASH_CPU=$(awk -v n="$(dash::cores)" '{p=$1/n*100; if(p>100)p=100; printf "%d", p}' /proc/loadavg)
    return 0
  fi
  return 1
}

dash::cpu() {
  dash::cpu_sample || return 1
  local model; model=$(awk -F: '/Hardware|model name|Processor/{gsub(/^ +/,"",$2); print $2; exit}' /proc/cpuinfo 2>/dev/null)
  dash::h "🖥  CPU" "$(dash::cores) cores${model:+ · ${model:0:24}}"
  dash::row "${DASH_CPU:-0}"
  if (( ${#DASH_CORES[@]} > 1 )); then
    local i p w; w=$(dash::w)
    if (( w >= 58 )); then                                  # wide: one labelled bar per core, two per line
      local half=$(( (w - 8) / 2 - 12 )); (( half < 6 )) && half=6; (( half > 18 )) && half=18
      for i in "${!DASH_CORES[@]}"; do
        p=${DASH_CORES[i]}
        (( i % 2 == 0 )) && printf '     '
        printf '%sc%-2d%s ' "$C_DIM" "$i" "$C_RESET"; ui::bar "$p" "$half"; printf ' %s%3d%%%s' "$C_DIM" "$p" "$C_RESET"
        (( i % 2 == 1 || i == ${#DASH_CORES[@]} - 1 )) && printf '\n' || printf '   '
      done
    else
      local out="     " ch=(▁ ▂ ▃ ▄ ▅ ▆ ▇ █) col lvl
      for i in "${!DASH_CORES[@]}"; do
        p=${DASH_CORES[i]}; lvl=$(( p * 7 / 100 )); col=$C_GREEN
        (( p >= 85 )) && col=$C_RED || { (( p >= 60 )) && col=$C_YELLOW; }
        out+="${col}${ch[lvl]}${C_RESET}"
      done
      printf '%s  %sper core%s\n' "$out" "$C_DIM" "$C_RESET"
    fi
  fi
  if [[ -r /proc/loadavg ]]; then printf '     %sload %s%s\n' "$C_DIM" "$(cut -d' ' -f1-3 /proc/loadavg)" "$C_RESET"; fi
}

# ── memory + swap ───────────────────────────────────────────────────────
dash::mem() {
  [[ -r /proc/meminfo ]] || return 1
  local t a f c st sf
  read -r t a f c st sf < <(awk '/^MemTotal:/{t=$2} /^MemAvailable:/{a=$2} /^MemFree:/{f=$2} /^Cached:/{c=$2} /^SwapTotal:/{st=$2} /^SwapFree:/{sf=$2} END{print t, a, f, c, st, sf}' /proc/meminfo)
  [[ $t =~ ^[0-9]+$ && $t -gt 0 ]] || return 1
  local used=$(( t - a )) pct=$(( (t - a) * 100 / t ))
  dash::h "🧠 Memory" "$(ui::human_kb "$used") / $(ui::human_kb "$t")"
  dash::row "$pct"
  printf '     %scached %s · free %s%s\n' "$C_DIM" "$(ui::human_kb "${c:-0}")" "$(ui::human_kb "${f:-0}")" "$C_RESET"
  if [[ $st =~ ^[0-9]+$ ]] && (( st > 0 )); then
    local su=$(( st - sf )) sp=$(( (st - sf) * 100 / st ))
    printf '     %sswap %s / %s%s\n' "$C_DIM" "$(ui::human_kb "$su")" "$(ui::human_kb "$st")" "$C_RESET"; dash::row "$sp"
  fi
}

# ── storage (every real mount) ──────────────────────────────────────────
dash::disk() {
  local shown=0 fs total used avail cap mount
  while read -r fs total used avail cap mount; do
    [[ $cap =~ ^[0-9]+%$ ]] || continue; cap=${cap%\%}
    (( shown == 0 )) && dash::h "💾 Storage"
    printf '     %s%s%s  %s%s / %s%s\n' "$C_CYAN" "$(viz::trunc "$mount" $(( $(dash::w) - 24 > 12 ? $(dash::w) - 24 : 12 )))" "$C_RESET" "$C_DIM" "$(ui::human_kb "$used")" "$(ui::human_kb "$total")" "$C_RESET"
    dash::row "$cap"
    shown=$((shown+1)); (( shown >= ${DASH_MAXDISK:-4} )) && break
  done < <(df -P -k 2>/dev/null | awk 'NR>1 && $1 !~ /tmpfs|devtmpfs|overlay|apex|^none/ && ($6 ~ /^\/$|^\/data$|^\/storage|^\/home|^\/sdcard|^\/mnt/) && $2 > 200000 && $2 < 4000000000')
  if (( shown == 0 )); then
    read -r fs total used avail cap mount < <(df -P -k "$HOME" 2>/dev/null | awk 'NR==2')
    [[ ${cap%\%} =~ ^[0-9]+$ ]] || return 1
    dash::h "💾 Storage" "home"; dash::row "${cap%\%}"
  fi
}

# ── battery ─────────────────────────────────────────────────────────────
dash::battery() {
  local bat pct st temp; bat=$(device::battery) || return 1
  IFS='|' read -r pct st temp <<<"$bat"; [[ $pct =~ ^[0-9]+$ ]] || return 1
  local ic="🔋"; [[ $st == charging || $st == full ]] && ic="⚡"
  dash::h "$ic Battery" "${st:-?}${temp:+ · ${temp}°C}"
  dash::row "$pct" invert
}

# ── network ─────────────────────────────────────────────────────────────
dash::net() {
  local ip ssid="" rssi="" j
  if declare -F device::_api_ok >/dev/null && device::_api_ok && command -v termux-wifi-connectioninfo >/dev/null 2>&1; then
    j=$(timeout 5 termux-wifi-connectioninfo 2>/dev/null)
    ssid=$(grep -o '"ssid": *"[^"]*"' <<<"$j" | cut -d'"' -f4); rssi=$(grep -o '"rssi": *-\?[0-9]*' <<<"$j" | grep -o '\-\?[0-9]*$')
  fi
  ip=$(ui::lan_ip)
  dash::h "📶 Network" "${ssid:-${ip:+connected}}"
  printf '     %s%s%s%s\n' "$C_DIM" "${ip:-offline}" "${rssi:+ · ${rssi} dBm}" "$C_RESET"
  if [[ -r /proc/net/dev ]]; then
    local a b; a=$(awk -F'[: ]+' '$2 ~ /^(wlan|rmnet|eth)/{rx+=$3; tx+=$11} END{print rx+0, tx+0}' /proc/net/dev 2>/dev/null)
    if [[ -n $a && $a != "0 0" ]]; then
      sleep "${DASH_SAMPLE:-0.35}"; b=$(awk -F'[: ]+' '$2 ~ /^(wlan|rmnet|eth)/{rx+=$3; tx+=$11} END{print rx+0, tx+0}' /proc/net/dev 2>/dev/null)
      local rate; rate=$(awk -v a="$a" -v b="$b" -v dt="${DASH_SAMPLE:-0.35}" 'BEGIN{split(a,x," "); split(b,y," "); printf "%d %d", (y[1]-x[1])/dt/1024, (y[2]-x[2])/dt/1024}')
      printf '     %s↓ %s KB/s   ↑ %s KB/s%s\n' "$C_DIM" "${rate% *}" "${rate#* }" "$C_RESET"
    fi
  fi
}

# ── temperatures ────────────────────────────────────────────────────────
dash::temp() {
  local out="" z t name n=0
  for z in /sys/class/thermal/thermal_zone*; do
    [[ -r $z/temp ]] || continue; t=$(<"$z/temp"); [[ $t =~ ^-?[0-9]+$ ]] || continue
    (( t > 1000 )) && t=$(( t / 1000 )); (( t < 5 || t > 120 )) && continue
    name=$(<"$z/type" 2>/dev/null); name=${name:0:10}
    out+="${name:-zone}: ${t}°C   "; n=$((n+1)); (( n >= 3 )) && break
  done
  local bt; bt=$(device::battery 2>/dev/null | cut -d'|' -f3); [[ -n $bt && -z $out ]] && out="battery: ${bt}°C"
  [[ -z $out ]] && return 1
  dash::h "🌡  Temperature"; printf '     %s%s%s\n' "$C_DIM" "$out" "$C_RESET"
}

# ── processes (what Android shows Termux) ───────────────────────────────
dash::top() {
  local n=${DASH_TOPN:-5} w; w=$(dash::w)
  local rows; rows=$(ps -eo rss=,comm= 2>/dev/null | awk '$1>0' | sort -rn | head -n "$n")
  [[ -n $rows ]] || return 1
  local mx; mx=$(head -1 <<<"$rows" | awk '{print $1}')
  local nw=$(( w >= 50 ? 18 : 12 )) bw; bw=$(( w - nw - 18 )); (( bw < 6 )) && bw=6; (( bw > 30 )) && bw=30
  dash::h "⚙  Top processes" "by memory"
  while read -r rss comm; do
    printf '     %-*s ' "$nw" "$(viz::trunc "${comm##*/}" "$nw")"; viz::bar "$rss" "$mx" "$bw" "$C_MAGENTA"; printf ' %s%s%s\n' "$C_DIM" "$(ui::human_kb "$rss")" "$C_RESET"
  done <<<"$rows"
}

# ── uptime / identity ───────────────────────────────────────────────────
dash::uptime() {
  local up; up=$(uptime -p 2>/dev/null | sed 's/^up //')
  [[ -z $up && -r /proc/uptime ]] && up=$(awk '{d=int($1/86400); h=int($1%86400/3600); m=int($1%3600/60); printf "%dd %dh %dm", d,h,m}' /proc/uptime)
  printf '%s' "$up"
}

# ── trend history (a sample is recorded at most every 5 minutes) ────────
dash::record() {
  local f="$NEBULA_CFG/status.hist" now; now=$(date +%s)
  [[ -f $f ]] && (( now - $(date -r "$f" +%s 2>/dev/null || echo 0) < 300 )) && return 0
  local mp="" cpu="${DASH_CPU:-}" b="" dp=""
  [[ -r /proc/meminfo ]] && mp=$(awk '/^MemTotal:/{t=$2} /^MemAvailable:/{a=$2} END{if(t>0) printf "%d", (t-a)*100/t}' /proc/meminfo)
  b=$(device::battery 2>/dev/null | cut -d'|' -f1)
  dp=$(df -P -k "$HOME" 2>/dev/null | awk 'NR==2{gsub("%","",$5); print $5}')
  mkdir -p "$NEBULA_CFG"; printf '%s|%s|%s|%s|%s\n' "$now" "$cpu" "$mp" "$b" "$dp" >> "$f"
  tail -n 120 "$f" > "$f.tmp" && mv "$f.tmp" "$f"
}
dash::trend() {
  local f="$NEBULA_CFG/status.hist"; [[ -s $f ]] || return 1
  local n; n=$(wc -l < "$f"); (( n >= 3 )) || return 1
  dash::h "📈 Trend" "last $n checks"
  local col name idx
  for col in "cpu 2" "memory 3" "battery 4" "storage 5"; do
    name=${col% *}; idx=${col#* }
    local vals; vals=$(tail -n 60 "$f" | cut -d'|' -f"$idx" | grep -E '^[0-9]+$')
    [[ $(wc -l <<<"$vals") -ge 3 ]] || continue
    printf '     %-8s %s %s%s%%%s\n' "$name" "$(viz::spark_fixed $(( $(dash::w) - 20 > 12 ? ($(dash::w) - 20 > 60 ? 60 : $(dash::w) - 20) : 12 )) <<<"$vals")" "$C_DIM" "$(tail -1 <<<"$vals")" "$C_RESET"
  done
}

# ── blocks + grid ───────────────────────────────────────────────────────
DASH_ALL="cpu mem disk battery net temp top trend"

# dash::header → the title rule, full width
dash::header() {
  local cols; cols=$(ui::cols)
  local fmt='%a %d %b · %H:%M'; (( cols < 44 )) && fmt='%d %b %H:%M'
  printf '\n%s%s⚡ Nebula status%s  %s%s%s\n' "$C_CYAN" "$C_BOLD" "$C_RESET" "$C_DIM" "$(date "+$fmt")" "$C_RESET"
  printf '%s%s%s\n' "$C_DIM" "$(ui::rep ─ "$cols")" "$C_RESET"
  printf '  %s%s@%s%s · up %s\n' "$C_DIM" "${NEBULA_USER:-$(id -un 2>/dev/null)}" "$(uname -n 2>/dev/null | cut -c1-14)" "$C_RESET" "$(dash::uptime)"
}

# dash::block <section> → the text of one section (empty if the device can't show it)
dash::block() {
  case $1 in
    cpu) dash::cpu ;; mem) dash::mem ;; disk) dash::disk ;; battery) dash::battery ;; net) dash::net ;;
    temp) dash::temp ;; top) dash::top ;; trend) dash::record; dash::trend ;;
    clock)     dash::clock ;;
    weather|crypto|news|sports) home::w_cached "$1" 2>/dev/null ;;
    todo)      home::w_todo 2>/dev/null ;;
    reminders) home::w_reminders 2>/dev/null ;;
  esac
}
dash::clock() {
  dash::h "🕐 $(date '+%H:%M:%S')" "$(date '+%A %d %B %Y')"
  printf '     %sup %s%s\n' "$C_DIM" "$(dash::uptime)" "$C_RESET"
}

# dash::body <min block width> <max columns> <sections…> → the sections laid out in a grid
dash::body() {
  local min=$1 max=$2; shift 2
  local n w; read -r n w < <(ui::grid_dims "$min" "$max")
  local UI_W=$w s b
  ui::blocks_reset
  for s in "$@"; do b=$(dash::block "$s" 2>/dev/null); [[ -n ${b//[$'\n ']/} ]] && ui::blocks_add "$b"; done
  ui::blocks_flush "$n" 3 | ui::clip "$(ui::cols)"
}

dash::render() {  # dash::render [sections…]
  local sec=("$@"); [[ ${#sec[@]} -eq 0 || ${sec[0]} == all ]] && sec=($DASH_ALL)
  ui::resized; DASH_SAMPLE=0.3
  dash::header
  dash::body 40 3 "${sec[@]}"
  printf '\n'
}

# ── full-screen mode ────────────────────────────────────────────────────
DASH_PANELS="clock cpu mem disk battery net temp top trend weather crypto news sports todo reminders"
dash::panels_load() {
  DASH_ON=(clock cpu mem disk battery net top trend)
  [[ -r $NEBULA_CFG/dash.conf ]] && { local l; l=$(sed -n 's/^panels=//p' "$NEBULA_CFG/dash.conf" | head -1); local p ok=(); for p in $l; do [[ " $DASH_PANELS " == *" $p "* ]] && ok+=("$p"); done; (( ${#ok[@]} )) && DASH_ON=("${ok[@]}"); }
  return 0
}
dash::panels_save() { mkdir -p "$NEBULA_CFG"; printf 'panels=%s\n' "${DASH_ON[*]}" > "$NEBULA_CFG/dash.conf"; }

# one full frame (header + grid) as text; the caller scrolls/clips it
dash::frame() {
  local cols rows bp; cols=$(ui::cols); rows=$(ui::rows); bp=$(ui::bp)
  local n w; read -r n w < <(ui::grid_dims 38 4)
  local UI_W=$w DASH_TOPN=$(( rows > 40 ? 10 : (rows > 28 ? 7 : 5) ))
  local s b
  ui::blocks_reset
  for s in "${DASH_ON[@]}"; do b=$(dash::block "$s" 2>/dev/null); [[ -n ${b//[$'\n ']/} ]] && ui::blocks_add "$b"; done
  ui::blocks_flush "$n" 3
}

cmd::dash() {
  if [[ ! -t 0 || ! -t 1 ]]; then dash::render; return; fi
  dash::panels_load
  local every=2 paused=0 off=0 key rc help=0 frame="" lines=() total=0 view rows cols bp first=1
  [[ ${1:-} =~ ^[0-9]+$ ]] && every=$1
  printf '\033[?1049h\033[?25l'                                  # alternate screen: your terminal comes back untouched
  trap 'printf "\033[?25h\033[?1049l"; trap - EXIT INT TERM WINCH' EXIT
  trap 'ui::resized; _dash_redraw=1' WINCH
  local last_build=0
  while :; do
    rows=$(ui::rows); cols=$(ui::cols); bp=$(ui::bp); view=$(( rows - 3 ))
    if (( first || (!paused && SECONDS - last_build >= every) || ${_dash_rebuild:-0} )); then
      DASH_SAMPLE=0.25; frame=$(dash::frame); last_build=$SECONDS; first=0; _dash_rebuild=0
      mapfile -t lines < <(printf '%s\n' "$frame" | ui::clip "$cols"); total=${#lines[@]}
    fi
    (( off > total - view )) && off=$(( total - view )); (( off < 0 )) && off=0
    local out i=0
    out=$'\033[H'
    local when; when=$(date '+%a %d %b %H:%M:%S'); (( cols < 52 )) && when=$(date '+%H:%M:%S')
    local ttl="⚡ Nebula ${cols}×${rows} ${bp} · ${when}$([[ $paused == 1 ]] && echo ' · paused')"
    out+="${C_CYAN}${C_BOLD}$(viz::trunc "$ttl" "$cols")${C_RESET}"$'\033[K\n'
    out+="${C_DIM}$(ui::rep ─ "$cols")${C_RESET}"$'\033[K\n'
    if (( help )); then
      local hl=("  ${C_BOLD}Keys${C_RESET}" "  q quit · r refresh now · space pause" "  j/k ↑/↓ scroll · g/G top/bottom" "  + / - refresh speed (now ${every}s)" "  1-9,0 toggle panels:" )
      local idx=0 p; for p in $DASH_PANELS; do idx=$((idx+1)); local m="off"; [[ " ${DASH_ON[*]} " == *" $p "* ]] && m="ON "; (( idx <= 10 )) && hl+=("    $(( idx % 10 )) ${m} $p"); done
      hl+=("" "  ? close help")
      mapfile -t hl < <(printf '%s\n' "${hl[@]}" | ui::clip "$cols")
      for ((i=0;i<view;i++)); do out+="${hl[i]:-}"$'\033[K\n'; done
    else
      for ((i=0;i<view;i++)); do out+="${lines[off+i]:-}"$'\033[K\n'; done
    fi
    local pos=""; (( total > view )) && pos=" · $(( off + 1 ))-$(( off + view > total ? total : off + view ))/$total ▲▼"
    out+="${C_DIM}$(viz::trunc "q quit · r refresh · space pause · +/- ${every}s · j/k scroll · 1-9 panels · ? help$pos" "$cols")${C_RESET}"$'\033[K\033[J'
    printf '%s' "$out"
    _dash_redraw=0
    IFS= read -rsn1 -t 1 key; rc=$?
    if (( rc > 128 )); then [[ ${_dash_redraw:-0} == 1 ]] && continue; continue; fi     # timeout or resize → loop (redraws; refreshes when due)
    [[ $key == $'\033' ]] && { IFS= read -rsn2 -t 0.02 key2; key+=$key2; }
    case $key in
      q|Q) break ;;
      r) _dash_rebuild=1 ;;
      ' ') paused=$(( 1 - paused )) ;;
      '+') every=$(( every > 1 ? every - 1 : 1 )) ;;  '-') every=$(( every + 1 )) ;;
      j|$'\033[B') off=$(( off + 1 )) ;;   k|$'\033[A') off=$(( off - 1 )) ;;
      $'\033[6') off=$(( off + view - 1 )); IFS= read -rsn1 -t 0.02 _ ;;  $'\033[5') off=$(( off - view + 1 )); IFS= read -rsn1 -t 0.02 _ ;;
      g) off=0 ;; G) off=$total ;;
      '?') help=$(( 1 - help )) ;;
      [0-9])
        local idx=$(( key == 0 ? 10 : key )) p2="" j=0 q
        for q in $DASH_PANELS; do j=$((j+1)); (( j == idx )) && p2=$q; done
        if [[ -n $p2 ]]; then
          if [[ " ${DASH_ON[*]} " == *" $p2 "* ]]; then local nw=(); for q in "${DASH_ON[@]}"; do [[ $q != "$p2" ]] && nw+=("$q"); done; DASH_ON=("${nw[@]}")
          else DASH_ON+=("$p2"); fi
          dash::panels_save; _dash_rebuild=1
        fi ;;
    esac
  done
  printf '\033[?25h\033[?1049l'; trap - EXIT INT TERM WINCH
}

cmd::status() {
  local live=0 every=2 sec=() a
  while (( $# )); do case $1 in
    --live|-l) live=1; [[ ${2:-} =~ ^[0-9]+$ ]] && { every=$2; shift; } ;;
    cpu|mem|memory|disk|storage|battery|net|network|temp|top|trend|all) a=$1; [[ $a == memory ]] && a=mem; [[ $a == storage ]] && a=disk; [[ $a == network ]] && a=net; sec+=("$a") ;;
    *) ui::say_status ERR "Usage: status [cpu|mem|disk|battery|net|temp|top|trend] [--live [seconds]]   ·   full screen: dash"; return 1 ;;
  esac; shift; done
  if (( live )); then cmd::dash "$every"; return; fi
  dash::render "${sec[@]}"
}
