"""The agent loop: model -> tools -> model, with approvals by mode."""
import os
import re
import sys
import threading
import time

from . import tools, context, store
from .providers import chat
from .theme import T
from . import ui
from .ui import C


class Spinner:
    FR = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, label, getter):
        self.label, self.getter = label, getter
        self.tty = sys.stdout.isatty()
        self._stop = threading.Event()
        self.t = None

    def __enter__(self):
        if not self.tty:
            print(self.label)
            return self
        sys.stdout.write("\x1b[?25l")

        def run():
            i = 0
            while not self._stop.wait(0.08):
                tk, pct = self.getter()
                extra = " · ".join(x for x in ("{:,} tok".format(tk) if tk else "", "ctx %d%%" % pct) if x)
                sys.stdout.write("\r\x1b[2K%s %s... %s" % (T.accent(self.FR[i % 10]), self.label, T.muted(extra)))
                sys.stdout.flush()
                i += 1
        self.t = threading.Thread(target=run, daemon=True)
        self.t.start()
        return self

    def __exit__(self, *a):
        if self.t:
            self._stop.set()
            self.t.join()
            sys.stdout.write("\r\x1b[2K\x1b[?25h")
            sys.stdout.flush()
        return False


def run_turn(cfg, history, user_input, ask_confirm, session_id=None, on_persist=None, stats=None):
    """Returns nothing; Ctrl-C (KeyboardInterrupt) inside is reported as cancelled."""
    history.append({"role": "user", "content": user_input})
    if on_persist:
        try: on_persist(history, user_input)
        except Exception: pass
    max_steps = cfg.get("maxSteps") or 25
    start = time.time()
    used_total = 0
    if stats is not None:
        stats["turns"] = stats.get("turns", 0) + 1
    budget, limit = context.working_budget(cfg["model"]), context.model_limit(cfg["model"])
    sysp = cfg.get("systemPrompt") or ""
    try:
        for step in range(max_steps):
            tr = context.trim_history(history, sysp, budget)
            if tr["trimmed"] > 0:
                history[:] = tr["history"]
                print(C.dim("  ↺ trimmed %d old message%s to fit %s-token window (%s → %s tok)" % (
                    tr["trimmed"], "" if tr["trimmed"] == 1 else "s", "{:,}".format(limit), "{:,}".format(tr["before"]), "{:,}".format(tr["after"]))))
            pct = min(100, round(tr["after"] / limit * 100))
            resp = None
            try:
                with Spinner("thinking", lambda: (used_total, pct)):
                    resp = chat(cfg, history)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                if context.is_context_error(e):
                    print(C.yellow("  ⚠ provider rejected: context too large — auto-compacting and retrying"))
                    er = context.emergency_trim(history, sysp, cfg["model"])
                    history[:] = er["history"]
                    print(C.dim("  ↺ compacted to {:,} tok".format(er["after"])))
                    try:
                        with Spinner("retrying", lambda: (used_total, 0)):
                            resp = chat(cfg, history)
                    except KeyboardInterrupt:
                        raise
                    except Exception as e2:
                        print(C.red("✗ provider error after retry: %s" % e2), file=sys.stderr)
                        print(C.dim("  try /reset to clear history, or /model to switch to a larger-window model"), file=sys.stderr)
                        return
                else:
                    print(C.red("✗ provider error: %s" % e), file=sys.stderr)
                    return
            used = (resp.get("usage") or {}).get("total_tokens") or 0
            used_total += used
            if stats is not None:
                stats["tokens"] = stats.get("tokens", 0) + used
            content = resp.get("content") or ""
            if content.strip():
                for m in re.findall(r"<thought>([\s\S]*?)</thought>", content):
                    print(ui.thought_block(m))
                content = re.sub(r"<thought>[\s\S]*?</thought>", "", content).strip()
                if content:
                    print("")
                    print(ui.assistant_block(content))
            calls = resp.get("tool_calls") or []
            history.append({"role": "assistant", "content": content, "tool_calls": calls})
            if not calls:
                if on_persist:
                    try: on_persist(history)
                    except Exception: pass
                print(ui.status_line(used_total, (time.time() - start) * 1000))
                return
            for call in calls:
                _do_call(call, step, cfg, history, ask_confirm, stats)
                if on_persist:
                    try: on_persist(history)
                    except Exception: pass
        print(C.yellow("(reached max %d steps)" % max_steps), file=sys.stderr)
        print(ui.status_line(used_total, (time.time() - start) * 1000))
    except KeyboardInterrupt:
        # keep history valid: every tool_call needs a tool result
        _close_dangling(history)
        print("\n" + C.yellow("(cancelled)"))
        if on_persist:
            try: on_persist(history)
            except Exception: pass


def _close_dangling(history):
    for i in range(len(history) - 1, -1, -1):
        m = history[i]
        if m.get("role") == "assistant":
            done = {x.get("tool_call_id") for x in history[i + 1:] if x.get("role") == "tool"}
            for tc in m.get("tool_calls") or []:
                if tc.get("id") not in done:
                    history.append({"role": "tool", "tool_call_id": tc.get("id"), "name": tc.get("name"),
                                    "content": "cancelled by user", "is_error": True})
            return


def _do_call(call, step, cfg, history, ask_confirm, stats):
    name, args = call.get("name"), call.get("args") or {}
    print("")
    print(ui.tool_header(name, tools.summarize_args(name, args)))
    if stats is not None:
        stats["toolCalls"] = stats.get("toolCalls", 0) + 1
    mode = cfg.get("mode") or "default"
    is_write = name in ("write_file", "edit_file", "apply_patch", "mkdir")
    diffable = name in ("write_file", "edit_file", "apply_patch")
    before = ""
    if diffable and args.get("path"):
        try:
            p = tools._abs(args["path"])
            before = tools._read(p) if os.path.exists(p) else ""
        except Exception:
            pass
    t0 = time.time()
    result, is_error = None, False
    if not tools.is_read_only_call(name, args):
        if mode == "yolo" or (mode == "acceptEdits" and is_write):
            pass
        elif mode == "plan":
            result, is_error = "blocked: plan mode is read-only — propose a plan first, then ask the user to switch modes", True
            print("  " + T.muted("└─ ") + C.yellow("blocked (plan mode)"))
        elif not ask_confirm("  %s" % C.yellow("▸ approve?")):
            result, is_error = "user denied this action", True
            print("  " + T.muted("└─ ") + C.yellow("skipped"))
    if result is None:
        try:
            result = tools.execute(name, args, cfg)
        except KeyboardInterrupt:
            history.append({"role": "tool", "tool_call_id": call.get("id") or "%s-%d" % (name, step), "name": name,
                            "content": "cancelled by user", "is_error": True})
            raise
        except Exception as e:
            result, is_error = "error: %s" % e, True
    ms = round((time.time() - t0) * 1000)
    if not is_error and diffable and args.get("path"):
        try:
            after = tools._read(tools._abs(args["path"]))
        except Exception:
            after = ""
        d = ui.diff_block(before, after, ui.home_short(args["path"]))
        print("\n".join("  " + l for l in d.split("\n")))
        print("  " + T.muted("└─ done in %dms" % ms))
    elif not is_error and name in ("bash", "run_code"):
        print(ui.tool_result_lines(ui.compact_output(result)))
        print("  " + T.muted("└─ exit · %dms" % ms))
    elif is_error:
        print("  " + T.muted("└─ ") + T.error(str(result).split("\n")[0]))
    else:
        print(ui.tool_result_lines(result))
    history.append({"role": "tool", "tool_call_id": call.get("id") or "%s-%d" % (name, step), "name": name,
                    "content": result if isinstance(result, str) else str(result), "is_error": is_error})
