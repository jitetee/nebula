"""Monitor: live system info for your phone/terminal (CPU, memory, storage, battery, network, processes, Nebula).

  monitor        keys: Tab/←→ switch tab · r refresh · k kill (processes) · q quit
"""
import curses
import os
import platform
import shutil
import subprocess
import sys
import time

from nebula_core import ai, help as nhelp, icons, paths, tui

ICO = icons.get


def read(path, default=""):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return default


def cpu_times():
    for ln in read("/proc/stat").split("\n"):
        if ln.startswith("cpu "):
            v = [int(x) for x in ln.split()[1:]]
            return sum(v), v[3] + (v[4] if len(v) > 4 else 0)
    return 0, 0


def meminfo():
    d = {}
    for ln in read("/proc/meminfo").split("\n"):
        if ":" in ln:
            k, v = ln.split(":", 1)
            try:
                d[k] = int(v.split()[0]) * 1024
            except (ValueError, IndexError):
                pass
    return d


def battery():
    try:
        if shutil.which("termux-battery-status"):
            import json
            return json.loads(subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=4).stdout)
    except Exception:
        pass
    base = "/sys/class/power_supply"
    try:
        for n in os.listdir(base):
            if read(os.path.join(base, n, "type")).strip() == "Battery":
                return {"percentage": int(read(os.path.join(base, n, "capacity"), "0")), "status": read(os.path.join(base, n, "status")).strip(),
                        "temperature": int(read(os.path.join(base, n, "temp"), "0") or 0) / 10.0}
    except OSError:
        pass
    return None


def net_bytes():
    rx = tx = 0
    for ln in read("/proc/net/dev").split("\n")[2:]:
        if ":" in ln:
            n, v = ln.split(":", 1)
            if n.strip() == "lo":
                continue
            f = v.split()
            rx += int(f[0]); tx += int(f[8])
    return rx, tx


def local_ips():
    out = []
    try:
        r = subprocess.run(["ip", "-o", "addr"], capture_output=True, text=True, timeout=3).stdout
        for ln in r.split("\n"):
            f = ln.split()
            if len(f) > 3 and f[2] == "inet" and f[1] != "lo":
                out.append("%s %s" % (f[1], f[3].split("/")[0]))
    except Exception:
        pass
    return out


def processes(n=40):
    try:
        r = subprocess.run(["ps", "-eo", "pid,pcpu,pmem,etime,comm", "--sort=-pcpu"], capture_output=True, text=True, timeout=4).stdout.split("\n")[1:]
    except Exception:
        try:
            r = subprocess.run(["ps", "-A", "-o", "PID,%CPU,%MEM,ELAPSED,COMMAND"], capture_output=True, text=True, timeout=4).stdout.split("\n")[1:]
        except Exception:
            return []
    out = []
    for ln in r:
        f = ln.split(None, 4)
        if len(f) == 5:
            out.append(f)
    return out[:n]


def uptime():
    try:
        s = float(read("/proc/uptime").split()[0])
        d, r = divmod(int(s), 86400); h, r = divmod(r, 3600)
        return "%dd %dh %dm" % (d, h, r // 60) if d else "%dh %dm" % (h, r // 60)
    except (ValueError, IndexError):
        return "?"


class Monitor(tui.App):
    tick_ms = 1000
    TABS = ["Overview", "Processes", "Storage", "Network", "Nebula"]

    def __init__(self):
        self.tab = 0
        self.prev = cpu_times()
        self.cpu = 0.0
        self.hist = []
        self.net_prev = (time.time(),) + net_bytes()
        self.net_rate = (0, 0)
        self.bat = battery()
        self.bat_t = time.time()
        self.procs = []
        self.proc_cur = 0
        self.cores = os.cpu_count() or 1
        self.sample()

    def sample(self):
        t, i = cpu_times()
        dt, di = t - self.prev[0], i - self.prev[1]
        self.cpu = 100.0 * (1 - di / dt) if dt > 0 else self.cpu
        self.prev = (t, i)
        self.hist = (self.hist + [self.cpu])[-60:]
        now = time.time()
        rx, tx = net_bytes()
        el = max(0.1, now - self.net_prev[0])
        self.net_rate = ((rx - self.net_prev[1]) / el, (tx - self.net_prev[2]) / el)
        self.net_prev = (now, rx, tx)
        if now - self.bat_t > 15:
            self.bat, self.bat_t = battery(), now
        if self.tab == 1:
            self.procs = processes()

    def tick(self, ui):
        self.sample()

    def spark(self, vals, w):
        bars = "▁▂▃▄▅▆▇█"
        vals = vals[-w:]
        return "".join(bars[min(7, int(v / 100.0 * 8))] for v in vals)

    def key(self, ui, k):
        if k in (ord("q"), 27):
            return False
        if k in (9, curses.KEY_RIGHT, ord("l")):
            self.tab = (self.tab + 1) % len(self.TABS)
        elif k in (curses.KEY_BTAB, curses.KEY_LEFT, ord("h")):
            self.tab = (self.tab - 1) % len(self.TABS)
        elif ord("1") <= k <= ord("5"):
            self.tab = k - ord("1")
        elif k == ord("r"):
            self.sample()
        elif self.tab == 1:
            if k in (curses.KEY_DOWN, ord("j")):
                self.proc_cur = min(len(self.procs) - 1, self.proc_cur + 1)
            elif k in (curses.KEY_UP, ord("k")) and False:
                pass
            elif k == curses.KEY_UP:
                self.proc_cur = max(0, self.proc_cur - 1)
            elif k == ord("K") and self.procs:
                p = self.procs[self.proc_cur]
                if ui.confirm("Stop process %s (pid %s)?" % (p[4], p[0]), "Stop it", "Cancel", danger=True):
                    try:
                        os.kill(int(p[0]), 15)
                    except OSError as e:
                        ui.message("Could not stop it", [str(e)])
        if self.tab == 1:
            self.procs = processes()
        return True

    def set_tab(self, i):
        self.tab = i
        if i == 1:
            self.procs = processes()

    def draw(self, ui):
        W, H = ui.w, ui.h
        ui.text(0, 0, " " * W, "bar"); ui.text(0, 1, ICO("cpu") + "  Monitor", "bar")
        ui.text(0, max(14, W - 30), time.strftime("%a %d %b  %H:%M:%S").rjust(29), "bar", 29)
        x = 0
        ui.fill(1, 0, 1, W, "panel")
        for i, t in enumerate(self.TABS):
            lab = t if W >= 60 else t[:4]
            x += ui.button(1, x, lab, (lambda ii: (lambda: self.set_tab(ii)))(i), "sel" if i == self.tab else "panel")
        body = (self.overview, self.procs_tab, self.storage, self.network, self.nebula_tab)[self.tab]
        body(ui, 3, W, H - 4)
        ui.text(H - 1, 1, "Tab/←→ switch tab · 1-5 jump · r refresh · q quit", "dim", W - 2)

    def meter(self, ui, y, x, w, label, frac, text, warn=0.85):
        ui.text(y, x, label, "second", 10)
        bw = max(6, w - 10 - tui.width(text) - 2)
        ui.bar(y, x + 10, bw, frac, "danger" if frac > warn else "primary")
        ui.text(y, x + 11 + bw, text, "text", w - 11 - bw)

    def overview(self, ui, y, W, h):
        m = meminfo()
        tot, av = m.get("MemTotal", 1), m.get("MemAvailable", m.get("MemFree", 0))
        sw, swf = m.get("SwapTotal", 0), m.get("SwapFree", 0)
        w = W - 4
        ui.text(y, 2, "DEVICE", "dim")
        host = platform.node() or "device"
        ui.text(y + 1, 2, "%s  %s  ·  %s %s  ·  up %s" % (ICO("terminal"), host, platform.system(), platform.machine(), uptime()), "text", w)
        ui.text(y + 3, 2, "LIVE", "dim")
        self.meter(ui, y + 4, 2, w, "CPU", self.cpu / 100, "%4.0f%%  %d cores" % (self.cpu, self.cores))
        ui.text(y + 5, 12, self.spark(self.hist, max(10, w - 12)), "primary", w - 10)
        self.meter(ui, y + 6, 2, w, "Memory", (tot - av) / tot, "%s / %s" % (tui.human(tot - av), tui.human(tot)))
        if sw:
            self.meter(ui, y + 7, 2, w, "Swap", (sw - swf) / sw, "%s / %s" % (tui.human(sw - swf), tui.human(sw)))
        try:
            du = shutil.disk_usage(os.path.expanduser("~"))
            self.meter(ui, y + 8, 2, w, "Storage", du.used / du.total, "%s / %s" % (tui.human(du.used), tui.human(du.total)), 0.9)
        except OSError:
            pass
        b = self.bat
        if b:
            pct = b.get("percentage", 0)
            self.meter(ui, y + 9, 2, w, "Battery", pct / 100.0, "%d%%  %s" % (pct, str(b.get("status", "")).lower()), -1) if False else None
            ui.text(y + 9, 2, "Battery", "second", 10)
            bw = max(6, w - 10 - 24)
            ui.bar(y + 9, 12, bw, pct / 100.0, "danger" if pct < 20 else "primary")
            ui.text(y + 9, 13 + bw, "%d%%  %s%s" % (pct, str(b.get("status", "")).lower(), "  %.1f°C" % b["temperature"] if b.get("temperature") else ""), "text", 24)
        ui.text(y + 11, 2, "NETWORK", "dim")
        ui.text(y + 12, 2, "%s down %s/s    up %s/s" % (ICO("net"), tui.human(self.net_rate[0]), tui.human(self.net_rate[1])), "text", w)
        for i, ip in enumerate(local_ips()[:2]):
            ui.text(y + 13 + i, 4, ip, "dim", w)

    def procs_tab(self, ui, y, W, h):
        ui.text(y, 2, "%-7s %5s %5s %9s  %s" % ("PID", "CPU%", "MEM%", "TIME", "COMMAND"), "dim", W - 4)
        if not self.procs:
            self.procs = processes()
        vis = h - 3
        top = max(0, self.proc_cur - vis + 1)
        for r in range(min(vis, len(self.procs) - top)):
            i = top + r
            p = self.procs[i]
            ui.text(y + 1 + r, 1, (" %-7s %5s %5s %9s  %s" % (p[0], p[1], p[2], p[3], p[4])).ljust(W - 2), "sel" if i == self.proc_cur else "text", W - 2)
            ui.region(y + 1 + r, 1, 1, W - 2, (lambda ii: (lambda: setattr(self, "proc_cur", ii)))(i))
        ui.text(y + h - 2, 2, "↑↓ select · K stops the selected process (asks first)", "dim", W - 4)

    def storage(self, ui, y, W, h):
        ui.text(y, 2, "MOUNTED STORAGE", "dim")
        seen, row = set(), 1
        cands = [("Home", os.path.expanduser("~")), ("Shared storage", os.path.expanduser("~/storage/shared")), ("/sdcard", "/sdcard"), ("Termux", os.environ.get("PREFIX", "/usr")), ("Temp", "/tmp"), ("Root", "/")]
        for name, p in cands:
            if not os.path.isdir(p):
                continue
            try:
                du = shutil.disk_usage(p); key = (du.total, du.used)
            except OSError:
                continue
            if key in seen:
                continue
            seen.add(key)
            self.meter(ui, y + row, 2, W - 4, name[:9], du.used / du.total, "%s / %s" % (tui.human(du.used), tui.human(du.total)), 0.9)
            ui.text(y + row + 1, 12, p, "dim", W - 14)
            row += 3
        ui.text(y + row, 2, "BIGGEST IN HOME (top level)", "dim")
        try:
            sizes = []
            for n in os.listdir(os.path.expanduser("~"))[:80]:
                p = os.path.join(os.path.expanduser("~"), n)
                if os.path.isdir(p) and not os.path.islink(p):
                    t = 0
                    for r, _, fs in os.walk(p):
                        for f in fs[:200]:
                            try:
                                t += os.lstat(os.path.join(r, f)).st_size
                            except OSError:
                                pass
                        if t > 5e9:
                            break
                    sizes.append((t, n))
            for i, (t, n) in enumerate(sorted(sizes, reverse=True)[:max(0, h - row - 3)]):
                ui.text(y + row + 1 + i, 4, "%8s  %s" % (tui.human(t), n), "text", W - 6)
        except OSError:
            pass

    def network(self, ui, y, W, h):
        ui.text(y, 2, "THROUGHPUT", "dim")
        ui.text(y + 1, 2, "%s  down %s/s   up %s/s" % (ICO("net"), tui.human(self.net_rate[0]), tui.human(self.net_rate[1])), "primary", W - 4)
        rx, tx = net_bytes()
        ui.text(y + 2, 2, "since boot: %s received, %s sent" % (tui.human(rx), tui.human(tx)), "dim", W - 4)
        ui.text(y + 4, 2, "ADDRESSES", "dim")
        for i, ip in enumerate(local_ips()[:6]):
            ui.text(y + 5 + i, 4, ip, "text", W - 6)
        ui.text(y + 12, 2, "Public IP / location: run  ip  in Nebula", "dim", W - 4)

    def nebula_tab(self, ui, y, W, h):
        ver = read(os.path.join(paths.home(), "VERSION")).strip() or "?"
        rows = [("Version", "Nebula " + ver), ("Home", paths.home()), ("Data", paths.cfg()), ("AI", ai.describe() if hasattr(ai, "describe") else "?"),
                ("Palette", __import__("nebula_core.theme", fromlist=["x"]).current_name()), ("Icons", icons.mode()),
                ("Plugins", str(len(paths.plugin_dirs()))), ("Python", platform.python_version()),
                ("Terminal", "%dx%d  %s" % (ui.w, ui.h, os.environ.get("TERM", "")))]
        ui.text(y, 2, "NEBULA", "dim")
        for i, (k, v) in enumerate(rows):
            ui.text(y + 1 + i, 2, "%-10s" % k, "second", 10); ui.text(y + 1 + i, 13, v, "text", W - 15)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    nhelp.maybe_help("monitor", argv)
    tui.run(Monitor())


if __name__ == "__main__":
    main()
