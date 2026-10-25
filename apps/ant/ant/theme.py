"""Colours. Nebula phosphor-green palette (256-colour indexes), auto-disabled without a TTY."""
import os
import re
import shutil
import sys


def _level():
    if os.environ.get("NO_COLOR"):
        return 0
    f = os.environ.get("FORCE_COLOR")
    if f == "0":
        return 0
    if f in ("1", "2", "3"):
        return int(f)
    term = os.environ.get("TERM", "")
    if sys.stdout.isatty():
        return 2 if "color" in term or "xterm" in term else 1
    return 0


LV = _level()
RESET = "\x1b[0m"


def _wrap(codes):
    if LV == 0:
        return lambda s: str(s)
    pre = "\x1b[%sm" % codes
    # re-open the style after any nested reset so nesting keeps the outer colour
    return lambda s: pre + str(s).replace(RESET, RESET + pre) + RESET


def fg(n):
    return _wrap("38;5;%d" % n)


def bg(n):
    return _wrap("48;5;%d" % n)


class _T:
    dim = staticmethod(_wrap("2"))
    bold = staticmethod(_wrap("1"))
    italic = staticmethod(_wrap("3"))
    underline = staticmethod(_wrap("4"))
    # Nebula greens (same family as the website and the rest of Nebula)
    accent = staticmethod(fg(48))
    accentSoft = staticmethod(fg(157))
    accentDeep = staticmethod(fg(35))
    accentBg = staticmethod(_wrap("48;5;22;38;5;157"))
    user = staticmethod(fg(120))
    assistant = staticmethod(fg(194))
    tool = staticmethod(fg(48))
    warn = staticmethod(fg(220))
    error = staticmethod(fg(203))
    success = staticmethod(fg(120))
    muted = staticmethod(fg(244))
    addBg = staticmethod(_wrap("48;5;22"))
    delBg = staticmethod(_wrap("48;5;52"))
    add = staticmethod(fg(120))
    delete = staticmethod(fg(203))


T = _T()

_ANSI = re.compile(r"\x1b\[[0-9;]*m|\x1b\]8;;[^\x07]*\x07")


def visible(s):
    return _ANSI.sub("", str(s))


def vlen(s):
    return len(visible(s))


def pad(s, n):
    v = vlen(s)
    return s if v >= n else s + " " * (n - v)


def truncate(s, n):
    if vlen(s) <= n:
        return s
    return visible(s)[: max(0, n - 1)] + "…"


def term_width(lo=40, hi=110):
    w = shutil.get_terminal_size((80, 24)).columns
    return min(w, max(lo, min(hi, w)))


def link(label, url):
    if LV == 0 or not url:
        return label
    return "\x1b]8;;%s\x07%s\x1b]8;;\x07" % (url, label)
