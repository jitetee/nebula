#!/data/data/com.termux/files/usr/bin/env bash
# nebula — tools: status, remind, serve, backup, restore, tour

# ── remind ──────────────────────────────────────────────────────────────
# data/reminders lines:  id|epoch|pid|text
remind::_file() { printf '%s' "$NEBULA_CFG/reminders"; }

remind::_arm() {  # remind::_arm <id>  → prints pid of the background worker
  ( NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" nohup bash "$NEBULA_HOME/lib/remind-fire.sh" "$1" >/dev/null 2>&1 & echo $! )
}

remind::_set_pid() {  # id pid
  local f; f=$(remind::_file)
  awk -F'|' -v OFS='|' -v id="$1" -v pid="$2" '$1==id{$3=pid} {print}' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
}

# remind::_parse <token> → sets REM_EPOCH (0 on failure)
remind::_parse() {
  local t=$1 now d h m s; now=$(date +%s); REM_EPOCH=0
  if [[ -n $t && $t =~ ^([0-9]+d)?([0-9]+h)?([0-9]+m)?([0-9]+s)?$ ]]; then
    d=${BASH_REMATCH[1]%d}; h=${BASH_REMATCH[2]%h}; m=${BASH_REMATCH[3]%m}; s=${BASH_REMATCH[4]%s}
    REM_EPOCH=$(( now + ${d:-0}*86400 + ${h:-0}*3600 + ${m:-0}*60 + ${s:-0} ))
  elif [[ $t =~ ^[0-9]+$ ]]; then
    REM_EPOCH=$(( now + t * 60 ))
  elif [[ $t =~ ^([0-9]{1,2}):([0-9]{2})$ ]] && (( 10#${BASH_REMATCH[1]} < 24 && 10#${BASH_REMATCH[2]} < 60 )); then
    local tgt; tgt=$(date -d "today $t" +%s 2>/dev/null) || return 1
    (( tgt <= now )) && tgt=$(( tgt + 86400 ))
    REM_EPOCH=$tgt
  fi
  (( REM_EPOCH > now ))
}

remind::_list() {
  local f; f=$(remind::_file)
  if [[ ! -s $f ]]; then ui::say_status INFO "No pending reminders.  Example: remind 10m call mom"; return 0; fi
  printf "${C_CYAN}${C_BOLD}⏰ Reminders${C_RESET}\n"
  sort -t'|' -k2,2n "$f" | while IFS='|' read -r id ep _ text; do
    printf "  ${C_GREEN}#%s${C_RESET} ${C_DIM}%s${C_RESET}  %s\n" "$id" "$(date -d "@$ep" '+%a %H:%M' 2>/dev/null)" "$text"
  done
}

# Reminders that fired while there was no phone notification path
remind::due() {
  local d="$NEBULA_CFG/reminders.due" ts text
  [[ -s $d ]] || return 0
  while IFS='|' read -r ts text; do
    printf "\n  ${C_YELLOW}⏰ Reminder${C_RESET} ${C_DIM}%s${C_RESET}  %s\n" "$(date -d "@$ts" '+%H:%M' 2>/dev/null)" "$text"
  done < "$d"
  : > "$d"; printf '\a'
}

# Fire anything that came due while Nebula wasn't running; re-arm the rest.
remind::check() {
  local f now id ep pid text; f=$(remind::_file); [[ -s $f ]] || return 0
  now=$(date +%s)
  while IFS='|' read -r id ep pid text; do
    [[ $id =~ ^[0-9]+$ ]] || continue
    if (( ep <= now )); then
      printf "  ${C_YELLOW}⏰ Reminder (%s):${C_RESET} %s\n" "$(date -d "@$ep" '+%a %H:%M' 2>/dev/null)" "$text"
      voice::say "Reminder. $text"
      grep -v "^${id}|" "$f" > "$f.tmp"; mv "$f.tmp" "$f"
    elif [[ -z $pid ]] || ! kill -0 "$pid" 2>/dev/null; then
      remind::_set_pid "$id" "$(remind::_arm "$id")"
    fi
  done < <(cat "$f")
}

cmd::remind() {
  local f; f=$(remind::_file); mkdir -p "$NEBULA_CFG"; touch "$f"
  case "${1:-}" in
    ""|list|ls) remind::_list; return ;;
    check)      remind::due; remind::check; return ;;
    due)        remind::due; return ;;
    rm|del|cancel)
      [[ ${2:-} =~ ^[0-9]+$ ]] || { ui::say_status WARN "Usage: remind rm <id>"; return 1; }
      if grep -q "^$2|" "$f"; then grep -v "^$2|" "$f" > "$f.tmp"; mv "$f.tmp" "$f"; ui::say_status OK "Cancelled #$2."
      else ui::say_status ERR "No reminder #$2"; return 1; fi
      return ;;
  esac
  [[ $1 == at ]] && shift
  local when=$1; shift
  local text="$*"
  if [[ -z $text ]]; then ui::say_status WARN "Usage: remind <when> <text>   e.g. remind 10m call mom"; return 1; fi
  if ! remind::_parse "$when"; then
    ui::say_status ERR "Couldn't read the time '$when'. Try 90s, 10m, 2h, 1h30m, 2d or 14:30"; return 1
  fi
  local id; id=$(awk -F'|' 'BEGIN{m=0} $1+0>m{m=$1+0} END{print m+1}' "$f")
  printf '%s|%s||%s\n' "$id" "$REM_EPOCH" "$text" >> "$f"
  remind::_set_pid "$id" "$(remind::_arm "$id")"
  ui::say_status OK "Reminder #$id set for $(date -d "@$REM_EPOCH" '+%a %H:%M'): $text"
  device::cap notify || \
    ui::say_status INFO "No phone notifications here — it will pop up (and speak) at your next prompt. See: settings"
}

# ── serve ───────────────────────────────────────────────────────────────
cmd::serve() {
  local dir=${1:-.} port=${2:-8000} py
  py=$(command -v python3 || command -v python) || { ui::say_status ERR "python is required. Run: nebula deps"; return 1; }
  [[ -d $dir ]] || { ui::say_status ERR "Not a folder: $dir"; return 1; }
  [[ $port =~ ^[0-9]+$ ]] && (( port >= 1024 && port <= 65535 )) || { ui::say_status ERR "Port must be 1024-65535"; return 1; }
  dir=$(cd "$dir" && pwd)
  ui::say_status WARN "This shares $dir with EVERYONE on your Wi-Fi (read-only)."
  ui::confirm "Start sharing?" N || { ui::say_status INFO "Cancelled."; return 0; }
  local ip; ip=$(ui::lan_ip); local url="http://${ip:-localhost}:$port"
  printf "\n  ${C_GREEN}${C_BOLD}Serving${C_RESET} %s\n  ${C_CYAN}%s${C_RESET}\n  ${C_DIM}Ctrl+C to stop${C_RESET}\n\n" "$dir" "$url"
  command -v qrencode >/dev/null 2>&1 && qrencode -t ANSIUTF8 "$url"
  "$py" -m http.server "$port" --bind 0.0.0.0 --directory "$dir"
  ui::say_status INFO "Server stopped."
}

# ── backup / restore ────────────────────────────────────────────────────
backup::dir() {
  local d=${NEBULA_BACKUP_DIR:-} c
  if [[ -z $d ]]; then
    for c in /sdcard "$HOME/storage/shared"; do
      [[ -d $c && -w $c ]] && { d=$c/Nebula; break; }
    done
  fi
  printf '%s' "$d"
}

cmd::backup() {
  local enc=ask d="" a
  for a in "$@"; do
    case "$a" in
      --encrypt|-e) enc=yes ;;
      --plain)      enc=no ;;
      *)            d=$a ;;
    esac
  done
  [[ -z $d ]] && d=$(backup::dir)
  if [[ -z $d ]]; then
    ui::say_status ERR "Shared storage isn't accessible."
    ui::say_status INFO "Run: termux-setup-storage   then try again (or: backup <folder>)"
    return 1
  fi
  mkdir -p "$d" || { ui::say_status ERR "Can't create $d"; return 1; }
  if [[ $enc == ask ]]; then
    if command -v openssl >/dev/null 2>&1 && ui::confirm "Encrypt with a passphrase? (recommended — backups hold your login hash)" Y; then enc=yes; else enc=no; fi
  fi
  if [[ $enc == yes ]] && ! command -v openssl >/dev/null 2>&1; then
    ui::say_status ERR "openssl-tool needed for encryption. Run: nebula deps"; return 1
  fi

  local stage tmp ts out; stage=$(mktemp -d); ts=$(date +%Y%m%d-%H%M%S)
  mkdir -p "$stage/data" "$stage/assets"
  cp -a "$NEBULA_CFG/." "$stage/data/" 2>/dev/null
  tmp="$stage.tar.gz"
  tar -C "$stage" -czf "$tmp" data assets || { ui::say_status ERR "tar failed"; rm -rf "$stage" "$tmp"; return 1; }
  out="$d/nebula-backup-$ts.tar.gz"
  if [[ $enc == yes ]]; then
    out+=".enc"
    openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt -in "$tmp" -out "$out" || { ui::say_status ERR "Encryption failed"; rm -rf "$stage" "$tmp" "$out"; return 1; }
  else
    cp "$tmp" "$out"
    ui::say_status WARN "Saved UNENCRYPTED — other apps with storage access can read it."
  fi
  chmod 600 "$out" 2>/dev/null
  rm -rf "$stage" "$tmp"
  # keep the 10 newest
  ls -1t "$d"/nebula-backup-* 2>/dev/null | tail -n +11 | while read -r old; do rm -f "$old"; done
  ui::say_status OK "Backup saved: $out ($(du -h "$out" | cut -f1))"
}

cmd::restore() {
  local d choice=${1:-} file="" list=() n=0 f
  d=$(backup::dir)
  if [[ -f $choice ]]; then file=$choice
  else
    [[ -z $d || ! -d $d ]] && { ui::say_status ERR "No backup folder found. Run termux-setup-storage, or: restore <file>"; return 1; }
    while IFS= read -r f; do list+=("$f"); done < <(ls -1t "$d"/nebula-backup-* 2>/dev/null)
    (( ${#list[@]} )) || { ui::say_status INFO "No backups in $d"; return 1; }
    if [[ $choice == latest ]]; then file=${list[0]}
    elif [[ $choice =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#list[@]} )); then file=${list[choice-1]}
    elif [[ -z $choice ]]; then
      printf "${C_CYAN}${C_BOLD}💾 Backups${C_RESET} ${C_DIM}(%s)${C_RESET}\n" "$d"
      for f in "${list[@]}"; do n=$((n+1)); printf "  ${C_GREEN}%2d${C_RESET}. %s ${C_DIM}%s%s${C_RESET}\n" "$n" "$(basename "$f")" "$(du -h "$f" | cut -f1)" "$([[ $f == *.enc ]] && echo ' · encrypted')"; done
      local pick; read -r -p "  Restore which? [1] " pick; pick=${pick:-1}
      [[ $pick =~ ^[0-9]+$ ]] && (( pick >= 1 && pick <= ${#list[@]} )) || { ui::say_status ERR "Invalid choice"; return 1; }
      file=${list[pick-1]}
    else ui::say_status ERR "No such backup: $choice"; return 1; fi
  fi

  local work; work=$(mktemp -d); local tgz="$work/b.tar.gz"
  if [[ $file == *.enc ]]; then
    command -v openssl >/dev/null 2>&1 || { ui::say_status ERR "openssl-tool needed. Run: nebula deps"; rm -rf "$work"; return 1; }
    openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -in "$file" -out "$tgz" 2>/dev/null \
      || { ui::say_status ERR "Wrong passphrase or damaged file."; rm -rf "$work"; return 1; }
  else cp "$file" "$tgz"; fi

  # Safety: only data/ and assets/banner.txt, no absolute or .. paths
  if ! tar -tzf "$tgz" >/dev/null 2>&1 \
     || tar -tzf "$tgz" | grep -Eq '(^/|\.\.)' \
     || tar -tzf "$tgz" | grep -Ev '^(data(/|$)|assets(/|$)|assets/banner\.txt$)' | grep -q .; then
    ui::say_status ERR "That archive isn't a valid Nebula backup."; rm -rf "$work"; return 1
  fi
  ui::say_status WARN "This replaces your current login, notes, todos and themes."
  ui::confirm "Restore $(basename "$file")?" N || { ui::say_status INFO "Cancelled."; rm -rf "$work"; return 0; }

  local safety_dir=${d:-$work}; mkdir -p "$safety_dir"
  local safety="$safety_dir/pre-restore-$(date +%Y%m%d-%H%M%S).tar.gz"
  tar -C "$(dirname "$NEBULA_CFG")" -czf "$safety" "$(basename "$NEBULA_CFG")" 2>/dev/null \
    && ui::say_status INFO "Current data saved first: $safety"
  tar -C "$work" -xzf "$tgz" || { ui::say_status ERR "Extract failed"; rm -rf "$work"; return 1; }
  mkdir -p "$NEBULA_CFG"
  cp -a "$work/data/." "$NEBULA_CFG/" 2>/dev/null
  [[ -f $work/assets/banner.txt && ! -s $NEBULA_CFG/banner.txt ]] && cp "$work/assets/banner.txt" "$NEBULA_CFG/banner.txt"   # backups made by older versions
  chmod 700 "$NEBULA_CFG"
  rm -rf "$work"
  ui::say_status OK "Restored. Open a new shell to see everything (login, themes…)."
}

# ── tour ────────────────────────────────────────────────────────────────
cmd::tour() {
  local steps=(
"🤖 Nebula AI|ask <question> for one answer · chat for a conversation that remembers · explain <cmd> and fix when a command fails."
"❓ Help|help lists everything. help <command> shows examples. help search <word> finds a command."
"🔐 Security|3 wrong passwords closes the whole session. passwd changes it · lock locks now · autolock 5 sets idle time · logins shows history · fingerprint on (needs termux-api)."
"💾 Your data|Everything lives in \$PREFIX/opt/nebula/data. Run backup (encrypt it!) to copy it to /sdcard/Nebula, and restore if Termux is ever wiped."
"🧰 Tools|status draws CPU/RAM/storage/battery charts (status --live) · remind 10m call mom · todo / notes · serve shares a folder over Wi-Fi."
"🎨 Make it yours|theme studio designs your prompt live · home edit picks your startup widgets · profile use work switches your whole setup · banner YOURNAME makes a custom logo."
"📦 Packages|deps opens the package picker any time. doctor --fix finds what's missing."
  )
  local i=0 s title body
  clear
  for s in "${steps[@]}"; do
    i=$((i+1)); title=${s%%|*}; body=${s#*|}
    printf "\n${C_CYAN}${C_BOLD}%s${C_RESET}  ${C_DIM}(%d/%d)${C_RESET}\n  %s\n" "$title" "$i" "${#steps[@]}" "$body"
    [[ -t 0 ]] || continue
    read -r -p "  ⏎ next · q to stop " a; [[ ${a,,} == q* ]] && break
  done
  mkdir -p "$NEBULA_CFG"; touch "$NEBULA_CFG/.toured"
  printf "\n  ${C_GREEN}That's it!${C_RESET} Type ${C_BOLD}help${C_RESET} any time. Replay with ${C_BOLD}tour${C_RESET}.\n\n"
}
