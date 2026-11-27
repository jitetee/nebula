#!/usr/bin/env python3
"""Render Nebula's key screens at phone width and flag layout bugs (broken boxes, wrapped frames).

  python3 tools/gallery.py --check            only look for problems (needs: pip install pyte)  — CI runs this
  python3 tools/gallery.py --png out/         also save a PNG per screen (needs: pillow, fonttools; font = assets/fonts/nebula.ttf)
  python3 tools/gallery.py --cols 40 --only help,ant     other width / some scenes

Add a screen: append to SCENES. Exit code 1 when a problem is found.
"""
import argparse, fcntl, os, pty, select, struct, sys, termios, time

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(NEBULA_HOME=HOME, NEBULA_NO_AUTH="1", NEBULA_VOICE="0", NEBULA_SOUNDS="0", TERM="xterm-256color", COLORTERM="truecolor")
N = ["bash", os.path.join(HOME, "bin", "nebula")]
SCENES = {   # name: (command, seconds to wait)
    "help":     (N + ["help"], 3),
    "help-cmd": (N + ["help", "backup"], 3),
    "doctor":   (N + ["doctor"], 25),
    "palette":  (N + ["palette"], 3),
    "plugins":  (N + ["plugin", "list"], 3),
    "ai":       (N + ["ai", "status"], 3),
    "check":    (N + ["check"], 20),
    "about":    (N + ["about"], 4),
    "settings": (N + ["settings"], 4),
    "launcher": (["python3", "-m", "nebula_gui.launcher"], 3),
    "monitor":  (["python3", "-m", "nebula_gui.monitor"], 3),
    "files":    (["python3", "-m", "nebula_gui.files", HOME], 3),
    "svn":      (["python3", "-m", "nebula_gui.svn", "--doctor"], 4),
    "gui-help": (["python3", "-m", "nebula_gui", "--help"], 3),
    "ant-help": (["python3", "-m", "ant", "-h"], 4),
    "jt-help":  (["python3", "-m", "jtlearn", "-h"], 6),
}
LEFT, RIGHT = "│║┃|┌╭└╰├╞╔╚╠", "│║┃|┐╮┘╯┤╡╗╝╣"
SIDE, CORNER = "│║┃|", "└╰┘╯├╚╝╠┐╮╗┌╭╔"


def render(cmd, wait, cols, rows=60):
    import pyte
    screen = pyte.Screen(cols, rows); stream = pyte.ByteStream(screen)
    env = dict(os.environ, **ENV, NEBULA_CFG=os.path.join(HOME, "data-gallery"), LINES=str(rows), COLUMNS=str(cols))
    app = None
    if cmd[0] == "python3":
        app = "gui" if cmd[2].startswith("nebula_gui") else cmd[2]
        env["PYTHONPATH"] = "%s:%s" % (os.path.join(HOME, "apps", app), os.path.join(HOME, "lib"))
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(os.path.join(HOME, "apps", app) if app else HOME)
        os.execvpe(cmd[0], cmd, env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    end = time.time() + wait
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                d = os.read(fd, 65536)
            except OSError:
                break
            if not d:
                break
            stream.feed(d)
    try:
        os.kill(pid, 9)
    except OSError:
        pass
    os.waitpid(pid, 0)
    return screen


def problems(screen, cols):
    out, rows = [], []
    for y in range(screen.lines):
        line = "".join(screen.buffer[y][x].data for x in range(cols)).rstrip()
        rows.append(line)
    last = max([i for i, l in enumerate(rows) if l.strip()] or [0])
    prev_framed = False
    for y, l in enumerate(rows[: last + 1]):
        s = l.strip()
        if not s:
            prev_framed = False; continue
        framed = s[0] in LEFT and len(s) > 3
        if framed and s[-1] not in RIGHT:
            out.append("row %d: frame not closed: %s" % (y + 1, s[:60]))
        if prev_framed and not framed and s[0] not in CORNER and rows[y - 1].strip()[-1:] in SIDE and len(rows[y - 1].strip()) >= cols - 1:
            out.append("row %d: text wrapped out of a frame: %s" % (y + 1, s[:60]))
        prev_framed = framed
    return out, rows[: last + 1]


def save_png(rows, screen, path, cols):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(os.path.join(HOME, "assets", "fonts", "nebula.ttf"), 20)
    fb = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    ff = ImageFont.truetype(fb, 20) if os.path.exists(fb) else font
    cw = round(font.getlength("M")); ch = 27
    img = Image.new("RGB", (cw * cols + 20, ch * len(rows) + 20), "#0b120e"); d = ImageDraw.Draw(img)
    from fontTools.ttLib import TTFont
    have = set(TTFont(os.path.join(HOME, "assets", "fonts", "nebula.ttf")).getBestCmap())
    names = {"default": "#d7e6dc"}
    for y in range(len(rows)):
        for x in range(cols):
            c = screen.buffer[y][x]
            if not c.data.strip():
                continue
            fg = c.fg if len(c.fg) == 6 else None
            col = ("#" + fg) if fg else {"green": "#00ff87", "cyan": "#00d7af", "brown": "#ffd75f", "red": "#ff5f5f", "blue": "#00af5f", "magenta": "#afffaf"}.get(c.fg, "#d7e6dc")
            d.text((10 + x * cw, 10 + y * ch), c.data, font=font if (ord(c.data[0]) in have or ord(c.data[0]) < 128) else ff, fill=col)
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true"); ap.add_argument("--png"); ap.add_argument("--cols", type=int, default=56)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    try:
        import pyte  # noqa
    except ImportError:
        print("pip install pyte"); return 2
    want = [s for s in a.only.split(",") if s] or list(SCENES)
    bad = 0
    for name in want:
        cmd, wait = SCENES[name]
        screen = render(cmd, wait, a.cols)
        probs, rows = problems(screen, a.cols)
        print("%s %-10s %s" % ("✖" if probs else "✔", name, "%d row(s)" % len(rows)))
        for p in probs:
            print("    " + p)
        bad += len(probs)
        if a.png:
            os.makedirs(a.png, exist_ok=True)
            save_png(rows, screen, os.path.join(a.png, "%s-%d.png" % (name, a.cols)), a.cols)
    print("\n%s at %d columns" % ("%d layout problem(s)" % bad if bad else "no layout problems", a.cols))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
