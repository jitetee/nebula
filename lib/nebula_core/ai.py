"""One AI backend for all of Nebula.

  ant   your own provider + key (OpenRouter, OpenAI, Anthropic, ...), set up once in `ant`
  tgpt  the free keyless fallback
  auto  (default) ant when it has a key, otherwise tgpt

Choose with `nebula ai backend ant|tgpt|auto`, or NEBULA_AI_BACKEND. Used by the shell (ask, chat, explain,
fix, ...), jtlearn's tutor, plugins, and `python3 -m nebula_core.ai "question"`.
"""
import os
import shutil
import subprocess
import sys

from . import paths

CHOICES = ("auto", "ant", "tgpt")


class AIError(Exception):
    pass


def _ant():
    d = os.path.join(paths.home(), "apps", "ant")
    if d not in sys.path:
        sys.path.insert(0, d)
    import ant.store as store  # noqa
    return store


def ant_ready():
    try:
        s = _ant()
        c = s.load()
        return bool(s.has_key(c, c["provider"]))
    except Exception:
        return False


def tgpt_path():
    return shutil.which("tgpt")


def setting():
    v = os.environ.get("NEBULA_AI_BACKEND", "").strip().lower()
    if not v:
        try:
            v = open(os.path.join(paths.cfg(), "ai.backend"), encoding="utf-8").read().strip().lower()
        except OSError:
            v = ""
    return v if v in CHOICES else "auto"


def backend_name():
    """The backend that will actually answer: 'ant', 'tgpt' or 'none'."""
    s = setting()
    if s == "ant":
        return "ant" if ant_ready() else ("tgpt" if tgpt_path() else "none")
    if s == "tgpt":
        return "tgpt" if tgpt_path() else ("ant" if ant_ready() else "none")
    if ant_ready():
        return "ant"
    return "tgpt" if tgpt_path() else "none"


def set_backend(v):
    if v not in CHOICES:
        raise AIError("backend must be one of: " + ", ".join(CHOICES))
    os.makedirs(paths.cfg(), exist_ok=True)
    with open(os.path.join(paths.cfg(), "ai.backend"), "w", encoding="utf-8") as f:
        f.write(v + "\n")


def describe():
    b = backend_name()
    if b == "ant":
        c = _ant().load()
        return "ant (%s, %s)" % (c.get("provider"), c.get("model"))
    return {"tgpt": "tgpt (free)", "none": "none: run `ant` and use /setup, or install tgpt"}[b]


def _tgpt(prompt, system, timeout):
    exe = tgpt_path()
    if not exe:
        raise AIError("tgpt is not installed")
    for flags in (["-q"], []):
        cmd = [exe] + flags + (["-preprompt", system] if system else []) + [prompt]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise AIError("tgpt timed out")
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    raise AIError("tgpt gave no answer")


def ask(prompt, system="", timeout=120):
    """Answer one prompt with the chosen backend. Raises AIError when nothing is available."""
    b = backend_name()
    if b == "none":
        raise AIError("no AI is set up: run `ant` and use /setup, or install tgpt")
    if b == "ant":
        try:
            _ant()
            from ant.rpc import ask_once
            return ask_once(prompt, system or None)
        except Exception as e:
            if setting() == "ant" or not tgpt_path():
                raise AIError(str(e))
    return _tgpt(prompt, system, timeout)


def main(argv):
    if argv and argv[0] in ("status", "describe"):
        print("backend: %s   (setting: %s)" % (describe(), setting()))
        return 0
    if argv and argv[0] == "backend-name":
        print(backend_name())
        return 0
    if argv and argv[0] == "backend":
        if len(argv) == 1:
            print(setting())
            return 0
        try:
            set_backend(argv[1])
        except AIError as e:
            print(e, file=sys.stderr)
            return 2
        print("AI backend: %s -> now using %s" % (argv[1], describe()))
        return 0
    system = ""
    if argv[:1] == ["--system"] and len(argv) >= 2:
        system, argv = argv[1], argv[2:]
    prompt = " ".join(argv).strip() or sys.stdin.read().strip()
    if not prompt:
        print("usage: python3 -m nebula_core.ai [--system TEXT] <prompt> | status | backend [auto|ant|tgpt]", file=sys.stderr)
        return 2
    try:
        print(ask(prompt, system))
        return 0
    except AIError as e:
        print("ai: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
