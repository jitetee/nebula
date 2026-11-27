#!/usr/bin/env python3
"""Build the Nebula master manual (PDF) from the real source, so it can never drift from the code.

  python3 tools/make-manual.py [--out docs/Nebula-Master-Manual.pdf]

Reads: the help registry (every command + plugin), `ant -h`, `jtlearn -h`, the Neovim keymaps/commands, docs/*.md,
nebula_core, the palettes, env vars used in the code, and docs/screenshots. Needs: reportlab, pillow.
"""
import argparse, datetime, glob, inspect, io, os, re, subprocess, sys, textwrap

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("NEBULA_HOME", HOME)
sys.path.insert(0, os.path.join(HOME, "lib"))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from nebula_core import help as nhelp, theme as nth

DJ = "/usr/share/fonts/truetype/dejavu/"
for name, f in [("Sans", "DejaVuSans.ttf"), ("Sans-B", "DejaVuSans-Bold.ttf"), ("Sans-I", "DejaVuSans-Oblique.ttf"),
                ("Sans-BI", "DejaVuSans-BoldOblique.ttf"), ("Mono", "DejaVuSansMono.ttf"), ("Mono-B", "DejaVuSansMono-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, DJ + f))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-B", italic="Sans-I", boldItalic="Sans-BI")
pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-B", italic="Mono", boldItalic="Mono-B")
pdfmetrics.registerFont(TTFont("NebulaMono", os.path.join(HOME, "assets", "fonts", "nebula.ttf")))

GREEN, DARK, INK, GREY, LIGHT = colors.HexColor("#00875a"), colors.HexColor("#0b120e"), colors.HexColor("#1b2a22"), colors.HexColor("#5c6b63"), colors.HexColor("#eef5f0")
W = A4[0] - 100

S = {
    "body": ParagraphStyle("body", fontName="Sans", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=4),
    "small": ParagraphStyle("small", fontName="Sans", fontSize=8, leading=11, textColor=GREY),
    "H1": ParagraphStyle("H1", fontName="Sans-B", fontSize=26, leading=30, textColor=GREEN, spaceBefore=0, spaceAfter=14),
    "H2": ParagraphStyle("H2", fontName="Sans-B", fontSize=16, leading=20, textColor=DARK, spaceBefore=16, spaceAfter=6),
    "H3": ParagraphStyle("H3", fontName="Mono-B", fontSize=11.5, leading=15, textColor=GREEN, spaceBefore=10, spaceAfter=1),
    "H4": ParagraphStyle("H4", fontName="Sans-B", fontSize=10.5, leading=14, textColor=DARK, spaceBefore=8, spaceAfter=3),
    "sum": ParagraphStyle("sum", fontName="Sans-B", fontSize=9.5, leading=13, textColor=INK, spaceAfter=3),
    "mono": ParagraphStyle("mono", fontName="Mono", fontSize=8, leading=11, textColor=INK, leftIndent=8),
    "ex": ParagraphStyle("ex", fontName="Mono", fontSize=8.5, leading=12, textColor=GREEN, leftIndent=8, spaceBefore=2, spaceAfter=2),
    "src": ParagraphStyle("src", fontName="Sans-I", fontSize=7.5, leading=10, textColor=GREY, spaceAfter=6),
    "li": ParagraphStyle("li", parent=None, fontName="Sans", fontSize=9.5, leading=13.5, textColor=INK, leftIndent=14, bulletIndent=3, spaceAfter=2),
    "cell": ParagraphStyle("cell", fontName="Sans", fontSize=8.5, leading=11.5, textColor=INK),
    "cellm": ParagraphStyle("cellm", fontName="Mono", fontSize=8, leading=11, textColor=INK),
    "cap": ParagraphStyle("cap", fontName="Sans-I", fontSize=8, leading=10, textColor=GREY, alignment=TA_CENTER, spaceAfter=8),
}


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(t):
    t = esc(t)
    t = re.sub(r"`([^`]+)`", r'<font name="Mono" color="#00724c">\1</font>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    return t


def P(t, st="body"):
    return Paragraph(inline(t), S[st])


def code(text, size=7.6):
    lines = []
    for ln in text.rstrip("\n").split("\n"):
        ln = ln.replace("\t", "    ")
        if len(ln) <= 104:
            lines.append(ln); continue
        ind = len(ln) - len(ln.lstrip())
        first = True
        for chunk in textwrap.wrap(ln, 104 - (0 if first else ind + 2), subsequent_indent=" " * (ind + 2), break_long_words=True):
            lines.append(chunk)
    pre = Preformatted("\n".join(lines), ParagraphStyle("pre", fontName="Mono", fontSize=size, leading=size + 2.6, textColor=INK, backColor=LIGHT,
                                                        borderPadding=(4, 5, 4, 5), leftIndent=6, rightIndent=6, spaceBefore=4, spaceAfter=8))
    return pre


def table(rows, widths, head=True, mono0=False):
    data = [[Paragraph(inline(str(c)), S["cellm"] if (mono0 and i == 0) else S["cell"]) for i, c in enumerate(r)] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfdcd3")),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if head:
        st += [("BACKGROUND", (0, 0), (-1, 0), LIGHT)]
    t.setStyle(TableStyle(st))
    return t


def md(text):
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1; buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j]); j += 1
            out.append(code("\n".join(buf))); i = j + 1; continue
        m = re.match(r"^(#{1,4})\s+(.*)", ln)
        if m:
            lvl = len(m.group(1))
            out.append(Paragraph(inline(m.group(2)), S["H4" if lvl >= 3 else "H4"] if lvl >= 3 else ParagraphStyle("mdh", parent=S["H2"], fontSize=13, leading=17, spaceBefore=12)))
            i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-+:?$", c) for c in cells):
                    rows.append(cells)
                i += 1
            n = max(len(r) for r in rows)
            rows = [r + [""] * (n - len(r)) for r in rows]
            ws = [W * 0.28] + [(W * 0.72) / (n - 1)] * (n - 1) if n > 1 else [W]
            out.append(table(rows, ws, mono0=False)); out.append(Spacer(1, 6)); continue
        m = re.match(r"^\s*([-*]|\d+\.)\s+(.*)", ln)
        if m:
            bullet = "•" if m.group(1) in "-*" else m.group(1)
            out.append(Paragraph(inline(m.group(2)), S["li"], bulletText=bullet)); i += 1; continue
        if ln.strip() == "":
            i += 1; continue
        para = [ln.strip()]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|```|\||\s*([-*]|\d+\.)\s)", lines[i]):
            para.append(lines[i].strip()); i += 1
        out.append(P(" ".join(para)))
    return out


class Doc(BaseDocTemplate):
    def __init__(self, fn, **kw):
        super().__init__(fn, pagesize=A4, leftMargin=50, rightMargin=50, topMargin=56, bottomMargin=52, title="Nebula Master Manual",
                         author="J.I.T.E.T.E.E.", **kw)
        fr = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="cover", frames=[fr], onPage=self.cover), PageTemplate(id="main", frames=[fr], onPageEnd=self.chrome)])
        self._n = 0

    def beforeDocument(self):
        self._n = 0          # heading keys must be identical on every pass or the TOC never settles
        self.section = ""

    def cover(self, c, d):
        c.saveState()
        c.setFillColor(DARK); c.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#00ff87")); c.setFont("Mono-B", 62); c.drawString(50, A4[1] - 250, "NEBULA")
        c.setFillColor(colors.HexColor("#87ff87")); c.setFont("Sans", 22); c.drawString(52, A4[1] - 290, "Master Manual")
        c.setFillColor(colors.HexColor("#d7e6dc")); c.setFont("Sans", 11)
        c.drawString(52, A4[1] - 325, "Every command, app, plugin and setting of your terminal operating system.")
        c.setFillColor(colors.HexColor("#00ff87")); c.setFont("NebulaMono", 34)
        c.drawString(52, A4[1] - 400, "\ue400  \ue401  \ue402  \ue403  \ue404  \ue405")
        c.setFillColor(colors.HexColor("#7f8f85")); c.setFont("Sans", 10)
        c.drawString(52, 80, "Version %s  ·  generated %s  ·  tools/make-manual.py" % (open(os.path.join(HOME, "VERSION")).read().strip(), datetime.date.today().isoformat()))
        c.drawString(52, 64, "J.I.T.E.T.E.E.  ·  github.com/jitetee/nebula")
        c.restoreState()

    def chrome(self, c, d):
        c.saveState()
        c.setStrokeColor(colors.HexColor("#cfdcd3")); c.setLineWidth(0.5)
        c.line(50, A4[1] - 40, A4[0] - 50, A4[1] - 40)
        c.setFont("Sans", 8); c.setFillColor(GREY)
        c.drawString(50, A4[1] - 34, "Nebula Master Manual")
        c.drawRightString(A4[0] - 50, A4[1] - 34, getattr(self, "section", ""))
        c.drawCentredString(A4[0] / 2, 30, "%d" % d.page)
        c.restoreState()

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("H1", "H2", "H3"):
            lvl = {"H1": 0, "H2": 1, "H3": 2}[f.style.name]
            text = f.getPlainText()
            if lvl == 0:
                self.section = text
            self._n += 1
            key = "h%d" % self._n
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, lvl, 0)
            self.notify("TOCEntry", (lvl, text, self.page, key))


def sh(cmd, cwd=None, env=None):
    e = dict(os.environ, NO_COLOR="1", TERM="dumb", NEBULA_HOME=HOME, NEBULA_NO_AUTH="1", **(env or {}))
    try:
        return subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, timeout=60).stdout
    except Exception as ex:
        return "(could not run: %s)" % ex


def source_of(cmdname):
    for f in sorted(glob.glob(os.path.join(HOME, "lib", "*.sh")) + [os.path.join(HOME, "bin", "nebula")] + glob.glob(os.path.join(HOME, "plugins", "*", "plugin.sh"))):
        try:
            if re.search(r"^cmd::%s\(\)" % re.escape(cmdname), open(f, encoding="utf-8").read(), re.M):
                return os.path.relpath(f, HOME)
        except OSError:
            pass
    return None


def detail_flow(lines):
    out, buf = [], []
    def flush():
        nonlocal buf
        if not buf:
            return
        rows = [(m.group(1), m.group(2)) for m in (re.match(r"^(\S.*?\S|\S)\s{2,}(\S.*)$", b) for b in buf)]
        t = Table([[Paragraph(esc(a), S["cellm"]), Paragraph(inline(b), S["cell"])] for a, b in rows], colWidths=[W * 0.34, W * 0.66])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
        out.append(t); buf = []
    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            flush(); continue
        if s.strip().startswith("Example:"):
            flush(); out.append(Paragraph("▶ " + esc(s.strip()[8:].strip()), S["ex"])); continue
        if re.match(r"^\S.*?\S\s{2,}\S", s) and not s.startswith(" "):
            buf.append(s); continue
        flush(); out.append(Paragraph(inline(s.strip()), S["body"]))
    flush()
    return out


# ── facts read straight from the code ──
_SRC_CACHE = {}
_BINS = ("termux-api", "curl", "mpv", "mpg123", "sox", "ffmpeg", "jq", "fzf", "tgpt", "git", "python3", "node", "nvim", "rg", "espeak", "qrencode",
         "zip", "unzip", "tar", "openssl", "gpg", "ssh", "rsync", "wget", "lsd", "bat", "fd", "pkg", "ant", "jtlearn")


def _read(path):
    if path not in _SRC_CACHE:
        try:
            _SRC_CACHE[path] = open(path, encoding="utf-8").read().split("\n")
        except (OSError, UnicodeDecodeError):
            _SRC_CACHE[path] = []
    return _SRC_CACHE[path]


def fn_info(name):
    """(relpath, line, body_lines, comment_above) of cmd::<name>() or None."""
    cands = sorted(glob.glob(os.path.join(HOME, "lib", "*.sh"))) + [os.path.join(HOME, "bin", "nebula")] + sorted(glob.glob(os.path.join(HOME, "plugins", "*", "plugin.sh")))
    for f in cands:
        L = _read(f)
        for i, ln in enumerate(L):
            if re.match(r"^cmd::%s\(\)" % re.escape(name), ln):
                j = i
                if not ln.rstrip().endswith("}") or ln.count("{") != ln.count("}"):
                    while j + 1 < len(L) and not L[j].startswith("}"):
                        j += 1
                body = L[i:j + 1]
                k, cm = i - 1, []
                while k >= 0 and L[k].startswith("#"):
                    t = re.sub(r"[─━═\-]{2,}", "", L[k].lstrip("# ")).strip()
                    if len(t) > 12 and t.lower().rstrip(".") != name:
                        cm.insert(0, t)
                    k -= 1
                return os.path.relpath(f, HOME), i + 1, body, cm
    return None


def _gate_maps():
    L = "\n".join(_read(os.path.join(HOME, "lib", "device.sh")))
    cap = {}
    blk = L.split("device::cmd_cap()", 1)[-1].split("DEVICE_GATED", 1)[0]
    for m in re.finditer(r"^\s+([A-Za-z0-9_|-]+)\)\s+echo (\w+)", blk, re.M):
        for c in m.group(1).split("|"):
            cap[c] = m.group(2)
    helpmap = {}
    for m in re.finditer(r'^\s+(\w+)\)\s+echo "([^|"]*)\|([^|"]*)\|([^"]*)"', L.split("device::cap_help()", 1)[-1], re.M):
        helpmap[m.group(1)] = (m.group(2), m.group(3), m.group(4))
    return cap, helpmap


GATE, GATEHELP = _gate_maps()


def facts_for(name, e):
    fi = fn_info(name)
    rows = []
    if fi:
        rel, line, body, cm = fi
        text = "\n".join(body)
        subs = []
        m = re.search(r'case "\$\{1:-[^}]*\}"? in|case "\$1" in|case \$\{?1\}? in|case "\$\{1[^}]*\}" in', text)
        if m:
            for mm in re.finditer(r"^\s{2,8}([A-Za-z0-9_?.-]+(?:\|[A-Za-z0-9_?.-]+)*)\)", text[m.end():], re.M):
                lab = mm.group(1)
                if lab not in ("*",) and lab not in subs:
                    subs.append(lab)
        if subs:
            rows.append(["Subcommands", ", ".join("`%s`" % x for x in subs[:24])])
        uses = sorted({b for b in re.findall(r"\b(termux-[a-z-]+|[a-z0-9]+)\b", text) if b in _BINS or b.startswith("termux-")})
        if uses:
            rows.append(["Uses", ", ".join("`%s`" % x for x in uses[:14])])
        rel_cmds = sorted({x for x in re.findall(r"\bcmd::([a-z0-9_-]+)", text) if x != name and not x.startswith("_")})
        if rel_cmds:
            rows.append(["Calls", ", ".join("`%s`" % x for x in rel_cmds[:12])])
        rows.append(["Source", "`%s` line %d (%d lines)" % (rel, line, len(body))])
        if cm:
            rows.insert(0, ["Note from the code", " ".join(cm)[:300]])
    cap = GATE.get(name)
    if cap and cap in GATEHELP:
        why, pkg, fix = GATEHELP[cap]
        rows.insert(0, ["Needs", "%s%s" % (why, ("  (fix: `%s`)" % fix) if fix and not fix.startswith("@") else "")])
    return rows


def codebase_map():
    rows = []
    pats = [("bin", "bin/nebula"), ("lib", "lib/*"), ("zsh", "zsh/**/*.zsh"), ("apps/ant", "apps/ant/ant/*.py"), ("apps/jtlearn", "apps/jtlearn/jtlearn/*.py"),
            ("apps/jtlearn engines", "apps/jtlearn/jtlearn/engines/*.py"), ("apps/jtlearn main", "apps/jtlearn/jtlearn/main/*.py"),
            ("neovim", "assets/nvim/**/*.lua"), ("nebula_core", "lib/nebula_core/*.py"), ("tools", "tools/*"), ("install", "install/*")]
    for group, pat in pats:
        files = [f for f in sorted(glob.glob(os.path.join(HOME, pat), recursive=True)) if os.path.isfile(f)]
        lines = []
        for f in files:
            L = _read(f)
            if not L:
                continue
            head = ""
            for ln in L[:6]:
                t = ln.strip()
                if t.startswith(("#", "--", '"""')) and not t.startswith("#!") and len(t.strip("#-\" ")) > 6:
                    head = t.strip("#-\" ").strip(); break
            lines.append((os.path.relpath(f, HOME), len(L), head))
        if lines:
            rows.append((group, lines))
    return rows


def hr_pair(title, level="H2"):
    return Paragraph(esc(title), S[level])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(HOME, "docs", "Nebula-Master-Manual.pdf")); a = ap.parse_args()
    version = open(os.path.join(HOME, "VERSION")).read().strip()
    entries = nhelp.load()
    by = {}
    order = []
    for e in entries.values():
        if e["cat"] not in by:
            by[e["cat"]] = []; order.append(e["cat"])
        by[e["cat"]].append(e)
    st = [NextPageTemplate("main"), PageBreak()]

    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("t0", fontName="Sans-B", fontSize=11, leading=17, leftIndent=0, spaceBefore=6, textColor=DARK),
                       ParagraphStyle("t1", fontName="Sans", fontSize=9.5, leading=13, leftIndent=14, textColor=INK),
                       ParagraphStyle("t2", fontName="Mono", fontSize=8, leading=11, leftIndent=30, textColor=GREY)]
    st += [Paragraph("Contents", S["H1"].clone("ctitle")), toc, PageBreak()]

    # ── 1 Start ──
    st += [Paragraph("Start here", S["H1"]),
           P("Nebula is a terminal operating system for Termux: a shell layer, apps (`ant`, `jtlearn`), a Neovim setup, a font with its own icons, and a plugin system. "
             "This manual is generated from the code, so every command in the registry is here, with its usage, details and examples, and the apps and plugins around it."),
           Paragraph("The five commands to know", S["H2"])]
    st += [table([["`help`", "list every command; `help <name>` explains one; `help search <word>` finds one"],
                  ["`<anything> --help`", "always shows that command's help (core commands, apps and plugins alike)"],
                  ["`nebula check`", "verifies every command, app and plugin has help (also runs in CI)"],
                  ["`nebula doctor`", "health of the whole setup: editor, font, AI, plugins, consistency"],
                  ["`nv setup`", "make plain `nvim` the Nebula editor; `nv doctor` fixes Copilot problems"]], [W * 0.3, W * 0.7], head=False, mono0=True)]
    st += [Paragraph("Install and update", S["H2"]), code("# install (Termux)\n# see docs/LAUNCH.md and docs/PACKAGING.md for the full flow\nnebula update          # pull the latest release\nnv setup               # once: link Nebula's Neovim setup, fetch plugins\nnebula palette ocean   # try another colour scheme everywhere\nnebula ai status       # which AI answers everywhere"),
           Paragraph("How the pieces fit", S["H2"]),
           P("**One registry.** `assets/help.txt` plus each plugin's `help.txt` is the single list of commands. The shell, tab-completion, `ant`, `jtlearn` and Neovim all read it."),
           P("**One AI choice.** `nebula ai backend auto|ant|tgpt` decides which AI answers `ask`, `chat`, `explain`, `fix`, jtlearn's tutor, plugins and Neovim's `Space a` commands."),
           P("**One palette.** `nebula palette <name>` colours the shell, `ant`, `jtlearn` and Neovim. `theme` styles only your prompt."),
           P("**One font.** Nebula Mono holds the Nebula icons (U+E400 to U+E405) and the UI symbols; `NEBULA_ICONS=nerd|plain` is the fallback."),
           PageBreak()]

    # ── 2 Commands ──
    st += [Paragraph("Part 1: Every command", S["H1"]),
           P("%d commands in %d categories. Each entry shows usage, what it does, its details and examples, and the file that implements it. "
             "Typing `<command> --help` in Nebula shows the same text." % (len(entries), len(order)))]
    for cat in order:
        st += [Paragraph(esc(cat), S["H2"])]
        for e in sorted(by[cat], key=lambda x: x["name"]):
            blk = [Paragraph(esc((e["name"] + " " + e["args"]).strip()), S["H3"]), Paragraph(inline(e["summary"]), S["sum"])]
            body = detail_flow(e["detail"])
            fr = facts_for(e["name"], e)
            tail = [Spacer(1, 3)]
            if fr:
                ft = Table([[Paragraph("<b>%s</b>" % esc(a), S["cell"]), Paragraph(inline(b), S["cell"])] for a, b in fr], colWidths=[W * 0.2, W * 0.8])
                ft.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LINEBELOW", (0, 0), (-1, -2), 0.2, colors.white)]))
                tail = [Spacer(1, 3), ft, Spacer(1, 6)]
            st += [KeepTogether(blk + body[:2])] + body[2:] + tail
    st.append(PageBreak())

    # ── 3 Apps ──
    st += [Paragraph("Part 2: Apps", S["H1"])]
    st += [Paragraph("ant: the terminal coding agent", S["H2"]),
           P("Your own coding agent. Pick a provider once (`/setup`), then ask it to read, edit and run things in your project. It asks before writing files or running commands. "
             "The same provider, key, memory and sessions power `nebula ask`, jtlearn's tutor and the Neovim AI commands."),
           code(re.sub(r"\x1b\[[0-9;]*m", "", sh([sys.executable, "-m", "ant", "-h"], cwd=os.path.join(HOME, "apps", "ant"), env={"PYTHONPATH": os.path.join(HOME, "apps", "ant") + ":" + os.path.join(HOME, "lib")})))]
    tools = re.findall(r'\{"name": "(\w+)", "description": "([^"]+)"', open(os.path.join(HOME, "apps/ant/ant/tools.py"), encoding="utf-8").read())
    if tools:
        st += [Paragraph("Tools the agent can use", S["H4"]), table([["Tool", "What it does"]] + [["`%s`" % n, d] for n, d in tools], [W * 0.28, W * 0.72])]
    prov = re.findall(r'^\s{4}"(\w+)":\s*\{', open(os.path.join(HOME, "apps/ant/ant/providers.py"), encoding="utf-8").read(), re.M)
    if prov:
        st += [Paragraph("Providers", S["H4"]), P("Built in: " + ", ".join("`%s`" % p for p in prov) + ". Any OpenAI-compatible server works through `generic` with a base URL.")]
    st += [Paragraph("Programmatic use", S["H4"]), code(inspect.cleandoc(open(os.path.join(HOME, "apps/ant/ant/rpc.py"), encoding="utf-8").read().split('"""')[1]))]
    st += [Paragraph("jtlearn: learn in the terminal", S["H2"]),
           P("The J.I.T.E.T.E.E. learning app (notes, quizzes, verses, AI tutor). Press `?` in its menu for help. The tutor uses your own AI when `nebula ai backend ant` is set."),
           code(re.sub(r"\x1b\[[0-9;]*m", "", sh([sys.executable, "-m", "jtlearn", "-h"], cwd=os.path.join(HOME, "apps", "jtlearn"), env={"PYTHONPATH": os.path.join(HOME, "apps", "jtlearn") + ":" + os.path.join(HOME, "lib")})), 7.2)]

    st += [Paragraph("GUI apps: files, monitor, player, gui", S["H2"]),
           P("Full-screen apps with mouse and touch support, built on `nebula_core.tui`. Tap buttons, tap rows, double-tap to open; everything also works from the keyboard. Press `?` inside any of them."),
           table([["App", "What it is", "Main keys"],
                  ["`files`", "Windows-Explorer-style file manager: address bar, toolbar, places, details pane, Trash with Restore, zip, search", "Enter open · Bksp up · Space tick · c x v · d trash · r rename · n/N new · i info · / filter"],
                  ["`monitor`", "Live CPU, memory, storage, battery, network, processes, Nebula info", "Tab/←→ tabs · 1-5 jump · K stop a process"],
                  ["`player`", "Audio player with library, queue, seek bar, volume (mpv)", "Space · n/p · ←/→ seek · +/- · s shuffle · r repeat"],
                  ["`gui`", "Tile launcher for every app", "number or tap"]], [W * 0.14, W * 0.5, W * 0.36], mono0=True),
           Paragraph("svn: save media from links", S["H2"]),
           P("`svn <link>` checks the link with yt-dlp, then asks: video or audio, quality (with size estimates), folder and name style, and downloads with live progress. Flags skip the questions."),
           code("svn https://youtube.com/shorts/6xhyB8Hlznc      # guided steps\nsvn <link> -a                  # audio (mp3), defaults\nsvn <link> -v 720              # video at 720p\nsvn <link> -f m4a -o ~/music   # format and folder\nsvn <link> --list              # every available format\nsvn history · svn --update · svn --doctor · svn sites"),
           Paragraph("Developer plugins", S["H2"]),
           table([["Command", "What it does"],
                  ["`repo`", "GitHub: create, edit, public/private, archive, delete (type the full name), branches, pull requests (mergeability check), issues, clone; token kept private (mode 600)"],
                  ["`gitx`", "Interactive git: advisor (what to do next), secret and large-file detection, AI commit messages, safe push, merge conflict prediction that never touches your files, force-push with lease and typed branch name"],
                  ["`fire`", "Firebase: login check, what changed per target, guarded deploy of hosting, functions and rules (rules need typed confirmation), preview channels"],
                  ["`accounts`", "One checklist of every login: git identity, GitHub (token type, scopes, expiry), Firebase, AI, Copilot, SSH, Termux"],
                  ["`project`", "Ask your project: next steps, review uncommitted changes, should I merge a branch?, is it safe to deploy?, explain the repo"]], [W * 0.16, W * 0.84], mono0=True),
           Paragraph("Ideas for more UI and plugins: docs/UI_IDEAS.md", S["small"])]

    # Neovim
    nv = os.path.join(HOME, "assets", "nvim", "lua", "nebula")
    keys = []
    for f in ("keymaps.lua", "ai.lua", "help.lua"):
        for m in re.finditer(r'(?:map|b)\(\s*(?:\{[^}]*\}|"[^"]+")\s*,\s*"([^"]+)"\s*,.*?,\s*"([^"]+)"', open(os.path.join(nv, f), encoding="utf-8").read()):
            keys.append((m.group(1).replace("<leader>", "Space "), m.group(2)))
    ucmds = []
    for f in sorted(glob.glob(os.path.join(nv, "*.lua"))):
        s = open(f, encoding="utf-8").read()
        for m in re.finditer(r'create_user_command\(\s*"(\w+)".*?desc\s*=\s*"([^"]+)"', s, re.S):
            ucmds.append((":" + m.group(1), m.group(2)))
    st += [Paragraph("Neovim: the Nebula editor", S["H2"]),
           P("`nv setup` makes plain `nvim` load Nebula's setup (your old config is backed up and `nv uninstall` restores it). Theme, statusline, tabs, start screen with recent files, fuzzy finder, file tree, completion, LSP, GitHub Copilot and AI coding powered by Ant. Your own tweaks go in `$NEBULA_CFG/nvim/user.lua`."),
           Paragraph("Keys (leader is Space)", S["H4"]), table([["Keys", "Does"]] + [[k, d] for k, d in dict.fromkeys(keys)], [W * 0.32, W * 0.68], mono0=True),
           Paragraph("Commands", S["H4"]), table([["Command", "Does"]] + [[c, d] for c, d in ucmds], [W * 0.32, W * 0.68], mono0=True),
           Paragraph("Copilot", S["H4"]),
           P("`:NebulaCopilot` (or `c` on the start screen) is the Copilot window: status, sign in, on/off, suggestions panel, log. Tab accepts a suggestion, Alt-] and Alt-[ cycle, Ctrl-] dismisses. Copilot is on in buffers with no filetype too. `nv doctor` checks Node, the server, sign-in and the network."),
           Paragraph("AI coding", S["H4"]),
           P("`Space a a` ask, `Space a e` edit the selection (you see a diff, Enter applies it), `Space a x` explain, `Space a f` fix diagnostics, `Space a g` agent (asks before writing or running), `Space a t` open Ant in a split. Agent runs from Neovim appear in `ant -c`."),
           PageBreak()]

    # ── 4 Plugins ──
    st += [Paragraph("Part 3: Plugins", S["H1"])]
    st += md(open(os.path.join(HOME, "docs", "PLUGINS.md"), encoding="utf-8").read().split("\n", 1)[1])
    st += [Paragraph("Walk-through: your first plugin", S["H2"]),
           code("$ nebula plugin new greet\n  ✔ Created ~/nebula/data/plugins/greet\n$ nebula greet --help        # answered from your help.txt\n$ nebula plugin list\n$ nebula check               # still consistent?"),
           P("Edit `plugin.sh` and `help.txt`. A scaffolded plugin looks like this:"),
           code("# plugin.sh\ncmd::greet() {\n  case \"${1:-}\" in\n    \"\") ui::say_status OK \"greet works\" ;;\n    *)  ui::say_status INFO \"greet got: $*\" ;;\n  esac\n}\n\n# help.txt\n@greet|Plugins|[args]|one line about what greet does\n  What it does, in a sentence or two.\n  Example: greet hello")]
    st += [Paragraph("nebula_core API", S["H2"]), P("A small standard-library layer every tool imports instead of re-implementing things.")]
    import nebula_core.paths as np_, nebula_core.help as nh_, nebula_core.ai as na_, nebula_core.theme as nt_, nebula_core.devtools as nd_, nebula_core.icons as ni_
    rows = [["Function", "Does"]]
    for mod, label in ((np_, "paths"), (nh_, "help"), (na_, "ai"), (nt_, "theme"), (nd_, "devtools"), (ni_, "icons")):
        for n, fn in inspect.getmembers(mod, inspect.isfunction):
            if fn.__module__ == mod.__name__ and not n.startswith("_") and fn.__doc__:
                sig = str(inspect.signature(fn))
                rows.append(["%s.%s%s" % (label, n, sig), fn.__doc__.strip().split("\n")[0]])
    st += [table(rows, [W * 0.46, W * 0.54], mono0=True), PageBreak()]

    # ── 5 Reference ──
    st += [Paragraph("Part 4: Reference", S["H1"])]
    st += [Paragraph("Palettes", S["H2"]), P("`nebula palette <name>` switches the shell, ant, jtlearn and Neovim.")]
    rows = [[Paragraph("<b>Name</b>", S["cell"])] + [Paragraph("<b>%s</b>" % r, S["cell"]) for r in ("primary", "second", "accent", "danger", "border")]]
    ts = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfdcd3"))]
    for i, (n, p) in enumerate(nth.PALETTES.items(), start=1):
        row = [Paragraph(n + (" (default)" if n == "nebula" else ""), S["cell"])]
        for j, r in enumerate(("primary", "second", "accent", "danger", "border"), start=1):
            hx = nth.xterm_hex(p[r]); row.append(Paragraph(hx, S["cellm"])); ts.append(("BACKGROUND", (j, i), (j, i), colors.HexColor(hx)))
            ts.append(("TEXTCOLOR", (j, i), (j, i), colors.black))
        rows.append(row)
    t = Table(rows, colWidths=[W * 0.2] + [W * 0.16] * 5, rowHeights=[16] + [22] * len(nth.PALETTES)); t.setStyle(TableStyle(ts)); st.append(t)
    st += [Paragraph("Nebula Mono: icons and symbols", S["H2"]), P("Nebula Mono is FiraCode Nerd Font Mono plus Nebula's own glyphs. Without it, `NEBULA_ICONS=nerd` or `plain` keeps every screen readable.")]
    gl = [("\ue400", "U+E400", "logo"), ("\ue401", "U+E401", "bolt"), ("\ue402", "U+E402", "sparkle"), ("\ue403", "U+E403", "prompt"), ("\ue404", "U+E404", "face"), ("\ue405", "U+E405", "planet"),
          ("\u2714", "U+2714", "check"), ("\u2716", "U+2716", "cross"), ("\u2717", "U+2717", "ballot x"), ("\u26a0", "U+26A0", "warning"), ("\u2139", "U+2139", "info"),
          ("\u27a4", "U+27A4", "arrowhead"), ("\u25b8", "U+25B8", "right triangle"), ("\u25be", "U+25BE", "down triangle"), ("\u2605", "U+2605", "star"), ("\u21ba", "U+21BA", "redo")]
    cells = [[Paragraph('<font name="NebulaMono" size="22" color="#00875a">%s</font><br/><font size="7.5" color="#5c6b63">%s %s</font>' % (g, c, n), ParagraphStyle("g", alignment=TA_CENTER, leading=26))] for g, c, n in gl]
    grid = [cells[i:i + 4] for i in range(0, len(cells), 4)]
    gt = Table([[c[0] for c in r] for r in grid], colWidths=[W / 4] * 4); gt.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfdcd3")), ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfdcd3")), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    st += [gt]
    st += [Paragraph("Files Nebula keeps ($NEBULA_CFG)", S["H2"]),
           table([["File or folder", "What it is"],
                  ["`palette.json`, `palette.sh`", "the active palette (`nebula palette`)"], ["`ai.backend`", "`auto`, `ant` or `tgpt` (`nebula ai backend`)"],
                  ["`plugins/`", "your plugins; `plugins.disabled` lists switched-off ones"], ["`nvim/user.lua`", "your Neovim tweaks, kept across updates"],
                  ["`.cache/help.merged`", "the merged command registry when plugins exist"], ["`nvim-plugins.log`", "output of the last `nv plugins`"],
                  ["`~/.ant/`", "ant's config, memory and sessions (shared with Neovim and nebula ai)"], ["`~/.config/nvim`", "link to Nebula's Neovim setup (`nv setup`); old config in `nvim.nebula-backup-*`"]],
                 [W * 0.34, W * 0.66], mono0=True)]
    env = {}
    for f in glob.glob(os.path.join(HOME, "lib", "*")) + glob.glob(os.path.join(HOME, "bin", "*")) + glob.glob(os.path.join(HOME, "zsh", "**", "*.zsh"), recursive=True) + glob.glob(os.path.join(HOME, "install", "*")) + glob.glob(os.path.join(HOME, "apps", "ant", "ant", "*.py")) + glob.glob(os.path.join(HOME, "assets", "nvim", "**", "*.lua"), recursive=True):
        try:
            for v in set(re.findall(r"\bNEBULA_[A-Z0-9_]+\b", open(f, encoding="utf-8").read())):
                env.setdefault(v, set()).add(os.path.relpath(f, HOME))
        except (OSError, UnicodeDecodeError):
            pass
    st += [Paragraph("Environment variables", S["H2"]), P("Every `NEBULA_*` variable the code reads, and where."),
           table([["Variable", "Used in"]] + [["`%s`" % k, ", ".join(sorted(v)[:3]) + (" …" if len(v) > 3 else "")] for k, v in sorted(env.items())], [W * 0.38, W * 0.62], mono0=True), PageBreak()]

    # ── 6 Codebase ──
    st += [Paragraph("Part 5: The codebase", S["H1"])]
    for title, f in (("Architecture", "ARCHITECTURE.md"), ("UI style", "UI_STYLE.md"), ("Packaging", "PACKAGING.md"), ("Launch", "LAUNCH.md")):
        p = os.path.join(HOME, "docs", f)
        if os.path.exists(p):
            st += [Paragraph(title, S["H2"])] + md(re.sub(r"^# .*\n", "", open(p, encoding="utf-8").read(), count=1))
    st += [Paragraph("Quality gates", S["H2"]),
           table([["Tool", "What it guarantees"], ["`nebula check` / `lib/check.sh`", "every command, plugin and app has help; registry entries match commands"],
                  ["`tools/test-core.sh`", "help everywhere, plugins, one AI backend, palette, Neovim help (29 tests)"],
                  ["`tools/gallery.py --check`", "key screens fit a phone: no broken boxes at 56 and 40 columns"],
                  ["`tools/make-font.py`", "rebuilds Nebula Mono with the Nebula icons and UI symbols"],
                  ["`tools/test_gui.py`", "every GUI app and dev plugin, driven in a pseudo-terminal against mock GitHub/Firebase/AI (56 checks)"],
                  ["`tools/make-manual.py`", "rebuilds this manual from the code"]], [W * 0.36, W * 0.64], mono0=True),
           PageBreak()]
    st += [Paragraph("Changelog", S["H1"])] + md(re.sub(r"^# .*\n", "", open(os.path.join(HOME, "docs", "CHANGELOG.md"), encoding="utf-8").read(), count=1)) + [PageBreak()]

    # ── 6b Codebase map + command source ──
    st += [Paragraph("Part 6: Codebase map", S["H1"]), P("Every source file, its size and what it says it is. Use it to find where a behaviour lives.")]
    for group, lines in codebase_map():
        st += [Paragraph(esc(group), S["H2"]), table([["File", "Lines", "Purpose (from its header)"]] + [["`%s`" % f, str(n), h or ""] for f, n, h in lines], [W * 0.42, W * 0.08, W * 0.5], mono0=True)]
    st.append(PageBreak())
    st += [Paragraph("Part 7: Command source", S["H1"]), P("The shell function behind every command (the entry point; long ones are cut at 140 lines). Read it with the entry above."), Paragraph("Listings, A to Z", S["H2"])]
    for e in sorted(entries.values(), key=lambda x: x["name"]):
        fi = fn_info(e["name"])
        if not fi:
            continue
        rel, line, body, cm = fi
        shown = body[:140] + (["    # … %d more lines in %s" % (len(body) - 140, rel)] if len(body) > 140 else [])
        st += [Paragraph("%s" % esc(e["name"]), S["H3"]), Paragraph(esc("%s line %d" % (rel, line)), S["src"]), code("\n".join(shown), 7.0)]
    st.append(PageBreak())

    # ── 7 Gallery ──
    shots = sorted(glob.glob(os.path.join(HOME, "docs", "screenshots", "*.png")))
    if shots:
        st += [Paragraph("Gallery", S["H1"]), P("Screens from Nebula and its Neovim setup (rendered in Nebula Mono).")]
        from PIL import Image as PI
        tmp = []
        for pth in shots:
            im = PI.open(pth).convert("RGB"); im.thumbnail((620, 760)); buf = os.path.join("/tmp", "man_" + os.path.basename(pth) + ".jpg"); im.save(buf, quality=78); tmp.append((buf, os.path.basename(pth), im.size))
        cellw = (W - 12) / 2
        for i in range(0, len(tmp), 2):
            row = []
            for buf, nm, (w, h) in tmp[i:i + 2]:
                sc = min(cellw / w, 330 / h); cap = re.sub(r"[-_]+", " ", os.path.splitext(nm)[0])
                row.append([Image(buf, width=w * sc, height=h * sc), Paragraph(esc(cap), S["cap"])])
            while len(row) < 2:
                row.append("")
            tb = Table([row], colWidths=[cellw + 6] * 2); tb.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")])); st.append(KeepTogether([tb]))
        st.append(PageBreak())

    # ── 8 Index ──
    st += [Paragraph("Index of commands", S["H1"]), P("All %d commands, alphabetical." % len(entries)),
           table([["Command", "Category", "What it does"]] + [["`%s`" % e["name"], e["cat"], e["summary"]] for e in sorted(entries.values(), key=lambda x: x["name"])], [W * 0.18, W * 0.14, W * 0.68], mono0=True)]

    doc = Doc(a.out)
    doc.multiBuild(st)
    print("wrote", a.out, "pages:", doc.page)


if __name__ == "__main__":
    main()
