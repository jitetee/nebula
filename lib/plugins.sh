#!/usr/bin/env bash
# nebula — plugins: add a command by dropping a folder in plugins/ (bundled) or $NEBULA_CFG/plugins/ (yours).
#   <name>/plugin.sh   defines cmd::<name>          (required)
#   <name>/help.txt    the registry entry for it    (required: every command has help, `nebula check` enforces it)
#   <name>/nvim.lua    optional: loaded by Neovim
#   <name>/skills/*.md optional: skills Ant can use
# Manage with:  nebula plugin list | new <name> | enable|disable <name> | check
# Details: docs/PLUGINS.md

plugin::dir_of() {   # plugin::dir_of <name> → folder (even if disabled)
  local d
  for d in "$NEBULA_HOME/plugins/$1" "$NEBULA_CFG/plugins/$1"; do [[ -d $d ]] && { printf '%s' "$d"; return 0; }; done
  return 1
}

plugin::summary() {   # first "# nebula plugin — ..." line
  sed -n 's/^# nebula plugin [—-] *//p' "$1/plugin.sh" 2>/dev/null | head -1
}

plugin::load_all() {
  local d n
  while IFS= read -r d; do
    [[ -f $d/plugin.sh ]] || continue
    n=${d##*/}
    if ! bash -n "$d/plugin.sh" 2>/dev/null; then
      ui::say_status WARN "plugin '$n' skipped: syntax error in $d/plugin.sh (nebula plugin check)"; continue
    fi
    NEBULA_PLUGIN_DIR=$d
    # shellcheck disable=SC1090
    source "$d/plugin.sh" 2>/dev/null || ui::say_status WARN "plugin '$n' failed to load"
  done < <(registry::plugin_dirs)
  unset NEBULA_PLUGIN_DIR
}

plugin::_list() {
  local d n kind st any=0 off=" "
  [[ -s $NEBULA_CFG/plugins.disabled ]] && off=" $(tr '\n' ' ' <"$NEBULA_CFG/plugins.disabled") "
  for d in "$NEBULA_HOME"/plugins/*/ "$NEBULA_CFG"/plugins/*/; do
    [[ -d $d ]] || continue; d=${d%/}; n=${d##*/}; [[ $n == [._]* ]] && continue
    any=1; kind=bundled; [[ $d == "$NEBULA_CFG"/* ]] && kind=yours
    st=on; [[ $off == *" $n "* ]] && st=off
    printf '  %-14s %-8s %-4s %s\n' "$n" "$kind" "$st" "$(plugin::summary "$d")"
  done
  (( any )) || { ui::say_status INFO "No plugins yet. Make one:  nebula plugin new <name>"; }
}

plugin::_new() {
  local n=${1:-} d
  [[ $n =~ ^[a-z][a-z0-9_-]{1,20}$ ]] || { ui::say_status ERR "Name: lowercase letters, digits, - or _ (2-21 chars)."; return 1; }
  if declare -F "cmd::$n" >/dev/null 2>&1 || grep -q "^@$n|" "$NEBULA_HOME/assets/help.txt"; then
    ui::say_status ERR "'$n' is already a Nebula command. Pick another name."; return 1; fi
  d="$NEBULA_CFG/plugins/$n"
  [[ -e $d ]] && { ui::say_status ERR "$d already exists."; return 1; }
  mkdir -p "$d" || return 1
  local v=${n//-/_}
  cat >"$d/plugin.sh" <<EOT
#!/usr/bin/env bash
# nebula plugin — one line about what $n does
# Defines the command \`$n\`. House rules (nebula check enforces the first two):
#   1. the registry entry lives in help.txt next to this file
#   2. \`$n --help\` is answered by Nebula itself, you do not handle it
#   3. messages: ui::say_status OK|INFO|WARN|ERR "text"      settings: "\$NEBULA_CFG/$n/"
#   4. AI: python3 -m nebula_core.ai "question"   (uses whichever AI the user chose, same as ask/ant/nvim)
_plugin_${v}_dir="\$NEBULA_PLUGIN_DIR"

cmd::$n() {
  case "\${1:-}" in
    "") ui::say_status OK "$n works. Edit \$_plugin_${v}_dir/plugin.sh" ;;
    *)  ui::say_status INFO "$n got: \$*" ;;
  esac
}
EOT
  cat >"$d/help.txt" <<EOT
@$n|Plugins|[args]|one line about what $n does
  What it does, in a sentence or two.
  Example: $n hello
EOT
  printf '# %s\n\nA Nebula plugin. See docs/PLUGINS.md in Nebula for the rules.\n' "$n" >"$d/README.md"
  ui::say_status OK "Created $d"
  ui::say_status INFO "Edit plugin.sh and help.txt, then try:  nebula $n    ·    help $n"
}

plugin::_toggle() {   # plugin::_toggle on|off <name>
  local want=$1 n=${2:-} f="$NEBULA_CFG/plugins.disabled"
  plugin::dir_of "$n" >/dev/null || { ui::say_status ERR "No plugin called '$n'."; return 1; }
  touch "$f"; grep -vx "$n" "$f" >"$f.tmp" 2>/dev/null; mv -f "$f.tmp" "$f"
  [[ $want == off ]] && echo "$n" >>"$f"
  ui::say_status OK "Plugin $n is now $want (takes effect next time you open Nebula)"
}

cmd::plugin() {
  case "${1:-list}" in
    list|ls|"")  shift 2>/dev/null; plugin::_list ;;
    new|create)  shift; plugin::_new "$@" ;;
    enable|on)   shift; plugin::_toggle on "$@" ;;
    disable|off) shift; plugin::_toggle off "$@" ;;
    path)        printf '%s\n' "$NEBULA_HOME/plugins" "$NEBULA_CFG/plugins" ;;
    check)       shift; cmd::check "$@" ;;
    *)           cmd::help plugin ;;
  esac
}
