// Editor-grade unified diff. LCS line diff + char-level intra-line diff,
// syntax-highlighted context, change marker bar, hunk separators with ranges.

import { T, vlen, termWidth, visible } from "./theme.js";
import { highlightLine } from "./markdown.js";

// Detect language from filename so context lines pick up syntax colors.
function langFromFilename(name = "") {
  const m = name.toLowerCase().match(/\.([a-z0-9]+)$/);
  if (!m) return "";
  const ext = m[1];
  if (ext === "js" || ext === "mjs" || ext === "cjs") return "js";
  if (ext === "ts" || ext === "tsx") return "ts";
  if (ext === "py") return "py";
  if (ext === "sh" || ext === "bash" || ext === "zsh") return "sh";
  if (ext === "html" || ext === "htm") return "html";
  if (ext === "css") return "css";
  if (ext === "json") return "json";
  return "";
}

function lcsLines(a, b) {
  const n = a.length, m = b.length;
  const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const ops = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { ops.push(["=", a[i], i, j]); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { ops.push(["-", a[i], i, j]); i++; }
    else { ops.push(["+", b[j], i, j]); j++; }
  }
  while (i < n) ops.push(["-", a[i], i++, j]);
  while (j < m) ops.push(["+", b[j], i, j++]);
  return ops;
}

// Word-level LCS between two single lines, returns array of [op, token].
function wordDiff(a, b) {
  const tokenize = (s) => s.split(/(\s+|\b)/).filter(Boolean);
  const A = tokenize(a), B = tokenize(b);
  const n = A.length, m = B.length;
  const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = A[i] === B[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const out = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (A[i] === B[j]) { out.push(["=", A[i]]); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { out.push(["-", A[i]]); i++; }
    else { out.push(["+", B[j]]); j++; }
  }
  while (i < n) out.push(["-", A[i++]]);
  while (j < m) out.push(["+", B[j++]]);
  return out;
}

function renderWordDiff(ops, side /* "del" | "add" */) {
  let out = "";
  const baseColor = side === "del" ? T.del : T.add;
  for (const [op, tok] of ops) {
    if (op === "=") out += baseColor(tok);
    else if (op === "-" && side === "del") out += T.bold(T.delBg(T.del(tok)));
    else if (op === "+" && side === "add") out += T.bold(T.addBg(T.add(tok)));
  }
  return out;
}

// Pair adjacent del/add lines so we can render word-level intra-line diffs.
// Returns groups: { type: 'pair', dels, adds } | { type: 'eq', line } | etc.
function groupOps(ops) {
  const groups = [];
  let buf = { d: [], a: [] };
  const flush = () => {
    if (buf.d.length || buf.a.length) {
      groups.push({ type: "change", dels: buf.d, adds: buf.a });
      buf = { d: [], a: [] };
    }
  };
  for (const op of ops) {
    if (op[0] === "-") buf.d.push(op);
    else if (op[0] === "+") buf.a.push(op);
    else { flush(); groups.push({ type: "eq", op }); }
  }
  flush();
  return groups;
}

function buildHunks(groups, context = 3) {
  const hunks = [];
  let i = 0;
  while (i < groups.length) {
    if (groups[i].type === "eq") { i++; continue; }
    let start = i;
    let bk = 0;
    while (start > 0 && groups[start - 1].type === "eq" && bk < context) { start--; bk++; }
    let end = i;
    while (end < groups.length) {
      if (groups[end].type !== "eq") { end++; continue; }
      let run = 0;
      while (end + run < groups.length && groups[end + run].type === "eq") run++;
      if (run > context * 2) { end += context; break; }
      end += run;
    }
    hunks.push(groups.slice(start, end));
    i = end;
  }
  return hunks;
}

// Pad a visually-correct width (ANSI-aware).
function vpad(s, n) {
  const v = vlen(s);
  return v >= n ? s : s + " ".repeat(n - v);
}

function pill(label, color) {
  return color(` ${label} `);
}

export function renderDiff(before, after, { context = 3, maxLines = 80, filename = "" } = {}) {
  const a = String(before || "").split("\n");
  const b = String(after || "").split("\n");
  if (a.length > 1 && a[a.length - 1] === "") a.pop();
  if (b.length > 1 && b[b.length - 1] === "") b.pop();
  const lang = langFromFilename(filename);
  const ops = lcsLines(a, b);
  const groups = groupOps(ops);
  const hunks = buildHunks(groups, context);

  let adds = 0, dels = 0;
  for (const [op] of ops) {
    if (op === "+") adds++;
    else if (op === "-") dels++;
  }

  const W = termWidth();
  const maxLineNo = Math.max(a.length, b.length, 1);
  const gw = String(maxLineNo).length;
  const blank = " ".repeat(gw);

  // Header: ╭─ filename  +N  −N  · lang
  const out = [];
  const isNew = a.length === 0 || (a.length === 1 && a[0] === "");
  const tag = isNew ? T.accentBg(" NEW ") : "";
  const addPill = adds ? T.bold(T.add(`+${adds}`)) : "";
  const delPill = dels ? T.bold(T.del(`−${dels}`)) : "";
  const stats = [addPill, delPill].filter(Boolean).join(" ");
  const langTag = lang ? T.muted(" · ") + T.accentSoft(lang) : "";
  const headerName = filename ? T.bold(T.accentSoft(filename)) : T.bold("(diff)");
  out.push(T.muted("╭─ ") + headerName + (tag ? " " + tag : "") + (stats ? "  " + stats : "") + langTag);

  const renderContext = (line) => lang ? highlightLine(line, lang) : line;

  // Render a single line row.
  const truncRight = W - gw * 2 - 8;
  const trim = (s) => {
    const v = vlen(s);
    if (v <= truncRight) return s;
    // ANSI-aware truncation: walk visible chars
    const plain = visible(s);
    return plain.slice(0, Math.max(0, truncRight - 1)) + T.muted("…");
  };

  let aLine = 1, bLine = 1;
  let total = 0;
  let firstHunk = true;

  for (const h of hunks) {
    if (!firstHunk) {
      // Hunk separator with line ranges, like @@ -aLine +bLine @@
      out.push(T.muted("│ ") + T.accent(`@@ −${aLine} +${bLine} @@`));
    }
    firstHunk = false;

    for (const g of h) {
      if (total++ > maxLines) {
        out.push(T.muted("│ ") + T.muted("… diff truncated"));
        out.push(T.muted("╰─"));
        return out.join("\n");
      }

      if (g.type === "eq") {
        const ln = g.op[1];
        const an = String(aLine).padStart(gw);
        const bn = String(bLine).padStart(gw);
        out.push(
          T.muted(`│ ${an} ${bn} `) + T.muted("│ ") + T.muted("  ") + trim(renderContext(ln))
        );
        aLine++; bLine++;
        continue;
      }

      // Change group — pair dels with adds for word-diff where possible.
      const { dels: D, adds: A } = g;
      const pairs = Math.min(D.length, A.length);
      for (let k = 0; k < pairs; k++) {
        const delLine = D[k][1];
        const addLine = A[k][1];
        const wd = wordDiff(delLine, addLine);
        const an = String(aLine).padStart(gw);
        out.push(
          T.muted(`│ ${an} ${blank} `) + T.del("▌") + " " + T.del("− ") + trim(renderWordDiff(wd, "del"))
        );
        const bn = String(bLine).padStart(gw);
        out.push(
          T.muted(`│ ${blank} ${bn} `) + T.add("▌") + " " + T.add("+ ") + trim(renderWordDiff(wd, "add"))
        );
        aLine++; bLine++;
      }
      // Leftover dels (no matching add)
      for (let k = pairs; k < D.length; k++) {
        const an = String(aLine).padStart(gw);
        out.push(
          T.muted(`│ ${an} ${blank} `) + T.del("▌") + " " + T.del("− ") + trim(T.del(D[k][1]))
        );
        aLine++;
      }
      // Leftover adds (no matching del)
      for (let k = pairs; k < A.length; k++) {
        const bn = String(bLine).padStart(gw);
        out.push(
          T.muted(`│ ${blank} ${bn} `) + T.add("▌") + " " + T.add("+ ") + trim(T.add(A[k][1]))
        );
        bLine++;
      }
    }
  }

  out.push(T.muted("╰─ ") + T.muted(`${a.length} → ${b.length} lines`));
  if (out.length === 2) return T.muted("(no textual changes)");
  return out.join("\n");
}
