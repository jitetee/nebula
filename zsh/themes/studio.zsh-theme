# Nebula prompt studio engine
#
# Builds PROMPT / RPROMPT from  $NEBULA_CFG/prompt.conf  (edited with `theme studio`).
# Everything dynamic is computed once per prompt in precmd, so nothing forks while
# you type, and the config is re-read automatically whenever the file changes
# (so studio edits show up in the shell you are using, no restart).
#
# prompt.conf keys (all validated; unknown or odd values are ignored):
#   layout    one | two
#   segments  left:  time user host path git venv jobs battery
#   right     right: status duration battery time jobs venv
#   char      1-3 characters         sep   space dot pipe slash arrow none
#   path_mode full trunc short dir   git_style  dirty branch off
#   time_fmt  %H:%M:%S | %H:%M | %I:%M %p | %I:%M:%S %p
#   blank 0|1   bold 0|1   c_accent c_path c_git c_time c_user c_error c_dim c_batt  (0-255)

autoload -U colors && colors
autoload -U add-zsh-hook
setopt PROMPT_SUBST
zmodload zsh/datetime 2>/dev/null
zmodload zsh/stat 2>/dev/null

typeset -gA _np
typeset -g  _np_mtime="" _np_rc=0 _np_t0=0 _np_dur=0
typeset -g  _np_v_git="" _np_v_batt="" _np_v_batt_r="" _np_v_venv="" _np_v_venv_r="" _np_v_dur="" _np_v_status="" _np_v_char="❯" _np_sepg=" "
typeset -g  _np_need_git=0 _np_need_batt=0 _np_need_venv=0 _np_conf="" _np_wb=2
typeset -ga _np_left_known=(time user host path git venv jobs battery)
typeset -ga _np_right_known=(status duration battery time jobs venv)

_np_defaults() {
  _np=(
    layout two  segments "time path git"  right "status duration"
    char "❯"  sep space  path_mode full  time_fmt "%H:%M:%S"  git_style dirty
    blank 0  bold 0  responsive 1
    c_accent 51  c_path 120  c_git 120  c_time 51  c_user 213  c_error 203  c_dim 245  c_batt 221
  )
}

# ── config (validated) ──────────────────────────────────────────────────
_np_load() {
  emulate -L zsh
  _np_conf="${NEBULA_CFG:-$HOME/.nebula}/prompt.conf"
  _np_defaults
  local k v s ok
  if [[ -r $_np_conf ]]; then
    while IFS='=' read -r k v; do
      case $k in
        layout)    [[ $v == (one|two) ]] && _np[layout]=$v ;;
        segments)  ok=(); for s in ${=v}; do (( ${_np_left_known[(Ie)$s]} )) && ok+=($s); done; _np[segments]="${ok[*]}" ;;
        right)     ok=(); for s in ${=v}; do (( ${_np_right_known[(Ie)$s]} )) && ok+=($s); done; _np[right]="${ok[*]}" ;;
        char)      [[ ${#v} -ge 1 && ${#v} -le 3 && $v != *[\`\\%]* ]] && _np[char]=$v ;;
        sep)       [[ $v == (space|dot|pipe|slash|arrow|none) ]] && _np[sep]=$v ;;
        path_mode) [[ $v == (full|trunc|short|dir) ]] && _np[path_mode]=$v ;;
        git_style) [[ $v == (dirty|branch|off) ]] && _np[git_style]=$v ;;
        time_fmt)  [[ $v == ('%H:%M:%S'|'%H:%M'|'%I:%M %p'|'%I:%M:%S %p') ]] && _np[time_fmt]=$v ;;
        blank|bold|responsive) [[ $v == [01] ]] && _np[$k]=$v ;;
        c_accent|c_path|c_git|c_time|c_user|c_error|c_dim|c_batt)
                   [[ $v == <-> && $v -le 255 ]] && _np[$k]=$v ;;
      esac
    done < "$_np_conf"
  elif [[ -r ${NEBULA_CFG:-/nonexistent}/theme.conf ]]; then      # colours from the old theme builder
    while IFS='=' read -r k v; do
      [[ $v == <-> ]] || continue
      case $k in accent) _np[c_accent]=$v; _np[c_time]=$v ;; path) _np[c_path]=$v; _np[c_git]=$v ;; error) _np[c_error]=$v ;; esac
    done < "${NEBULA_CFG}/theme.conf"
  fi
  zstat -A _np_mtime +mtime -- "$_np_conf" 2>/dev/null
}

# ── build PROMPT / RPROMPT (static strings; dynamic parts are ${_np_v_*}) ─
_np_build() {
  emulate -L zsh
  local s piece out="" sepg b="" nl=$'\n' pathx first=1
  # responsive: on narrow screens drop optional segments and shorten the path
  local w=${COLUMNS:-80} segs=${_np[segments]} rsegs=${_np[right]} pm=${_np[path_mode]} keep=""
  _np_wb=$(( w < 38 ? 0 : (w < 50 ? 1 : 2) ))
  if (( ${_np[responsive]} && _np_wb < 2 )); then
    for s in ${=segs}; do [[ $s == (path|git|jobs) ]] && keep+="$s "; done; segs=${keep% }
    rsegs="status"
    if (( _np_wb == 0 )); then pm=dir; segs=${segs//jobs/}; rsegs=""; elif [[ $pm == full ]]; then pm=short; fi
  fi
  local boff=""; (( ${_np[bold]} )) && { b="%B"; boff="%b"; }
  case ${_np[sep]} in
    space) sepg=" " ;; none) sepg="" ;;
    dot)   sepg=" %F{${_np[c_dim]}}·%f " ;;   pipe)  sepg=" %F{${_np[c_dim]}}│%f " ;;
    slash) sepg=" %F{${_np[c_dim]}}/%f " ;;   arrow) sepg=" %F{${_np[c_dim]}}›%f " ;;
  esac
  case $pm in
    full)  pathx='%~' ;;
    trunc) pathx='%(4~|…/%3~|%~)' ;;
    short) pathx='%(4~|%-1~/…/%1~|%~)' ;;
    dir)   pathx='%1~' ;;
  esac
  _np_need_git=0 _np_need_batt=0 _np_need_venv=0
  [[ " $segs " == *" git "* && ${_np[git_style]} != off ]] && _np_need_git=1
  [[ " $segs $rsegs " == *" battery "* ]] && _np_need_batt=1
  [[ " $segs $rsegs " == *" venv "* ]] && _np_need_venv=1

  for s in ${=segs}; do
    case $s in
      time)    piece="%F{${_np[c_time]}}%D{${_np[time_fmt]}}%f" ;;
      user)    piece="%F{${_np[c_user]}}%n%f" ;;
      host)    piece="%F{${_np[c_user]}}%m%f" ;;
      path)    piece="%F{${_np[c_path]}}${pathx}%f" ;;
      jobs)    piece="%(1j.%F{${_np[c_batt]}}⚙%j%f.)" ;;
      git)     piece='${_np_v_git}' ;;
      venv)    piece='${_np_v_venv}' ;;
      battery) piece='${_np_v_batt}' ;;
      *)       continue ;;
    esac
    # dynamic pieces (git/venv/battery) carry their own separator, so an empty one leaves no gap
    if [[ $s == (git|venv|battery) ]]; then out+="$piece"
    elif (( first )); then out+="$piece"
    else out+="${sepg}${piece}"; fi
    first=0
  done
  _np_sepg=$sepg

  local blank=""; (( ${_np[blank]} )) && blank=$nl
  if [[ ${_np[layout]} == one ]]; then
    PROMPT="${blank}${b}${out} \${_np_v_char}${boff} "
  else
    PROMPT="${blank}${b}${out}${boff}${nl}\${_np_v_char} "
  fi

  local r="" rs
  for rs in ${=rsegs}; do
    case $rs in
      status)   r+='${_np_v_status}' ;;
      duration) r+='${_np_v_dur}' ;;
      battery)  r+='${_np_v_batt_r}' ;;
      time)     r+=" %F{${_np[c_dim]}}%D{${_np[time_fmt]}}%f" ;;
      jobs)     r+=" %(1j.%F{${_np[c_batt]}}⚙%j%f.)" ;;
      venv)     r+='${_np_v_venv_r}' ;;
    esac
  done
  RPROMPT="${r}"
}

# ── dynamic values, once per prompt ─────────────────────────────────────
_np_git() {
  command -v git >/dev/null 2>&1 || return
  local b dirty=""
  b=$(command git symbolic-ref --short HEAD 2>/dev/null) || b=$(command git rev-parse --short HEAD 2>/dev/null) || return
  if [[ ${_np[git_style]} == dirty ]]; then
    if [[ -n $(command git status --porcelain 2>/dev/null | head -n1) ]]; then dirty="%F{221}±%f"; else dirty="%F{${_np[c_git]}}✓%f"; fi
  fi
  print -rn -- "${_np_sepg} %F{${_np[c_git]}}(${b})%f${dirty}"
}

_np_fmt_dur() {  # seconds → 3s / 1m5s / 1h2m
  local d=$1
  if   (( d >= 3600 )); then print -rn -- "$((d/3600))h$(( (d%3600)/60 ))m"
  elif (( d >= 60 ));   then print -rn -- "$((d/60))m$((d%60))s"
  else                       print -rn -- "${d}s"; fi
}

_np_precmd() {
  local rc=$?
  _np_rc=$rc
  if (( _np_t0 )); then _np_dur=$(( EPOCHSECONDS - _np_t0 )); _np_t0=0; else _np_dur=0; fi
  _NEBULA_LAST_STATUS=$rc; _NEBULA_LAST_DUR=$_np_dur       # kept for older themes/plugins

  # re-read the config when it changes (studio edits apply instantly)
  local m=""; zstat -A m +mtime -- "$_np_conf" 2>/dev/null
  if [[ "$m" != "$_np_mtime" ]]; then _np_load; _np_build
  elif (( ${_np[responsive]} )) && (( (${COLUMNS:-80} < 38 ? 0 : (${COLUMNS:-80} < 50 ? 1 : 2)) != _np_wb )); then _np_build; fi

  _np_v_char="%F{${_np[c_accent]}}${_np[char]}%f"
  (( rc )) && _np_v_char="%F{${_np[c_error]}}${_np[char]}%f"
  _np_v_status=""; (( rc )) && _np_v_status=" %F{${_np[c_error]}}✖ ${rc}%f"
  _np_v_dur=""; (( _np_dur >= 2 )) && _np_v_dur=" %F{${_np[c_dim]}}$(_np_fmt_dur $_np_dur)%f"
  _np_v_git=""; (( _np_need_git )) && _np_v_git="$(_np_git)"
  _np_v_venv=""; _np_v_venv_r=""
  if (( _np_need_venv )) && [[ -n $VIRTUAL_ENV ]]; then _np_v_venv="${_np_sepg} %F{${_np[c_git]}}(${VIRTUAL_ENV:t})%f"; _np_v_venv_r=" %F{${_np[c_git]}}(${VIRTUAL_ENV:t})%f"; fi
  _np_v_batt=""; _np_v_batt_r=""
  if (( _np_need_batt )); then
    local bf="${NEBULA_CFG}/.battery" pct st ic col age bm=""
    if [[ -r $bf ]]; then
      IFS='|' read -r pct st < "$bf"
      if [[ $pct == <-> ]]; then
        col=${_np[c_batt]}; (( pct <= 20 )) && col=${_np[c_error]}; (( pct >= 60 )) && col=${_np[c_git]}
        ic="🔋"; [[ $st == (charging|full) ]] && ic="⚡"
        _np_v_batt="${_np_sepg} %F{$col}${ic}${pct}%%%f"; _np_v_batt_r=" %F{$col}${ic}${pct}%%%f"
      fi
    fi
    zstat -A bm +mtime -- "$bf" 2>/dev/null
    if [[ -z $bm ]] || (( EPOCHSECONDS - bm > 120 )); then "${NEBULA_HOME}/lib/battcache.sh" &! ; fi
  fi
}
_np_preexec() { _np_t0=$EPOCHSECONDS }

# the studio's live preview runs this (fake data, same build code)
_np_preview() {
  emulate -L zsh
  _np_load; _np_build
  _np_rc=${1:-1}; _np_v_status=" %F{${_np[c_error]}}✖ 1%f"; _np_v_dur=" %F{${_np[c_dim]}}3s%f"
  _np_v_git=""; (( _np_need_git )) && _np_v_git="${_np_sepg} %F{${_np[c_git]}}(main)%f$([[ ${_np[git_style]} == dirty ]] && print -rn -- "%F{221}±%f")"
  _np_v_venv="${_np_sepg} %F{${_np[c_git]}}(env)%f"; _np_v_venv_r=" %F{${_np[c_git]}}(env)%f"
  _np_v_batt="${_np_sepg} %F{${_np[c_git]}}🔋82%%%f"; _np_v_batt_r=" %F{${_np[c_git]}}🔋82%%%f"
  _np_v_char="%F{${_np[c_accent]}}${_np[char]}%f"
  print -P -- "$PROMPT"
  print -rn -- $'\x1f'; print -P -- "$RPROMPT"
}

# redraw the prompt right away when the window is resized across a breakpoint
TRAPWINCH() {
  (( ${_np[responsive]} )) || return
  (( (${COLUMNS:-80} < 38 ? 0 : (${COLUMNS:-80} < 50 ? 1 : 2)) != _np_wb )) || return
  _np_build; zle && zle reset-prompt 2>/dev/null
}

_np_load
_np_build
add-zsh-hook precmd  _np_precmd
add-zsh-hook preexec _np_preexec
