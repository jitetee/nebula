// Single source of truth for colors. Detects truecolor / 256-color / no-color.
// All other modules import from here — never hardcode an escape code.

const NO_COLOR = !!process.env.NO_COLOR;
const FORCE = process.env.FORCE_COLOR;
const COLORTERM = process.env.COLORTERM || "";
const TERM = process.env.TERM || "";

function level() {
  if (NO_COLOR) return 0;
  if (FORCE === "0") return 0;
  if (FORCE === "3" || /truecolor|24bit/i.test(COLORTERM)) return 3;
  if (FORCE === "2" || /-256color/.test(TERM)) return 2;
  if (FORCE === "1") return 1;
  if (process.stdout.isTTY) return /color/.test(TERM) ? 2 : 1;
  return 0;
}

const LV = level();
const RESET = "\x1b[0m";

function sgr(...codes) {
  if (LV === 0) return (s) => String(s);
  return (s) => `\x1b[${codes.join(";")}m${s}${RESET}`;
}

function rgb(r, g, b) {
  if (LV === 0) return (s) => String(s);
  if (LV >= 3) return (s) => `\x1b[38;2;${r};${g};${b}m${s}${RESET}`;
  // approximate to 256-color
  const i = 16 + 36 * Math.round(r / 51) + 6 * Math.round(g / 51) + Math.round(b / 51);
  return (s) => `\x1b[38;5;${i}m${s}${RESET}`;
}

function bgRgb(r, g, b) {
  if (LV === 0) return (s) => String(s);
  if (LV >= 3) return (s) => `\x1b[48;2;${r};${g};${b}m${s}${RESET}`;
  const i = 16 + 36 * Math.round(r / 51) + 6 * Math.round(g / 51) + Math.round(b / 51);
  return (s) => `\x1b[48;5;${i}m${s}${RESET}`;
}

// Palette — Anthropic-ish warm neutrals + accents
export const T = {
  // base
  reset: RESET,
  dim: sgr(2),
  bold: sgr(1),
  italic: sgr(3),
  underline: sgr(4),

  // accents — blue family
  accent: rgb(96, 165, 250),       // primary blue
  accentSoft: rgb(147, 197, 253),  // soft sky
  accentDeep: rgb(59, 130, 246),   // deep blue
  accentBg: bgRgb(15, 30, 60),     // dark blue panel
  user: rgb(125, 211, 252),
  assistant: rgb(219, 234, 254),
  tool: rgb(96, 165, 250),
  warn: rgb(250, 204, 21),
  error: rgb(248, 113, 113),
  success: rgb(110, 231, 183),
  muted: rgb(120, 134, 156),

  // diff
  addBg: bgRgb(15, 50, 35),
  delBg: bgRgb(60, 25, 30),
  add: rgb(110, 231, 183),
  del: rgb(248, 113, 113),

  // syntax (blue-leaning palette)
  kw: rgb(125, 211, 252),
  str: rgb(165, 243, 252),
  num: rgb(253, 224, 71),
  com: rgb(100, 116, 139),
  fn: rgb(96, 165, 250),
  type: rgb(147, 197, 253),
  punct: rgb(186, 200, 220),

  // mode badges
  modeDefault: rgb(96, 165, 250),
  modeAccept: rgb(110, 231, 183),
  modePlan: rgb(250, 204, 21),
  modeYolo: rgb(248, 113, 113),
};

// Visible-length math (strips SGR escapes).
const ANSI = /\x1b\[[0-9;]*m/g;
export const visible = (s) => String(s).replace(ANSI, "");
export const vlen = (s) => [...visible(s)].length; // codepoint-aware

// Width-aware pad/truncate.
export function pad(s, n) {
  const v = vlen(s);
  if (v >= n) return s;
  return s + " ".repeat(n - v);
}

export function padLeft(s, n) {
  const v = vlen(s);
  if (v >= n) return s;
  return " ".repeat(n - v) + s;
}

export function truncate(s, n) {
  if (vlen(s) <= n) return s;
  const plain = visible(s);
  // walk codepoints to keep emoji intact
  let out = "";
  let count = 0;
  for (const ch of plain) {
    if (count + 1 >= n) break;
    out += ch;
    count++;
  }
  return out + "…";
}

export function termWidth(min = 40, max = 110) {
  const w = process.stdout.columns || 80;
  // Never exceed the actual terminal width — avoids hard wraps on narrow
  // terminals (Termux often reports 40–60 cols).
  return Math.min(w, Math.max(min, Math.min(max, w)));
}

// OSC-8 hyperlink (terminals that support it; harmless elsewhere).
export function link(label, url) {
  if (LV === 0 || !url) return label;
  return `\x1b]8;;${url}\x07${label}\x1b]8;;\x07`;
}

export const colorLevel = LV;
