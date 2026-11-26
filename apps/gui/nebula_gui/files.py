"""Files: a Windows-Explorer-style file manager for the terminal (mouse/touch and keyboard).

  files [folder]        open Files        keys: press ? inside
"""
import curses
import json
import mimetypes
import os
import shutil
import stat
import subprocess
import sys
import time
import uuid
import zipfile

from nebula_core import help as nhelp, icons, paths, tui

ICO = icons.get


def trash_dir():
    d = os.path.join(paths.cfg(), "trash")
    os.makedirs(d, exist_ok=True)
    return d


def places():
    h = os.path.expanduser("~")
    cands = [("Home", h, "home"), ("Storage", os.path.join(h, "storage", "shared") if os.path.isdir(os.path.join(h, "storage", "shared")) else "/sdcard", "disk"),
             ("Downloads", os.path.join(h, "storage", "downloads"), "download"), ("Pictures", os.path.join(h, "storage", "pictures"), "image"),
             ("Camera", os.path.join(h, "storage", "dcim"), "camera"), ("Music", os.path.join(h, "storage", "music"), "music"),
             ("Documents", os.path.join(h, "storage", "documents"), "text"), ("Nebula", os.environ.get("NEBULA_HOME", ""), "bolt"),
             ("Termux", os.environ.get("PREFIX", ""), "terminal"), ("Root", "/", "disk")]
    out = [(n, p, i) for n, p, i in cands if p and os.path.isdir(p)]
    out.append(("Trash", "trash:", "delete"))
    return out


def fmt_time(t):
    d = time.time() - t
    f = "%H:%M" if d < 86400 else ("%b %d" if d < 86400 * 300 else "%Y-%m")
    return time.strftime(f, time.localtime(t))


def dir_size(path, limit=200000):
    total, n = 0, 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
            n += 1
            if n > limit:
                return total, True
    return total, False


class Files(tui.App):
    def __init__(self, start=None):
        self.cwd = os.path.abspath(os.path.expanduser(start or os.getcwd()))
        self.entries, self.sel, self.cur, self.top = [], set(), 0, 0
        self.sort, self.rev, self.hidden, self.filter = "name", False, False, ""
        self.clip = None             # ("copy"|"cut", [paths])
        self.multi = False           # touch mode: a tap ticks instead of moving
        self.msg, self.msg_t = "", 0
        self.back, self.fwd = [], []
        self.trash_view = False
        self.layout = {}
        self.load()

    # ── data ──
    def say(self, m):
        self.msg, self.msg_t = m, time.time()

    def load(self):
        self.entries = []
        if self.trash_view:
            for f in sorted(os.listdir(trash_dir())):
                if f.endswith(".info"):
                    try:
                        meta = json.load(open(os.path.join(trash_dir(), f)))
                        data = os.path.join(trash_dir(), f[:-5])
                        st = os.lstat(data)
                        self.entries.append(dict(name=os.path.basename(meta["orig"]), path=data, dir=os.path.isdir(data), size=st.st_size, mtime=meta["when"], orig=meta["orig"], id=f[:-5]))
                    except (OSError, ValueError, KeyError):
                        pass
        else:
            try:
                names = os.listdir(self.cwd)
            except OSError as e:
                self.say("Cannot open: %s" % e.strerror)
                names = []
            for n in names:
                if not self.hidden and n.startswith("."):
                    continue
                if self.filter and self.filter.lower() not in n.lower():
                    continue
                p = os.path.join(self.cwd, n)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                isd = stat.S_ISDIR(st.st_mode) or (stat.S_ISLNK(st.st_mode) and os.path.isdir(p))
                self.entries.append(dict(name=n, path=p, dir=isd, size=st.st_size, mtime=st.st_mtime, link=stat.S_ISLNK(st.st_mode)))
        key = {"name": lambda e: e["name"].lower(), "size": lambda e: e["size"], "date": lambda e: e["mtime"],
               "type": lambda e: (os.path.splitext(e["name"])[1].lower(), e["name"].lower())}[self.sort]
        self.entries.sort(key=key, reverse=self.rev)
        self.entries.sort(key=lambda e: not e["dir"])
        self.cur = max(0, min(self.cur, len(self.entries) - 1))

    def cd(self, path, push=True):
        if path == "trash:":
            self.trash_view = True
            path = self.cwd
        else:
            self.trash_view = False
            path = os.path.abspath(path)
            if not os.path.isdir(path):
                self.say("Not a folder: " + path); return
        if push and (path != self.cwd or self.trash_view):
            self.back.append(self.cwd); self.fwd.clear()
        self.cwd, self.cur, self.top, self.sel, self.filter = path, 0, 0, set(), ""
        self.load()

    def go_back(self):
        if self.back:
            self.fwd.append(self.cwd); self.trash_view = False; self.cd(self.back.pop(), push=False)

    def go_fwd(self):
        if self.fwd:
            self.back.append(self.cwd); self.trash_view = False; self.cd(self.fwd.pop(), push=False)

    def up(self):
        if self.trash_view:
            self.trash_view = False; self.load()
        else:
            self.cd(os.path.dirname(self.cwd))

    def current(self):
        return self.entries[self.cur] if self.entries else None

    def targets(self):
        sel = [e for e in self.entries if e["path"] in self.sel]
        if sel:
            return sel
        c = self.current()
        return [c] if c else []

    # ── actions ──
    def open_entry(self, ui, e=None):
        e = e or self.current()
        if not e:
            return
        if e["dir"] and not self.trash_view:
            self.cd(e["path"]); return
        p = e["path"]
        kind = icons.for_path(p)
        if kind == "audio":
            env = dict(os.environ, PYTHONPATH=os.pathsep.join([os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.path.join(paths.home(), "lib")]))
            ui.suspend(lambda: subprocess.call([sys.executable, "-m", "nebula_gui.player", p], env=env))
        elif kind in ("text", "code") or (mimetypes.guess_type(p)[0] or "").startswith("text"):
            ed = os.environ.get("EDITOR") or next((x for x in ("nvim", "vim", "nano", "vi") if shutil.which(x)), None)
            if ed:
                ui.suspend(lambda: subprocess.call([ed, p])); self.load()
            else:
                self.say("No editor found (pkg install neovim)")
        else:
            op = next((x for x in ("termux-open", "xdg-open") if shutil.which(x)), None)
            if op:
                subprocess.Popen([op, p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); self.say("Opened with " + op)
            else:
                self.say("No app to open this (pkg install termux-tools)")

    def new(self, ui, folder):
        n = ui.prompt("New folder" if folder else "New file", "")
        if not n:
            return
        p = os.path.join(self.cwd, n)
        try:
            if os.path.exists(p):
                self.say("Already exists"); return
            if folder:
                os.makedirs(p)
            else:
                open(p, "a").close()
            self.load(); self.pick(n); self.say("Created " + n)
        except OSError as e:
            self.say("Failed: %s" % e.strerror)

    def pick(self, name):
        for i, e in enumerate(self.entries):
            if e["name"] == name:
                self.cur = i

    def rename(self, ui):
        e = self.current()
        if not e or self.trash_view:
            return
        n = ui.prompt("Rename", e["name"])
        if n and n != e["name"]:
            try:
                os.rename(e["path"], os.path.join(self.cwd, n)); self.load(); self.pick(n); self.say("Renamed")
            except OSError as ex:
                self.say("Failed: %s" % ex.strerror)

    def set_clip(self, op):
        t = self.targets()
        if t and not self.trash_view:
            self.clip = (op, [e["path"] for e in t]); self.say("%s %d item(s): go somewhere and press Paste" % ("Copied" if op == "copy" else "Cut", len(t)))

    def paste(self, ui):
        if not self.clip or self.trash_view:
            self.say("Nothing to paste"); return
        op, items = self.clip
        done = skipped = 0
        policy = None
        for src in items:
            if not os.path.exists(src):
                continue
            dst = os.path.join(self.cwd, os.path.basename(src))
            if os.path.abspath(src) == os.path.abspath(dst):
                if op == "cut":
                    continue
                dst = self.unique(dst)
            elif os.path.exists(dst):
                if policy is None:
                    c = ui.choose("%s already exists" % os.path.basename(dst), ["Replace", "Keep both", "Skip"])
                    policy = {0: "r", 1: "k", 2: "s"}.get(c, "s")
                if policy == "s":
                    skipped += 1; continue
                if policy == "k":
                    dst = self.unique(dst)
                else:
                    shutil.rmtree(dst) if os.path.isdir(dst) else os.remove(dst)
            try:
                if os.path.isdir(src) and os.path.commonpath([os.path.abspath(dst), os.path.abspath(src)]) == os.path.abspath(src):
                    self.say("Cannot copy a folder into itself"); continue
                if op == "copy":
                    shutil.copytree(src, dst, symlinks=True) if os.path.isdir(src) else shutil.copy2(src, dst)
                else:
                    shutil.move(src, dst)
                done += 1
            except (OSError, shutil.Error) as ex:
                self.say("Failed: %s" % ex)
        if op == "cut":
            self.clip = None
        self.load(); self.say("Pasted %d item(s)%s" % (done, ", skipped %d" % skipped if skipped else ""))

    @staticmethod
    def unique(path):
        base, ext = os.path.splitext(path)
        i = 2
        while os.path.exists(path):
            path = "%s (%d)%s" % (base, i, ext); i += 1
        return path

    def delete(self, ui, permanent=False):
        t = self.targets()
        if not t:
            return
        names = ", ".join(e["name"] for e in t[:3]) + (" …" if len(t) > 3 else "")
        if self.trash_view or permanent:
            if not ui.confirm("Delete forever?\n%d item(s): %s\nThis cannot be undone." % (len(t), names), "Delete forever", "Cancel", danger=True, typed="delete"):
                return
            for e in t:
                try:
                    shutil.rmtree(e["path"]) if os.path.isdir(e["path"]) and not os.path.islink(e["path"]) else os.remove(e["path"])
                    if self.trash_view:
                        os.remove(e["path"] + ".info")
                except OSError as ex:
                    self.say("Failed: %s" % ex.strerror)
        else:
            if not ui.confirm("Move %d item(s) to the Trash?\n%s" % (len(t), names), "Move to Trash", "Cancel", title="Delete"):
                return
            for e in t:
                tid = uuid.uuid4().hex[:12]
                try:
                    shutil.move(e["path"], os.path.join(trash_dir(), tid))
                    json.dump({"orig": e["path"], "when": time.time()}, open(os.path.join(trash_dir(), tid + ".info"), "w"))
                except (OSError, shutil.Error) as ex:
                    self.say("Failed: %s" % ex)
        self.sel.clear(); self.load(); self.say("Deleted")

    def restore(self, ui):
        for e in self.targets():
            if not self.trash_view:
                return
            dst = e["orig"]
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                dst = self.unique(dst)
            try:
                shutil.move(e["path"], dst); os.remove(e["path"] + ".info")
            except (OSError, shutil.Error) as ex:
                self.say("Failed: %s" % ex)
        self.sel.clear(); self.load(); self.say("Restored")

    def empty_trash(self, ui):
        if self.trash_view and ui.confirm("Empty the Trash?\nEverything in it is deleted forever.", "Empty Trash", "Cancel", danger=True, typed="empty"):
            shutil.rmtree(trash_dir(), ignore_errors=True); self.load(); self.say("Trash emptied")

    def info(self, ui):
        e = self.current()
        if not e:
            return
        p = e["path"]
        st = os.lstat(p)
        lines = ["Name       %s" % e["name"], "Location   %s" % os.path.dirname(p),
                 "Type       %s" % ("Folder" if e["dir"] else (mimetypes.guess_type(p)[0] or "File"))]
        if e["dir"]:
            sz, cut = dir_size(p)
            n = sum(len(f) for _, _, f in os.walk(p))
            lines.append("Size       %s%s  (%d files)" % (tui.human(sz), "+" if cut else "", n))
        else:
            lines.append("Size       %s  (%d bytes)" % (tui.human(st.st_size), st.st_size))
        lines += ["Modified   %s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                  "Accessed   %s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_atime)),
                  "Access     %s  (%s)" % (stat.filemode(st.st_mode), oct(st.st_mode & 0o777)[2:])]
        if e.get("link"):
            lines.append("Link to    %s" % os.readlink(p))
        ui.message("Properties", lines)

    def search(self, ui):
        q = ui.prompt("Search in " + os.path.basename(self.cwd or "/"), "", "searches this folder and everything inside it")
        if not q:
            return
        found = []
        for root, dirs, files in os.walk(self.cwd):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for n in dirs + files:
                if q.lower() in n.lower():
                    found.append(os.path.join(root, n))
            if len(found) >= 200:
                break
        if not found:
            self.say("Nothing found for '%s'" % q); return
        c = ui.choose("%d result(s)" % len(found), [(os.path.relpath(f, self.cwd), "") for f in found])
        if c is not None:
            f = found[c]
            self.cd(os.path.dirname(f) if os.path.isfile(f) else f); self.pick(os.path.basename(f))

    def compress(self, ui):
        t = self.targets()
        if not t or self.trash_view:
            return
        n = ui.prompt("Zip name", (t[0]["name"] if len(t) == 1 else "archive") + ".zip")
        if not n:
            return
        out = self.unique(os.path.join(self.cwd, n))
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for e in t:
                if e["dir"]:
                    for root, _, files in os.walk(e["path"]):
                        for f in files:
                            fp = os.path.join(root, f); z.write(fp, os.path.relpath(fp, self.cwd))
                else:
                    z.write(e["path"], e["name"])
        self.sel.clear(); self.load(); self.pick(os.path.basename(out)); self.say("Created " + os.path.basename(out))

    def extract(self, ui):
        e = self.current()
        if e and e["name"].lower().endswith(".zip") and ui.confirm("Extract %s here?" % e["name"], "Extract", "Cancel", title="Extract"):
            d = self.unique(os.path.join(self.cwd, e["name"][:-4]))
            with zipfile.ZipFile(e["path"]) as z:
                z.extractall(d)
            self.load(); self.pick(os.path.basename(d)); self.say("Extracted")

    def choose_place(self, ui):
        ps = places()
        c = ui.choose("Go to", [(n, "") for n, _, _ in ps])
        if c is not None:
            self.cd(ps[c][1])

    def help(self, ui):
        ui.pager("Files help", [l for l in (nhelp.render("files", color=False) or "").split("\n")] + [
            "", "Mouse / touch", "  tap a row = select · double-tap = open · tap a header = sort · tap the path to jump",
            "  Select button = tap rows to tick several · tap a sidebar place to go there", "",
            "Keys", "  ↑↓ move · Enter open · Backspace up · Alt-←/→ back/forward · Space tick · a all",
            "  c copy · x cut · v paste · d trash · D delete forever · r/F2 rename · n new file · N new folder",
            "  i properties · / filter · f search inside · . hidden · s sort · S reverse · z zip · u unzip",
            "  t trash · R restore (in trash) · E empty trash · g places · e edit · q quit"])

    # ── events ──
    def key(self, ui, k):
        e = self.current()
        n = len(self.entries)
        if k in (ord("q"), 27):
            if self.filter:
                self.filter = ""; self.load(); return True
            return False
        if k in (curses.KEY_DOWN, ord("j")):
            self.cur = min(n - 1, self.cur + 1)
        elif k in (curses.KEY_UP, ord("k")):
            self.cur = max(0, self.cur - 1)
        elif k == curses.KEY_NPAGE:
            self.cur = min(n - 1, self.cur + 10)
        elif k == curses.KEY_PPAGE:
            self.cur = max(0, self.cur - 10)
        elif k in (curses.KEY_HOME, ord("g") if False else -2):
            self.cur = 0
        elif k == curses.KEY_END:
            self.cur = max(0, n - 1)
        elif k in tui.ENTER or k in (curses.KEY_RIGHT, ord("l")):
            self.open_entry(ui)
        elif k in tui.BACKSPACE or k in (curses.KEY_LEFT, ord("h")):
            self.up()
        elif k == ord(" ") and e:
            self.sel ^= {e["path"]}; self.cur = min(n - 1, self.cur + 1)
        elif k == ord("a"):
            self.sel = set() if len(self.sel) == n else {x["path"] for x in self.entries}
        elif k == ord("c"):
            self.set_clip("copy")
        elif k == ord("x"):
            self.set_clip("cut")
        elif k == ord("v"):
            self.paste(ui)
        elif k in (ord("d"), curses.KEY_DC):
            self.delete(ui)
        elif k == ord("D"):
            self.delete(ui, True)
        elif k in (ord("r"), curses.KEY_F2):
            self.restore(ui) if self.trash_view else self.rename(ui)
        elif k == ord("R"):
            self.restore(ui)
        elif k == ord("n"):
            self.new(ui, False)
        elif k == ord("N"):
            self.new(ui, True)
        elif k == ord("i"):
            self.info(ui)
        elif k == ord("/"):
            f = ui.prompt("Filter", self.filter)
            if f is not None:
                self.filter = f; self.load()
        elif k == ord("f"):
            self.search(ui)
        elif k == ord("."):
            self.hidden = not self.hidden; self.load()
        elif k == ord("s"):
            order = ["name", "size", "date", "type"]; self.sort = order[(order.index(self.sort) + 1) % 4]; self.load(); self.say("Sorted by " + self.sort)
        elif k == ord("S"):
            self.rev = not self.rev; self.load()
        elif k == ord("z"):
            self.compress(ui)
        elif k == ord("u"):
            self.extract(ui)
        elif k == ord("t"):
            self.cd("trash:")
        elif k == ord("E"):
            self.empty_trash(ui)
        elif k == ord("g"):
            self.choose_place(ui)
        elif k == ord("e") and e and not e["dir"]:
            self.open_entry(ui)
        elif k == ord("~"):
            self.cd(os.path.expanduser("~"))
        elif k == ord("?"):
            self.help(ui)
        elif k == 2:   # ctrl-b
            self.go_back()
        elif k == 6:   # ctrl-f
            self.go_fwd()
        return True

    def scroll(self, ui, n):
        self.cur = max(0, min(len(self.entries) - 1, self.cur + n))

    def click(self, ui, y, x, double):
        pass

    def set_sort(self, key):
        if self.sort == key:
            self.rev = not self.rev
        else:
            self.sort, self.rev = key, False
        self.load()

    # ── drawing ──
    def row_click(self, ui, i):
        e = self.entries[i]
        if self.multi:
            self.sel ^= {e["path"]}; self.cur = i
        elif ui.double and i == self.cur:
            self.open_entry(ui, e)
        else:
            self.cur = i

    def draw(self, ui):
        H, W = ui.h, ui.w
        self.layout = {}
        narrow = W < 72
        side_w = 0 if narrow else 17
        det_w = 0 if W < 112 else 34
        # title bar
        ui.text(0, 0, " " * W, "bar")
        ui.text(0, 1, ICO("folder") + "  Files", "bar")
        try:
            du = shutil.disk_usage(self.cwd)
            ui.text(0, max(14, W - 28), ("%s free of %s" % (tui.human(du.free), tui.human(du.total))).rjust(27), "bar", 27)
        except OSError:
            pass
        # address bar
        ui.fill(1, 0, 1, W, "panel")
        x = 0
        x += ui.button(1, x, ICO("prev") if icons.mode() != "plain" else "<", self.go_back, "panel_p" if self.back else "panel_dim")
        x += ui.button(1, x, ICO("next") if icons.mode() != "plain" else ">", self.go_fwd, "panel_p" if self.fwd else "panel_dim")
        x += ui.button(1, x, ICO("up"), lambda: self.up(), "panel_p")
        x += ui.button(1, x, ICO("refresh"), self.load, "panel_p")
        if self.trash_view:
            ui.text(1, x + 1, ICO("delete") + " Trash", "panel_a", W - x - 2)
        else:
            parts = [p for p in self.cwd.split(os.sep) if p]
            segs = [("/", os.sep)] + [(p, os.sep + os.sep.join(parts[:i + 1])) for i, p in enumerate(parts)]
            home = os.path.expanduser("~")
            if self.cwd.startswith(home):
                hp = [p for p in home.split(os.sep) if p]
                segs = [("~", home)] + [(p, os.sep + os.sep.join(parts[:len(hp) + i + 1])) for i, p in enumerate(parts[len(hp):])]
            room = W - x - 2
            while len(segs) > 1 and sum(tui.width(s[0]) + 3 for s in segs) > room:
                segs.pop(1)
            x += 1
            for i, (nm, path) in enumerate(segs):
                lab = tui.clip(nm, 16)
                tui.width(lab)
                ui.text(1, x, lab, "panel_p" if i == len(segs) - 1 else "panel", room)
                ui.region(1, x, 1, tui.width(lab), (lambda p: (lambda: self.cd(p)))(path))
                x += tui.width(lab)
                if i < len(segs) - 1:
                    ui.text(1, x, " › ", "panel_dim"); x += 3
        # toolbar
        ui.fill(2, 0, 1, W, "panel")
        tb = [("new", "New", lambda: self.new(ui, False)), ("folder", "Folder", lambda: self.new(ui, True)), ("copy", "Copy", lambda: self.set_clip("copy")),
              ("cut", "Cut", lambda: self.set_clip("cut")), ("paste", "Paste", lambda: self.paste(ui)), ("rename", "Rename", lambda: self.rename(ui)),
              ("delete", "Delete", lambda: self.delete(ui)), ("info", "Info", lambda: self.info(ui)), ("search", "Find", lambda: self.search(ui)),
              ("sort", "Sort", lambda: self.set_sort({"name": "size", "size": "date", "date": "type", "type": "name"}[self.sort])),
              ("grid", "Select" + (" ✔" if self.multi else ""), lambda: setattr(self, "multi", not self.multi))]
        if self.trash_view:
            tb = [("up", "Restore", lambda: self.restore(ui)), ("delete", "Delete", lambda: self.delete(ui)), ("delete", "Empty", lambda: self.empty_trash(ui)), ("grid", "Select" + (" ✔" if self.multi else ""), lambda: setattr(self, "multi", not self.multi))]
        x = 0
        compact = W < 64
        for ic, label, cb in tb:
            lab = ICO(ic) if compact else (ICO(ic) + " " + label)
            if x + tui.width(lab) + 2 > W:
                break
            x += ui.button(2, x, lab, cb, "panel_a" if (label.startswith("Select") and self.multi) else "panel") + 0
        top, bot = 3, H - 2
        # sidebar
        lx = 0
        if side_w:
            ui.fill(top, 0, bot - top, side_w, "panel")
            ui.text(top, 1, "PLACES", "panel_dim", side_w - 2)
            for i, (nm, path, ic) in enumerate(places()):
                if top + 1 + i >= bot - 3:
                    break
                here = (path == "trash:" and self.trash_view) or (path == self.cwd and not self.trash_view)
                lab = " %s %s" % (ICO(ic), nm)
                ui.text(top + 1 + i, 0, lab.ljust(side_w), "sel" if here else "panel", side_w)
                ui.region(top + 1 + i, 0, 1, side_w, (lambda p: (lambda: self.cd(p)))(path))
            try:
                du = shutil.disk_usage(self.cwd)
                ui.text(bot - 3, 1, "STORAGE", "panel_dim", side_w - 2)
                ui.bar(bot - 2, 1, side_w - 2, du.used / du.total, "primary" if du.used / du.total < 0.9 else "danger")
                ui.text(bot - 1 if bot - 1 < H else bot - 2, 1, "%s used" % tui.human(du.used), "panel_dim", side_w - 2)
            except OSError:
                pass
            lx = side_w
        lw = W - lx - det_w
        # list header
        cols_date = lw >= 46
        name_w = lw - 8 - (13 if cols_date else 0) - 3
        hy = top
        ui.fill(hy, lx, 1, lw, "panel")
        def head(xx, lab, key):
            arrow = (" ↓" if self.rev else " ↑") if self.sort == key else ""
            ui.text(hy, xx, lab + arrow, "panel_p" if self.sort == key else "panel", 12)
            ui.region(hy, xx, 1, tui.width(lab) + 2, lambda: self.set_sort(key))
        head(lx + 3, "Name", "name"); head(lx + 3 + name_w, "Size", "size")
        if cols_date:
            head(lx + 3 + name_w + 8, "Modified", "date")
        # rows
        vis = bot - top - 1
        self.cur = max(0, min(self.cur, len(self.entries) - 1))
        if self.cur < self.top:
            self.top = self.cur
        if self.cur >= self.top + vis:
            self.top = self.cur - vis + 1
        self.top = max(0, self.top)
        if not self.entries:
            ui.text(top + 2, lx + 3, "(empty)" if not self.filter else "Nothing matches '%s'" % self.filter, "dim")
        for r in range(vis):
            i = self.top + r
            if i >= len(self.entries):
                break
            e = self.entries[i]
            y = top + 1 + r
            cur = i == self.cur
            ticked = e["path"] in self.sel
            base = "sel" if cur else ("accent" if ticked else ("primary" if e["dir"] else "text"))
            ui.text(y, lx, " " * lw, "sel" if cur else "text", lw)
            mark = "●" if ticked else " "
            ui.text(y, lx, mark, "sel" if cur else "accent", 1)
            ui.text(y, lx + 1, ICO(icons.for_path(e["name"], e["dir"])), base, 2)
            ui.text(y, lx + 3, e["name"] + ("/" if e["dir"] else ""), base, name_w - 1)
            ui.text(y, lx + 3 + name_w, ("" if e["dir"] else tui.human(e["size"])).rjust(6), "sel" if cur else "dim", 7)
            if cols_date:
                ui.text(y, lx + 3 + name_w + 8, fmt_time(e["mtime"]), "sel" if cur else "dim", 12)
            ui.region(y, lx, 1, lw, (lambda ii: (lambda: self.row_click(ui, ii)))(i))
        # details pane
        if det_w:
            dx = W - det_w
            ui.fill(top, dx, bot - top, det_w, "panel")
            ui.text(top, dx + 1, "DETAILS", "panel_dim", det_w - 2)
            self.details(ui, dx + 1, top + 2, det_w - 2, bot - top - 3)
        # status + hints
        n = len(self.entries)
        selsz = sum(e["size"] for e in self.entries if e["path"] in self.sel and not e["dir"])
        st = "%d item%s" % (n, "" if n == 1 else "s")
        if self.sel:
            st += "  ·  %d selected (%s)" % (len(self.sel), tui.human(selsz))
        if self.clip:
            st += "  ·  %s %d" % ("copied" if self.clip[0] == "copy" else "cut", len(self.clip[1]))
        if self.filter:
            st += "  ·  filter: " + self.filter
        ui.fill(H - 2, 0, 1, W, "panel")
        ui.text(H - 2, 1, st, "panel", W - 2)
        if self.msg and time.time() - self.msg_t < 4:
            ui.text(H - 2, max(0, W - tui.width(self.msg) - 2), self.msg, "panel_a", W - 2)
        ui.text(H - 1, 1, "↑↓ move  Enter open  ⌫ up  Space tick  c x v  d trash  r rename  / filter  ? help  q quit", "dim", W - 2)

    def details(self, ui, x, y, w, h):
        e = self.current()
        if not e:
            return
        ui.text(y, x, ICO(icons.for_path(e["name"], e["dir"])) + " " + e["name"], "panel_p", w)
        ui.text(y + 1, x, ("Folder" if e["dir"] else (mimetypes.guess_type(e["name"])[0] or "File")), "panel_dim", w)
        if not e["dir"]:
            ui.text(y + 2, x, "%s  ·  %s" % (tui.human(e["size"]), fmt_time(e["mtime"])), "panel", w)
        else:
            try:
                ui.text(y + 2, x, "%d items" % len(os.listdir(e["path"])), "panel", w)
            except OSError:
                pass
        p = e["path"]
        if not e["dir"] and e["size"] < 400000 and icons.for_path(p) in ("text", "code"):
            try:
                with open(p, "r", errors="replace") as f:
                    for i, ln in enumerate(f):
                        if i >= h - 5:
                            break
                        ui.text(y + 4 + i, x, ln.rstrip("\n").replace("\t", "  "), "text", w)
            except OSError:
                pass


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    nhelp.maybe_help("files", argv)
    tui.run(Files(argv[0] if argv else None))


if __name__ == "__main__":
    main()
