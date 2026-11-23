"""The help registry, read the same way by the shell, ant, jtlearn, plugins and Neovim.

Format (assets/help.txt and <plugin>/help.txt):
  @name|Category|args|one-line summary
    indented detail lines
"""
import os
import re
import sys

from . import paths

WANT = {"-h", "--help"}


def files():
    fs = [os.path.join(paths.home(), "assets", "help.txt")]
    for d in paths.plugin_dirs():
        p = os.path.join(d, "help.txt")
        if os.path.isfile(p):
            fs.append(p)
    return fs


def load():
    """name -> {name, cat, args, summary, detail[list]}. Core entries win over plugin entries of the same name."""
    entries = {}
    for f in files():
        try:
            lines = open(f, encoding="utf-8").read().splitlines()
        except OSError:
            continue
        cur = None
        for ln in lines:
            if ln.startswith("@"):
                p = ln[1:].split("|")
                p += [""] * (4 - len(p))
                name = p[0].strip()
                cur = None if name in entries else {"name": name, "cat": p[1], "args": p[2], "summary": "|".join(p[3:]), "detail": []}
                if cur:
                    entries[name] = cur
            elif cur is not None and ln.startswith("  "):
                cur["detail"].append(ln[2:])
    return entries


def _paint(code, s, on):
    return "\x1b[%sm%s\x1b[0m" % (code, s) if on else s


def render(name, color=None, entries=None):
    e = (entries or load()).get(name)
    if not e:
        return None
    on = sys.stdout.isatty() and "NO_COLOR" not in os.environ if color is None else color
    out = ["", "%s %s" % (_paint("1", name, on), _paint("32", e["args"], on)), _paint("2", e["summary"], on), ""]
    out += ["  " + d for d in e["detail"]]
    return "\n".join(out) + "\n"


def listing(entries=None):
    by = {}
    for e in (entries or load()).values():
        by.setdefault(e["cat"], []).append(e)
    return by


def maybe_help(name, argv, out=None):
    """Call first thing in any Nebula tool: `tool --help` / `-h` prints the registry entry and exits."""
    if len(argv) == 1 and argv[0] in WANT:
        txt = render(name)
        if txt:
            (out or sys.stdout).write(txt)
            sys.exit(0)


def main(argv):
    if not argv or argv[0] in ("--list", "list"):
        for cat, es in sorted(listing().items()):
            print("%s:" % cat)
            for e in sorted(es, key=lambda x: x["name"]):
                print("  %-12s %s" % (e["name"], e["summary"]))
        return 0
    if argv[0] == "--names":
        print(" ".join(sorted(load())))
        return 0
    if argv[0] in ("--search", "search"):
        w = " ".join(argv[1:]).lower()
        for e in sorted(load().values(), key=lambda x: x["name"]):
            if w in (e["name"] + " " + e["summary"] + " " + " ".join(e["detail"])).lower():
                print("  %-12s %s" % (e["name"], e["summary"]))
        return 0
    txt = render(argv[0])
    if txt is None:
        print("No help for '%s'. Try: nebula help search %s" % (argv[0], argv[0]), file=sys.stderr)
        return 1
    sys.stdout.write(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
