# Nebula pick — Tab / Ctrl-R / Ctrl-T / Alt-C powered by Nebula's own fuzzy
# picker (lib/pick.sh). Written from scratch; no fzf.
#
#   Tab      context-aware: commands · folders (cd) · tool names (install) ·
#            songs (play) · leagues (sports) · files
#   Ctrl-R   search history              Ctrl-T   pick a file → insert
#   Alt-C    pick a folder and cd        Shift-Tab  normal zsh completion

typeset -g _NPICK="${NEBULA_HOME}/lib/pick.sh"

# _npick_run <prompt> <initial-query> < candidates  → selection on stdout
_npick_run() { PICK_INLINE_ABOVE=1 PICK_QUERY="$2" bash "$_NPICK" "$1"; }

# insert $2 in place of the current word; $3 = "space" | "none"
_npick_insert() {
  local sel=$1 cur=$2 tail=${3:-space} ins
  if [[ $sel == [[:alnum:]_.+-]## ]]; then ins=$sel; else ins=${(q)sel}; fi
  LBUFFER="${LBUFFER[1,${#LBUFFER}-${#cur}]}${ins}"
  [[ $tail == space ]] && LBUFFER+=" "
}

_npick_history() {
  local -a h; h=( ${(f)"$(fc -lnr 1 2>/dev/null)"} ); h=( ${h## #} ); h=( ${(u)h} )
  print -rl -- $h
}

_npick_dirs() {
  (( _nebula_frecent_stale )) && _nebula_frecent_load
  local d; for d in $_nebula_frecent; do print -r -- "${d/#$HOME/~}"; done
  print -rl -- *(/N) .. ~ ~/storage/shared(/N) /sdcard(/N) 2>/dev/null
}

_npick_files() {  # _npick_files <dir>
  local dir=${1:-.}
  find "$dir" -maxdepth 3 -mindepth 1 ! -path '*/.git/*' ! -path '*/node_modules/*' 2>/dev/null | head -n 6000 | sed "s|^\./||"
}

_nebula_tab() {
  emulate -L zsh
  setopt extendedglob nonomatch
  POSTDISPLAY=""
  local lb=$LBUFFER sel cur="" tail=space
  local -a words cand
  words=( ${(z)lb} ) 2>/dev/null

  # 1. empty line → history
  if [[ -z ${lb// } ]]; then
    zle -I; sel=$(_npick_history | _npick_run "history" "")
    [[ -n $sel ]] && { LBUFFER=$sel; CURSOR=${#LBUFFER} }
    zle reset-prompt; return
  fi

  [[ $lb == *[[:space:]] ]] || cur=${words[-1]}
  local idx=${#words}; [[ -z $cur ]] && idx=$(( idx + 1 ))
  local cmd=${words[1]} sub=""
  [[ $cmd == nebula ]] && { sub=${words[2]:-}; [[ $idx -ge 3 ]] || sub=""; }
  [[ $cmd != nebula ]] && sub=$cmd

  local prompt="complete" kind=plain
  # 2. command position
  if (( idx == 1 )); then
    (( ${#_nebula_cmdnames} )) || _nebula_names_load
    cand=( $_nebula_cmdnames ${(k)commands} ${(k)aliases} ${(k)functions[(I)[^_]*]} )
    cand=( ${(ou)cand} ); prompt="command"
  # 3. nebula <sub>
  elif [[ $cmd == nebula && $idx -eq 2 ]]; then
    (( ${#_nebula_cmdnames} )) || _nebula_names_load
    cand=( $_nebula_cmdnames ); prompt="nebula"
  elif [[ $cmd == (cd|pushd|z) ]]; then
    cand=( ${(f)"$(_npick_dirs)"} ); prompt="folder"; kind=dir; tail=none
  else
    case $sub in
      install|uninstall|remove)
        cand=( ${(f)"$(awk -F'|' '!/^#/ && NF>=5 {printf "%-16s %s\n", $1, $5}' "$NEBULA_HOME/assets/registry.txt")"} ); prompt="tool"; kind=name ;;
      play)
        local idxf="$NEBULA_CFG/music.idx"; [[ -r $idxf ]] && cand=( ${(f)"$(<$idxf)"} ); prompt="song"; kind=path ;;
      sports)
        cand=( ${(f)"$(awk -F'|' '!/^#/{printf "%-12s %s\n",$1,$2}' "$NEBULA_HOME/assets/leagues.txt")"} table next yesterday live ); prompt="league"; kind=name ;;
      news)    cand=( world africa tech business science health sport hn topics ); prompt="topic" ;;
      help)    (( ${#_nebula_cmdnames} )) || _nebula_names_load; cand=( $_nebula_cmdnames search ); prompt="help" ;;
      theme)   cand=( studio set reset export import nebula compact minimal forest sky hacker classic zen ); prompt="theme" ;;
      home)    cand=( edit preset presets refresh set off on classic minimal dashboard focus newsroom info clean ); prompt="home" ;;
      profile) cand=( use save new show rm export import list default work chill minimal saver ); prompt="profile" ;;
      layout)  cand=( auto phone wide ); prompt="layout" ;;
      dash)    cand=( 1 2 5 ); prompt="refresh seconds" ;;
      english) cand=( ask auto off ); prompt="plain English" ;;
      status)  cand=( cpu mem disk battery net temp top trend --live ); prompt="status" ;;
      update)  cand=( --check --force --rollback --self --branch ); prompt="update" ;;
      crypto)  cand=( btc eth sol bnb xrp ada doge ton dot ltc avax link --kes --usd --eur --days ); prompt="coin" ;;
      backup)  cand=( --encrypt --plain ); prompt="backup" ;;
      doctor)  cand=( --fix ); prompt="doctor" ;;
      fingerprint) cand=( on off status ); prompt="fingerprint" ;;
      autolock)    cand=( off 1 5 10 30 ); prompt="autolock" ;;
    esac
    if (( ${#cand} == 0 )); then
      # files under the directory part of the word
      local dir="." base=$cur
      if [[ $cur == */* ]]; then dir=${cur%/*}; [[ -z $dir ]] && dir=/; base=${cur##*/}; fi
      dir=${dir/#\~/$HOME}
      cand=( ${(f)"$(_npick_files "$dir")"} ); prompt="file"; kind=file
      [[ $cur == */* ]] && cand=( ${cand/#$dir\//${cur%/*}/} )
    fi
  fi

  # strip a leading description column for name-kinds later; zero candidates → normal completion
  if (( ${#cand} == 0 )); then zle expand-or-complete; return; fi

  # exactly one prefix match → no UI, just complete
  # one candidate matches the word at all → complete without opening the picker
  local -a pm; pm=( ${(M)cand:#*${cur}*} )
  if [[ -n $cur ]] && (( ${#pm} == 1 )) && [[ $kind != name ]]; then sel=${pm[1]}
  else
    zle -I
    local q=$cur; [[ $kind == file && $cur == */* ]] && q=${cur##*/}
    [[ $kind == dir || $kind == path ]] && q=$cur
    sel=$(print -rl -- $cand | _npick_run "$prompt" "$q")
    [[ -z $sel ]] && { zle reset-prompt; return; }
  fi

  case $kind in
    name) sel=${sel%% *} ;;
    dir)  sel=${sel/#\~/$HOME} ;;
  esac
  local ft=space
  if [[ $kind == dir ]]; then ft=none
  elif [[ $kind == file || $kind == path ]]; then
    local chk=${sel/#\~/$HOME}; [[ -d $chk ]] && { [[ $sel == */ ]] || sel+="/"; ft=none; }
  fi
  _npick_insert "$sel" "$cur" $ft
  CURSOR=${#LBUFFER}
  zle reset-prompt
}
zle -N _nebula_tab

_nebula_hist_widget() {
  zle -I
  local sel; sel=$(_npick_history | _npick_run "history" "$LBUFFER")
  [[ -n $sel ]] && { LBUFFER=$sel; CURSOR=${#LBUFFER} }
  zle reset-prompt
}
_nebula_file_widget() {
  zle -I
  local sel; sel=$(_npick_files . | _npick_run "file" "")
  [[ -n $sel ]] && { [[ $sel == [[:alnum:]_.+/-]## ]] || sel=${(q)sel}; LBUFFER+="$sel " }
  zle reset-prompt
}
_nebula_cd_widget() {
  zle -I
  local sel; sel=$(_npick_dirs | _npick_run "cd" "")
  if [[ -n $sel ]]; then
    sel=${sel/#\~/$HOME}; BUFFER="cd ${(q)sel}"; POSTDISPLAY=""; zle accept-line; return
  fi
  zle reset-prompt
}
zle -N _nebula_hist_widget
zle -N _nebula_file_widget
zle -N _nebula_cd_widget

bindkey '^I'   _nebula_tab
bindkey '^R'   _nebula_hist_widget
bindkey '^T'   _nebula_file_widget
bindkey '^[c'  _nebula_cd_widget
bindkey '^[[Z' expand-or-complete
