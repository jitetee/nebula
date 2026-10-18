# Nebula suggest engine — as-you-type ghost text. Pure zsh: no forks per keystroke.
#
#   cd <Tab>-less hints : "cd" → your most-visited folder; "cd th" → thesis/ (cwd child
#                         or a frecent folder); partial names match anywhere.
#   nebula <x>          : Nebula command names; "nebula install <x>" → tool names
#   anything else       : most recent matching history line, then command names
#   →  / Ctrl-F / End   : accept      Alt-F : accept one word
#
# Tab opens Nebula's own fuzzy picker (see plugins/nebula-pick).

: ${NSH_AUTOSUGGEST_COLOR:='fg=244'}
: ${NSH_AUTOSUGGEST_HINT:='fg=240'}
zmodload zsh/datetime 2>/dev/null

typeset -g  _nsh_sugg=""            # text appended after the cursor
typeset -g  _nebula_sugg_full=""    # when set, accepting REPLACES the whole buffer
typeset -g  _nebula_last_buf="" _nebula_last_cur=-1
typeset -gi _nebula_frecent_stale=1
typeset -ga _nebula_frecent=() _nebula_cmdnames=() _nebula_registry=()

# ── data sources (loaded once, refreshed lazily) ────────────────────────
_nebula_frecent_load() {
  emulate -L zsh
  _nebula_frecent_stale=0
  local f=${_Z_DATA:-${NEBULA_CFG:-$HOME}/.nsh_z} d r t mult age now=$EPOCHSECONDS
  local -a rows=()
  [[ -r $f ]] || { _nebula_frecent=(); return }
  while IFS='|' read -r d r t; do
    [[ -d $d ]] || continue
    age=$(( now - ${t:-0} ))
    if   (( age < 3600 ));   then mult=4
    elif (( age < 86400 ));  then mult=2
    elif (( age < 604800 )); then mult=0.5
    else                          mult=0.25; fi
    rows+=( "$(printf '%012d' $(( ${r:-1} * mult * 100 )))|$d" )
  done < $f
  _nebula_frecent=( ${${(On)rows}#*|} )
}
_nebula_mark_stale() { _nebula_frecent_stale=1 }
_nebula_names_load() {
  emulate -L zsh
  local reg="${NEBULA_HOME}/assets/help.txt" l
  local -a hidden=() all=()
  [[ -s $NEBULA_CFG/hidden.txt ]] && hidden=( ${=$(<"$NEBULA_CFG/hidden.txt")} )
  [[ -r $reg ]] && while IFS= read -r l; do [[ $l == @* ]] && all+=( ${${l%%|*}#@} ); done < "$reg"
  _nebula_cmdnames=( ${all:|hidden} )
}
_nebula_registry_load() {
  emulate -L zsh
  local f="${NEBULA_HOME}/assets/registry.txt" l
  [[ -r $f ]] || return
  _nebula_registry=()
  while IFS= read -r l; do [[ $l == \#* || -z $l ]] || _nebula_registry+=( ${l%%|*} ); done < "$f"
}

# ── the suggestion ──────────────────────────────────────────────────────
_nebula_suggest() {
  emulate -L zsh
  setopt extendedglob nonomatch
  _nsh_sugg=""; _nebula_sugg_full=""; POSTDISPLAY=""; region_highlight=()
  [[ -z $BUFFER || $CURSOR -ne ${#BUFFER} ]] && return
  local b=$BUFFER ghost="" hint="" full="" i m

  # ── cd / pushd / z : folders ────────────────────────────────────────
  if [[ $b == (cd|pushd|z) || $b == (cd|pushd|z)\ * ]]; then
    (( _nebula_frecent_stale )) && _nebula_frecent_load
    local cmd=${b%% *} arg=""
    [[ $b == *" "* ]] && arg=${b#* }
    arg=${arg## #}
    local abs="" name="" kind=""
    if [[ -z $arg ]]; then
      for m in $_nebula_frecent; do [[ $m != $PWD ]] && { abs=$m; break }; done
      if [[ -z $abs ]]; then local -a kids; kids=( *(/N[1]) ); [[ -n $kids ]] && abs=$PWD/${kids[1]}; fi
      if [[ -n $abs ]]; then
        [[ $b == *" " ]] && ghost="${abs/#$HOME/~}" || ghost=" ${abs/#$HOME/~}"
        full="$cmd ${(q)abs}"
      fi
    elif [[ $arg == */* || $arg == [.~]* ]]; then
      local exp=${arg/#\~/$HOME}; local -a hits
      hits=( ${~${(q)exp}}*(/N[1]) )
      [[ -n $hits ]] && { ghost="${hits[1]#$exp}/"; [[ $arg == \~* ]] && :; }
    elif [[ $arg != *[\*\?\[]* ]]; then
      local -a kids; kids=( ${~${(q)arg}}*(/N) )
      if (( ${#kids} == 1 )); then
        ghost="${kids[1]#$arg}/"; full="$cmd ${(q)kids[1]}/"
      else
        for m in $_nebula_frecent; do
          [[ ${m:t} == (#i)${arg}* && $m != $PWD ]] && { abs=$m; kind=prefix; break }
        done
        if [[ -z $abs && -n $kids ]]; then ghost="${kids[1]#$arg}/"; full="$cmd ${(q)kids[1]}/"
        elif [[ -n $abs ]]; then
          name=${abs:t}; ghost="${name#$arg}"; hint="  → ${abs/#$HOME/~}"; full="$cmd ${(q)abs}"
        else
          for m in $_nebula_frecent; do
            [[ ${m:t} == (#i)*${arg}* && $m != $PWD ]] && { hint="  → ${m/#$HOME/~}"; full="$cmd ${(q)m}"; break }
          done
        fi
      fi
    fi
  fi

  # ── nebula subcommands ──────────────────────────────────────────────
  if [[ -z $ghost && -z $hint && $b == nebula\ * ]]; then
    local a=${b#nebula }
    if [[ $a != *" "* ]]; then
      (( ${#_nebula_cmdnames} )) || _nebula_names_load
      for m in $_nebula_cmdnames; do [[ $m == ${a}?* ]] && { ghost=${m#$a}; break }; done
    elif [[ $a == (install|uninstall|remove)\ * && $a != *" "*" "* ]]; then
      local q=${a#* }
      (( ${#_nebula_registry} )) || _nebula_registry_load
      for m in $_nebula_registry; do [[ $m == ${q}?* ]] && { ghost=${m#$q}; break }; done
    fi
  fi

  # ── history (newest first) ──────────────────────────────────────────
  if [[ -z $ghost && -z $hint ]]; then
    local lim=$(( HISTNO > 1500 ? HISTNO - 1500 : 1 ))
    for (( i = HISTNO - 1; i >= lim; i-- )); do
      m=${history[$i]}
      [[ ${#m} -gt ${#b} && ${m[1,${#b}]} == $b ]] && { ghost=${m[${#b}+1,-1]}; break }
    done
  fi

  # ── command names (first word only) ─────────────────────────────────
  if [[ -z $ghost && -z $hint && $b != *[[:space:]]* && ${#b} -ge 2 ]]; then
    (( ${#_nebula_cmdnames} )) || _nebula_names_load
    for m in $_nebula_cmdnames; do [[ $m == ${b}?* ]] && { ghost=${m#$b}; break }; done
    if [[ -z $ghost ]]; then
      local -a cs; cs=( ${(k)commands[(I)${b}?*]} )
      (( ${#cs} )) && { cs=( ${(o)cs} ); ghost=${${cs[1]}#$b}; }
    fi
  fi

  [[ -z $ghost && -z $hint ]] && return
  _nsh_sugg="$ghost$hint"; _nebula_sugg_full=$full
  POSTDISPLAY="$_nsh_sugg"
  local e1=$(( ${#BUFFER} + ${#ghost} )) e2=$(( ${#BUFFER} + ${#ghost} + ${#hint} ))
  (( ${#ghost} )) && region_highlight+=( "${#BUFFER} $e1 ${NSH_AUTOSUGGEST_COLOR}" )
  (( ${#hint}  )) && region_highlight+=( "$e1 $e2 ${NSH_AUTOSUGGEST_HINT}" )
}

# recompute only when the line really changed (works for every editing widget)
_nebula_suggest_redraw() {
  [[ $BUFFER == $_nebula_last_buf && $CURSOR -eq $_nebula_last_cur ]] && return
  _nebula_last_buf=$BUFFER; _nebula_last_cur=$CURSOR
  _nebula_suggest
}
autoload -Uz add-zle-hook-widget add-zsh-hook 2>/dev/null
if (( $+functions[add-zle-hook-widget] )); then
  add-zle-hook-widget line-pre-redraw _nebula_suggest_redraw
fi
add-zsh-hook chpwd _nebula_mark_stale
add-zsh-hook precmd _nebula_mark_stale
_nsh_suggest() { _nebula_suggest }          # kept for older callers

# ── accepting ───────────────────────────────────────────────────────────
_nsh_accept() {
  if [[ -n $_nebula_sugg_full ]]; then
    BUFFER=$_nebula_sugg_full; CURSOR=${#BUFFER}; POSTDISPLAY=""; _nsh_sugg=""; _nebula_sugg_full=""; region_highlight=()
  elif [[ -n $POSTDISPLAY ]]; then
    BUFFER="$BUFFER$POSTDISPLAY"; CURSOR=${#BUFFER}; POSTDISPLAY=""; region_highlight=()
  else
    zle .forward-char 2>/dev/null || zle .end-of-line
  fi
}
_nsh_accept_word() {
  if [[ -n $POSTDISPLAY && -z $_nebula_sugg_full ]]; then
    local word="${POSTDISPLAY%% *} "
    [[ $POSTDISPLAY == *" "* ]] || word=$POSTDISPLAY
    BUFFER="$BUFFER$word"; CURSOR=${#BUFFER}; POSTDISPLAY="${POSTDISPLAY#$word}"
    region_highlight=( "${#BUFFER} $(( ${#BUFFER} + ${#POSTDISPLAY} )) ${NSH_AUTOSUGGEST_COLOR}" )
  elif [[ -n $_nebula_sugg_full ]]; then _nsh_accept
  else zle .forward-word 2>/dev/null; fi
}
zle -N _nsh_accept
zle -N _nsh_accept_word
_nsh_accept_line() { POSTDISPLAY=""; zle .accept-line }
zle -N accept-line _nsh_accept_line

bindkey '^[[C' _nsh_accept
bindkey '^F'   _nsh_accept
bindkey '^[[F' _nsh_accept
bindkey '^E'   _nsh_accept
bindkey '^[f'  _nsh_accept_word
