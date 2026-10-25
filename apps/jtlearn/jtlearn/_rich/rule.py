from ._core import markup_to_ansi, term_width, vlen


class Rule:
    def __init__(self, title="", characters="─", style="", align="center", **_):
        self.title, self.ch, self.style, self.align = title, characters, style, align

    def _render_lines(self, width):
        from ._core import style_to_ansi, RESET
        a = style_to_ansi(self.style or "dim") or ""
        end = RESET if a else ""
        if not self.title:
            return [f"{a}{self.ch * width}{end}"]
        t = " " + markup_to_ansi(str(self.title)) + " "
        room = max(0, width - vlen(t))
        if self.align == "left":
            l, r = 2, room - 2
        elif self.align == "right":
            l, r = room - 2, 2
        else:
            l = room // 2; r = room - l
        l, r = max(0, l), max(0, r)
        return [f"{a}{self.ch * l}{end}{t}{a}{self.ch * r}{end}"]
