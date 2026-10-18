# nebula prompt theme: minimal — monochrome grey, no external deps.
# Everything (path, git, prompt char, clock) sits in soft greys so the
# prompt fades into the background.

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
    dirty='%F{245}±%f'
  else
    dirty='%F{245}✓%f'
  fi
  printf ' %%F{244}(%%F{250}%s%%F{244})%s' "$b" "$dirty"
}

_nebula_rp() {
  local out=""
  (( ${_NEBULA_LAST_DUR:-0} > 1 )) && out+="%F{244}⏱ ${_NEBULA_LAST_DUR}s%f  "
  (( ${_NEBULA_LAST_STATUS:-0} != 0 )) && out+="%F{244}✖ ${_NEBULA_LAST_STATUS}%f"
  printf '%s' "$out"
}

# Two-line, all-grey: path + git on line 1, soft prompt char on line 2.
PROMPT=$'\n%F{250}%~%f$(_nebula_git)\n%(?.%F{244}.%F{245})❯%f '
RPROMPT='$(_nebula_rp)%F{244} %D{%H:%M:%S}%f'
