"""Where things are. Every tool asks here instead of guessing."""
import os

_LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def home():
    return os.environ.get("NEBULA_HOME") or os.path.dirname(_LIB)


def cfg():
    return os.environ.get("NEBULA_CFG") or os.path.join(home(), "data")


def disabled_plugins():
    try:
        with open(os.path.join(cfg(), "plugins.disabled"), encoding="utf-8") as f:
            return {l.strip() for l in f if l.strip() and not l.startswith("#")}
    except OSError:
        return set()


def plugin_dirs(include_disabled=False):
    """Bundled plugins (plugins/) first, then yours ($NEBULA_CFG/plugins). Folder name = plugin name."""
    off = set() if include_disabled else disabled_plugins()
    out = []
    for root in (os.path.join(home(), "plugins"), os.path.join(cfg(), "plugins")):
        try:
            names = sorted(os.listdir(root))
        except OSError:
            continue
        for n in names:
            d = os.path.join(root, n)
            if os.path.isdir(d) and not n.startswith((".", "_")) and n not in off:
                out.append(d)
    return out
