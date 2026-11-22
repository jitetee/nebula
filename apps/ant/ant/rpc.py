"""ant as a library for other tools: `python3 -m ant --rpc` (editors) and `python3 -m ant --ask "question"` (scripts).

Same provider, model, keys, memory and sessions as the interactive ant (~/.ant), so Neovim, the shell and the
terminal agent never disagree about which AI is in use. Protocol: one JSON object per line.

  in : {"id":1,"op":"hello"}
       {"id":2,"op":"ask","prompt":"...","context":{...}}                 -> one answer, no tools
       {"id":3,"op":"edit","instruction":"...","context":{...}}           -> replacement text for the selection
       {"id":4,"op":"agent","prompt":"...","cwd":"...","mode":"default"}  -> full ant agent (tools), asks to confirm
       {"op":"confirm_reply","cid":7,"ok":true}
  out: {"id":N,"type":"log","text":"..."}      progress lines (tool calls, diffs) from the agent
       {"id":N,"type":"confirm","cid":7,"message":"..."}
       {"id":N,"type":"done","text":"...","session":"..."}  or  {"id":N,"type":"error","message":"..."}
"""
import json
import os
import re
import sys
import time

from . import VERSION, store
from .agent import run_turn
from .providers import chat, ProviderError

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")
FENCE = re.compile(r"^\s*```[\w+-]*\n([\s\S]*?)\n?```\s*$")


def _base_system():
    from .__main__ import system_prompt   # same prompt + memory as the terminal agent
    return system_prompt()


def _ctx_text(c):
    c = c or {}
    parts = []
    if c.get("file"):
        parts.append("File: %s%s" % (c["file"], " (%s)" % c["filetype"] if c.get("filetype") else ""))
    if c.get("diagnostics"):
        parts.append("Diagnostics:\n" + "\n".join("- line %s: %s" % (d.get("line"), d.get("message")) for d in c["diagnostics"][:20]))
    if c.get("selection"):
        parts.append("Selected code (lines %s-%s):\n```\n%s\n```" % (c.get("start"), c.get("end"), c["selection"]))
    elif c.get("buffer"):
        parts.append("Current file (around line %s):\n```\n%s\n```" % (c.get("line"), c["buffer"]))
    return "\n\n".join(parts)


def _complete(system, user, with_tools=False):
    cfg = store.load()
    cfg["systemPrompt"] = system
    resp = chat(cfg, [{"role": "user", "content": user}], with_tools=with_tools)
    return (resp.get("content") or "").strip()


def ask_once(prompt, system=None):
    """Used by `--ask` and by shell/jtlearn helpers: one question, plain text answer."""
    return _complete(system or "You are a concise, helpful assistant inside a terminal.", prompt)


def strip_fence(text):
    m = FENCE.match(text)
    return m.group(1) if m else text


class Server:
    def __init__(self, inp, out):
        self.inp, self.out = inp, out
        self.cid = 0

    def send(self, **kw):
        self.out.write(json.dumps(kw, ensure_ascii=False) + "\n")
        self.out.flush()

    def read(self):
        line = self.inp.readline()
        if not line:
            raise EOFError
        try:
            return json.loads(line)
        except ValueError:
            return {}

    def run(self):
        while True:
            try:
                req = self.read()
            except EOFError:
                return 0
            if req.get("op") in (None, "confirm_reply"):
                continue
            rid = req.get("id")
            try:
                getattr(self, "op_" + req["op"])(rid, req)
            except AttributeError:
                self.send(id=rid, type="error", message="unknown op: %s" % req.get("op"))
            except ProviderError as e:
                self.send(id=rid, type="error", message=str(e))
            except Exception as e:  # never die: the editor keeps this process for the whole session
                self.send(id=rid, type="error", message="%s: %s" % (type(e).__name__, e))

    # ── ops ──
    def op_hello(self, rid, req):
        cfg = store.load()
        self.send(id=rid, type="done", text="ok", version=VERSION, provider=cfg["provider"], model=cfg["model"],
                  has_key=store.has_key(cfg, cfg["provider"]))

    def op_ask(self, rid, req):
        system = _base_system() + "\n\nYou are answering inside a code editor. Be concise. Use markdown; keep code in fenced blocks."
        user = (_ctx_text(req.get("context")) + "\n\n" if req.get("context") else "") + req.get("prompt", "")
        self.send(id=rid, type="done", text=_complete(system, user))

    def op_edit(self, rid, req):
        c = req.get("context") or {}
        system = ("You rewrite code inside an editor. Reply with ONLY the new text that replaces the selected code: "
                  "no explanation, no markdown fences, keep the indentation style and keep unrelated lines unchanged.")
        user = "%s\n\nInstruction: %s" % (_ctx_text(c), req.get("instruction", ""))
        self.send(id=rid, type="done", text=strip_fence(_complete(system, user)))

    def op_agent(self, rid, req):
        cwd = req.get("cwd")
        if cwd and os.path.isdir(cwd):
            os.chdir(cwd)
        cfg = store.load()
        cfg["systemPrompt"] = cfg.get("systemPrompt") or _base_system()
        cfg["mode"] = req.get("mode") or "default"
        sid = req.get("session") or store.new_session_id()
        created, first = int(time.time() * 1000), (req.get("prompt") or "")[:120]
        history = []

        def persist(h, first_user=None):   # same format as the terminal ant: `ant -c` resumes it
            store.save_session(sid, {"cwd": os.getcwd(), "provider": cfg["provider"], "model": cfg["model"],
                                     "history": h, "firstMessage": first, "createdAt": created})

        def confirm(msg):
            self.cid += 1
            self.send(id=rid, type="confirm", cid=self.cid, message=ANSI.sub("", msg).strip())
            while True:
                r = self.read()
                if r.get("op") == "confirm_reply" and r.get("cid") == self.cid:
                    return bool(r.get("ok"))

        class Log:                           # run_turn prints for humans; forward each line to the editor
            buf = ""
            def write(s, t):
                s.buf += t
                while "\n" in s.buf:
                    line, s.buf = s.buf.split("\n", 1)
                    line = ANSI.sub("", line).rstrip()
                    if line.strip():
                        self.send(id=rid, type="log", text=line)
                return len(t)
            def flush(s): pass
            def isatty(s): return False

        prompt = req.get("prompt", "")
        if req.get("context"):
            prompt = _ctx_text(req["context"]) + "\n\n" + prompt
        real_out, real_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = Log()
        try:
            run_turn(cfg, history, prompt, confirm, sid, persist, {})
        finally:
            sys.stdout, sys.stderr = real_out, real_err
        final = ""
        for m in reversed(history):
            if m.get("role") == "assistant" and (m.get("content") or "").strip():
                final = re.sub(r"<thought>[\s\S]*?</thought>", "", m["content"]).strip()
                break
        self.send(id=rid, type="done", text=final, session=sid)


def serve():
    # keep the real stdout for the protocol; anything else that prints goes to stderr
    out = sys.stdout
    sys.stdout = sys.stderr
    return Server(sys.stdin, out).run()


def ask_cli(argv):
    prompt = " ".join(argv).strip() or sys.stdin.read().strip()
    if not prompt:
        print("usage: ant --ask <question>", file=sys.stderr)
        return 2
    try:
        print(ask_once(prompt))
        return 0
    except ProviderError as e:
        print("ant: %s" % e, file=sys.stderr)
        return 1
