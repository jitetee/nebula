#!/usr/bin/env bash
# nebula pick — Nebula's own fuzzy picker (no fzf, written from scratch).
#
#   candidates | pick.sh "prompt"        → selected line on stdout (exit 1 = cancelled)
#   PICK_QUERY=foo        start with a query
#   PICK_INLINE_ABOVE=1   draw on a fresh line below the cursor (zle widgets)
#   source pick.sh   →   pick::choose "prompt"   (same, as a function)
#
# Keys: type to filter · ↑/↓ (Ctrl-P/N) move · PgUp/PgDn · Enter or Tab select
#       Esc / Ctrl-C cancel · Backspace · Ctrl-U clear · Ctrl-W delete word
#
# Matching: every space-separated word must match; substring hits beat scattered
# letters, word starts and file-name hits score higher, shorter lines win ties.

PICK_AWK='
BEGIN { nt = split(tolower(Q), tok, " ") }
{
  line = $0; low = tolower(line); total = 0; ok = 1
  base = low; sub(/.*\//, "", base)
  for (t = 1; t <= nt; t++) {
    q = tok[t]; s = 0
    p = index(low, q)
    if (p > 0) {
      s = 100 - 10 * p / (length(low) + 1)
      prev = (p > 1) ? substr(low, p - 1, 1) : " "
      if (prev ~ /[ \/_.-]/) s += 25
      b = index(base, q); if (b > 0) { s += 20; if (b == 1) s += 30 }
    } else {
      pos = 0; last = 0; s = 40; nq = length(q)
      for (i = 1; i <= nq; i++) {
        c = substr(q, i, 1); j = index(substr(low, pos + 1), c)
        if (j == 0) { ok = 0; break }
        pos += j
        if (last && pos == last + 1) s += 6
        prev = (pos > 1) ? substr(low, pos - 1, 1) : " "
        if (prev ~ /[ \/_.-]/) s += 8
        gap = pos - last - 1; if (last && gap > 0) s -= (gap > 8 ? 8 : gap)
        last = pos
      }
      if (!ok) break
    }
    total += s
  }
  if (ok) printf "%.2f\t%s\n", total - length(line) / 20, line
}'

# pick::_marks <text> <query>  → space-separated 0-based indexes to highlight
pick::_marks() {
  local text=${1,,} tok pos i j c n=${#1} out=""
  local -a idx=()
  for tok in ${2,,}; do
    local rest=${text}
    if [[ $text == *"$tok"* ]]; then
      local pre=${text%%"$tok"*}; pos=${#pre}
      for ((i=0;i<${#tok};i++)); do idx+=($((pos+i))); done
    else
      pos=0
      for ((i=0;i<${#tok};i++)); do
        c=${tok:i:1}; local r=${text:pos}
        [[ $r == *"$c"* ]] || break
        local pre=${r%%"$c"*}; pos=$((pos+${#pre})); idx+=($pos); pos=$((pos+1))
      done
    fi
  done
  printf '%s ' "${idx[@]}"
}

pick::choose() {
  local prompt=${1:-Pick} query=${PICK_QUERY:-}
  local items; items=$(mktemp "${TMPDIR:-/tmp}/nebula-pick.XXXXXX") || return 1
  head -n 30000 > "$items"
  local total; total=$(wc -l < "$items")
  (( total == 0 )) && { rm -f "$items"; return 1; }
  exec 3<>/dev/tty || { rm -f "$items"; return 1; }

  local rows cols H cur=0 top=0 n=0 key rest krc result=1 above=${PICK_INLINE_ABOVE:-0}
  local -a MATCH=()
  read -r rows cols < <(stty size <&3 2>/dev/null || echo "24 60")
  H=$(( rows - 5 )); (( H > 12 )) && H=12; (( H < 3 )) && H=3
  local B=$'\033[1m' DIM=$'\033[2m' CY=$'\033[38;5;51m' YL=$'\033[1;38;5;221m' RS=$'\033[0m' SEL=$'\033[48;5;236m'

  filter() {
    if [[ -z ${query// } ]]; then mapfile -t MATCH < <(head -n 300 "$items")
    else mapfile -t MATCH < <(awk -v Q="$query" "$PICK_AWK" "$items" | sort -t$'\t' -k1,1nr -s | head -n 300 | cut -f2-)
    fi
    n=${#MATCH[@]}; (( cur >= n )) && cur=$(( n > 0 ? n - 1 : 0 )); (( cur < 0 )) && cur=0
  }

  draw() {
    local out="" i line text marks m j ch run styled w=$(( cols - 4 ))
    (( cur < top )) && top=$cur; (( cur >= top + H )) && top=$(( cur - H + 1 )); (( top < 0 )) && top=0
    local cnt="$n/$total"
    out+=$'\r\033[K'"${CY}${B}${prompt}${RS} ${CY}❯${RS} ${query}${DIM}"
    out+=$'\0337'"${RS}"
    for (( i=top; i<top+H; i++ )); do
      out+=$'\n\033[K'
      (( i >= n )) && continue
      text=${MATCH[i]}; (( ${#text} > w )) && text="${text:0:w-1}…"
      declare -A mk=(); marks=""
      [[ -n ${query// } ]] && marks=$(pick::_marks "$text" "$query")
      for m in $marks; do mk[$m]=1; done
      styled=""; run=0
      for (( j=0; j<${#text}; j++ )); do
        ch=${text:j:1}
        if [[ -n ${mk[$j]:-} ]]; then styled+="${YL}${ch}${RS}"; (( i == cur )) && styled+="$SEL"; else styled+="$ch"; fi
      done
      unset mk
      if (( i == cur )); then out+="${SEL}${CY}❯ ${RS}${SEL}${styled}${RS}"; else out+="  ${styled}"; fi
    done
    local hint="↑↓ move · Enter/Tab select · Esc cancel"; (( cols < 52 )) && hint="↑↓ · Enter · Esc"
    out+=$'\n\033[K'"${DIM}${cnt}  ${hint:0:cols-${#cnt}-3}${RS}"
    out+=$'\033['"$((H+1))"$'A\r\0338'
    printf '%s' "$out" >&3
  }

  # reserve space and hide the cursor
  (( above )) && printf '\n' >&3
  local k; for (( k=0; k<H+2; k++ )); do printf '\n' >&3; done
  printf '\033[%dA\033[?25l' $((H+2)) >&3
  trap 'printf "\033[?25h" >&3 2>/dev/null' EXIT
  trap ':' WINCH

  filter; draw
  while :; do
    IFS= read -rsn1 -u 3 key; krc=$?
    if (( krc > 128 )); then                                   # terminal resized → re-measure and redraw
      read -r rows cols < <(stty size <&3 2>/dev/null || echo "24 60")
      H=$(( rows - 5 )); (( H > 12 )) && H=12; (( H < 3 )) && H=3
      (( H > total + 0 )) && true
      printf '\033[J' >&3; draw; continue
    fi
    (( krc != 0 )) && break
    if [[ $key == $'\033' ]]; then
      IFS= read -rsn2 -t 0.04 -u 3 rest || rest=""
      case "$rest" in
        '[A'|OA) key=UP ;; '[B'|OB) key=DOWN ;; '[5') read -rsn1 -t 0.04 -u 3 _; key=PGUP ;;
        '[6') read -rsn1 -t 0.04 -u 3 _; key=PGDN ;; '[H'|OH) key=HOME ;; '[F'|OF) key=END ;;
        '') key=ESC ;; *) key=IGNORE ;;
      esac
    fi
    case "$key" in
      UP|$'\020')   (( cur > 0 )) && cur=$((cur-1)) ;;
      DOWN|$'\016') (( cur < n-1 )) && cur=$((cur+1)) ;;
      PGUP)  cur=$(( cur - H < 0 ? 0 : cur - H )) ;;
      PGDN)  cur=$(( cur + H > n-1 ? n-1 : cur + H )) ;;
      HOME)  cur=0 ;; END) cur=$((n-1)) ;;
      ''|$'\t') (( n > 0 )) && { result=0; break; } ;;
      ESC|$'\003'|$'\007') break ;;
      $'\177'|$'\b') query=${query%?}; cur=0; filter ;;
      $'\025') query=""; cur=0; filter ;;
      $'\027') query=${query% *}; [[ $query == *" "* ]] || query=""; cur=0; filter ;;
      IGNORE) ;;
      *) if [[ $key == [[:print:]] ]]; then query+=$key; cur=0; filter; fi ;;
    esac
    draw
  done

  printf '\r\033[J\033[?25h' >&3
  (( above )) && printf '\033[1A' >&3
  trap - EXIT
  exec 3>&-
  if (( result == 0 )); then printf '%s\n' "${MATCH[cur]}"; fi
  rm -f "$items"
  return $result
}

# run directly: candidates on stdin
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then pick::choose "${1:-Pick}"; exit $?; fi
