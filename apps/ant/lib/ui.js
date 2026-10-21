// UI layer — aider-inspired minimal style with ant identity.
// Clean rules as separators, colored roles, content-first banners.

import path from "node:path";
import { execSync } from "node:child_process";
import { T, vlen, pad, padLeft, truncate, termWidth, link, visible } from "./theme.js";
import { renderMarkdown } from "./markdown.js";
import { renderDiff } from "./diff.js";

// Helper to get git branch
function getGitBranch() {
  try {
    return execSync('git rev-parse --abbrev-ref HEAD 2>/dev/null').toString().trim();
  } catch {
    return "no branch";
  }
}

// ---------- Backwards-compatible color helper ----------
export const C = {
  dim: (s) => T.dim(s),
  bold: (s) => T.bold(s),
  cyan: (s) => T.tool(s),
  green: (s) => T.success(s),
  yellow: (s) => T.warn(s),
  red: (s) => T.error(s),
  magenta: (s) => T.assistant(s),
  gray: (s) => T.muted(s),
};

export { vlen, visible, termWidth };

// ---------- Layout primitives ----------

const LEFT_PAD = 2;
const RIGHT_PAD = 2;

// A clean rule with optional centered tag — accented label, dim line.
export function rule(label = "", { color = T.muted } = {}) {
  const W = termWidth();
  if (!label) return color("─".repeat(W));
  const left = 4;
  const tag = " " + T.accent(label) + " ";
  const used = left + 1 + vlen(label) + 1; // dashes + spaces around label
  const right = Math.max(2, W - used);
  return color("─".repeat(left)) + tag + color("─".repeat(right));
}

// Two-tone rule: dim line, accented label.
export function section(label) {
  return "\n" + rule(label) + "\n";
}

// ---------- Framed box primitives ----------
// Rounded boxes with optional title + subtitle pills. Width-clamped.

function _vpad(s, n) {
  const v = vlen(s);
  return v >= n ? s : s + " ".repeat(n - v);
}

export function framedTop(title = "", subtitle = "", { width, color = T.muted } = {}) {
  const W = width || termWidth();
  const inner = W - 2;
  let titlePart = "";
  if (title) {
    const t = " " + T.bold(T.accent(title)) + " ";
    titlePart = color("┤") + t + color("├");
  }
  let subPart = "";
  if (subtitle) {
    subPart = color("┤") + T.accentBg(` ${subtitle} `) + color("├");
  }
  const titleLen = title ? vlen(" " + title + " ") + 2 : 0;
  const subLen = subtitle ? vlen(` ${subtitle} `) + 2 : 0;
  const fillTotal = Math.max(0, inner - titleLen - subLen - 4);
  const leftFill = "─".repeat(2);
  const rightFill = "─".repeat(Math.max(0, fillTotal));
  return color("╭") + color(leftFill) + titlePart + (subPart ? " " + subPart : "") + color(rightFill) + color("╮");
}

export function framedBot({ width, color = T.muted, footer = "" } = {}) {
  const W = width || termWidth();
  const inner = W - 2;
  if (!footer) return color("╰" + "─".repeat(inner) + "╯");
  const tag = color("┤") + " " + T.muted(footer) + " " + color("├");
  const used = vlen(" " + footer + " ") + 2;
  const fill = "─".repeat(Math.max(0, inner - used - 2));
  return color("╰") + color("─".repeat(2)) + tag + color(fill) + color("╯");
}

export function framedRow(content, { width, color = T.muted } = {}) {
  const W = width || termWidth();
  const inner = W - 4; // 2 borders + 2 inner pad
  return color("│") + " " + _vpad(truncate(content, inner), inner) + " " + color("│");
}

export function framedDivider({ width, color = T.muted, label = "" } = {}) {
  const W = width || termWidth();
  const inner = W - 2;
  if (!label) return color("├" + "─".repeat(inner) + "┤");
  const tag = " " + T.accentSoft(label) + " ";
  const used = vlen(tag);
  const fill = "─".repeat(Math.max(0, inner - used - 2));
  return color("├") + color("─".repeat(2)) + tag + color(fill) + color("┤");
}

// Convenience: render a fully framed block of lines with a title.
export function framedBlock(title, lines, { subtitle = "", width, footer = "", color = T.muted } = {}) {
  const W = width || termWidth();
  const out = [framedTop(title, subtitle, { width: W, color })];
  for (const ln of lines) {
    if (ln === "---") out.push(framedDivider({ width: W, color }));
    else if (ln && typeof ln === "object" && ln.divider) out.push(framedDivider({ width: W, color, label: ln.divider }));
    else out.push(framedRow(ln, { width: W, color }));
  }
  out.push(framedBot({ width: W, color, footer }));
  return out.join("\n");
}

// ---------- Sparklines & bar graphs ----------

const SPARK = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"];
export function sparkline(values, { color = T.accent } = {}) {
  if (!values || !values.length) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return color(values.map((v) => SPARK[Math.min(SPARK.length - 1, Math.max(0, Math.round(((v - min) / range) * (SPARK.length - 1))))]).join(""));
}

// Horizontal bar with filled blocks. width = total cells.
export function barGraph(value, max, { width = 24, color = T.accent, bg = T.muted } = {}) {
  const pct = Math.max(0, Math.min(1, max ? value / max : 0));
  const filled = Math.round(pct * width);
  const empty = width - filled;
  return color("█".repeat(filled)) + bg("░".repeat(empty));
}

// Multi-row bar graph for an exit summary, etc.
// rows: [{ label, value, max?, color? }]
export function multiBar(rows, { labelW = 10, barW = 30 } = {}) {
  const maxVal = Math.max(1, ...rows.map((r) => r.max ?? r.value ?? 0));
  return rows.map((r) => {
    const max = r.max ?? maxVal;
    const bar = barGraph(r.value || 0, max, { width: barW, color: r.color || T.accent });
    const lbl = T.muted(String(r.label).padEnd(labelW));
    const val = T.bold(String(r.display ?? r.value));
    return "  " + lbl + " " + bar + "  " + val;
  }).join("\n");
}

// ---------- Welcome banner ----------
// Aider's banner is just lines of facts. We adopt that, but lead with a small
// stylized wordmark + a one-line tagline. Recent sessions list inline.

const WORDMARK = [
  "  █████╗ ███╗   ██╗████████╗",
  " ██╔══██╗████╗  ██║╚══██╔══╝",
  " ███████║██╔██╗ ██║   ██║   ",
  " ██╔══██║██║╚██╗██║   ██║   ",
  " ██║  ██║██║ ╚████║   ██║   ",
  " ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ",
];

// Per-line gradient: deep → soft, top to bottom.
const WORDMARK_TINTS = [
  T.accentDeep, T.accentDeep, T.accent, T.accent, T.accentSoft, T.accentSoft,
];

function _centerInside(s, w) {
  const v = vlen(s);
  if (v >= w) return truncate(s, w);
  const pre = Math.floor((w - v) / 2);
  return " ".repeat(pre) + s + " ".repeat(w - v - pre);
}

export function welcomeBanner(cfg, version = "0.1.0", recent = []) {
  const W = termWidth(40, 110);
  const inner = W - 4;
  const cwd = (process.cwd() || "").replace(process.env.HOME || "", "~");
  const lines = [];

  // Wordmark — gradient + centered inside box
  if (W >= 40) {
    for (let i = 0; i < WORDMARK.length; i++) {
      const tint = WORDMARK_TINTS[i] || T.accent;
      lines.push(_centerInside(tint(WORDMARK[i]), inner));
    }
  } else {
    lines.push(_centerInside(T.bold(T.accent("ant")), inner));
  }

  // Tagline + version chip
  const versionChip = T.accentBg(` v${version} `);
  lines.push(_centerInside(T.bold(T.accentSoft("Ant CLI")) + " " + versionChip + T.muted("  ·  ") + T.dim("a terminal coding agent"), inner));
  lines.push("");
  lines.push({ divider: "session" });

  // Facts block — aligned key/value with bar accent
  const bar = T.accent("▎");
  const kv = (k, v) => bar + " " + T.muted(k.padEnd(9)) + v;
  lines.push(kv("model", T.bold(T.accentSoft(cfg.model || "(unset)")) + T.muted("  ·  ") + T.tool(cfg.provider || "?")));
  lines.push(kv("mode", cfg.mode && cfg.mode !== "default" ? modeBadge(cfg.mode) : T.muted("default")));
  lines.push(kv("cwd", T.tool(cwd)));

  if (recent && recent.length) {
    lines.push("");
    lines.push({ divider: "recent" });
    for (const s of recent.slice(0, 4)) {
      const msg = (s.firstMessage || "(empty)").replace(/\s+/g, " ").trim();
      const when = s.relTime ? T.muted(s.relTime.padStart(7) + "  ") : "";
      lines.push(T.accent("◆") + " " + when + truncate(msg, Math.max(20, inner - 14)));
    }
    lines.push("");
    lines.push(T.muted("resume: ") + T.accentSoft("ant -c") + T.muted("  or  ") + T.accentSoft("ant --session <id>"));
  } else {
    lines.push("");
    lines.push({ divider: "tips" });
    lines.push(T.muted("type a request like ") + T.bold(T.accentSoft("\"make a flask app\"")));
    lines.push(T.muted("run ") + T.accentSoft("/help") + T.muted(" for commands · ") + T.accentSoft("/key") + T.muted(" to set a key"));
  }

  return framedBlock("ant", lines, {
    subtitle: `v${version}`,
    width: W,
    footer: cfg.model ? `${cfg.model} · ${cfg.provider || "?"}` : "",
  });
}

// ---------- Tool headers / output ----------
// Inspired by Claude-style "● verb description (args) — Nms".
// We render single-line headers, with a tree-formatted body underneath.

const TOOL_META = {
  read_file:   { glyph: "▸", verb: "Read",     icon: "📖" },
  list_dir:    { glyph: "▸", verb: "List",     icon: "🗂" },
  search:      { glyph: "▸", verb: "Search",   icon: "🔍" },
  glob:        { glyph: "▸", verb: "Glob",     icon: "✨" },
  write_file:  { glyph: "+", verb: "Write",    icon: "📝" },
  edit_file:   { glyph: "*", verb: "Edit",     icon: "✏️" },
  apply_patch: { glyph: "*", verb: "Patch",    icon: "🩹" },
  mkdir:       { glyph: "+", verb: "Mkdir",    icon: "📁" },
  delete_path: { glyph: "-", verb: "Delete",   icon: "🗑" },
  bash:        { glyph: "$", verb: "Bash",     icon: "▶" },
  run_code:    { glyph: "$", verb: "Run",      icon: "🧪" },
  http_get:    { glyph: "↓", verb: "Fetch",    icon: "🌐" },
  git:         { glyph: "⌥", verb: "Git",      icon: "" },
  skill_list:  { glyph: "▸", verb: "Skills",   icon: "🎒" },
  skill_get:   { glyph: "▸", verb: "Skill",    icon: "📚" },
};

function toolColor(name) {
  if (["write_file", "edit_file", "apply_patch", "mkdir"].includes(name)) return T.success;
  if (["delete_path"].includes(name)) return T.del;
  if (["bash", "run_code"].includes(name)) return T.warn;
  if (["http_get"].includes(name)) return T.accentSoft;
  return T.accent;
}

export function toolHeader(name, summary, { ms } = {}) {
  const meta = TOOL_META[name] || { glyph: "●", verb: name, icon: "" };
  const color = toolColor(name);
  // Bolder, distinct vertical bar separator
  const dot = T.bold(color("┃"));
  const head = `${dot} ${T.bold(meta.verb)}`;
  const args = summary ? " " + T.muted(summary) : "";
  const right = ms != null ? T.muted(`  ${ms}ms`) : "";
  return head + args + right;
}

// Tree-connector formatted multi-line body. Auto-detects diff lines.
export function toolResultLines(result, max = 14) {
  const lines = String(result == null ? "" : result).split("\n");
  if (lines.length === 1 && !lines[0].trim()) return T.muted("  └─ (empty)");
  const head = lines.slice(0, max);
  const overflow = lines.length > max;
  const tail = overflow ? lines.slice(-2) : [];

  const colorize = (l) => {
    if (/^@@ /.test(l)) return T.muted(l);
    if (l.startsWith("+ ") || /^\+\s/.test(l)) return T.add(l);
    if (l.startsWith("- ") || /^-\s/.test(l)) return T.del(l);
    if (/^---|^\+\+\+|stdout|stderr|exit=/.test(l)) return T.muted(l);
    return l;
  };

  const out = [];
  for (let i = 0; i < head.length; i++) {
    const isLast = !overflow && i === head.length - 1;
    const elbow = isLast ? "└─ " : "├─ ";
    out.push("  " + T.muted(elbow) + colorize(head[i]));
  }
  if (overflow) {
    out.push("  " + T.muted(`├─ … +${lines.length - max} more lines`));
    for (let i = 0; i < tail.length; i++) {
      const elbow = i === tail.length - 1 ? "└─ " : "├─ ";
      out.push("  " + T.muted(elbow) + colorize(tail[i]));
    }
  }
  return out.join("\n");
}

export function diffBlock(before, after, filename = "") {
  return renderDiff(before, after, { filename });
}

// ---------- Mode badges ----------

const MODE_COLOR = {
  default:    T.tool,
  acceptEdits: T.success,
  plan:       T.warn,
  yolo:       T.error,
};

export function modeBadge(mode = "default") {
  const fn = MODE_COLOR[mode] || MODE_COLOR.default;
  return fn(`▎${mode}`);
}

// ---------- Status / exit summary ----------

export function statusLine({ tokens, elapsedMs }) {
  const s = Math.round((elapsedMs || 0) / 1000);
  const mm = Math.floor(s / 60), ss = s % 60;
  const t = `${mm}m${ss.toString().padStart(2, "0")}s`;
  const tk = tokens && tokens > 0 ? `${tokens.toLocaleString()} tok` : "";
  const core = [tk, t].filter(Boolean).join(T.muted(" · "));
  return "  " + T.muted(core);
}

export function exitSummary({ sessionId, model, provider, cwd, tokens, elapsedMs, turns, toolCalls, firstMessage, costUSD, tokensSeries }) {
  const W = termWidth(60, 100);
  const elapsedSec = Math.round((elapsedMs || 0) / 1000);
  const mm = Math.floor(elapsedSec / 60), ss = elapsedSec % 60;
  const elapsed = `${mm}m ${ss.toString().padStart(2, "0")}s`;
  const tk = (tokens || 0).toLocaleString();
  const cwdShort = (cwd || "").replace(process.env.HOME || "", "~");
  const firstMsg = (firstMessage || "(no messages)").replace(/\s+/g, " ").trim();
  const cost = costUSD != null ? `$${costUSD.toFixed(4)}` : "—";

  const bar = T.accent("▎");
  const kv = (k, v) => bar + " " + T.muted(k.padEnd(9)) + v;

  const lines = [];
  lines.push(kv("id", T.tool(sessionId || "")));
  lines.push(kv("first", truncate(firstMsg, W - 18)));
  lines.push(kv("model", T.bold(T.accentSoft(model || "?")) + T.muted("  ·  ") + T.tool(provider || "?")));
  lines.push(kv("cwd", T.tool(cwdShort)));
  lines.push("");
  lines.push({ divider: "stats" });

  // Bar graph of session metrics — each row scaled to its own max so they read.
  const barRows = multiBar([
    { label: "turns",    value: turns || 0,                max: Math.max(turns || 0, 10),                       color: T.accent,     display: String(turns || 0) },
    { label: "tools",    value: toolCalls || 0,            max: Math.max(toolCalls || 0, 10),                   color: T.accentSoft, display: String(toolCalls || 0) },
    { label: "tokens",   value: tokens || 0,               max: Math.max(tokens || 0, 1000),                    color: T.accentDeep, display: tk },
    { label: "elapsed",  value: elapsedSec,                max: Math.max(elapsedSec, 60),                       color: T.success,    display: elapsed },
    { label: "cost",     value: costUSD != null ? Math.round(costUSD * 10000) : 0, max: 10000,                  color: T.warn,       display: cost },
  ], { labelW: 9, barW: Math.max(16, W - 32) });
  for (const ln of barRows.split("\n")) lines.push(ln.replace(/^ {2}/, "")); // un-pad: framedRow adds its own pad

  if (tokensSeries && tokensSeries.length > 1) {
    lines.push("");
    lines.push(T.muted("trend     ") + sparkline(tokensSeries) + T.muted(`  ${tokensSeries.length} samples`));
  }

  lines.push("");
  lines.push({ divider: "resume" });
  lines.push(T.muted("resume:  ") + T.accentSoft(`ant --session ${sessionId || ""}`));
  lines.push(T.muted("or:      ") + T.accentSoft("ant -c"));

  return framedBlock("session summary", lines, {
    subtitle: elapsed,
    width: W,
    footer: `${(turns || 0)} turns · ${tk} tok`,
  });
}

// ---------- Assistant text with markdown ----------

export function assistantBlock(text) {
  if (!text || !text.trim()) return "";
  // Use a cleaner, slightly accented vertical bar instead of a bullet
  const bar = T.assistant("┃");
  const md = renderMarkdown(text);

  const indent = " ".repeat(LEFT_PAD);
  // Add spacing for cleaner reading
  return md.split('\n').map(line => indent + bar + " " + line).join('\n');
}

export function thoughtBlock(text) {
  if (!text || !text.trim()) return "";
  const icon = T.muted("◷");
  const lines = text.trim().split('\n');
  return lines.map(l => "  " + icon + " " + T.dim(l)).join('\n');
}

export function actionHeader(verb, description) {
  return T.success("●") + " " + T.bold(verb) + (description ? " " + description : "");
}

// A premium, IDE-like action summary box.
export function actionSummary(title, body, changes = []) {
  const W = termWidth(60, 100);
  const bar = T.accent("▀".repeat(W));
  const lines = [
    "",
    bar,
    "",
    T.bold(T.accent(`  ${title}`)),
    "",
    T.dim(`  ${body.replace(/\n/g, '\n  ')}`),
    ""
  ];

  for (const c of changes) {
    const icon = c.type === 'edit' ? T.success("✓ Edit") : T.tool("✓ Read");
    const detail = c.details ? ` ${T.muted(c.details)}` : "";
    lines.push(`  ${icon}  ${c.path}${detail}`);
  }
  lines.push("", bar, "");
  return lines.join("\n");
}

export function userPrefix(cfg) {
  // Modern, clean prompt: a soft cyan chevron.
  return T.accent("  ❯ ") + " ";
}

// Framed top of input — rounded with a "ask" pill.
export function inputBoxTop() {
  const W = termWidth();
  return T.dim("╭" + "─".repeat(W - 2) + "╮");
}

// Framed bottom + status bar with pretty separators.
export function inputBoxBottom(cfg = {}, stats = {}) {
  const W = termWidth();
  // Bottom border
  const bot = T.dim("╰" + "─".repeat(W - 2) + "╯");
  
  const branch = getGitBranch();
  const cwd = path.basename(process.cwd()) || "/";
  
  // Structured footer data
  const footerParts = [
    `  ${cwd}`,
    `  ${branch}`,
    `  no sandbox`,
    ` 󱚟 ${cfg.model || '?'}`
  ];

  const barContent = footerParts.join(' │ ');
  
  // Use accentBg for a premium solid status bar feel
  const bar = T.accentBg(barContent.padEnd(W).slice(0, W)); 
  
  return bot + "\n" + bar;
}

// ---------- Bottom bar (opt-in via ANT_BOTTOM_BAR=1) ----------
export function makeBottomBar({ hint = "⏵⏵ accept edits on (shift+tab to cycle)", getter = () => ({ tokens: 0, elapsedMs: 0 }) } = {}) {
  const out = process.stdout;
  let installed = false;
  const height = 3;
  const rows = () => out.rows || 24;
  const cols = () => out.columns || 80;

  const drawBox = () => {
    const r = rows(), c = cols();
    const top = r - height + 1;
    out.write("\x1b[s");
    out.write(`\x1b[${top};1H\x1b[2K` + T.muted("─".repeat(c)));
    out.write(`\x1b[${top + 1};1H\x1b[2K` + T.success("›") + " ");
    out.write(`\x1b[${top + 2};1H\x1b[2K` + T.muted("─".repeat(c)));
    out.write(`\x1b[${top + 1};4H`);
  };
  const install = () => {
    if (installed) return;
    installed = true;
    const r = rows();
    out.write(`\x1b[1;${Math.max(1, r - height)}r`);
    out.write(`\x1b[${Math.max(1, r - height)};1H`);
    drawBox();
  };
  const uninstall = () => {
    if (!installed) return;
    installed = false;
    out.write(`\x1b[r`);
    out.write(`\x1b[${rows()};1H\n`);
  };
  const redraw = () => { if (installed) drawBox(); };
  const onResize = () => {
    if (!installed) return;
    out.write(`\x1b[1;${Math.max(1, rows() - height)}r`);
    drawBox();
  };
  return { install, uninstall, redraw, onResize, height };
}

export function filePath(p) {
  const rel = p.replace(process.env.HOME || "", "~");
  const url = "file://" + (path.isAbsolute(p) ? p : path.resolve(p));
  return T.tool(link(rel, url));
}

// Compact bash/code output (head/tail).
export function compactOutput(text, head = 8, tail = 4) {
  const lines = String(text).split("\n");
  if (lines.length <= head + tail + 2) return text;
  const hidden = lines.length - head - tail;
  return [
    ...lines.slice(0, head),
    T.muted(`… ${hidden} hidden lines …`),
    ...lines.slice(-tail),
  ].join("\n");
}
