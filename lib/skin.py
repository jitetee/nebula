#!/usr/bin/env python3
"""skin.py - the shared J.I.T.E.T.E.E. terminal look (same style as jtlearn), standard library only.

Every Nebula screen (bash) calls this through lib/skin.sh:

  skin.py box    [--title T] [--width N] [--style rounded|double|heavy|plain]   stdin lines -> framed panel
  skin.py menu   [--title T] [--width N]    stdin "key<TAB>icon<TAB>label<TAB>description" -> two-column menu panel
  skin.py table  [--title T] [--width N]    stdin TSV, first line = header -> table
  skin.py banner TEXT [--tag LINE]...       big block letters inside a double frame
  skin.py bubble [--right] [--name N] [--time T] [--width N]   stdin text -> chat bubble
  skin.py prompt [TEXT]                     the  "└─➤ Your choice:"  prompt (no newline)
  skin.py kv     [--title T]                stdin "key<TAB>value" -> aligned key/value panel
  skin.py status KIND TEXT                  ✔ / ⚠ / ✖ / ℹ line
  skin.py bar PCT [--width N]               progress bar

NO_COLOR, a dumb terminal, or NEBULA_PLAIN=1 switch to plain ASCII lines.  Under 40 columns boxes
become a simple titled rule so phones never wrap.
"""
import os
import re
import shutil
import sys
import unicodedata

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RESET = "\x1b[0m"

PLAIN = bool(os.environ.get("NO_COLOR")) or os.environ.get("TERM") == "dumb" or os.environ.get("NEBULA_PLAIN") == "1"


def fg(n):
    return "" if PLAIN else "\x1b[38;5;%dm" % n


BOLD = "" if PLAIN else "\x1b[1m"
DIM = "" if PLAIN else "\x1b[2m"
RS = "" if PLAIN else RESET
PRIMARY, SECOND, ACCENT, DANGER, INFO, MUTED, BORDER, TEXT = (
    fg(48), fg(120), fg(221), fg(203), fg(35), fg(245), fg(35), fg(255))

STYLES = {
    "rounded": "╭╮╰╯─│├┤┬┴┼",
    "double": "╔╗╚╝═║╠╣╦╩╬",
    "heavy": "┏┓┗┛━┃┣┫┳┻╋",
    "plain": "++++-|+++++",
}


def cols():
    try:
        c = int(os.environ.get("NEBULA_COLS") or 0)
    except ValueError:
        c = 0
    return c or shutil.get_terminal_size((80, 24)).columns


def cw(ch):
    o = ord(ch)
    if o == 0xFE0F or o == 0x200D or unicodedata.combining(ch):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    if 0x1F300 <= o <= 0x1FAFF or o in (0x26A1, 0x2B50, 0x2764, 0x2705, 0x274C):
        return 2 if o != 0x2764 else 1
    return 1


def vlen(s):
    return sum(cw(c) for c in ANSI.sub("", s))


def pad(s, n):
    return s + " " * max(0, n - vlen(s))


def wrap(line, width):
    """Wrap one line (may contain ANSI) to width cells; continuation keeps the leading indent."""
    if vlen(line) <= width:
        return [line]
    lead = len(line) - len(line.lstrip(" "))
    indent = " " * min(lead, max(0, width // 2))
    out, cur, curw = [], "", 0
    for word in re.split(r"( +)", line.lstrip(" ")):
        if word == "":
            continue
        ww = vlen(word)
        if curw + ww > width - len(indent) and curw > 0 and word.strip():
            out.append(indent + cur.rstrip())
            cur, curw = "", 0
        if ww > width - len(indent):           # one huge word: hard-split
            for ch in re.findall(r"\x1b\[[0-9;?]*[A-Za-z]|.", word):
                w = 0 if ANSI.fullmatch(ch) else cw(ch)
                if curw + w > width - len(indent):
                    out.append(indent + cur)
                    cur, curw = "", 0
                cur += ch
                curw += w
            continue
        cur += word
        curw += ww
    out.append(indent + cur.rstrip())
    return out


def box_width(req=None):
    w = req or min(cols() - 1, 100)
    return max(20, min(w, cols() - 1))


def frame(lines, title="", width=None, style="rounded", color=BORDER, title_color=None):
    """Return the framed lines."""
    title_color = title_color or (BOLD + PRIMARY)
    W = box_width(width)
    if cols() < 40 or PLAIN and style != "plain":
        style = "plain" if PLAIN else style
    tl, tr, bl, br, h, v = STYLES[style][:6]
    if cols() < 40 and not PLAIN:               # phones: no side borders, just rules
        out = []
        if title:
            out.append(color + h * 2 + RS + " " + title_color + title + RS + " " + color + h * max(2, W - vlen(title) - 4) + RS)
        else:
            out.append(color + h * W + RS)
        for ln in lines:
            out.extend(wrap(ln, W))
        out.append(color + h * W + RS)
        return out
    inner = W - 4
    out = []
    if title:
        t = " " + title + " "
        side = max(1, W - 2 - vlen(t))
        left = side // 2
        out.append(color + tl + h * left + RS + title_color + t + RS + color + h * (side - left) + tr + RS)
    else:
        out.append(color + tl + h * (W - 2) + tr + RS)
    for ln in lines:
        for seg in wrap(ln, inner):
            out.append(color + v + RS + " " + pad(seg, inner) + " " + color + v + RS)
    out.append(color + bl + h * (W - 2) + br + RS)
    return out


def emit(lines):
    sys.stdout.write("\n".join(lines) + "\n")


def read_lines():
    if sys.stdin.isatty():
        return []
    t = sys.stdin.read().rstrip("\n")
    return t.split("\n") if t else []


def split_cols(argv):
    opts = {"title": "", "width": None, "style": "rounded", "tag": [], "right": False, "nodot": False, "name": "", "time": ""}
    rest, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a in ("--title", "--width", "--style", "--name", "--time", "--tag") and i + 1 < len(argv):
            k = a[2:]
            if k == "tag":
                opts["tag"].append(argv[i + 1])
            elif k == "width":
                opts["width"] = int(argv[i + 1])
            else:
                opts[k] = argv[i + 1]
            i += 2
        elif a == "--nodot":
            opts["nodot"] = True
            i += 1
        elif a == "--right":
            opts["right"] = True
            i += 1
        else:
            rest.append(a)
            i += 1
    return opts, rest


def menu_rows(rows, width, dot=". "):
    """rows: key, icon, label, desc  ->  list of aligned strings with a │ between label and description."""
    kw = max([vlen(r[0]) for r in rows] + [1])
    lw = max([vlen(r[2]) + (vlen(r[1]) + 1 if r[1] else 0) for r in rows] + [1])
    inner = width - 4
    lw = min(lw + kw + 2, max(14, inner // 2))
    out = []
    for key, icon, label, desc in rows:
        left = (icon + " " if icon else "") + ACCENT + key + RS + (dot if key else "") + SECOND + label + RS
        if vlen(left) > lw:                      # too long for its column: cut with an ellipsis
            plain = ANSI.sub("", left)
            while vlen(plain) > lw - 1:
                plain = plain[:-1]
            left = SECOND + plain + "…" + RS
        left = pad(left, lw)
        d = DIM + MUTED + desc + RS
        first = True
        for seg in wrap(desc, max(10, inner - lw - 3)) or [""]:
            out.append((left if first else " " * lw) + " " + BORDER + "│" + RS + " " + MUTED + seg + RS)
            first = False
    return out


def cmd_box(o, rest):
    emit(frame(read_lines(), o["title"], o["width"], o["style"]))


def cmd_menu(o, rest):
    rows = []
    for ln in read_lines():
        p = ln.split("\t")
        p += [""] * (4 - len(p))
        rows.append(p[:4])
    W = box_width(o["width"])
    if cols() < 40 and not PLAIN:               # phone: label on one line, description underneath
        body = []
        for k, ic, lb, ds in rows:
            body.append((ic + " " if ic else "") + ACCENT + k + RS + ("  " if o["nodot"] else ". ") + SECOND + lb + RS)
            if ds:
                body.append("   " + MUTED + ds + RS)
        emit(frame(body, o["title"], W))
        return
    emit(frame(menu_rows(rows, W, "  " if o["nodot"] else ". "), o["title"], W))


def cmd_table(o, rest):
    data = [ln.split("\t") for ln in read_lines()]
    if not data:
        return
    head, body = data[0], data[1:]
    n = len(head)
    body = [r + [""] * (n - len(r)) for r in body]
    W = box_width(o["width"])
    inner = W - 4
    widths = [max(vlen(r[i]) for r in [head] + body) for i in range(n)]
    gap = 3 * (n - 1)
    while sum(widths) + gap > inner and max(widths) > 6:
        widths[widths.index(max(widths))] -= 1
    def cell(s, w):
        s = ANSI.sub("", s) if vlen(s) > w else s
        while vlen(s) > w:
            s = s[:-1]
        return pad(s, w)
    sep = " " + BORDER + "│" + RS + " "
    lines = [BOLD + PRIMARY + sep.join(cell(h, widths[i]) for i, h in enumerate(head)) + RS,
             BORDER + "─┼─".join("─" * w for w in widths) + RS]
    for r in body:
        lines.append(sep.join(TEXT + cell(c, widths[i]) + RS for i, c in enumerate(r)))
    emit(frame(lines, o["title"], W))


def cmd_kv(o, rest):
    rows = [ln.split("\t", 1) + [""] for ln in read_lines()]
    rows = [r[:2] for r in rows]
    kw = max([vlen(r[0]) for r in rows] + [1])
    emit(frame([ACCENT + pad(k, kw) + RS + "  " + BORDER + "│" + RS + " " + TEXT + v + RS for k, v in rows], o["title"], o["width"]))


def load_alphabet():
    home = os.environ.get("NEBULA_HOME") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    glyphs, cur = {}, None
    try:
        for ln in open(os.path.join(home, "assets", "alphabet.txt"), encoding="utf-8"):
            ln = ln.rstrip("\n")
            if ln.startswith("#"):
                continue
            if ln.startswith(":") and len(ln) >= 2:
                cur = ln[1]
                glyphs[cur] = []
            elif cur is not None:
                glyphs[cur].append(ln)
    except OSError:
        pass
    return glyphs


def big(text):
    g = load_alphabet()
    rows = [""] * 5
    for ch in text.upper():
        gl = g.get(ch) or g.get(" ") or ["  "] * 5
        gl = (gl + [""] * 5)[:5]
        w = max(vlen(x) for x in gl)
        for i in range(5):
            rows[i] += pad(gl[i], w) + " "
    return rows


def cmd_banner(o, rest):
    text = rest[0] if rest else "NEBULA"
    W = box_width(o["width"])
    art = big(text)
    if cols() < 40 or max(vlen(r) for r in art) > W - 4:
        art = [BOLD + PRIMARY + text.upper() + RS]
    else:
        art = [PRIMARY + r + RS for r in art]
    body = art + [""] + [MUTED + t + RS if i else ACCENT + t + RS for i, t in enumerate(o["tag"])]
    emit(frame(body, "", W, "double"))


def cmd_bubble(o, rest):
    lines = read_lines()
    W = box_width(o["width"])
    mw = max(16, int(W * 0.7))
    wrapped = []
    for ln in lines:
        wrapped.extend(wrap(ln, mw - 4))
    bw = max([vlen(x) for x in wrapped] + [vlen(o["name"]) + 2, 4]) + 4
    col = PRIMARY if o["right"] else INFO
    title = o["name"]
    box = frame(wrapped, title, bw, "rounded", color=col, title_color=BOLD + col)
    if o["time"]:
        box.append(MUTED + o["time"] + RS)
    off = max(0, W - bw) if o["right"] else 0
    emit([" " * off + ln for ln in box])


def cmd_rule(o, rest):
    W = box_width(o["width"])
    t = " " + o["title"] + " "
    side = max(2, W - vlen(t))
    left = side // 2
    emit([BORDER + "─" * left + RS + BOLD + PRIMARY + t + RS + BORDER + "─" * (side - left) + RS])


def cmd_prompt(o, rest):
    text = rest[0] if rest else "Your choice"
    sys.stdout.write(BORDER + "└─➤ " + RS + BOLD + PRIMARY + text + ":" + RS + " ")


def cmd_status(o, rest):
    kind, text = (rest + ["", ""])[:2]
    icon, col = {"OK": ("✔", SECOND), "WARN": ("⚠", ACCENT), "ERR": ("✖", DANGER), "INFO": ("ℹ", INFO)}.get(kind, ("•", ""))
    sys.stdout.write("  %s%s%s %s\n" % (col, icon, RS, text))


def cmd_bar(o, rest):
    pct = max(0, min(100, int(rest[0] if rest else 0)))
    w = o["width"] or 20
    f = pct * w // 100
    col = SECOND if pct < 75 else ACCENT if pct < 95 else DANGER
    sys.stdout.write("%s%s%s%s%s %d%%\n" % (col, "█" * f, MUTED, "░" * (w - f), RS, pct))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    cmd = sys.argv[1]
    o, rest = split_cols(sys.argv[2:])
    fn = globals().get("cmd_" + cmd)
    if not fn:
        print("skin.py: unknown command " + cmd, file=sys.stderr)
        return 2
    try:
        fn(o, rest)
    except BrokenPipeError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
