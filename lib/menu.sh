#!/data/data/com.termux/files/usr/bin/env bash
# nebula — arrow-key menu engine (used by `settings`)
#
#   items=( $'label\tright text\tcolor' ... )     color: g y r d (optional)
#   MENU_CUR=0  MENU_INFO=$'line1\nline2'
#   menu::pick "Title" "hint" items   → 0 + MENU_IDX on Enter, 1 on back/q
#
# Keys: ↑/↓ (or j/k) move · Enter/Space select · q / Esc / ← back

MENU_CUR=0; MENU_IDX=-1; MENU_INFO=""

menu::_key() {  # → sets MENU_KEY to up|down|enter|back|other
  local k rest
  IFS= read -rsn1 k </dev/tty; local rc=$?
  (( rc > 128 )) && { MENU_KEY=resize; return; }            # a resize interrupted the read → just redraw
  (( rc != 0 )) && { MENU_KEY=back; return; }
  if [[ $k == $'\033' ]]; then
    IFS= read -rsn2 -t 0.05 rest </dev/tty || rest=""
    case "$rest" in
      '[A'|OA) MENU_KEY=up ;;   '[B'|OB) MENU_KEY=down ;;
      '[D'|OD) MENU_KEY=back ;; '[C'|OC) MENU_KEY=enter ;;
      '')      MENU_KEY=back ;;  *) MENU_KEY=other ;;
    esac
    return
  fi
  case "$k" in
    k) MENU_KEY=up ;; j) MENU_KEY=down ;; ''|' ') MENU_KEY=enter ;;
    q|Q|h) MENU_KEY=back ;; *) MENU_KEY=other ;;
  esac
}

# menu::_vw <text> → number of terminal cells (emoji and other wide symbols count 2)
menu::_vw() {
  local t=$1 w=${#1} k
  if [[ $t == *[^\ -~]* ]]; then for k in $UI_WIDE; do [[ $t == *"$k"* ]] && { local r=${t//"$k"/}; w=$(( w + (${#t} - ${#r}) / ${#k} )); t=$r; }; done; fi
  printf '%s' "$w"
}

menu::pick() {
  local title=$1 hint=$2; local -n _items=$3
  local N=${#_items[@]} rows cols H top=0 i label right col ptr line avail lw
  (( N == 0 )) && return 1
  (( MENU_CUR >= N )) && MENU_CUR=$((N-1)); (( MENU_CUR < 0 )) && MENU_CUR=0
  local B=$'\033[1m' DIM=$'\033[2m' CY=$'\033[38;5;51m' RS=$'\033[0m'
  local G=$'\033[38;5;120m' Y=$'\033[38;5;221m' R=$'\033[38;5;203m'
  printf '\033[?25l'; trap 'printf "\033[?25h"' EXIT INT TERM
  trap 'ui::resized' WINCH
  while :; do
    rows=$(ui::rows); cols=$(ui::cols)
    local info_lines=0; [[ -n $MENU_INFO ]] && info_lines=$(( $(grep -c '' <<<"$MENU_INFO") + 1 ))
    H=$(( rows - 5 - info_lines )); (( H > 16 )) && H=16; (( H < 3 )) && H=3; (( H > N )) && H=$N
    (( MENU_CUR < top )) && top=$MENU_CUR
    (( MENU_CUR >= top + H )) && top=$(( MENU_CUR - H + 1 ))
    printf '\033[H\033[2J'
    while (( $(menu::_vw "$title") > cols - 1 )); do title=${title%?}; done
    printf '%s%s%s\n' "$B$CY" "$title" "$RS"
    printf '%s%s%s\n' "$DIM" "${hint:0:cols-1}" "$RS"
    [[ -n $MENU_INFO ]] && printf '\n%s\n' "$MENU_INFO"
    printf '\n'
    for (( i=top; i<top+H; i++ )); do
      # split on tabs WITHOUT collapsing empty fields
      local _it=${_items[i]} _rest
      label=${_it%%$'\t'*}; right=""; col=""
      if [[ $_it == *$'\t'* ]]; then
        _rest=${_it#*$'\t'}; right=${_rest%%$'\t'*}
        [[ $_rest == *$'\t'* ]] && col=${_rest#*$'\t'}
      fi
      lw=$(menu::_vw "$label")
      if (( lw > cols - 6 )); then while (( lw > cols - 7 )); do label=${label%?}; lw=$(menu::_vw "$label"); done; label+="…"; lw=$(( lw + 1 )); fi
      ptr=" "; (( i == MENU_CUR )) && ptr="❯"
      avail=$(( cols - lw - 6 ))
      case $col in g) col=$G;; y) col=$Y;; r) col=$R;; d) col=$DIM;; *) col="";; esac
      if (( i == MENU_CUR )); then printf '%s%s %s%s' "$B$CY" "$ptr" "$label" "$RS"
      else printf '%s %s' "$ptr" "$label"; fi
      (( avail > 2 )) && [[ -n $right ]] && printf '  %s%s%s' "$col" "${right:0:avail}" "$RS"
      printf '\n'
    done
    printf '\n%s%d/%d%s\n' "$DIM" $((MENU_CUR+1)) "$N" "$RS"
    menu::_key
    case $MENU_KEY in
      up)    MENU_CUR=$(( (MENU_CUR - 1 + N) % N )) ;;
      down)  MENU_CUR=$(( (MENU_CUR + 1) % N )) ;;
      enter) MENU_IDX=$MENU_CUR; printf '\033[?25h'; trap - EXIT INT TERM WINCH; return 0 ;;
      back)  MENU_IDX=-1; printf '\033[?25h'; trap - EXIT INT TERM WINCH; return 1 ;;
    esac
  done
}

menu::wait() { printf '\n%s  press any key…%s' "${C_DIM:-}" "${C_RESET:-}"; IFS= read -rsn1 </dev/tty; }
