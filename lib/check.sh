#!/usr/bin/env bash
# nebula — `nebula check`: the consistency rules for the whole codebase (also run by CI before every push).
#   1. every command has a help entry (or says `# alias-of: x` / `# internal` on its definition line)
#   2. every help entry belongs to a real command
#   3. every plugin has plugin.sh, help.txt, a cmd::<name> and its own help entry
#   4. every app answers --help, Neovim has :NebulaHelp, and the registry entries are complete
# Exit code 0 = consistent. Add a command/plugin/app and this tells you what is still missing.

check::run() {
  local home="${NEBULA_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}" bad=0 total=0 f n line
  local cfgd="${NEBULA_CFG:-$home/data}"
  local -a pdirs=("$home"/plugins/*/ "$cfgd"/plugins/*/) pfiles=()
  for f in "${pdirs[@]}"; do [[ -f ${f%/}/plugin.sh ]] && pfiles+=("${f%/}/plugin.sh"); done
  local BUILTINS=" cd clear exit ls ll motd reset-auth deps cls quit bye "
  local reg; reg=$(NEBULA_HOME=$home "$home/lib/registry.sh")
  local names; names=" $(awk -F'|' '/^@/{print substr($1,2)}' "$reg" | tr '\n' ' ') "
  fail() { bad=$((bad+1)); printf '  ✖ %s\n' "$1"; }
  ok()   { total=$((total+1)); }

  # 1. commands → help
  while IFS=: read -r f ln line; do
    n=$(sed -n 's/.*cmd::\([A-Za-z0-9_-]*\)().*/\1/p' <<<"$line")
    [[ -z $n || $n == _* ]] && continue
    ok
    [[ $line == *"# internal"* || $line == *"# alias-of:"* || $names == *" $n "* ]] || fail "command '$n' ($(basename "$f"):$ln) has no help entry in help.txt"
  done < <(grep -Hn "^cmd::[A-Za-z0-9_-]*()" "$home"/lib/*.sh "$home"/bin/nebula "${pfiles[@]}" 2>/dev/null | sed 's/^\([^:]*\):\([0-9]*\):/\1:\2:/')

  # 2. help entries → commands
  local defs; defs=" $(grep -ho "cmd::[A-Za-z0-9_-]*()" "$home"/lib/*.sh "$home"/bin/nebula "${pfiles[@]}" 2>/dev/null | sed 's/cmd:://;s/()//' | tr '\n' ' ') "
  for n in $names; do
    ok
    [[ $BUILTINS == *" $n "* || $defs == *" $n "* ]] || fail "help entry '$n' has no command behind it"
  done

  # 3. plugins
  local d pn
  for d in "${pdirs[@]}"; do
    [[ -d $d ]] || continue; d=${d%/}; pn=${d##*/}; [[ $pn == [._]* ]] && continue
    ok; [[ -f $d/plugin.sh ]] || { fail "plugin $pn: plugin.sh missing"; continue; }
    bash -n "$d/plugin.sh" 2>/dev/null || fail "plugin $pn: syntax error in plugin.sh"
    grep -q "^cmd::$pn()" "$d/plugin.sh" || fail "plugin $pn: plugin.sh must define cmd::$pn"
    { [[ -f $d/help.txt ]] && grep -q "^@$pn|" "$d/help.txt"; } || fail "plugin $pn: help.txt must contain @$pn|..."
  done

  # 4. apps answer --help, Neovim has help, entries are complete
  if command -v python3 >/dev/null 2>&1; then
    local app out rc
    for app in ant jtlearn gui; do
      [[ -d $home/apps/$app ]] || continue; ok
      local mod=$app; [[ $app == gui ]] && mod=nebula_gui
      out=$(cd "$home/apps/$app" && NEBULA_HOME=$home NEBULA_CFG="${NEBULA_CFG:-$home/data}" PYTHONPATH="$home/apps/$app:$home/lib" timeout 40 python3 -m "$mod" --help 2>&1 </dev/null); rc=$?
      (( rc == 0 )) && [[ $(wc -l <<<"$out") -ge 3 && $out != *Traceback* ]] || fail "$app --help does not work (exit $rc)"
    done
  fi
  ok; grep -q "NebulaHelp" "$home/assets/nvim/lua/nebula/help.lua" 2>/dev/null || fail "Neovim: :NebulaHelp is missing (assets/nvim/lua/nebula/help.lua)"
  while IFS='|' read -r a cat args sum; do
    ok; [[ -n ${cat// } && -n ${sum// } ]] || fail "help entry ${a#@}: category and summary are required"
  done < <(grep "^@" "$reg")

  if (( bad )); then printf '\n  %d problem(s) in %d checks. Fix them, then run: nebula check\n' "$bad" "$total"; return 1; fi
  printf '  ✔ consistent: %d checks, every command, plugin, app and Neovim has help\n' "$total"
}

cmd::check() { check::run "$@"; }

[[ ${BASH_SOURCE[0]} == "$0" ]] && check::run
