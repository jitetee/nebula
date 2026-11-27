"""repo: GitHub repositories with full CRUD, as a full-screen app (mouse/touch) and as plain commands."""
import argparse
import curses
import os
import shutil
import subprocess
import sys
import webbrowser

from nebula_core import ai, devtools as dt, help as nhelp, icons, tui

ICO = icons.get


def me():
    return dt.gh("GET", "/user")["login"]


def full(name):
    return name if "/" in name else "%s/%s" % (me(), name)


def whoami_info():
    u, hd = dt.gh("GET", "/user", want_headers=True)
    h = {k.lower(): v for k, v in hd.items()}
    scopes = h.get("x-oauth-scopes")
    return {"login": u["login"], "name": u.get("name") or "", "scopes": scopes, "expires": h.get("github-authentication-token-expiration"),
            "kind": "classic token" if scopes is not None else "fine-grained token", "rate": h.get("x-ratelimit-remaining"), "source": dt.token()[1]}


def list_repos(limit=300):
    out, page = [], 1
    while len(out) < limit:
        r = dt.gh("GET", "/user/repos?per_page=100&sort=updated&page=%d" % page)
        out += r
        if len(r) < 100:
            break
        page += 1
    return out


def create_repo(name, desc="", private=False, readme=False, gitignore="", license_=""):
    body = {"name": name, "description": desc, "private": private, "auto_init": bool(readme or gitignore or license_)}
    if gitignore:
        body["gitignore_template"] = gitignore
    if license_:
        body["license_template"] = license_
    return dt.gh("POST", "/user/repos", body)


def edit_repo(slug, **kw):
    return dt.gh("PATCH", "/repos/" + slug, {k: v for k, v in kw.items() if v is not None})


def delete_repo(slug):
    dt.gh("DELETE", "/repos/" + slug)


def branches(slug):
    return dt.gh("GET", "/repos/%s/branches?per_page=100" % slug)


def pulls(slug):
    return dt.gh("GET", "/repos/%s/pulls?state=open&per_page=50" % slug)


def merge_check(slug, n):
    """(ok, summary lines, warnings) before merging pull request n."""
    pr = dt.gh("GET", "/repos/%s/pulls/%s" % (slug, n))
    lines = ["#%s  %s" % (pr["number"], pr["title"]), "%s → %s" % (pr["head"]["ref"], pr["base"]["ref"]),
             "%s commit(s), %s file(s), +%s −%s" % (pr.get("commits", "?"), pr.get("changed_files", "?"), pr.get("additions", "?"), pr.get("deletions", "?"))]
    warn, ok = [], True
    ms = pr.get("mergeable_state")
    if pr.get("mergeable") is False or ms == "dirty":
        ok = False; warn.append("It has merge conflicts. Resolve them first (gitx can help).")
    elif ms == "blocked":
        ok = False; warn.append("Blocked: required checks or reviews are missing.")
    elif ms == "behind":
        warn.append("The branch is behind %s: consider updating it first." % pr["base"]["ref"])
    elif ms == "unstable":
        warn.append("Some checks are failing.")
    if pr.get("state") != "open":
        ok = False; warn.append("It is not open.")
    return ok, lines, warn


def merge_pr(slug, n, method="merge"):
    return dt.gh("PUT", "/repos/%s/pulls/%s/merge" % (slug, n), {"merge_method": method})


def say(msg):
    print(msg)


# ── plain commands ──
def need_login():
    if not dt.token()[0]:
        print("✖ Not logged in to GitHub. Run:  repo login")
        return True
    return False


def login(tok=None):
    import getpass
    t = tok or (getpass.getpass("Paste a GitHub token (input hidden): ") if sys.stdin.isatty() else sys.stdin.readline().strip())
    if not t:
        print("✖ Nothing entered"); return 1
    try:
        u = dt.gh("GET", "/user", tok=t)
    except dt.GitHubError as e:
        print("✖ %s" % e); return 1
    dt.save_token(t)
    print("✔ Logged in as %s. Token saved (mode 600) in Nebula's data folder." % u["login"])
    return 0


def cmd_whoami():
    try:
        w = whoami_info()
    except dt.GitHubError as e:
        print("✖ %s" % e); return 1
    print("✔ %s%s" % (w["login"], " (%s)" % w["name"] if w["name"] else ""))
    print("  token: %s from %s" % (w["kind"], w["source"]))
    if w["scopes"] is not None:
        print("  scopes: %s" % (w["scopes"] or "(none)"))
        if "delete_repo" not in w["scopes"]:
            print("  note: no delete_repo scope, so `repo delete` will be refused")
    if w["expires"]:
        print("  expires: %s" % w["expires"])
    return 0


def fmt_repo(r):
    return "%s %-28s %-7s ★%-4s %s" % ("🔒" if r["private"] else "  ", r["full_name"], "private" if r["private"] else "public", r["stargazers_count"], (r.get("description") or "")[:40])


def main_cli(a):
    c = a.cmd
    if c == "login":
        return login(a.args[0] if a.args else None)
    if c == "logout":
        print("✔ token removed" if dt.forget_token() else "(no saved token)"); return 0
    if need_login():
        return 1
    try:
        if c == "whoami":
            return cmd_whoami()
        if c == "list":
            for r in list_repos():
                print(fmt_repo(r))
            return 0
        if c == "view":
            r = dt.gh("GET", "/repos/" + full(a.args[0]))
            print("%s\n  %s\n  %s · default branch %s · ★%s · forks %s · issues %s%s\n  %s" % (r["full_name"], r.get("description") or "(no description)",
                  "private" if r["private"] else "public", r["default_branch"], r["stargazers_count"], r["forks_count"], r["open_issues_count"],
                  " · ARCHIVED" if r["archived"] else "", r["html_url"]))
            return 0
        if c == "create":
            r = create_repo(a.args[0], a.desc or "", a.private, a.readme)
            print("✔ created %s\n  %s" % (r["full_name"], r["html_url"])); return 0
        if c == "edit":
            slug = full(a.args[0])
            r = edit_repo(slug, description=a.desc, private=True if a.private else (False if a.public else None), homepage=a.homepage, name=a.rename)
            print("✔ updated %s" % r["full_name"]); return 0
        if c == "archive":
            r = edit_repo(full(a.args[0]), archived=not a.undo)
            print("✔ %s is now %s" % (r["full_name"], "active" if a.undo else "archived (read-only)")); return 0
        if c == "delete":
            slug = full(a.args[0])
            typed = a.confirm
            if typed is None and sys.stdin.isatty():
                print("This permanently deletes %s, including issues and pull requests." % slug)
                typed = input("Type the full name to confirm: ").strip()
            if typed != slug:
                print("✖ cancelled (the name did not match)"); return 1
            delete_repo(slug); print("✔ deleted %s" % slug); return 0
        if c == "prs":
            for p in pulls(full(a.args[0])):
                print("#%-4s %-40s %s → %s  by %s" % (p["number"], p["title"][:40], p["head"]["ref"], p["base"]["ref"], p["user"]["login"]))
            return 0
        if c == "merge":
            slug, n = full(a.args[0]), a.args[1]
            ok, lines, warn = merge_check(slug, n)
            print("\n".join(lines))
            for w in warn:
                print("  ⚠ " + w)
            if not ok:
                print("✖ not merging"); return 1
            if not (a.yes or (sys.stdin.isatty() and input("Merge now? [y/N] ").lower().startswith("y"))):
                print("cancelled"); return 1
            merge_pr(slug, n, "squash" if a.squash else "rebase" if a.rebase else "merge"); print("✔ merged #%s" % n); return 0
        if c == "ask":
            q = " ".join(a.args)
            ctx = dt.project_context()
            print(ai.ask("You are a senior engineer. Answer using only this project context.\n\n%s\n\nQuestion: %s" % (ctx, q), "Be concrete and short."))
            return 0
    except dt.GitHubError as e:
        print("✖ %s" % e); return 1
    except ai.AIError as e:
        print("✖ %s" % e); return 1
    except IndexError:
        print("✖ missing argument. See: repo --help"); return 2
    return 2


# ── the full-screen app ──
class RepoApp(tui.App):
    tick_ms = 1000

    def __init__(self):
        self.repos, self.cur, self.top, self.filter = [], 0, 0, ""
        self.msg, self.who = "", ""

    def start(self, ui):
        if not dt.token()[0]:
            t = ui.prompt("GitHub token", "", "paste a token (hidden). Create one at github.com/settings/tokens", secret=True)
            if t:
                try:
                    dt.gh("GET", "/user", tok=t); dt.save_token(t); self.msg = "Logged in"
                except dt.GitHubError as e:
                    ui.message("Login failed", [str(e)])
        self.refresh(ui)

    def refresh(self, ui=None):
        try:
            self.who = me()
            self.repos = list_repos()
            self.msg = "%d repositories" % len(self.repos)
        except dt.GitHubError as e:
            self.repos, self.msg = [], str(e)
            if ui:
                ui.message("GitHub", [str(e)])

    def items(self):
        f = self.filter.lower()
        return [r for r in self.repos if f in r["name"].lower() or f in (r.get("description") or "").lower()] if f else self.repos

    def sel(self):
        it = self.items()
        return it[self.cur] if it and self.cur < len(it) else None

    def guard(self, ui, fn):
        try:
            return fn()
        except dt.GitHubError as e:
            ui.message("GitHub says no", [str(e)])
        return None

    # actions
    def a_new(self, ui):
        v = ui.form("New repository", [dict(key="name", label="Name", value=""), dict(key="desc", label="Description", value=""), dict(key="private", label="Private", value=True, kind="bool"),
                                       dict(key="readme", label="Add README", value=True, kind="bool"),
                                       dict(key="ignore", label="Gitignore", value="", kind="choice", choices=["", "Python", "Node", "Go", "Rust", "Java"]),
                                       dict(key="lic", label="License", value="", kind="choice", choices=["", "mit", "apache-2.0", "gpl-3.0"])])
        if not v or not v["name"].strip():
            return
        if not ui.confirm("Create %s repository “%s”?" % ("private" if v["private"] else "PUBLIC", v["name"]), "Create", "Cancel", title="New repository"):
            return
        r = self.guard(ui, lambda: create_repo(v["name"].strip(), v["desc"], v["private"], v["readme"], v["ignore"], v["lic"]))
        if r:
            self.refresh(); self.msg = "Created " + r["full_name"]

    def a_edit(self, ui):
        r = self.sel()
        if not r:
            return
        v = ui.form("Edit " + r["name"], [dict(key="desc", label="Description", value=r.get("description") or ""), dict(key="home", label="Homepage", value=r.get("homepage") or ""),
                                           dict(key="name", label="Name", value=r["name"])])
        if not v:
            return
        if v["name"] != r["name"] and not ui.confirm("Rename “%s” to “%s”?\nLinks and clones need updating." % (r["name"], v["name"]), "Rename", "Cancel"):
            return
        if self.guard(ui, lambda: edit_repo(r["full_name"], description=v["desc"], homepage=v["home"], name=v["name"])):
            self.refresh(); self.msg = "Updated"

    def a_visibility(self, ui):
        r = self.sel()
        if not r:
            return
        to_private = not r["private"]
        warn = "Make “%s” %s?" % (r["name"], "PRIVATE" if to_private else "PUBLIC")
        if not to_private:
            warn += "\nEveryone on the internet will be able to see the code. Check it has no secrets."
        if ui.confirm(warn, "Yes, change it", "Cancel", danger=not to_private, typed=None if to_private else r["name"]):
            if self.guard(ui, lambda: edit_repo(r["full_name"], private=to_private)):
                self.refresh(); self.msg = "Now " + ("private" if to_private else "public")

    def a_archive(self, ui):
        r = self.sel()
        if r and ui.confirm("%s “%s”?" % ("Unarchive" if r["archived"] else "Archive (make read-only)", r["name"]), "Yes", "Cancel"):
            if self.guard(ui, lambda: edit_repo(r["full_name"], archived=not r["archived"])):
                self.refresh(); self.msg = "Done"

    def a_delete(self, ui):
        r = self.sel()
        if not r:
            return
        if not ui.confirm("Delete %s forever?\nThis removes the code, issues and pull requests.\nIt cannot be undone." % r["full_name"], "Delete forever", "Cancel", danger=True, typed=r["full_name"], title="Delete repository"):
            self.msg = "Not deleted"; return
        if self.guard(ui, lambda: (delete_repo(r["full_name"]), True)[1]):
            self.cur = 0; self.refresh(); self.msg = "Deleted " + r["full_name"]

    def a_branches(self, ui):
        r = self.sel()
        if not r:
            return
        bs = self.guard(ui, lambda: branches(r["full_name"]))
        if bs is None:
            return
        c = ui.choose("Branches of " + r["name"] + "  (Enter = make default)", [(b["name"] + ("  (default)" if b["name"] == r["default_branch"] else ""), "protected" if b.get("protected") else "") for b in bs])
        if c is not None and bs[c]["name"] != r["default_branch"]:
            if ui.confirm("Make “%s” the default branch?" % bs[c]["name"], "Yes", "Cancel"):
                if self.guard(ui, lambda: edit_repo(r["full_name"], default_branch=bs[c]["name"])):
                    self.refresh(); self.msg = "Default branch changed"

    def a_prs(self, ui):
        r = self.sel()
        if not r:
            return
        ps = self.guard(ui, lambda: pulls(r["full_name"]))
        if ps is None:
            return
        if not ps:
            ui.message("Pull requests", ["No open pull requests."]); return
        c = ui.choose("Open pull requests: Enter to review", [("#%s %s" % (p["number"], p["title"]), "%s→%s" % (p["head"]["ref"], p["base"]["ref"])) for p in ps])
        if c is None:
            return
        n = ps[c]["number"]
        res = self.guard(ui, lambda: merge_check(r["full_name"], n))
        if not res:
            return
        ok, lines, warn = res
        ui.message("Pull request", lines + [""] + ["⚠ " + w for w in warn] + ([""] if warn else []) + ["Ready to merge." if ok else "Not mergeable yet."])
        if ok:
            m = ui.choose("Merge #%s how?" % n, ["Merge commit", "Squash and merge", "Rebase and merge", "Close without merging", "Do nothing"])
            if m in (0, 1, 2):
                if ui.confirm("Merge #%s into %s?" % (n, ps[c]["base"]["ref"]), "Merge", "Cancel", title="Merge"):
                    if self.guard(ui, lambda: merge_pr(r["full_name"], n, ["merge", "squash", "rebase"][m])):
                        self.msg = "Merged #%s" % n; self.refresh()
            elif m == 3 and ui.confirm("Close #%s without merging?" % n, "Close it", "Cancel", danger=True):
                self.guard(ui, lambda: dt.gh("PATCH", "/repos/%s/pulls/%s" % (r["full_name"], n), {"state": "closed"}))
                self.msg = "Closed #%s" % n

    def a_issues(self, ui):
        r = self.sel()
        if not r:
            return
        its = self.guard(ui, lambda: dt.gh("GET", "/repos/%s/issues?state=open" % r["full_name"]))
        if its is None:
            return
        opts = [("+ New issue", "")] + [("#%s %s" % (i["number"], i["title"]), i["user"]["login"]) for i in its]
        c = ui.choose("Issues of " + r["name"], opts)
        if c == 0:
            t = ui.prompt("Issue title")
            if t:
                b = ui.prompt("Describe it (optional)") or ""
                if self.guard(ui, lambda: dt.gh("POST", "/repos/%s/issues" % r["full_name"], {"title": t, "body": b})):
                    self.msg = "Issue created"; self.refresh()
        elif c:
            i = its[c - 1]
            if ui.confirm("#%s %s\n\n%s\n\nClose this issue?" % (i["number"], i["title"], (i.get("body") or "")[:200]), "Close issue", "Leave open"):
                self.guard(ui, lambda: dt.gh("PATCH", "/repos/%s/issues/%s" % (r["full_name"], i["number"]), {"state": "closed"})); self.msg = "Closed"; self.refresh()

    def a_clone(self, ui):
        r = self.sel()
        if not r:
            return
        d = ui.prompt("Clone into", os.path.join(os.path.expanduser("~"), r["name"]))
        if d:
            url = r.get("clone_url") or r["html_url"] + ".git"
            ui.suspend(lambda: (subprocess.call(["git", "clone", url, os.path.expanduser(d)]), input("\nPress Enter to return ")))

    def a_open(self, ui):
        r = self.sel()
        if r:
            op = dt.which("termux-open-url", "xdg-open")
            if op:
                subprocess.Popen([op, r["html_url"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); self.msg = "Opened in browser"
            else:
                ui.message("Link", [r["html_url"]])

    ACTIONS = [("new", "New", "a_new"), ("rename", "Edit", "a_edit"), ("eye", "Public/Private", "a_visibility"), ("archive", "Archive", "a_archive"),
               ("branch", "Branches", "a_branches"), ("code", "PRs", "a_prs"), ("info", "Issues", "a_issues"), ("download", "Clone", "a_clone"),
               ("link", "Open", "a_open"), ("delete", "Delete", "a_delete")]

    def key(self, ui, k):
        it = self.items()
        if k in (ord("q"), 27):
            return False
        if k in (curses.KEY_DOWN, ord("j")):
            self.cur = min(len(it) - 1, self.cur + 1)
        elif k in (curses.KEY_UP, ord("k")):
            self.cur = max(0, self.cur - 1)
        elif k == ord("n"):
            self.a_new(ui)
        elif k == ord("e"):
            self.a_edit(ui)
        elif k == ord("v"):
            self.a_visibility(ui)
        elif k == ord("A"):
            self.a_archive(ui)
        elif k == ord("b"):
            self.a_branches(ui)
        elif k == ord("p"):
            self.a_prs(ui)
        elif k == ord("i"):
            self.a_issues(ui)
        elif k == ord("c"):
            self.a_clone(ui)
        elif k == ord("o"):
            self.a_open(ui)
        elif k in (ord("d"), curses.KEY_DC):
            self.a_delete(ui)
        elif k == ord("r"):
            self.refresh(ui)
        elif k == ord("/"):
            f = ui.prompt("Filter repositories", self.filter)
            if f is not None:
                self.filter = f; self.cur = 0
        elif k == ord("?"):
            ui.pager("repo help", (nhelp.render("repo", color=False) or "").split("\n"))
        return True

    def scroll(self, ui, n):
        self.cur = max(0, min(len(self.items()) - 1, self.cur + n))

    def draw(self, ui):
        W, H = ui.w, ui.h
        ui.text(0, 0, " " * W, "bar"); ui.text(0, 1, ICO("github") + "  GitHub repos", "bar")
        ui.text(0, max(16, W - 24), (self.who and ("%s %s" % (ICO("user"), self.who)) or "not logged in").rjust(23), "bar", 23)
        ui.fill(1, 0, 1, W, "panel")
        x = 0
        compact = W < 70
        for ic, label, fn in self.ACTIONS:
            lab = ICO(ic) if compact else "%s %s" % (ICO(ic), label)
            if x + tui.width(lab) + 3 > W:
                break
            x += ui.button(1, x, lab, (lambda f: (lambda: getattr(self, f)(ui)))(fn), "panel_d" if fn == "a_delete" else "panel")
        it = self.items()
        det_w = 0 if W < 100 else 38
        lw = W - det_w
        self.cur = max(0, min(self.cur, len(it) - 1))
        vis = H - 4
        if self.cur < self.top:
            self.top = self.cur
        if self.cur >= self.top + vis:
            self.top = self.cur - vis + 1
        if not it:
            ui.text(3, 2, "No repositories. Press n to create one." if not self.filter else "No match.", "dim")
        for r_ in range(vis):
            i = self.top + r_
            if i >= len(it):
                break
            r = it[i]
            y = 2 + r_
            cur = i == self.cur
            ui.text(y, 0, " " * lw, "sel" if cur else "text", lw)
            ui.text(y, 1, ICO("lock") if r["private"] else ICO("folder_open"), "sel" if cur else ("accent" if r["private"] else "second"), 2)
            ui.text(y, 4, r["name"] + ("  [archived]" if r["archived"] else ""), "sel" if cur else "primary", lw - 18)
            ui.text(y, max(4, lw - 12), ("★%d" % r["stargazers_count"]).rjust(6) + ("  %s" % (r.get("language") or "")[:4]).ljust(5), "sel" if cur else "dim", 12)
            ui.region(y, 0, 1, lw, (lambda ii: (lambda: setattr(self, "cur", ii)))(i))
        sel = self.sel()
        if det_w and sel:
            dx = W - det_w
            ui.fill(2, dx, H - 4, det_w, "panel")
            for k, line in enumerate([sel["full_name"], "", sel.get("description") or "(no description)", "", "%s · %s" % ("private" if sel["private"] else "public", sel.get("language") or "-"),
                                      "branch  %s" % sel["default_branch"], "★ %s   forks %s   issues %s" % (sel["stargazers_count"], sel["forks_count"], sel["open_issues_count"]),
                                      "pushed  %s" % (sel.get("pushed_at") or "")[:10]]):
                ui.text(3 + k, dx + 1, line, "panel_p" if k == 0 else "panel", det_w - 2)
        elif sel:
            ui.text(H - 2, 1, "%s · %s · %s" % (sel["full_name"], "private" if sel["private"] else "public", (sel.get("description") or "")[:W - 40]), "dim", W - 2)
        ui.text(H - 1, 1, (self.msg + "   ") + "n new · e edit · v visibility · d delete · b branches · p PRs · i issues · c clone · ? help", "accent" if self.msg else "dim", W - 2)

    def click(self, ui, y, x, double):
        pass


def main():
    argv = sys.argv[1:]
    nhelp.maybe_help("repo", argv)
    ap = argparse.ArgumentParser(prog="repo", add_help=False)
    ap.add_argument("cmd", nargs="?")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--desc"); ap.add_argument("--private", action="store_true"); ap.add_argument("--public", action="store_true")
    ap.add_argument("--readme", action="store_true"); ap.add_argument("--homepage"); ap.add_argument("--rename")
    ap.add_argument("--undo", action="store_true"); ap.add_argument("--confirm"); ap.add_argument("--yes", action="store_true")
    ap.add_argument("--squash", action="store_true"); ap.add_argument("--rebase", action="store_true")
    a = ap.parse_args(argv)
    if not a.cmd:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            print("repo needs a terminal for the full-screen manager. Try: repo list"); return 2
        tui.run(RepoApp()); return 0
    return main_cli(a)


if __name__ == "__main__":
    sys.exit(main())
