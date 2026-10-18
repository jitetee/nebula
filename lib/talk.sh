#!/data/data/com.termux/files/usr/bin/env bash
# nebula — talk to Termux directly.
#
#   gh auth login          gh isn't installed → "Install it now?" → installs → runs your command
#   show me big files      not a command → "Translate with Nebula AI?" → a plan you review
#   tell <request>         same, on purpose                 english ask|auto|off   how eager to be
#   (in the nebula shell)  !cmd = run exactly as typed      ?request = plain English
#
# Nebula NEVER runs an AI plan without showing it first; risky commands need you to type "yes".

# ── 1. command not found → which package provides it? ───────────────────
# sets CNF_PKG / CNF_DESC ; returns 0 if a package was found
cnf::lookup() {
  local c=$1 out p
  CNF_PKG=""; CNF_DESC=""
  if pm::find "$c" 2>/dev/null; then CNF_PKG=$PM_NAME; CNF_DESC=$PM_DESC; return 0; fi
  local helper="${PREFIX:-/data/data/com.termux/files/usr}/libexec/termux/command-not-found"
  if [[ -x $helper ]]; then
    out=$("$helper" "$c" 2>&1)
    p=$(grep -o 'pkg install [A-Za-z0-9.+-]*' <<<"$out" | head -1 | awk '{print $3}')
    [[ -n $p ]] && { CNF_PKG=$p; CNF_DESC="from Termux's package index"; return 0; }
  fi
  if command -v apt-cache >/dev/null 2>&1 && apt-cache show "$c" >/dev/null 2>&1; then CNF_PKG=$c; CNF_DESC="Termux package"; return 0; fi
  return 1
}

# ── 2. plain English ────────────────────────────────────────────────────
nl::mode() {
  local m=ask; [[ -f $NEBULA_CFG/nl_mode ]] && m=$(<"$NEBULA_CFG/nl_mode")
  m=${NEBULA_NL:-$m}; [[ $m == @(ask|auto|off) ]] || m=ask; echo "$m"
}
cmd::english() {
  case "${1:-}" in
    ask|auto|off) mkdir -p "$NEBULA_CFG"; echo "$1" > "$NEBULA_CFG/nl_mode"
      case $1 in ask) ui::say_status OK "Plain-English mode: ask first (default)";; auto) ui::say_status OK "Plain-English mode: read-only plans run at once, everything else asks";; off) ui::say_status OK "Plain-English mode off.";; esac ;;
    *) ui::say_status INFO "Plain-English mode: $(nl::mode)   ·   english ask | auto | off"; printf '   %sask%s  offer to translate sentences · %sauto%s  run read-only plans at once · %soff%s  never\n' "$C_BOLD" "$C_RESET" "$C_BOLD" "$C_RESET" "$C_BOLD" "$C_RESET" ;;
  esac
}
cmd::nl() { cmd::english "$@"; }      # old name, kept so existing habits still work
# does this look like a sentence rather than a mistyped command?
nl::wanted() {
  [[ $(nl::mode) == off ]] && return 1
  command -v tgpt >/dev/null 2>&1 || return 1
  local text="$*"; local -a w=($text)
  (( ${#w[@]} >= 3 )) || return 1
  [[ ${w[0]} =~ ^[a-z]{2,}$ ]] || return 1
  [[ $text != *[\|\&\;\<\>\$\`\(\)]* ]] || return 1
}

# risky? (must be typed "yes")
tell::danger() {
  local c=$1
  [[ $c =~ (^|[[:space:];\&\|])(sudo|su|tsu)[[:space:]] ]] && return 0
  [[ $c =~ rm[[:space:]]+-[a-zA-Z]*[rRfF] ]] && return 0
  [[ $c =~ (^|[[:space:];\&\|])(dd|mkfs[.a-z0-9]*|fdisk|shred|reboot|poweroff|shutdown)([[:space:]]|$) ]] && return 0
  [[ $c =~ (curl|wget)[^\|]*\|[[:space:]]*(ba|z)?sh ]] && return 0
  [[ $c =~ (chmod|chown)[[:space:]]+-R ]] && return 0
  [[ $c =~ git[[:space:]]+push.*(--force|[[:space:]]-f([[:space:]]|$)) ]] && return 0
  [[ $c =~ \>[[:space:]]*/dev/ || $c == *':(){'* ]] && return 0
  [[ $c =~ (kill|pkill|killall)[[:space:]]+-9 ]] && return 0
  return 1
}
# read-only? (the only kind `english auto` runs without asking)
tell::safe() {
  local c=$1 seg w
  [[ $c == *'>'* || $c == *'-exec'* || $c == *'-delete'* || $c == *'$('* || $c == *'`'* ]] && return 1
  while IFS= read -r seg; do
    seg=${seg#"${seg%%[![:space:]]*}"}; w=${seg%% *}
    case $w in
      ls|cat|pwd|echo|df|du|free|uptime|uname|whoami|date|head|tail|wc|grep|find|which|type|file|stat|ps|id|env|printf|tree|sort|uniq|cut|awk|sed|nproc|hostname|ip|ifconfig|getprop|lsd|bat|rg|fd|jq|stat|realpath|basename|dirname|true) ;;
      git) [[ $seg =~ ^git[[:space:]]+(status|log|diff|branch|remote|show|rev-parse|config[[:space:]]+--get) ]] || return 1 ;;
      *) return 1 ;;
    esac
  done < <(sed 's/&&/\n/g; s/||/\n/g; s/;/\n/g; s/|/\n/g' <<<"$c")
  return 0
}

tell::context() {
  local mgr="pkg"; pm::have pip && mgr+=", pip"; pm::have npm && mgr+=", npm"
  local have="" t; for t in git python node gh ffmpeg; do command -v "$t" >/dev/null 2>&1 && have+="$t "; done
  printf 'Termux on Android (%s). Shell: %s. Current folder: %s. Home: %s. Package managers: %s. Installed: %s.' \
    "$(uname -m)" "${SHELL##*/}" "$PWD" "$HOME" "$mgr" "${have:-none of the common tools}"
}

# parse the AI reply → TELL_CMDS TELL_WHY TELL_SAY
tell::parse() {
  TELL_CMDS=(); TELL_WHY=(); TELL_SAY=""
  local raw=$1 l c infence=0 fenced=()
  while IFS= read -r l; do
    l=${l#"${l%%[![:space:]]*}"}; l=${l%$'\r'}
    case $l in
      '```'*) infence=$((1-infence)); continue ;;
      CMD:*)  c=${l#CMD:}; c=${c#"${c%%[![:space:]]*}"}; c=${c#\`}; c=${c%\`}; [[ -n $c ]] && { TELL_CMDS+=("$c"); TELL_WHY+=(""); } ;;
      WHY:*)  (( ${#TELL_WHY[@]} )) && TELL_WHY[${#TELL_WHY[@]}-1]=${l#WHY:} ;;
      SAY:*)  TELL_SAY=${l#SAY:} ;;
      *) (( infence )) && [[ -n $l && $l != \#* ]] && fenced+=("${l#\$ }") ;;
    esac
  done <<<"$raw"
  if (( ${#TELL_CMDS[@]} == 0 && ${#fenced[@]} )); then local f; for f in "${fenced[@]}"; do TELL_CMDS+=("$f"); TELL_WHY+=(""); done; fi
  (( ${#TELL_CMDS[@]} > 8 )) && TELL_CMDS=("${TELL_CMDS[@]:0:8}")
  return 0
}

# run commands sequentially in THIS shell; stop at the first failure
tell::exec() {
  local c rc=0
  for c in "$@"; do
    printf '%s❯%s %s\n' "$C_DIM" "$C_RESET" "$c"
    history -s "$c" 2>/dev/null
    eval "$c"; rc=$?
    nebula::_record "$c" "$rc" 2>/dev/null
    (( rc )) && { printf '%s✖ stopped (exit %d)%s — try: fix\n' "$C_RED" "$rc" "$C_RESET"; return $rc; }
  done
  return 0
}
tell::exec_file() { local -a cs=(); local l; while IFS= read -r l; do [[ -n $l ]] && cs+=("$l"); done < "$1"; rm -f "$1"; tell::exec "${cs[@]}"; }

# tell::flow <request> [--out file]
tell::flow() {
  local text=$1 out=${2:-}
  # fast path: "install X" needs no AI
  local lt=${text,,}
  if [[ $lt =~ ^(please )?(install|add|get|download)\ +([a-z0-9._+-]+)( and ([a-z0-9._+-]+))?$ ]]; then
    local a=${BASH_REMATCH[3]} b=${BASH_REMATCH[5]}
    pm::find "$a" 2>/dev/null && { PM_YES=0 pm::install_one "$a"; [[ -n $b ]] && PM_YES=0 pm::install_one "$b"; return 0; }
  fi
  cmd::_need_tgpt || return 1
  local prompt="You turn a user's request into shell commands for Termux on Android. Context: $(tell::context)
Reply ONLY with lines in this exact format, no markdown:
CMD: <one-line shell command>
WHY: <at most 8 words>
Rules: at most 6 commands; each command on ONE line (chain with &&); use pkg for packages (never apt, never sudo); use non-interactive flags like -y; no interactive editors; commands must be safe for a beginner. If the request is only a question and needs no command, reply with one line: SAY: <short answer>.
Request: $text"
  printf '  %s⠿%s %sNebula AI is working it out…%s\r' "$C_CYAN" "$C_RESET" "$C_DIM" "$C_RESET"
  local raw; raw=$(ai::_think "$prompt"); printf '\033[2K\r'
  [[ -z $raw ]] && { ui::say_status ERR "No reply (network?)"; return 1; }
  tell::parse "$raw"

  if (( ${#TELL_CMDS[@]} == 0 )); then
    printf '%s%s🤖 Nebula AI%s\n' "$C_BLUE" "$C_BOLD" "$C_RESET"
    printf '%s\n' "${TELL_SAY:-$raw}" | md::render; return 1
  fi

  printf '\n%s%s🤖 Nebula AI%s %splan for:%s %s\n\n' "$C_BLUE" "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET" "$text"
  local i danger=0 allsafe=1
  for i in "${!TELL_CMDS[@]}"; do
    local mark="${C_CYAN}▸${C_RESET}"
    if tell::danger "${TELL_CMDS[i]}"; then mark="${C_RED}⚠${C_RESET}"; danger=1; fi
    tell::safe "${TELL_CMDS[i]}" || allsafe=0
    printf '  %s%d%s %s %s%s%s\n' "$C_DIM" $((i+1)) "$C_RESET" "$mark" "$C_BOLD" "${TELL_CMDS[i]}" "$C_RESET"
    [[ -n ${TELL_WHY[i]// } ]] && printf '       %s%s%s\n' "$C_DIM" "${TELL_WHY[i]# }" "$C_RESET"
  done
  echo

  local approved=("${TELL_CMDS[@]}") ans
  if [[ $(nl::mode) == auto ]] && (( allsafe && ! danger )); then
    printf '  %s(read-only — running)%s\n' "$C_DIM" "$C_RESET"
  elif (( danger )); then
    printf '  %s⚠ This plan contains risky commands (marked ⚠).%s\n' "$C_YELLOW" "$C_RESET"
    read -r -p "  Type 'yes' to run it, anything else cancels: " ans </dev/tty || return 1
    [[ $ans == yes ]] || { ui::say_status INFO "Cancelled. Nothing was run."; return 1; }
  else
    while :; do
      read -r -p "  Run it?  [Y]es · [n]o · [s]tep by step · [e]dit  " ans </dev/tty || return 1
      case ${ans,,} in
        ""|y|yes) break ;;
        n|no|q)   ui::say_status INFO "Cancelled. Nothing was run."; return 1 ;;
        s|step)   local step=(); local c2
                  for c2 in "${approved[@]}"; do read -r -p "  ▸ $c2   run? [Y/n] " a2 </dev/tty; [[ ${a2,,} == n* ]] || step+=("$c2"); done
                  approved=("${step[@]}"); break ;;
        e|edit)   local ed=() c3
                  for c3 in "${approved[@]}"; do read -e -r -i "$c3" -p "  ▸ " c3 </dev/tty; [[ -n $c3 ]] && ed+=("$c3"); done
                  approved=("${ed[@]}")
                  for c3 in "${approved[@]}"; do tell::danger "$c3" && { read -r -p "  ⚠ '$c3' is risky. Type 'yes' to keep it: " a3 </dev/tty; [[ $a3 == yes ]] || { ui::say_status INFO "Cancelled."; return 1; }; }; done
                  break ;;
      esac
    done
  fi
  (( ${#approved[@]} )) || { ui::say_status INFO "Nothing to run."; return 1; }

  if [[ -n $out ]]; then printf '%s\n' "${approved[@]}" > "$out"; return 0; fi
  tell::exec "${approved[@]}"
}

cmd::tell() {
  local out="" args=()
  while (( $# )); do case $1 in --out) out=$2; shift ;; *) args+=("$1") ;; esac; shift; done
  local text="${args[*]}"
  [[ -z $text ]] && { ui::say_status WARN "Usage: tell <what you want>   e.g. tell show the 5 biggest files here"; return 1; }
  tell::flow "$text" "$out"
}

# ── 3. the entry point for "command not found" (zsh handler and nebula shell) ─
# exit: 0 = installed, run the original command again   20 = plan written to data/.plan.sh   1 = nothing to do
cmd::cnf() {
  local c=${1:-}; shift
  [[ -t 0 && -t 1 ]] || return 1
  [[ -n $c && $c != */* ]] || return 1
  if [[ $c =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] && cnf::lookup "$c"; then
    printf '\n  %s📦 %s isn'"'"'t installed.%s  %sPackage:%s %s%s%s %s%s%s\n' "$C_YELLOW" "$c" "$C_RESET" "$C_DIM" "$C_RESET" "$C_BOLD" "$CNF_PKG" "$C_RESET" "$C_DIM" "${CNF_DESC:+— $CNF_DESC}" "$C_RESET"
    ui::confirm "Install it now and run your command?" Y || return 1
    PM_YES=1 pm::install_one "$CNF_PKG" || return 1
    pm::rehash 2>/dev/null; hash -r
    command -v "$c" >/dev/null 2>&1 && return 0
    ui::say_status WARN "Installed, but '$c' still isn't on your PATH. Restart the shell and try again."; return 1
  fi
  if nl::wanted "$c" "$@"; then
    printf '\n  %s💬 "%s" isn'"'"'t a command — it reads like a request.%s\n' "$C_YELLOW" "$c $*" "$C_RESET"
    if [[ $(nl::mode) == ask ]]; then ui::confirm "Let Nebula AI turn it into commands?" Y || return 1; fi
    mkdir -p "$NEBULA_CFG"; rm -f "$NEBULA_CFG/.plan.sh"
    tell::flow "$c $*" "$NEBULA_CFG/.plan.sh" && return 20
  fi
  return 1
}
