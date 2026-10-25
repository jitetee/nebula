from ._core import Span, parse_markup, spans_to_ansi, wrap_spans


class Text:
    def __init__(self, text="", style="", justify=None, **_):
        self._parts = [Span(str(text), str(style))] if text else []
        self.style, self.justify = str(style), justify

    @classmethod
    def from_markup(cls, s, **kw):
        t = cls(**kw); t._parts = parse_markup(s); return t

    @classmethod
    def assemble(cls, *parts, **kw):
        t = cls(**kw)
        for p in parts:
            if isinstance(p, tuple): t.append(p[0], p[1])
            else: t.append(str(p))
        return t

    def append(self, text, style=""):
        self._parts.append(Span(str(text), str(style))); return self

    def stylize(self, style, *_a):
        for p in self._parts: p.style = (p.style + " " + str(style)).strip()

    @property
    def plain(self):
        return "".join(p.text for p in self._parts)

    def _spans(self):
        return [Span(p.text, (self.style + " " + p.style).strip() if p.style != self.style else p.style) for p in self._parts]

    def __str__(self):
        return self.plain
