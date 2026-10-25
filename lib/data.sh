#!/data/data/com.termux/files/usr/bin/env bash
# nebula — live data dashboards: crypto, news, sports
# Free, key-less public sources:  CoinGecko · BBC/HN RSS · ESPN scoreboards

# ════════════════════════════════════════════════════════════════════════
#  CRYPTO
# ════════════════════════════════════════════════════════════════════════
crypto::id() {
  case "${1,,}" in
    btc|bitcoin) echo bitcoin;; eth|ethereum) echo ethereum;; sol|solana) echo solana;;
    bnb) echo binancecoin;; xrp|ripple) echo ripple;; ada|cardano) echo cardano;;
    doge|dogecoin) echo dogecoin;; ton) echo the-open-network;; usdt|tether) echo tether;;
    usdc) echo usd-coin;; trx|tron) echo tron;; dot|polkadot) echo polkadot;;
    ltc|litecoin) echo litecoin;; shib) echo shiba-inu;; avax) echo avalanche-2;;
    link|chainlink) echo chainlink;; matic|pol) echo matic-network;; xlm|stellar) echo stellar;;
    *) viz::fetch "https://api.coingecko.com/api/v3/search?query=$(printf '%s' "$1" | sed 's/ /%20/g')" 2>/dev/null \
         | python3 "$NEBULA_HOME/lib/jx.py" coin-id 2>/dev/null ;;
  esac
}

crypto::sym() {  # currency → symbol
  case $1 in usd) echo '$';; eur) echo '€';; gbp) echo '£';; kes) echo 'KSh ';; ngn) echo '₦';;
    zar) echo 'R';; inr) echo '₹';; jpy) echo '¥';; *) echo "${1^^} ";; esac
}

crypto::top() {
  local cur=$1 sym; sym=$(crypto::sym "$cur")
  local body; body=$(viz::fetch "https://api.coingecko.com/api/v3/coins/markets?vs_currency=$cur&order=market_cap_desc&per_page=10&page=1&sparkline=true&price_change_percentage=24h,7d") \
    || { ui::say_status ERR "Couldn't reach CoinGecko (offline or rate-limited — try again in a minute)"; return 1; }
  python3 "$NEBULA_HOME/lib/jx.py" is-array <<<"$body" 2>/dev/null || { ui::say_status ERR "Unexpected reply from CoinGecko (rate limit?)"; return 1; }

  viz::title "📈 Crypto market" "${cur^^} · $(date +%H:%M)"
  local cols sw wide=0 nospark=0; cols=$(ui::cols); sw=$(( cols - 44 )); (( sw < 8 )) && sw=8; (( sw > 40 )) && sw=40
  (( cols >= 76 )) && wide=1; (( cols < 42 )) && nospark=1
  if (( wide )); then printf "${C_DIM} #  %-5s %12s  %9s  %-9s %s${C_RESET}\n" "Coin" "Price" "24h" "Mkt cap" "7 days"
  elif (( nospark )); then printf "${C_DIM} #  %-5s %11s  %9s${C_RESET}\n" "Coin" "Price" "24h"
  else printf "${C_DIM} #  %-5s %12s  %9s  %s${C_RESET}\n" "Coin" "Price" "24h" "7 days"; fi
  local total; total=$(python3 "$NEBULA_HOME/lib/jx.py" market-total <<<"$body")
  local i=0 sy price ch24 spark mc
  (( wide )) || sw=$(( cols - 36 )); (( sw < 8 )) && sw=8; (( sw > 14 )) && ! (( wide )) && sw=14
  while IFS=$'\037' read -r sy price ch24 mc spark; do
    i=$((i+1))
    if (( wide )); then
      printf " %-2s %-5s %12s  %s  %-9s %s\n" "$i" "${sy^^}" "$sym$(viz::money "$price")" "$(viz::pct "$ch24")" "$sym$(viz::short "$mc")" "$(tr ' ' '\n' <<<"$spark" | viz::spark "$sw")"
    elif (( nospark )); then
      printf " %-2s %-5s %11s  %s\n" "$i" "${sy^^}" "$sym$(viz::money "$price")" "$(viz::pct "$ch24")"
    else
      printf " %-2s %-5s %12s  %s  %s\n" "$i" "${sy^^}" "$sym$(viz::money "$price")" "$(viz::pct "$ch24")" "$(tr ' ' '\n' <<<"$spark" | viz::spark "$sw")"
    fi
  done < <(python3 "$NEBULA_HOME/lib/jx.py" market-rows <<<"$body")

  printf "\n${C_DIM}Market-cap share (top 10)${C_RESET}\n"
  python3 "$NEBULA_HOME/lib/jx.py" market-top5 <<<"$body" | while IFS=$'\037' read -r sy mc; do
    printf "  %-5s %s %s\n" "${sy^^}" "$(viz::bar "$mc" "$total" "$(ui::bw)")" "$(awk -v a="$mc" -v t="$total" 'BEGIN{printf "%.0f%%", a/t*100}')"
  done
  ui::hint "Detail view: crypto <coin> [--days 90] [--kes]"
}

crypto::coin() {
  local q=$1 cur=$2 days=$3 sym id; sym=$(crypto::sym "$cur")
  id=$(crypto::id "$q"); [[ -z $id ]] && { ui::say_status ERR "No coin found for '$q'"; return 1; }
  local m; m=$(viz::fetch "https://api.coingecko.com/api/v3/coins/markets?vs_currency=$cur&ids=$id&price_change_percentage=24h,7d,30d") \
    || { ui::say_status ERR "Couldn't reach CoinGecko"; return 1; }
  local row; row=$(python3 "$NEBULA_HOME/lib/jx.py" coin-row <<<"$m" 2>/dev/null)
  [[ -z $row ]] && { ui::say_status ERR "No data for '$q'"; return 1; }
  local name s rank price c24 c7 c30 hi lo mc vol ath
  IFS=$'\037' read -r name s rank price c24 c7 c30 hi lo mc vol ath <<<"$row"
  local ch; ch=$(viz::fetch "https://api.coingecko.com/api/v3/coins/$id/market_chart?vs_currency=$cur&days=$days") 2>/dev/null
  local cols; cols=$(ui::cols)
  local rows chh; rows=$(ui::rows)
  local cw=$(( cols - 14 )); (( cw > 120 )) && cw=120; (( cw < 16 )) && cw=16
  chh=$(( rows / 3 )); (( chh > 16 )) && chh=16; (( chh < 6 )) && chh=6

  viz::title "🪙 $name (${s^^})" "rank #$rank · ${cur^^}"
  printf "\n  ${C_BOLD}${C_WHITE}%s%s${C_RESET}   %s ${C_DIM}24h${C_RESET}\n" "$sym" "$(viz::money "$price")" "$(viz::pct "$c24")"
  printf "  ${C_DIM}7d${C_RESET} %s  ${C_DIM}·${C_RESET}  ${C_DIM}30d${C_RESET} %s\n\n" "$(viz::pct "$c7")" "$(viz::pct "$c30")"
  if [[ -n $ch ]]; then
    local t0 t1
    t0=$(python3 "$NEBULA_HOME/lib/jx.py" chart-t0 <<<"$ch"); t1=$(python3 "$NEBULA_HOME/lib/jx.py" chart-t1 <<<"$ch")
    python3 "$NEBULA_HOME/lib/jx.py" chart-prices <<<"$ch" | viz::area "$cw" "$chh" "$(date -d "@$t0" '+%d %b')" "$(date -d "@$t1" '+%d %b')"
  fi
  local pc rb; pc=$(awk -v p="$price" -v l="$lo" -v h="$hi" 'BEGIN{print (h>l)?(p-l)/(h-l)*100:50}')
  printf "\n  ${C_DIM}24h range${C_RESET}\n"
  if (( cols >= 56 )); then
    rb=$(( cols - 38 )); (( rb > 40 )) && rb=40
    printf "  %s ${C_DIM}low${C_RESET} %s ${C_DIM}high${C_RESET} %s\n" "$sym$(viz::money "$lo")" "$(viz::bar "$pc" 100 "$rb")" "$sym$(viz::money "$hi")"
  else
    printf "  ${C_DIM}low${C_RESET} %s   ${C_DIM}high${C_RESET} %s\n  %s\n" "$sym$(viz::money "$lo")" "$sym$(viz::money "$hi")" "$(viz::bar "$pc" 100 $(( cols - 4 )))"
  fi
  printf '\n'; viz::wrap $(( cols - 1 )) "  " "  " "${C_DIM}Market cap${C_RESET} $sym$(viz::short "$mc")   ${C_DIM}Volume${C_RESET} $sym$(viz::short "$vol")"
  printf "  ${C_DIM}All-time high${C_RESET} %s%s\n\n" "$sym" "$(viz::money "$ath")"
}

cmd::crypto() {
  cmd::_need_curl || return 1; viz::need_py || return 1
  local cur=usd days=30 coin=() a
  while (( $# )); do
    case "$1" in
      --usd|--eur|--gbp|--kes|--ngn|--zar|--inr|--jpy) cur=${1#--} ;;
      --days|-d) days=${2:-30}; shift ;;
      --days=*) days=${1#--days=} ;;
      top|list|market) ;;
      *) coin+=("$1") ;;
    esac; shift
  done
  [[ $days =~ ^[0-9]+$ ]] || days=30
  if (( ${#coin[@]} == 0 )); then crypto::top "$cur"; else crypto::coin "${coin[*]}" "$cur" "$days"; fi
}

# ════════════════════════════════════════════════════════════════════════
#  NEWS
# ════════════════════════════════════════════════════════════════════════
news::feed() {  # topic → "Label|url"
  case "$1" in
    world|"")  echo "BBC World|https://feeds.bbci.co.uk/news/world/rss.xml" ;;
    africa)    echo "BBC Africa|https://feeds.bbci.co.uk/news/world/africa/rss.xml" ;;
    tech)      echo "BBC Tech|https://feeds.bbci.co.uk/news/technology/rss.xml" ;;
    business)  echo "BBC Business|https://feeds.bbci.co.uk/news/business/rss.xml" ;;
    science)   echo "BBC Science|https://feeds.bbci.co.uk/news/science_and_environment/rss.xml" ;;
    health)    echo "BBC Health|https://feeds.bbci.co.uk/news/health/rss.xml" ;;
    sport)     echo "BBC Sport|https://feeds.bbci.co.uk/sport/rss.xml" ;;
    hn|hacker) echo "Hacker News|https://hnrss.org/frontpage?count=15" ;;
    *) return 1 ;;
  esac
}

# RSS → TSV: title \t link \t epoch \t description
news::parse() {
  tr '\n\r' '  ' | sed 's#</item>#\n#g; s#</entry>#\n#g' | awk '
    function tag(s, t,   x, e) { if (!match(s, "<" t "[^>]*>")) return ""; x = substr(s, RSTART + RLENGTH); e = index(x, "</" t ">"); if (!e) return ""
      x = substr(x, 1, e - 1); gsub(/<!\[CDATA\[|\]\]>/, "", x); gsub(/<[^>]+>/, "", x); gsub(/\037/, " ", x); gsub(/^ +| +$/, "", x); return x }
    /<item[ >]|<entry[ >]/ { match($0, /<item[ >]|<entry[ >]/); $0 = substr($0, RSTART); t = tag($0, "title"); l = tag($0, "link"); d = tag($0, "pubDate"); if (d == "") d = tag($0, "updated")
      s = tag($0, "description"); if (s == "") s = tag($0, "summary"); if (t != "") print t "\037" l "\037" d "\037" s }' \
  | sed -e 's/&amp;/\&/g; s/&quot;/"/g; s/&#39;/'"'"'/g; s/&apos;/'"'"'/g; s/&#8217;/’/g; s/&#8216;/‘/g; s/&#8220;/“/g; s/&#8221;/”/g; s/&#8211;/–/g; s/&#8212;/—/g; s/&lt;/</g; s/&gt;/>/g; s/&nbsp;/ /g'
}

news::list() {
  local topic=$1 n=$2 feed=$3 label url
  if [[ -n $feed ]]; then label="Custom feed"; url=$feed
  else local f; f=$(news::feed "$topic") || { ui::say_status ERR "Unknown topic '$topic'. Try: news topics"; return 1; }
    label=${f%%|*}; url=${f#*|}; fi
  local body; body=$(curl -fsSL --max-time 12 -A 'nebula-termux' "$url") || { ui::say_status ERR "Couldn't reach $label (offline?)"; return 1; }
  local rows; rows=$(news::parse <<<"$body" | head -n "$n")
  [[ -z $rows ]] && { ui::say_status ERR "No stories found in that feed"; return 1; }

  local cols; cols=$(ui::cols)
  mkdir -p "$NEBULA_CFG"; : > "$NEBULA_CFG/.news_last"
  viz::title "📰 ${topic:-world} news" "$label · $(date +%H:%M)"

  # trending words (data panel)
  local words; words=$(awk -F'\037' 'BEGIN{split("the a an and for with from that this are was were has have not but over after into amid says say new will can its their about more than what when who how why you your they them been being also out off our all one two", sw, " "); for(i in sw) stop[sw[i]]=1}
    { t=tolower($1); gsub(/[^a-z ]/, " ", t); n=split(t, w, " "); for(i=1;i<=n;i++) if (length(w[i])>=4 && !(w[i] in stop)) c[w[i]]++ }
    END { for (k in c) if (c[k]>1) print c[k], k }' <<<"$rows" | sort -rn | head -4)
  if [[ -n $words ]]; then
    printf "\n${C_DIM}🔥 Trending in these headlines${C_RESET}\n"
    local mx; mx=$(head -1 <<<"$words" | cut -d' ' -f1)
    while read -r cnt w; do printf "  %-12s %s ${C_DIM}%s${C_RESET}\n" "$w" "$(viz::bar "$cnt" "$mx" 10 "$C_YELLOW")" "$cnt"; done <<<"$words"
  fi

  local gn gw; read -r gn gw < <(ui::grid_dims 46 3)
  local UI_W=$gw; ui::blocks_reset
  local i=0 title link date desc ep col age card
  while IFS=$'\037' read -r title link date desc; do
    i=$((i+1))
    ep=$(date -d "$date" +%s 2>/dev/null || echo 0)
    age=""; col=$C_DIM
    if (( ep > 0 )); then age=$(viz::ago "$ep"); d=$(( $(date +%s) - ep ))
      (( d < 3600 )) && col=$C_GREEN || { (( d < 21600 )) && col=$C_YELLOW; }; fi
    printf '%s\037%s\037%s\037%s\037%s\n' "$i" "$title" "$link" "$desc" "$label" >> "$NEBULA_CFG/.news_last"
    card=$(
      printf '\n'
      viz::wrap $((UI_W-5)) " ${col}▎${C_RESET} ${C_BOLD}$i  " " ${col}▎${C_RESET}    " "$title$C_RESET"
      printf " ${col}▎${C_RESET}    ${C_DIM}%s%s${C_RESET}\n" "$label" "${age:+ · $age}"
      [[ -n $desc ]] && viz::wrap $((UI_W-7)) " ${col}▎${C_RESET}    $C_DIM" " ${col}▎${C_RESET}    " "$(viz::trunc "$desc" 110)$C_RESET"
    )
    ui::blocks_add "$card"
  done <<<"$rows"
  ui::blocks_flush "$gn" 3 | ui::clip "$(ui::cols)"
  ui::hint "news <n> details · news open <n> · news ai <n> · news topics"
}

news::item() { awk -F'\037' -v n="$1" '$1==n{print; exit}' "$NEBULA_CFG/.news_last" 2>/dev/null; }

cmd::news() {
  cmd::_need_curl || return 1
  local topic="" n=6 feed="" sub="" arg=""; (( $(ui::cols) >= 90 )) && n=9
  while (( $# )); do
    case "$1" in
      topics) sub=topics ;;
      open)   sub=open; arg=${2:-}; shift ;;
      ai)     sub=ai;   arg=${2:-}; shift ;;
      -n)     n=${2:-6}; shift ;;
      --feed) feed=${2:-}; shift ;;
      [0-9]*) sub=show; arg=$1 ;;
      *)      topic=$1 ;;
    esac; shift
  done
  case $sub in
    topics) printf "${C_CYAN}Topics:${C_RESET} world · africa · tech · business · science · health · sport · hn\n  ${C_DIM}or: news --feed <rss-url>${C_RESET}\n"; return ;;
    show|open|ai)
      local row; row=$(news::item "$arg"); [[ -z $row ]] && { ui::say_status WARN "Run 'news' first, then pick a number."; return 1; }
      local t l d lab; IFS=$'\037' read -r _ t l d lab <<<"$row"
      case $sub in
        show) local cols=$(ui::cols); printf '\n'; viz::wrap $((cols-2)) "  $C_BOLD" "  " "$t$C_RESET"
              printf "  ${C_DIM}%s${C_RESET}\n\n" "$lab"; [[ -n $d ]] && viz::wrap $((cols-2)) "  " "  " "$d"
              printf "\n  ${C_BLUE}${C_UNDER}%s${C_RESET}\n\n" "$l" ;;
        open) if command -v termux-open-url >/dev/null 2>&1; then termux-open-url "$l"; else printf '%s\n' "$l"; fi ;;
        ai)   cmd::_need_tgpt || return 1; printf "${C_BLUE}${C_BOLD}🤖 Nebula AI${C_RESET}\n"
              ai::_think "Explain this news story simply in 3 bullet points and say why it matters. Headline: $t. Summary: $d" ;;
      esac; return ;;
  esac
  news::list "$topic" "$n" "$feed"
}

# ════════════════════════════════════════════════════════════════════════
#  SPORTS  (ESPN public scoreboards)
# ════════════════════════════════════════════════════════════════════════
sports::registry() { cat "$NEBULA_HOME/assets/leagues.txt" | grep -v '^#'; }

sports::choose() {  # sports::choose "title" < lines "label|key"  → prints key
  local title=$1 items=() keys=() l
  while IFS= read -r l; do [[ -z $l ]] && continue; items+=("${l%%|*}"); keys+=("${l##*|}"); done
  if declare -F pick::choose >/dev/null 2>&1 && [[ -t 0 || -r /dev/tty ]]; then
    local sel; sel=$(printf '%s\n' "${items[@]}" | pick::choose "$title") || return 1
    local i; for i in "${!items[@]}"; do [[ ${items[i]} == "$sel" ]] && { echo "${keys[i]}"; return 0; }; done
    return 1
  fi
  local i=1; for l in "${items[@]}"; do printf '  %2d. %s\n' "$i" "$l" >&2; i=$((i+1)); done
  local pick; read -r -p "  $title [1] " pick </dev/tty; pick=${pick:-1}
  [[ $pick =~ ^[0-9]+$ ]] && echo "${keys[pick-1]}"
}

sports::resolve() {  # tokens… → sets S_KEY S_NAME S_SPORT S_PATH
  S_KEY=""; local tok line k n sp path al
  for tok in "$@"; do
    while IFS='|' read -r k n sp path al; do
      if [[ $tok == "$k" ]] || [[ " $al " == *" $tok "* ]] || [[ ${n,,} == "$tok" ]]; then
        S_KEY=$k; S_NAME=$n; S_SPORT=$sp; S_PATH=$path; return 0; fi
    done < <(sports::registry)
  done
  return 1
}

sports::scoreboard() {
  local path=$1 name=$2 date=$3
  local url="https://site.api.espn.com/apis/site/v2/sports/$path/scoreboard"
  [[ -n $date ]] && url+="?dates=$date"
  local body; body=$(viz::fetch "$url") || { ui::say_status ERR "Couldn't reach the scores service (offline?)"; return 1; }
  local rows; rows=$(python3 "$NEBULA_HOME/lib/jx.py" sports-rows <<<"$body" 2>/dev/null)
  local dlabel; dlabel=$( [[ -n $date ]] && date -d "${date:0:8}" '+%a %d %b' || date '+%a %d %b' )
  viz::title "$(sports::icon "$S_SPORT") $name" "$dlabel"
  if [[ -z $rows ]]; then printf '\n  %sNo matches on this date.%s\n  %sTry: sports %s next  ·  sports %s table%s\n\n' "$C_DIM" "$C_RESET" "$C_DIM" "$S_KEY" "$S_KEY" "$C_RESET"; return 0; fi

  local cols=$(ui::cols) grp gn gw; read -r gn gw < <(ui::grid_dims 38 3)
  local UI_W=$gw
  for grp in in pre post; do
    local label color count=0; ui::blocks_reset
    case $grp in in) label="LIVE"; color=$C_RED;; pre) label="UPCOMING"; color=$C_YELLOW;; post) label="FINISHED"; color=$C_GREEN;; esac
    while IFS=$'\037' read -r dt st det clk hn hab hs an aab as ev; do
      [[ $st == "$grp" ]] || continue
      (( count == 0 )) && printf '\n%s%s%s\n' "$color$C_BOLD" "$label" "$C_RESET"
      count=$((count+1))
      local when
      case $grp in
        pre)  when=$(date -d "$dt" '+%H:%M' 2>/dev/null || echo "$det") ;;
        in)   when="${det:-$clk}" ;;
        post) when="${det:-FT}" ;;
      esac
      local mx=1; [[ $hs =~ ^[0-9]+$ ]] && (( hs > mx )) && mx=$hs; [[ $as =~ ^[0-9]+$ ]] && (( as > mx )) && mx=$as
      local hbold="" abold=""
      if [[ $grp == post && $hs =~ ^[0-9]+$ && $as =~ ^[0-9]+$ ]]; then (( hs > as )) && hbold=$C_BOLD; (( as > hs )) && abold=$C_BOLD; fi
      local card tw=$(( UI_W - 14 )); (( tw < 10 )) && tw=10
      card=$(
        printf " %s▎%s %s%-*s%s %s%s%s\n" "$color" "$C_RESET" "$hbold" "$tw" "$(viz::trunc "$hn" "$tw")" "$C_RESET" "$C_BOLD" "${hs}" "$C_RESET"
        printf " %s▎%s %s%-*s%s %s%s%s   %s%s%s\n" "$color" "$C_RESET" "$abold" "$tw" "$(viz::trunc "$an" "$tw")" "$C_RESET" "$C_BOLD" "${as}" "$C_RESET" "$C_DIM" "$when" "$C_RESET"
        if [[ $grp != pre && $hs =~ ^[0-9]+$ && $as =~ ^[0-9]+$ && $S_SPORT == soccer ]]; then
          printf "   %s %s\n" "$(viz::bar "$hs" "$mx" 8 "$C_GREEN")" "$(viz::bar "$as" "$mx" 8 "$C_BLUE")"
        fi
      )
      ui::blocks_add "$card"
    done <<<"$rows"
    ui::blocks_flush "$gn" 3 | ui::clip "$cols"
  done
  ui::hint "sports $S_KEY table · next · yesterday · live"; printf '\n'
}

sports::icon() { case $1 in soccer) echo ⚽;; basketball) echo 🏀;; "american football") echo 🏈;; hockey) echo 🏒;; baseball) echo ⚾;; racing) echo 🏎;; tennis) echo 🎾;; *) echo 🏆;; esac; }

sports::table() {
  local path=$1 name=$2
  local sp=${path%%/*} lg=${path#*/}
  local body; body=$(viz::fetch "https://site.api.espn.com/apis/v2/sports/$sp/$lg/standings") || { ui::say_status ERR "Couldn't reach the standings service"; return 1; }
  local rows; rows=$(python3 "$NEBULA_HOME/lib/jx.py" standings <<<"$body" 2>/dev/null)
  viz::title "$(sports::icon "$S_SPORT") $name — table" "$(date '+%d %b')"
  [[ -z $rows ]] && { printf '\n  %sNo standings available for this competition.%s\n\n' "$C_DIM" "$C_RESET"; return 0; }
  local cols=$(ui::cols) soccer=0 g lastg="__" gi=0
  [[ $S_SPORT == soccer ]] && soccer=1
  # columns by available width: full → no points bar → no goal difference
  local show_bar=1 show_gd=1 tw
  tw=$(( cols - 33 )); if (( tw < 10 )); then show_bar=0; tw=$(( cols - 27 )); fi
  if (( tw < 10 )); then show_gd=0; tw=$(( cols - 23 )); fi
  (( tw < 4 )) && tw=4; (( tw > 28 )) && tw=28
  (( soccer )) || { tw=$(( cols - 17 )); (( tw < 8 )) && tw=8; (( tw > 28 )) && tw=28; }
  local total; total=$(wc -l <<<"$rows")
  local maxpts; maxpts=$(awk -F'\037' '{ if ($9>m) m=$9 } END{print m+0}' <<<"$rows")
  local gname team rank gp w d l gd pts pct
  while IFS=$'\037' read -r gname team rank gp w d l gd pts pct; do
    if [[ $gname != "$lastg" ]]; then
      [[ -n $gname ]] && printf '\n%s%s%s\n' "$C_BOLD$C_CYAN" "$gname" "$C_RESET"
      if (( soccer )); then
        printf "${C_DIM}  # %-${tw}s  P  W  D  L" "Team"; (( show_gd )) && printf "   GD"; printf "  Pts${C_RESET}\n"
      else printf "${C_DIM}  # %-${tw}s  W   L   PCT${C_RESET}\n" "Team"; fi
      lastg=$gname; gi=0
    fi
    gi=$((gi+1)); local mark=" "
    if (( soccer )); then
      (( rank <= 4 )) && mark="${C_GREEN}●${C_RESET}"; (( rank > total - 3 && total > 12 )) && mark="${C_RED}●${C_RESET}"
      printf " %s%2d %-${tw}s %2d %2d %2d %2d" "$mark" "$rank" "$(viz::trunc "$team" "$tw")" "$gp" "$w" "$d" "$l"
      (( show_gd )) && printf " %+4d" "$gd"
      printf "  ${C_BOLD}%3d${C_RESET}" "$pts"
      (( show_bar )) && printf " %s" "$(viz::bar "$pts" "$maxpts" 5)"
      printf '\n'
    else
      printf "  %2d %-${tw}s %2d  %2d  %.3f\n" "$rank" "$(viz::trunc "$team" "$tw")" "$w" "$l" "$pct"
    fi
  done < <(sort -t$'\037' -k1,1 -k3,3n <<<"$rows")
  (( soccer )) && printf "\n${C_GREEN}●${C_RESET}${C_DIM} top 4   ${C_RESET}${C_RED}●${C_RESET}${C_DIM} bottom 3${C_RESET}\n"
  printf '\n'
}

cmd::sports() {
  cmd::_need_curl || return 1; viz::need_py || return 1
  local view=scores date="" toks=() sportword="" t
  for t in "$@"; do
    t=${t,,}
    case $t in
      table|standings|league|tables|positions) view=table ;;
      live|now) view=live ;;
      next|upcoming|fixtures|tomorrow) view=next ;;
      yesterday|results|last) view=yesterday ;;
      today|match|matches|games|game|scores|score|fixture|on) ;;
      football|soccer) sportword=soccer ;;
      basketball) sportword=basketball ;;
      [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) date=${t//-/} ;;
      [0-9]*) date=$t ;;
      *) toks+=("$t") ;;
    esac
  done
  if ! sports::resolve "${toks[@]}" 2>/dev/null; then
    # not named → narrow by sport, then ask
    local menu
    if [[ -n $sportword ]]; then menu=$(sports::registry | awk -F'|' -v s="$sportword" '$3==s{print $2 "|" $1}')
    else menu=$(sports::registry | awk -F'|' '{print $2 " (" $3 ")|" $1}'); fi
    local last=""; [[ -f $NEBULA_CFG/sports.last ]] && last=$(<"$NEBULA_CFG/sports.last")
    local key; key=$(sports::choose "Which league?" <<<"$menu") || { ui::say_status WARN "No league chosen."; return 1; }
    sports::resolve "$key" || return 1
  fi
  mkdir -p "$NEBULA_CFG"; echo "$S_KEY" > "$NEBULA_CFG/sports.last"
  case $view in
    table)     sports::table "$S_PATH" "$S_NAME" ;;
    live)      sports::scoreboard "$S_PATH" "$S_NAME" "" ;;
    yesterday) sports::scoreboard "$S_PATH" "$S_NAME" "$(date -d yesterday +%Y%m%d)" ;;
    next)      sports::scoreboard "$S_PATH" "$S_NAME" "$(date -d tomorrow +%Y%m%d)" ;;
    *)         sports::scoreboard "$S_PATH" "$S_NAME" "$date" ;;
  esac
}
