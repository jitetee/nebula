# nebula — markdown → ANSI renderer (POSIX awk; mawk/gawk/busybox safe)
# usage: awk -v COLS=80 -f md.awk < markdown
BEGIN {
  ESC = sprintf("%c", 27)
  cols = COLS + 0; if (cols < 24) cols = 80
  bytemode = (length("é") > 1)
  # mawk counts bytes: drop UTF-8 continuation bytes when measuring. Built at run time
  # because gawk in a UTF-8 locale rejects a literal [\200-\277].
  if (bytemode) cont = "[" sprintf("%c", 128) "-" sprintf("%c", 191) "]"
  R = ESC "[0m"; B = ESC "[1m"; BO = ESC "[22m"; I = ESC "[3m"; IO = ESC "[23m"
  U = ESC "[4m"; UO = ESC "[24m"; S = ESC "[9m"; SO = ESC "[29m"; D = ESC "[2m"
  CY = ESC "[38;5;51m"; BL = ESC "[38;5;75m"; GR = ESC "[38;5;120m"; YL = ESC "[38;5;221m"
  OR = ESC "[38;5;215m"; MG = ESC "[38;5;213m"; GY = ESC "[38;5;245m"; FG0 = ESC "[39m"
  CODEBG = ESC "[48;5;236m" ESC "[38;5;223m"; CODEOFF = ESC "[49m" FG0
  incode = 0; nt = 0; blank = 1
}
function vis(s,   t) { t = s; gsub(/\033\[[0-9;]*m/, "", t); if (bytemode) gsub(cont, "", t); return length(t) }
function rep(ch, n,   o, i) { o = ""; for (i = 0; i < n; i++) o = o ch; return o }

# ── inline spans ────────────────────────────────────────────────────────
function inline(s,   k, tok, i, txt, url, r, m, lead, trail, core, guard) {
  nc = 0
  while (match(s, /`[^`]+`/)) { nc++; code[nc] = substr(s, RSTART + 1, RLENGTH - 2)
    s = substr(s, 1, RSTART - 1) "\001" nc "\002" substr(s, RSTART + RLENGTH) }
  guard = 0
  while (match(s, /\[[^]]+\]\([^)]+\)/) && guard++ < 50) {
    tok = substr(s, RSTART, RLENGTH); i = index(tok, "](")
    txt = substr(tok, 2, i - 2); url = substr(tok, i + 2, length(tok) - i - 2)
    r = BL U txt UO FG0
    if (url != txt) r = r D " (" url ")" BO
    s = substr(s, 1, RSTART - 1) r substr(s, RSTART + RLENGTH)
  }
  guard = 0
  while (match(s, /\*\*[^*]+\*\*/) && guard++ < 50) s = substr(s, 1, RSTART - 1) B substr(s, RSTART + 2, RLENGTH - 4) BO substr(s, RSTART + RLENGTH)
  guard = 0
  while (match(s, /__[^_]+__/) && guard++ < 50) s = substr(s, 1, RSTART - 1) B substr(s, RSTART + 2, RLENGTH - 4) BO substr(s, RSTART + RLENGTH)
  guard = 0
  while (match(s, /~~[^~]+~~/) && guard++ < 50) s = substr(s, 1, RSTART - 1) S substr(s, RSTART + 2, RLENGTH - 4) SO substr(s, RSTART + RLENGTH)
  guard = 0
  while (match(s, /\*[^* ]([^*]*[^* ])?\*/) && guard++ < 50) s = substr(s, 1, RSTART - 1) I substr(s, RSTART + 1, RLENGTH - 2) IO substr(s, RSTART + RLENGTH)
  guard = 0
  while (match(s, /(^|[ (])_[^_ ]([^_]*[^_ ])?_([ ).,;:!?]|$)/) && guard++ < 50) {
    m = substr(s, RSTART, RLENGTH)
    lead = (substr(m, 1, 1) == "_") ? "" : substr(m, 1, 1)
    trail = (substr(m, length(m), 1) == "_") ? "" : substr(m, length(m), 1)
    core = substr(m, length(lead) + 2, length(m) - length(lead) - length(trail) - 2)
    s = substr(s, 1, RSTART - 1) lead I core IO trail substr(s, RSTART + RLENGTH)
  }
  while (match(s, /\001[0-9]+\002/)) { k = substr(s, RSTART + 1, RLENGTH - 2)
    s = substr(s, 1, RSTART - 1) CODEBG " " code[k] " " CODEOFF substr(s, RSTART + RLENGTH) }
  return s
}

# ── word wrap with hanging indent ───────────────────────────────────────
function wrap(first, restp, text,   n, w, i, line, cur, wl, pl, rl) {
  n = split(text, w, " "); line = first; cur = vis(first); pl = cur; rl = vis(restp)
  if (n == 0) { print first; return }
  for (i = 1; i <= n; i++) {
    wl = vis(w[i])
    if (cur + wl + (cur > pl ? 1 : 0) > cols - 1 && cur > pl) { print line; line = restp; cur = rl; pl = rl }
    if (cur > pl) { line = line " " w[i]; cur += 1 + wl } else { line = line w[i]; cur += wl }
  }
  print line
}

# ── tables ──────────────────────────────────────────────────────────────
function flushtable(   r, c, nr, nc2, cells, row, hdr, total, maxw, shrink, plain, line, sep, j, w) {
  nr = 0; nc2 = 0; hdr = 0
  for (r = 1; r <= nt; r++) {
    row = tbl[r]; sub(/^[ \t]*\|/, "", row); sub(/\|[ \t]*$/, "", row)
    c = split(row, cells, "|")
    if (r == 2 && c > 0) { w = 1; for (j = 1; j <= c; j++) if (cells[j] !~ /^[ \t]*:?-+:?[ \t]*$/) w = 0; if (w) { hdr = 1; continue } }
    nr++; for (j = 1; j <= c; j++) { v = cells[j]; gsub(/^[ \t]+|[ \t]+$/, "", v); cell[nr, j] = v }
    ncols[nr] = c; if (c > nc2) nc2 = c
  }
  for (j = 1; j <= nc2; j++) colw[j] = 1
  for (r = 1; r <= nr; r++) for (j = 1; j <= ncols[r]; j++) { st[r, j] = inline(cell[r, j]); w = vis(st[r, j]); if (w > colw[j]) colw[j] = w }
  total = 1; for (j = 1; j <= nc2; j++) total += colw[j] + 3
  while (total > cols - 1) {   # shrink the widest column
    maxw = 1; shrink = 1; for (j = 1; j <= nc2; j++) if (colw[j] > maxw) { maxw = colw[j]; shrink = j }
    if (maxw <= 6) break
    colw[shrink]--; total--
  }
  line = D "┌"; for (j = 1; j <= nc2; j++) line = line rep("─", colw[j] + 2) (j < nc2 ? "┬" : "┐"); print line R
  for (r = 1; r <= nr; r++) {
    line = D "│" R
    for (j = 1; j <= nc2; j++) {
      s2 = (j <= ncols[r]) ? st[r, j] : ""
      w = vis(s2)
      if (w > colw[j]) { # truncate plain text
        s2 = cell[r, j]; gsub(/[*_`~]/, "", s2); s2 = substr(s2, 1, colw[j] - 1) "…"; w = vis(s2) }
      if (r == 1 && hdr) s2 = B CY s2 R
      line = line " " s2 rep(" ", colw[j] - w) " " D "│" R
    }
    print line
    if (r == 1 && hdr && nr > 1) { sep = D "├"; for (j = 1; j <= nc2; j++) sep = sep rep("─", colw[j] + 2) (j < nc2 ? "┼" : "┤"); print sep R }
  }
  line = D "└"; for (j = 1; j <= nc2; j++) line = line rep("─", colw[j] + 2) (j < nc2 ? "┴" : "┘"); print line R
  nt = 0
}

{
  line = $0; sub(/\r$/, "", line)

  # fenced code block
  if (line ~ /^[ \t]*```/) {
    if (nt) flushtable()
    if (!incode) {
      incode = 1; lang = line; sub(/^[ \t]*```/, "", lang); gsub(/[ \t]+/, "", lang)
      printf "%s┌─%s %s%s%s %s%s%s\n", D, R, B OR, (lang == "" ? "code" : lang), R, D, rep("─", cols - 6 - length(lang == "" ? "code" : lang)), R
    } else { incode = 0; printf "%s└%s%s\n", D, rep("─", cols - 2), R }
    blank = 0; next
  }
  if (incode) {
    if (line ~ /^[ \t]*(#|\/\/|--) /) printf "%s│%s %s%s%s\n", D, R, GY, line, R
    else printf "%s│%s %s%s%s\n", D, R, ESC "[38;5;223m", line, R
    next
  }

  # table rows
  if (line ~ /^[ \t]*\|.*\|[ \t]*$/) { tbl[++nt] = line; next }
  if (nt) flushtable()

  if (line ~ /^[ \t]*$/) { if (!blank) print ""; blank = 1; next }
  wasblank = blank; blank = 0

  # horizontal rule
  if (line ~ /^[ \t]*(-{3,}|\*{3,}|_{3,})[ \t]*$/) { print D rep("─", cols - 1) R; next }

  # headings
  if (match(line, /^#+ /)) {
    lvl = RLENGTH - 1; txt = inline(substr(line, RLENGTH + 1))
    if (lvl == 1) { if (!wasblank) print ""; wrap(B CY "▌ ", B CY "  ", txt R); print D rep("═", cols - 1) R }
    else if (lvl == 2) { if (!wasblank) print ""; wrap(B BL "▎ ", B BL "  ", txt R); print D rep("─", cols - 1) R }
    else if (lvl == 3) { wrap(B MG "› ", B MG "  ", txt R) }
    else wrap(B "", B, txt R)
    next
  }

  # blockquote
  if (line ~ /^[ \t]*>/) { sub(/^[ \t]*> ?/, "", line); wrap(D "▎ " R I GY, D "▎ " R I GY, inline(line) R); next }

  # bullets
  if (match(line, /^[ \t]*[-*+] /)) {
    ind = int((RLENGTH - 2) / 2); txt = inline(substr(line, RLENGTH + 1))
    b = (ind % 2 == 0) ? "•" : "◦"
    wrap(rep(" ", ind * 2 + 1) CY b R " ", rep(" ", ind * 2 + 3), txt); next
  }
  # numbered
  if (match(line, /^[ \t]*[0-9]+[.)] /)) {
    ind = int(match(line, /[0-9]/) / 2); m2 = substr(line, 1, RLENGTH); gsub(/^[ \t]+/, "", m2)
    txt = inline(substr(line, RLENGTH + 1))
    wrap(rep(" ", ind * 2 + 1) B CY m2 R, rep(" ", ind * 2 + 2 + length(m2)), txt); next
  }

  # paragraph
  gsub(/^[ \t]+/, "", line)
  wrap("", "", inline(line))
}
END { if (nt) flushtable(); if (incode) print "" }
