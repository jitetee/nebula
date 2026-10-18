#!/data/data/com.termux/files/usr/bin/env bash
# nebula — render markdown (AI output) as styled terminal text.
#   some-command | md::render         plain text passes through when piped
#   md::plain "text"                  markdown stripped (for voice)

md::render() {
  if [[ ! -t 1 && -z ${NEBULA_FORCE_MD:-} ]] || [[ ${NEBULA_PLAIN_AI:-0} == 1 ]]; then cat; return; fi
  local cols raw out; cols=$(ui::cols)
  raw=$(cat)
  # if the renderer ever fails, show the plain text instead of nothing
  if out=$(printf '%s\n' "$raw" | awk -v COLS="$cols" -f "$NEBULA_HOME/lib/md.awk" 2>/dev/null) && [[ -n $out ]]; then
    printf '%s\n' "$out"
  else
    printf '%s\n' "$raw"
  fi
}

md::plain() {
  printf '%s' "$*" | sed -E 's/```[a-zA-Z]*//g; s/[*_`#>~]//g; s/\[([^]]+)\]\([^)]*\)/\1/g' | tr '\n' ' '
}
