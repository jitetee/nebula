"""Nebula GUI: a tile launcher for everything (tap a tile or press its number).  Run: gui"""
import curses
import os
import shutil
import subprocess
import sys
import time

from nebula_core import ai, help as nhelp, icons, paths, tui

ICO = icons.get

TILES = [  # (icon, title, description, nebula command)
    ("folder", "Files", "browse, copy, trash", "files"),
    ("cpu", "Monitor", "CPU, memory, battery", "monitor"),
    ("music", "Player", "play your music", "player"),
    ("download", "Save media", "video/audio from links", "svn"),
    ("terminal", "Code", "Neovim editor", "nv"),
    ("bolt", "Ant", "AI coding agent", "ant"),
    ("star", "Learn", "jtlearn tutor", "jtlearn"),
    ("branch", "Git", "commit, branch, merge", "gitx"),
    ("github", "GitHub", "repos: create, edit, delete", "repo"),
    ("cloud", "Firebase", "deploy hosting, rules", "fire"),
    ("user", "Accounts", "who am I logged in as", "accounts"),
    ("gear", "Palette", "colours everywhere", "palette"),
]


def nebula_bin():
    return os.path.join(paths.home(), "bin", "nebula")


class Launcher(tui.App):
    tick_ms = 1000

    def __init__(self):
        self.cur = 0
        self.branch = ""
        self.cols = 2
        self.msg = ""

    def git_branch(self):
        try:
            return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=2).stdout.strip()
        except Exception:
            return ""

    def run_cmd(self, ui, cmd):
        env = dict(os.environ, NEBULA_HOME=paths.home(), NEBULA_CFG=paths.cfg())
        def go():
            subprocess.call(["bash", nebula_bin(), cmd], env=env)
            input("\nPress Enter to return to Nebula GUI ")
        if cmd in ("files", "monitor", "player"):
            ui.suspend(lambda: subprocess.call(["bash", nebula_bin(), cmd], env=env))
        else:
            ui.suspend(go)

    def key(self, ui, k):
        n = len(TILES)
        if k in (ord("q"), 27):
            return False
        if k in (curses.KEY_RIGHT, ord("l")):
            self.cur = min(n - 1, self.cur + 1)
        elif k in (curses.KEY_LEFT, ord("h")):
            self.cur = max(0, self.cur - 1)
        elif k in (curses.KEY_DOWN, ord("j")):
            self.cur = min(n - 1, self.cur + self.cols)
        elif k in (curses.KEY_UP, ord("k")):
            self.cur = max(0, self.cur - self.cols)
        elif k in tui.ENTER:
            self.run_cmd(ui, TILES[self.cur][3])
        elif ord("1") <= k <= ord("9") and k - ord("1") < n:
            self.run_cmd(ui, TILES[k - ord("1")][3])
        elif k == ord("0") and n >= 10:
            self.run_cmd(ui, TILES[9][3])
        elif k == ord("?"):
            ui.pager("Nebula GUI", (nhelp.render("gui", color=False) or "").split("\n"))
        return True

    def tick(self, ui):
        pass

    def draw(self, ui):
        W, H = ui.w, ui.h
        ui.text(0, 0, " " * W, "bar"); ui.text(0, 1, ICO("logo") + "  Nebula", "bar")
        ui.text(0, max(12, W - 22), time.strftime("%a %d %b  %H:%M").rjust(21), "bar", 21)
        ver = ""
        try:
            ver = open(os.path.join(paths.home(), "VERSION")).read().strip()
        except OSError:
            pass
        self.branch = self.branch or self.git_branch()
        st = "v%s  ·  AI: %s" % (ver, ai.describe().split(" (")[0]) + (("  ·  %s %s" % (ICO("branch"), self.branch)) if self.branch else "")
        ui.text(2, 2, "Good %s." % ("morning" if time.localtime().tm_hour < 12 else "afternoon" if time.localtime().tm_hour < 18 else "evening"), "primary")
        ui.text(3, 2, st, "dim", W - 4)
        self.cols = 2 if W < 70 else 3
        pad = 2
        tw = (W - pad * 2 - (self.cols - 1)) // self.cols
        th = 4
        y0 = 5
        for i, (ic, title, desc, cmd) in enumerate(TILES):
            r, c = divmod(i, self.cols)
            y, x = y0 + r * (th + 0), pad + c * (tw + 1)
            if y + th > H - 2:
                break
            sel = i == self.cur
            ui.box(y, x, th, tw, "", "primary" if sel else "border")
            ui.text(y + 1, x + 2, "%s  %s" % (ICO(ic), title), "primary" if sel else "text", tw - 4)
            ui.text(y + 2, x + 2, desc, "dim", tw - 4)
            ui.text(y, x + tw - 4, str(i + 1) if i < 9 else "0" if i == 9 else "", "dim", 3)
            ui.region(y, x, th, tw, (lambda ii: (lambda: (setattr(self, "cur", ii), self.run_cmd(ui, TILES[ii][3]))))(i))
        ui.text(H - 1, 1, "tap a tile or press its number · arrows + Enter · ? help · q quit", "dim", W - 2)

    def click(self, ui, y, x, double):
        pass


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    nhelp.maybe_help("gui", argv)
    tui.run(Launcher())


if __name__ == "__main__":
    main()
