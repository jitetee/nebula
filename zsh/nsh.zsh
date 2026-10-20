# NSH — Nebula Shell framework
# A small, self-contained zsh framework. Replaces oh-my-zsh for nebula users.
# Everything is custom-made in-house.

: ${NSH_HOME:=${0:A:h}}
export NSH_HOME

# ── 1. history ────────────────────────────────────────────────────────────
if (( ! ${NSH_SKIP_HISTORY:-0} )); then
  HISTFILE=${HISTFILE:-${NEBULA_CFG:-$HOME}/.zsh_history}
  HISTSIZE=50000
  SAVEHIST=50000
  setopt HIST_IGNORE_DUPS HIST_IGNORE_SPACE HIST_REDUCE_BLANKS
  setopt SHARE_HISTORY APPEND_HISTORY INC_APPEND_HISTORY
fi

# ── 2. completion ─────────────────────────────────────────────────────────
if (( ! ${NSH_SKIP_COMPLETION:-0} )); then
  autoload -Uz compinit
  compinit -C 2>/dev/null
  zstyle ":completion:*" menu select
  zstyle ":completion:*" matcher-list "m:{a-zA-Z}={A-Za-z}"
  zstyle ":completion:*" list-colors ""

# nebula <TAB>: command names from the help registry, plus per-command arguments
_nebula_complete() {
  local reg="${NEBULA_HOME:-$NSH_HOME/..}/assets/help.txt" cur sub
  local -a names
  names=(${(f)"$(awk -F'|' '/^@/{print substr($1,2)}' "$reg" 2>/dev/null)"})
  [[ -s $NEBULA_CFG/hidden.txt ]] && names=(${names:|${=$(<"$NEBULA_CFG/hidden.txt")}})
  if (( CURRENT == 2 )); then
    compadd -a names
  else
    sub=${words[2]}
    case $sub in
      help)        compadd -a names search ;;
      theme)       compadd builder set reset nebula minimal forest sky custom ;;
      backup)      compadd --encrypt --plain ;;
      restore)     compadd latest ;;
      fingerprint) compadd on off status ;;
      autolock)    compadd off 1 5 10 30 ;;
      remind)      compadd list rm check 10m 30m 1h ;;
      todo)        compadd done pri rm clear ;;
      notes)       compadd search rm edit ;;
      doctor)      compadd --fix ;;
      *)           _files ;;
    esac
  fi
}
(( $+functions[compdef] )) && compdef _nebula_complete nebula
fi

# ── 3. custom key bindings & history search ──────────────────────────────
bindkey -e  # emacs-style

# In-house history prefix search
_nsh_h_pos=0
_nsh_h_query=""

_nsh_history_search_backward() {
  if [[ $LASTWIDGET != _nsh_history_search_* ]]; then
    _nsh_h_query=$LBUFFER
    _nsh_h_pos=$HISTCMD
  fi
  
  if [[ -z $_nsh_h_query ]]; then
    zle .up-line-or-history
    return
  fi

  local i=$_nsh_h_pos
  while (( --i > 0 )); do
    if [[ $history[$i] == $_nsh_h_query* && $history[$i] != $BUFFER ]]; then
      BUFFER=$history[$i]
      CURSOR=${#BUFFER}
      _nsh_h_pos=$i
      return
    fi
  done
}

_nsh_history_search_forward() {
  if [[ $LASTWIDGET != _nsh_history_search_* ]]; then
    zle .down-line-or-history
    return
  fi

  local i=$_nsh_h_pos
  while (( ++i < HISTCMD )); do
    if [[ $history[$i] == $_nsh_h_query* && $history[$i] != $BUFFER ]]; then
      BUFFER=$history[$i]
      CURSOR=${#BUFFER}
      _nsh_h_pos=$i
      return
    fi
  done
  
  if [[ $i -ge $HISTCMD ]]; then
    BUFFER=$_nsh_h_query
    CURSOR=${#BUFFER}
    _nsh_h_pos=$HISTCMD
  fi
}

zle -N _nsh_history_search_backward
zle -N _nsh_history_search_forward
bindkey "^[[A" _nsh_history_search_backward
bindkey "^[[B" _nsh_history_search_forward
bindkey "^[[1;5C" forward-word
bindkey "^[[1;5D" backward-word

# ── 4. plugins ──────────────────────────────────────────────────────────
if (( ! ${NSH_SKIP_AUTOSUGGEST:-0} )); then
  [[ -f "$NSH_HOME/plugins/autosuggestions/autosuggestions.zsh" ]] &&     source "$NSH_HOME/plugins/autosuggestions/autosuggestions.zsh"
fi

if (( ! ${NSH_SKIP_Z:-0} )); then
  [[ -f "$NSH_HOME/plugins/z/z.sh" ]] && source "$NSH_HOME/plugins/z/z.sh"
fi

# Nebula's own fuzzy picker on Tab / Ctrl-R / Ctrl-T / Alt-C (no fzf)
if (( ! ${NSH_SKIP_PICK:-0} )); then
  [[ -f "$NSH_HOME/plugins/nebula-pick/nebula-pick.zsh" ]] && source "$NSH_HOME/plugins/nebula-pick/nebula-pick.zsh"
fi

if (( ! ${NSH_SKIP_SYNTAX:-0} )); then
  [[ -f "$NSH_HOME/plugins/syntax-highlighting/syntax-highlighting.zsh" ]] &&     source "$NSH_HOME/plugins/syntax-highlighting/syntax-highlighting.zsh"
fi

# ── 5. prompt theme ──────────────────────────────────────────────────────
if (( ! ${NSH_SKIP_THEME:-0} )); then
  local _nsh_theme="studio"
  if [[ -f "$NEBULA_CFG/theme" ]]; then
    local _t=$(<"$NEBULA_CFG/theme")
    [[ -f "$NEBULA_CFG/themes/${_t}.zsh-theme" ]] && _nsh_theme=$_t      # a user-imported classic .zsh-theme
  fi
  if [[ $_nsh_theme == studio ]]; then source "$NSH_HOME/themes/studio.zsh-theme"
  else source "$NEBULA_CFG/themes/${_nsh_theme}.zsh-theme"; fi
  unset _nsh_theme
fi

# ── 6. in-house ls with icons ───────────────────────────────────────────
_nebula_ls() {
  ls -F --color=auto "$@" | while read -r line; do
    local icon="📄"
    case "$line" in
      */*) icon="📂" ;;
      *\*) icon="🏗" ;;
      *.sh) icon="🏗" ;;
      *.md) icon="📝" ;;
      *.txt) icon="📄" ;;
      *.py|*.js|*.go|*.c|*.cpp) icon="⚙️" ;;
    esac
    printf "%s  %s\n" "$icon" "$line"
  done
}

alias ls="_nebula_ls"
alias ll="_nebula_ls -lh"
alias la="_nebula_ls -lah"

# ── 6b. nebula commands inside plain zsh ─────────────────────────────────
# Names from the help registry (space-padded for fast matching)
_nebula_names=" $(awk -F'|' '/^@/{print substr($1,2)}' "${NEBULA_HOME:-$NSH_HOME/..}/assets/help.txt" 2>/dev/null | tr '\n' ' ') "

# Typing a Nebula command (status, backup, remind, fix…) just works; typos get
# a "did you mean".
command_not_found_handler() {
  local c=$1
  if [[ -n $c && $_nebula_names == *" $c "* ]]; then
    "${NEBULA_HOME}/bin/nebula" "$@"
    return $?
  fi
  # Not a Nebula command. At a real terminal, offer to install the missing tool
  # (gh, ffmpeg, …) and re-run what you typed, or to turn a sentence into commands.
  if [[ -o interactive && -t 0 && -t 1 && -n $c && $c != */* ]]; then
    "${NEBULA_HOME}/bin/nebula" cnf "$@"
    case $? in
      0)  rehash; "$@"; return $? ;;
      20) _nebula_run_plan; return $? ;;
    esac
  fi
  print -u2 -P "%F{203}zsh: command not found: $c%f"
  "${NEBULA_HOME}/lib/suggest.sh" "$c" >&2
  return 127
}

# run a plan Nebula AI wrote (already reviewed and confirmed) in THIS shell, so cd/export stick
_nebula_run_plan() {
  local f="$NEBULA_CFG/.plan.sh" l rc=0
  [[ -s $f ]] || return 1
  while IFS= read -r l; do
    [[ -z $l ]] && continue
    print -s -- "$l"
    print -P "%F{245}❯%f $l"
    eval "$l"; rc=$?
    (( rc )) && { print -P "%F{203}✖ stopped (exit $rc)%f — try: fix"; break; }
  done < "$f"
  rm -f "$f"; return $rc
}
# tell <request> — plain English → reviewed commands, run in this shell
tell() {
  local f="$NEBULA_CFG/.plan.sh"; rm -f "$f"
  "${NEBULA_HOME}/bin/nebula" tell --out "$f" "$@" || return $?
  [[ -s $f ]] && _nebula_run_plan
}

# Remember the last command + last failure so `fix` / `explain` can use them
_nebula_lastcmd=""
_nebula_rec_preexec() { _nebula_lastcmd=$1 }
_nebula_rec_precmd() {
  local rc=$?
  if [[ -n $_nebula_lastcmd && -n $NEBULA_CFG && -d $NEBULA_CFG ]]; then
    case ${_nebula_lastcmd%% *} in
      fix|explain|help|chat|ask|nebula) ;;
      *)
        print -r -- "$_nebula_lastcmd" >| "$NEBULA_CFG/.last_cmd"
        (( rc )) && print -r -- "$rc|$_nebula_lastcmd" >| "$NEBULA_CFG/.last_fail"
        ;;
    esac
  fi
  _nebula_lastcmd=""
  # reminders that fired without a phone notification path
  [[ -s "$NEBULA_CFG/reminders.due" ]] && "$NEBULA_HOME/bin/nebula" remind due
  return $rc    # keep $? intact for the prompt theme
}
autoload -Uz add-zsh-hook
add-zsh-hook preexec _nebula_rec_preexec
add-zsh-hook precmd  _nebula_rec_precmd

# ── hardware keys (Termux extra-keys row sends Alt+digit) ──────────────
# Alt-1 vol- · Alt-2 vol+ · Alt-3 mute · Alt-4 brightness- · Alt-5 brightness+ · Alt-6 torch · Alt-7 lock
_nebula_hwkey() {  # silent: result shows as a one-line message under the prompt
  local out; out=$("$NSH_HOME/../lib/hwkey.sh" "$@" 2>&1 | head -n1)
  zle -M "$out"
}
_nebula_hw_1() { _nebula_hwkey vol down }
_nebula_hw_2() { _nebula_hwkey vol up }
_nebula_hw_3() { _nebula_hwkey vol mute }
_nebula_hw_4() { _nebula_hwkey bright down }
_nebula_hw_5() { _nebula_hwkey bright up }
_nebula_hw_6() { _nebula_hwkey torch }
for _k in 1 2 3 4 5 6; do zle -N _nebula_hw_$_k; bindkey "^[$_k" _nebula_hw_$_k; done
_nebula_lock_key() { zle -I; "$NSH_HOME/../lib/lock.sh" || exit 1; zle reset-prompt; }
zle -N _nebula_lock_key; bindkey '^[7' _nebula_lock_key
unset _k

# ── 7. other aliases ────────────────────────────────────────────────────
alias ..="cd .."
alias c="clear"
alias gs="git status"

# session lock (3 wrong passwords close the whole session)
if (( ! ${NSH_SKIP_AUTH:-0} )) && [[ -o interactive && -z $NEBULA_REPL ]]; then
  [[ -x "$NSH_HOME/../lib/session-auth.sh" ]] && { "$NSH_HOME/../lib/session-auth.sh" || exit 1; }

  # idle auto-lock: re-prompt for the password after N minutes at the prompt
  if [[ ! -f "$NEBULA_CFG/no-lock" && -f "$NEBULA_CFG/auth" ]]; then
    _nebula_al=10
    [[ -f "$NEBULA_CFG/autolock" ]] && _nebula_al=$(<"$NEBULA_CFG/autolock")
    if [[ $_nebula_al == <-> ]] && (( _nebula_al > 0 )); then
      TMOUT=$(( _nebula_al * 60 ))
      TRAPALRM() {
        zle -I 2>/dev/null
        "$NSH_HOME/../lib/lock.sh" || exit 1
        zle reset-prompt 2>/dev/null
        return 0     # a trap must return 0 or zsh aborts the current line
      }
    fi
    unset _nebula_al
  fi
fi

# motd
if (( ! ${NSH_SKIP_MOTD:-0} )) && [[ -o interactive ]]; then
  _nsh_motd="$NSH_HOME/../motd/init.sh"
  if [[ -r $_nsh_motd ]]; then
    _nebula_show_motd() {
      [[ -x $_nsh_motd ]] && "$_nsh_motd" || bash "$_nsh_motd"
      add-zsh-hook -d precmd _nebula_show_motd
      [[ -s "$NEBULA_CFG/reminders" ]] && "$NEBULA_HOME/bin/nebula" remind check
    }
    autoload -Uz add-zsh-hook
    add-zsh-hook precmd _nebula_show_motd
  fi
fi
