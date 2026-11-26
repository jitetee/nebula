"""Nebula's terminal GUI toolkit (curses, standard library only): the same look, mouse/touch and dialogs for every GUI.

Colours come from the shared palette (`nebula palette`), icons from nebula_core.icons.

    from nebula_core import tui
    class App(tui.App):
        def draw(self, ui): ...                 # paint the whole screen with ui.text / ui.box / ui.button / ui.bar
        def key(self, ui, k): ...               # return False to quit
        def click(self, ui, y, x, double): ...  # only for areas that are not buttons
    tui.run(App())

Dialogs (blocking, drawn over the current screen): ui.confirm, ui.prompt, ui.choose, ui.form, ui.message, ui.pager.
"""
import curses
import locale
import os
import time
import unicodedata

from . import icons, theme

ESC, ENTER = 27, (10, 13, curses.KEY_ENTER)
BACKSPACE = (127, 8, curses.KEY_BACKSPACE)


def width(s):
    w = 0
    for ch in s:
        if unicodedata.combining(ch):
            continue
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def clip(s, n):
    """s cut to at most n columns (with … when cut)."""
    if n <= 0:
        return ""
    if width(s) <= n:
        return s
    out, w = "", 0
    for ch in s:
        cw = width(ch)
        if w + cw > n - 1:
            break
        out += ch; w += cw
    return out + "…"


def human(n):
    n = float(n)
    for u in ("B", "K", "M", "G", "T"):
        if n < 1024 or u == "T":
            return ("%d%s" % (n, u)) if u == "B" else ("%.1f%s" % (n, u))
        n /= 1024


class UI:
    def __init__(self, scr):
        self.scr = scr
        self.regions = []      # (y, x, h, w, callback)
        self.draw_cb = lambda ui: None
        self._last_click = (0, -1, -1)
        self.double = False
        self.h = self.w = 0
        self._colors()
        curses.curs_set(0)
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        curses.mouseinterval(0)
        scr.keypad(True)

    # ── colours ──
    def _colors(self):
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        p = theme.load()
        big = curses.COLORS >= 256
        c = lambda role, fallback: p[role]["idx"] if big else fallback
        P, S, A, D, B, M, T = c("primary", curses.COLOR_GREEN), c("second", curses.COLOR_GREEN), c("accent", curses.COLOR_YELLOW), c("danger", curses.COLOR_RED), c("border", curses.COLOR_GREEN), c("muted", curses.COLOR_WHITE), c("text", curses.COLOR_WHITE)
        panel = 235 if big else -1
        black = 232 if big else curses.COLOR_BLACK
        pairs = {1: (T, -1), 2: (P, -1), 3: (S, -1), 4: (A, -1), 5: (D, -1), 6: (M, -1), 7: (black, P), 8: (T, panel), 9: (P, panel), 10: (black, B),
                 11: (A, panel), 12: (D, panel), 13: (M, panel), 14: (black, A), 15: (black, D), 16: (B, -1)}
        for i, (f, b) in pairs.items():
            curses.init_pair(i, f, b)
        cp = curses.color_pair
        self.a = {"text": cp(1), "primary": cp(2) | curses.A_BOLD, "second": cp(3), "accent": cp(4), "danger": cp(5), "dim": cp(6),
                  "sel": cp(7) | curses.A_BOLD, "panel": cp(8), "panel_p": cp(9) | curses.A_BOLD, "bar": cp(10) | curses.A_BOLD,
                  "panel_a": cp(11), "panel_d": cp(12), "panel_dim": cp(13), "warn_sel": cp(14) | curses.A_BOLD, "danger_sel": cp(15) | curses.A_BOLD,
                  "border": cp(16), "bold": curses.A_BOLD}

    # ── drawing ──
    def text(self, y, x, s, attr="text", maxw=None):
        if y < 0 or y >= self.h or x >= self.w:
            return
        n = (maxw if maxw is not None else self.w - x)
        n = min(n, self.w - x)
        s = clip(s, n) if width(s) > n else s
        try:
            self.scr.addstr(y, max(0, x), s, self.a.get(attr, attr) if isinstance(attr, str) else attr)
        except curses.error:
            pass

    def fill(self, y, x, h, w, attr="text"):
        for r in range(y, min(y + h, self.h)):
            self.text(r, x, " " * min(w, self.w - x), attr)

    def hline(self, y, x, w, attr="border", ch="─"):
        self.text(y, x, ch * w, attr, w)

    def box(self, y, x, h, w, title="", attr="border", fill=True):
        if h < 2 or w < 2:
            return
        if fill:
            self.fill(y, x, h, w, "text")
        self.text(y, x, "╭" + "─" * (w - 2) + "╮", attr, w)
        for r in range(y + 1, y + h - 1):
            self.text(r, x, "│", attr, 1); self.text(r, x + w - 1, "│", attr, 1)
        self.text(y + h - 1, x, "╰" + "─" * (w - 2) + "╯", attr, w)
        if title:
            self.text(y, x + 2, " " + clip(title, w - 6) + " ", "primary")

    def bar(self, y, x, w, frac, attr="primary", label=""):
        frac = max(0.0, min(1.0, frac))
        full = int(frac * w)
        self.text(y, x, "█" * full, attr, w)
        self.text(y, x + full, "░" * (w - full), "dim", w - full)
        if label:
            self.text(y, x + max(0, (w - width(label)) // 2), label, "bar" if False else "text")

    def button(self, y, x, label, cb, attr="panel", key=None):
        """A clickable label; returns its width."""
        s = " %s " % label
        self.text(y, x, s, attr)
        w = width(s)
        self.regions.append((y, x, 1, w, cb))
        return w

    def region(self, y, x, h, w, cb):
        self.regions.append((y, x, h, w, cb))

    # ── event loop ──
    def size(self):
        self.h, self.w = self.scr.getmaxyx()

    def redraw(self):
        self.size()
        self.regions = []
        self.scr.erase()
        self.draw_cb(self)
        self.scr.refresh()

    def _hit(self, y, x):
        for (ry, rx, rh, rw, cb) in reversed(self.regions):
            if ry <= y < ry + rh and rx <= x < rx + rw:
                return cb, (y - ry, x - rx)
        return None, None

    def get_event(self, timeout=500):
        """('key', code) | ('click', y, x, double) | ('scroll', ±n) | ('tick',) | ('resize',)"""
        self.scr.timeout(timeout)
        k = self.scr.getch()
        if k == -1:
            return ("tick",)
        if k == curses.KEY_RESIZE:
            return ("resize",)
        if k == curses.KEY_MOUSE:
            try:
                _, mx, my, _, b = curses.getmouse()
            except curses.error:
                return ("tick",)
            if b & curses.BUTTON4_PRESSED:
                return ("scroll", -3)
            if b & getattr(curses, "BUTTON5_PRESSED", 0x200000):
                return ("scroll", 3)
            if b & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                now = time.time()
                lt, ly, lx = self._last_click
                dbl = bool(b & curses.BUTTON1_DOUBLE_CLICKED) or (now - lt < 0.6 and (ly, lx) == (my, mx))
                self._last_click = (0 if dbl else now, my, mx)
                return ("click", my, mx, dbl)
            return ("tick",)
        return ("key", k)

    def dispatch_click(self, y, x, double=False):
        self.double = double      # callbacks can read ui.double (a double tap)
        cb, rel = self._hit(y, x)
        if cb:
            cb()
            return True
        return False

    # ── dialogs ──
    def _overlay(self, h, w, title="", attr="border"):
        self.redraw()
        y, x = max(0, (self.h - h) // 2), max(0, (self.w - w) // 2)
        self.box(y, x, h, w, title, attr)
        return y, x

    def message(self, title, lines, ok="OK"):
        lines = [clip(l, self.w - 8) for l in (lines if isinstance(lines, list) else str(lines).split("\n"))]
        while True:
            self.size()
            w = min(self.w - 2, max([width(l) for l in lines] + [width(title) + 6, 24]) + 4)
            h = len(lines) + 4
            y, x = self._overlay(h, w, title)
            for i, l in enumerate(lines):
                self.text(y + 1 + i, x + 2, l, "text", w - 4)
            res = []
            self.button(y + h - 2, x + (w - width(ok) - 2) // 2, ok, lambda: res.append(1), "sel")
            self.scr.refresh()
            ev = self.get_event(1000)
            if ev[0] == "key" and ev[1] in (ESC, ord("q"), ord(" "), *ENTER):
                return
            if ev[0] == "click":
                self.dispatch_click(ev[1], ev[2], ev[3])
                if res:
                    return

    def confirm(self, msg, yes="Yes", no="No", danger=False, typed=None, title="Confirm"):
        """True/False. danger=True paints it red; typed='name' makes the user type that text first."""
        lines = [clip(l, self.w - 8) for l in str(msg).split("\n")]
        buf = ""
        sel = 1 if danger else 0
        while True:
            self.size()
            w = min(self.w - 2, max([width(l) for l in lines] + [width(title) + 6, 30]) + 4)
            h = len(lines) + 4 + (2 if typed else 0)
            y, x = self._overlay(h, w, title, "danger" if danger else "border")
            for i, l in enumerate(lines):
                self.text(y + 1 + i, x + 2, l, "danger" if danger and i == 0 else "text", w - 4)
            if typed:
                self.text(y + len(lines) + 1, x + 2, "Type  %s  to confirm:" % typed, "accent", w - 4)
                self.text(y + len(lines) + 2, x + 2, "› " + buf + "▏", "primary", w - 4)
            res = {}
            by = y + h - 2
            bx = x + 2
            bx += self.button(by, bx, no, lambda: res.update(v=False), "sel" if sel == 1 else "panel") + 2
            self.button(by, bx, yes, lambda: res.update(v=True), ("danger_sel" if danger else "sel") if sel == 0 else "panel")
            self.scr.refresh()
            ev = self.get_event(1000)
            if ev[0] == "click":
                self.dispatch_click(ev[1], ev[2], ev[3])
            elif ev[0] == "key":
                k = ev[1]
                if k == ESC:
                    return False
                if typed is not None:
                    if k in ENTER:
                        return buf == typed
                    if k in BACKSPACE:
                        buf = buf[:-1]
                    elif 32 <= k < 127:
                        buf += chr(k)
                    continue
                if k in (curses.KEY_LEFT, curses.KEY_RIGHT, 9, ord("h"), ord("l")):
                    sel = 1 - sel
                elif k in (ord("y"), ord("Y")):
                    return True
                elif k in (ord("n"), ord("N")):
                    return False
                elif k in ENTER:
                    return sel == 0
            if "v" in res:
                if typed is not None and res["v"]:
                    return buf == typed
                return res["v"]

    def prompt(self, title, default="", hint="", secret=False):
        """One line of text, or None if cancelled. Left/right/home/end/backspace/delete work."""
        buf, pos = list(default), len(default)
        while True:
            self.size()
            w = min(self.w - 2, max(40, width(title) + 8, width(hint) + 6))
            h = 5 + (1 if hint else 0)
            y, x = self._overlay(h, w, title)
            if hint:
                self.text(y + 1, x + 2, hint, "dim", w - 4)
            shown = ("•" * len(buf)) if secret else "".join(buf)
            iw = w - 6
            start = max(0, pos - iw + 1)
            self.text(y + 1 + (1 if hint else 0), x + 2, "› " + shown[start:start + iw], "primary", w - 4)
            self.text(y + h - 2, x + 2, "Enter = OK   Esc = cancel", "dim", w - 4)
            curses.curs_set(1)
            try:
                self.scr.move(y + 1 + (1 if hint else 0), x + 4 + pos - start)
            except curses.error:
                pass
            self.scr.refresh()
            ev = self.get_event(1000)
            if ev[0] != "key":
                continue
            k = ev[1]
            if k == ESC:
                curses.curs_set(0); return None
            if k in ENTER:
                curses.curs_set(0); return "".join(buf)
            if k in BACKSPACE and pos > 0:
                del buf[pos - 1]; pos -= 1
            elif k == curses.KEY_DC and pos < len(buf):
                del buf[pos]
            elif k == curses.KEY_LEFT:
                pos = max(0, pos - 1)
            elif k == curses.KEY_RIGHT:
                pos = min(len(buf), pos + 1)
            elif k in (curses.KEY_HOME, 1):
                pos = 0
            elif k in (curses.KEY_END, 5):
                pos = len(buf)
            elif k == 21:
                buf, pos = [], 0
            elif k >= 32 and k != 127:
                try:
                    ch = chr(k) if k < 256 else None
                    if k >= 128:   # UTF-8 multibyte: curses gives bytes; gather them
                        bs = bytearray([k])
                        self.scr.timeout(5)
                        for _ in range(3):
                            nk = self.scr.getch()
                            if nk == -1:
                                break
                            bs.append(nk)
                        ch = bs.decode("utf-8", "ignore")
                    if ch:
                        buf.insert(pos, ch); pos += 1
                except Exception:
                    pass

    def choose(self, title, options, multi=False, selected=None, danger_index=None):
        """options: list of str or (label, detail). Single → index or None. multi → list of indices or None (Space toggles)."""
        opts = [(o, "") if isinstance(o, str) else o for o in options]
        cur, top = 0, 0
        chosen = set(selected or [])
        while True:
            self.size()
            w = min(self.w - 2, max([width(l) + width(d) + 8 for l, d in opts] + [width(title) + 8, 34]))
            vis = min(len(opts), max(3, self.h - 8))
            h = vis + 4
            y, x = self._overlay(h, w, title)
            cur = max(0, min(cur, len(opts) - 1))
            top = min(max(top, cur - vis + 1), cur) if cur < top or cur >= top + vis else top
            for i in range(vis):
                j = top + i
                if j >= len(opts):
                    break
                lab, det = opts[j]
                mark = ("[x] " if j in chosen else "[ ] ") if multi else ""
                line = mark + lab
                attr = "sel" if j == cur else "text"
                self.text(y + 1 + i, x + 1, (" " + line).ljust(w - 2), attr, w - 2)
                if det:
                    self.text(y + 1 + i, x + w - 2 - width(det), det, "sel" if j == cur else "dim", width(det))
                self.region(y + 1 + i, x + 1, 1, w - 2, (lambda jj: (lambda: setattr(self, "_pick", jj)))(j))
            self.text(y + h - 2, x + 2, ("Space = tick · " if multi else "") + "Enter = OK · Esc = cancel", "dim", w - 4)
            self.scr.refresh()
            ev = self.get_event(1000)
            if ev[0] == "scroll":
                cur += ev[1] // 3
            elif ev[0] == "click":
                self._pick = None
                self.dispatch_click(ev[1], ev[2], ev[3])
                if self._pick is not None:
                    cur = self._pick
                    if multi:
                        chosen ^= {cur}
                    elif ev[3] or True:
                        return cur
            elif ev[0] == "key":
                k = ev[1]
                if k == ESC or k == ord("q"):
                    return None
                if k in (curses.KEY_DOWN, ord("j")):
                    cur += 1
                elif k in (curses.KEY_UP, ord("k")):
                    cur -= 1
                elif k == curses.KEY_NPAGE:
                    cur += vis
                elif k == curses.KEY_PPAGE:
                    cur -= vis
                elif multi and k == ord(" "):
                    chosen ^= {cur}
                elif k in ENTER:
                    return sorted(chosen) if multi else cur

    def form(self, title, fields):
        """fields: list of dicts {key,label,value,kind:'text'|'bool'|'choice',choices:[...]}. Returns {key:value} or None."""
        vals = {f["key"]: f.get("value", "") for f in fields}
        cur = 0
        while True:
            self.size()
            w = min(self.w - 2, 64)
            h = len(fields) + 5
            y, x = self._overlay(h, w, title)
            for i, f in enumerate(fields):
                v = vals[f["key"]]
                shown = ("[x]" if v else "[ ]") if f.get("kind") == "bool" else clip(str(v), w - width(f["label"]) - 10)
                line = " %-14s %s" % (f["label"], shown)
                self.text(y + 1 + i, x + 1, line.ljust(w - 2), "sel" if i == cur else "text", w - 2)
                self.region(y + 1 + i, x + 1, 1, w - 2, (lambda ii: (lambda: setattr(self, "_pick", ii)))(i))
            self.text(y + h - 2, x + 2, "Enter = edit/toggle · s = save · Esc = cancel", "dim", w - 4)
            self.scr.refresh()
            ev = self.get_event(1000)
            if ev[0] == "click":
                self._pick = None
                self.dispatch_click(ev[1], ev[2], ev[3])
                if self._pick is not None:
                    cur = self._pick
                continue
            if ev[0] != "key":
                continue
            k = ev[1]
            if k == ESC:
                return None
            if k in (curses.KEY_DOWN, ord("j")):
                cur = min(len(fields) - 1, cur + 1)
            elif k in (curses.KEY_UP, ord("k")):
                cur = max(0, cur - 1)
            elif k == ord("s"):
                return vals
            elif k in ENTER or k == ord(" "):
                f = fields[cur]
                if f.get("kind") == "bool":
                    vals[f["key"]] = not vals[f["key"]]
                elif f.get("kind") == "choice":
                    c = self.choose(f["label"], f["choices"])
                    if c is not None:
                        vals[f["key"]] = f["choices"][c]
                else:
                    r = self.prompt(f["label"], str(vals[f["key"]]))
                    if r is not None:
                        vals[f["key"]] = r

    def pager(self, title, lines):
        top = 0
        while True:
            self.size()
            w, h = self.w - 2, self.h - 2
            y, x = self._overlay(h, w, title)
            vis = h - 3
            top = max(0, min(top, max(0, len(lines) - vis)))
            for i in range(vis):
                if top + i < len(lines):
                    self.text(y + 1 + i, x + 2, lines[top + i], "text", w - 4)
            self.text(y + h - 2, x + 2, "↑↓ scroll · q close   %d/%d" % (min(len(lines), top + vis), len(lines)), "dim", w - 4)
            self.scr.refresh()
            ev = self.get_event(1000)
            if ev[0] == "scroll":
                top += ev[1]
            elif ev[0] == "key":
                k = ev[1]
                if k in (ESC, ord("q"), *ENTER):
                    return
                if k in (curses.KEY_DOWN, ord("j")):
                    top += 1
                elif k in (curses.KEY_UP, ord("k")):
                    top -= 1
                elif k in (curses.KEY_NPAGE, ord(" ")):
                    top += vis
                elif k == curses.KEY_PPAGE:
                    top -= vis
                elif k == ord("g"):
                    top = 0
                elif k == ord("G"):
                    top = len(lines)

    def suspend(self, fn):
        """Leave the GUI, run fn() on the plain terminal (editors, installers), then come back."""
        curses.def_prog_mode(); curses.endwin()
        try:
            return fn()
        finally:
            curses.reset_prog_mode(); self.scr.refresh(); curses.curs_set(0)


class App:
    tick_ms = 500
    def draw(self, ui): ...
    def key(self, ui, k): return True
    def click(self, ui, y, x, double): ...
    def scroll(self, ui, n): ...
    def tick(self, ui): ...


def run(app):
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")

    def main(scr):
        ui = UI(scr)
        ui.draw_cb = app.draw
        if hasattr(app, "start"):
            app.start(ui)
        while True:
            ui.redraw()
            ev = ui.get_event(app.tick_ms)
            if ev[0] == "key":
                if app.key(ui, ev[1]) is False:
                    return
            elif ev[0] == "click":
                if not ui.dispatch_click(ev[1], ev[2], ev[3]):
                    app.click(ui, ev[1], ev[2], ev[3])
                if getattr(app, "quit", False):
                    return
            elif ev[0] == "scroll":
                app.scroll(ui, ev[1])
            elif ev[0] == "tick":
                app.tick(ui)
    curses.wrapper(main)
