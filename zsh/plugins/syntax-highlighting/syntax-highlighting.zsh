# NSH syntax-highlighting — minimal original implementation
# Highlights the command line as you type: valid commands green,
# invalid red, strings yellow, options cyan.

typeset -gA NSH_SH_COLORS=(
  command       'fg=green'
  builtin       'fg=green,bold'
  alias         'fg=green'
  function      'fg=green'
  unknown       'fg=red,bold'
  string        'fg=yellow'
  option        'fg=cyan'
  path          'fg=blue,underline'
  comment       'fg=240'
)

_nsh_sh_highlight() {
  region_highlight=()
  [[ -z $BUFFER ]] && return

  local -a tokens
  tokens=(${(z)BUFFER})   # zsh tokenizer, respects quotes
  local pos=0 tok start end kind

  for tok in "${tokens[@]}"; do
    # Find token position in BUFFER starting from pos
    start=${BUFFER[(ib:pos+1:)$tok]}
    start=$((start - 1))
    (( start < pos )) && start=$pos
    end=$((start + ${#tok}))
    pos=$end

    # Classify first token (command) vs args
    if [[ $pos -eq $end && ${#region_highlight} -eq 0 ]] || \
       [[ ${BUFFER:$((start-1)):1} == '|' || ${BUFFER:$((start-2)):2} == '&&' ]]; then
      kind=unknown
      if   (( $+commands[$tok] ));                         then kind=command
      elif [[ -n ${aliases[$tok]:-} ]];                    then kind=alias
      elif [[ -n ${functions[$tok]:-} ]];                  then kind=function
      elif [[ -n ${builtins[$tok]:-} ]];                   then kind=builtin
      fi
    else
      if   [[ $tok == \"*\" || $tok == \'*\' ]]; then kind=string
      elif [[ $tok == -* ]];                     then kind=option
      elif [[ -e ${tok/#\~/$HOME} ]];            then kind=path
      elif [[ $tok == \#* ]];                    then kind=comment
      else                                            kind=""
      fi
    fi

    [[ -n $kind ]] && region_highlight+=("$start $end ${NSH_SH_COLORS[$kind]}")
  done
}

# Recompute after each line edit
autoload -U add-zle-hook-widget 2>/dev/null
if command -v add-zle-hook-widget >/dev/null 2>&1; then
  zle -N _nsh_sh_highlight
  add-zle-hook-widget line-pre-redraw _nsh_sh_highlight
fi
