"""Slash commands. handle() returns True when recognised."""
import os
import re
import signal
import subprocess

from . import store
from .store import PROVIDERS, has_key, load, save, set_key, list_for, default_model, list_sessions, rel_time
from .tools import is_read_only_bash
from .picker import pick, ask
from .ui import C, rule

HELP = [
    ("navigation", [("/help", "show this help"), ("/exit", "quit")]),
    ("session control", [("/cancel", "abort the running turn (press Ctrl-C)"), ("/reset", "clear conversation history (new session)"),
                         ("/sessions", "list recent saved sessions"), ("/resume [id]", "resume session (or last if omitted)")]),
    ("configuration", [("/provider", "pick provider (interactive)"), ("/model", "pick model (interactive)"),
                       ("/key [provider]", "set API key (interactive)"), ("/baseurl <url>", "set base URL (generic provider)"),
                       ("/system <text|default>", "set/clear custom system prompt"), ("/mode [name]", "default · acceptEdits · plan · yolo"),
                       ("/setup", "re-run first-run setup")]),
    ("filesystem", [("/cd <path>", "change working directory"), ("/pwd", "show working directory"),
                    ("/show", "show current config"), ("/clear", "clear screen")]),
    ("shell", [("/run <cmd>", "execute a shell command (safety checked)"), ("!<cmd>", "shortcut for /run")]),
]

DANGEROUS = [r"\brm\s+(-[a-zA-Z]*\s+)*(/|~|\$HOME|\*)(\s|$)", r"\bmkfs\b", r"\bdd\s+.*of=/dev/", r":\(\)\s*\{",
             r">\s*/dev/(sd|mmcblk|nvme)", r"\bchmod\s+-R\s+0?777\s+/", r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z)?sh\b"]


def help_():
    print("")
    for sec, rows in HELP:
        print(rule(sec))
        for c, d in rows:
            print("  %s %s" % (C.cyan(c.ljust(24)), d))
    print("")


def _pick_provider(cfg):
    items = [{"id": p, "label": p, "note": "key set" if has_key(cfg, p) else "no key"} for p in PROVIDERS]
    s = pick("Select provider", items, max(0, PROVIDERS.index(cfg["provider"]) if cfg["provider"] in PROVIDERS else 0))
    return s["id"] if s else None


def _pick_model(provider, current):
    lst = list_for(provider)
    if not lst:
        return ask(C.dim("Enter model id for %s: " % provider)) or None
    ids = [m["id"] for m in lst]
    s = pick("Select model for %s" % provider, [{"id": m["id"], "label": m["id"], "note": m["note"]} for m in lst],
             ids.index(current) if current in ids else 0)
    return s["id"] if s else None


def ask_key(provider):
    k = ask(C.dim("Paste API key for %s (input hidden): " % provider), hide=True)
    if not k:
        print(C.yellow("no key entered")); return False
    set_key(provider, k)
    print(C.green("✓ key saved for %s" % provider))
    return True


def _run_shell(cmd):
    if not cmd:
        print(C.yellow("Usage: /run <shell command>")); return
    if any(re.search(p, cmd) for p in DANGEROUS):
        print(C.red("refused: that command looks destructive. Run it yourself if you are sure.")); return
    if not is_read_only_bash(cmd):
        if not re.match(r"^y", ask(C.yellow("run `%s`? (y/N) " % cmd)), re.I):
            print(C.dim("cancelled")); return
    sh = os.environ.get("SHELL") or "/bin/sh"
    try:
        p = subprocess.Popen([sh, "-c", cmd])
        try:
            code = p.wait(timeout=120)
        except subprocess.TimeoutExpired:
            print(C.yellow("\n(timed out after 120s, stopping)")); p.terminate(); code = p.wait()
        except KeyboardInterrupt:
            p.send_signal(signal.SIGINT); code = p.wait()
        if code:
            print(C.dim("exit %s" % code))
    except OSError as e:
        print(C.red("error: %s" % e))


def handle(text, ctx):
    parts = text.strip().split(None, 1)
    name = parts[0]
    arg = parts[1].strip() if len(parts) > 1 else ""
    cfg = ctx["cfg"]
    if name in ("/help", "/?"):
        help_(); return True
    if name in ("/exit", "/quit", "/q"):
        ctx["quit"](); return True
    if name == "/cancel":
        print(C.dim("press Ctrl-C while a turn is running to cancel it")); return True
    if name == "/reset":
        ctx["reset"](); print(C.dim("✓ conversation cleared")); return True
    if name == "/sessions":
        l = list_sessions(10)
        if not l:
            print(C.dim("no saved sessions yet"))
        for s in l:
            print("  %s  %s  %s" % (C.cyan(s["id"]), C.dim(rel_time(s.get("updatedAt") or s.get("createdAt"))), (s.get("firstMessage") or "")[:60]))
        if l:
            print(C.dim("  resume one with /resume <id>"))
        return True
    if name == "/resume":
        sid = arg or store.latest_session_id()
        if not sid:
            print(C.yellow("no session to resume")); return True
        if not ctx["resume"](sid):
            print(C.yellow("could not find session: %s" % sid))
        return True
    if name == "/provider":
        p = _pick_provider(load())
        if not p:
            return True
        c = load(); c["provider"] = p; c["model"] = default_model(p) or c["model"]; save(c); cfg.update(c)
        print(C.green("✓ provider=%s  model=%s" % (p, c["model"])))
        if not has_key(c, p):
            print(C.yellow("no key for %s yet: use /key" % p))
        return True
    if name == "/model":
        c = load(); m = _pick_model(c["provider"], c["model"])
        if not m:
            return True
        c["model"] = m; save(c); cfg.update(c); print(C.green("✓ model=%s" % m)); return True
    if name == "/key":
        p = arg or _pick_provider(load())
        if not p:
            return True
        if p not in PROVIDERS:
            print(C.yellow("unknown provider: %s" % p)); return True
        ask_key(p); cfg.update(load()); return True
    if name == "/baseurl":
        if not arg:
            print(C.dim("base url: %s" % (load().get("baseUrl") or "(none)"))); return True
        if not re.match(r"^https?://", arg, re.I):
            print(C.yellow("must start with http:// or https://")); return True
        c = load(); c["baseUrl"] = arg; save(c); cfg.update(c); print(C.green("✓ base url saved")); return True
    if name == "/system":
        c = load()
        if not arg:
            print(C.dim("custom prompt: " + c["systemPrompt"][:200] if c.get("systemPrompt") else "using the built-in prompt")); return True
        c["systemPrompt"] = "" if arg == "default" else arg; save(c); cfg.update(c)
        print(C.green("✓ back to the built-in prompt" if arg == "default" else "✓ custom prompt saved")); return True
    if name == "/mode":
        if not arg:
            print(C.dim("mode: %s  (options: %s)" % (ctx["state"].get("mode", "default"), ", ".join(store.MODES)))); return True
        if arg not in store.MODES:
            print(C.yellow("unknown mode: %s  (options: %s)" % (arg, ", ".join(store.MODES)))); return True
        ctx["state"]["mode"] = arg; print(C.green("✓ mode=%s" % arg)); return True
    if name == "/setup":
        c = load(); p = _pick_provider(c)
        if not p:
            return True
        c["provider"] = p; save(c)
        if not has_key(load(), p):
            ask_key(p)
        c2 = load(); m = _pick_model(p, default_model(p))
        if m:
            c2["model"] = m
        save(c2); cfg.update(c2)
        print(C.green("✓ provider=%s  model=%s" % (c2["provider"], c2["model"]))); return True
    if name == "/cd":
        if not arg:
            print(C.yellow("Usage: /cd <path>")); return True
        try:
            os.chdir(os.path.abspath(os.path.expanduser(arg))); print(C.dim(os.getcwd()))
        except OSError as e:
            print(C.red("cannot cd: %s" % e))
        return True
    if name == "/pwd":
        print(os.getcwd()); return True
    if name == "/show":
        import json
        c = load()
        print(json.dumps({"provider": c["provider"], "model": c["model"], "baseUrl": c.get("baseUrl") or "", "maxSteps": c.get("maxSteps"),
                          "maxTokens": c.get("maxTokens"), "mode": ctx["state"].get("mode", "default"),
                          "keys": {p: "••••" for p in PROVIDERS if has_key(c, p)}, "config": store.CONFIG_PATH}, indent=2))
        return True
    if name == "/clear":
        print("\x1b[2J\x1b[H", end=""); return True
    if name == "/run":
        _run_shell(arg); return True
    return False


def palette(ctx):
    items = [{"id": c.split()[0], "label": c.split()[0], "note": d} for _, rows in HELP for c, d in rows if c.startswith("/")]
    s = pick("Commands", items, 0)
    if s:
        handle(s["id"], ctx)
