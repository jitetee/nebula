# nebula prompt theme: sky — sky-blue text on grey accents, no external deps.

autoload -U colors && colors
autoload -U add-zsh-hook
setopt PROMPT_SUBST

zmodload zsh/datetime 2>/dev/null

_nebula_t0=0
_nebula_timer_start() { _nebula_t0=$EPOCHSECONDS; }
_nebula_timer_stop()  {
  _NEBULA_LAST_STATUS=$?
  if (( _nebula_t0 )); then
    _NEBULA_LAST_DUR=$(( EPOCHSECONDS - _nebula_t0 ))
    _nebula_t0=0
  else
    _NEBULA_LAST_DUR=0
  fi
}
add-zsh-hook preexec _nebula_timer_start
add-zsh-hook precmd  _nebula_timer_stop

_nebula_git() {
  command -v git >/dev/null 2>&1 || return
  local b
  b=$(command git symbolic-ref --short HEAD 2>/dev/null) \
    || b=$(command git rev-parse --short HEAD 2>/dev/null) \
    || return
  local dirty
  if [[ -n $(command git status --porcelain 2>/dev/null) ]]; then
    dirty='%F{223}±%f'
  else
    dirty='%F{117}✓%f'
  fi
  printf ' %%F{244}(%%F{117}%s%%F{244})%s' "$b" "$dirty"
}

_nebula_rp() {
  local out=""
  (( ${_NEBULA_LAST_DUR:-0} > 1 )) && out+="%F{244}⏱ ${_NEBULA_LAST_DUR}s%f  "
  (( ${_NEBULA_LAST_STATUS:-0} != 0 )) && out+="%F{203}✖ ${_NEBULA_LAST_STATUS}%f"
  printf '%s' "$out"
}

# Sky-blue path on a grey separator, sky-blue prompt char.
PROMPT=$'\n%F{117}%~%f$(_nebula_git)\n%(?.%F{117}.%F{203})❯%f '
RPROMPT='$(_nebula_rp)%F{244} %D{%H:%M:%S}%f'
