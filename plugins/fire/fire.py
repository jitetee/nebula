"""fire: Firebase assistant on top of the official Firebase CLI."""
import argparse
import curses
import json
import os
import shlex
import subprocess
import sys

from nebula_core import ai, devtools as dt, help as nhelp, icons, tui

ICO = icons.get


def fb_cmd():
    e = os.environ.get("FIREBASE_BIN")
    if e:
        return shlex.split(e)
    p = dt.which("firebase")
    return [p] if p else None


def fb(args, cwd=None, timeout=300):
    c = fb_cmd()
    if not c:
        raise RuntimeError("The Firebase CLI is not installed. Run:  npm install -g firebase-tools")
    r = subprocess.run(c + args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)


def find_root(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(d, "firebase.json")):
            return d
        n = os.path.dirname(d)
        if n == d:
            return None
        d = n


def account():
    try:
        rc, out = fb(["login:list"])
    except RuntimeError as e:
        return None, str(e)
    for ln in out.splitlines():
        if "Logged in as" in ln:
            return ln.split("Logged in as", 1)[1].strip(), ""
    return None, "Not logged in. Run:  fire login"


def projects():
    rc, out = fb(["projects:list", "--json"])
    try:
        return [(p["projectId"], p.get("displayName", "")) for p in json.loads(out[out.index("{"):])["result"]]
    except (ValueError, KeyError):
        return []


def rc_projects(root):
    try:
        return json.load(open(os.path.join(root, ".firebaserc"))).get("projects", {})
    except (OSError, ValueError):
        return {}


def default_project(root):
    return rc_projects(root).get("default") or next(iter(rc_projects(root).values()), None)


def targets(root):
    """[{key, label, files:[...], note, risky}] from firebase.json."""
    try:
        cfg = json.load(open(os.path.join(root, "firebase.json")))
    except (OSError, ValueError):
        return []
    out = []

    def one(v):
        return v[0] if isinstance(v, list) and v else v

    h = one(cfg.get("hosting"))
    if h:
        pub = h.get("public", "public")
        n = sum(len(f) for _, _, f in os.walk(os.path.join(root, pub))) if os.path.isdir(os.path.join(root, pub)) else 0
        out.append(dict(key="hosting", label="Hosting", files=[pub], note="%s/ (%d files)" % (pub, n), risky=False, problem=("The folder “%s” is missing: build your site first." % pub) if not os.path.isdir(os.path.join(root, pub)) else ("“%s” is empty." % pub if n == 0 else "")))
    f = one(cfg.get("functions"))
    if f:
        src = f.get("source", "functions") if isinstance(f, dict) else "functions"
        nm = os.path.isdir(os.path.join(root, src, "node_modules"))
        out.append(dict(key="functions", label="Functions", files=[src], note="%s/ (code that runs on Google's servers, can cost money)" % src, risky=False, problem="" if nm or not os.path.isdir(os.path.join(root, src)) else "Run npm install in %s/ first." % src))
    for key, label in (("firestore", "Firestore rules"), ("storage", "Storage rules"), ("database", "Realtime Database rules")):
        v = cfg.get(key)
        if v:
            v = one(v)
            rules = (v.get("rules") if isinstance(v, dict) else None) or {"firestore": "firestore.rules", "storage": "storage.rules", "database": "database.rules.json"}[key]
            out.append(dict(key=key, label=label, files=[rules] + ([v["indexes"]] if isinstance(v, dict) and v.get("indexes") else []), note="%s: decides who can read and write your data" % rules, risky=True,
                            problem="" if os.path.isfile(os.path.join(root, rules)) else "%s is missing." % rules))
    return out


def changed(root, files):
    """True if those files have uncommitted changes."""
    if not dt.in_repo(root):
        return False
    rc, out, _ = dt.git(["status", "--porcelain", "--"] + files, root)
    return bool(out.strip())


def advice(root, ts):
    a = []
    if dt.in_repo(root):
        _, br, _ = dt.git(["rev-parse", "--abbrev-ref", "HEAD"], root)
        br = br.strip()
        if br not in ("main", "master"):
            a.append(("warn", "You are on branch “%s”, not main. Deploy from main unless this is on purpose." % br))
        _, st, _ = dt.git(["status", "--porcelain"], root)
        if st.strip():
            a.append(("warn", "You have uncommitted changes. Commit them (gitx) so you can roll back this deploy."))
        _, ab, _ = dt.git(["rev-list", "--count", "@{u}..HEAD"], root)
        if ab.strip().isdigit() and int(ab) > 0:
            a.append(("info", "%s commit(s) not pushed yet." % ab.strip()))
    for t in ts:
        if t["problem"]:
            a.append(("bad", "%s: %s" % (t["label"], t["problem"])))
        elif changed(root, t["files"]):
            a.append(("info", "%s changed since the last commit." % t["label"]))
    return a or [("ok", "Nothing blocks a deploy.")]


def deploy(root, keys, project, preview=None, log=None):
    only = ",".join({"firestore": "firestore", "storage": "storage", "database": "database"}.get(k, k) for k in keys)
    args = (["hosting:channel:deploy", preview, "--expires", "7d"] if preview else ["deploy", "--only", only]) + (["--project", project] if project else []) + ["--non-interactive"]
    rc, out = fb(args, root, timeout=900)
    return rc, out


def status_lines(root):
    acct, why = account()
    lines = ["Account   %s" % (acct or "✖ " + why)]
    if not root:
        return lines + ["Project   (no firebase.json here or above)"]
    lines.append("Project   %s   (config: %s)" % (default_project(root) or "none set: fire use <project>", os.path.relpath(os.path.join(root, "firebase.json"))))
    ts = targets(root)
    for t in ts:
        lines.append("  %-24s %s%s" % (t["label"], t["note"], "   ✎ changed" if changed(root, t["files"]) else ""))
    for lvl, text in advice(root, ts):
        lines.append("  %s %s" % ({"bad": "✖", "warn": "⚠", "info": "▸", "ok": "✔"}[lvl], text))
    return lines


def cli(a):
    root = find_root()
    if a.cmd in (None, "status"):
        print("\n".join(status_lines(root))); return 0
    if a.cmd == "login":
        c = fb_cmd()
        if not c:
            print("✖ Firebase CLI missing: npm install -g firebase-tools"); return 1
        return subprocess.call(c + ["login", "--no-localhost"])
    if a.cmd == "projects":
        try:
            for pid, name in projects():
                print("  %-28s %s" % (pid, name))
        except RuntimeError as e:
            print("✖ %s" % e); return 1
        return 0
    if a.cmd == "use":
        if not root or not a.args:
            print("✖ run inside a Firebase project folder: fire use <project-id>"); return 2
        rc = rc_projects(root); rc["default"] = a.args[0]
        json.dump({"projects": rc}, open(os.path.join(root, ".firebaserc"), "w"), indent=2); print("✔ default project: %s" % a.args[0]); return 0
    if a.cmd in ("deploy", "preview"):
        if not root:
            print("✖ no firebase.json found here or above"); return 1
        acct, why = account()
        if not acct:
            print("✖ %s" % why); return 1
        ts = {t["key"]: t for t in targets(root)}
        keys = [k for k in (a.args if a.cmd == "deploy" else ["hosting"]) if k in ts] if (a.args or a.cmd == "preview") else list(ts)
        unknown = [k for k in (a.args if a.cmd == "deploy" else []) if k not in ts]
        if unknown:
            print("✖ not in your firebase.json: %s (have: %s)" % (", ".join(unknown), ", ".join(ts) or "nothing")); return 2
        for k in keys:
            if ts[k]["problem"]:
                print("✖ %s: %s" % (ts[k]["label"], ts[k]["problem"])); return 1
        proj = a.project or default_project(root)
        print("Deploying %s to %s as %s%s" % (", ".join(keys), proj or "(default)", acct, "  [PREVIEW]" if a.cmd == "preview" else ""))
        if any(ts[k]["risky"] for k in keys) and not a.yes:
            typed = input("Rules decide who can read your data. Type  rules  to continue: ").strip() if sys.stdin.isatty() else ""
            if typed != "rules":
                print("✖ cancelled"); return 1
        elif not a.yes and not (sys.stdin.isatty() and input("Continue? [y/N] ").lower().startswith("y")):
            print("cancelled"); return 1
        rc, out = deploy(root, keys, proj, preview=(a.args[0] if a.cmd == "preview" and a.args else "preview") if a.cmd == "preview" else None)
        print(out.strip()); return rc
    if a.cmd == "ask":
        try:
            ctx = dt.project_context(root or os.getcwd()) + "\n\nFirebase status:\n" + "\n".join(status_lines(root))
            print(ai.ask("You help someone deploy a Firebase project. Use only this context.\n\n%s\n\nQuestion: %s" % (ctx, " ".join(a.args) or "Should I deploy now, and what?"), "Be concrete and short."))
            return 0
        except (ai.AIError, RuntimeError) as e:
            print("✖ %s" % e); return 1
    return 2


class FireApp(tui.App):
    tick_ms = 3000

    def __init__(self):
        self.root = find_root()
        self.acct, self.why = (None, "")
        self.ts, self.pick, self.cur, self.msg, self.proj = [], set(), 0, "", None

    def start(self, ui):
        self.refresh()
        if not self.root:
            ui.message("Firebase", ["No firebase.json here or above.", "Run  firebase init  in your project folder first."])

    def refresh(self):
        self.acct, self.why = account()
        self.ts = targets(self.root) if self.root else []
        self.proj = default_project(self.root) if self.root else None
        self.pick = {t["key"] for t in self.ts if changed(self.root, t["files"])} & {t["key"] for t in self.ts} if self.root else set()

    def a_login(self, ui):
        ui.suspend(lambda: subprocess.call(fb_cmd() + ["login", "--no-localhost"]) if fb_cmd() else print("Firebase CLI missing: npm install -g firebase-tools"))
        self.refresh()

    def a_project(self, ui):
        try:
            ps = projects()
        except RuntimeError as e:
            ui.message("Firebase", [str(e)]); return
        if not ps:
            ui.message("Projects", ["No projects found (are you logged in?)"]); return
        c = ui.choose("Use which project?", [(a, b) for a, b in ps])
        if c is not None and self.root:
            rc = rc_projects(self.root); rc["default"] = ps[c][0]
            json.dump({"projects": rc}, open(os.path.join(self.root, ".firebaserc"), "w"), indent=2); self.refresh(); self.msg = "Project: " + ps[c][0]

    def a_deploy(self, ui, preview=False):
        if not self.acct:
            ui.message("Not logged in", [self.why or "Run login first."]); return
        keys = [t["key"] for t in self.ts if t["key"] in self.pick] if not preview else ["hosting"]
        if not keys:
            ui.message("Deploy", ["Tick what to deploy first (Space)."]); return
        bad = [t for t in self.ts if t["key"] in keys and t["problem"]]
        if bad:
            ui.message("Cannot deploy yet", [t["label"] + ": " + t["problem"] for t in bad]); return
        risky = any(t["risky"] for t in self.ts if t["key"] in keys)
        summary = "Deploy %s\nto project %s\nas %s%s" % (", ".join(keys), self.proj or "(default)", self.acct, "\n(preview link, not live)" if preview else "")
        if not ui.confirm(summary + ("\n\nRules decide who can read your data." if risky else ""), "Deploy", "Cancel", danger=risky and not preview, typed="rules" if risky and not preview else None, title="Deploy"):
            return
        self.msg = "Deploying …"; ui.redraw()
        rc, out = deploy(self.root, keys, self.proj, preview="preview" if preview else None)
        ui.pager("%s: %s" % ("Deploy finished" if rc == 0 else "Deploy FAILED", ", ".join(keys)), out.splitlines())
        self.msg = "Deployed" if rc == 0 else "Deploy failed"
        self.refresh()

    def a_ask(self, ui):
        q = ui.prompt("Ask about deploying", "Should I deploy now, and what?")
        if q:
            try:
                ctx = dt.project_context(self.root or os.getcwd()) + "\n\nFirebase status:\n" + "\n".join(status_lines(self.root))
                ui.pager("Answer", ai.ask("You help someone deploy a Firebase project. Use only this context.\n\n%s\n\nQuestion: %s" % (ctx, q), "Be concrete and short.").splitlines())
            except (ai.AIError, RuntimeError) as e:
                ui.message("AI not available", [str(e)])

    def key(self, ui, k):
        if k in (ord("q"), 27):
            return False
        if k in (curses.KEY_DOWN, ord("j")):
            self.cur = min(len(self.ts) - 1, self.cur + 1)
        elif k in (curses.KEY_UP, ord("k")):
            self.cur = max(0, self.cur - 1)
        elif k == ord(" ") and self.ts:
            self.pick ^= {self.ts[self.cur]["key"]}
        elif k in (ord("d"), *tui.ENTER):
            self.a_deploy(ui)
        elif k == ord("v"):
            self.a_deploy(ui, True)
        elif k == ord("p"):
            self.a_project(ui)
        elif k == ord("l"):
            self.a_login(ui)
        elif k == ord("i"):
            self.a_ask(ui)
        elif k == ord("r"):
            self.refresh()
        elif k == ord("?"):
            ui.pager("fire help", (nhelp.render("fire", color=False) or "").split("\n"))
        return True

    def tick(self, ui):
        pass

    def draw(self, ui):
        W, H = ui.w, ui.h
        ui.text(0, 0, " " * W, "bar"); ui.text(0, 1, ICO("cloud") + "  Firebase", "bar")
        ui.fill(1, 0, 1, W, "panel")
        x = 0
        for ic, lab, cb in (("rocket", "Deploy", lambda: self.a_deploy(ui)), ("eye", "Preview", lambda: self.a_deploy(ui, True)), ("folder", "Project", lambda: self.a_project(ui)),
                            ("user", "Login", lambda: self.a_login(ui)), ("bolt", "Ask", lambda: self.a_ask(ui))):
            t = ICO(ic) if W < 56 else "%s %s" % (ICO(ic), lab)
            x += ui.button(1, x, t, cb, "panel")
        ui.text(3, 2, "Account", "dim"); ui.text(3, 12, self.acct or ("✖ " + (self.why or "unknown")), "second" if self.acct else "danger", W - 14)
        ui.text(4, 2, "Project", "dim"); ui.text(4, 12, self.proj or "none: press p", "primary" if self.proj else "accent", W - 14)
        ui.text(6, 2, "WHAT TO DEPLOY  (Space ticks · changed items are pre-ticked)", "dim", W - 4)
        for i, t in enumerate(self.ts):
            y = 7 + i * 2
            sel = i == self.cur
            ui.text(y, 0, " " * W, "sel" if sel else "text", W)
            ui.text(y, 1, "[x]" if t["key"] in self.pick else "[ ]", "sel" if sel else "second", 3)
            ui.text(y, 5, t["label"] + ("  ✎ changed" if changed(self.root, t["files"]) else ""), "sel" if sel else "primary", W - 7)
            ui.text(y + 1, 5, t["problem"] or t["note"], "danger" if t["problem"] else "dim", W - 7)
            ui.region(y, 0, 2, W, (lambda ii: (lambda: (setattr(self, "cur", ii), self.pick.symmetric_difference_update({self.ts[ii]["key"]}))))(i))
        if not self.ts:
            ui.text(8, 3, "No deploy targets in firebase.json", "dim")
        ay = 8 + len(self.ts) * 2
        for i, (lvl, text) in enumerate(advice(self.root, self.ts)[:4] if self.root else []):
            ui.text(ay + i, 2, {"bad": "✖", "warn": "⚠", "info": "▸", "ok": "✔"}[lvl] + " " + text, {"bad": "danger", "warn": "accent", "info": "text", "ok": "second"}[lvl], W - 4)
        ui.text(H - 1, 1, (self.msg + "   " if self.msg else "") + "Space tick · d deploy · v preview · p project · l login · i ask · ? help", "accent" if self.msg else "dim", W - 2)

    def click(self, ui, y, x, double):
        pass


def main():
    argv = sys.argv[1:]
    nhelp.maybe_help("fire", argv)
    ap = argparse.ArgumentParser(prog="fire", add_help=False)
    ap.add_argument("cmd", nargs="?"); ap.add_argument("args", nargs="*"); ap.add_argument("--project"); ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    if not a.cmd and sys.stdin.isatty() and sys.stdout.isatty():
        tui.run(FireApp()); return 0
    return cli(a)


if __name__ == "__main__":
    sys.exit(main())
