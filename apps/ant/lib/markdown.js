// Tiny markdown + syntax highlighter — zero deps.
// Handles: headers, bold, italic, inline code, fenced code, lists, blockquote.

import { T } from "./theme.js";
import { highlight } from "./mini.js";

function highlightBlock(code, lang) {
  // Map our internal lang aliases to cli-highlight supported languages
  const language = lang === 'py' ? 'python' : (lang === 'sh' ? 'bash' : lang);
  try {
    return highlight(code, { language, ignoreIllegals: true });
  } catch {
    return code; // Fallback to plain text if highlighting fails
  }
}

// Render markdown -> ANSI string.
export function renderMarkdown(md) {
  if (!md) return "";
  const lines = String(md).split("\n");
  const out = [];
  let inFence = false;
  let fenceLang = "";
  let fenceBuf = [];

  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i];

    // fenced code
    const fence = ln.match(/^```\s*([a-zA-Z0-9_-]*)\s*$/);
    if (fence) {
      if (!inFence) {
        inFence = true;
        fenceLang = (fence[1] || "").toLowerCase();
        fenceBuf = [];
      } else {
        // close fence — render a rounded code-fence with lang pill
        const code = highlightBlock(fenceBuf.join("\n"), fenceLang);
        const W = 64;
        const pill = fenceLang ? T.accentBg(` ${fenceLang} `) : "";
        const headFill = T.muted("─".repeat(Math.max(2, W - (fenceLang ? fenceLang.length + 4 : 0))));
        out.push(T.muted("╭─") + pill + headFill);
        for (const c of code.split("\n")) {
          out.push(T.muted("│ ") + c);
        }
        out.push(T.muted("╰" + "─".repeat(W)));
        inFence = false;
        fenceLang = "";
        fenceBuf = [];
      }
      continue;
    }
    if (inFence) {
      fenceBuf.push(ln);
      continue;
    }

    // headers
    let m = ln.match(/^(#{1,6})\s+(.*)$/);
    if (m) {
      const level = m[1].length;
      const text = m[2];
      const prefix = "█".repeat(Math.max(1, 4 - level));
      out.push(T.accent(prefix) + " " + T.bold(text));
      continue;
    }

    // bullets
    m = ln.match(/^(\s*)[-*]\s+(.*)$/);
    if (m) {
      out.push(m[1] + T.accent("•") + " " + inline(m[2]));
      continue;
    }
    m = ln.match(/^(\s*)(\d+)\.\s+(.*)$/);
    if (m) {
      out.push(m[1] + T.accent(m[2] + ".") + " " + inline(m[3]));
      continue;
    }

    // blockquote
    m = ln.match(/^>\s?(.*)$/);
    if (m) {
      out.push(T.muted("│ ") + T.italic(inline(m[1])));
      continue;
    }

    // horizontal rule
    if (/^[-*_]{3,}$/.test(ln.trim())) {
      out.push(T.muted("─".repeat(60)));
      continue;
    }

    out.push(inline(ln));
  }

  // unterminated fence — flush as code
  if (inFence && fenceBuf.length) {
    const code = highlightBlock(fenceBuf.join("\n"), fenceLang);
    for (const c of code.split("\n")) out.push(T.muted("│ ") + c);
  }

  // collapse triple+ blank lines
  return out.join("\n").replace(/\n{3,}/g, "\n\n").trimEnd();
}

function inline(s) {
  if (!s) return "";
  // inline code
  s = s.replace(/`([^`]+)`/g, (_m, code) => T.accentBg(" " + code + " "));
  // bold **x** or __x__
  s = s.replace(/\*\*([^*]+)\*\*/g, (_m, t) => T.bold(t));
  s = s.replace(/__([^_]+)__/g, (_m, t) => T.bold(t));
  // italic *x* or _x_
  s = s.replace(/(^|[^*])\*([^*]+)\*/g, (_m, p, t) => p + T.italic(t));
  s = s.replace(/(^|[^_])_([^_]+)_/g, (_m, p, t) => p + T.italic(t));
  // links [text](url)
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, label, url) => T.tool(label) + T.muted(` (${url})`));
  return s;
}

function highlightLine(line, lang) { return highlightBlock(line, lang); }

export { highlightBlock, highlightLine };
