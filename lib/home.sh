#!/data/data/com.termux/files/usr/bin/env bash
# nebula — customizable home screen shown after login.
#   home            show it now          home edit      arrow-key editor
#   home preset X   switch layout        home refresh   update weather/crypto/news/sports
#   home off / on   hide / show at login
# Network widgets are served from a cache and refreshed in the background, so
# logging in is always instant.

HOME_KEYS="widgets weather_city crypto_coins news_topic sports_league ttl clear"
HOME_WIDGETS="logo greeting sysinfo disk battery network todo reminders weather crypto news sports tip trend"
declare -gA HC=()

home::defaults() { HC=( [widgets]="logo sysinfo disk" [weather_city]="" [crypto_coins]="btc,eth" [news_topic]=world [sports_league]=epl [ttl]=900 [clear]=1 ); }

home::valid() {
  local k=$1 v=$2 w
  case $k in
    widgets)       for w in $v; do [[ " $HOME_WIDGETS " == *" $w "* ]] || return 1; done ;;
    weather_city)  [[ $v =~ ^[A-Za-z0-9\ ,._+-]{0,40}$ ]] ;;
    crypto_coins)  [[ $v =~ ^[a-z0-9,-]{0,40}$ ]] ;;
    news_topic)    [[ $v == @(world|africa|tech|business|science|health|sport|hn) ]] ;;
    sports_league) [[ $v =~ ^[a-z0-9]{0,12}$ ]] ;;
    ttl)           [[ $v =~ ^[0-9]{2,5}$ ]] && (( v >= 60 )) ;;
    clear)         [[ $v == [01] ]] ;;
    *) return 1 ;;
  esac
}
home::load() {
  local f=${1:-$NEBULA_CFG/home.conf} k v; home::defaults
  [[ -r $f ]] || return 0
  while IFS='=' read -r k v; do [[ -z $k || $k == \#* ]] && continue; home::valid "$k" "$v" && HC[$k]=$v; done < "$f"
}
home::save() { local k; mkdir -p "$NEBULA_CFG"; { for k in $HOME_KEYS; do printf '%s=%s\n' "$k" "${HC[$k]}"; done; } > "$NEBULA_CFG/home.conf.tmp" && mv "$NEBULA_CFG/home.conf.tmp" "$NEBULA_CFG/home.conf"; }
home::presets() { local f; for f in "$NEBULA_HOME"/assets/home/*.conf; do basename "$f" .conf; done; }

# ── cache for network widgets ───────────────────────────────────────────
home::cache() { printf '%s' "$NEBULA_CFG/cache/home-$1.txt"; }
home::stale() {  # widget → 0 if the cache should be refreshed
  local f try now; f=$(home::cache "$1"); try="$f.try"; now=$(date +%s)
  [[ -f $try ]] && (( now - $(date -r "$try" +%s 2>/dev/null || echo 0) < 120 )) && return 1   # failed recently: don't hammer
  [[ -s $f ]] || return 0
  (( now - $(date -r "$f" +%s 2>/dev/null || echo 0) > ${HC[ttl]} ))
}
home::age() { local f; f=$(home::cache "$1"); [[ -s $f ]] || return; local d=$(( $(date +%s) - $(date -r "$f" +%s 2>/dev/null || echo 0) )); (( d < 90 )) && echo "now" || { (( d < 3600 )) && echo "$((d/60))m ago" || echo "$((d/3600))h ago"; }; }

# ── generators (run in the background; print the finished block) ────────
home::gen_weather() {
  command -v curl >/dev/null 2>&1 || return 1
  local city=${HC[weather_city]// /+} line
  line=$(curl -fsS --max-time 6 "https://wttr.in/${city}?format=%l:+%c+%t+%C&M" 2>/dev/null) || return 1
  [[ -n $line && $line != *Unknown* && $line != *"<"* ]] || return 1
  printf '  %s\n' "$line"
}
home::gen_crypto() {
  command -v curl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1 || return 1
  local ids="" c i; for c in ${HC[crypto_coins]//,/ }; do i=$(crypto::id_fast "$c") && ids+="${ids:+,}$i"; done
  [[ -n $ids ]] || return 1
  local body; body=$(curl -fsSL --max-time 8 "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=$ids&sparkline=true&price_change_percentage=24h" 2>/dev/null) || return 1
  [[ $(jq -r 'type' <<<"$body" 2>/dev/null) == array ]] || return 1
  local sy p ch sp
  while IFS=$'\037' read -r sy p ch sp; do
    printf '  %s%-5s%s %10s  %s  %s\n' "$C_BOLD" "${sy^^}" "$C_RESET" "\$$(viz::money "$p")" "$(viz::pct "$ch")" "$(tr ' ' '\n' <<<"$sp" | viz::spark 10)"
  done < <(jq -r '.[] | [.symbol, .current_price, (.price_change_percentage_24h // ""), (.sparkline_in_7d.price | map(tostring) | join(" "))] | map(tostring) | join("\u001f")' <<<"$body")
}
crypto::id_fast() { case "${1,,}" in btc) echo bitcoin;; eth) echo ethereum;; sol) echo solana;; bnb) echo binancecoin;; xrp) echo ripple;; ada) echo cardano;; doge) echo dogecoin;; ton) echo the-open-network;; dot) echo polkadot;; ltc) echo litecoin;; avax) echo avalanche-2;; link) echo chainlink;; trx) echo tron;; bitcoin|ethereum|solana|cardano|dogecoin|litecoin|ripple|polkadot) echo "${1,,}";; *) return 1;; esac; }
home::gen_news() {
  command -v curl >/dev/null 2>&1 || return 1
  local f; f=$(news::feed "${HC[news_topic]}") || return 1
  local body; body=$(curl -fsSL --max-time 8 -A nebula-termux "${f#*|}" 2>/dev/null) || return 1
  local rows; rows=$(news::parse <<<"$body" | head -n 3); [[ -n $rows ]] || return 1
  local t l d s ep
  while IFS=$'\037' read -r t l d s; do
    ep=$(date -d "$d" +%s 2>/dev/null || echo 0)
    printf '%s\t%s\n' "$ep" "$t"
  done <<<"$rows"
}
home::gen_sports() {
  command -v curl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1 || return 1
  [[ -n ${HC[sports_league]} ]] || return 1
  sports::resolve "${HC[sports_league]}" || return 1
  local body; body=$(curl -fsSL --max-time 8 "https://site.api.espn.com/apis/site/v2/sports/$S_PATH/scoreboard" 2>/dev/null) || return 1
  local rows; rows=$(jq -r '.events[]? | (.competitions[0].competitors // []) as $c | ($c | map(select(.homeAway=="home"))[0] // $c[0]) as $h | ($c | map(select(.homeAway=="away"))[0] // $c[1]) as $a |
    [.status.type.state, (.status.type.shortDetail // ""), ($h.team.abbreviation // $h.athlete.shortName // "?"), ($h.score // ""), ($a.team.abbreviation // $a.athlete.shortName // "?"), ($a.score // ""), .date] | map(tostring) | join("\u001f")' <<<"$body" 2>/dev/null | head -n 20)
  [[ -n $rows ]] || { printf '  %s%s Nothing on today%s\n' "$C_DIM" "$(sports::icon "$S_SPORT")" "$C_RESET"; return 0; }
  local n=0 st det h hs a as dt col
  for want in in pre post; do
    while IFS=$'\037' read -r st det h hs a as dt; do
      [[ $st == "$want" ]] || continue
      case $st in in) col=$C_RED;; pre) col=$C_YELLOW; det=$(date -d "$dt" +%H:%M 2>/dev/null || echo "$det");; *) col=$C_GREEN;; esac
      printf '  %s%s%s %-4s %2s – %-2s %-4s %s%s%s\n' "$col" "▎" "$C_RESET" "$h" "${hs:-·}" "${as:-·}" "$a" "$C_DIM" "$det" "$C_RESET"
      n=$((n+1)); (( n >= 4 )) && break 2
    done <<<"$rows"
  done
}

# ── widgets (instant, local) ────────────────────────────────────────────
home::w_greeting() {
  local h w; h=$(date +%H); h=$((10#$h)); w=$(ui::cols); local g="Good evening"
  (( h < 5 )) && g="Burning the midnight oil" || { (( h < 12 )) && g="Good morning" || { (( h < 17 )) && g="Good afternoon"; }; }
  local who=${NEBULA_USER:-$(id -un 2>/dev/null)} when
  if   (( w >= 60 )); then when=$(date '+%a %d %b · %H:%M')
  elif (( w >= 44 )); then when=$(date '+%H:%M')
  else when=""; (( w < 34 )) && g=${g%% *}; fi
  printf '\n  %s%s%s, %s%s%s ⚡%s\n' "$C_CYAN" "$g" "$C_RESET" "$C_BOLD" "$who" "$C_RESET" "${when:+  $C_DIM$when$C_RESET}"
}
home::w_sysinfo() {
  printf '\n'
  DASH_SAMPLE=0.2 dash::cpu_sample && { printf '  🖥  CPU  '; ui::bar "${DASH_CPU:-0}" "$(ui::bw $(( $(dash::w) - 6 )))"; printf ' %s%3d%%%s\n' "$C_DIM" "${DASH_CPU:-0}" "$C_RESET"; }
  if [[ -r /proc/meminfo ]]; then
    local t a; read -r t a < <(awk '/^MemTotal:/{t=$2} /^MemAvailable:/{a=$2} END{print t, a}' /proc/meminfo)
    [[ $t =~ ^[0-9]+$ && $t -gt 0 ]] && { printf '  🧠 RAM  '; ui::bar $(( (t - a) * 100 / t )) "$(ui::bw $(( $(dash::w) - 6 )))"; printf ' %s%3d%%%s %s%s%s\n' "$C_DIM" $(( (t - a) * 100 / t )) "$C_RESET" "$C_DIM" "$(ui::human_kb $((t-a)))" "$C_RESET"; }
  fi
  local b; b=$(device::battery 2>/dev/null) && { local pct st; IFS='|' read -r pct st _ <<<"$b"; [[ $pct =~ ^[0-9]+$ ]] && { printf '  🔋 BAT  '; ui::bar "$pct" "$(ui::bw $(( $(dash::w) - 14 )))" invert; printf ' %s%3d%%%s %s%s%s\n' "$C_DIM" "$pct" "$C_RESET" "$C_DIM" "$st" "$C_RESET"; }; }
  printf '  %s⏱  up %s%s\n' "$C_DIM" "$(dash::uptime)" "$C_RESET"
}
home::w_disk()    { printf '\n'; DASH_MAXDISK=2 dash::disk 2>/dev/null | sed -n '2,$p'; }
home::w_battery() { local b pct st temp; b=$(device::battery 2>/dev/null) || return; IFS='|' read -r pct st temp <<<"$b"; printf '\n  🔋 %s%% %s%s%s\n  ' "$pct" "$C_DIM" "${st}${temp:+ · ${temp}°C}" "$C_RESET"; ui::bar "$pct" "$(ui::bw $(( $(dash::w) - 6 )))" invert; printf '\n'; }
home::w_network() { local ip; ip=$(ui::lan_ip); printf '\n  📶 %s%s%s\n' "$C_DIM" "${ip:-offline}" "$C_RESET"; }
home::w_trend()   { local out; out=$(dash::trend 2>/dev/null) && printf '%s\n' "$out"; }
home::w_tip()     { local f="$NEBULA_HOME/assets/tips.txt"; [[ -s $f ]] || return; printf '\n'; viz::wrap "$(( $(dash::w) - 1 ))" "  ${C_DIM}💡 " "     ${C_DIM}" "$(shuf -n1 "$f" 2>/dev/null || head -1 "$f")"; printf '%s' "$C_RESET"; }
home::w_todo() {
  local f="$NEBULA_CFG/todo.md"; [[ -s $f ]] || return
  local rows; rows=$(awk '/^- \[ \]/{ line=$0; sub(/^- \[ \] /,"",line); r=3; if (line ~ /^\(H\)/) r=1; else if (line ~ /^\(M\)/) r=2; else if (line ~ /^\(L\)/) r=4; print r "\t" line }' "$f" | sort -n -s | head -3 | cut -f2-)
  [[ -n $rows ]] || return
  printf '\n  %s✅ To do%s\n' "$C_BOLD" "$C_RESET"
  local tw=$(( $(dash::w) - 6 )); (( tw < 12 )) && tw=12
  while IFS= read -r l; do l=$(viz::trunc "$l" "$(( tw ))"); l=${l/\(H\)/${C_RED}●${C_RESET}}; l=${l/\(M\)/${C_YELLOW}●${C_RESET}}; l=${l/\(L\)/${C_BLUE}●${C_RESET}}; printf '    %s\n' "$l"; done <<<"$rows"
}
home::w_reminders() {
  local f="$NEBULA_CFG/reminders"; [[ -s $f ]] || return
  local rows; rows=$(sort -t'|' -k2,2n "$f" | head -2); [[ -n $rows ]] || return
  printf '\n  %s⏰ Coming up%s\n' "$C_BOLD" "$C_RESET"
  local id ep pid text tw=$(( $(dash::w) - 18 )); (( tw < 10 )) && tw=10
  while IFS='|' read -r id ep pid text; do printf '    %s%s%s  %s\n' "$C_DIM" "$(date -d "@$ep" '+%a %H:%M' 2>/dev/null)" "$C_RESET" "$(viz::trunc "$text" "$tw")"; done <<<"$rows"
}
home::w_cached() {  # network widget from cache
  local w=$1 f age; f=$(home::cache "$w"); [[ -s $f ]] || return 0
  age=$(home::age "$w"); printf '\n'
  if [[ $w == news ]]; then home::fmt_news < "$f"; else ui::clip "$(dash::w)" < "$f"; fi
  [[ -n $age && $age != now ]] && printf '  %s· %s%s\n' "$C_DIM" "$age" "$C_RESET"
}
# news cache lines are "epoch<TAB>title" (older caches hold ready-made lines, shown as they are)
home::fmt_news() {
  local w ep t age room line; w=$(dash::w)
  while IFS=$'\t' read -r ep t; do
    if [[ $ep =~ ^[0-9]+$ && -n $t ]]; then
      age=""; (( ep > 0 )) && age=" · $(viz::ago "$ep")"
      room=$(( w - 5 - ${#age} )); (( room < 10 )) && { age=""; room=$(( w - 5 )); }
      printf '  %s▎%s %s%s%s\n' "$C_CYAN" "$C_RESET" "$(viz::trunc "$t" "$room")" "$C_DIM" "$age$C_RESET"
    else line=$ep${t:+$'\t'$t}; printf '%s\n' "$line" | ui::clip "$w"; fi
  done
}

home::widget() {
  case $1 in
    logo)      bash "$NEBULA_HOME/motd/motd.d/10-nebula-logo" ;;
    greeting)  home::w_greeting ;;   sysinfo)   home::w_sysinfo ;;   disk)    home::w_disk ;;
    battery)   home::w_battery ;;    network)   home::w_network ;;   todo)    home::w_todo ;;
    reminders) home::w_reminders ;;  tip)       home::w_tip ;;       trend)   home::w_trend ;;
    weather|crypto|news|sports) home::w_cached "$1" ;;
  esac
}

# ── render ──────────────────────────────────────────────────────────────
home::render() {  # home::render [noclear]
  home::load; local noclear=0; [[ ${1:-} == noclear ]] && noclear=1
  local widgets=${HC[widgets]} w compact=0
  [[ -f $NEBULA_CFG/compact ]] && compact=1
  (( compact )) && widgets="greeting sysinfo disk"        # lighter, but still shows status + storage
  (( ${HC[clear]} && ! noclear )) && [[ -t 1 ]] && printf '\033[H\033[2J'
  ui::resized
  local cols n gw; cols=$(ui::cols); read -r n gw < <(ui::grid_dims 42 3)
  local UI_W=$gw b
  ui::blocks_reset
  for w in $widgets; do
    case $w in
      logo|greeting|tip)                                   # full-width: flush the grid first, then print
        ui::blocks_flush "$n" 3 | ui::clip "$cols"; ui::blocks_reset
        home::widget "$w" | ui::clip "$cols" ;;
      *) b=$(home::widget "$w"); [[ -n ${b//[$'\n ']/} ]] && ui::blocks_add "$b" ;;
    esac
  done
  ui::blocks_flush "$n" 3 | ui::clip "$cols"
  printf '\n'
  # refresh stale network widgets in the background (never blocks the login)
  local need=()
  for w in weather crypto news sports; do
    [[ " $widgets " == *" $w "* ]] && home::stale "$w" && need+=("$w")
  done
  (( ${#need[@]} )) && ( NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" nohup bash "$NEBULA_HOME/lib/home-refresh.sh" "${need[@]}" >/dev/null 2>&1 & )
  return 0
}

home::refresh() {  # home::refresh [widgets…]  (foreground)
  home::load; mkdir -p "$NEBULA_CFG/cache"
  local ws=("$@"); (( ${#ws[@]} )) || ws=(weather crypto news sports)
  local w f tmp
  for w in "${ws[@]}"; do
    [[ " ${HC[widgets]} " == *" $w "* || $# -gt 0 ]] || continue
    f=$(home::cache "$w"); tmp="$f.tmp"; touch "$f.try"
    if "home::gen_$w" > "$tmp" 2>/dev/null && [[ -s $tmp ]]; then mv "$tmp" "$f"; [[ -t 1 ]] && ui::say_status OK "$w updated"
    else rm -f "$tmp"; [[ -t 1 ]] && ui::say_status WARN "$w: no data (offline, or missing curl/jq)"; fi
  done
}

# ── editor ──────────────────────────────────────────────────────────────
home::editor() {
  [[ -t 0 && -t 1 ]] || { ui::say_status WARN "The editor needs a terminal."; return 1; }
  home::load; [[ -f $NEBULA_CFG/home.conf ]] || home::save
  local cur=0
  while :; do
    home::load
    local -a on=(${HC[widgets]}) items=() kinds=() names=() w
    for w in "${on[@]}"; do items+=("$(( ${#names[@]} + 1 )). $w"$'\tON\tg'); kinds+=(on); names+=("$w"); done
    for w in $HOME_WIDGETS; do [[ " ${on[*]} " == *" $w "* ]] && continue; items+=("   $w"$'\toff\td'); kinds+=(off); names+=("$w"); done
    items+=("🎞  Preview now"$'\t'); kinds+=(act); names+=(preview)
    items+=("📦 Presets…"$'\t'); kinds+=(act); names+=(presets)
    items+=("🌤 Weather city"$'\t'"${HC[weather_city]:-auto}"); kinds+=(act); names+=(city)
    items+=("₿  Coins"$'\t'"${HC[crypto_coins]}"); kinds+=(act); names+=(coins)
    items+=("📰 News topic"$'\t'"${HC[news_topic]}"); kinds+=(act); names+=(topic)
    items+=("⚽ League"$'\t'"${HC[sports_league]:-none}"); kinds+=(act); names+=(league)
    items+=("⏲  Refresh every"$'\t'"$(( HC[ttl] / 60 )) min"); kinds+=(act); names+=(ttl)
    items+=("🧹 Clear screen at login"$'\t'"$([[ ${HC[clear]} == 1 ]] && echo ON || echo off)"); kinds+=(act); names+=(clear)
    items+=("🔄 Refresh network widgets"$'\t'); kinds+=(act); names+=(refresh)
    MENU_INFO="${C_DIM}Order: top → bottom${C_RESET}"; MENU_CUR=$cur
    menu::pick "🏠 Home screen" "Enter: add / edit · q: close" items || break
    cur=$MENU_IDX; MENU_INFO=""; w=${names[cur]}
    case ${kinds[cur]} in
      off) HC[widgets]="${HC[widgets]:+${HC[widgets]} }$w"; home::save ;;
      on)
        local -a opt=($'↑ Move up\t' $'↓ Move down\t' $'✖ Remove\t' $'← Back\t'); MENU_CUR=0; MENU_INFO="${C_BOLD}$w${C_RESET}"
        menu::pick "Edit '$w'" "Enter to choose" opt || { MENU_INFO=""; continue; }
        local i idx=-1; for i in "${!on[@]}"; do [[ ${on[i]} == "$w" ]] && idx=$i; done
        case $MENU_IDX in
          0) (( idx > 0 )) && { local t=${on[idx-1]}; on[idx-1]=${on[idx]}; on[idx]=$t; } ;;
          1) (( idx < ${#on[@]}-1 )) && { local t=${on[idx+1]}; on[idx+1]=${on[idx]}; on[idx]=$t; } ;;
          2) unset 'on[idx]'; on=("${on[@]}") ;;
        esac
        HC[widgets]="${on[*]}"; home::save; MENU_INFO="" ;;
      act)
        case $w in
          preview) home::render noclear; menu::wait ;;
          presets) local p; p=$(for x in $(home::presets); do printf '%-10s %s\n' "$x" "$(sed -n '1s/^# *//p' "$NEBULA_HOME/assets/home/$x.conf")"; done | pick::choose "Home preset") && home::apply_preset "${p%% *}" ;;
          city)   read -r -p "  City (empty = auto-detect): " c; home::valid weather_city "$c" && { HC[weather_city]=$c; home::save; rm -f "$(home::cache weather)"; } ;;
          coins)  read -r -p "  Coins, comma separated (btc,eth,sol): " c; c=${c,,}; c=${c// /}; home::valid crypto_coins "$c" && { HC[crypto_coins]=$c; home::save; rm -f "$(home::cache crypto)"; } ;;
          topic)  local t2; t2=$(printf '%s\n' world africa tech business science health sport hn | pick::choose "News topic") && { HC[news_topic]=$t2; home::save; rm -f "$(home::cache news)"; } ;;
          league) local lg; lg=$(sports::registry | awk -F'|' '{print $1 "  " $2}' | pick::choose "League") && { HC[sports_league]=${lg%% *}; home::save; rm -f "$(home::cache sports)"; } ;;
          ttl)    case ${HC[ttl]} in 300) HC[ttl]=900;; 900) HC[ttl]=3600;; *) HC[ttl]=300;; esac; home::save ;;
          clear)  [[ ${HC[clear]} == 1 ]] && HC[clear]=0 || HC[clear]=1; home::save ;;
          refresh) printf '\033[H\033[2J'; home::refresh weather crypto news sports; menu::wait ;;
        esac ;;
    esac
  done
  printf '\033[H\033[2J'
}

home::apply_preset() {
  local f="$NEBULA_HOME/assets/home/$1.conf"; [[ -f $f ]] || { ui::say_status ERR "No home preset '$1'. Try: home presets"; return 1; }
  home::load; local k v; while IFS='=' read -r k v; do [[ -z $k || $k == \#* ]] && continue; home::valid "$k" "$v" && HC[$k]=$v; done < "$f"
  home::save
}

cmd::home() {
  case "${1:-show}" in
    show|"")  home::render noclear ;;
    edit|editor|studio) home::editor ;;
    preset)   [[ -n ${2:-} ]] || { ui::say_status WARN "Usage: home preset <name>   (home presets)"; return 1; }
              home::apply_preset "$2" && { ui::say_status OK "Home screen: $2"; home::refresh 2>/dev/null >/dev/null; home::render noclear; } ;;
    presets|list) local p; printf "${C_CYAN}${C_BOLD}🏠 Home presets${C_RESET}\n"; for p in $(home::presets); do local lab; printf -v lab '%-10s' "$p"; ui::item "$lab" 10 "$(sed -n '1s/^# *//p' "$NEBULA_HOME/assets/home/$p.conf")"; done ;;
    refresh)  home::refresh; ;;
    off)      mkdir -p "$NEBULA_CFG"; touch "$NEBULA_CFG/home.off"; ui::say_status OK "Home screen hidden at login. Bring it back: home on" ;;
    on)       rm -f "$NEBULA_CFG/home.off"; ui::say_status OK "Home screen on." ;;
    set)      local k=${2:-} v=${*:3}; home::load; home::valid "$k" "$v" && { HC[$k]=$v; home::save; ui::say_status OK "$k = $v"; } || { ui::say_status ERR "Invalid setting. Keys: $HOME_KEYS"; return 1; } ;;
    *)        ui::say_status ERR "Usage: home [edit|preset <name>|presets|refresh|set <key> <value>|off|on]"; return 1 ;;
  esac
}
