#!/usr/bin/env python3
"""Drive a terminal program in a pseudo-terminal: send keys/clicks, read the screen, save a PNG. Used by the GUI tests.

    from drive import Session
    s = Session(["python3", "-m", "nebula_gui.files"], cols=80, rows=30)
    s.keys("jj"); s.click(10, 5); print(s.text()); s.png("out.png"); s.close()
"""
import fcntl, os, pty, select, struct, sys, termios, time

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMED = {"black": "#000000", "red": "#cd3131", "green": "#0dbc79", "brown": "#e5e510", "blue": "#2472c8", "magenta": "#bc3fbc", "cyan": "#11a8cd",
         "white": "#e5e5e5", "brightblack": "#666666", "brightred": "#f14c4c", "brightgreen": "#23d18b", "brightbrown": "#f5f543",
         "brightblue": "#3b8eea", "brightmagenta": "#d670d6", "brightcyan": "#29b8db", "brightwhite": "#ffffff"}


class Session:
    def __init__(self, cmd, cols=80, rows=30, cwd=None, env=None, wait=1.2):
        import pyte
        self.cols, self.rows = cols, rows
        self.screen = pyte.Screen(cols, rows); self.stream = pyte.ByteStream(self.screen)
        e = dict(os.environ, TERM="xterm-256color", COLORTERM="truecolor", LINES=str(rows), COLUMNS=str(cols), NEBULA_HOME=HOME)
        e["PYTHONPATH"] = os.path.join(HOME, "lib") + os.pathsep + os.environ.get("PYTHONPATH", "")
        e.update(env or {})
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            if cwd:
                os.chdir(cwd)
            os.execvpe(cmd[0], cmd, e)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        self.pump(wait)

    def pump(self, t=0.4):
        end = time.time() + t
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if r:
                try:
                    d = os.read(self.fd, 65536)
                except OSError:
                    return False
                if not d:
                    return False
                self.stream.feed(d)
        return True

    def send(self, data, wait=0.35):
        os.write(self.fd, data if isinstance(data, bytes) else data.encode())
        self.pump(wait)

    keys = send

    def click(self, x, y, wait=0.35):
        """1-based terminal cell → SGR mouse press + release."""
        self.send("\x1b[<0;%d;%dM\x1b[<0;%d;%dm" % (x + 1, y + 1, x + 1, y + 1), wait)

    def scroll(self, x, y, up=True, wait=0.3):
        self.send("\x1b[<%d;%d;%dM" % (64 if up else 65, x + 1, y + 1), wait)

    def lines(self):
        return ["".join(self.screen.buffer[y][x].data for x in range(self.cols)).rstrip() for y in range(self.rows)]

    def text(self):
        return "\n".join(self.lines())

    def has(self, s):
        return s in self.text()

    def alive(self):
        try:
            st = open("/proc/%d/stat" % self.pid).read().rsplit(")", 1)[1].split()[0]
            return st != "Z"
        except OSError:
            return False

    def png(self, path, font=None):
        from PIL import Image, ImageDraw, ImageFont
        from fontTools.ttLib import TTFont
        fp = font or os.path.join(HOME, "assets", "fonts", "nebula.ttf")
        f = ImageFont.truetype(fp, 20)
        fbp = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
        ff = ImageFont.truetype(fbp, 20) if os.path.exists(fbp) else f
        have = set(TTFont(fp).getBestCmap())
        cw, ch = round(f.getlength("M")), 27
        BG = "#0b120e"
        img = Image.new("RGB", (cw * self.cols + 20, ch * self.rows + 20), BG); d = ImageDraw.Draw(img)

        def col(c, default):
            if c == "default":
                return default
            if c in NAMED:
                return NAMED[c]
            if len(c) == 6:
                try:
                    int(c, 16); return "#" + c
                except ValueError:
                    pass
            return default
        for y in range(self.rows):
            for x in range(self.cols):
                c = self.screen.buffer[y][x]
                fg, bg = col(c.fg, "#d7e6dc"), col(c.bg, BG)
                if c.reverse:
                    fg, bg = bg, fg
                X, Y = 10 + x * cw, 10 + y * ch
                if bg != BG:
                    d.rectangle([X, Y, X + cw, Y + ch], fill=bg)
                if c.data.strip():
                    o = ord(c.data[0])
                    d.text((X, Y + 2), c.data, font=f if (o in have or o < 128) else ff, fill=fg)
        img.save(path)

    def close(self):
        try:
            os.write(self.fd, b"\x03"); time.sleep(0.1); os.kill(self.pid, 9)
        except OSError:
            pass
        try:
            os.waitpid(self.pid, 0)
        except ChildProcessError:
            pass
