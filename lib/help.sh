#!/data/data/com.termux/files/usr/bin/env bash
# nebula — help system. Reads assets/help.txt (the command registry).

help::_file() { printf '%s' "$NEBULA_HOME/assets/help.txt"; }

# All command names, one per line
help::names() { awk -F'|' '/^@/{print substr($1,2)}' "$(help::_file)"; }

help::_hidden() { [[ -s $NEBULA_CFG/hidden.txt ]] && printf ' %s ' "$(<"$NEBULA_CFG/hidden.txt")"; }

help::_list() {
  local hide=" "; [[ ${1:-} == --all ]] || hide=$(help::_hidden)
  printf "\n${C_CYAN}${C_BOLD}Nebula commands${C_RESET}\n"; ui::hint "help <command> for details"
  local a b lab
  while IFS=$'\t' read -r a b; do
    if [[ $a == H ]]; then printf '\n%s%s%s\n' "$C_BOLD$C_CYAN" "$b" "$C_RESET"
    else printf -v lab '%-11s' "$a"; ui::item "${C_GREEN}${lab}${C_RESET}" 11 "$b"; fi
  done < <(awk -F'|' -v hide="$hide" '
    /^@/ { name=substr($1,2); cat=$2; sum=$4
           if (index(hide, " " name " ")) next
           if (!(cat in seen)) { seen[cat]=1; order[++n]=cat }
           items[cat]=items[cat] name "\t" sum "\n" }
    END { for (i=1;i<=n;i++) { print "H\t" order[i]; printf "%s", items[order[i]] } }' "$(help::_file)")
  local h; h=$(help::_hidden)
  [[ -n ${h// } ]] && ui::hint "Some commands are hidden because this device can't run them. See them with: help --all · fix in: settings"
  ui::hint "Anything else is passed to your shell."; printf '\n'
}

help::_detail() {  # help::_detail <name>  → 0 if found
  local name=$1
  awk -F'|' -v n="$name" -v G="$C_GREEN" -v D="$C_DIM" -v B="$C_BOLD" -v R="$C_RESET" '
    /^@/ { if (on) exit
           if (substr($1,2)==n) { on=1; args=$3; if ($4=="" ) {}
             printf "\n%s%s%s %s%s%s\n%s%s%s\n\n", B, n, R, G, args, R, D, $NF, R; next } }
    on && /^  / { sub(/^  /,""); printf "  %s\n", $0 }
    END { exit !on }
  ' "$(help::_file)"
}

help::_search() {
  local w=$1
  printf "\n${C_CYAN}${C_BOLD}Search: %s${C_RESET}\n" "$w"
  awk -v w="$w" -v G="$C_GREEN" -v D="$C_DIM" -v R="$C_RESET" '
    BEGIN { w=tolower(w) }
    function flush() { if (name!="" && index(tolower(block),w)) { printf "  %s%-11s%s %s%s%s\n", G,name,R,D,sum,R; found=1 } }
    /^@/ { flush(); split($0,a,"|"); name=substr(a[1],2); sum=a[4]; block=$0; next }
    /^  / { block=block " " $0 }
    END { flush(); if (!found) print "  (nothing found)" }
  ' "$(help::_file)"
  echo
}

cmd::help() {
  local a=${1:-}
  case "$a" in
    "")        help::_list ;;
    --all|all) help::_list --all ;;
    search|find|s) shift; [[ -z ${1:-} ]] && { ui::say_status WARN "Usage: help search <word>"; return 1; }; help::_search "$*" ;;
    cls)       help::_detail clear ;;
    quit|bye)  help::_detail exit ;;
    ll|la)     help::_detail ls ;;
    *)
      if help::_detail "$a"; then
        device::gate "$a" >/dev/null 2>&1 || device::gate "$a"
      else
        ui::say_status ERR "No help for '$a'."
        local s; s=$("$NEBULA_HOME/lib/suggest.sh" --nebula "$a" 2>/dev/null)
        [[ -n $s ]] && printf '%s\n' "$s"
        ui::say_status INFO "Try: help search $a"
        return 1
      fi ;;
  esac
}
