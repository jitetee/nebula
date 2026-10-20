#!/data/data/com.termux/files/usr/bin/env bash
# nebula — terminal data-visualisation helpers (sparklines, area charts, bars,
# cards). Used by crypto, news, sports. Pure bash + awk, no extra packages.

VIZ_AWK='
function money(v,   s, p, ip, out) {
  if (v >= 1) s = sprintf("%.2f", v); else if (v >= 0.01) s = sprintf("%.4f", v); else s = sprintf("%.8f", v)
  split(s, p, "."); ip = p[1]; out = ""
  while (length(ip) > 3) { out = "," substr(ip, length(ip) - 2) out; ip = substr(ip, 1, length(ip) - 3) }
  return ip out "." p[2]
}
function short(v) { if (v >= 1e12) return sprintf("%.2fT", v/1e12); if (v >= 1e9) return sprintf("%.2fB", v/1e9); if (v >= 1e6) return sprintf("%.2fM", v/1e6); if (v >= 1e3) return sprintf("%.1fK", v/1e3); return sprintf("%.0f", v) }
function resample(n, W,   c, i, a, b, s, k) {
  for (c = 1; c <= W; c++) { a = int((c - 1) * n / W) + 1; b = int(c * n / W); if (b < a) b = a; s = 0; k = 0
    for (i = a; i <= b; i++) { s += v[i]; k++ } r[c] = s / k }
}
'

# viz::money <number>  → 67,250.00
viz::money() { awk -v x="$1" "$VIZ_AWK"'BEGIN{print money(x+0)}'; }
# viz::short <number>  → 1.25T
viz::short() { awk -v x="$1" "$VIZ_AWK"'BEGIN{print short(x+0)}'; }

# viz::pct <float> → colored ▲ 2.31% / ▼ 1.20%
viz::pct() {
  awk -v x="${1:-0}" -v G="$C_GREEN" -v R="$C_RED" -v D="$C_DIM" -v X="$C_RESET" 'BEGIN{
    if (x == "" || x == "null") { printf "%s  n/a%s", D, X; exit }
    if (x >= 0) printf "%s▲ %.2f%%%s", G, x, X; else printf "%s▼ %.2f%%%s", R, -x, X }'
}

# viz::spark [width]  — numbers on stdin → one-line sparkline (trend coloured)
viz::spark() {
  awk -v W="${1:-12}" -v G="$C_GREEN" -v R="$C_RED" -v X="$C_RESET" "$VIZ_AWK"'
    { v[++n] = $1 + 0 }
    END { if (n < 2) exit; resample(n, W); mn = r[1]; mx = r[1]
      for (c = 1; c <= W; c++) { if (r[c] < mn) mn = r[c]; if (r[c] > mx) mx = r[c] }
      split("▁ ▂ ▃ ▄ ▅ ▆ ▇ █", blk, " "); out = ""
      for (c = 1; c <= W; c++) { l = (mx == mn) ? 4 : int((r[c] - mn) / (mx - mn) * 7) + 1; out = out blk[l] }
      printf "%s%s%s", (r[W] >= r[1] ? G : R), out, X }'
}

# viz::area <width> <height> [label_start] [label_end]
# numbers on stdin → filled area chart with a y-axis; colour follows the trend
viz::area() {
  awk -v W="${1:-40}" -v H="${2:-8}" -v L1="${3:-}" -v L2="${4:-}" -v G="$C_GREEN" -v R="$C_RED" -v D="$C_DIM" -v X="$C_RESET" "$VIZ_AWK"'
    { v[++n] = $1 + 0 }
    END { if (n < 2) exit; resample(n, W); mn = r[1]; mx = r[1]
      for (c = 1; c <= W; c++) { if (r[c] < mn) mn = r[c]; if (r[c] > mx) mx = r[c] }
      col = (r[W] >= r[1]) ? G : R
      split("▁ ▂ ▃ ▄ ▅ ▆ ▇", blk, " ")
      lw = length(money(mx)); if (length(money(mn)) > lw) lw = length(money(mn))
      for (row = 0; row < H; row++) {
        lab = ""; if (row == 0) lab = money(mx); else if (row == H - 1) lab = money(mn)
        line = ""
        for (c = 1; c <= W; c++) {
          lvl = (mx == mn) ? H * 4 : (r[c] - mn) / (mx - mn) * (H * 8 - 1) + 1
          f = lvl - (H - 1 - row) * 8
          if (f >= 8) ch = "█"; else if (f < 1) ch = " "; else ch = blk[int(f)]
          line = line ch
        }
        printf "%s%*s ┤%s%s%s\n", D, lw, lab, col, line, X
      }
      printf "%s%*s └", D, lw, ""; for (c = 1; c <= W; c++) printf "─"; printf "%s\n", X
      if (L1 != "" || L2 != "") { pad = W - length(L1) - length(L2); if (pad < 1) pad = 1
        printf "%s%*s  %s%*s%s%s\n", D, lw, "", L1, pad, "", L2, X }
    }'
}

# viz::bar <value> <max> [width] [colour]  → ██████░░░░ (no newline)
viz::bar() {
  awk -v v="${1:-0}" -v m="${2:-1}" -v W="${3:-10}" -v C="${4:-$C_CYAN}" -v D="$C_DIM" -v X="$C_RESET" 'BEGIN{
    if (m <= 0) m = 1; f = int(v / m * W + 0.5); if (f > W) f = W; if (f < 0) f = 0
    o = C; for (i = 0; i < f; i++) o = o "█"; o = o D; for (i = f; i < W; i++) o = o "░"; printf "%s%s", o, X }'
}

# viz::ago <epoch> → 5m / 3h / 2d
viz::ago() {
  local d=$(( $(date +%s) - $1 ))
  (( d < 0 )) && d=0
  if   (( d < 90 ));    then echo "just now"
  elif (( d < 3600 ));  then echo "$(( d / 60 ))m ago"
  elif (( d < 86400 )); then echo "$(( d / 3600 ))h ago"
  else                       echo "$(( d / 86400 ))d ago"; fi
}

# viz::title "📈 Title" "right side"   → header line + rule
viz::title() {
  local cols; cols=$(ui::cols)
  printf '\n%s%s%s' "$C_CYAN$C_BOLD" "$1" "$C_RESET"
  [[ -n ${2:-} ]] && printf '  %s%s%s' "$C_DIM" "$2" "$C_RESET"
  printf '\n%s' "$C_DIM"; awk -v n="$((cols-1))" 'BEGIN{for(i=0;i<n;i++)printf "─"; print ""}'; printf '%s' "$C_RESET"
}

# viz::trunc <string> <width> → string cut with … if longer
viz::trunc() { local s=$1 w=$2; (( ${#s} > w )) && s="${s:0:w-1}…"; printf '%s' "$s"; }

# viz::fetch <url> → body (honours NEBULA_TOKEN-free public APIs, 10s cap)
viz::fetch() { curl -fsSL --max-time 12 -H 'accept: application/json' -A 'nebula-termux' "$@"; }

viz::need_jq() {
  command -v jq >/dev/null 2>&1 && return 0
  ui::say_status ERR "jq is needed for this view. Run: nebula install jq"; return 1
}

# viz::wrap <width> <first-prefix> <rest-prefix> <text...>   word-wrap, UTF-8 aware
viz::wrap() {
  local w=$1 first=$2 rest=$3; shift 3
  printf '%s' "$*" | awk -v W="$w" -v F="$first" -v Rp="$rest" '
    function vis(s,  t) { t = s; gsub(/\033\[[0-9;]*m/, "", t); if (bm) gsub(cont, "", t); return length(t) }
    BEGIN { bm = (length("é") > 1); if (bm) cont = "[" sprintf("%c", 128) "-" sprintf("%c", 191) "]" }
    { n = split($0, a, " "); line = F; cur = vis(F); pl = cur
      for (i = 1; i <= n; i++) { wl = vis(a[i])
        if (cur + wl + (cur > pl ? 1 : 0) > W && cur > pl) { print line; line = Rp; cur = vis(Rp); pl = cur }
        if (cur > pl) { line = line " " a[i]; cur += 1 + wl } else { line = line a[i]; cur += wl } }
      print line }'
}

# viz::spark_fixed [width] — numbers 0-100 on stdin → sparkline on a fixed scale (no auto-zoom)
viz::spark_fixed() {
  awk -v W="${1:-24}" -v G="$C_GREEN" -v Y="$C_YELLOW" -v R="$C_RED" -v X="$C_RESET" '
    { v[++n] = $1 + 0 }
    END { split("▁ ▂ ▃ ▄ ▅ ▆ ▇ █", blk, " "); out = ""; start = (n > W) ? n - W + 1 : 1
      for (i = start; i <= n; i++) { p = v[i]; if (p > 100) p = 100; if (p < 0) p = 0
        l = int(p / 100 * 7) + 1; c = (p >= 85) ? R : ((p >= 60) ? Y : G); out = out c blk[l] X }
      printf "%s", out }'
}
