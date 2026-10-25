from ._core import style_to_ansi


class Style:
    def __init__(self, color=None, bgcolor=None, bold=False, dim=False, italic=False, underline=False, **_):
        parts = []
        if bold: parts.append("bold")
        if dim: parts.append("dim")
        if italic: parts.append("italic")
        if underline: parts.append("underline")
        if color: parts.append(str(color))
        if bgcolor: parts.append("on " + str(bgcolor))
        self.spec = " ".join(parts)

    @classmethod
    def parse(cls, spec):
        s = cls(); s.spec = spec; return s

    def __str__(self):
        return self.spec
