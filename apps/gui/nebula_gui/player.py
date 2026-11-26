"""Player: a touch-friendly audio player for the terminal (library, queue, seek bar, volume, shuffle/repeat).

  player [files or folders]     keys: Space pause · n/p next/prev · ←/→ seek · +/- volume · s shuffle · r repeat · / search · q quit
Plays through mpv (pkg install mpv). It finds music in your phone's Music folders when you give it nothing.
"""
import curses
import json
import os
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import time

from nebula_core import help as nhelp, icons, tui

ICO = icons.get
EXTS = (".mp3", ".m4a", ".flac", ".wav", ".ogg", ".oga", ".opus", ".aac", ".wma", ".mka", ".aiff", ".mp2")


def music_roots():
    h = os.path.expanduser("~")
    return [p for p in (os.path.join(h, "storage", "music"), os.path.join(h, "storage", "shared", "Music"), "/sdcard/Music", os.path.join(h, "Music"), "/storage/emulated/0/Music") if os.path.isdir(p)]


def scan(paths, limit=6000):
    out, seen = [], set()
    for root in paths:
        if os.path.isfile(root):
            if root.lower().endswith(EXTS) and root not in seen:
                out.append(root); seen.add(root)
            continue
        for r, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for f in sorted(files):
                p = os.path.join(r, f)
                if f.lower().endswith(EXTS) and p not in seen:
                    out.append(p); seen.add(p)
            if len(out) >= limit:
                return out
    return out


def mmss(s):
    s = int(max(0, s or 0))
    return "%d:%02d" % (s // 60, s % 60)


class MPV:
    """Thin client for mpv's JSON IPC socket."""
    def __init__(self):
        self.sock_path = os.path.join(tempfile.gettempdir(), "nebula-mpv-%d.sock" % os.getpid())
        args = ["mpv", "--no-video", "--idle=yes", "--force-window=no", "--really-quiet", "--input-ipc-server=" + self.sock_path, "--no-terminal", "--volume=70"]
        ao = os.environ.get("NEBULA_PLAYER_AO")
        if ao:
            args.append("--ao=" + ao)
        self.proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.s = None
        for _ in range(50):
            try:
                self.s = socket.socket(socket.AF_UNIX); self.s.connect(self.sock_path); self.s.settimeout(0.5); break
            except OSError:
                time.sleep(0.1)
        self.buf = b""
        self.rid = 0

    def cmd(self, *args):
        if not self.s:
            return None
        self.rid += 1
        rid = self.rid
        try:
            self.s.sendall((json.dumps({"command": list(args), "request_id": rid}) + "\n").encode())
            end = time.time() + 1.0
            while time.time() < end:
                while b"\n" in self.buf:
                    line, self.buf = self.buf.split(b"\n", 1)
                    try:
                        m = json.loads(line)
                    except ValueError:
                        continue
                    if m.get("request_id") == rid:
                        return m.get("data") if m.get("error") == "success" else None
                try:
                    d = self.s.recv(65536)
                    if not d:
                        return None
                    self.buf += d
                except socket.timeout:
                    break
        except OSError:
            return None
        return None

    def get(self, prop):
        return self.cmd("get_property", prop)

    def set(self, prop, val):
        return self.cmd("set_property", prop, val)

    def close(self):
        try:
            if self.s:
                self.s.sendall(b'{"command":["quit"]}\n')
        except OSError:
            pass
        try:
            self.proc.terminate(); self.proc.wait(timeout=1)
        except Exception:
            pass
        try:
            os.remove(self.sock_path)
        except OSError:
            pass


class Player(tui.App):
    tick_ms = 250

    def __init__(self, paths_):
        self.lib = scan(paths_ or music_roots())
        self.queue = []
        self.qi = -1
        self.view = "lib"
        self.cur, self.top = 0, 0
        self.filter = ""
        self.mpv = None
        self.pos = self.dur = 0.0
        self.paused = False
        self.vol = 70
        self.shuffle = False
        self.repeat = 0          # 0 off, 1 all, 2 one
        self.msg = ""
        self.title = ""
        self.artist = ""
        self.started = False
        self.bar = (0, 0, 0)     # y, x, w of the seek bar for clicks

    # ── backend ──
    def start(self, ui):
        if not shutil.which("mpv"):
            self.msg = "mpv is not installed. Run: pkg install mpv"
            return
        self.mpv = MPV()
        if not self.mpv.s:
            self.msg = "Could not start mpv"; self.mpv = None

    def items(self):
        src = self.queue if self.view == "queue" else self.lib
        if self.filter:
            f = self.filter.lower()
            src = [p for p in src if f in os.path.basename(p).lower() or f in os.path.dirname(p).lower()]
        return src

    def play_index(self, i):
        if not self.mpv or not (0 <= i < len(self.queue)):
            return
        self.qi = i
        self.mpv.cmd("loadfile", self.queue[i], "replace")
        self.mpv.set("pause", False)
        self.paused, self.started = False, True
        self.title = os.path.splitext(os.path.basename(self.queue[i]))[0]
        self.artist = os.path.basename(os.path.dirname(self.queue[i]))

    def play_from_list(self, i):
        src = self.items()
        if not src:
            return
        if self.view == "lib":
            self.queue = list(src)
            if self.shuffle:
                first = self.queue[i]
                random.shuffle(self.queue)
                self.queue.remove(first); self.queue.insert(0, first); i = 0
            self.play_index(i)
        else:
            self.play_index(self.queue.index(src[i]))

    def toggle(self):
        if not self.mpv:
            return
        if not self.started:
            src = self.items()
            if src:
                self.play_from_list(self.cur)
            return
        self.paused = not self.paused
        self.mpv.set("pause", self.paused)

    def nxt(self, step=1, auto=False):
        if not self.queue:
            return
        if auto and self.repeat == 2:
            return self.play_index(self.qi)
        j = self.qi + step
        if j >= len(self.queue):
            if self.repeat == 1 or not auto:
                j = 0
            else:
                self.started = False; self.pos = 0; return
        if j < 0:
            j = len(self.queue) - 1
        self.play_index(j)

    def seek(self, d):
        if self.mpv and self.started:
            self.mpv.cmd("seek", d, "relative")

    def set_vol(self, v):
        self.vol = max(0, min(130, v))
        if self.mpv:
            self.mpv.set("volume", self.vol)

    def tick(self, ui):
        if not self.mpv or not self.started:
            return
        p, d = self.mpv.get("time-pos"), self.mpv.get("duration")
        if isinstance(p, (int, float)):
            self.pos = p
        if isinstance(d, (int, float)):
            self.dur = d
        idle = self.mpv.get("idle-active")
        eof = self.mpv.get("eof-reached")
        if (idle is True or eof is True) and self.started and self.dur and self.pos >= self.dur - 1.5:
            self.nxt(1, auto=True)
        t = self.mpv.get("media-title")
        md = self.mpv.get("metadata") or {}
        if isinstance(md, dict):
            a = md.get("artist") or md.get("ARTIST")
            if a:
                self.artist = a
            tt = md.get("title") or md.get("TITLE")
            if tt:
                self.title = tt

    # ── events ──
    def key(self, ui, k):
        src = self.items()
        n = len(src)
        if k in (ord("q"), 27):
            if self.filter:
                self.filter = ""; return True
            if self.mpv:
                self.mpv.close()
            return False
        if k == ord(" "):
            self.toggle()
        elif k in (curses.KEY_DOWN, ord("j")):
            self.cur = min(n - 1, self.cur + 1)
        elif k in (curses.KEY_UP, ord("k")):
            self.cur = max(0, self.cur - 1)
        elif k == curses.KEY_NPAGE:
            self.cur = min(n - 1, self.cur + 10)
        elif k == curses.KEY_PPAGE:
            self.cur = max(0, self.cur - 10)
        elif k in tui.ENTER:
            self.play_from_list(self.cur)
        elif k == ord("n"):
            self.nxt(1)
        elif k == ord("p"):
            self.nxt(-1)
        elif k == curses.KEY_RIGHT:
            self.seek(10)
        elif k == curses.KEY_LEFT:
            self.seek(-10)
        elif k in (ord("+"), ord("=")):
            self.set_vol(self.vol + 5)
        elif k in (ord("-"), ord("_")):
            self.set_vol(self.vol - 5)
        elif k == ord("s"):
            self.shuffle = not self.shuffle; self.msg = "Shuffle " + ("on" if self.shuffle else "off")
        elif k == ord("r"):
            self.repeat = (self.repeat + 1) % 3; self.msg = "Repeat " + ["off", "all", "one"][self.repeat]
        elif k == ord("/"):
            f = ui.prompt("Search music", self.filter)
            if f is not None:
                self.filter = f; self.cur = 0
        elif k == ord("a") and n:
            p = src[self.cur]
            if p not in self.queue:
                self.queue.append(p)
            self.msg = "Added to queue"
        elif k == 9:
            self.view = "queue" if self.view == "lib" else "lib"; self.cur = 0
        elif k == ord("o"):
            d = ui.prompt("Add a folder or file", "~/storage/music" if not music_roots() else music_roots()[0])
            if d:
                found = scan([os.path.expanduser(d)])
                self.lib = found + [x for x in self.lib if x not in found]; self.msg = "%d tracks" % len(found)
        return True

    def scroll(self, ui, n):
        self.cur = max(0, min(len(self.items()) - 1, self.cur + n))

    def click(self, ui, y, x, double):
        by, bx, bw = self.bar
        if y == by and bx <= x < bx + bw and self.dur:
            self.mpv.cmd("seek", (x - bx) / max(1, bw - 1) * self.dur, "absolute") if self.mpv else None

    def row_click(self, ui, i):
        if ui.double and i == self.cur:
            self.play_from_list(i)
        else:
            self.cur = i

    # ── drawing ──
    def draw(self, ui):
        W, H = ui.w, ui.h
        ui.text(0, 0, " " * W, "bar"); ui.text(0, 1, ICO("music") + "  Player", "bar")
        ui.text(0, max(12, W - 22), ("%d tracks" % len(self.lib)).rjust(21), "bar", 21)
        # now playing card
        ui.box(1, 1, 7, W - 2, "Now playing")
        if self.started:
            ui.text(2, 3, ICO("play" if not self.paused else "pause") + "  " + self.title, "primary", W - 8)
            ui.text(3, 3, self.artist, "dim", W - 8)
        else:
            ui.text(2, 3, "Nothing playing", "dim", W - 8)
            ui.text(3, 3, self.msg or "Pick a track and press Enter or double-tap", "dim", W - 8)
        bx = 3 + 5
        bw = max(8, W - 2 * 3 - 10)
        ui.text(4, 3, mmss(self.pos), "text", 5)
        frac = (self.pos / self.dur) if self.dur else 0
        ui.bar(4, bx, bw, frac, "primary")
        ui.text(4, bx + bw + 1, mmss(self.dur), "text", 5)
        self.bar = (4, bx, bw)
        ui.region(4, bx, 1, bw, lambda: self.click(ui, 4, bx + (0), False))
        # controls
        x = 3
        for lab, cb, on in ((ICO("prev"), lambda: self.nxt(-1), False), (ICO("pause") if (self.started and not self.paused) else ICO("play"), self.toggle, True),
                            (ICO("next"), lambda: self.nxt(1), False), (ICO("shuffle"), lambda: setattr(self, "shuffle", not self.shuffle), self.shuffle),
                            (ICO("repeat") + ["", "·all", "·1"][self.repeat], lambda: setattr(self, "repeat", (self.repeat + 1) % 3), self.repeat > 0)):
            x += ui.button(6, x, lab, cb, "sel" if on and lab in (ICO("pause"), ICO("play")) else ("panel_a" if on else "panel")) + 1
        vx = max(x + 2, W - 28)
        ui.text(6, vx, ICO("volume"), "second", 2)
        ui.button(6, vx + 2, "-", lambda: self.set_vol(self.vol - 5), "panel")
        ui.bar(6, vx + 6, 12, self.vol / 130.0, "primary")
        ui.region(6, vx + 6, 1, 12, lambda: None)
        ui.button(6, vx + 19, "+", lambda: self.set_vol(self.vol + 5), "panel")
        ui.text(6, vx + 23, "%d%%" % self.vol, "dim", 5)
        # tabs
        ty = 9
        ui.fill(ty, 0, 1, W, "panel")
        x = ui.button(ty, 0, "Library", lambda: (setattr(self, "view", "lib"), setattr(self, "cur", 0)), "sel" if self.view == "lib" else "panel")
        x += ui.button(ty, x, "Queue (%d)" % len(self.queue), lambda: (setattr(self, "view", "queue"), setattr(self, "cur", 0)), "sel" if self.view == "queue" else "panel")
        ui.button(ty, x, ICO("search") + (" " + self.filter if self.filter else ""), lambda: self.key(ui, ord("/")), "panel_a" if self.filter else "panel")
        src = self.items()
        vis = H - ty - 3
        self.cur = max(0, min(self.cur, len(src) - 1))
        self.top = min(max(self.top, self.cur - vis + 1), self.cur) if (self.cur < self.top or self.cur >= self.top + vis) else self.top
        if not src:
            ui.text(ty + 2, 3, "No music found. Press o to add a folder (try ~/storage/music).", "dim", W - 6)
        for r in range(vis):
            i = self.top + r
            if i >= len(src):
                break
            p = src[i]
            playing = self.started and self.qi < len(self.queue) and self.queue[self.qi] == p
            y = ty + 1 + r
            base = "sel" if i == self.cur else ("primary" if playing else "text")
            ui.text(y, 0, " " * W, "sel" if i == self.cur else "text", W)
            ui.text(y, 1, (ICO("play") if playing else ICO("audio")), base, 2)
            ui.text(y, 4, os.path.splitext(os.path.basename(p))[0], base, W - 6 - 20)
            ui.text(y, max(4, W - 20), os.path.basename(os.path.dirname(p)), "sel" if i == self.cur else "dim", 19)
            ui.region(y, 0, 1, W, (lambda ii: (lambda: self.row_click(ui, ii)))(i))
        ui.text(H - 1, 1, "Space pause · n/p track · ←/→ seek · +/- vol · s shuffle · r repeat · Tab queue · a add · / search · q quit", "dim", W - 2)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    nhelp.maybe_help("player", argv)
    tui.run(Player([os.path.expanduser(a) for a in argv]))


if __name__ == "__main__":
    main()
