#!/data/data/com.termux/files/usr/bin/env bash
# nebula — profiles: one command switches voice, sounds, auto-lock, startup mode,
# prompt theme and home screen together.
#   profile                 list          profile use work      apply
#   profile save <name>     snapshot what you have now
#   profile show|new|rm|export|import
# Profiles hold ONLY known settings (no commands), so importing one is safe.

profile::dir() { printf '%s' "$NEBULA_CFG/profiles"; }
profile::file() {  # name → path (user profiles win over built-ins)
  local n=$1
  [[ -f $(profile::dir)/$n.profile ]] && { printf '%s' "$(profile::dir)/$n.profile"; return 0; }
  [[ -f $NEBULA_HOME/assets/profiles/$n.profile ]] && { printf '%s' "$NEBULA_HOME/assets/profiles/$n.profile"; return 0; }
  return 1
}
profile::names() { { ls "$NEBULA_HOME"/assets/profiles/*.profile "$(profile::dir)"/*.profile 2>/dev/null | sed 's|.*/||; s|\.profile$||'; } | sort -u; }
profile::current() { [[ -f $NEBULA_CFG/profile.current ]] && cat "$NEBULA_CFG/profile.current" || echo default; }
profile::desc() { local f; f=$(profile::file "$1") && sed -n '1s/^# *//p' "$f"; }

# profile::valid <key> <value>
profile::valid() {
  local k=$1 v=$2
  case $k in
    set.voice|set.sounds|set.compact) [[ $v == [01] ]] ;;
    set.autolock) [[ $v =~ ^[0-9]{1,4}$ ]] && (( v <= 1440 )) ;;
    set.lock)     [[ $v == on || $v == off ]] ;;
    prompt.preset) [[ -f $NEBULA_HOME/assets/prompts/$v.conf ]] ;;
    home.preset)   [[ -f $NEBULA_HOME/assets/home/$v.conf ]] ;;
    prompt.*)      prompt::valid "${k#prompt.}" "$v" ;;
    home.*)        home::valid "${k#home.}" "$v" ;;
    *) return 1 ;;
  esac
}

# stdin → only valid key=value lines (comments kept as the description line)
profile::sanitize() {
  local k v n=0 first=1
  while IFS= read -r line; do
    if [[ $line == \#* ]]; then (( first )) && { echo "$line"; first=0; }; continue; fi
    k=${line%%=*}; v=${line#*=}; [[ $line == *=* ]] || continue
    profile::valid "$k" "$v" && { printf '%s=%s\n' "$k" "$v"; n=$((n+1)); }
    (( n > 60 )) && break
  done
}

profile::snapshot() {  # prints the current state as a profile
  local v=1 s=1 m=10 c=0 l=on k
  [[ ${NEBULA_VOICE:-1} -eq 0 ]] && v=0; [[ ${NEBULA_SOUNDS:-1} -eq 0 ]] && s=0
  [[ -f $NEBULA_CFG/autolock ]] && m=$(<"$NEBULA_CFG/autolock"); [[ -f $NEBULA_CFG/compact ]] && c=1; [[ -f $NEBULA_CFG/no-lock ]] && l=off
  echo "# Saved from my current setup"
  echo "set.voice=$v"; echo "set.sounds=$s"; echo "set.autolock=$m"; echo "set.compact=$c"; echo "set.lock=$l"
  prompt::load; for k in $PROMPT_KEYS; do echo "prompt.$k=${PC[$k]}"; done
  home::load;   for k in $HOME_KEYS;   do echo "home.$k=${HC[$k]}"; done
}

cmd::profile() {
  local sub=${1:-list}
  case $sub in
    list|ls|"")
      local cur n; cur=$(profile::current)
      printf "${C_CYAN}${C_BOLD}👤 Profiles${C_RESET}\n"
      for n in $(profile::names); do
        local tag=""; [[ -f $(profile::dir)/$n.profile ]] && tag=" (yours)"; local lab; printf -v lab '%-9s' "$n"
        if [[ $n == "$cur" ]]; then ui::item "${C_GREEN}●${C_RESET} $lab" 11 "$(profile::desc "$n")$tag"
        else ui::item "${C_DIM}○${C_RESET} $lab" 11 "$(profile::desc "$n")$tag"; fi
      done
      ui::hint "profile use <name> · profile save <name> · profile show <name> · profile export <name>" ;;
    use|switch|apply)
      local n=${2:-}
      if [[ -z $n ]]; then
        [[ -t 1 ]] || { ui::say_status WARN "Usage: profile use <name>"; return 1; }
        n=$(for x in $(profile::names); do printf '%-9s %s\n' "$x" "$(profile::desc "$x")"; done | pick::choose "Switch profile") || return 0; n=${n%% *}
      fi
      profile::apply "$n" ;;
    show)
      local f; f=$(profile::file "${2:-}") || { ui::say_status ERR "No profile '${2:-}'."; return 1; }
      printf "${C_BOLD}%s${C_RESET}  ${C_DIM}%s${C_RESET}\n" "$2" "$(profile::desc "$2")"; grep -v '^#' "$f" | sed 's/^/  /' ;;
    save)
      local n=${2:-}; [[ $n =~ ^[a-z0-9_-]{1,20}$ ]] || { ui::say_status ERR "Name: 1-20 of a-z 0-9 _ -"; return 1; }
      [[ -f $NEBULA_HOME/assets/profiles/$n.profile ]] && { ui::say_status ERR "'$n' is a built-in. Pick another name."; return 1; }
      mkdir -p "$(profile::dir)"; profile::snapshot > "$(profile::dir)/$n.profile"
      echo "$n" > "$NEBULA_CFG/profile.current"; ui::say_status OK "Saved profile '$n' (switch back any time: profile use $n)" ;;
    new)
      local n=${2:-} from=default; [[ ${3:-} == --from ]] && from=${4:-default}
      [[ $n =~ ^[a-z0-9_-]{1,20}$ ]] || { ui::say_status ERR "Name: 1-20 of a-z 0-9 _ -"; return 1; }
      local src; src=$(profile::file "$from") || { ui::say_status ERR "No profile '$from'."; return 1; }
      mkdir -p "$(profile::dir)"; { echo "# $n — based on $from"; grep -v '^#' "$src"; } > "$(profile::dir)/$n.profile"
      ui::say_status OK "Created '$n' from '$from'. Edit it by switching to it, tweaking settings, then: profile save $n" ;;
    rm|delete)
      local n=${2:-}; [[ -f $(profile::dir)/$n.profile ]] || { ui::say_status ERR "'$n' isn't one of your profiles (built-ins can't be removed)."; return 1; }
      ui::confirm "Delete profile '$n'?" N || return 0; rm -f "$(profile::dir)/$n.profile"; ui::say_status OK "Deleted." ;;
    export|share)
      local f; f=$(profile::file "${2:-}") || { ui::say_status ERR "No profile '${2:-}'."; return 1; }
      printf "\n  ${C_BOLD}Share code${C_RESET} ${C_DIM}(paste into: profile import <code>)${C_RESET}\n  NEBP1:%s\n\n" "$(base64 -w0 "$f")" ;;
    import)
      local src=${2:-} text="" name=${3:-imported}
      if   [[ $src == NEBP1:* ]]; then text=$(printf '%s' "${src#NEBP1:}" | base64 -d 2>/dev/null)
      elif [[ -f $src ]]; then text=$(head -c 8192 "$src")
      elif [[ $src == https://* ]] && command -v curl >/dev/null 2>&1; then text=$(curl -fsSL --max-time 10 "$src" 2>/dev/null | head -c 8192)
      else ui::say_status WARN "Usage: profile import <NEBP1:code | file | https://url> [name]"; return 1; fi
      [[ $name =~ ^[a-z0-9_-]{1,20}$ ]] || { ui::say_status ERR "Bad name."; return 1; }
      local clean; clean=$(profile::sanitize <<<"$text"); [[ -n $(grep -v '^#' <<<"$clean") ]] || { ui::say_status ERR "Nothing valid in that profile (Nebula only accepts known settings)."; return 1; }
      mkdir -p "$(profile::dir)"; printf '%s\n' "$clean" > "$(profile::dir)/$name.profile"
      ui::say_status OK "Imported as '$name'. Review: profile show $name  ·  apply: profile use $name" ;;
    *) ui::say_status ERR "Usage: profile [list|use <name>|save <name>|new <name> [--from X]|show <name>|rm <name>|export <name>|import <code>]"; return 1 ;;
  esac
}

profile::apply() {
  local n=$1 f; f=$(profile::file "$n") || { ui::say_status ERR "No profile '$n'. Try: profile list"; return 1; }
  # read the profile into maps
  local -A P=(); local k v line
  while IFS= read -r line; do [[ $line == \#* || $line != *=* ]] && continue; k=${line%%=*}; v=${line#*=}; profile::valid "$k" "$v" && P[$k]=$v; done < "$f"

  # turning the login lock OFF is security-sensitive → confirm with the password
  if [[ ${P[set.lock]:-on} == off && ! -f $NEBULA_CFG/no-lock ]]; then
    ui::say_status WARN "This profile turns the login lock off."; auth::confirm || return 1
  fi
  mkdir -p "$NEBULA_CFG"
  [[ -n ${P[set.voice]:-}    ]] && { echo "${P[set.voice]}" > "$NEBULA_CFG/voice"; export NEBULA_VOICE=${P[set.voice]}; }
  [[ -n ${P[set.sounds]:-}   ]] && { echo "${P[set.sounds]}" > "$NEBULA_CFG/sounds"; export NEBULA_SOUNDS=${P[set.sounds]}; }
  [[ -n ${P[set.autolock]:-} ]] && echo "${P[set.autolock]}" > "$NEBULA_CFG/autolock"
  [[ -n ${P[set.compact]:-}  ]] && { [[ ${P[set.compact]} == 1 ]] && touch "$NEBULA_CFG/compact" || rm -f "$NEBULA_CFG/compact"; }
  [[ -n ${P[set.lock]:-}     ]] && { [[ ${P[set.lock]} == off ]] && touch "$NEBULA_CFG/no-lock" || rm -f "$NEBULA_CFG/no-lock"; }

  # prompt: preset first, then individual keys
  if [[ -n ${P[prompt.preset]:-} ]] || [[ -n $(printf '%s\n' "${!P[@]}" | grep '^prompt\.' | grep -v preset) ]]; then
    if [[ -n ${P[prompt.preset]:-} ]]; then prompt::load "$NEBULA_HOME/assets/prompts/${P[prompt.preset]}.conf"; else prompt::load; fi
    for k in "${!P[@]}"; do [[ $k == prompt.* && $k != prompt.preset ]] && PC[${k#prompt.}]=${P[$k]}; done
    prompt::save
  fi
  # home screen
  if [[ -n ${P[home.preset]:-} ]] || [[ -n $(printf '%s\n' "${!P[@]}" | grep '^home\.' | grep -v preset) ]]; then
    if [[ -n ${P[home.preset]:-} ]]; then home::load "$NEBULA_HOME/assets/home/${P[home.preset]}.conf"; else home::load; fi
    for k in "${!P[@]}"; do [[ $k == home.* && $k != home.preset ]] && HC[${k#home.}]=${P[$k]}; done
    home::save
  fi
  echo "$n" > "$NEBULA_CFG/profile.current"
  ui::say_status OK "Profile '$n' applied."
  printf "   ${C_DIM}voice %s · sounds %s · auto-lock %s · startup %s · prompt %s · home %s${C_RESET}\n" \
    "$([[ ${P[set.voice]:-1} == 1 ]] && echo on || echo off)" "$([[ ${P[set.sounds]:-1} == 1 ]] && echo on || echo off)" \
    "${P[set.autolock]:-10}m" "$([[ ${P[set.compact]:-0} == 1 ]] && echo compact || echo full)" "${P[prompt.preset]:-custom}" "${P[home.preset]:-custom}"
  ui::say_status INFO "Your prompt updates at the next line; the home screen at next login (or run: home)."
}
