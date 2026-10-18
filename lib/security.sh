#!/data/data/com.termux/files/usr/bin/env bash
# nebula — security commands: passwd, lock, autolock, fingerprint, logins

cmd::passwd() {
  if [[ ! -f $NEBULA_AUTH ]]; then
    ui::say_status WARN "No login set up yet — it is created on first launch."
    return 1
  fi
  auth::confirm || return 1
  local new new2
  while :; do
    auth::_read_password "  🔑 New password     : " new
    auth::_read_password "  🔑 Confirm password : " new2
    if   [[ -z $new ]];        then ui::say_status ERR "Password cannot be empty"
    elif (( ${#new} < 6 ));    then ui::say_status ERR "Use at least 6 characters"
    elif [[ $new != "$new2" ]]; then ui::say_status ERR "Passwords do not match"
    elif [[ "$(auth::_hash "$new")" == "$NEBULA_HASH" ]]; then ui::say_status ERR "That is your current password"
    else break; fi
  done
  local created=${NEBULA_CREATED:-}
  ( umask 077
    {
      printf 'NEBULA_USER=%q\n' "$NEBULA_USER"
      printf 'NEBULA_HASH=%s\n' "$(auth::_hash "$new")"
      printf 'NEBULA_CREATED=%q\n' "$created"
      printf 'NEBULA_CHANGED=%q\n' "$(date -Iseconds 2>/dev/null || date)"
    } > "$NEBULA_AUTH.tmp" && mv "$NEBULA_AUTH.tmp" "$NEBULA_AUTH" )
  NEBULA_HASH=$(auth::_hash "$new")
  auth::_log PASSWD "password changed"
  ui::say_status OK "Password changed."
}

cmd::lock() {
  if [[ -f $NEBULA_CFG/no-lock ]]; then
    ui::say_status WARN "Session lock is off (noauth on). Run: noauth off"
    return 1
  fi
  if [[ ! -f $NEBULA_AUTH ]]; then
    ui::say_status WARN "No login set up yet."
    return 1
  fi
  auth::unlock
}

# minutes of idle time before locking (0 = never). Default 10.
auth::idle_seconds() {
  local m=10
  [[ -f $NEBULA_CFG/autolock ]] && m=$(<"$NEBULA_CFG/autolock")
  [[ $m =~ ^[0-9]+$ ]] || m=10
  [[ -f $NEBULA_CFG/no-lock || ${NEBULA_NO_AUTH:-0} -eq 1 || ! -f $NEBULA_AUTH ]] && m=0
  echo $(( m * 60 ))
}

cmd::autolock() {
  local f="$NEBULA_CFG/autolock" a=${1:-}
  case "$a" in
    "")
      local m=10; [[ -f $f ]] && m=$(<"$f")
      if [[ $m == 0 ]]; then ui::say_status INFO "Auto-lock is OFF.  Use: autolock <minutes>"
      else ui::say_status INFO "Auto-lock after $m minute(s) idle.  Change: autolock <minutes|off>"; fi ;;
    off|0) mkdir -p "$NEBULA_CFG"; echo 0 > "$f"; ui::say_status OK "Auto-lock disabled." ;;
    *)
      if [[ $a =~ ^[0-9]+$ ]] && (( a >= 1 && a <= 1440 )); then
        mkdir -p "$NEBULA_CFG"; echo "$a" > "$f"
        ui::say_status OK "Auto-lock set to $a minute(s). New shells pick it up automatically."
      else
        ui::say_status ERR "Give minutes between 1 and 1440, or 'off'."; return 1
      fi ;;
  esac
}

cmd::fingerprint() {
  local flag="$NEBULA_CFG/fingerprint"
  case "${1:-status}" in
    on)
      if ! command -v termux-fingerprint >/dev/null 2>&1; then
        ui::say_status ERR "termux-api is not installed. Run: deps  (and install the Termux:API app)"; return 1
      fi
      auth::confirm || return 1
      ui::say_status INFO "Testing — touch the sensor now…"
      if auth::_fingerprint; then
        mkdir -p "$NEBULA_CFG"; touch "$flag"
        ui::say_status OK "Fingerprint unlock enabled. Your password still works."
      else
        ui::say_status ERR "Fingerprint test failed. Is one enrolled in Android settings? Not enabled."; return 1
      fi ;;
    off) rm -f "$flag"; ui::say_status OK "Fingerprint unlock disabled." ;;
    status|"")
      ui::say_status INFO "Fingerprint unlock: $([[ -f $flag ]] && echo ON || echo OFF)"
      command -v termux-fingerprint >/dev/null 2>&1 || ui::say_status WARN "termux-api not installed" ;;
    *) ui::say_status ERR "Use: fingerprint on|off|status"; return 1 ;;
  esac
}

cmd::logins() {
  local n=${1:-15}
  [[ $n =~ ^[0-9]+$ ]] || n=15
  if [[ ! -s $NEBULA_AUTHLOG ]]; then ui::say_status INFO "No login history yet."; return 0; fi
  printf "${C_CYAN}${C_BOLD}🔐 Login history${C_RESET}  ${C_DIM}(last %s)${C_RESET}\n" "$n"
  tail -n "$n" "$NEBULA_AUTHLOG" | awk -F'|' -v G="$C_GREEN" -v R="$C_RED" -v Y="$C_YELLOW" -v D="$C_DIM" -v X="$C_RESET" '
    { c=D; ic="•"
      if ($2=="OK"||$2=="FP-OK") { c=G; ic="✔" }
      else if ($2=="FAIL")        { c=R; ic="✖" }
      else if ($2=="LOCKOUT")     { c=R; ic="⛔" }
      else if ($2=="PASSWD"||$2=="RESET"||$2=="SETUP") { c=Y; ic="⚙" }
      printf "  %s%s %s  %-8s %s%s\n", c, ic, $1, $2, $3, X }'
  local f; f=$(auth::_failed_since_ok)
  (( f > 0 )) && ui::say_status WARN "$f failed attempt(s) since the last successful login."
}
