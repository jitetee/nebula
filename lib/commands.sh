#!/data/data/com.termux/files/usr/bin/env bash
# nebula — built-in commands


cmd::about() {
  ui::banner
  ui::maker_intro
}

cmd::_need_tgpt() {
  if ! command -v tgpt >/dev/null 2>&1; then
    ui::say_status ERR "tgpt not installed. Run: pkg install tgpt  (or see README)"
    return 1
  fi
}

cmd::_need_curl() {
  if ! command -v curl >/dev/null 2>&1; then
    ui::say_status ERR "curl is required for this command"
    return 1
  fi
}


cmd::joke() {
  cmd::_need_tgpt || return 1
  local topics=(programming science animals food coffee space "dad joke" music
                math cats dogs AI robots aliens pirates ninjas wizards)
  local t=${topics[RANDOM % ${#topics[@]}]}
  local nonce=$RANDOM
  printf "${C_YELLOW}😄${C_RESET} "
  local joke; joke=$(tgpt "Tell me ONE fresh short clean genuinely funny joke about $t. Different from your last one. Just the joke, no preamble. [seed=$nonce]" 2>/dev/null); printf "%s\n" "$joke" | md::render; voice::say "$(md::plain "$joke")"
}

cmd::fact() {
  cmd::_need_tgpt || return 1
  local topics=(history biology physics space oceans animals "ancient civilizations"
                psychology geography chemistry technology music language food
                mathematics medicine sports "deep sea" insects)
  local t=${topics[RANDOM % ${#topics[@]}]}
  local nonce=$RANDOM
  printf "${C_CYAN}💡${C_RESET} "
  local fact; fact=$(tgpt "Give me ONE surprising fun fact about $t in 1-2 sentences. Something most people don't know. No preamble. [seed=$nonce]" 2>/dev/null); printf "%s\n" "$fact" | md::render; voice::say "$(md::plain "$fact")"
}

cmd::meme() {
  local url=""
  if command -v curl >/dev/null 2>&1; then
    url=$(curl -fsSL --max-time 5 https://meme-api.com/gimme 2>/dev/null | \
          grep -oE '"url":"[^"]+"' | head -n1 | cut -d'"' -f4)
  fi
  if [[ -z $url && -f ${NEBULA_HOME}/assets/memes.txt ]]; then
    url=$(shuf -n1 "${NEBULA_HOME}/assets/memes.txt" 2>/dev/null || \
          awk 'NR==int(rand()*NR)+1' "${NEBULA_HOME}/assets/memes.txt")
    ui::say_status INFO "Using bundled meme (API unreachable)"
  fi
  if [[ -z $url ]]; then
    ui::say_status ERR "No meme available"; return 1
  fi
  printf "${C_MAGENTA}🖼  Meme:${C_RESET} %s\n" "$url"
  if command -v termux-open-url >/dev/null 2>&1; then
    termux-open-url "$url"
  fi
}

cmd::weather() {
  local city="${*:-}"
  cmd::_need_curl || return 1
  curl -fsSL --max-time 10 "https://wttr.in/${city// /+}?format=v2&m" 2>/dev/null || \
    ui::say_status ERR "Weather service unreachable"
}

cmd::sysinfo() {
  if command -v neofetch >/dev/null 2>&1; then
    neofetch
  else
    printf "User     : %s\n" "${NEBULA_USER:-$USER}"
    printf "Shell    : %s\n" "$SHELL"
    printf "Host     : %s\n" "$(uname -n)"
    printf "Kernel   : %s\n" "$(uname -sr)"
    printf "Uptime   : %s\n" "$(uptime -p 2>/dev/null || uptime)"
  fi
}

# ── news (Hacker News top 5) ─────────────────────────────────────────────


# ── ip (public IP + geo) ─────────────────────────────────────────────────
cmd::ip() {
  cmd::_need_curl || return 1
  local data
  data=$(curl -fsSL --max-time 6 "https://ipinfo.io/json" 2>/dev/null)
  [[ -z $data ]] && { ui::say_status ERR "ipinfo.io unreachable"; return 1; }
  local ip city region country org
  ip=$(printf '%s' "$data" | grep -oE '"ip":"[^"]+"' | cut -d'"' -f4)
  city=$(printf '%s' "$data" | grep -oE '"city":"[^"]+"' | cut -d'"' -f4)
  region=$(printf '%s' "$data" | grep -oE '"region":"[^"]+"' | cut -d'"' -f4)
  country=$(printf '%s' "$data" | grep -oE '"country":"[^"]+"' | cut -d'"' -f4)
  org=$(printf '%s' "$data" | grep -oE '"org":"[^"]+"' | cut -d'"' -f4)
  printf "${C_CYAN}🌐 Public IP${C_RESET}\n"
  printf "   IP       : ${C_BOLD}%s${C_RESET}\n" "${ip:-?}"
  printf "   Location : %s, %s, %s\n" "${city:-?}" "${region:-?}" "${country:-?}"
  [[ -n $org ]] && printf "   Org      : ${C_DIM}%s${C_RESET}\n" "$org"
}

# ── define (dictionaryapi.dev) ───────────────────────────────────────────
cmd::define() {
  cmd::_need_curl || return 1
  local word="${1:-}"
  [[ -z $word ]] && { ui::say_status WARN "Usage: define <word>"; return 1; }
  local data
  data=$(curl -fsSL --max-time 6 \
    "https://api.dictionaryapi.dev/api/v2/entries/en/$word" 2>/dev/null)
  if [[ -z $data || $data == *'"title":"No Definitions Found"'* ]]; then
    ui::say_status ERR "No definition found for: $word"
    return 1
  fi
  printf "${C_CYAN}${C_BOLD}📖 %s${C_RESET}\n" "$word"
  # pull a couple of definitions with crude grep (no jq dependency)
  printf '%s' "$data" \
    | grep -oE '"partOfSpeech":"[^"]+"|"definition":"[^"]+"' \
    | head -n 8 \
    | awk -F'"' '
        /partOfSpeech/ { printf "\n  \033[38;5;215m(%s)\033[0m\n", $4; next }
        /definition/   { printf "    • %s\n", $4 }'
}

# ── qr ───────────────────────────────────────────────────────────────────
cmd::qr() {
  if ! command -v qrencode >/dev/null 2>&1; then
    ui::say_status ERR "qrencode not installed. Run: pkg install qrencode"
    return 1
  fi
  local text="$*"
  [[ -z $text ]] && { ui::say_status WARN "Usage: qr <text or URL>"; return 1; }
  qrencode -t ANSIUTF8 "$text"
}

# ── note / notes ─────────────────────────────────────────────────────────
cmd::note() {
  local f="$NEBULA_CFG/notes.md"
  mkdir -p "$(dirname "$f")"
  local text="$*"
  if [[ -z $text ]]; then
    ui::say_status WARN "Usage: note <text>  (use 'notes' to list)"
    return 1
  fi
  printf -- '- [%s] %s\n' "$(date '+%Y-%m-%d %H:%M')" "$text" >> "$f"
  ui::say_status OK "Noted."
}

cmd::notes() {
  local f="$NEBULA_CFG/notes.md" sub="${1:-}"
  case "$sub" in
    search|find)
      shift; local kw="$*"
      [[ -z $kw ]] && { ui::say_status WARN "Usage: notes search <word>"; return 1; }
      [[ -s $f ]] || { ui::say_status INFO "No notes yet."; return 0; }
      printf "${C_CYAN}${C_BOLD}🔎 Notes matching '%s'${C_RESET}\n" "$kw"
      grep -in -- "$kw" "$f" | awk -F: '{n=$1; sub(/^[0-9]+:/,""); printf "  %3d  %s\n", n, $0}' | ui::wrap "$(( $(ui::cols) - 1 ))" 7 || true
      return 0 ;;
    rm|del|remove)
      local n="${2:-}"
      [[ $n =~ ^[0-9]+$ ]] || { ui::say_status WARN "Usage: notes rm <number>   (numbers from 'notes')"; return 1; }
      local total; total=$(wc -l < "$f" 2>/dev/null || echo 0)
      (( n >= 1 && n <= total )) || { ui::say_status ERR "No note #$n"; return 1; }
      sed -i "${n}d" "$f" && ui::say_status OK "Deleted note #$n."
      return 0 ;;
    edit)
      local ed="${EDITOR:-}"
      [[ -z $ed ]] && for ed in nano nvim vim vi; do command -v "$ed" >/dev/null 2>&1 && break; done
      mkdir -p "$(dirname "$f")"; touch "$f"; "$ed" "$f"; return 0 ;;
  esac
  if [[ ! -s $f ]]; then
    ui::say_status INFO "No notes yet. Add with: note <text>"
    return 0
  fi
  printf "${C_CYAN}${C_BOLD}📝 Your notes${C_RESET}  ${C_DIM}(search · rm <n> · edit)${C_RESET}\n"
  awk '{printf "  %3d  %s\n", NR, $0}' "$f" | ui::wrap "$(( $(ui::cols) - 1 ))" 7
}

# ── todo ─────────────────────────────────────────────────────────────────
cmd::todo() {
  local f="$NEBULA_CFG/todo.md"
  mkdir -p "$(dirname "$f")"
  touch "$f"
  local sub="${1:-}"
  case "$sub" in
    done|do)
      local n="${2:-}"
      [[ $n =~ ^[0-9]+$ ]] || { ui::say_status WARN "Usage: todo done <number>   (numbers from 'todo')"; return 1; }
      (( $(grep -c '^- \[' "$f") >= n && n >= 1 )) || { ui::say_status ERR "No todo #$n"; return 1; }
      awk -v n="$n" '
        /^- \[/ { i++; if (i==n) { sub(/\[ \]/, "[x]") } }
        { print }
      ' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
      ui::say_status OK "Marked #$n done."
      cmd::todo   # reprint
      ;;
    rm|remove)
      local n="${2:-}"
      [[ $n =~ ^[0-9]+$ ]] || { ui::say_status WARN "Usage: todo rm <number>"; return 1; }
      (( $(grep -c '^- \[' "$f") >= n && n >= 1 )) || { ui::say_status ERR "No todo #$n"; return 1; }
      awk -v n="$n" '
        /^- \[/ { i++; if (i==n) next }
        { print }
      ' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
      ui::say_status OK "Removed #$n."
      cmd::todo
      ;;
    clear)
      : > "$f"
      ui::say_status OK "Todo list cleared."
      ;;
    pri|priority|p)
      local n="${2:-}" lv="${3:-}" tag=""
      [[ $n =~ ^[0-9]+$ ]] || { ui::say_status WARN "Usage: todo pri <n> high|med|low|none"; return 1; }
      case "${lv,,}" in
        high|h) tag="(H) " ;; med|medium|m) tag="(M) " ;; low|l) tag="(L) " ;; none|clear|"") tag="" ;;
        *) ui::say_status ERR "Priority must be high, med, low or none"; return 1 ;;
      esac
      awk -v n="$n" -v tag="$tag" '
        /^- \[/ { i++; if (i==n) { head=substr($0,1,6); rest=substr($0,7); sub(/^\((H|M|L)\) /,"",rest); $0=head tag rest } }
        { print }
      ' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
      ui::say_status OK "Priority updated for #$n."
      cmd::todo
      ;;
    "")
      if [[ ! -s $f ]]; then
        ui::say_status INFO "Empty. Add with: todo <text>  |  done <n>  |  pri <n> high|med|low"
        return 0
      fi
      printf "${C_CYAN}${C_BOLD}✅ Todo${C_RESET}\n"
      awk '
        /^- \[/ { i++; L[i]=$0
          if ($0 ~ /\[x\]/) r=5; else if ($0 ~ /\] \(H\) /) r=1; else if ($0 ~ /\] \(M\) /) r=2; else if ($0 ~ /\] \(L\) /) r=4; else r=3
          R[i]=r }
        END { for (r=1;r<=5;r++) for (k=1;k<=i;k++) if (R[k]==r) {
            line=L[k]; sub(/^- /, "", line)
            if (r==5) { gsub(/\[x\]/, "\033[38;5;120m[✓]\033[0m", line); printf "  \033[2m%2d. %s\033[0m\n", k, line; continue }
            gsub(/\[ \]/, "\033[38;5;221m[ ]\033[0m", line)
            gsub(/\(H\)/, "\033[38;5;203m(H)\033[0m", line)
            gsub(/\(M\)/, "\033[38;5;221m(M)\033[0m", line)
            gsub(/\(L\)/, "\033[38;5;75m(L)\033[0m", line)
            printf "  %2d. %s\n", k, line } }
      ' "$f" | ui::wrap "$(( $(ui::cols) - 1 ))" 6
      ;;
    *)
      printf -- '- [ ] %s\n' "$*" >> "$f"
      ui::say_status OK "Added."
      ;;
  esac
}

# ── timer (pomodoro) ─────────────────────────────────────────────────────
# ── timer (hacker‑styled countdown) ─────────────────────────────────
cmd::timer() {
  local mins="${1:-25}"
  if ! [[ $mins =~ ^[0-9]+$ ]] || (( mins <= 0 )); then
    ui::say_status WARN "Usage: timer <minutes>"; return 1
  fi
  local secs=$(( mins * 60 ))
  local end=$(( $(date +%s) + secs ))
  
  # Weather‑style frame
  local top="┌─────────────────────────────────────────────────────────────────┐"
  local mid="├─────────────────────────────────────────────────────────────────┤"
  local bot="└─────────────────────────────────────────────────────────────────┘"
  
  ui::say_status INFO "⚡ HACKER TIMER: ${mins}m session - Ctrl+C to abort"
  printf "\n${C_CYAN}%s${C_RESET}\n" "$top"
  printf "${C_CYAN}│${C_RESET}  ${C_GREEN}⏳ nebula TIMER${C_RESET}                                    ${C_CYAN}│${C_RESET}\n"
  printf "${C_CYAN}%s${C_RESET}\n" "$mid"
  
  trap 'printf "\n${C_CYAN}%s${C_RESET}\n" "$bot"; ui::say_status WARN "⚠ Timer aborted."; trap - INT; return 130' INT
  
  while (( $(date +%s) < end )); do
    local left=$(( end - $(date +%s) ))
    local perc=$(( ( (secs - left) * 100 ) / secs ))
    local filled=$(( perc * 60 / 100 ))
    local empty=$(( 60 - filled ))
    
    # Build gradient bar
    local bar=""
    for ((i=0; i<filled; i++)); do
      if (( i < filled/3 )); then
        bar+="${C_GREEN}█${C_RESET}"
      elif (( i < filled*2/3 )); then
        bar+="${C_YELLOW}▓${C_RESET}"
      else
        bar+="${C_RED}▒${C_RESET}"
      fi
    done
    for ((i=0; i<empty; i++)); do
      bar+="${C_DIM}░${C_RESET}"
    done
    
    local min_left=$(( left / 60 )); local sec_left=$(( left % 60 ));
    local time_str=$(printf "%02d:%02d" $min_left $sec_left)
    
    printf "${C_CYAN}│${C_RESET}  [${bar}] ${C_BOLD}%s${C_RESET}  ${C_YELLOW}%3d%%${C_RESET} ${C_CYAN}│${C_RESET}\r" "$time_str" "$perc"
    sleep 1
  done
  
  printf "\n${C_CYAN}│${C_RESET}  ${C_BOLD}${C_GREEN}✔ TIMER COMPLETE!${C_RESET}                                   ${C_CYAN}│${C_RESET}\n"
  printf "${C_CYAN}%s${C_RESET}\n\n" "$bot"

  if command -v voice::say >/dev/null 2>&1; then
    local msgs=("Timer complete, ${NEBULA_USER:-sir}. Your ${mins} minute session has ended." "Focus session finished. Time to take a break, ${NEBULA_USER:-sir}." "The countdown has reached zero. Subsystems are standing by." "Alert. ${mins} minutes have elapsed. Task duration complete."); voice::say "${msgs[RANDOM % ${#msgs[@]}]}"
  fi
  if command -v sound::chime >/dev/null 2>&1; then sound::chime; fi
  if command -v termux-notification >/dev/null 2>&1; then
    termux-notification -t "nebula timer" -c "${mins}m elapsed" 2>/dev/null || true
  fi
}

# ── doctor (environment audit) ───────────────────────────────────────────
cmd::doctor() {
  local fix=0 miss_req=0 miss_opt=0
  [[ ${1:-} == --fix || ${1:-} == fix ]] && fix=1
  printf "${C_CYAN}${C_BOLD}🩺 nebula Doctor${C_RESET}\n"
  printf "${C_GRAY}%s${C_RESET}\n" "$(ui::rep ─ $(( $(ui::cols) > 33 ? 32 : $(ui::cols) - 2 )))"
  _nebula_doctor_check() {
    local label=$1 bin=$2 required=${3:-optional} b found="" cols lw=22 pw
    cols=$(ui::cols); (( cols < 56 )) && lw=12; pw=$(( cols - lw - 8 )); (( pw < 8 )) && pw=8
    for b in ${bin//,/ }; do command -v "$b" >/dev/null 2>&1 && { found=$(command -v "$b"); break; }; done
    if [[ -n $found ]]; then
      printf "  ${C_GREEN}✔${C_RESET} %-${lw}s ${C_DIM}(%s)${C_RESET}\n" "$label" "$(viz::trunc "$found" "$pw")"
    else
      if [[ $required == required ]]; then
        printf "  ${C_RED}✖${C_RESET} %-${lw}s ${C_RED}MISSING${cols:+$( (( cols >= 56 )) && echo ' (required)')}${C_RESET}\n" "$label"
        miss_req=$((miss_req+1))
      else
        printf "  ${C_YELLOW}○${C_RESET} %-${lw}s ${C_DIM}not installed${C_RESET}\n" "$label"
        miss_opt=$((miss_opt+1))
      fi
    fi
  }
  _nebula_doctor_check "bash"      bash    required
  _nebula_doctor_check "zsh"       zsh     required
  _nebula_doctor_check "git"       git     required
  _nebula_doctor_check "curl"      curl    required
  _nebula_doctor_check "openssl"   openssl required
  _nebula_doctor_check "lsd"       lsd
  _nebula_doctor_check "tgpt"      tgpt
  _nebula_doctor_check "gawk"      awk
  _nebula_doctor_check "jq"        jq
  _nebula_doctor_check "mpv/mpg123" mpv,mpg123
  _nebula_doctor_check "fd"        fd
  _nebula_doctor_check "espeak"    espeak
  _nebula_doctor_check "sox"       sox,play
  _nebula_doctor_check "qrencode"  qrencode
  _nebula_doctor_check "neofetch"  neofetch
  _nebula_doctor_check "python"    python3
  _nebula_doctor_check "termux-api" termux-notification
  printf "${C_GRAY}%s${C_RESET}\n" "$(ui::rep ─ $(( $(ui::cols) > 33 ? 32 : $(ui::cols) - 2 )))"
  local ok=1 f
  for f in "$NEBULA_HOME/bin/nebula" "$NEBULA_HOME/motd/init.sh" "$NEBULA_HOME/lib/auth.sh" "$NEBULA_HOME/assets/help.txt"; do
    if [[ -e $f ]]; then
      printf "  ${C_GREEN}✔${C_RESET} %s\n" "${f#$NEBULA_HOME/}"
    else
      printf "  ${C_RED}✖${C_RESET} %s ${C_RED}missing${C_RESET}\n" "${f#$NEBULA_HOME/}"
      ok=0
    fi
  done
  # data + safety checks
  if [[ -d $NEBULA_CFG && -w $NEBULA_CFG ]]; then
    printf "  ${C_GREEN}✔${C_RESET} data folder writable ${C_DIM}(%s)${C_RESET}\n" "$NEBULA_CFG" | ui::wrap "$(( $(ui::cols) - 1 ))" 4
  else
    printf "  ${C_RED}✖${C_RESET} data folder not writable: %s\n" "$NEBULA_CFG"; ok=0
  fi
  local al=10; [[ -f $NEBULA_CFG/autolock ]] && al=$(<"$NEBULA_CFG/autolock")
  printf "  ${C_GREEN}✔${C_RESET} auto-lock: %s\n" "$([[ $al == 0 ]] && echo off || echo "$al min")"
  local bd last; bd=$(backup::dir 2>/dev/null)
  last=$([[ -n $bd ]] && ls -1t "$bd"/nebula-backup-* 2>/dev/null | head -1)
  if [[ -n $last ]]; then
    printf "  ${C_GREEN}✔${C_RESET} last backup: %s\n" "$(date -r "$last" '+%Y-%m-%d %H:%M' 2>/dev/null)"
  else
    printf "  ${C_YELLOW}○${C_RESET} no backup yet — run: backup\n"
  fi
  local de dw di; read -r de dw di < <(device::issue_counts 2>/dev/null)
  (( ${de:-0} + ${dw:-0} > 0 )) && ui::say_status WARN "Device checks: ${de:-0} error(s), ${dw:-0} warning(s) — run: settings"
  if (( ok )); then
    ui::say_status OK "nebula install looks healthy."
  else
    ui::say_status ERR "Some nebula files are missing — try: nebula update"
  fi
  unset -f _nebula_doctor_check
  if (( miss_req + miss_opt > 0 )); then
    if (( fix )); then
      bash "$NEBULA_HOME/install/install.sh" --deps-only
    else
      ui::say_status INFO "$miss_req required / $miss_opt optional package(s) missing. Run: doctor --fix"
    fi
  fi
}

cmd::voice_toggle() {
  local cfg="$NEBULA_CFG/voice"
  case "${1:-}" in
    on)
      export NEBULA_VOICE=1
      mkdir -p "$(dirname "$cfg")"
      printf '1\n' > "$cfg"
      ui::say_status OK "Voice enabled (saved)"
      voice::say "Voice online."
      ;;
    off)
      export NEBULA_VOICE=0
      mkdir -p "$(dirname "$cfg")"
      printf '0\n' > "$cfg"
      ui::say_status OK "Voice muted (saved)"
      ;;
    *)
      ui::say_status INFO "Voice is currently: $([[ ${NEBULA_VOICE:-1} -eq 1 ]] && echo on || echo off)"
      ;;
  esac
}

cmd::banner() {
  local text="$*"
  if [[ -z $text ]]; then
    ui::say_status WARN "Usage: banner <text>   (letters/digits only, no spaces)"
    return 1
  fi
  if ! command -v banner::build >/dev/null 2>&1; then
    [[ -f "$NEBULA_HOME/lib/banner.sh" ]] && source "$NEBULA_HOME/lib/banner.sh"
  fi
  banner::build "$text"
}

cmd::whoami() {
  printf "  ${C_CYAN}%s${C_RESET} (nebula session)\n" "${NEBULA_USER:-unknown}"
}



cmd::noauth() {
  local cfg="$NEBULA_CFG/no-lock"
  case "${1:-}" in
    on)
      auth::confirm || return 1
      mkdir -p "$(dirname "$cfg")"
      touch "$cfg"
      ui::say_status OK "Authentication bypass enabled (no-auth ON)"
      ;;
    off)
      rm -f "$cfg"
      ui::say_status OK "Authentication bypass disabled (no-auth OFF)"
      ;;
    *)
      ui::say_status INFO "No-auth is currently: $([[ -f $cfg ]] && echo ON || echo OFF)"
      ui::say_status INFO "Use: noauth on|off to toggle."
      ;;
  esac
}

# ── time (hacker‑styled clock) ────────────────────────────────────────
cmd::time() {
  clear
  local top="┌─────────────────────────────────────────────────────────────────┐"
  local mid="├─────────────────────────────────────────────────────────────────┤"
  local bot="└─────────────────────────────────────────────────────────────────┘"
  
  printf "${C_CYAN}%s${C_RESET}\n" "$top"
  printf "${C_CYAN}│${C_RESET}  ${C_GREEN}⏰ nebula SYSTEM CLOCK${C_RESET}                                ${C_CYAN}│${C_RESET}\n"
  printf "${C_CYAN}%s${C_RESET}\n" "$mid"
  
  while true; do
    local now=$(date '+%Y-%m-%d %H:%M:%S')
    local day=$(date '+%A')
    local zone=$(date '+%Z')
    printf "${C_CYAN}│${C_RESET}  ${C_BOLD}${C_YELLOW}%s${C_RESET}  ${C_DIM}(%s %s)${C_RESET}                     ${C_CYAN}│${C_RESET}\r" "$now" "$day" "$zone"
    sleep 1
  done
}

cmd::date() {
  printf "${C_CYAN}📅 ${C_BOLD}%s${C_RESET}\n" "$(date '+%A, %B %d, %Y')"
  printf "  ${C_DIM}Full:${C_RESET} %s\n" "$(date '+%Y-%m-%d %H:%M:%S %Z')"
  printf "  ${C_DIM}Unix:${C_RESET} %s\n" "$(date +%s)"
}

# ── calc (terminal calculator) ────────────────────────────────────────
cmd::calc() {
  local expr="$*"
  if [[ -z $expr ]]; then
    ui::say_status WARN "Usage: calc <expression>"
    ui::say_status INFO "Example: calc 2+2, calc '(10*5)/2', calc 'sqrt(144)'"
    return 1
  fi
  # Use bc for calculation, sanitize input
  local clean=$(printf '%s' "$expr" | tr -cd '0-9.+\\-*/%()sqrt ' 2>/dev/null)
  if [[ -z $clean ]]; then
    ui::say_status ERR "Invalid expression"
    return 1
  fi
  local result
  result=$(echo "scale=4; $clean" | bc 2>/dev/null)
  if [[ -z $result ]]; then
    ui::say_status ERR "Calculation error"
    return 1
  fi
  printf "${C_CYAN}🧮 ${C_BOLD}%s${C_RESET} = ${C_GREEN}%s${C_RESET}\n" "$expr" "$result"
}

# ── bible (verse lookup) ─────────────────────────────────────────────
cmd::bible() {
  cmd::_need_curl || return 1
  local ref="${*:-John 3:16}"
  
  # Parse reference
  local book chapter verse
  book=$(printf '%s' "$ref" | grep -oE '^[0-9a-zA-Z]+' | head -1)
  chapter=$(printf '%s' "$ref" | grep -oE '[0-9]+:[0-9]+' | head -1 | cut -d: -f1)
  verse=$(printf '%s' "$ref" | grep -oE '[0-9]+:[0-9]+' | head -1 | cut -d: -f2)
  
  if [[ -z $book || -z $chapter || -z $verse ]]; then
    ui::say_status WARN "Usage: bible <book chapter:verse>"
    ui::say_status INFO "Example: bible John 3:16, bible Genesis 1:1"
    return 1
  fi
  
  # Using bible-api.com (free, no key needed)
  local api_ref=$(printf '%s' "$ref" | sed 's/ /%20/g')
  local data
  data=$(curl -fsSL --max-time 8 "https://bible-api.com/$api_ref" 2>/dev/null)
  
  if [[ -z $data ]]; then
    ui::say_status ERR "Verse not found or service unreachable"
    return 1
  fi
  
  local text=$(printf '%s' "$data" | grep -oE '"text":"[^"]+"' | head -1 | cut -d'"' -f4 | sed 's/\\n/ /g' | xargs)
  local ref_out=$(printf '%s' "$data" | grep -oE '"reference":"[^"]+"' | head -1 | cut -d'"' -f4)
  
  if [[ -z $text ]]; then
    ui::say_status ERR "Could not parse verse"
    return 1
  fi
  
  # Display with nice formatting
  local top="┌─────────────────────────────────────────────────────────────────┐"
  local bot="└─────────────────────────────────────────────────────────────────┘"
  
  printf "\n${C_CYAN}%s${C_RESET}\n" "$top"
  printf "${C_CYAN}│${C_RESET}  ${C_YELLOW}📖 ${C_BOLD}%s${C_RESET}                                      ${C_CYAN}│${C_RESET}\n" "${ref_out:-$ref}"
  printf "${C_CYAN}│${C_RESET}                                                                ${C_CYAN}│${C_RESET}\n"
  
  # Word wrap the verse text
  local words=($text)
  local line=""
  for word in "${words[@]}"; do
    if ((${#line} + ${#word} + 1 > 60)); then
      printf "${C_CYAN}│${C_RESET}  %s ${C_CYAN}│${C_RESET}\n" "$line"
      line=""
    fi
    line+="$word "
  done
  [[ -n $line ]] && printf "${C_CYAN}│${C_RESET}  %s ${C_CYAN}│${C_RESET}\n" "$line"
  
  printf "${C_CYAN}%s${C_RESET}\n\n" "$bot"
}

# ── apps (launcher listing) ──────────────────────────────────────────
cmd::apps() {
  printf "${C_CYAN}${C_BOLD}🚀 nebula App Launcher${C_RESET}\n"
  printf "${C_GRAY}────────────────────────────────────────────${C_RESET}\n"
  
  local -a apps=(
    "weather ⛅ Weather forecast (wttr.in)"
    "crypto 💰 Cryptocurrency prices"
    "news 📰 Hacker News headlines"
    "calc 🧮 Terminal calculator"
    "bible 📖 Bible verse lookup"
    "define 📖 Dictionary lookup"
    "ip 🌐 Public IP & geolocation"
    "timer ⏳ Pomodoro timer"
    "notes 📝 View/edit notes"
    "todo ✅ Todo list manager"
    "ask 🤖 Ask Nebula AI (AI assistant)"
    "joke 😄 Random jokes"
    "fact 💡 Fun facts"
    "qr 🖼 Generate QR codes"
    "sysinfo 💻 System information"
    "time ⏰ Live clock"
    "theme 🎨 Switch prompt theme"
    "doctor 🩺 System health check"
  )
  
  for app in "${apps[@]}"; do
    local cmd="${app%% *}"
    local desc="${app#* }"
    printf "  ${C_GREEN}%-12s${C_RESET} %s\n" "$cmd" "$desc"
  done
  
  printf "\n${C_GRAY}────────────────────────────────────────────${C_RESET}\n"
  printf "${C_DIM}Usage: nebula <command>${C_RESET}\n"
}

# `nebula voice on|off` and `nebula sounds on|off` (also in Settings → Features)
cmd::voice() { cmd::voice_toggle "$@"; }
cmd::sounds() {
  case "${1:-}" in
    on|off)
      local v=1; [[ $1 == off ]] && v=0
      mkdir -p "$NEBULA_CFG"; echo "$v" > "$NEBULA_CFG/sounds"; export NEBULA_SOUNDS=$v
      ui::say_status OK "UI sounds $1." ;;
    *) ui::say_status INFO "UI sounds are $([[ ${NEBULA_SOUNDS:-1} -eq 0 ]] && echo off || echo on).  Use: sounds on|off" ;;
  esac
}
