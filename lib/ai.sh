#!/data/data/com.termux/files/usr/bin/env bash
# nebula — Nebula AI commands: chat, explain, fix, summarize, translate

# ai::_complete <prompt>  → prints the reply (non-streaming)
ai::_complete() {
  local out
  out=$(tgpt -q "$1" 2>/dev/null)
  [[ -z $out ]] && out=$(tgpt "$1" 2>/dev/null)
  printf '%s\n' "$out"
}

# Run ai::_complete with a small "thinking" indicator on a real terminal
ai::_think() {
  local tmp; tmp=$(mktemp "${TMPDIR:-${PREFIX:-/tmp}/tmp}/nebula-ai.XXXXXX" 2>/dev/null || mktemp)
  ai::_complete "$1" > "$tmp" &
  local pid=$! i=0 sp=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
  if [[ -t 1 ]]; then
    while kill -0 "$pid" 2>/dev/null; do
      printf '\r  %s%s%s Nebula AI is thinking…' "$C_CYAN" "${sp[i++ % 10]}" "$C_RESET"
      sleep 0.12
    done
    printf '\r\033[2K'
  fi
  wait "$pid" 2>/dev/null
  md::render < "$tmp"; rm -f "$tmp"
}

# ── chat ────────────────────────────────────────────────────────────────
cmd::chat() {
  cmd::_need_tgpt || return 1
  local dir="$NEBULA_CFG/chats"; mkdir -p "$dir"
  local log="$dir/chat-$(date +%Y%m%d-%H%M%S).md"
  local transcript="" msg reply prompt
  printf "\n${C_CYAN}${C_BOLD}💬 Nebula AI chat${C_RESET}  ${C_DIM}/clear forget · /help · /exit${C_RESET}\n\n"
  while :; do
    printf "${C_MAGENTA}you ❯${C_RESET} "
    IFS= read -r msg || break
    case "$msg" in
      "") continue ;;
      /exit|/quit|/q) break ;;
      /clear) transcript=""; ui::say_status OK "Context cleared."; continue ;;
      /help)  printf "  ${C_DIM}/clear  forget the conversation so far\n  /exit   leave chat (log is saved)\n  anything else is sent to Nebula AI${C_RESET}\n"; continue ;;
    esac
    prompt="You are Nebula AI, a concise, friendly assistant inside a phone terminal (Termux). Keep answers short unless asked for detail.
Conversation so far:
${transcript}
User: ${msg}
Nebula AI:"
    printf "  ${C_CYAN}⠿${C_RESET} ${C_DIM}Nebula AI is thinking…${C_RESET}\r"
    reply=$(ai::_think "$prompt"); printf '\033[2K\r'
    if [[ -z $reply ]]; then ui::say_status ERR "No reply (network?)"; continue; fi
    printf "${C_BLUE}${C_BOLD}🤖 Nebula AI${C_RESET}\n"; printf '%s\n' "$reply" | md::render; printf '\n'
    transcript+="User: ${msg}
Nebula AI: ${reply}
"
    transcript=${transcript: -4000}
    printf '**you:** %s\n\n**nebula ai:** %s\n\n' "$msg" "$reply" >> "$log"
    voice::say "$(md::plain "${reply:0:240}")"
  done
  [[ -s $log ]] && ui::say_status INFO "Chat saved: $log"
}

# ── explain ─────────────────────────────────────────────────────────────
cmd::explain() {
  cmd::_need_tgpt || return 1
  local c="$*"
  if [[ -z $c && -s $NEBULA_CFG/.last_cmd ]]; then
    c=$(<"$NEBULA_CFG/.last_cmd")
    ui::say_status INFO "Explaining your last command: $c"
  fi
  [[ -z $c ]] && { ui::say_status WARN "Usage: explain <command>"; return 1; }
  printf "${C_BLUE}🤖 Nebula AI:${C_RESET}\n"
  ai::_think "Explain this shell command for someone using Termux on Android. Start with a one-line summary, then briefly break down each part, and warn clearly if it could delete data or is risky. Be brief.

$c"
}

# ── fix ─────────────────────────────────────────────────────────────────
# The shell records the last failed command to data/.last_fail as "rc|command"
cmd::fix() {
  cmd::_need_tgpt || return 1
  local f="$NEBULA_CFG/.last_fail" rc cmd extra="$*"
  if [[ ! -s $f && -z $extra ]]; then
    ui::say_status INFO "No failed command recorded yet. Run something, then type: fix"
    return 0
  fi
  if [[ -s $f ]]; then IFS='|' read -r rc cmd < "$f"; fi
  [[ -n ${cmd:-} ]] && printf "  ${C_DIM}Last failed:${C_RESET} %s ${C_DIM}(exit %s)${C_RESET}\n" "$cmd" "$rc"
  printf "${C_BLUE}🤖 Nebula AI:${C_RESET}\n"
  ai::_think "I am using Termux on Android (bash/zsh). A command failed.
Command: ${cmd:-unknown}
Exit code: ${rc:-unknown}
Extra error text from me: ${extra:-none}
Explain the most likely cause in 1-2 sentences, then give the corrected command(s) in a code block. Be brief."
  printf "\n${C_DIM}Nebula never runs suggestions for you — review before pasting.${C_RESET}\n"
}

# ── summarize ───────────────────────────────────────────────────────────
cmd::summarize() {
  cmd::_need_tgpt || return 1
  local src=${1:-} text
  if [[ $src == - ]]; then
    text=$(head -c 8000)
  elif [[ -z $src ]]; then
    ui::say_status WARN "Usage: summarize <file>   (or: cat file | nebula summarize -)"; return 1
  elif [[ ! -f $src ]]; then
    ui::say_status ERR "File not found: $src"; return 1
  elif ! grep -Iq . "$src" 2>/dev/null; then
    ui::say_status ERR "That looks like a binary file."; return 1
  else
    text=$(head -c 8000 "$src")
    (( $(wc -c < "$src") > 8000 )) && ui::say_status INFO "File is large — summarizing the first 8 KB."
  fi
  printf "${C_BLUE}🤖 Nebula AI:${C_RESET}\n"
  ai::_think "Summarize the following in at most 6 short bullet points.

$text"
}

# ── translate ───────────────────────────────────────────────────────────
cmd::translate() {
  cmd::_need_tgpt || return 1
  local lang=${1:-}; shift 2>/dev/null
  local text="$*"
  if [[ -z $lang || -z $text ]]; then
    ui::say_status WARN "Usage: translate <language> <text>   e.g. translate swahili good morning"
    return 1
  fi
  printf "${C_BLUE}🤖 Nebula AI:${C_RESET}\n"
  ai::_think "Translate the following text into ${lang}. Reply with only the translation.

$text"
}

# ── ask ─────────────────────────────────────────────────────────────────
cmd::ask() {
  cmd::_need_tgpt || return 1
  local q="$*"
  [[ -z $q ]] && { ui::say_status WARN "Usage: ask <question>"; return 1; }
  printf "${C_BLUE}${C_BOLD}🤖 Nebula AI${C_RESET}\n"
  ai::_think "$q"
}
