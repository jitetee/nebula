"""Arrow-key picker (numbered fallback when not a TTY) and prompts."""
import getpass
import os
import sys

from .ui import C


def pick(title, items, initial=0):
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return _numbered(title, items, initial)
    try:
        import termios, tty
    except ImportError:
        return _numbered(title, items, initial)
    idx = max(0, min(initial, len(items) - 1))
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    first = True
    w = sys.stdout.write

    def draw():
        nonlocal first
        if not first:
            w("\x1b[%dA" % (len(items) + 2))
        first = False
        w("\x1b[J%s\n" % C.bold(title))
        w(C.dim("  ↑/↓ select · enter to confirm · esc to cancel") + "\n")
        for i, it in enumerate(items):
            label, note = it.get("label") or it.get("id") or "", it.get("note") or ""
            n = "  " + C.dim(note) if note else ""
            w(("%s %s%s" % (C.green("❯"), C.cyan(label), n) if i == idx else "  %s%s" % (label, n)) + "\n")
        sys.stdout.flush()

    try:
        tty.setcbreak(fd)
        draw()
        while True:
            ch = os.read(fd, 1)
            if ch == b"\x1b":
                import select
                if select.select([fd], [], [], 0.05)[0]:
                    seq = os.read(fd, 2)
                    if seq == b"[A":
                        idx = (idx - 1) % len(items); draw()
                    elif seq == b"[B":
                        idx = (idx + 1) % len(items); draw()
                else:
                    return None
            elif ch in (b"k",):
                idx = (idx - 1) % len(items); draw()
            elif ch in (b"j",):
                idx = (idx + 1) % len(items); draw()
            elif ch in (b"\r", b"\n"):
                return items[idx]
            elif ch in (b"\x03", b"\x04", b""):
                return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _numbered(title, items, initial):
    print(C.bold(title))
    for i, it in enumerate(items, 1):
        note = it.get("note") or ""
        print("  %s. %s%s" % (C.cyan(str(i).rjust(2)), it.get("label") or it.get("id"), "  " + C.dim(note) if note else ""))
    try:
        ans = input(C.dim("pick [1-%d, default %d]: " % (len(items), initial + 1))).strip()
    except EOFError:
        return items[initial]
    try:
        n = int(ans)
        return items[n - 1] if 1 <= n <= len(items) else items[initial]
    except ValueError:
        return items[initial]


def ask(question, hide=False):
    try:
        if hide and sys.stdin.isatty():
            return getpass.getpass(question).strip()
        return input(question).strip()
    except EOFError:
        return ""
