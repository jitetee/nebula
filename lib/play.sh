#!/data/data/com.termux/files/usr/bin/env bash
# nebula — `nebula play <song>`: finds music anywhere on the phone (typo-tolerant)
# and plays it with whatever player is installed — or tells you which to install.

PLAY_EXTS='mp3 m4a flac wav ogg oga opus aac wma mka aiff mp2'

# song matcher: every query word must match (substring > near-spelling > scattered letters)
PLAY_AWK='
function lev(a, b,   la, lb, i, j, c, p, m, cur) {
  la = length(a); lb = length(b); for (j = 0; j <= lb; j++) p[j] = j
  for (i = 1; i <= la; i++) { cur[0] = i
    for (j = 1; j <= lb; j++) { c = (substr(a, i, 1) == substr(b, j, 1)) ? 0 : 1
      m = p[j] + 1; if (cur[j-1] + 1 < m) m = cur[j-1] + 1; if (p[j-1] + c < m) m = p[j-1] + c; cur[j] = m }
    for (j = 0; j <= lb; j++) p[j] = cur[j] }
  return p[lb] }
BEGIN { nt = split(tolower(Q), tok, " ") }
{
  path = $0; name = path; sub(/.*\//, "", name); sub(/\.[A-Za-z0-9]+$/, "", name)
  dir = path; sub(/\/[^\/]*$/, "", dir); sub(/.*\//, "", dir)
  txt = tolower(name); gsub(/[_.\-]+/, " ", txt); full = txt " " tolower(dir)
  total = 0; ok = 1
  for (t = 1; t <= nt; t++) {
    q = tok[t]; s = 0
    if (index(txt, q)) { s = 100; p = index(txt, q); if (p == 1 || substr(txt, p - 1, 1) == " ") s += 20 }
    else if (index(full, q)) s = 55
    else {
      nw = split(txt, w, " "); best = 99
      for (i = 1; i <= nw; i++) { if (length(w[i]) >= 3) { d = lev(q, w[i]); if (d < best) best = d } }
      lim = (length(q) >= 7) ? 2 : ((length(q) >= 4) ? 1 : 0)
      if (best <= lim) s = 75 - 10 * best
      else { pos = 0; sub_ok = 1
        for (i = 1; i <= length(q); i++) { c = substr(q, i, 1); j = index(substr(txt, pos + 1), c); if (!j) { sub_ok = 0; break }; pos += j }
        if (sub_ok && length(q) >= 3) s = 35; else { ok = 0; break } }
    }
    total += s
  }
  if (ok) printf "%.1f\t%s\n", total - length(txt) / 30, path
}'

play::roots() {
  local r seen=" " out=() real
  for r in ${NEBULA_MUSIC_DIRS:-} /storage/emulated/0 "$HOME/storage/shared" /sdcard /storage/*/ "$HOME/Music" "$HOME"; do
    [[ -d $r && -r $r ]] || continue
    real=$(readlink -f "$r" 2>/dev/null || echo "$r")
    [[ $real == /storage/self* ]] && continue
    [[ $seen == *" $real "* ]] && continue
    # skip a root that is inside one we already have
    local inside=0 o; for o in "${out[@]}"; do [[ $real == "$o"/* ]] && inside=1; done
    (( inside )) && continue
    seen+="$real "; out+=("$real")
  done
  printf '%s\n' "${out[@]}"
}

play::index() {  # play::index [--force]
  local idx="$NEBULA_CFG/music.idx" force=${1:-}
  mkdir -p "$NEBULA_CFG"
  if [[ $force != --force && -s $idx ]] && (( $(date +%s) - $(date -r "$idx" +%s 2>/dev/null || echo 0) < 86400 )); then return 0; fi
  local roots; mapfile -t roots < <(play::roots)
  (( ${#roots[@]} )) || { ui::say_status WARN "No readable storage found. Run: termux-setup-storage"; : > "$idx"; return 1; }
  [[ -t 1 ]] && printf '  %s🔍 Scanning your phone for music…%s\r' "$C_DIM" "$C_RESET"
  local args=() e; for e in $PLAY_EXTS; do args+=(-o -iname "*.$e"); done
  find "${roots[@]}" \( -name Android -o -name .git -o -name node_modules -o -name '.thumbnails' -o -name '.cache' -o -name 'WhatsApp Voice Notes' -o -name proc -o -name sys \) -prune \
       -o -type f \( -false "${args[@]}" \) -size +120k -print 2>/dev/null | sort > "$idx.tmp"
  mv "$idx.tmp" "$idx"
  [[ -t 1 ]] && printf '\033[2K\r'
  ui::say_status INFO "Indexed $(wc -l < "$idx") tracks"
}

# ── players ─────────────────────────────────────────────────────────────
play::ext() { local e=${1##*.}; echo "${e,,}"; }

# play::player_for <ext> → prints the player name that can handle it (best first)
play::player_for() {
  local e=$1
  command -v mpv >/dev/null 2>&1 && { echo mpv; return 0; }
  command -v ffplay >/dev/null 2>&1 && { echo ffplay; return 0; }
  if command -v play >/dev/null 2>&1 && [[ $e == @(mp3|wav|flac|ogg|oga|opus|aiff) ]]; then echo sox; return 0; fi
  if command -v mpg123 >/dev/null 2>&1 && [[ $e == @(mp3|mp2) ]]; then echo mpg123; return 0; fi
  if declare -F device::cap >/dev/null 2>&1 && device::cap notify && command -v termux-media-player >/dev/null 2>&1 && [[ $e == @(mp3|m4a|aac|wav|ogg|flac|opus) ]]; then echo termux; return 0; fi
  return 1
}

play::advice() {  # nothing can play $1
  local e=$1 have=""
  command -v mpg123 >/dev/null 2>&1 && have="mpg123 (MP3 only)"
  command -v play  >/dev/null 2>&1 && have="${have:+$have, }sox"
  printf "\n  ${C_YELLOW}⚠ No player here can play .%s files.${C_RESET}\n" "$e"
  [[ -n $have ]] && printf "  ${C_DIM}Installed: %s${C_RESET}\n" "$have"
  printf "\n  ${C_BOLD}Pick a player${C_RESET}\n"
  printf "    ${C_GREEN}Lightweight${C_RESET}  pkg install mpg123   ${C_DIM}~1 MB · MP3 only${C_RESET}\n"
  printf "                 pkg install sox      ${C_DIM}small · mp3 wav flac ogg${C_RESET}\n"
  printf "    ${C_BLUE}Full power${C_RESET}   pkg install mpv      ${C_DIM}plays everything · bigger download${C_RESET}\n"
  printf "                 pkg install ffmpeg   ${C_DIM}ffplay · huge · only if you need it anyway${C_RESET}\n"
  printf "    ${C_MAGENTA}Phone engine${C_RESET} termux-api + Termux:API app ${C_DIM}(Android's own decoder)${C_RESET}\n\n"
  if [[ -t 0 && -t 1 ]]; then
    local choice
    choice=$(printf '%s\n' "mpg123   — tiny, MP3 only" "sox      — small, mp3/wav/flac/ogg" "mpv      — plays everything (recommended if you have space)" "Not now" | pick::choose "Install a player") || return 1
    case $choice in
      mpg123*|sox*|mpv*) declare -F pm::install_one >/dev/null && PM_YES=0 pm::install_one "${choice%% *}" && hash -r ;;
      *) return 1 ;;
    esac
    command -v "${choice%% *}" >/dev/null 2>&1 || [[ ${choice%% *} == sox && -n $(command -v play) ]]
    return $?
  fi
  return 1
}

play::hint() {
  case $1 in
    mpv)     echo "space pause · ←/→ seek · 9/0 volume · > next · q quit" ;;
    mpg123)  echo "s pause · f next · d prev · +/- volume · q quit" ;;
    ffplay)  echo "space pause · ←/→ seek · q quit" ;;
    sox)     echo "Ctrl-C to stop" ;;
    termux)  echo "plays in the background · play stop to end" ;;
  esac
}

play::run() {  # play::run <player> <bg 0|1> files…
  local pl=$1 bg=$2; shift 2
  local -a cmd
  case $pl in
    mpv)    cmd=(mpv --no-video --force-window=no "$@") ;;
    mpg123) cmd=(mpg123 -C "$@") ;;
    ffplay) cmd=(ffplay -nodisp -autoexit -loglevel quiet) ;;
    sox)    cmd=(play -q "$@") ;;
    termux) termux-media-player play "$1" >/dev/null 2>&1; return $? ;;
  esac
  if (( bg )); then
    if [[ $pl == ffplay || $pl == sox ]]; then
      ( for f in "$@"; do "${cmd[@]}" "$f" >/dev/null 2>&1; done ) &
    else nohup "${cmd[@]}" >/dev/null 2>&1 & fi
    echo $! > "$NEBULA_CFG/play.pid"; disown 2>/dev/null
    ui::say_status OK "Playing in the background. Stop with: play stop"; return 0
  fi
  if [[ $pl == ffplay || $pl == sox ]]; then
    local f; for f in "$@"; do "${cmd[@]}" "$f" || { (( $? == 130 )) && return 130; }; done
  else "${cmd[@]}"; fi
}

play::card() {  # now-playing card
  local f=$1 pl=$2 n=${3:-1} name size
  name=${f##*/}; name=${name%.*}; size=$(du -h "$f" 2>/dev/null | cut -f1)
  printf "\n${C_MAGENTA}${C_BOLD}♪ Now playing${C_RESET}  ${C_DIM}via %s%s${C_RESET}\n" "$pl" "$( (( n > 1 )) && echo " · queue of $n")"
  printf "  ${C_BOLD}%s${C_RESET}\n  ${C_DIM}%s · %s${C_RESET}\n  ${C_DIM}%s${C_RESET}\n\n" "$(viz::trunc "$name" $(( $(ui::cols) - 4 )))" "$(viz::trunc "${f/#$HOME/~}" $(( $(ui::cols) - 12 )))" "${size:-?}" "$(play::hint "$pl")"
}

cmd::play() {
  local query=() bg=0 all=0 shuffle=0 reindex=0 a
  for a in "$@"; do
    case $a in
      stop|--stop)  [[ -f $NEBULA_CFG/play.pid ]] && kill "$(<"$NEBULA_CFG/play.pid")" 2>/dev/null
                    pkill -x mpv 2>/dev/null; pkill -x mpg123 2>/dev/null; pkill -x ffplay 2>/dev/null
                    command -v termux-media-player >/dev/null 2>&1 && termux-media-player stop >/dev/null 2>&1
                    rm -f "$NEBULA_CFG/play.pid"; ui::say_status OK "Stopped."; return 0 ;;
      --bg|-b)      bg=1 ;;
      --all|-a)     all=1 ;;
      --shuffle|shuffle|random|-s) shuffle=1 ;;
      --reindex|--scan) reindex=1 ;;
      *)            query+=("$a") ;;
    esac
  done
  play::index $( ((reindex)) && echo --force ) || return 1
  local idx="$NEBULA_CFG/music.idx"
  [[ -s $idx ]] || { ui::say_status WARN "No music found on this phone. Folders searched:"; play::roots | sed 's/^/    /'; ui::say_status INFO "Grant storage access with: termux-setup-storage  ·  then: play --reindex"; return 1; }

  local -a files=(); local q="${query[*]}"
  if [[ -z $q ]]; then
    if (( shuffle )); then mapfile -t files < <(shuf "$idx" | head -n 50)
    elif [[ -t 1 ]] && declare -F pick::choose >/dev/null; then
      local sel; sel=$(pick::choose "Play" < "$idx") || return 0; files=("$sel")
    else ui::say_status WARN "Usage: play <song name>"; return 1; fi
  else
    local scored; scored=$(awk -v Q="$q" "$PLAY_AWK" "$idx" | sort -t$'\t' -k1,1nr -s | head -n 30)
    if [[ -z $scored ]]; then
      ui::say_status WARN "Nothing on this phone matches '$q'."
      ui::say_status INFO "Searched $(wc -l < "$idx") tracks. New files? Try: play --reindex"
      local near; near=$(awk -F'/' '{n=$NF; sub(/\.[^.]*$/,"",n); print n}' "$idx" | awk -v q="$(tr 'A-Z' 'a-z' <<<"${query[0]}")" '{l=tolower($0); if (substr(l,1,1)==substr(q,1,1)) print $0}' | head -3)
      [[ -n $near ]] && { ui::say_status INFO "Songs starting with the same letter:"; sed 's/^/     ♪ /' <<<"$near"; }
      return 1
    fi
    local top second; top=$(head -1 <<<"$scored" | cut -f1); second=$(sed -n 2p <<<"$scored" | cut -f1)
    if (( all )); then mapfile -t files < <(cut -f2- <<<"$scored")
    elif [[ -z $second ]] || awk -v a="$top" -v b="$second" 'BEGIN{exit !(a-b >= 25)}'; then
      files=("$(head -1 <<<"$scored" | cut -f2-)")
    elif [[ -t 1 ]] && declare -F pick::choose >/dev/null; then
      local sel; sel=$(cut -f2- <<<"$scored" | head -10 | pick::choose "Which one?") || return 0; files=("$sel")
    else files=("$(head -1 <<<"$scored" | cut -f2-)"); fi
    (( shuffle )) && mapfile -t files < <(printf '%s\n' "${files[@]}" | shuf)
  fi

  # pick a player that can handle the first file
  local ext pl; ext=$(play::ext "${files[0]}")
  pl=$(play::player_for "$ext") || { play::advice "$ext" || return 1; pl=$(play::player_for "$ext") || return 1; }
  # drop queue items this player can't play
  local -a ok=(); local f; for f in "${files[@]}"; do [[ $(play::player_for "$(play::ext "$f")") == "$pl" ]] && ok+=("$f"); done
  (( ${#ok[@]} )) && files=("${ok[@]}")
  play::card "${files[0]}" "$pl" "${#files[@]}"
  play::run "$pl" "$bg" "${files[@]}"
}
