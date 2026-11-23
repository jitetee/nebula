#!/usr/bin/env bash
# nebula — the command registry: assets/help.txt plus every enabled plugin's help.txt, merged.
# Everything that lists, completes or explains commands asks here, so a plugin's help is automatically
# everywhere (help, tab-completion, "did you mean", Neovim :NebulaHelp).
#   source lib/registry.sh; registry::file      → path of the registry to read
#   lib/registry.sh                             → prints that path (for zsh / awk callers)
NEBULA_HOME="${NEBULA_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NEBULA_CFG="${NEBULA_CFG:-$NEBULA_HOME/data}"

registry::plugin_dirs() {   # enabled plugin folders: bundled (plugins/) first, then yours ($NEBULA_CFG/plugins)
  local d n off=" "
  [[ -s $NEBULA_CFG/plugins.disabled ]] && off=" $(tr '\n' ' ' <"$NEBULA_CFG/plugins.disabled") "
  for d in "$NEBULA_HOME"/plugins/*/ "$NEBULA_CFG"/plugins/*/; do
    [[ -d $d ]] || continue
    d=${d%/}; n=${d##*/}
    [[ $n == [._]* || $off == *" $n "* ]] && continue
    printf '%s\n' "$d"
  done
}

registry::file() {
  local base="$NEBULA_HOME/assets/help.txt" out="$NEBULA_CFG/.cache/help.merged" d
  local -a src=() watch=("$base" "$NEBULA_HOME/plugins" "$NEBULA_CFG/plugins" "$NEBULA_CFG/plugins.disabled")
  while IFS= read -r d; do
    [[ -f $d/help.txt ]] && { src+=("$d/help.txt"); watch+=("$d/help.txt"); }
  done < <(registry::plugin_dirs)
  if (( ${#src[@]} == 0 )); then printf '%s' "$base"; return; fi
  local stale=0 w
  [[ -f $out ]] || stale=1
  if (( ! stale )); then for w in "${watch[@]}"; do [[ -e $w && $w -nt $out ]] && { stale=1; break; }; done; fi
  if (( stale )); then
    mkdir -p "${out%/*}" 2>/dev/null
    { cat "$base"; for w in "${src[@]}"; do printf '\n'; cat "$w"; done; } | awk '
      /^@/ { n=$0; sub(/\|.*/,"",n); skip=(n in seen); seen[n]=1 }
      !skip { print }' >"$out.tmp" 2>/dev/null && mv -f "$out.tmp" "$out" || { printf '%s' "$base"; return; }
  fi
  printf '%s' "$out"
}

[[ ${BASH_SOURCE[0]} == "$0" ]] && registry::file
