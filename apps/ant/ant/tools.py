"""Agent tools. Pure stdlib."""
import fnmatch
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import urllib.request

from . import store

READ_ONLY = {"read_file", "list_dir", "search", "glob", "http_get", "skill_list", "skill_get", "summarize_text"}
WRITE_OR_EXEC = {"write_file", "edit_file", "apply_patch", "mkdir", "delete_path", "bash", "run_code", "git"}
MAX_OUTPUT = 200_000
BASH_TIMEOUT = 30
GIT_TIMEOUT = 60

RO_HEADS = set("""ls ll la cat bat head tail wc stat file pwd whoami id env printenv echo date uptime uname hostname which type
command compgen ps top df du free lsof netstat ss node npm npx python python3 pip pip3 gh git yarn pnpm bun deno go cargo rustc
tree find grep rg ag ack fd fzf curl wget ping dig nslookup host termux-info pkg dpkg apt tldr man help jq yq xq diff cmp awk""".split())

MUTATING = {
    "git": set("push pull fetch merge rebase reset checkout switch commit add rm mv stash tag clone init clean cherry-pick revert apply am submodule worktree config".split()),
    "npm": set("install i uninstall remove rm update upgrade publish unpublish link unlink init run start test ci audit fund dedupe prune rebuild".split()),
    "yarn": set("add remove install upgrade publish link unlink init".split()),
    "pnpm": set("add remove install i update publish link unlink init".split()),
    "pkg": set("install i uninstall remove rm upgrade update".split()),
    "apt": set("install remove purge upgrade update autoremove".split()),
    "pip": {"install", "uninstall", "wheel"}, "pip3": {"install", "uninstall", "wheel"},
    "go": set("install get mod build run test clean".split()),
    "cargo": set("install uninstall publish build run test clean update".split()),
}


def is_read_only_bash(command):
    if not command or not isinstance(command, str):
        return False
    cmd = command.strip()
    if re.search(r"[`$]\(", cmd) or "`" in cmd:
        return False
    if re.search(r"(^|[^&])>>?\s*\S", cmd):
        return False
    if re.search(r"[;&]", cmd) and not re.match(r"^\s*[^|;&]+(\s*\|\s*[^|;&]+)*\s*$", cmd):
        return False
    segs = [s.strip() for s in cmd.split("|") if s.strip()]
    if not segs:
        return False
    for seg in segs:
        stripped = re.sub(r"^(\s*[A-Z_][A-Z0-9_]*=\S+\s+)+", "", seg, flags=re.I)
        toks = stripped.split()
        if not toks:
            return False
        head = toks[0].split("/")[-1]
        if head not in RO_HEADS:
            return False
        mut = MUTATING.get(head)
        if mut and len(toks) > 1 and not toks[1].startswith("-") and toks[1] in mut:
            return False
    return True


def is_read_only_call(name, args):
    if name in READ_ONLY:
        return True
    if name == "bash":
        return is_read_only_bash((args or {}).get("command", ""))
    if name == "git":
        a = (args or {}).get("args") or []
        return bool(a) and a[0] not in MUTATING["git"]
    return False


def _s(**props):
    return {"type": "object", "properties": props, "required": [k for k, v in props.items() if not v.pop("_opt", False)]}


def _str(d=None, **kw):
    x = {"type": "string"}
    if d:
        x["description"] = d
    x.update(kw)
    return x


TOOL_SCHEMAS = [
    {"name": "summarize_text", "description": "Summarize a large text blob into a concise answer.",
     "parameters": _s(text=_str("The long text to summarise"), max_tokens={"type": "integer", "default": 300, "_opt": True})},
    {"name": "read_file", "description": "Read a UTF-8 text file from disk. Returns its full contents.",
     "parameters": _s(path=_str("Absolute or relative path"))},
    {"name": "list_dir", "description": "List entries in a directory (non-recursive).", "parameters": _s(path=_str())},
    {"name": "search", "description": "Recursively grep a regex in a directory. Returns matching lines with file:line.",
     "parameters": _s(path=_str(), pattern=_str("Regular expression (Python syntax)"), max_results={"type": "integer", "default": 200, "_opt": True})},
    {"name": "write_file", "description": "Create or overwrite a file with the given UTF-8 content. Creates parent directories.",
     "parameters": _s(path=_str(), content=_str())},
    {"name": "edit_file", "description": "Replace the first occurrence of old_string with new_string in path. old_string must be unique. Set replace_all=true to replace every occurrence.",
     "parameters": _s(path=_str(), old_string=_str(), new_string=_str(), replace_all={"type": "boolean", "default": False, "_opt": True})},
    {"name": "mkdir", "description": "Create a directory (recursive).", "parameters": _s(path=_str())},
    {"name": "delete_path", "description": "Delete a file or directory (recursive).", "parameters": _s(path=_str())},
    {"name": "bash", "description": "Run a shell command. Returns combined stdout+stderr and exit code.",
     "parameters": _s(command=_str(), cwd=_str("Working directory; defaults to current.", _opt=True), timeout_ms={"type": "integer", "default": 60000, "_opt": True})},
    {"name": "run_code", "description": "Execute a snippet in a chosen language. Supported: python, bash, sh (node if installed).",
     "parameters": _s(language=_str(enum=["python", "node", "bash", "sh"]), code=_str(), timeout_ms={"type": "integer", "default": 60000, "_opt": True})},
    {"name": "glob", "description": 'Find files by glob pattern (e.g. "src/**/*.ts").',
     "parameters": _s(pattern=_str(), path=_str("Root dir, default cwd", _opt=True), max_results={"type": "integer", "default": 200, "_opt": True})},
    {"name": "apply_patch", "description": "Apply multiple edits to a single file atomically.",
     "parameters": _s(path=_str(), edits={"type": "array", "items": {"type": "object", "properties": {
         "old_string": _str(), "new_string": _str(), "replace_all": {"type": "boolean", "default": False}},
         "required": ["old_string", "new_string"]}})},
    {"name": "http_get", "description": "HTTP GET a URL and return the response body (text). Caps at 200KB.",
     "parameters": _s(url=_str(), headers={"type": "object", "_opt": True}, timeout_ms={"type": "integer", "default": 30000, "_opt": True})},
    {"name": "git", "description": "Run a git subcommand in cwd. Refuses destructive actions unless confirm=true.",
     "parameters": _s(args={"type": "array", "items": {"type": "string"}}, cwd=_str(_opt=True), confirm={"type": "boolean", "default": False, "_opt": True})},
    {"name": "skill_list", "description": "List available skills.", "parameters": {"type": "object", "properties": {}}},
    {"name": "skill_get", "description": "Load a skill by name.", "parameters": _s(name=_str())},
]


def _abs(p):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.abspath(os.path.join(os.getcwd(), p))


def _run(argv, cwd=None, timeout=None, shell_cmd=None):
    try:
        p = subprocess.Popen(argv, cwd=cwd or os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             stdin=subprocess.DEVNULL, start_new_session=True)
    except OSError as e:
        return {"stdout": "", "stderr": str(e), "exit": -1, "timed_out": False}
    timed = False
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed = True
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            p.kill()
        out, err = p.communicate()
    except KeyboardInterrupt:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            p.kill()
        p.communicate()
        raise
    return {"stdout": out.decode("utf-8", "replace"), "stderr": err.decode("utf-8", "replace"), "exit": p.returncode, "timed_out": timed}


def _fmt(r):
    parts = ["exit=%s%s" % (r["exit"], " (timed out)" if r["timed_out"] else "")]
    cut = lambda s: s[:MAX_OUTPUT] + "\n…[TRUNCATED: Output exceeded token limit. Some data was cut.]" if len(s) > MAX_OUTPUT else s
    if r["stdout"]:
        parts.append("--- stdout ---\n" + cut(r["stdout"].rstrip()))
    if r["stderr"]:
        parts.append("--- stderr ---\n" + cut(r["stderr"].rstrip()))
    return "\n".join(parts)


def _read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def _write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def _apply(text, old, new, all_, label=""):
    if all_:
        if old not in text:
            raise ValueError(label + "old_string not found")
        return text.replace(old, new)
    i = text.find(old)
    if i < 0:
        raise ValueError(label + "old_string not found")
    if text.find(old, i + 1) >= 0:
        raise ValueError(label + "old_string not unique")
    return text[:i] + new + text[i + len(old):]


def _skip(name):
    return name.startswith(".git") or name == "node_modules" or name == "__pycache__"


def _glob_re(g):
    r, i = "^", 0
    while i < len(g):
        c = g[i]
        if c == "*":
            if g[i + 1:i + 2] == "*":
                r += ".*"; i += 1
                if g[i + 1:i + 2] == "/":
                    i += 1
            else:
                r += "[^/]*"
        elif c == "?":
            r += "[^/]"
        else:
            r += re.escape(c)
        i += 1
    return re.compile(r + "$")


def execute(name, args, cfg=None):
    a = args or {}
    if name == "read_file":
        c = _read(_abs(a["path"]))
        return c[:MAX_OUTPUT] + "\n…[TRUNCATED: File too large, only first 200KB shown.]" if len(c) > MAX_OUTPUT else c
    if name == "list_dir":
        p = _abs(a["path"])
        return "\n".join("%s %s" % ("d" if os.path.isdir(os.path.join(p, n)) else "f", n) for n in sorted(os.listdir(p)))
    if name == "search":
        rx, mx, out = re.compile(a["pattern"]), a.get("max_results") or 200, []
        for dp, dns, fns in os.walk(_abs(a["path"])):
            dns[:] = sorted(d for d in dns if not _skip(d))
            for fn in sorted(fns):
                if len(out) >= mx:
                    break
                if _skip(fn):
                    continue
                full = os.path.join(dp, fn)
                try:
                    for i, line in enumerate(_read(full)[:MAX_OUTPUT].split("\n"), 1):
                        if rx.search(line):
                            out.append("%s:%d: %s" % (full, i, line))
                            if len(out) >= mx:
                                break
                except OSError:
                    pass
        return "\n".join(out) or "(no matches)"
    if name == "write_file":
        p = _abs(a["path"]); existed = os.path.exists(p)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        _write(p, a["content"])
        return "%s %s (%d lines)" % ("rewrote" if existed else "created", p, a["content"].count("\n") + 1)
    if name == "edit_file":
        p = _abs(a["path"])
        _write(p, _apply(_read(p), a["old_string"], a["new_string"], a.get("replace_all")))
        return "edited " + p
    if name == "mkdir":
        p = _abs(a["path"]); os.makedirs(p, exist_ok=True)
        return "mkdir " + p
    if name == "delete_path":
        p = _abs(a["path"])
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.lexists(p):
            os.remove(p)
        return "deleted " + p
    if name == "bash":
        sh = os.environ.get("SHELL") or "/bin/sh"
        if not os.path.exists(sh):
            sh = "/bin/sh"
        t = a.get("timeout_ms")
        r = _run([sh, "-c", a["command"]], _abs(a["cwd"]) if a.get("cwd") else None, (t / 1000) if t else BASH_TIMEOUT)
        o = _fmt(r)
        return o[:MAX_OUTPUT] + "\n…[truncated]" if len(o) > MAX_OUTPUT else o
    if name == "run_code":
        lang = a["language"]
        ext = {"python": ".py", "node": ".mjs"}.get(lang, ".sh")
        fd, f = tempfile.mkstemp(prefix="ant-", suffix=ext)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(a["code"])
        try:
            if lang == "python":
                argv = [sys.executable, f]
            elif lang == "node":
                if not shutil.which("node"):
                    raise ValueError("node is not installed; use python or bash")
                argv = ["node", f]
            else:
                argv = ["/bin/sh", f]
            return _fmt(_run(argv, None, (a.get("timeout_ms") or 60000) / 1000))
        finally:
            try:
                os.remove(f)
            except OSError:
                pass
    if name == "glob":
        root = _abs(a.get("path") or os.getcwd()); rx = _glob_re(a["pattern"]); mx = a.get("max_results") or 200
        found = []
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in (".git", "node_modules", "__pycache__")]
            for fn in fns:
                full = os.path.join(dp, fn)
                if rx.match(os.path.relpath(full, root)):
                    try:
                        found.append((os.path.getmtime(full), full))
                    except OSError:
                        pass
        found.sort(reverse=True)
        return "\n".join(f for _, f in found[:mx]) or "(no matches)"
    if name == "apply_patch":
        p = _abs(a["path"]); text = _read(p); edits = a.get("edits") or []
        for i, e in enumerate(edits):
            text = _apply(text, e["old_string"], e["new_string"], e.get("replace_all"), "edit %d: " % i)
        _write(p, text)
        return "applied %d edit%s to %s" % (len(edits), "" if len(edits) == 1 else "s", p)
    if name == "http_get":
        req = urllib.request.Request(a["url"], headers=a.get("headers") or {})
        try:
            with urllib.request.urlopen(req, timeout=(a.get("timeout_ms") or 30000) / 1000) as r:
                code, reason, ctype, body = r.status, r.reason, r.headers.get("content-type", ""), r.read(MAX_OUTPUT + 1)
        except urllib.error.HTTPError as e:
            code, reason, ctype, body = e.code, e.reason, e.headers.get("content-type", ""), e.read(MAX_OUTPUT + 1)
        txt = body.decode("utf-8", "replace")
        if len(txt) > MAX_OUTPUT:
            txt = txt[:MAX_OUTPUT] + "\n…[TRUNCATED: Response too large, only first 200KB shown.]"
        return "HTTP %s %s\ncontent-type: %s\n\n%s" % (code, reason, ctype, txt)
    if name == "git":
        argv = a.get("args") or []
        sub = argv[0] if argv else ""
        bad = ((sub == "push") or (sub == "reset" and "--hard" in argv)
               or (sub == "clean" and any(re.search(r"-.*f", x) for x in argv))
               or (sub == "branch" and "-D" in argv)
               or (sub == "checkout" and ("." in argv or "--" in argv)))
        if bad and not a.get("confirm"):
            return "refused: destructive git %s requires confirm=true" % sub
        r = _run(["git"] + argv, _abs(a["cwd"]) if a.get("cwd") else None, GIT_TIMEOUT)
        return _fmt(r)
    if name == "skill_list":
        if not os.path.isdir(store.SKILLS):
            return "(no skills directory)"
        f = sorted(n[:-3] for n in os.listdir(store.SKILLS) if n.endswith(".md"))
        return "\n".join(f) or "(no skills)"
    if name == "skill_get":
        f = os.path.join(store.SKILLS, os.path.basename(a["name"]) + ".md")
        if not os.path.exists(f):
            raise ValueError("skill not found: %s" % a["name"])
        return _read(f)
    if name == "summarize_text":
        from .providers import chat
        c = dict(cfg or store.load(), systemPrompt="Summarize the following text concisely (max tokens: %s)." % (a.get("max_tokens") or 300),
                 maxTokens=a.get("max_tokens") or 300)
        r = chat(c, [{"role": "user", "content": a["text"]}], with_tools=False)
        return (r.get("content") or "").strip()
    raise ValueError("unknown tool: %s" % name)


def summarize_args(name, a):
    a = a or {}
    if name == "write_file":
        c = a.get("content") or ""
        return "%s (%d bytes)" % (a.get("path"), len(c.encode()))
    if name == "edit_file":
        return '%s  - "%s…" → "%s…"%s' % (a.get("path"), (a.get("old_string") or "")[:30], (a.get("new_string") or "")[:30], "  [all]" if a.get("replace_all") else "")
    if name == "apply_patch":
        n = len(a.get("edits") or [])
        return "%s  %d edit%s" % (a.get("path"), n, "" if n == 1 else "s")
    if name == "bash":
        return a.get("command", "")
    if name == "run_code":
        c = a.get("code") or ""
        return ("%s: %s" % (a.get("language"), (c[:120] + ("…" if len(c) > 120 else "")).replace("\n", "⏎")[:100]))
    if name == "git":
        l = a.get("args") or []
        return "git " + " ".join(l[:5]) + (" …" if len(l) > 5 else "")
    if name in ("delete_path", "mkdir", "glob", "http_get", "skill_get"):
        return a.get("path") or a.get("url") or a.get("name") or a.get("pattern") or ""
    return json.dumps(a)
