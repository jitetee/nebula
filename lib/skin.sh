#!/data/data/com.termux/files/usr/bin/env bash
# nebula — the shared J.I.T.E.T.E.E. look (same style as jtlearn). Thin wrappers around lib/skin.py.
#
#   skin::box    "Title"            stdin lines → rounded panel
#   skin::menu   "Title" [--nodot]  stdin  key⇥icon⇥label⇥description → two-column menu panel
#   skin::table  "Title"            stdin TSV (first line = header) → table
#   skin::kv     "Title"            stdin  key⇥value → aligned panel
#   skin::banner NAME "tag" …       big letters in a double frame
#   skin::bubble [--right] name [time]   stdin text → chat bubble
#   skin::prompt ["Your choice"]    └─➤ prompt (no newline)
#   skin::bar PCT [width]           progress bar line
#   skin::spin "label" cmd…         run a command with a spinner; keeps its exit code
#   skin::load "label" [seconds]    short animated loading bar
# NEBULA_PLAIN=1 / NO_COLOR → plain ASCII; under 40 columns panels become simple rules.

skin::_py() { NEBULA_COLS=$(ui::cols 2>/dev/null) NEBULA_HOME=${NEBULA_HOME:-} python3 "${NEBULA_HOME:-.}/lib/skin.py" "$@"; }
skin::box()    { skin::_py box --title "${1:-}"; }
skin::menu()   { local t=${1:-}; shift; skin::_py menu --title "$t" "$@"; }
skin::table()  { skin::_py table --title "${1:-}"; }
skin::kv()     { skin::_py kv --title "${1:-}"; }
skin::banner() { local n=$1; shift; local a=(); local t; for t in "$@"; do a+=(--tag "$t"); done; skin::_py banner "$n" "${a[@]}"; }
skin::bubble() { local r=(); [[ ${1:-} == --right ]] && { r=(--right); shift; }; skin::_py bubble "${r[@]}" --name "${1:-}" --time "${2:-}"; }
skin::prompt() { skin::_py prompt "${1:-Your choice}"; }
skin::bar()    { skin::_py bar "$1" --width "${2:-20}"; }
skin::status() { skin::_py status "$1" "$2"; }

skin::spin() {  # skin::spin "label" command args…
  local label=$1; shift
  if [[ ! -t 1 || ${NEBULA_PLAIN:-0} == 1 || -n ${NO_COLOR:-} ]]; then printf '  … %s\n' "$label"; "$@"; return; fi
  local f=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏) i=0 pid rc
  "$@" & pid=$!
  printf '\033[?25l'
  while kill -0 "$pid" 2>/dev/null; do printf '\r  %s%s%s %s ' "$C_CYAN" "${f[i++ % 10]}" "$C_RESET" "$label"; sleep 0.08; done
  wait "$pid"; rc=$?
  printf '\r\033[K\033[?25h'
  (( rc == 0 )) && ui::say_status OK "$label" || ui::say_status ERR "$label"
  return $rc
}

skin::load() {  # skin::load "label" [seconds=1]
  local label=$1 secs=${2:-1} i steps=20
  [[ -t 1 && ${NEBULA_PLAIN:-0} != 1 && -z ${NO_COLOR:-} ]] || { printf '  … %s\n' "$label"; return; }
  for ((i=0; i<=steps; i++)); do
    printf '\r  %s %s' "$label" "$(skin::_py bar $(( i * 100 / steps )) --width 20 | tr -d '\n')"
    sleep "$(awk -v s="$secs" -v n="$steps" 'BEGIN{printf "%.3f", s/n}')"
  done
  printf '\r\033[K'
}
