from . import _core as c


class Column:
    def __init__(self, header="", style="", justify="left", width=None, min_width=None, max_width=None,
                 no_wrap=False, ratio=None, header_style=None, overflow=None, **_):
        self.header, self.style, self.justify, self.width = header, style or "", justify, width
        self.min_width, self.max_width, self.no_wrap, self.ratio = min_width, max_width, no_wrap, ratio
        self.header_style = header_style


class Table:
    def __init__(self, *headers, title=None, caption=None, box=c.ROUNDED, show_header=True, header_style="bold",
                 border_style="", show_lines=False, padding=(0, 1), expand=False, title_style="bold",
                 show_edge=True, row_styles=None, width=None, title_justify="center", pad_edge=True,
                 collapse_padding=False, min_width=None, style="", **_):
        self.cols = [Column(h) for h in headers]
        self.rows, self.title, self.caption, self.box = [], title, caption, box
        self.show_header, self.header_style, self.border = show_header, header_style, border_style
        self.show_lines, self.expand, self.title_style, self.show_edge = show_lines, expand, title_style, show_edge
        self.row_styles, self.fixed, self.title_justify, self.style = row_styles or [], width, title_justify, style
        self.padx = padding[1] if isinstance(padding, (tuple, list)) and len(padding) >= 2 else (padding if isinstance(padding, int) else 1)
        self.sections = set()

    def add_column(self, header="", **kw):
        self.cols.append(Column(header, **kw))

    def add_row(self, *cells, style=None, end_section=False, **_):
        row = list(cells) + [""] * (len(self.cols) - len(cells))
        while len(self.cols) < len(row):
            self.cols.append(Column(""))
        self.rows.append((row, style))
        if end_section:
            self.sections.add(len(self.rows) - 1)

    def add_section(self):
        if self.rows: self.sections.add(len(self.rows) - 1)

    # --- layout
    def _spans(self, cell, base=""):
        if hasattr(cell, "_spans"):
            return cell._spans()
        return c.parse_markup("" if cell is None else str(cell), base)

    def _render_lines(self, avail):
        b = self.box
        n = len(self.cols)
        if n == 0:
            return []
        edge = 2 if (b is not None and self.show_edge) else 0
        sep = 1 if b is not None else 0
        pad = self.padx * 2
        limit = min(avail, self.fixed or avail)
        room = limit - edge - sep * (n - 1) - pad * n
        heads = [self._spans(col.header, "") for col in self.cols]
        cellspans = [[self._spans(r[i]) for i in range(n)] for r, _ in self.rows]
        nat = []
        for i, col in enumerate(self.cols):
            w = max([c.spans_width(s) for l in c.wrap_spans(heads[i], 10 ** 6) for s in [l]] + [0]) if self.show_header else 0
            for row in cellspans:
                for l in c.wrap_spans(row[i], 10 ** 6):
                    w = max(w, c.spans_width(l))
            nat.append(max(w, col.min_width or 0))
        widths = [col.width if col.width else nat[i] for i, col in enumerate(self.cols)]
        for i, col in enumerate(self.cols):
            if col.max_width: widths[i] = min(widths[i], col.max_width)
        total = sum(widths)
        ratios = [col.ratio for col in self.cols]
        if (self.expand or self.fixed) and total < room:
            extra = room - total
            flex = [i for i in range(n) if ratios[i]] or [i for i in range(n) if not self.cols[i].width]
            if flex:
                rs = sum((ratios[i] or 1) for i in flex)
                for i in flex:
                    widths[i] += extra * (ratios[i] or 1) // rs
                widths[flex[-1]] += room - sum(widths)
        elif total > room:
            over = total - room
            flex = [i for i in range(n) if not self.cols[i].width and not self.cols[i].no_wrap] or list(range(n))
            while over > 0 and flex:
                i = max(flex, key=lambda k: widths[k])
                floor = max(4, self.cols[i].min_width or 0)
                if widths[i] <= floor:
                    flex.remove(i); continue
                widths[i] -= 1; over -= 1
        widths = [max(1, w) for w in widths]

        bc = c.style_to_ansi(self.border); end = c.RESET if bc else ""
        col_ = lambda s: f"{bc}{s}{end}" if bc and s.strip() else s
        px = " " * self.padx

        def cell_lines(spans, w, col, base_style):
            sp = [c.Span(s.text, (base_style + " " + s.style).strip()) for s in spans] if base_style else spans
            return [c.spans_to_ansi(c.pad_line(l, w, col.justify)) for l in c.wrap_spans(sp, w, col.no_wrap)] 

        def line_for(cells_lines):
            h = max(len(x) for x in cells_lines)
            out = []
            for k in range(h):
                parts = []
                for i, cl in enumerate(cells_lines):
                    parts.append(px + (cl[k] if k < len(cl) else " " * widths[i]) + px)
                mid = col_(b.vm) if b is not None else ""
                row = mid.join(parts)
                if b is not None and self.show_edge:
                    row = col_(b.v) + row + col_(b.v)
                out.append(row)
            return out

        def rule_line(left, fill, mid, right):
            segs = [fill * (widths[i] + pad) for i in range(n)]
            s = mid.join(segs)
            if self.show_edge: s = left + s + right
            return col_(s)

        lines = []
        if b is not None and self.show_edge and b.t.strip():
            lines.append(rule_line(b.tl, b.t, b.tm, b.tr))
        if self.show_header:
            hs = [self.header_style or ""]
            hl = [cell_lines(heads[i], widths[i], self.cols[i], self.cols[i].header_style or self.header_style or "") for i in range(n)]
            lines += line_for(hl)
            if b is not None and b.h.strip():
                lines.append(rule_line(b.ml, b.h, b.mm, b.mr))
        for ri, (row, rstyle) in enumerate(self.rows):
            st = rstyle or ""
            if self.row_styles:
                st = (st + " " + self.row_styles[ri % len(self.row_styles)]).strip()
            cl = [cell_lines(cellspans[ri][i], widths[i], self.cols[i], (self.cols[i].style + " " + st).strip()) for i in range(n)]
            lines += line_for(cl)
            if b is not None and b.h.strip() and ((self.show_lines and ri < len(self.rows) - 1) or ri in self.sections) and ri < len(self.rows) - 1:
                lines.append(rule_line(b.ml, b.h, b.mm, b.mr))
        if b is not None and self.show_edge and b.b.strip():
            lines.append(rule_line(b.bl, b.b, b.bm, b.br))
        width = max([c.vlen(l) for l in lines] + [0])
        head = []
        if self.title:
            t = c.markup_to_ansi(str(self.title), self.title_style)
            pad_l = max(0, (width - c.vlen(t)) // 2) if self.title_justify == "center" else 0
            head.append(" " * pad_l + t)
        tail = []
        if self.caption:
            t = c.markup_to_ansi(str(self.caption), "dim")
            tail.append(" " * max(0, (width - c.vlen(t)) // 2) + t)
        return head + lines + tail
