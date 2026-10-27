#!/data/data/com.termux/files/usr/bin/env bash
# nebula — auth (first-run setup + login)

NEBULA_CFG="${NEBULA_CFG:-${NEBULA_HOME:-${PREFIX:-/data/data/com.termux/files/usr}/opt/nebula}/data}"
NEBULA_AUTH="$NEBULA_CFG/auth"
NEBULA_AUTHLOG="$NEBULA_CFG/auth.log"

# ── password hashing ─────────────────────────────────────────────────────
# New format (stored in NEBULA_HASH):  pbkdf2:<iterations>:<salt hex>:<key hex>
#   PBKDF2-HMAC-SHA256 with a random 16-byte salt, so identical passwords differ and every guess is slow.
# Old format (versions up to 0.9.x): a bare 64-hex SHA-256. Still accepted, and upgraded the moment you
# log in successfully (see auth::_upgrade).
NEBULA_KDF_ITER="${NEBULA_KDF_ITER:-120000}"

auth::_sha256() {   # legacy: unsalted sha256
  if command -v openssl >/dev/null 2>&1; then printf '%s' "$1" | openssl dgst -sha256 | awk '{print $NF}'
  else printf '%s' "$1" | sha256sum | awk '{print $1}'; fi
}

# auth::_kdf <password> <salt hex> <iterations> → key hex  (password goes in on stdin, never in a process list)
auth::_kdf() {
  local pw=$1 salt=$2 iter=$3 key=""
  if command -v openssl >/dev/null 2>&1; then
    key=$(printf '%s' "$pw" | openssl enc -aes-256-cbc -pbkdf2 -md sha256 -iter "$iter" -S "$salt" -P -pass stdin 2>/dev/null | sed -n 's/^key *= *//p')
  fi
  if [[ -z $key ]] && command -v python3 >/dev/null 2>&1; then
    key=$(printf '%s' "$pw" | python3 -c 'import sys,hashlib,binascii; print(binascii.hexlify(hashlib.pbkdf2_hmac("sha256", sys.stdin.buffer.read(), binascii.unhexlify(sys.argv[1]), int(sys.argv[2]), 32)).decode())' "$salt" "$iter" 2>/dev/null)
  fi
  printf '%s' "${key,,}"
}

auth::_salt() {     # 16 random bytes as hex
  local s=""
  if command -v openssl >/dev/null 2>&1; then s=$(openssl rand -hex 16 2>/dev/null); fi
  [[ ${#s} -eq 32 ]] || s=$(head -c 16 /dev/urandom 2>/dev/null | od -An -tx1 | tr -d ' \n')
  printf '%s' "$s"
}

# auth::_hash <password> → the value to store in NEBULA_HASH (new format; legacy sha256 only if no KDF is available)
auth::_hash() {
  local salt key; salt=$(auth::_salt)
  [[ ${#salt} -eq 32 ]] && key=$(auth::_kdf "$1" "$salt" "$NEBULA_KDF_ITER")
  if [[ ${#key} -eq 64 ]]; then printf 'pbkdf2:%s:%s:%s' "$NEBULA_KDF_ITER" "$salt" "$key"
  else auth::_sha256 "$1"; fi
}

# auth::_verify <password> [stored hash] → 0 if it matches
auth::_verify() {
  local pw=$1 stored=${2:-${NEBULA_HASH:-}} _ iter salt key
  if [[ $stored == pbkdf2:* ]]; then
    IFS=: read -r _ iter salt key <<<"$stored"
    [[ $iter =~ ^[0-9]+$ && $salt =~ ^[0-9a-f]{32}$ && $key =~ ^[0-9a-f]{64}$ ]] || return 1
    [[ "$(auth::_kdf "$pw" "$salt" "$iter")" == "$key" ]]
  else
    [[ -n $stored && "$(auth::_sha256 "$pw")" == "$stored" ]]
  fi
}

# After a successful login with an old-style hash: store a salted one instead (keeps the other lines of the file)
auth::_upgrade() {
  [[ ${NEBULA_HASH:-} == pbkdf2:* || ! -f $NEBULA_AUTH ]] && return 0
  local h; h=$(auth::_hash "$1"); [[ $h == pbkdf2:* ]] || return 0
  ( umask 077; sed "s|^NEBULA_HASH=.*|NEBULA_HASH=$h|" "$NEBULA_AUTH" > "$NEBULA_AUTH.tmp" && mv "$NEBULA_AUTH.tmp" "$NEBULA_AUTH" ) \
    && { NEBULA_HASH=$h; chmod 600 "$NEBULA_AUTH"; auth::_log UPGRADE "password hash upgraded"; }
}

# Read a password while echoing `*` per keystroke. Supports backspace.
# Usage: auth::_read_password "  🔑 Password: " VARNAME
auth::_read_password() {
  local prompt=$1 __outvar=$2
  local pw="" char
  printf '%s' "$prompt"
  # Turn off canonical mode + echo so we can handle each byte
  stty -echo -icanon min 1 time 0 2>/dev/null
  while IFS= read -r -n1 char; do
    # Enter = done (some terminals send empty when Enter pressed in raw mode)
    if [[ -z $char ]]; then
      break
    fi
    # Backspace (DEL 0x7f or ^H 0x08)
    if [[ $char == $'\x7f' || $char == $'\b' ]]; then
      if [[ -n $pw ]]; then
        pw=${pw%?}
        printf '\b \b'
      fi
      continue
    fi
    # Ignore other control chars
    if [[ $char == $'\x03' ]]; then  # Ctrl-C
      stty sane 2>/dev/null
      printf '\n'; return 130
    fi
    pw+=$char
    printf '*'
  done
  stty sane 2>/dev/null
  printf '\n'
  printf -v "$__outvar" '%s' "$pw"
}

# ── logging ──────────────────────────────────────────────────────────────
# auth::_log EVENT [detail]   → data/auth.log   (timestamp|EVENT|detail)
auth::_log() {
  local d=${2:-}
  d=${d//[^A-Za-z0-9 _.@:=-]/?}; d=${d:0:60}
  mkdir -p "$NEBULA_CFG" 2>/dev/null
  printf '%s|%s|%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "$d" >> "$NEBULA_AUTHLOG" 2>/dev/null
  chmod 600 "$NEBULA_AUTHLOG" 2>/dev/null
  if [[ -f $NEBULA_AUTHLOG ]] && (( $(wc -l < "$NEBULA_AUTHLOG") > 600 )); then
    tail -n 400 "$NEBULA_AUTHLOG" > "$NEBULA_AUTHLOG.tmp" && mv "$NEBULA_AUTHLOG.tmp" "$NEBULA_AUTHLOG"
  fi
}

# Load credentials (upgrades a login file written by the old cvui)
auth::_load() {
  if grep -q '^cvui_' "$NEBULA_AUTH" 2>/dev/null; then
    sed -i 's/^cvui_/NEBULA_/' "$NEBULA_AUTH"
  fi
  # shellcheck disable=SC1090
  source "$NEBULA_AUTH"
}

# Failed attempts since the last successful login
auth::_failed_since_ok() {
  [[ -f $NEBULA_AUTHLOG ]] || { echo 0; return; }
  awk -F'|' '$2=="OK"||$2=="FP-OK"{n=0} $2=="FAIL"{n++} END{print n+0}' "$NEBULA_AUTHLOG"
}

# ── closing the whole session ────────────────────────────────────────────
# Ends the Termux session (the session leader and everything under it),
# not just Nebula. Used after 3 failed attempts.
auth::kill_session() {
  printf '\n  %s✖ Too many failed attempts — closing this session.%s\n' "${C_RED:-}" "${C_RESET:-}"
  auth::_log LOCKOUT "session closed after 3 failures"
  command -v voice::say >/dev/null 2>&1 && voice::say "Access denied. Closing session."
  command -v sound::deny >/dev/null 2>&1 && sound::deny
  sleep 1
  clear 2>/dev/null
  local sid
  sid=$(sed 's/^.*) //' "/proc/$$/stat" 2>/dev/null | awk '{print $4}')
  if [[ $sid =~ ^[0-9]+$ ]] && (( sid > 1 )); then
    kill -HUP -- "-$sid" 2>/dev/null
    kill -HUP "$sid" 2>/dev/null
    sleep 0.3
    kill -KILL "$sid" 2>/dev/null
  fi
  kill -HUP "$PPID" 2>/dev/null
  exit 1
}

# ── fingerprint (optional, needs termux-api) ─────────────────────────────
auth::_fp_enabled() {
  [[ -f $NEBULA_CFG/fingerprint ]] && command -v termux-fingerprint >/dev/null 2>&1
}
auth::_fingerprint() {
  local out
  out=$(timeout 40 termux-fingerprint -t "Nebula" -d "Unlock Nebula" -c "Use password" 2>/dev/null)
  [[ $out == *AUTH_RESULT_SUCCESS* ]]
}

auth::setup() {
  mkdir -p "$NEBULA_CFG"
  chmod 700 "$NEBULA_CFG"
  ui::hr
  printf "  ${C_CYAN}${C_BOLD}First-run setup${C_RESET} — create your nebula credentials\n"
  ui::hr
  local u p p2
  while :; do
    read -r -p "  👤 Choose a username: " u
    [[ -n $u ]] && break
  done
  while :; do
    auth::_read_password "  🔑 Choose a password: " p
    auth::_read_password "  🔑 Confirm password : " p2
    if [[ -z $p ]]; then
      ui::say_status ERR "Password cannot be empty"
    elif [[ $p != "$p2" ]]; then
      ui::say_status ERR "Passwords do not match, try again"
    else
      break
    fi
  done
  umask 077
  {
    printf 'NEBULA_USER=%q\n' "$u"
    printf 'NEBULA_HASH=%s\n' "$(auth::_hash "$p")"
    printf 'NEBULA_CREATED=%q\n' "$(date -Iseconds 2>/dev/null || date)"
  } > "$NEBULA_AUTH"
  auth::_log SETUP "account created"
  ui::say_status OK "Credentials saved to $NEBULA_AUTH"
  sleep 1
}

# auth::_challenge <login|unlock>
# login  → username + password      unlock → password only
# 3 wrong answers close the whole session.
auth::_challenge() {
  local mode=${1:-login} tries=3 u p title="nebula Authentication"
  [[ $mode == unlock ]] && title="🔒 Locked"

  if auth::_fp_enabled; then
    printf '\n'; printf '%s\n' "👆 Touch the fingerprint sensor (or cancel to use your password)" | skin::box "🔐 $title"
    if auth::_fingerprint; then
      export NEBULA_USER
      auth::_log FP-OK "fingerprint"
      command -v sound::chime >/dev/null 2>&1 && sound::chime
      ui::say_status OK "Access granted. Welcome back, $NEBULA_USER."
      sleep 0.6
      return 0
    fi
    ui::say_status INFO "Fingerprint not accepted — use your password."
  fi

  while (( tries > 0 )); do
    printf '\n'; printf '%s\n' "$([[ $mode == login ]] && echo 'Sign in to continue' || echo 'Enter your password to unlock')" | skin::box "🔐 $title"
    if [[ $mode == login ]]; then
      read -r -p "  👤 Username: " u
    else
      u=$NEBULA_USER
      printf "  👤 %s\n" "$u"
    fi
    auth::_read_password "  🔑 Password: " p
    if [[ $u == "$NEBULA_USER" ]] && auth::_verify "$p"; then
      auth::_upgrade "$p"
      export NEBULA_USER
      local failed; failed=$(auth::_failed_since_ok)
      auth::_log OK "$mode"
      command -v sound::chime >/dev/null 2>&1 && sound::chime
      ui::say_status OK "Access granted. Welcome back, $NEBULA_USER."
      (( failed > 0 )) && ui::say_status WARN "$failed failed attempt(s) since your last login — see: logins"
      sleep 0.6
      return 0
    fi
    ((tries--))
    auth::_log FAIL "user=$u"
    command -v sound::deny >/dev/null 2>&1 && sound::deny
    ui::say_status ERR "Invalid credentials. Attempts left: $tries"
  done
  auth::kill_session
}

auth::login() {
  [[ -f $NEBULA_AUTH ]] || auth::setup
  auth::_load

  # If stdin isn't a real terminal bail out instead of burning attempts.
  if [[ ! -t 0 ]]; then
    ui::say_status WARN "No interactive terminal — skipping auth."
    ui::say_status INFO "Run 'nebula' manually to log in."
    return 1
  fi
  stty sane 2>/dev/null
  auth::_challenge login
}

# Re-lock a running session (idle timeout or `lock`)
auth::unlock() {
  [[ -f $NEBULA_AUTH ]] || return 0
  auth::_load
  [[ -t 0 ]] || return 0
  stty sane 2>/dev/null
  clear 2>/dev/null
  auth::_log LOCK "locked"
  auth::_challenge unlock || return 1
  clear 2>/dev/null
}

# Ask for the current password (used before sensitive changes).
# 3 wrong answers close the session.
auth::confirm() {
  [[ -f $NEBULA_AUTH ]] || return 0
  auth::_load
  local tries=3 p
  while (( tries > 0 )); do
    auth::_read_password "  🔑 Confirm your password: " p
    if auth::_verify "$p"; then auth::_upgrade "$p"; return 0; fi
    ((tries--))
    auth::_log FAIL "confirm"
    ui::say_status ERR "Wrong password. Attempts left: $tries"
  done
  auth::kill_session
}

auth::reset() {
  rm -f "$NEBULA_AUTH"
  auth::_log RESET "credentials cleared"
  ui::say_status OK "Credentials cleared. Run nebula again to set up new ones."
}
