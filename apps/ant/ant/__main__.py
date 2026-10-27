"""ant entry point: python3 -m ant [-c | --session ID | -h]"""
import os
import re
import sys
import time

from . import VERSION, store, ui, commands
from .agent import run_turn
from .store import PROVIDERS, has_key, load, save, set_key, list_for, default_model
from .picker import pick, ask
from .theme import T
from .ui import C

try:
    import readline  # line editing + history (stdlib; optional)
except ImportError:  # pragma: no cover
    readline = None


def system_prompt():
    return f"""You are Ant, a terminal coding agent running on the user's device.
- Working directory: {os.getcwd()}
- Platform: {sys.platform} (Termux/Android-friendly)
- File tools: read_file, list_dir, glob, search.
- Edit tools: write_file (create/rewrite), edit_file (single surgical edit), apply_patch (multiple edits to one file atomically).
- Exec tools: bash, run_code (python/bash/sh), git (refuses destructive subcommands without confirm=true).
- Net tools: http_get for fetching docs or public APIs.
- Skills: call skill_list to see available playbooks, then skill_get <name> to load one — follow the loaded markdown as instructions for the current task. Skills live at ~/.ant/skills/.

ACT, DON'T HESITATE. When the user asks a question that a shell command can answer, run the command immediately — don't ask permission, don't speculate, don't suggest the user run it. Examples:
- "am I logged in to github?" → run `gh auth status`
- "is the dev server running?" → run `ps aux | grep -i node` or check the port
- "any errors in the logs?" → `tail -n 200` the log file, or `journalctl`/`logcat` if relevant
- "what python version?" → `python3 -V`
- "is X installed?" → `which X` or `command -v X`
Read-only inspection commands (`gh auth status`, `git status/log/diff/branch`, `ls`, `cat`, `which`, `env`, `ps`, `tail`, `head`, `wc`, `pwd`) auto-approve — just run them.

When a command times out, you'll see partial stdout/stderr captured up to the kill — use it. Re-run with a longer timeout_ms or a narrower invocation if needed.

Prefer reading before editing. Prefer apply_patch over multiple edit_file calls when changing several spots in one file. Be concise. After finishing a task, give a one or two sentence summary.

""" + (store.load_memory() or "")


HELP_ROWS = [("ant", "start a new session"), ("ant -c, --continue", "resume the most recent session"),
             ("ant --session <id>", "resume a specific session"), ("ant -h, --help", "show this help")]


def help_text():
    from .ui import framed_block, term_width, C
    W = term_width(40, 100)
    return framed_block("ant — terminal coding agent", [C.cyan(a.ljust(24)) + C.dim(b) for a, b in HELP_ROWS], width=W)





def parse_args(argv):
    o = {"resume": None, "cont": False, "help": False}
    i = 0
    while i < len(argv):
        t = argv[i]
        if t in ("--session", "-s"):
            i += 1
            o["resume"] = argv[i] if i < len(argv) else None
        elif t in ("-c", "--continue", "--resume"):
            o["cont"] = True
        elif t in ("-h", "--help"):
            o["help"] = True
        elif t.startswith("--session="):
            o["resume"] = t.split("=", 1)[1]
        i += 1
    return o


def ensure_setup(cfg):
    if cfg["provider"] not in PROVIDERS:
        cfg["provider"] = "openrouter"
        save(cfg)
    ids = [m["id"] for m in list_for(cfg["provider"])]
    if has_key(cfg, cfg["provider"]) and cfg.get("model") and (cfg["model"] in ids or not ids or cfg["provider"] == "generic"):
        return cfg
    print(ui.rule("first-time setup"))
    if not has_key(cfg, cfg["provider"]):
        k = ask(C.dim("Paste API key for %s (input hidden): " % cfg["provider"]), hide=True)
        if k:
            set_key(cfg["provider"], k)
            print(C.dim("saved key for %s" % cfg["provider"]))
        else:
            print(C.yellow("no key entered — you can set one later with /key"))
    cfg = load()
    if ids and cfg.get("model") not in ids:
        cfg["model"] = default_model(cfg["provider"])
    lst = list_for(cfg["provider"])
    if lst:
        sel = pick("Select model for %s" % cfg["provider"], [{"id": m["id"], "label": m["id"], "note": m["note"]} for m in lst],
                   ids.index(cfg["model"]) if cfg["model"] in ids else 0)
        if sel:
            cfg["model"] = sel["id"]
    else:
        m = ask(C.dim("Enter model id for %s: " % cfg["provider"]))
        if m:
            cfg["model"] = m
    save(cfg)
    print(C.dim("✓ provider=%s  model=%s" % (cfg["provider"], cfg["model"])))
    print("")
    return cfg


def rl_prompt(s):
    # tell readline which bytes are invisible so line editing keeps the right width
    return re.sub(r"(\x1b\[[0-9;]*m)", "\x01\\1\x02", s)


def main(argv):
    args = parse_args(argv)
    if args["help"]:
        print(help_text())
        return 0
    cfg = load()
    recent = [{"firstMessage": s.get("firstMessage", ""), "relTime": store.rel_time(s.get("updatedAt"))} for s in store.list_sessions(4)]
    resume_id = args["resume"] or (store.latest_session_id() if args["cont"] else None)
    print(ui.welcome_banner(cfg, VERSION, recent))
    print("")
    cfg = ensure_setup(cfg)
    if sys.stdout.isatty():
        sys.stdout.write("\x1b]0;ant•%s\x07" % (os.path.basename(os.getcwd()) or "/"))
    hist_file = os.path.join(store.DIR, "history")
    if readline and sys.stdin.isatty():
        try:
            readline.read_history_file(hist_file)
        except OSError:
            pass
        readline.set_history_length(500)

    S = {"history": [], "id": store.new_session_id(), "first": "", "created": int(time.time() * 1000), "mode": "default", "quit": False}
    stats = {"tokens": 0, "turns": 0, "toolCalls": 0}
    t_start = time.time()

    def do_resume(sid):
        s = store.load_session(sid)
        if not s:
            return False
        S.update(id=s["id"], history=s.get("history") or [], first=s.get("firstMessage") or "", created=s.get("createdAt") or S["created"])
        print(C.dim("↺ resumed session %s (%d messages)" % (C.cyan(S["id"]), len(S["history"]))))
        print("")
        return True

    if resume_id and not do_resume(resume_id):
        print(C.yellow("could not find session: %s" % resume_id))

    def persist(h, first_user=None):
        if not S["first"] and first_user:
            S["first"] = first_user[:120]
        store.save_session(S["id"], {"cwd": os.getcwd(), "provider": cfg["provider"], "model": cfg["model"],
                                     "history": h, "firstMessage": S["first"], "createdAt": S["created"]})

    def reset():
        S.update(history=[], id=store.new_session_id(), first="", created=int(time.time() * 1000))

    def quit_():
        S["quit"] = True

    def confirm(msg):
        return bool(re.match(r"^y", ask(C.yellow("%s (y/N) " % msg)), re.I))

    def ctx():
        return {"cfg": cfg, "state": S, "reset": reset, "resume": do_resume, "quit": quit_}

    def summary():
        print("")
        print(ui.exit_summary(S["id"], cfg["model"], cfg["provider"], os.getcwd(), stats["tokens"], (time.time() - t_start) * 1000,
                              stats["turns"], stats["toolCalls"], S["first"]))
        if sys.stdout.isatty():
            sys.stdout.write("\x1b]0;\x07")

    sigint_at = 0.0
    tty = sys.stdin.isatty()
    while not S["quit"]:
        if tty:
            print(ui.input_box_top())
        try:
            line = input(rl_prompt(ui.user_prefix()) if tty else "")
        except EOFError:
            break
        except KeyboardInterrupt:
            now = time.time()
            if now - sigint_at < 2:
                print("")
                break
            sigint_at = now
            print("\n" + C.dim("(ctrl-c again to quit)"))
            continue
        if tty:
            print(ui.input_box_bottom(cfg["model"]))
        text = line.strip()
        if not text:
            continue
        try:
            if text == "/":
                commands.palette(ctx()); continue
            if text.startswith("/"):
                if not commands.handle(text, ctx()):
                    print(C.yellow("unknown command — /help"))
                continue
            if text.startswith("!"):
                cmd = text[1:].strip()
                if not cmd:
                    print(C.yellow("Usage: !<shell command>"))
                else:
                    commands.handle("/run " + cmd, ctx())
                continue
            live = load()
            live["systemPrompt"] = live.get("systemPrompt") or system_prompt()
            live["mode"] = S["mode"]
            run_turn(live, S["history"], text, confirm, S["id"], persist, stats)
        except KeyboardInterrupt:
            print("\n" + C.yellow("(cancelled)"))
        except Exception as e:  # never crash the REPL
            print(C.red("error: %s" % e), file=sys.stderr)
    if readline and tty:
        try:
            os.makedirs(store.DIR, mode=0o700, exist_ok=True)
            readline.write_history_file(hist_file)
        except OSError:
            pass
    summary()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
