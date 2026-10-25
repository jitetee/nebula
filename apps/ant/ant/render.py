"""Syntax colouring, markdown and diff rendering (stdlib only)."""
import os
import re

from .theme import T, vlen, term_width, visible

_KW = set(("abstract as async await break case catch class const continue debugger default def del delete do elif "
           "else enum except export extends false finally fn for from function global if import in instanceof is "
           "lambda let match new nonlocal None not null of or pass print raise return self static struct super "
           "switch this throw true True try typeof undefined var void while with yield and echo fi then done esac").split())
_RE = re.compile(r"(#[^\n]*|//[^\n]*|/\*[\s\S]*?\*/)|(\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)"
                 r"|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)")


def highlight(code):
    if os.environ.get("NO_COLOR"):
        return code

    def sub(m):
        cm, st, num, ident = m.groups()
        if cm:
            return T.dim(cm)
        if st:
            return T.success(st)
        if num:
            return T.warn(num)
        if ident and ident in _KW:
            return T.bold(T.accent(ident))
        return m.group(0)

    return _RE.sub(sub, code)


# ---------------- markdown ----------------

def _inline(s):
    if not s:
        return ""
    s = re.sub(r"`([^`]+)`", lambda m: T.accentBg(" " + m.group(1) + " "), s)
    s = re.sub(r"\*\*([^*]+)\*\*", lambda m: T.bold(m.group(1)), s)
    s = re.sub(r"__([^_]+)__", lambda m: T.bold(m.group(1)), s)
    s = re.sub(r"(^|[^*])\*([^*]+)\*", lambda m: m.group(1) + T.italic(m.group(2)), s)
    s = re.sub(r"(^|[^_\w])_([^_]+)_", lambda m: m.group(1) + T.italic(m.group(2)), s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: T.tool(m.group(1)) + T.muted(" (%s)" % m.group(2)), s)
    return s


def render_markdown(md):
    if not md:
        return ""
    out, in_fence, lang, buf = [], False, "", []

    def flush_code():
        code = highlight("\n".join(buf))
        w = 64
        pill = T.accentBg(" %s " % lang) if lang else ""
        head = T.muted("─" * max(2, w - (len(lang) + 4 if lang else 0)))
        out.append(T.muted("╭─") + pill + head)
        for c in code.split("\n"):
            out.append(T.muted("│ ") + c)
        out.append(T.muted("╰" + "─" * w))

    for ln in str(md).split("\n"):
        f = re.match(r"^```\s*([a-zA-Z0-9_-]*)\s*$", ln)
        if f:
            if not in_fence:
                in_fence, lang, buf = True, f.group(1).lower(), []
            else:
                flush_code()
                in_fence, lang, buf = False, "", []
            continue
        if in_fence:
            buf.append(ln)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            out.append(T.accent("█" * max(1, 4 - len(m.group(1)))) + " " + T.bold(m.group(2)))
            continue
        m = re.match(r"^(\s*)[-*]\s+(.*)$", ln)
        if m:
            out.append(m.group(1) + T.accent("•") + " " + _inline(m.group(2)))
            continue
        m = re.match(r"^(\s*)(\d+)\.\s+(.*)$", ln)
        if m:
            out.append(m.group(1) + T.accent(m.group(2) + ".") + " " + _inline(m.group(3)))
            continue
        m = re.match(r"^>\s?(.*)$", ln)
        if m:
            out.append(T.muted("│ ") + T.italic(_inline(m.group(1))))
            continue
        if re.match(r"^[-*_]{3,}$", ln.strip()):
            out.append(T.muted("─" * 60))
            continue
        out.append(_inline(ln))
    if in_fence and buf:
        for c in highlight("\n".join(buf)).split("\n"):
            out.append(T.muted("│ ") + c)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip()


# ---------------- diff ----------------

def _lang(name):
    m = re.search(r"\.([a-z0-9]+)$", (name or "").lower())
    if not m:
        return ""
    e = m.group(1)
    return {"js": "js", "mjs": "js", "cjs": "js", "ts": "ts", "tsx": "ts", "py": "py", "sh": "sh", "bash": "sh",
            "zsh": "sh", "html": "html", "htm": "html", "css": "css", "json": "json"}.get(e, "")


def _lcs(a, b):
    n, m = len(a), len(b)
    if n * m > 4_000_000:  # huge: treat as full replace instead of eating memory
        return [("-", x) for x in a] + [("+", y) for y in b]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        ai, row, nxt = a[i], dp[i], dp[i + 1]
        for j in range(m - 1, -1, -1):
            row[j] = nxt[j + 1] + 1 if ai == b[j] else (nxt[j] if nxt[j] >= row[j + 1] else row[j + 1])
    ops, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            ops.append(("=", a[i])); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            ops.append(("-", a[i])); i += 1
        else:
            ops.append(("+", b[j])); j += 1
    ops += [("-", x) for x in a[i:]]
    ops += [("+", y) for y in b[j:]]
    return ops


def _word_diff(a, b):
    tok = lambda s: [t for t in re.split(r"(\s+|\b)", s) if t]
    A, B = tok(a), tok(b)
    return _lcs(A, B)


def _render_words(ops, side):
    base = T.delete if side == "del" else T.add
    out = ""
    for op, t in ops:
        if op == "=":
            out += base(t)
        elif op == "-" and side == "del":
            out += T.bold(T.delBg(T.delete(t)))
        elif op == "+" and side == "add":
            out += T.bold(T.addBg(T.add(t)))
    return out


def _group(ops):
    groups, d, a = [], [], []
    for op in ops:
        if op[0] == "-":
            d.append(op)
        elif op[0] == "+":
            a.append(op)
        else:
            if d or a:
                groups.append(("change", d, a)); d, a = [], []
            groups.append(("eq", op))
    if d or a:
        groups.append(("change", d, a))
    return groups


def _hunks(groups, context=3):
    hunks, i = [], 0
    while i < len(groups):
        if groups[i][0] == "eq":
            i += 1
            continue
        start, bk = i, 0
        while start > 0 and groups[start - 1][0] == "eq" and bk < context:
            start -= 1; bk += 1
        end = i
        while end < len(groups):
            if groups[end][0] != "eq":
                end += 1
                continue
            run = 0
            while end + run < len(groups) and groups[end + run][0] == "eq":
                run += 1
            if run > context * 2:
                end += context
                break
            end += run
        hunks.append(groups[start:end])
        i = end
    return hunks


def render_diff(before, after, context=3, max_lines=80, filename=""):
    a = str(before or "").split("\n")
    b = str(after or "").split("\n")
    if len(a) > 1 and a[-1] == "":
        a.pop()
    if len(b) > 1 and b[-1] == "":
        b.pop()
    lang = _lang(filename)
    ops = _lcs(a, b)
    hunks = _hunks(_group(ops), context)
    adds = sum(1 for o in ops if o[0] == "+")
    dels = sum(1 for o in ops if o[0] == "-")
    W = term_width()
    gw = len(str(max(len(a), len(b), 1)))
    blank = " " * gw
    is_new = len(a) == 0 or (len(a) == 1 and a[0] == "")
    stats = " ".join(x for x in (T.bold(T.add("+%d" % adds)) if adds else "", T.bold(T.delete("−%d" % dels)) if dels else "") if x)
    head = T.muted("╭─ ") + (T.bold(T.accentSoft(filename)) if filename else T.bold("(diff)"))
    out = [head + (" " + T.accentBg(" NEW ") if is_new else "") + ("  " + stats if stats else "")
           + (T.muted(" · ") + T.accentSoft(lang) if lang else "")]
    room = W - gw * 2 - 8

    def trim(s):
        return s if vlen(s) <= room else visible(s)[: max(0, room - 1)] + T.muted("…")

    ctx = (lambda l: highlight(l)) if lang else (lambda l: l)
    al = bl = 1
    total, first = 0, True
    for h in hunks:
        if not first:
            out.append(T.muted("│ ") + T.accent("@@ −%d +%d @@" % (al, bl)))
        first = False
        for g in h:
            total += 1
            if total > max_lines + 1:
                out.append(T.muted("│ … diff truncated"))
                out.append(T.muted("╰─"))
                return "\n".join(out)
            if g[0] == "eq":
                out.append(T.muted("│ %s %s │ " % (str(al).rjust(gw), str(bl).rjust(gw))) + "  " + trim(ctx(g[1][1])))
                al += 1; bl += 1
                continue
            D, A = g[1], g[2]
            pairs = min(len(D), len(A))
            for k in range(pairs):
                wd = _word_diff(D[k][1], A[k][1])
                out.append(T.muted("│ %s %s " % (str(al).rjust(gw), blank)) + T.delete("▌") + " " + T.delete("− ") + trim(_render_words(wd, "del")))
                out.append(T.muted("│ %s %s " % (blank, str(bl).rjust(gw))) + T.add("▌") + " " + T.add("+ ") + trim(_render_words(wd, "add")))
                al += 1; bl += 1
            for k in range(pairs, len(D)):
                out.append(T.muted("│ %s %s " % (str(al).rjust(gw), blank)) + T.delete("▌") + " " + T.delete("− ") + trim(T.delete(D[k][1])))
                al += 1
            for k in range(pairs, len(A)):
                out.append(T.muted("│ %s %s " % (blank, str(bl).rjust(gw))) + T.add("▌") + " " + T.add("+ ") + trim(T.add(A[k][1])))
                bl += 1
    out.append(T.muted("╰─ ") + T.muted("%d → %d lines" % (len(a), len(b))))
    if len(out) == 2:
        return T.muted("(no textual changes)")
    return "\n".join(out)
