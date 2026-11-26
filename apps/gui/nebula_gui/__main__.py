"""python3 -m nebula_gui [files|monitor|player|launcher] [args]"""
import sys

from nebula_core import help as nhelp

TOOLS = {"files": "nebula_gui.files", "monitor": "nebula_gui.monitor", "player": "nebula_gui.player", "launcher": "nebula_gui.launcher", "gui": "nebula_gui.launcher"}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help", "?"):
        print("Nebula GUI apps (mouse/touch + keyboard):")
        for n in ("files", "monitor", "player", "gui"):
            e = nhelp.load().get(n)
            print("  %-9s %s" % (n, e["summary"] if e else ""))
        print("\nRun one:  python3 -m nebula_gui <name>   or   nebula <name>")
        return 0
    name = argv[0]
    if name not in TOOLS:
        print("unknown GUI app: %s" % name, file=sys.stderr)
        return 2
    import importlib
    return importlib.import_module(TOOLS[name]).main(argv[1:]) or 0


if __name__ == "__main__":
    sys.exit(main())
