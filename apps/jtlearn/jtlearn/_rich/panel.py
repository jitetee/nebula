from . import _core as c


class Panel:
    def __init__(self, renderable="", box=None, title=None, subtitle=None, title_align="center", border_style="",
                 style="", padding=(0, 1), expand=True, width=None, **_):
        self.r, self.box, self.title, self.subtitle = renderable, box or c.ROUNDED, title, subtitle
        self.title_align, self.border, self.style = title_align, border_style, style
        if isinstance(padding, int): padding = (padding, padding)
        if len(padding) == 2: padding = (padding[0], padding[1], padding[0], padding[1])
        self.pad, self.expand, self.fixed = padding, expand, width

    @classmethod
    def fit(cls, renderable, **kw):
        kw["expand"] = False
        return cls(renderable, **kw)

    def _render_lines(self, width):
        b = self.box
        total = self.fixed or width
        total = min(total, width)
        pt, pr, pb, pl = self.pad
        inner = max(4, total - 2 - pl - pr)
        body = c.to_lines(self.r, inner, self.style)
        if not self.expand and not self.fixed:
            w = max([c.vlen(l) for l in body] + [0])
            tw = c.vlen(c.markup_to_ansi(str(self.title))) + 2 if self.title else 0
            inner = max(1, min(inner, max(w, tw)))
            body = c.to_lines(self.r, inner, self.style)
        bc = c.style_to_ansi(self.border)
        end = c.RESET if bc else ""
        col = lambda s: f"{bc}{s}{end}"
        span = inner + pl + pr

        def edge(left, fill, right, label, align):
            if label:
                t = " " + c.markup_to_ansi(str(label)) + " "
                tl = c.vlen(t)
                room = span - tl
                if room < 0:
                    t, room = c.strip_ansi(t)[:span], 0
                    tl = len(t)
                if align == "left": l = 1 if room >= 1 else 0
                elif align == "right": l = max(0, room - 1)
                else: l = room // 2
                r = max(0, room - l)
                return col(left + fill * l) + t + col(fill * r + right)
            return col(left + fill * span + right)

        out = [edge(b.tl, b.t, b.tr, self.title, self.title_align)]
        blank = col(b.v) + " " * span + col(b.v)
        out += [blank] * pt
        for l in body:
            out.append(col(b.v) + " " * pl + l + " " * (inner - c.vlen(l)) + " " * pr + col(b.v))
        out += [blank] * pb
        out.append(edge(b.bl, b.b, b.br, self.subtitle, "center"))
        return out
