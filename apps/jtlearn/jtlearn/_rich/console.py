import getpass
import sys
import threading
import time

from . import _core as c


class Console:
    def __init__(self, width=None, force_terminal=None, file=None, stderr=False, **_):
        self._width = width
        self._file = file or (sys.stderr if stderr else None)

    @property
    def file(self):
        return self._file or sys.stdout

    @property
    def width(self):
        return self._width or c.term_width()

    @property
    def size(self):
        import shutil
        s = shutil.get_terminal_size((80, 24))
        return s.columns, s.lines

    @property
    def is_terminal(self):
        return self.file.isatty()

    def _out(self, s):
        f = self.file
        f.write(s); f.flush()

    def print(self, *objects, sep=" ", end="\n", style="", justify=None, markup=True, highlight=None,
              soft_wrap=False, overflow=None, no_wrap=False, crop=None, **_):
        w = self.width
        if not objects:
            self._out(end); return
        chunks = []
        plain_run = []
        for o in objects:
            if isinstance(o, str) or not (hasattr(o, "_render_lines") or hasattr(o, "_spans")):
                plain_run.append(str(o))
            else:
                if plain_run:
                    chunks.append(self._text(sep.join(plain_run), w, style, justify, markup, no_wrap)); plain_run = []
                chunks.append(self._obj(o, w, style, justify))
        if plain_run:
            chunks.append(self._text(sep.join(plain_run), w, style, justify, markup, no_wrap))
        out = "\n".join(chunks)
        self._out(out + end)

    def _text(self, s, w, style, justify, markup, no_wrap):
        spans = c.parse_markup(s, style) if markup else [c.Span(s, style)]
        lines = c.wrap_spans(spans, w, no_wrap=no_wrap or self.width >= 10 ** 5)
        if justify in ("center", "right"):
            lines = [c.pad_line(l, w, justify) for l in lines]
        return "\n".join(c.spans_to_ansi(l) for l in lines)

    def _obj(self, o, w, style, justify):
        lines = c.to_lines(o, w, style)
        if justify in ("center", "right"):
            lines = [(" " * ((w - c.vlen(l)) // (2 if justify == "center" else 1))) + l for l in lines]
        return "\n".join(lines)

    def rule(self, title="", **kw):
        from .rule import Rule
        self.print(Rule(title, **kw))

    def clear(self, home=True):
        if self.is_terminal:
            self._out("\033[H\033[2J\033[3J")

    def line(self, count=1):
        self._out("\n" * count)

    def input(self, prompt="", password=False, markup=True, **_):
        text = c.markup_to_ansi(str(prompt)) if markup else str(prompt)
        if password:
            return getpass.getpass(c.strip_ansi(text))
        self._out(text)
        try:
            return input()
        except EOFError:
            return ""

    def status(self, status="", spinner="dots", **_):
        return Status(self, status)

    def print_json(self, json=None, data=None, indent=2, **_):
        import json as _j
        self.print(_j.dumps(data if json is None else _j.loads(json), indent=indent))

    def show_cursor(self, show=True):
        self._out("\033[?25h" if show else "\033[?25l")

    def log(self, *a, **k):
        self.print(*a, **k)


class Status:
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, console, text):
        self.console, self.text, self._stop, self._t = console, text, threading.Event(), None

    def update(self, status=None, **_):
        if status is not None: self.text = status

    def __enter__(self):
        if self.console.is_terminal:
            def spin():
                i = 0
                while not self._stop.is_set():
                    msg = c.markup_to_ansi(str(self.text))
                    self.console._out(f"\r\033[K{c.style_to_ansi('cyan')}{self.FRAMES[i % 10]}{c.RESET} {msg}")
                    i += 1; time.sleep(0.08)
            self._t = threading.Thread(target=spin, daemon=True); self._t.start()
        else:
            self.console.print(self.text)
        return self

    def __exit__(self, *a):
        self._stop.set()
        if self._t:
            self._t.join(timeout=0.3)
            self.console._out("\r\033[K")
        return False
