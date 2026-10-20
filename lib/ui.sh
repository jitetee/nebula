#!/data/data/com.termux/files/usr/bin/env bash
[[ -r "${NEBULA_HOME:-.}/lib/layout.sh" ]] && source "${NEBULA_HOME:-.}/lib/layout.sh"
# nebula — UI helpers (colors, banners, ls wrappers)

# --- colors ---
export C_RESET=$'\033[0m'
export C_BOLD=$'\033[1m'
export C_DIM=$'\033[2m'
export C_RED=$'\033[38;5;203m'
export C_GREEN=$'\033[38;5;120m'
export C_YELLOW=$'\033[38;5;221m'
export C_BLUE=$'\033[38;5;75m'
export C_CYAN=$'\033[38;5;51m'
export C_MAGENTA=$'\033[38;5;213m'
export C_WHITE=$'\033[38;5;255m'
export C_UNDER=$'\033[4m'
export C_ORANGE=$'\033[38;5;215m'
export C_GRAY=$'\033[38;5;245m'

# ui::rep <char> <count> → the character repeated (multibyte-safe; never use tr for this)
ui::rep() { local s; printf -v s '%*s' "$2" ''; printf '%s' "${s// /$1}"; }

ui::hr() {
  local w=$(ui::cols)
  printf '%s%s%s\n' "$C_DIM" "$(ui::rep ─ "$w")" "$C_RESET"
}

ui::banner() {
  # Full motd-style splash: big Nebula logo + sysinfo + disk panel
  local motd="${NEBULA_HOME}/motd/init.sh"
  if [[ -x $motd ]]; then
    "$motd"
  else
    local file="${NEBULA_CFG:-$NEBULA_HOME/data}/banner.txt"; [[ -s $file ]] || file="${NEBULA_HOME}/assets/banner.txt"
    [[ -f $file ]] && printf "${C_CYAN}%s${C_RESET}\n" "$(cat "$file")"
  fi
}

ui::small_banner() {
  # Compact banner for status lines (post-login, etc)
  local file="${NEBULA_CFG:-$NEBULA_HOME/data}/banner.txt"; [[ -s $file ]] || file="${NEBULA_HOME}/assets/banner.txt"
  [[ -f $file ]] && printf "${C_CYAN}%s${C_RESET}\n" "$(cat "$file")"
}

ui::maker_intro() {
  cat <<EOF

${C_CYAN}${C_BOLD}⚡ Nebula • AI UI ⚡${C_RESET}
${C_GRAY}────────────────────────${C_RESET}
  A Nebula AI shell UI for Termux
  ${C_GRAY}Based on cvui${C_RESET}
  ${C_GRAY}by cybervaultke (MIT)${C_RESET}
${C_GRAY}────────────────────────${C_RESET}
EOF
}

ui::say_status() {
  # ui::say_status OK "message"   (long messages wrap under themselves instead of breaking mid-word)
  local tag=$1 icon col; shift
  case $tag in
    OK)   icon="✔"; col=$C_GREEN ;;
    WARN) icon="⚠"; col=$C_YELLOW ;;
    ERR)  icon="✖"; col=$C_RED ;;
    INFO) icon="ℹ"; col=$C_BLUE ;;
    *)    icon="•"; col="" ;;
  esac
  local msg="$*" cols
  if (( ${#msg} > 20 )) && cols=$(ui::cols 2>/dev/null) && [[ $cols =~ ^[0-9]+$ ]] && (( ${#msg} + 4 > cols - 1 )); then
    printf '  %s%s%s %s\n' "$col" "$icon" "$C_RESET" "$msg" | ui::wrap "$(( cols - 1 ))" 4
  else
    printf '  %s%s%s %s\n' "$col" "$icon" "$C_RESET" "$msg"
  fi
}

ui::prompt_char() {
  printf "${C_MAGENTA}❯${C_RESET} "
}

# ls with icons (matches user's Termux setup: lsd + FiraCode)
ui::ls() {
  if command -v lsd >/dev/null 2>&1; then
    lsd --icon=always --icon-theme=unicode --group-dirs=first "$@"
  else
    ls --color=auto "$@"
  fi
}

ui::ll() {
  if command -v lsd >/dev/null 2>&1; then
    lsd -l --icon=always --icon-theme=unicode --group-dirs=first "$@"
  else
    ls -l --color=auto "$@"
  fi
}

# ui::confirm "question" [Y|N]  → 0 yes / 1 no (non-interactive → default)
ui::confirm() {
  local q=$1 def=${2:-Y} ans hint="[Y/n]"
  [[ $def == N ]] && hint="[y/N]"
  [[ ${NEBULA_YES:-0} == 1 ]] && return 0
  [[ -t 0 ]] || { [[ $def == Y ]]; return; }
  read -r -p "  $q $hint " ans || ans=""
  ans=${ans:-$def}
  [[ ${ans,,} == y* ]]
}

# ui::bar <percent> [width=20] [invert]  → colored [████░░░░] bar (no newline)
# Colors go green→yellow→red as the bar FILLS. Pass "invert" when a low value
# is the bad one (battery).
ui::bar() {
  local pct=$1 w=${2:-20} f e i bar="" color sev
  [[ $pct =~ ^[0-9]+$ ]] || pct=0
  (( pct > 100 )) && pct=100
  f=$(( pct * w / 100 )); e=$(( w - f ))
  sev=$pct; [[ ${3:-} == invert ]] && sev=$(( 100 - pct ))
  if   (( sev >= 95 )); then color=$C_RED
  elif (( sev >= 75 )); then color=$C_YELLOW
  else                       color=$C_GREEN; fi
  for ((i=0;i<f;i++)); do bar+="█"; done
  for ((i=0;i<e;i++)); do bar+="░"; done
  printf '%s[%s]%s' "$color" "$bar" "$C_RESET"
}

# ui::lan_ip → this phone's Wi-Fi/LAN address (best effort)
ui::lan_ip() {
  local ip=""
  if declare -F device::_api_ok >/dev/null 2>&1 && device::_api_ok && command -v termux-wifi-connectioninfo >/dev/null 2>&1; then
    ip=$(timeout 5 termux-wifi-connectioninfo 2>/dev/null | grep -o '"ip": *"[0-9.]*"' | grep -o '[0-9][0-9.]*' | head -1)
  fi
  [[ -z $ip || $ip == 0.0.0.0 ]] && ip=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1)
  [[ -z $ip ]] && ip=$(ifconfig 2>/dev/null | awk '/inet /{print $2}' | sed 's/addr://' | grep -v '^127\.' | head -1)
  [[ -z $ip ]] && ip=$(ip -4 -o addr show 2>/dev/null | awk '$2!="lo"{sub(/\/.*/,"",$4);print $4}' | head -1)
  printf '%s' "$ip"
}

# ui::human_kb <kilobytes> → 1.2G / 340M
ui::human_kb() {
  awk -v k="$1" 'BEGIN{ if(k>=1048576) printf "%.1fG",k/1048576; else if(k>=1024) printf "%.0fM",k/1024; else printf "%dK",k }'
}

# ── responsive text helpers ─────────────────────────────────────────────
# ui::item <styled label> <label visible width> <description> [lead=2]
#   "  name      description that wraps under itself on narrow screens"
ui::item() {
  local lead=${4:-2} cols w pad rest; cols=$(ui::cols); w=$(( cols - 1 ))
  printf -v pad '%*s' "$lead" ''
  if (( lead + $2 + 1 > cols / 2 )); then        # label too wide to sit beside the text: put the text underneath
    printf '%s%s\n' "$pad" "$1"
    printf -v rest '%*s' $(( lead + 2 )) ''
    viz::wrap "$w" "${rest}${C_DIM}" "${rest}${C_DIM}" "$3"
  else
    printf -v rest '%*s' $(( lead + $2 + 1 )) ''
    viz::wrap "$w" "${pad}$1 ${C_DIM}" "${rest}${C_DIM}" "$3"
  fi
  printf '%s' "$C_RESET"
}
# ui::hint <text…> : a dim hint line that wraps instead of overflowing
ui::hint() { printf '\n'; viz::wrap "$(( $(ui::cols) - 2 ))" "  ${C_DIM}" "  ${C_DIM}" "$*"; printf '%s' "$C_RESET"; }
