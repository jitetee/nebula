"""Terminal UI: boxes, banner, tool output, summaries."""
import os
import subprocess

from .theme import T, vlen, truncate, term_width, link
from .render import render_markdown, render_diff


class C:
    dim = staticmethod(T.dim)
    bold = staticmethod(T.bold)
    cyan = staticmethod(T.tool)
    green = staticmethod(T.success)
    yellow = staticmethod(T.warn)
    red = staticmethod(T.error)
    magenta = staticmethod(T.assistant)
    gray = staticmethod(T.muted)


def home_short(p):
    h = os.environ.get("HOME", "")
    return p.replace(h, "~", 1) if h and p.startswith(h) else p


def git_branch():
    try:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=2)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "no branch"
    except Exception:
        return "no branch"


def rule(label="", color=None):
    color = color or T.muted
    W = term_width()
    if not label:
        return color("─" * W)
    used = 4 + 1 + len(label) + 1
    return color("─" * 4) + " " + T.accent(label) + " " + color("─" * max(2, W - used))


def _vpad(s, n):
    v = vlen(s)
    return s if v >= n else s + " " * (n - v)


def framed_top(title="", subtitle="", width=None, color=None):
    color = color or T.muted
    W = width or term_width()
    inner = W - 2
    tp = color("┤") + " " + T.bold(T.accent(title)) + " " + color("├") if title else ""
    sp = color("┤") + T.accentBg(" %s " % subtitle) + color("├") if subtitle else ""
    tl = len(" %s " % title) + 2 if title else 0
    sl = len(" %s " % subtitle) + 2 if subtitle else 0
    fill = max(0, inner - tl - sl - 4)
    return color("╭") + color("─" * 2) + tp + (" " + sp if sp else "") + color("─" * fill) + color("╮")


def framed_bot(width=None, footer="", color=None):
    color = color or T.muted
    W = width or term_width()
    inner = W - 2
    if not footer:
        return color("╰" + "─" * inner + "╯")
    tag = color("┤") + " " + T.muted(footer) + " " + color("├")
    used = len(" %s " % footer) + 2
    return color("╰") + color("─" * 2) + tag + color("─" * max(0, inner - used - 2)) + color("╯")


def framed_row(content, width=None, color=None):
    color = color or T.muted
    W = width or term_width()
    inner = W - 4
    return color("│") + " " + _vpad(truncate(content, inner), inner) + " " + color("│")


def framed_divider(width=None, label="", color=None):
    color = color or T.muted
    W = width or term_width()
    inner = W - 2
    if not label:
        return color("├" + "─" * inner + "┤")
    tag = " " + T.accentSoft(label) + " "
    return color("├") + color("─" * 2) + tag + color("─" * max(0, inner - vlen(tag) - 2)) + color("┤")


def framed_block(title, lines, subtitle="", width=None, footer="", color=None):
    W = width or term_width()
    out = [framed_top(title, subtitle, W, color)]
    for ln in lines:
        if ln == "---":
            out.append(framed_divider(W, "", color))
        elif isinstance(ln, dict):
            out.append(framed_divider(W, ln["divider"], color))
        else:
            out.append(framed_row(ln, W, color))
    out.append(framed_bot(W, footer, color))
    return "\n".join(out)


_SPARK = "▁▂▃▄▅▆▇█"


def bar_graph(value, mx, width=24, color=None):
    color = color or T.accent
    pct = max(0.0, min(1.0, value / mx if mx else 0))
    filled = round(pct * width)
    return color("█" * filled) + T.muted("░" * (width - filled))


def multi_bar(rows, label_w=10, bar_w=30):
    mv = max([1] + [r.get("max") or r.get("value") or 0 for r in rows])
    out = []
    for r in rows:
        bar = bar_graph(r.get("value") or 0, r.get("max") or mv, bar_w, r.get("color"))
        out.append(T.muted(str(r["label"]).ljust(label_w)) + " " + bar + "  " + T.bold(str(r.get("display", r.get("value")))))
    return out


_WORDMARK = [
    "  █████╗ ███╗   ██╗████████╗",
    " ██╔══██╗████╗  ██║╚══██╔══╝",
    " ███████║██╔██╗ ██║   ██║   ",
    " ██╔══██║██║╚██╗██║   ██║   ",
    " ██║  ██║██║ ╚████║   ██║   ",
    " ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ",
]


def _center(s, w):
    v = vlen(s)
    if v >= w:
        return truncate(s, w)
    pre = (w - v) // 2
    return " " * pre + s + " " * (w - v - pre)


def mode_badge(mode="default"):
    fn = {"default": T.tool, "acceptEdits": T.success, "plan": T.warn, "yolo": T.error}.get(mode, T.tool)
    return fn("▎" + mode)


def welcome_banner(cfg, version, recent):
    W = term_width(40, 110)
    inner = W - 4
    cwd = home_short(os.getcwd())
    tints = [T.accentDeep, T.accentDeep, T.accent, T.accent, T.accentSoft, T.accentSoft]
    lines = []
    if W >= 40:
        for i, w in enumerate(_WORDMARK):
            lines.append(_center(tints[i](w), inner))
    else:
        lines.append(_center(T.bold(T.accent("ant")), inner))
    lines.append(_center(T.bold(T.accentSoft("Ant CLI")) + " " + T.accentBg(" v%s " % version) + T.muted("  ·  ") + T.dim("a terminal coding agent"), inner))
    lines.append("")
    lines.append({"divider": "session"})
    bar = T.accent("▎")
    kv = lambda k, v: bar + " " + T.muted(k.ljust(9)) + v
    lines.append(kv("model", T.bold(T.accentSoft(cfg.get("model") or "(unset)")) + T.muted("  ·  ") + T.tool(cfg.get("provider") or "?")))
    mode = cfg.get("mode")
    lines.append(kv("mode", mode_badge(mode) if mode and mode != "default" else T.muted("default")))
    lines.append(kv("cwd", T.tool(cwd)))
    if recent:
        lines.append("")
        lines.append({"divider": "recent"})
        for s in recent[:4]:
            msg = " ".join((s.get("firstMessage") or "(empty)").split())
            when = T.muted((s.get("relTime") or "").rjust(7) + "  ") if s.get("relTime") else ""
            lines.append(T.accent("◆") + " " + when + truncate(msg, max(20, inner - 14)))
        lines.append("")
        lines.append(T.muted("resume: ") + T.accentSoft("ant -c") + T.muted("  or  ") + T.accentSoft("ant --session <id>"))
    else:
        lines.append("")
        lines.append({"divider": "tips"})
        lines.append(T.muted("type a request like ") + T.bold(T.accentSoft('"make a flask app"')))
        lines.append(T.muted("run ") + T.accentSoft("/help") + T.muted(" for commands · ") + T.accentSoft("/key") + T.muted(" to set a key"))
    return framed_block("ant", lines, subtitle="v" + version, width=W,
                        footer="%s · %s" % (cfg["model"], cfg.get("provider") or "?") if cfg.get("model") else "")


_META = {
    "read_file": "Read", "list_dir": "List", "search": "Search", "glob": "Glob", "write_file": "Write",
    "edit_file": "Edit", "apply_patch": "Patch", "mkdir": "Mkdir", "delete_path": "Delete", "bash": "Bash",
    "run_code": "Run", "http_get": "Fetch", "git": "Git", "skill_list": "Skills", "skill_get": "Skill",
    "summarize_text": "Summarize",
}


def _tool_color(name):
    if name in ("write_file", "edit_file", "apply_patch", "mkdir"):
        return T.success
    if name == "delete_path":
        return T.delete
    if name in ("bash", "run_code"):
        return T.warn
    if name == "http_get":
        return T.accentSoft
    return T.accent


def tool_header(name, summary="", ms=None):
    verb = _META.get(name, name)
    head = T.bold(_tool_color(name)("┃")) + " " + T.bold(verb)
    return head + (" " + T.muted(summary) if summary else "") + (T.muted("  %dms" % ms) if ms is not None else "")


def _colorize(l):
    import re
    if l.startswith("@@ "):
        return T.muted(l)
    if re.match(r"^\+\s", l):
        return T.add(l)
    if re.match(r"^-\s", l):
        return T.delete(l)
    if re.match(r"^---|^\+\+\+|stdout|stderr|exit=", l):
        return T.muted(l)
    return l


def tool_result_lines(result, mx=14):
    lines = str("" if result is None else result).split("\n")
    if len(lines) == 1 and not lines[0].strip():
        return T.muted("  └─ (empty)")
    head = lines[:mx]
    over = len(lines) > mx
    tail = lines[-2:] if over else []
    out = []
    for i, l in enumerate(head):
        last = not over and i == len(head) - 1
        out.append("  " + T.muted("└─ " if last else "├─ ") + _colorize(l))
    if over:
        out.append("  " + T.muted("├─ … +%d more lines" % (len(lines) - mx)))
        for i, l in enumerate(tail):
            out.append("  " + T.muted("└─ " if i == len(tail) - 1 else "├─ ") + _colorize(l))
    return "\n".join(out)


def diff_block(before, after, filename=""):
    return render_diff(before, after, filename=filename)


def status_line(tokens=0, elapsed_ms=0):
    s = round((elapsed_ms or 0) / 1000)
    t = "%dm%02ds" % (s // 60, s % 60)
    parts = [x for x in ("{:,} tok".format(tokens) if tokens else "", t) if x]
    return "  " + T.muted(" · ".join(parts))


def exit_summary(session_id, model, provider, cwd, tokens, elapsed_ms, turns, tool_calls, first_message):
    W = term_width(60, 100)
    es = round((elapsed_ms or 0) / 1000)
    elapsed = "%dm %02ds" % (es // 60, es % 60)
    tk = "{:,}".format(tokens or 0)
    first = " ".join((first_message or "(no messages)").split())
    bar = T.accent("▎")
    kv = lambda k, v: bar + " " + T.muted(k.ljust(9)) + v
    lines = [kv("id", T.tool(session_id or "")),
             kv("first", truncate(first, W - 18)),
             kv("model", T.bold(T.accentSoft(model or "?")) + T.muted("  ·  ") + T.tool(provider or "?")),
             kv("cwd", T.tool(home_short(cwd or ""))),
             "", {"divider": "stats"}]
    lines += multi_bar([
        {"label": "turns", "value": turns or 0, "max": max(turns or 0, 10), "color": T.accent, "display": str(turns or 0)},
        {"label": "tools", "value": tool_calls or 0, "max": max(tool_calls or 0, 10), "color": T.accentSoft, "display": str(tool_calls or 0)},
        {"label": "tokens", "value": tokens or 0, "max": max(tokens or 0, 1000), "color": T.accentDeep, "display": tk},
        {"label": "elapsed", "value": es, "max": max(es, 60), "color": T.success, "display": elapsed},
    ], 9, max(16, W - 32))
    lines += ["", {"divider": "resume"},
              T.muted("resume:  ") + T.accentSoft("ant --session %s" % (session_id or "")),
              T.muted("or:      ") + T.accentSoft("ant -c")]
    return framed_block("session summary", lines, subtitle=elapsed, width=W, footer="%d turns · %s tok" % (turns or 0, tk))


def assistant_block(text):
    if not text or not text.strip():
        return ""
    bar = T.assistant("┃")
    return "\n".join("  " + bar + " " + l for l in render_markdown(text).split("\n"))


def thought_block(text):
    if not text or not text.strip():
        return ""
    return "\n".join("  " + T.muted("◷") + " " + T.dim(l) for l in text.strip().split("\n"))


def user_prefix():
    return T.accent("  ❯ ") + " "


def input_box_top():
    return T.dim("╭" + "─" * (term_width() - 2) + "╮")


def input_box_bottom(model=""):
    W = term_width()
    bot = T.dim("╰" + "─" * (W - 2) + "╯")
    parts = ["  " + (os.path.basename(os.getcwd()) or "/"), "  " + git_branch(), "  " + (model or "?")]
    content = " │ ".join(parts)
    return bot + "\n" + T.accentBg(content.ljust(W)[:W])


def compact_output(text, head=8, tail=4):
    lines = str(text).split("\n")
    if len(lines) <= head + tail + 2:
        return text
    return "\n".join(lines[:head] + [T.muted("… %d hidden lines …" % (len(lines) - head - tail))] + lines[-tail:])
