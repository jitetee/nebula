"""A small, dependency-free stand-in for the parts of `rich` that jtlearn uses.

Standard library only. It understands rich-style markup ("[bold cyan]hi[/]"), draws panels, tables and
rules with box characters, and wraps text to the terminal width. It is not a full copy of rich.
"""
import os
import re
import shutil
import sys
import unicodedata

RESET = "\033[0m"

_BASE = {"black": 0, "red": 1, "green": 2, "yellow": 3, "blue": 4, "magenta": 5, "cyan": 6, "white": 7}
_EXTRA = {
    "orange1": 214, "orange3": 172, "dark_orange": 208, "gold1": 220, "gold3": 178, "deep_sky_blue1": 39,
    "deep_sky_blue2": 38, "dodger_blue1": 33, "spring_green1": 48, "spring_green3": 41, "medium_purple": 104,
    "purple": 129, "violet": 177, "pink1": 218, "hot_pink": 205, "light_green": 120, "light_cyan": 159,
    "sky_blue1": 117, "turquoise2": 45, "aquamarine1": 122, "chartreuse1": 118, "khaki1": 228, "salmon1": 209,
    "grey": 244, "gray": 244, "orchid": 170, "plum1": 219, "dark_cyan": 36, "dark_green": 22, "navy_blue": 17,
    "bright_black": 8,
}
_ATTRS = {"bold": "1", "b": "1", "dim": "2", "italic": "3", "i": "3", "underline": "4", "u": "4",
          "blink": "5", "reverse": "7", "strike": "9", "s": "9"}


# J.I.T.E.T.E.E. look: the standard colour names map to the same phosphor-green palette Nebula and the website
# use. Set NEBULA_BRAND=classic to get the terminal's own colours back.
_BRAND = {"cyan": 48, "bright_cyan": 48, "blue": 35, "bright_blue": 35, "magenta": 157, "bright_magenta": 157,
          "green": 120, "bright_green": 120, "yellow": 221, "bright_yellow": 221, "red": 203, "bright_red": 203}
_BRANDED = os.environ.get("NEBULA_BRAND", "jitetee").lower() != "classic"


def _color_code(name, bg=False):
    """Return the SGR parameters for a colour name, or '' if unknown."""
    base = 48 if bg else 38
    n = name.strip().lower()
    if n in ("default", ""):
        return ""
    if _BRANDED and n in _BRAND:
        return f"{base};5;{_BRAND[n]}"
    if n.startswith("#") and len(n) == 7:
        try:
            r, g, b = int(n[1:3], 16), int(n[3:5], 16), int(n[5:7], 16)
            return f"{base};2;{r};{g};{b}"
        except ValueError:
            return ""
    m = re.fullmatch(r"color\((\d+)\)", n)
    if m:
        return f"{base};5;{m.group(1)}"
    m = re.fullmatch(r"gr[ae]y(\d+)", n)
    if m:
        v = min(100, int(m.group(1)))
        return f"{base};5;{232 + v * 23 // 100}"
    if n.startswith("bright_") and n[7:] in _BASE:
        return f"{base};5;{8 + _BASE[n[7:]]}"
    if n in _BASE:
        return f"{base};5;{_BASE[n]}" if False else str((40 if bg else 30) + _BASE[n])
    if n in _EXTRA:
        return f"{base};5;{_EXTRA[n]}"
    return ""


def style_to_ansi(spec):
    """'bold cyan on black' -> '\\033[1;36;40m' ('' if nothing applies)."""
    if not spec:
        return ""
    codes, bg, words = [], False, str(spec).replace(",", " ").split()
    for w in words:
        lw = w.lower()
        if lw == "on":
            bg = True
            continue
        if lw in ("not", "link") or lw.startswith("link="):
            continue
        if lw in _ATTRS and not bg:
            codes.append(_ATTRS[lw])
        else:
            c = _color_code(lw, bg)
            if c:
                codes.append(c)
        bg = False if lw != "on" else bg
    return "\033[" + ";".join(codes) + "m" if codes else ""


def cell_len(s):
    n = 0
    for ch in s:
        o = ord(ch)
        if o == 0x200D or 0xFE00 <= o <= 0xFE0F or unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in ("W", "F") or 0x1F300 <= o <= 0x1FAFF:
            n += 2
        else:
            n += 1
    return n


_ANSI = re.compile(r"\033\[[0-9;]*m")
_TAG = re.compile(r"(\\?)\[(/?)([A-Za-z#@][^\[\]]*|)\]")
_STYLE_WORD = re.compile(r"^(on|not|link|link=.*|[a-z_]+\d*|#[0-9a-fA-F]{6}|color\(\d+\)|\w+)$")


def strip_ansi(s):
    return _ANSI.sub("", s)


def vlen(s):
    return cell_len(strip_ansi(s))


class Span:
    """A run of text with one style string."""
    __slots__ = ("text", "style")

    def __init__(self, text, style=""):
        self.text, self.style = text, style


def parse_markup(s, base=""):
    """Markup string -> list of Span. Unknown/invalid tags stay literal text."""
    out, stack, pos = [], [base] if base else [], 0
    cur = lambda: " ".join(x for x in stack if x)
    for m in _TAG.finditer(s):
        if m.start() > pos:
            out.append(Span(s[pos:m.start()], cur()))
        pos = m.end()
        esc, close, body = m.group(1), m.group(2), m.group(3)
        if esc:                      # \[tag] -> literal [tag]
            out.append(Span("[" + close + body + "]", cur()))
            continue
        if close:
            if stack and (len(stack) > (1 if base else 0)):
                stack.pop()
            continue
        if body and all(_STYLE_WORD.match(w) for w in body.split()):
            stack.append(body)
        else:
            out.append(Span(m.group(0), cur()))
    if pos < len(s):
        out.append(Span(s[pos:], cur()))
    return out


def spans_to_ansi(spans):
    out, merged = [], []
    for sp in spans:                         # join neighbours with the same style (fewer escape codes)
        if merged and merged[-1].style == sp.style:
            merged[-1] = Span(merged[-1].text + sp.text, sp.style)
        else:
            merged.append(Span(sp.text, sp.style))
    for sp in merged:
        a = style_to_ansi(sp.style)
        out.append(f"{a}{sp.text}{RESET}" if a else sp.text)
    return "".join(out)


def markup_to_ansi(s, style=""):
    return spans_to_ansi(parse_markup(s, style))


def _split_words(spans):
    """Spans -> list of (text, style) tokens, each either a word or a run of spaces."""
    toks = []
    for sp in spans:
        for part in re.findall(r"\s+|\S+", sp.text):
            toks.append((part, sp.style))
    return toks


def wrap_spans(spans, width, no_wrap=False):
    """Word-wrap styled spans to width. Returns list of lines (each a list of Span)."""
    width = max(1, width)
    lines, cur, curw = [], [], 0

    def push():
        nonlocal cur, curw
        while cur and cur[-1].text.isspace():
            cur.pop()
        lines.append(cur)
        cur, curw = [], 0

    # explicit newlines first
    segs, line = [], []
    for sp in spans:
        parts = sp.text.split("\n")
        for i, p in enumerate(parts):
            if i:
                segs.append(line)
                line = []
            if p:
                line.append(Span(p, sp.style))
    segs.append(line)
    for seg in segs:
        cur, curw = [], 0
        first = True                              # keep indentation at the very start of a source line (like rich)
        for tok, st in _split_words(seg):
            w = cell_len(tok)
            lead, first = first, False
            if no_wrap:
                cur.append(Span(tok, st)); curw += w
                continue
            if tok.isspace():
                if curw == 0 and not lead:
                    continue
                if curw + w > width:
                    push(); continue
                cur.append(Span(tok, st)); curw += w
                continue
            if curw + w > width and curw > 0:
                push()
            while w > width:                      # a word longer than the line: hard split
                piece, pw = "", 0
                for ch in tok:
                    cw = cell_len(ch)
                    if pw + cw > width:
                        break
                    piece += ch; pw += cw
                cur.append(Span(piece, st)); push()
                tok = tok[len(piece):]; w = cell_len(tok)
            cur.append(Span(tok, st)); curw += w
        push()
    return lines or [[]]


def spans_width(spans):
    return sum(cell_len(s.text) for s in spans)


def pad_line(spans, width, justify="left"):
    w = spans_width(spans)
    extra = max(0, width - w)
    if justify == "right":
        return [Span(" " * extra)] + spans
    if justify == "center":
        l = extra // 2
        return [Span(" " * l)] + spans + [Span(" " * (extra - l))]
    return spans + [Span(" " * extra)]


def term_width(default=80):
    try:
        return max(20, shutil.get_terminal_size((default, 24)).columns)
    except Exception:
        return default


# ---- box characters: top-left, top, top-mid, top-right, side, head-left, head-mid, head-right, row-sep, hmid,
# bottom-left, bottom, bottom-mid, bottom-right
class Box:
    def __init__(self, tl, t, tm, tr, v, vm, ml, h, mm, mr, bl, b, bm, br):
        self.tl, self.t, self.tm, self.tr, self.v, self.vm = tl, t, tm, tr, v, vm
        self.ml, self.h, self.mm, self.mr, self.bl, self.b, self.bm, self.br = ml, h, mm, mr, bl, b, bm, br


ROUNDED = Box("╭", "─", "┬", "╮", "│", "│", "├", "─", "┼", "┤", "╰", "─", "┴", "╯")
SQUARE = Box("┌", "─", "┬", "┐", "│", "│", "├", "─", "┼", "┤", "└", "─", "┴", "┘")
HEAVY = Box("┏", "━", "┳", "┓", "┃", "┃", "┣", "━", "╋", "┫", "┗", "━", "┻", "┛")
DOUBLE = Box("╔", "═", "╦", "╗", "║", "║", "╠", "═", "╬", "╣", "╚", "═", "╩", "╝")
ASCII = Box("+", "-", "+", "+", "|", "|", "+", "-", "+", "+", "+", "-", "+", "+")
SIMPLE = Box(" ", " ", " ", " ", " ", " ", " ", "─", " ", " ", " ", " ", " ", " ")
MINIMAL = Box(" ", " ", " ", " ", " ", "│", " ", "─", "┼", " ", " ", " ", " ", " ")
HORIZONTALS = Box(" ", "─", " ", " ", " ", " ", " ", "─", " ", " ", " ", "─", " ", " ")


def to_lines(obj, width, style=""):
    """Anything printable -> list of rendered (ANSI) lines no wider than `width`."""
    if hasattr(obj, "_render_lines"):
        return obj._render_lines(width)
    spans = obj._spans() if hasattr(obj, "_spans") else parse_markup(str(obj), style)
    return [spans_to_ansi(l) for l in wrap_spans(spans, width)]


def ansi_to_spans(line):
    return [Span(line)]
