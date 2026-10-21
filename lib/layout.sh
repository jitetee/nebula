#!/data/data/com.termux/files/usr/bin/env bash
# nebula — responsive layout layer.  One source of truth for the screen size, plus
# helpers to adapt to it: breakpoints, bar widths, a side-by-side grid, a clipper.
#
#   ui::cols / ui::rows     current size (re-measured after a resize)
#   ui::bp                  xs <36 · sm <55 · md <90 · lg <140 · xl
#   ui::bw [block_width]    a good progress-bar width for that much room
#   ui::grid_dims MIN MAX   → "<columns> <block width>" for blocks that need ≥ MIN cells
#   ui::columns GAP f1 f2…  print files side by side (ANSI/UTF-8 aware)
#   ui::clip WIDTH          stdin → lines cut to WIDTH visible cells (keeps colours)
#   ui::resized             forget the cached size (call from a WINCH trap)
#   NEBULA_COLS / NEBULA_ROWS   force a size (testing, screenshots)
#   NEBULA_LAYOUT=phone|auto|wide   phone = always one column

_UI_COLS=""; _UI_ROWS=""
# characters Nebula prints that occupy 2 cells; the grid and clipper count them as 2
UI_WIDE="🖥 🧠 💾 🔋 📶 🌡 ⚙ 🕐 ⚡ 📦 📚 📰 🔥 🪙 📈 🏆 ⚽ 🏀 🏈 🏒 ⚾ 🏎 🎾 🎨 🏠 👤 🔐 🔒 ✅ ⏰ 💡 🎵 🤖 💬 🩺 📱 🔧 📐 📤 📥 📖 🔄 🧭 🧹 🎞 📂 🌤 ₿ ✔ ✖ ⚠ ℹ"
[[ -z ${NEBULA_LAYOUT:-} && -r ${NEBULA_CFG:-/nonexistent}/layout ]] && NEBULA_LAYOUT=$(<"$NEBULA_CFG/layout")

ui::_measure() {
  local r c sz
  if [[ -n ${NEBULA_COLS:-} && -n ${NEBULA_ROWS:-} ]]; then r=$NEBULA_ROWS; c=$NEBULA_COLS
  else
    sz=$({ stty size </dev/tty; } 2>/dev/null)
    r=${sz% *}; c=${sz#* }
    [[ $r =~ ^[0-9]+$ && $c =~ ^[0-9]+$ && $c -gt 0 ]] || { c=${COLUMNS:-}; r=${LINES:-}; }
    [[ $c =~ ^[0-9]+$ && $c -gt 0 ]] || c=$(tput cols 2>/dev/null)
    [[ $r =~ ^[0-9]+$ && $r -gt 0 ]] || r=$(tput lines 2>/dev/null)
  fi
  [[ -n ${NEBULA_COLS:-} ]] && c=$NEBULA_COLS; [[ -n ${NEBULA_ROWS:-} ]] && r=$NEBULA_ROWS
  [[ $c =~ ^[0-9]+$ ]] && (( c >= 20 )) || c=80
  [[ $r =~ ^[0-9]+$ ]] && (( r >= 5 ))  || r=24
  _UI_COLS=$c; _UI_ROWS=$r
}
ui::cols()    { [[ -n $_UI_COLS ]] || ui::_measure; printf '%s' "$_UI_COLS"; }
ui::rows()    { [[ -n $_UI_ROWS ]] || ui::_measure; printf '%s' "$_UI_ROWS"; }
ui::resized() { _UI_COLS=""; _UI_ROWS=""; }

ui::bp() {
  local c=${1:-$(ui::cols)}
  if   (( c < 36 )); then echo xs
  elif (( c < 55 )); then echo sm
  elif (( c < 90 )); then echo md
  elif (( c < 140 )); then echo lg
  else echo xl; fi
}

# bar width for a block that is $1 cells wide (default: whole screen)
ui::bw() {
  local w=${1:-${UI_W:-$(ui::cols)}} b
  b=$(( w - 20 )); (( b < 6 )) && b=6; (( b > 44 )) && b=44
  printf '%s' "$b"
}

# ui::grid_dims <min block width> [max columns]  → "n width"
ui::grid_dims() {
  local min=${1:-40} max=${2:-3} c n gap=3
  c=$(ui::cols)
  [[ ${NEBULA_LAYOUT:-auto} == phone ]] && max=1
  n=$(( (c + gap) / (min + gap) )); (( n < 1 )) && n=1; (( n > max )) && n=max
  printf '%s %s' "$n" "$(( (c - gap * (n - 1)) / n ))"
}

# ui::columns <gap> <file1> <file2> …   (each file = one block of text)
ui::columns() {
  local gap=$1; shift
  awk -v GAP="$gap" -v N="$#" -v FILES="$*" -v WIDE="$UI_WIDE" '
    BEGIN {
      bm = (length("é") > 1); if (bm) cont = "[" sprintf("%c", 128) "-" sprintf("%c", 191) "]"
      nw = split(WIDE, wl, " "); wre = ""; for (k = 1; k <= nw; k++) wre = wre (k > 1 ? "|" : "") wl[k]
      split(FILES, f, " "); maxn = 0
      for (i = 1; i <= N; i++) { n[i] = 0; w[i] = 0
        while ((getline line < f[i]) > 0) { n[i]++; L[i, n[i]] = line; v = vis(line); if (v > w[i]) w[i] = v }
        close(f[i]); if (n[i] > maxn) maxn = n[i] }
      for (r = 1; r <= maxn; r++) { out = ""
        for (i = 1; i <= N; i++) { s = (r <= n[i]) ? L[i, r] : ""; out = out s (i < N ? pad(w[i] - vis(s) + GAP) : "") }
        print out "\033[0m" }
    }
    function vis(s,   t) { t = s; gsub(/\033\[[0-9;]*[a-zA-Z]/, "", t); gsub(/\357\270\217/, "", t)
      if (wre != "") gsub(wre, "xx", t); if (bm) gsub(cont, "", t); return length(t) }
    function pad(n,   o) { o = ""; while (n-- > 0) o = o " "; return o }'
}

# ui::clip <width> : cut each stdin line to <width> visible cells, keeping ANSI colours intact
ui::clip() {
  awk -v W="$1" -v WIDE="$UI_WIDE" '
    BEGIN { bm = (length("é") > 1)
            if (bm) for (i = 0; i < 256; i++) ord[sprintf("%c", i)] = i
            nw = split(WIDE, wl, " "); for (k = 1; k <= nw; k++) wide[wl[k]] = 1 }
    {
      s = $0; out = ""; vis = 0; n = length(s); i = 1
      while (i <= n) {
        c = substr(s, i, 1)
        if (c == "\033") {                                   # copy an escape sequence untouched
          j = i + 1; if (substr(s, j, 1) == "[") { j++; while (j <= n && substr(s, j, 1) !~ /[A-Za-z]/) j++ }
          out = out substr(s, i, j - i + 1); i = j + 1; continue }
        len = 1
        if (bm) { o = ord[c] + 0; len = (o >= 240) ? 4 : ((o >= 224) ? 3 : ((o >= 192) ? 2 : 1)) }
        ch = substr(s, i, len); cw = (ch in wide) ? 2 : 1
        if (ch == "\357" || ch == sprintf("%c", 65039)) cw = 0
        if (vis + cw > W) { out = out "\033[0m"; break }
        out = out ch; vis += cw; i += len
      }
      print out
    }'
}

# ui::wrap <width> [hang=0] : stdin lines → word-wrapped to <width> cells (ANSI/UTF-8 aware).
# Continuation lines are indented by <hang> spaces; leading indentation of a line is kept.
ui::wrap() {
  awk -v W="$1" -v H="${2:-0}" '
    function vis(s,   t) { t = s; gsub(/\033\[[0-9;]*[a-zA-Z]/, "", t); if (bm) gsub(cont, "", t); return length(t) }
    BEGIN { bm = (length("é") > 1); if (bm) cont = "[" sprintf("%c", 128) "-" sprintf("%c", 191) "]"
            pad = ""; for (i = 0; i < H; i++) pad = pad " " }
    {
      if ($0 ~ /^[ \t]*$/) { print; next }
      match($0, /^ */); lead = substr($0, 1, RLENGTH); rest = substr($0, RLENGTH + 1)
      n = split(rest, a, " "); line = lead; cur = vis(lead); base = cur
      for (i = 1; i <= n; i++) { wl = vis(a[i])
        if (cur > base && cur + 1 + wl > W) { print line; line = pad; cur = H; base = H }
        if (cur > base) { line = line " " a[i]; cur += 1 + wl } else { line = line a[i]; cur += wl } }
      print line
    }'
}

# Grid helper: collect blocks, then print them in n columns.
#   ui::blocks_reset; ui::blocks_add "text"; …; ui::blocks_flush <n> <gap>
_UI_BLK=()
ui::blocks_reset() { _UI_BLK=(); }
ui::blocks_add()   { _UI_BLK+=("$1"); }
ui::blocks_flush() {
  local n=${1:-1} gap=${2:-3} i b tmp; tmp=$(mktemp -d "${TMPDIR:-/tmp}/nebula-grid.XXXXXX") || return 1
  if (( n <= 1 )); then for b in "${_UI_BLK[@]}"; do printf '%s\n' "$b"; done; rm -rf "$tmp"; return 0; fi
  # greedy: each block goes to the currently shortest column
  local -a h=(); for ((i=0;i<n;i++)); do h[i]=0; : > "$tmp/c$i"; done
  local lines col k cw; cw=$(( ($(ui::cols) - gap * (n - 1)) / n ))
  for b in "${_UI_BLK[@]}"; do
    b=$(printf '%s\n' "$b" | ui::clip "$cw")
    col=0; for ((k=1;k<n;k++)); do (( h[k] < h[col] )) && col=$k; done
    printf '%s\n' "$b" >> "$tmp/c$col"; lines=$(grep -c '' <<<"$b"); h[col]=$(( h[col] + lines ))
  done
  local files=(); for ((i=0;i<n;i++)); do [[ -s $tmp/c$i ]] && files+=("$tmp/c$i"); done
  ui::columns "$gap" "${files[@]}"
  rm -rf "$tmp"
}

# `layout` command: auto = adapt to the screen · phone = always one column · wide = use every column that fits
cmd::layout() {
  case "${1:-}" in
    auto|phone|wide) mkdir -p "$NEBULA_CFG"; echo "$1" > "$NEBULA_CFG/layout"; export NEBULA_LAYOUT=$1; ui::say_status OK "Layout: $1" ;;
    "") ui::say_status INFO "Layout: ${NEBULA_LAYOUT:-auto}  ·  screen $(ui::cols)×$(ui::rows) ($(ui::bp))  ·  layout auto|phone|wide" ;;
    *)  ui::say_status ERR "Use: layout auto|phone|wide"; return 1 ;;
  esac
}
