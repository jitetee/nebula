"""gitx: interactive git with an advisor and safety checks."""
import argparse
import curses
import os
import re
import subprocess
import sys

from nebula_core import ai, devtools as dt, help as nhelp, icons, tui

ICO = icons.get
PROTECTED = ("main", "master", "production", "prod", "release", "develop")
SECRET_RE = re.compile(r"(AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AIza[0-9A-Za-z_\-]{30,}|sk-[A-Za-z0-9]{32,}|xox[baprs]-[A-Za-z0-9-]{10,})")


def G(args, cwd=None):
    return dt.git(args, cwd)


def state(cwd=None):
    """Everything the dashboard and advisor need, from one `git status` call plus a few cheap ones."""
    rc, out, _ = G(["status", "--porcelain=v2", "--branch"], cwd)
    s = dict(branch="", upstream="", ahead=0, behind=0, staged=[], unstaged=[], untracked=[], conflicts=[], detached=False, oid="")
    for ln in out.splitlines():
        if ln.startswith("# branch.head "):
            s["branch"] = ln.split(" ", 2)[2]; s["detached"] = s["branch"] == "(detached)"
        elif ln.startswith("# branch.upstream "):
            s["upstream"] = ln.split(" ", 2)[2]
        elif ln.startswith("# branch.ab "):
            m = re.match(r"# branch.ab \+(\d+) -(\d+)", ln)
            if m:
                s["ahead"], s["behind"] = int(m.group(1)), int(m.group(2))
        elif ln.startswith("1 ") or ln.startswith("2 "):
            xy, path = ln.split(" ")[1], ln.split(" ", 8)[-1] if ln.startswith("1 ") else ln.split(" ", 9)[-1].split("\t")[0]
            if xy[0] != ".":
                s["staged"].append((xy[0], path))
            if xy[1] != ".":
                s["unstaged"].append((xy[1], path))
        elif ln.startswith("u "):
            s["conflicts"].append(ln.split(" ", 10)[-1])
        elif ln.startswith("? "):
            s["untracked"].append(("?", ln[2:]))
    _, st, _ = G(["stash", "list"], cwd)
    s["stashes"] = len([l for l in st.splitlines() if l])
    _, lg, _ = G(["log", "--oneline", "--decorate=short", "-8"], cwd)
    s["log"] = lg.splitlines()
    s["has_commits"] = G(["rev-parse", "HEAD"], cwd)[0] == 0
    s["remote"] = bool(G(["remote"], cwd)[1].strip())
    return s


def staged_secrets(cwd=None):
    _, d, _ = G(["diff", "--cached", "-U0"], cwd)
    hits = []
    cur = ""
    for ln in d.splitlines():
        if ln.startswith("+++ b/"):
            cur = ln[6:]
        elif ln.startswith("+") and SECRET_RE.search(ln):
            hits.append(cur)
    return sorted(set(hits))


def big_staged(cwd=None, mb=50):
    out = []
    root = dt.repo_root(cwd) or "."
    for _, p in state(cwd)["staged"]:
        try:
            if os.path.getsize(os.path.join(root, p)) > mb * 1024 * 1024:
                out.append(p)
        except OSError:
            pass
    return out


def advise(s, cwd=None):
    """[(level 'bad'|'warn'|'ok'|'info', text, key)] most important first."""
    a = []
    if s["conflicts"]:
        a.append(("bad", "Fix merge conflicts in %d file(s), then stage them and commit." % len(s["conflicts"]), "x"))
    if s["detached"]:
        a.append(("warn", "You are on a detached HEAD. Make a branch (b) before committing or you may lose work.", "b"))
    sec = staged_secrets(cwd) if s["staged"] else []
    if sec:
        a.append(("bad", "Possible secret in staged changes (%s). Unstage it before committing." % ", ".join(sec[:2]), "space"))
    big = big_staged(cwd) if s["staged"] else []
    if big:
        a.append(("warn", "Large file staged (%s, over 50 MB). GitHub rejects files over 100 MB." % big[0], "space"))
    if s["staged"]:
        a.append(("info", "%d file(s) staged. Commit them (c)." % len(s["staged"]), "c"))
    if s["unstaged"] or s["untracked"]:
        a.append(("info", "%d changed file(s) not staged. Stage (Space/a) then commit (c)." % (len(s["unstaged"]) + len(s["untracked"])), "a"))
        if s["branch"] in PROTECTED:
            a.append(("warn", "You are editing directly on %s. A feature branch (b) keeps it safe." % s["branch"], "b"))
    if s["has_commits"] and not s["upstream"] and not s["detached"]:
        a.append(("info", ("Publish this branch: push will set its upstream (P)." if s["remote"] else "No remote yet: git remote add origin <url>"), "P"))
    elif s["ahead"] and s["behind"]:
        a.append(("warn", "Diverged: %d ahead, %d behind. Pull with rebase (p), then push. Do not force-push." % (s["ahead"], s["behind"]), "p"))
    elif s["behind"]:
        a.append(("info", "%d new commit(s) upstream. Pull (p)." % s["behind"], "p"))
    elif s["ahead"]:
        a.append(("info", "%d commit(s) not pushed yet. Push (P)." % s["ahead"], "P"))
    if not a:
        a.append(("ok", "All clean and in sync with %s." % (s["upstream"] or "nothing yet"), ""))
    order = {"bad": 0, "warn": 1, "info": 2, "ok": 3}
    return sorted(a, key=lambda x: order[x[0]])


def merge_check(target, cwd=None):
    """(can_merge, info lines, conflicted files). Never changes your files."""
    _, cnt, _ = G(["rev-list", "--count", "HEAD..%s" % target], cwd)
    _, stat, _ = G(["diff", "--stat", "HEAD...%s" % target], cwd)
    lines = ["%s commit(s) would come in from %s" % (cnt.strip() or "0", target)] + [l for l in stat.strip().splitlines()[-6:]]
    rc, out, err = G(["merge-tree", "--write-tree", "--name-only", "HEAD", target], cwd)
    conflicts = []
    if rc == 1:
        conflicts = [l for l in out.splitlines()[1:] if l and not l.startswith(("Auto-merging", "CONFLICT"))][:20]
        conflicts = conflicts or ["(see git status after merging)"]
    elif rc not in (0, 1):    # older git without merge-tree --write-tree: try a real merge and undo it
        r, _, _ = G(["merge", "--no-commit", "--no-ff", target], cwd)
        if r != 0:
            _, u, _ = G(["diff", "--name-only", "--diff-filter=U"], cwd)
            conflicts = u.split() or ["(conflicts)"]
        G(["merge", "--abort"], cwd)
    return (not conflicts, lines, conflicts)


def force_info(branch, cwd=None):
    """What a force-push would throw away: commits on the remote that you do not have."""
    G(["fetch", "--quiet"], cwd)
    rc, out, _ = G(["rev-list", "--oneline", "%s..origin/%s" % (branch, branch)], cwd)
    return out.splitlines() if rc == 0 else []


def suggest_message(cwd=None):
    _, d, _ = G(["diff", "--cached", "--stat"], cwd)
    _, p, _ = G(["diff", "--cached", "-U1"], cwd)
    q = "Write ONE git commit message (imperative mood, max 70 chars, no quotes, no period) for these staged changes.\n\n%s\n\n%s" % (d[:1200], p[:3500])
    return ai.ask(q, "Reply with only the commit message.").strip().splitlines()[0].strip("`\"' ")[:100]


def ask_repo(question, cwd=None):
    return ai.ask("You are a senior engineer helping with this project. Use only this context; say what you cannot tell.\n\n%s\n\nQuestion: %s" % (dt.project_context(cwd), question), "Be concrete and short. Give commands when useful.")


# ── plain commands ──
def cli(a):
    cwd = os.getcwd()
    if not dt.in_repo(cwd):
        print("✖ This folder is not a git repository. Run:  git init"); return 1
    s = state(cwd)
    if a.cmd == "status":
        print("%s %s%s" % (ICO("branch"), s["branch"], ("  ↑%d ↓%d" % (s["ahead"], s["behind"])) if s["upstream"] else "  (no upstream)"))
        print("  staged %d · modified %d · untracked %d%s" % (len(s["staged"]), len(s["unstaged"]), len(s["untracked"]), " · CONFLICTS %d" % len(s["conflicts"]) if s["conflicts"] else ""))
        return 0
    if a.cmd == "advise":
        for lvl, text, _ in advise(s, cwd):
            print("  %s %s" % ({"bad": "✖", "warn": "⚠", "info": "▸", "ok": "✔"}[lvl], text))
        return 0
    if a.cmd == "commit":
        if a.all:
            G(["add", "-A"], cwd)
        sec = staged_secrets(cwd)
        if sec and not a.force_secrets:
            print("✖ possible secret in: %s. Unstage it, or use --force-secrets if you are sure." % ", ".join(sec)); return 1
        msg = a.message
        if not msg:
            try:
                msg = suggest_message(cwd); print("AI suggests: %s" % msg)
            except ai.AIError as e:
                print("✖ give a message with -m (%s)" % e); return 1
        rc, out, err = G(["commit", "-m", msg], cwd)
        print((out or err).strip().splitlines()[0] if (out or err).strip() else ""); return rc
    if a.cmd == "push":
        if s["behind"] and not a.no_check:
            print("✖ the remote has %d commit(s) you do not have. Pull first:  git pull --rebase" % s["behind"]); return 1
        args = ["push"] + ([] if s["upstream"] else ["-u", "origin", s["branch"]])
        rc, out, err = G(args, cwd); print((out + err).strip()); return rc
    if a.cmd == "force":
        lost = force_info(s["branch"], cwd)
        print("A force-push replaces origin/%s with your version." % s["branch"])
        print("Commits on the remote that would be LOST: %d" % len(lost))
        for l in lost[:8]:
            print("   - " + l)
        if s["branch"] in PROTECTED:
            print("⚠ %s is a protected-looking branch name." % s["branch"])
        typed = a.confirm if a.confirm is not None else (input("Type the branch name to force-push: ").strip() if sys.stdin.isatty() else "")
        if typed != s["branch"]:
            print("✖ cancelled (name did not match)"); return 1
        rc, out, err = G(["push", "--force-with-lease"], cwd); print((out + err).strip()); return rc
    if a.cmd == "merge":
        if not a.args:
            print("✖ which branch? gitx merge <branch>"); return 2
        ok, lines, conflicts = merge_check(a.args[0], cwd)
        print("\n".join(lines))
        if conflicts:
            print("✖ would conflict in:\n   " + "\n   ".join(conflicts)); return 1
        print("✔ no conflicts predicted")
        if a.check:
            return 0
        if not (a.yes or (sys.stdin.isatty() and input("Merge now? [y/N] ").lower().startswith("y"))):
            print("cancelled"); return 1
        rc, out, err = G(["merge", "--no-edit", a.args[0]], cwd); print((out + err).strip().splitlines()[-1] if (out + err).strip() else ""); return rc
    if a.cmd == "ask":
        try:
            print(ask_repo(" ".join(a.args), cwd)); return 0
        except ai.AIError as e:
            print("✖ %s" % e); return 1
    return 2


# ── dashboard ──
class Dash(tui.App):
    tick_ms = 2000

    def __init__(self):
        self.cwd = dt.repo_root() or os.getcwd()
        self.s = None
        self.cur = 0
        self.msg = ""
        self.adv = []

    def refresh(self):
        self.s = state(self.cwd)
        self.adv = advise(self.s, self.cwd)

    def start(self, ui):
        if not dt.in_repo(self.cwd):
            if ui.confirm("This folder is not a git repository.\nCreate one here (git init)?", "git init", "Quit"):
                G(["init"], self.cwd)
            else:
                self.quit = True; return
        self.refresh()

    def files(self):
        s = self.s
        return [("staged", c, p) for c, p in s["staged"]] + [("unstaged", c, p) for c, p in s["unstaged"]] + [("untracked", c, p) for c, p in s["untracked"]] + [("conflict", "U", p) for p in s["conflicts"]]

    def tick(self, ui):
        self.refresh()

    def run_git(self, ui, args, ok_msg):
        rc, out, err = G(args, self.cwd)
        self.refresh()
        if rc:
            ui.message("git said", (err or out).strip().splitlines()[-6:] or ["failed"])
        else:
            self.msg = ok_msg

    def toggle(self, ui):
        f = self.files()
        if not f or self.cur >= len(f):
            return
        kind, c, p = f[self.cur]
        if kind == "staged":
            self.run_git(ui, ["reset", "-q", "HEAD", "--", p], "Unstaged " + p)
        else:
            self.run_git(ui, ["add", "--", p], "Staged " + p)

    def a_commit(self, ui):
        s = self.s
        if s["conflicts"]:
            ui.message("Conflicts", ["Fix the conflicts and stage those files first."]); return
        if not s["staged"]:
            if (s["unstaged"] or s["untracked"]) and ui.confirm("Nothing is staged.\nStage everything and commit?", "Stage all", "Cancel"):
                G(["add", "-A"], self.cwd); self.refresh()
            else:
                return
        sec = staged_secrets(self.cwd)
        if sec and not ui.confirm("Possible SECRET in: %s\nCommitting it can leak it forever.\nCommit anyway?" % ", ".join(sec[:3]), "Commit anyway", "Stop", danger=True, typed="commit"):
            return
        how = ui.choose("Commit message", ["Write it myself", "Suggest one with AI"])
        if how is None:
            return
        pre = ""
        if how == 1:
            try:
                pre = suggest_message(self.cwd)
            except ai.AIError as e:
                ui.message("AI not available", [str(e), "", "Type the message yourself."])
        m = ui.prompt("Commit message", pre)
        if m:
            self.run_git(ui, ["commit", "-m", m], "Committed")

    def a_push(self, ui):
        s = self.s
        if s["behind"]:
            ui.message("Pull first", ["The remote has %d commit(s) you do not have." % s["behind"], "Press p to pull (rebase), then push again."]); return
        args = ["push"] + ([] if s["upstream"] else ["-u", "origin", s["branch"]])
        if not s["upstream"] and not ui.confirm("Publish branch “%s” to origin?" % s["branch"], "Publish", "Cancel"):
            return
        self.run_git(ui, args, "Pushed")

    def a_force(self, ui):
        s = self.s
        if not s["upstream"]:
            ui.message("Force push", ["This branch has no upstream yet: a normal push (P) is enough."]); return
        lost = force_info(s["branch"], self.cwd)
        lines = ["Force-pushing replaces origin/%s with your version." % s["branch"], "Remote commits that would be LOST: %d" % len(lost)] + ["  - " + l for l in lost[:5]]
        if s["branch"] in PROTECTED:
            lines.append("⚠ %s looks like a shared branch: others may lose work." % s["branch"])
        lines.append("It uses --force-with-lease, so it stops if someone pushed meanwhile.")
        if ui.confirm("\n".join(lines), "Force push", "Cancel", danger=True, typed=s["branch"], title="Force push"):
            self.run_git(ui, ["push", "--force-with-lease"], "Force-pushed")

    def a_pull(self, ui):
        c = ui.choose("Pull how?", ["Rebase (clean history, recommended)", "Merge", "Fast-forward only (safest)"])
        if c is not None:
            self.run_git(ui, ["pull"] + [["--rebase"], ["--no-rebase"], ["--ff-only"]][c], "Pulled")

    def a_branch(self, ui):
        rc, out, _ = G(["branch", "--format=%(refname:short)|%(HEAD)"], self.cwd)
        bs = [l.split("|") for l in out.splitlines()]
        c = ui.choose("Branches (Enter = switch)", [("+ New branch", "")] + [(b, "current" if h == "*" else "") for b, h in bs] + [("- Delete a branch…", "")])
        if c is None:
            return
        if c == 0:
            n = ui.prompt("New branch name", "")
            if n:
                self.run_git(ui, ["switch", "-c", n], "On new branch " + n)
        elif c == len(bs) + 1:
            d = ui.choose("Delete which branch?", [b for b, h in bs if h != "*"])
            names = [b for b, h in bs if h != "*"]
            if d is not None and ui.confirm("Delete branch “%s”?\n(It must be fully merged, otherwise git refuses.)" % names[d], "Delete", "Cancel", danger=True):
                self.run_git(ui, ["branch", "-d", names[d]], "Deleted " + names[d])
        else:
            if (self.s["unstaged"] or self.s["staged"]) and not ui.confirm("You have uncommitted changes.\nSwitching may carry them along or fail.", "Switch anyway", "Cancel"):
                return
            self.run_git(ui, ["switch", bs[c - 1][0]], "Switched to " + bs[c - 1][0])

    def a_merge(self, ui):
        _, out, _ = G(["branch", "--format=%(refname:short)"], self.cwd)
        others = [b for b in out.split() if b != self.s["branch"]]
        if not others:
            ui.message("Merge", ["There is no other branch to merge."]); return
        c = ui.choose("Merge which branch into %s?" % self.s["branch"], others)
        if c is None:
            return
        ok, lines, conflicts = merge_check(others[c], self.cwd)
        body = lines + [""] + (["✖ Would conflict in:"] + ["   " + x for x in conflicts] if conflicts else ["✔ No conflicts predicted."])
        if conflicts:
            ui.message("Merge check", body + ["", "Not merging. Resolve first (rebase the branch, or merge in a copy)."]); return
        if ui.confirm("\n".join(body) + "\n\nMerge into %s now?" % self.s["branch"], "Merge", "Cancel", title="Merge"):
            self.run_git(ui, ["merge", "--no-edit", others[c]], "Merged " + others[c])

    def a_stash(self, ui):
        c = ui.choose("Stash", ["Stash my changes", "Restore the latest stash (pop)", "Show stashes"])
        if c == 0:
            self.run_git(ui, ["stash", "push", "-u"], "Stashed")
        elif c == 1:
            self.run_git(ui, ["stash", "pop"], "Restored")
        elif c == 2:
            ui.pager("Stashes", G(["stash", "list"], self.cwd)[1].splitlines() or ["(none)"])

    def a_discard(self, ui):
        f = self.files()
        if not f or self.cur >= len(f):
            return
        kind, c, p = f[self.cur]
        if kind == "staged":
            ui.message("Discard", ["Unstage it first (Space)."]); return
        if ui.confirm("Throw away your changes to\n%s ?\nThis cannot be undone." % p, "Discard", "Cancel", danger=True, typed="discard"):
            self.run_git(ui, (["clean", "-f", "--", p] if kind == "untracked" else ["checkout", "--", p]), "Discarded " + p)

    def a_undo(self, ui):
        s = self.s
        if not s["has_commits"]:
            return
        pushed = s["upstream"] and s["ahead"] == 0
        if ui.confirm("Undo the last commit (keeps your changes staged)?" + ("\n⚠ It is already pushed: you would need a force-push to publish the undo." if pushed else ""), "Undo commit", "Cancel", danger=bool(pushed)):
            self.run_git(ui, ["reset", "--soft", "HEAD~1"], "Last commit undone")

    def a_log(self, ui):
        ui.pager("History", G(["log", "--graph", "--oneline", "--decorate", "-60"], self.cwd)[1].splitlines())

    def a_diff(self, ui):
        f = self.files()
        if f and self.cur < len(f):
            kind, c, p = f[self.cur]
            args = ["diff", "--cached", "--", p] if kind == "staged" else ["diff", "--", p]
            ui.pager("Diff: " + p, (G(args, self.cwd)[1] or "(no diff: new file?)").splitlines())

    def a_ask(self, ui):
        q = ui.prompt("Ask about this repo", "", "e.g. should I merge? what changed? is it safe to deploy?")
        if q:
            self.msg = "Thinking …"; ui.redraw()
            try:
                ui.pager("Answer", ask_repo(q, self.cwd).splitlines())
            except ai.AIError as e:
                ui.message("AI not available", [str(e)])
            self.msg = ""

    BUTTONS = [("up", "Stage", "toggle"), ("ok", "Commit", "a_commit"), ("upload", "Push", "a_push"), ("down", "Pull", "a_pull"), ("branch", "Branch", "a_branch"),
               ("link", "Merge", "a_merge"), ("archive", "Stash", "a_stash"), ("info", "Log", "a_log"), ("bolt", "Ask", "a_ask"), ("warn", "Force", "a_force")]

    def key(self, ui, k):
        f = self.files()
        if k in (ord("q"), 27):
            return False
        if k in (curses.KEY_DOWN, ord("j")):
            self.cur = min(len(f) - 1, self.cur + 1)
        elif k in (curses.KEY_UP, ord("k")):
            self.cur = max(0, self.cur - 1)
        elif k == ord(" "):
            self.toggle(ui)
        elif k == ord("a"):
            self.run_git(ui, ["add", "-A"], "Staged everything")
        elif k == ord("c"):
            self.a_commit(ui)
        elif k == ord("P"):
            self.a_push(ui)
        elif k == ord("F"):
            self.a_force(ui)
        elif k == ord("p"):
            self.a_pull(ui)
        elif k == ord("b"):
            self.a_branch(ui)
        elif k == ord("m"):
            self.a_merge(ui)
        elif k == ord("s"):
            self.a_stash(ui)
        elif k == ord("x"):
            self.a_discard(ui)
        elif k == ord("u"):
            self.a_undo(ui)
        elif k == ord("l"):
            self.a_log(ui)
        elif k in tui.ENTER:
            self.a_diff(ui)
        elif k == ord("i"):
            self.a_ask(ui)
        elif k == ord("r"):
            self.refresh()
        elif k == ord("?"):
            ui.pager("gitx help", (nhelp.render("gitx", color=False) or "").split("\n"))
        return True

    def draw(self, ui):
        if not self.s:
            return
        W, H = ui.w, ui.h
        s = self.s
        ui.text(0, 0, " " * W, "bar")
        ui.text(0, 1, "%s  %s" % (ICO("branch"), s["branch"] or "?"), "bar", W - 4)
        badge = ("↑%d ↓%d" % (s["ahead"], s["behind"])) if s["upstream"] else "no upstream"
        ui.text(0, max(14, W - len(badge) - 2), badge, "bar")
        ui.fill(1, 0, 1, W, "panel")
        x = 0
        for ic, lab, fn in self.BUTTONS:
            t = ICO(ic) if W < 66 else "%s %s" % (ICO(ic), lab)
            if x + tui.width(t) + 3 > W:
                break
            x += ui.button(1, x, t, (lambda f: (lambda: (self.toggle(ui) if f == "toggle" else getattr(self, f)(ui))))(fn), "panel_d" if fn == "a_force" else "panel")
        f = self.files()
        wide = W >= 90
        lw = W - 44 if wide else W
        # advisor
        ay = 2
        ui.text(ay, 1, "WHAT TO DO", "dim")
        for i, (lvl, text, key) in enumerate(self.adv[:3]):
            col = {"bad": "danger", "warn": "accent", "info": "text", "ok": "second"}[lvl]
            ui.text(ay + 1 + i, 1, {"bad": "✖", "warn": "⚠", "info": "▸", "ok": "✔"}[lvl] + " " + text, col, W - 3)
        y0 = ay + 5
        ui.text(y0, 1, "CHANGES  (%d)" % len(f), "dim")
        vis = H - y0 - 3
        self.cur = max(0, min(self.cur, len(f) - 1))
        top = max(0, self.cur - vis + 1)
        names = {"M": "modified", "A": "added", "D": "deleted", "R": "renamed", "?": "new", "U": "conflict", "T": "type"}
        for r in range(min(vis, len(f) - top)):
            i = top + r
            kind, c, p = f[i]
            y = y0 + 1 + r
            sel = i == self.cur
            tag = {"staged": "●", "unstaged": "○", "untracked": "+", "conflict": "!"}[kind]
            col = "sel" if sel else {"staged": "second", "unstaged": "accent", "untracked": "dim", "conflict": "danger"}[kind]
            ui.text(y, 0, " " * lw, "sel" if sel else "text", lw)
            ui.text(y, 1, "%s %-9s %s" % (tag, names.get(c, c), p), col, lw - 2)
            ui.region(y, 0, 1, lw, (lambda ii: (lambda: setattr(self, "cur", ii)))(i))
        if not f:
            ui.text(y0 + 2, 3, "Working tree clean.", "second")
        if wide:
            dx = W - 42
            ui.fill(y0, dx, H - y0 - 1, 42, "panel")
            ui.text(y0, dx + 1, "RECENT COMMITS", "panel_dim", 40)
            for i, ln in enumerate(s["log"][:H - y0 - 3]):
                ui.text(y0 + 1 + i, dx + 1, ln, "panel", 40)
        ui.text(H - 1, 1, (self.msg + "   " if self.msg else "") + "Space stage · c commit · P push · p pull · b branch · m merge · F force · ? help", "accent" if self.msg else "dim", W - 2)

    def click(self, ui, y, x, double):
        pass


def main():
    argv = sys.argv[1:]
    nhelp.maybe_help("gitx", argv)
    ap = argparse.ArgumentParser(prog="gitx", add_help=False)
    ap.add_argument("cmd", nargs="?"); ap.add_argument("args", nargs="*")
    ap.add_argument("-m", "--message"); ap.add_argument("-a", "--all", action="store_true"); ap.add_argument("--check", action="store_true")
    ap.add_argument("--yes", action="store_true"); ap.add_argument("--confirm"); ap.add_argument("--no-check", action="store_true"); ap.add_argument("--force-secrets", action="store_true")
    a = ap.parse_args(argv)
    if not a.cmd:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            return cli(argparse.Namespace(cmd="status", args=[]))
        tui.run(Dash()); return 0
    return cli(a)


if __name__ == "__main__":
    sys.exit(main())
