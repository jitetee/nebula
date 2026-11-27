"""svn: save video or audio from a link (YouTube, TikTok, Instagram, X, Facebook, Reddit, Vimeo, SoundCloud and ~1000 more) with yt-dlp.

  svn <link>            guided steps: check the link, video or audio, quality, folder, download
  svn <link> -a         audio (mp3) with defaults          svn <link> -v 720   video at 720p
  svn <link> --list     show every available format        svn history · --update · --doctor · sites
Save only what you have the right to, and follow each site's terms.
"""
import argparse
import curses
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse

from nebula_core import help as nhelp, icons, paths, tui

ICO = icons.get
URL_RE = re.compile(r"https?://[^\s<>\"']+")
SITES = "YouTube (videos, shorts, music), TikTok, Instagram (public posts/reels; private needs --cookies), Facebook, X/Twitter, Reddit, Vimeo, Dailymotion, Twitch (clips/VODs), SoundCloud, Bandcamp, Pinterest, Snapchat spotlight, LinkedIn, Streamable, Imgur, Bilibili and ~1000 more (yt-dlp --list-extractors)."


# ── helpers ──
def ytdlp_cmd():
    e = os.environ.get("NEBULA_SVN_YTDLP")
    if e:
        return e.split()
    w = shutil.which("yt-dlp")
    if w:
        return [w]
    try:
        import yt_dlp  # noqa
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        return None


def has_ffmpeg():
    return bool(shutil.which("ffmpeg"))


def clipboard():
    for c in (["termux-clipboard-get"], ["wl-paste"], ["xclip", "-o", "-selection", "clipboard"], ["pbpaste"]):
        if shutil.which(c[0]):
            try:
                out = subprocess.run(c, capture_output=True, text=True, timeout=3).stdout
                m = URL_RE.search(out)
                if m:
                    return m.group(0)
            except Exception:
                pass
    return ""


def clean_url(u):
    m = URL_RE.search(u or "")
    return m.group(0).rstrip(".,)") if m else (u or "").strip()


def out_dirs(kind):
    h = os.path.expanduser("~")
    sub = {"video": "movies", "audio": "music"}.get(kind, "pictures")
    cands = []
    for base in (os.path.join(h, "storage", sub), os.path.join(h, "storage", "downloads"), os.path.join(h, "storage", "shared", "Download"), os.path.join(h, "Downloads")):
        if os.path.isdir(base):
            cands.append(os.path.join(base, "Nebula") if "storage" in base and sub in base or base.endswith("Download") or base.endswith("Downloads") else base)
    cands.append(os.path.join(h, "nebula-media"))
    out = []
    for c in cands:
        if c not in out:
            out.append(c)
    return out


def friendly_error(text):
    t = text.lower()
    if "private" in t or "login" in t or "sign in" in t or "cookies" in t:
        return "This one needs a login (private, age-gated or members-only). Try  svn <link> --cookies cookies.txt"
    if "unsupported url" in t:
        return "That link is not a video page. Open the video itself and copy its link."
    if "429" in t or "rate" in t:
        return "The site is rate-limiting you. Wait a minute and try again."
    if "404" in t or "http error 4" in t and "not found" in t:
        return "That link does not exist (404). Check it and try again."
    if "not available" in t or "removed" in t or "unavailable" in t:
        return "That video is not available (removed, or blocked in your country)."
    if "network" in t or "resolve" in t or "connection" in t or "timed out" in t:
        return "No connection. Check your internet and try again."
    last = [l for l in text.strip().splitlines() if l.strip()]
    return (last[-1] if last else "unknown error")[:200]


def human_dur(s):
    if not s:
        return "?"
    s = int(s)
    h, r = divmod(s, 3600)
    return ("%d:%02d:%02d" % (h, r // 60, r % 60)) if h else ("%d:%02d" % (r // 60, r % 60))


def video_heights(info):
    """[(height, approx_bytes)] best first."""
    best = {}
    audio = max([f.get("filesize") or f.get("filesize_approx") or 0 for f in info.get("formats", []) if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")] or [0])
    for f in info.get("formats", []):
        h = f.get("height")
        if not h or f.get("vcodec") in (None, "none"):
            continue
        sz = (f.get("filesize") or f.get("filesize_approx") or 0)
        if f.get("acodec") in (None, "none"):
            sz += audio
        best[h] = max(best.get(h, 0), sz)
    return sorted(best.items(), reverse=True)


def build_args(info_kind, quality, fmt, outdir, template, cookies=None, playlist=False, ffmpeg=True, items=None):
    a = ["--newline", "--progress", "--no-colors", "--no-warnings", "--windows-filenames", "--retries", "5", "--fragment-retries", "5", "--socket-timeout", "20", "-N", "4",
         "--embed-metadata", "--progress-template", "download:NEBPROG|%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.total_bytes_estimate)s",
         "--print", "after_move:NEBFILE|%(filepath)s", "-o", os.path.join(outdir, template)]
    a += ["--yes-playlist"] if playlist else ["--no-playlist"]
    if items:
        a += ["--playlist-items", items]
    if cookies:
        a += ["--cookies", cookies]
    if info_kind == "video":
        h = quality
        cap = "[height<=%s]" % h if h else ""
        if ffmpeg:
            a += ["-f", "bv*%s[vcodec^=avc1]+ba[ext=m4a]/bv*%s+ba/b%s/b" % (cap, cap, cap), "--merge-output-format", "mp4"]
        else:
            a += ["-f", "b%s[ext=mp4]/b%s/b" % (cap, cap)]
    elif info_kind == "audio":
        if ffmpeg:
            if fmt == "mp3":
                a += ["-f", "ba/b", "-x", "--audio-format", "mp3", "--audio-quality", {None: "0"}.get(quality, "%sK" % quality)]
            else:
                a += ["-f", "ba[ext=m4a]/ba/b" if fmt == "m4a" else "ba/b", "-x", "--audio-format", fmt]
        else:
            a += ["-f", "ba[ext=m4a]/ba/b"]
    else:
        a += ["--skip-download", "--write-thumbnail"] + (["--convert-thumbnails", "jpg"] if ffmpeg else [])
    return a


class Job:
    """One yt-dlp run in a thread; the UI reads its fields."""
    def __init__(self, cmd, url):
        self.cmd, self.url = cmd, url
        self.pct, self.speed, self.eta, self.done_b, self.total_b = 0.0, "", "", 0, 0
        self.stage, self.files, self.log, self.error, self.finished = "starting", [], [], "", False
        self.proc = None
        self.t = threading.Thread(target=self.run, daemon=True)
        self.t.start()

    def run(self):
        try:
            self.proc = subprocess.Popen(self.cmd + [self.url], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except OSError as e:
            self.error = str(e); self.finished = True; return
        for ln in self.proc.stdout:
            ln = ln.rstrip("\n")
            if ln.startswith("NEBPROG|") or ln.startswith("download:NEBPROG|"):
                p = ln.split("NEBPROG|", 1)[1].split("|")
                try:
                    self.pct = float(p[0].strip().rstrip("%") or 0)
                except ValueError:
                    pass
                self.speed, self.eta = p[1].strip(), p[2].strip()
                for v in (p[4], p[5]):
                    try:
                        self.total_b = int(float(v)); break
                    except (ValueError, IndexError):
                        pass
                try:
                    self.done_b = int(float(p[3]))
                except (ValueError, IndexError):
                    pass
                self.stage = "downloading"
            elif ln.startswith("NEBFILE|"):
                self.files.append(ln.split("|", 1)[1]); self.stage = "finishing"
            else:
                self.log.append(ln)
                if "[Merger]" in ln or "[ExtractAudio]" in ln or "[VideoConvertor]" in ln or "[Metadata]" in ln or "[ThumbnailsConvertor]" in ln:
                    self.stage = "converting"
        rc = self.proc.wait()
        if rc != 0 and not self.files:
            self.error = friendly_error("\n".join(self.log))
        self.finished = True

    def cancel(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()


def fetch_info(url, cookies=None, timeout=60):
    cmd = ytdlp_cmd()
    a = cmd + ["-J", "--no-warnings", "--flat-playlist"] + (["--cookies", cookies] if cookies else []) + [url]
    r = subprocess.run(a, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(friendly_error(r.stderr or r.stdout))
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise RuntimeError("Could not read the link's details")


def history_file():
    d = os.path.join(paths.cfg(), "svn")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "history.jsonl")


def remember(url, title, path):
    try:
        with open(history_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps({"url": url, "title": title, "path": path, "when": int(time.time())}) + "\n")
    except OSError:
        pass


def read_history():
    out = []
    try:
        for ln in open(history_file(), encoding="utf-8"):
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    except OSError:
        pass
    return out[::-1]


# ── the guided steps ──
STEPS = ["Link", "Check", "Type", "Quality", "Save", "Download"]


class Wizard(tui.App):
    tick_ms = 150

    def __init__(self, url="", cookies=None, preset=None):
        self.url, self.cookies = clean_url(url), cookies
        self.step = 0 if not self.url else 1
        self.info, self.err = None, ""
        self.kind, self.quality, self.fmt, self.outdir = "video", None, "mp4", ""
        self.sel = 0
        self.name_style = 0
        self.playlist = False
        self.fetch = None
        self.job = None
        self.result = None
        self.opts = []
        self.quit = False
        self.msg = ""
        self.ffmpeg = has_ffmpeg()

    # ── flow ──
    def start(self, ui):
        if not ytdlp_cmd():
            self.step = -1
        elif self.step == 1:
            self.begin_fetch()

    def begin_fetch(self):
        self.info, self.err, self.step = None, "", 1
        box = {}
        def work():
            try:
                box["info"] = fetch_info(self.url, self.cookies)
            except subprocess.TimeoutExpired:
                box["err"] = "The site took too long to answer."
            except Exception as e:
                box["err"] = str(e)
        t = threading.Thread(target=work, daemon=True)
        t.start()
        self.fetch = (t, box)

    def poll_fetch(self):
        if self.fetch and not self.fetch[0].is_alive():
            box = self.fetch[1]
            self.fetch = None
            if "info" in box:
                self.info = box["info"]
            else:
                self.err = box.get("err", "unknown error")

    def set_step(self, s):
        self.step, self.sel = s, 0
        self.opts = self.options_for(s)

    def options_for(self, s):
        if s == 2:
            o = [("Video", "MP4  (with sound)", "video", "mp4"), ("Audio", "MP3  (works everywhere)", "audio", "mp3"),
                 ("Audio", "M4A  (no re-encode, fastest)", "audio", "m4a"), ("Audio", "OPUS  (small, great quality)", "audio", "opus"),
                 ("Picture", "the thumbnail image", "thumb", "jpg")]
            return [("%s  %s" % (a, b), "", k, f) for a, b, k, f in o]
        if s == 3:
            if self.kind == "video":
                hs = video_heights(self.info or {})
                out = [("Best available", "", None)]
                for h, sz in hs:
                    if h >= 144:
                        out.append(("%dp" % h, ("~" + tui.human(sz)) if sz else "", h))
                return out
            if self.kind == "audio" and self.fmt == "mp3":
                return [("Best (VBR ~245k)", "", None), ("320 kbps", "", 320), ("192 kbps", "", 192), ("128 kbps", "", 128), ("64 kbps  (voice, tiny)", "", 64)]
            return [("Best available", "", None)]
        if s == 4:
            return [(d, "", d) for d in out_dirs(self.kind)] + [("Somewhere else…", "", "?")]
        return []

    def duration_note(self):
        d = (self.info or {}).get("duration")
        return human_dur(d)

    def start_download(self):
        template = ["%(title).80s [%(id)s].%(ext)s", "%(title).100s.%(ext)s", "%(uploader).30s - %(title).70s.%(ext)s"][self.name_style]
        os.makedirs(self.outdir, exist_ok=True)
        args = build_args(self.kind, self.quality, self.fmt, self.outdir, template, self.cookies, self.playlist, self.ffmpeg)
        self.job = Job(ytdlp_cmd() + args, self.url)
        self.step = 5

    # ── events ──
    def go_next(self, ui):
        s = self.step
        if s == 0:
            u = ui.prompt("Paste the link", self.url or clipboard(), "YouTube, TikTok, Instagram, X, Facebook, Reddit …")
            if u:
                self.url = clean_url(u)
                if self.url.startswith("http"):
                    self.begin_fetch()
                else:
                    self.msg = "That does not look like a link"
        elif s == 1 and self.info:
            if self.info.get("_type") == "playlist" and self.info.get("entries"):
                c = ui.choose("This is a playlist (%d items)" % len(self.info["entries"]), ["Whole playlist", "Only the first video"])
                if c is None:
                    return
                self.playlist = c == 0
            self.set_step(2)
        elif s in (2, 3, 4) and self.opts:
            o = self.opts[self.sel]
            if s == 2:
                self.kind, self.fmt = o[2], o[3]
                self.set_step(3 if self.kind != "thumb" else 4)
            elif s == 3:
                self.quality = o[2]; self.set_step(4)
            else:
                if o[2] == "?":
                    d = ui.prompt("Folder to save in", os.path.expanduser("~"))
                    if not d:
                        return
                    self.outdir = os.path.expanduser(d)
                else:
                    self.outdir = o[2]
                self.start_download()
        elif s == 5 and self.job and self.job.finished and not self.job.error:
            self.step = 6
        elif s == 6:
            self.quit = True

    def go_back(self):
        if self.step in (1,) or self.step == 0:
            self.step = 0; self.info = None; self.fetch = None
        elif self.step in (2, 3, 4):
            self.set_step(self.step - 1 if not (self.step == 4 and self.kind == "thumb") else 2)
        elif self.step in (5, 6) and (not self.job or self.job.finished):
            self.set_step(4)

    def key(self, ui, k):
        if k in (ord("q"), 27):
            if self.job and not self.job.finished:
                if not ui.confirm("Stop the download?", "Stop", "Keep going", danger=True):
                    return True
                self.job.cancel()
            return False
        if k in (curses.KEY_DOWN, ord("j")):
            self.sel = min(len(self.opts) - 1, self.sel + 1)
        elif k in (curses.KEY_UP, ord("k")):
            self.sel = max(0, self.sel - 1)
        elif k in tui.ENTER:
            self.go_next(ui)
        elif k in tui.BACKSPACE or k == ord("b"):
            self.go_back()
        elif ord("1") <= k <= ord("9") and self.step in (2, 3, 4) and k - ord("1") < len(self.opts):
            self.sel = k - ord("1"); self.go_next(ui)
        elif k == ord("n") and self.step == 4:
            self.name_style = (self.name_style + 1) % 3
        elif k == ord("p") and self.step == 6 and self.result:
            self.act_play()
        elif k == ord("o") and self.step == 6 and self.result:
            self.act_open()
        elif k == ord("f") and self.step == 6 and self.result:
            self.act_files(ui)
        elif k == ord("a") and self.step == 6:
            self.__init__("", self.cookies); self.step = 0
        return True

    def tick(self, ui):
        self.poll_fetch()
        if self.step == 0 and not self.url and not self.err:
            pass
        if self.step == 5 and self.job and self.job.finished:
            if self.job.error:
                return
            self.result = (self.job.files[-1] if self.job.files else self.outdir)
            title = (self.info or {}).get("title", "")
            for f in (self.job.files or [self.outdir]):
                remember(self.url, title, f)
            self.step = 6

    def row_pick(self, ui, i):
        self.sel = i
        if ui.double or True:
            self.go_next(ui)

    def act_open(self):
        op = next((x for x in ("termux-open", "xdg-open") if shutil.which(x)), None)
        if op and self.result:
            subprocess.Popen([op, self.result], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); self.msg = "Opened"
        else:
            self.msg = "No app to open files (pkg install termux-tools)"

    def act_play(self):
        if self.result:
            self.msg = "Play it with:  player \"%s\"" % self.result

    def act_files(self, ui):
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([os.path.join(paths.home(), "apps", "gui"), os.path.join(paths.home(), "lib")]))
        d = self.result if os.path.isdir(self.result or "") else os.path.dirname(self.result or self.outdir)
        ui.suspend(lambda: subprocess.call([sys.executable, "-m", "nebula_gui.files", d], env=env))

    # ── drawing ──
    def draw(self, ui):
        W, H = ui.w, ui.h
        ui.text(0, 0, " " * W, "bar"); ui.text(0, 1, ICO("download") + "  Save media", "bar")
        # step header
        ui.fill(1, 0, 1, W, "panel")
        x = 0
        for i, name in enumerate(STEPS):
            lab = ("%d %s" % (i + 1, "Get" if name == "Download" else name)) if W >= 54 else str(i + 1)
            cur = (self.step == i) or (self.step == 6 and i == 5)
            done = i < self.step
            x += ui.button(1, x, lab, (lambda ii: (lambda: self.jump(ii)))(i), "sel" if cur else ("panel_p" if done else "panel_dim"))
        y = 3
        if self.step == -1:
            return self.draw_missing(ui, y)
        body = {0: self.d_link, 1: self.d_check, 2: self.d_list, 3: self.d_list, 4: self.d_list, 5: self.d_download, 6: self.d_done}[self.step]
        body(ui, y)
        if self.msg:
            ui.text(H - 2, 2, self.msg, "accent", W - 4)
        hint = {0: "Enter = type or paste the link", 1: "Enter = continue · b = other link", 2: "↑↓ choose · Enter · b back", 3: "↑↓ choose · Enter · b back",
                4: "↑↓ choose · Enter = start · n = name style · b back", 5: "q = cancel", 6: "o open · f folder · a another link · q quit"}.get(self.step, "q quit")
        ui.text(H - 1, 1, hint, "dim", W - 2)

    def jump(self, i):
        if i < self.step and self.step != 5 and not (self.job and not self.job.finished):
            if i == 0:
                self.step = 0
            elif i == 1:
                self.step = 1
            else:
                self.set_step(i)

    def draw_missing(self, ui, y):
        ui.box(y, 1, 9, ui.w - 2, "Setup needed", "danger")
        for i, l in enumerate(["svn needs the downloader yt-dlp.", "", "In Termux run:   pkg install yt-dlp ffmpeg", "Anywhere:        pip install -U yt-dlp", "", "Then run svn again.  (svn --doctor checks everything)"]):
            ui.text(y + 1 + i, 3, l, "text", ui.w - 6)

    def d_link(self, ui, y):
        ui.text(y, 2, "Paste a link to save its video or audio.", "text")
        ui.text(y + 1, 2, "YouTube · TikTok · Instagram · X · Facebook · Reddit · Vimeo · SoundCloud …", "dim", ui.w - 4)
        ui.button(y + 3, 2, ICO("link") + " Type or paste link", lambda: self.go_next(ui), "sel")
        cb = clipboard()
        if cb:
            ui.button(y + 5, 2, ICO("paste") if False else "Use clipboard link", lambda: (setattr(self, "url", cb), self.begin_fetch()), "panel_a")
            ui.text(y + 6, 4, cb, "dim", ui.w - 6)
        if self.err:
            ui.text(y + 8, 2, self.err, "danger", ui.w - 4)

    def d_check(self, ui, y):
        host = urlparse(self.url).netloc.replace("www.", "")
        if self.err:
            ui.box(y, 1, 7, ui.w - 2, "Could not read the link", "danger")
            for i, l in enumerate(self.wrap(self.err, ui.w - 6)[:3]):
                ui.text(y + 1 + i, 3, l, "text", ui.w - 6)
            ui.button(y + 5, 3, "Try another link", lambda: setattr(self, "step", 0), "sel")
            return
        if not self.info:
            sp = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[int(time.time() * 10) % 10]
            ui.text(y, 2, "%s Checking %s …" % (sp, host), "primary")
            return
        i = self.info
        ui.box(y, 1, 8, ui.w - 2, "Found it", "primary")
        ui.text(y + 1, 3, i.get("title", "?"), "primary", ui.w - 6)
        ui.text(y + 2, 3, "%s  ·  %s" % (i.get("uploader") or i.get("channel") or i.get("extractor_key", ""), host), "dim", ui.w - 6)
        ui.text(y + 3, 3, "Length %s" % human_dur(i.get("duration")) + ("   ·   playlist of %d" % len(i["entries"]) if i.get("entries") else ""), "text", ui.w - 6)
        ui.button(y + 5, 3, "Continue ▸", lambda: self.go_next(ui), "sel")
        ui.button(y + 5, 17, "Other link", lambda: setattr(self, "step", 0), "panel")

    @staticmethod
    def wrap(s, w):
        out, cur = [], ""
        for word in s.split():
            if len(cur) + len(word) + 1 > w:
                out.append(cur); cur = word
            else:
                cur = (cur + " " + word).strip()
        return out + ([cur] if cur else [])

    def d_list(self, ui, y):
        if not self.opts:
            self.opts = self.options_for(self.step)
        title = {2: "What do you want to save?", 3: "Pick the quality" if self.kind == "video" else "Pick the audio quality", 4: "Where should it go?"}[self.step]
        ui.text(y, 2, title, "primary")
        if self.info:
            ui.text(y + 1, 2, self.info.get("title", ""), "dim", ui.w - 4)
        vis = ui.h - y - 5
        for i, o in enumerate(self.opts[:vis]):
            yy = y + 3 + i
            sel = i == self.sel
            lab = "%d  %s" % (i + 1, o[0]) if i < 9 else "   " + o[0]
            ui.text(yy, 1, (" " + lab).ljust(ui.w - 2), "sel" if sel else "text", ui.w - 2)
            if o[1]:
                ui.text(yy, max(4, ui.w - 3 - tui.width(o[1])), o[1], "sel" if sel else "dim", tui.width(o[1]))
            ui.region(yy, 1, 1, ui.w - 2, (lambda ii: (lambda: self.row_pick(ui, ii)))(i))
        if self.step == 4:
            ui.text(ui.h - 3, 2, "Name: " + ["Title [id]", "Title only", "Uploader - Title"][self.name_style] + "   (n changes)", "dim", ui.w - 4)
        if self.step == 3 and not self.ffmpeg:
            ui.text(ui.h - 3, 2, "No ffmpeg: video is limited to what one file offers. pkg install ffmpeg for all qualities.", "accent", ui.w - 4)

    def d_download(self, ui, y):
        j = self.job
        if not j:
            return
        ui.text(y, 2, (self.info or {}).get("title", self.url), "primary", ui.w - 4)
        if j.error:
            ui.box(y + 2, 1, 6, ui.w - 2, "Failed", "danger")
            for i, l in enumerate(self.wrap(j.error, ui.w - 6)[:3]):
                ui.text(y + 3 + i, 3, l, "text", ui.w - 6)
            ui.button(y + 7, 3, "Back", lambda: self.set_step(4), "sel")
            return
        label = {"starting": "Starting …", "downloading": "Downloading", "converting": "Converting / merging …", "finishing": "Finishing …"}.get(j.stage, j.stage)
        ui.text(y + 2, 2, label, "text")
        ui.bar(y + 3, 2, ui.w - 14, j.pct / 100.0, "primary")
        ui.text(y + 3, ui.w - 11, ("%5.1f%%" % j.pct).rjust(8), "primary", 9)
        sz = "%s of %s" % (tui.human(j.done_b), tui.human(j.total_b)) if j.total_b else tui.human(j.done_b)
        ui.text(y + 5, 2, "%s   %s   ETA %s" % (sz, j.speed or "", j.eta or "?"), "dim", ui.w - 4)
        ui.button(y + 7, 2, "Cancel", lambda: (j.cancel(), self.set_step(4)), "panel_d")

    def d_done(self, ui, y):
        ui.box(y, 1, 8, ui.w - 2, "Saved", "primary")
        ui.text(y + 1, 3, ICO("ok") + "  " + (self.info or {}).get("title", "Done"), "primary", ui.w - 6)
        for i, l in enumerate(self.wrap(self.result or "", ui.w - 6)[:2]):
            ui.text(y + 2 + i, 3, l, "text", ui.w - 6)
        try:
            if self.result and os.path.isfile(self.result):
                ui.text(y + 4, 3, tui.human(os.path.getsize(self.result)), "dim")
        except OSError:
            pass
        x = 3
        x += ui.button(y + 6, x, "Open", self.act_open, "sel") + 1
        x += ui.button(y + 6, x, "Folder", lambda: self.act_files(ui), "panel") + 1
        x += ui.button(y + 6, x, "Another", lambda: (self.__init__("", self.cookies), setattr(self, "step", 0)), "panel") + 1
        ui.button(y + 6, x, "Quit", lambda: setattr(self, "quit", True), "panel")

    def click(self, ui, y, x, double):
        pass


# ── command line ──
def doctor():
    yd = ytdlp_cmd()
    print("svn doctor")
    if yd:
        v = subprocess.run(yd + ["--version"], capture_output=True, text=True).stdout.strip()
        print("  ✔ yt-dlp %s" % v)
    else:
        print("  ✖ yt-dlp missing → pkg install yt-dlp   (or pip install -U yt-dlp)")
    print("  %s ffmpeg %s" % ("✔" if has_ffmpeg() else "✖", "found" if has_ffmpeg() else "missing → pkg install ffmpeg  (needed for MP3 and high-quality video)"))
    d = out_dirs("video")[0]
    shared = os.path.isdir(os.path.expanduser("~/storage"))
    print("  %s phone storage %s" % ("✔" if shared else "✖", "linked (~/storage)" if shared else "not linked → run: termux-setup-storage"))
    print("  saves to: %s" % d)
    print("  %s clipboard link %s" % ("✔" if shutil.which("termux-clipboard-get") else "○", "available" if shutil.which("termux-clipboard-get") else "needs Termux:API (optional)"))
    return 0 if yd else 1


def list_formats(url, cookies):
    try:
        info = fetch_info(url, cookies)
    except Exception as e:
        print("✖ %s" % e); return 1
    print("%s\n  %s  ·  %s" % (info.get("title", "?"), info.get("uploader", ""), human_dur(info.get("duration"))))
    print("\n  VIDEO   " + ("  ".join("%dp (~%s)" % (h, tui.human(s) if s else "?") for h, s in video_heights(info)) or "best available"))
    abrs = sorted({int(f.get("abr")) for f in info.get("formats", []) if f.get("abr") and f.get("vcodec") in (None, "none")}, reverse=True)
    print("  AUDIO   " + (", ".join("%dk" % a for a in abrs) or "best") + "   →  mp3 / m4a / opus")
    return 0


def run_plain(url, kind, quality, fmt, outdir, cookies, playlist):
    yd = ytdlp_cmd()
    if not yd:
        print("✖ yt-dlp is missing: pkg install yt-dlp ffmpeg"); return 1
    outdir = os.path.expanduser(outdir or out_dirs(kind)[0])
    os.makedirs(outdir, exist_ok=True)
    args = build_args(kind, quality, fmt, outdir, "%(title).80s [%(id)s].%(ext)s", cookies, playlist, has_ffmpeg())
    print("→ %s  (%s%s) into %s" % (url, kind, (" " + str(quality) + ("p" if kind == "video" else "k")) if quality else " best", outdir))
    job = Job(yd + args, url)
    last = -1
    while not job.finished:
        time.sleep(0.3)
        if int(job.pct) != last and job.stage == "downloading":
            last = int(job.pct)
            sys.stdout.write("\r  %5.1f%%  %s  ETA %s   " % (job.pct, job.speed, job.eta)); sys.stdout.flush()
    print()
    if job.error:
        print("✖ %s" % job.error); return 1
    for f in job.files:
        print("✔ saved %s" % f); remember(url, os.path.basename(f), f)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    nhelp.maybe_help("svn", argv)
    ap = argparse.ArgumentParser(prog="svn", add_help=False)
    ap.add_argument("urls", nargs="*")
    ap.add_argument("-a", "--audio", action="store_true")
    ap.add_argument("-v", "--video", nargs="?", const="best")
    ap.add_argument("-f", "--format")
    ap.add_argument("-q", "--quality")
    ap.add_argument("-o", "--out")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--cookies")
    ap.add_argument("-y", "--yes", action="store_true")
    ap.add_argument("--playlist", action="store_true")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--doctor", action="store_true")
    a = ap.parse_args(argv)
    words = [u for u in a.urls]
    if words[:1] == ["history"]:
        h = read_history()
        if not h:
            print("Nothing saved yet."); return 0
        for e in h[:30]:
            print("%s  %s\n    %s" % (time.strftime("%Y-%m-%d %H:%M", time.localtime(e.get("when", 0))), e.get("title", "")[:60], e.get("path", "")))
        return 0
    if words[:1] == ["sites"]:
        print(SITES); return 0
    if a.doctor or words[:1] == ["doctor"]:
        return doctor()
    if a.update or words[:1] == ["update"]:
        cmd = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"] if not shutil.which("pkg") else ["pkg", "upgrade", "-y", "yt-dlp"]
        print("Updating yt-dlp: " + " ".join(cmd)); return subprocess.call(cmd)
    urls = [clean_url(u) for u in words if u.startswith("http") or "." in u]
    if a.list and urls:
        return list_formats(urls[0], a.cookies)
    kind = "audio" if a.audio or (a.format in ("mp3", "m4a", "opus")) else ("video" if (a.video or a.format == "mp4" or a.yes) else None)
    if kind and urls:
        fmt = a.format or ("mp3" if kind == "audio" else "mp4")
        q = a.quality or (a.video if a.video not in (None, "best") else None)
        q = int(re.sub(r"\D", "", str(q))) if q else None
        rc = 0
        for u in urls:
            rc = run_plain(u, kind, q, fmt, a.out, a.cookies, a.playlist) or rc
        return rc
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("svn needs a terminal for the guided steps. Use flags instead: svn <link> -a  or  svn <link> -v 720"); return 2
    tui.run(Wizard(urls[0] if urls else "", a.cookies))
    return 0


if __name__ == "__main__":
    sys.exit(main())
