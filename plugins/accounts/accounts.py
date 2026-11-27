"""accounts: one checklist of every login Nebula's tools depend on."""
import json
import os
import shutil
import subprocess
import sys

from nebula_core import ai, devtools as dt, help as nhelp


def git_identity():
    n = dt.git(["config", "--global", "user.name"])[1].strip()
    e = dt.git(["config", "--global", "user.email"])[1].strip()
    if n and e:
        return ("ok", "%s <%s>" % (n, e), "")
    return ("bad", "not set (commits will fail or be anonymous)", 'git config --global user.name "Your Name" && git config --global user.email you@example.com')


def github():
    tok, src = dt.token()
    if not tok:
        return ("bad", "not logged in", "accounts login github")
    try:
        import repo
        w = repo.whoami_info()
    except dt.GitHubError as e:
        return ("bad", str(e), "accounts login github")
    bits = ["%s (%s, from %s)" % (w["login"], w["kind"], w["source"])]
    note = ""
    if w["scopes"] is not None and "delete_repo" not in w["scopes"]:
        note = "can't delete repos (no delete_repo scope)"
    if w["expires"]:
        bits.append("expires " + w["expires"][:10])
    return ("ok" if not note else "warn", "; ".join(bits) + ("; " + note if note else ""), "")


def gh_cli():
    if not shutil.which("gh"):
        return ("none", "not installed (optional)", "pkg install gh")
    r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    return ("ok", "logged in", "") if r.returncode == 0 else ("warn", "installed, not logged in", "gh auth login")


def ssh_key():
    for k in ("id_ed25519", "id_rsa", "id_ecdsa"):
        if os.path.exists(os.path.expanduser("~/.ssh/%s.pub" % k)):
            return ("ok", "~/.ssh/%s.pub" % k, "")
    return ("none", "no SSH key (HTTPS with a token works too)", 'ssh-keygen -t ed25519 -C "you@example.com"')


def firebase():
    try:
        import fire
        acct, why = fire.account()
    except Exception as e:
        return ("none", "not checked (%s)" % e, "")
    if fire.fb_cmd() is None:
        return ("none", "Firebase CLI not installed (optional)", "npm install -g firebase-tools")
    return ("ok", acct, "") if acct else ("bad", why, "fire login")


def ai_backend():
    d = ai.describe()
    return ("ok" if not d.startswith("none") else "bad", d, "" if not d.startswith("none") else "run `ant` and type /setup, or: pkg install tgpt")


def copilot():
    d = os.path.expanduser("~/.config/github-copilot")
    if os.path.isfile(d + "/apps.json") or os.path.isfile(d + "/hosts.json"):
        return ("ok", "signed in", "")
    return ("none", "not signed in (optional)", "nvim, then :NebulaCopilot and press s")


def termux():
    api = shutil.which("termux-battery-status")
    st = os.path.isdir(os.path.expanduser("~/storage"))
    bits = ["Termux:API %s" % ("ok" if api else "missing"), "phone storage %s" % ("linked" if st else "not linked")]
    fix = ""
    if not st:
        fix = "termux-setup-storage"
    elif not api:
        fix = "pkg install termux-api  (and the Termux:API app)"
    return ("ok" if api and st else "warn", ", ".join(bits), fix)


CHECKS = [("git identity", git_identity), ("GitHub", github), ("GitHub CLI", gh_cli), ("SSH key", ssh_key), ("Firebase", firebase),
          ("AI backend", ai_backend), ("Copilot", copilot), ("Termux", termux)]


def collect():
    out = []
    for name, fn in CHECKS:
        try:
            s, d, f = fn()
        except Exception as e:
            s, d, f = "warn", "check failed: %s" % e, ""
        out.append({"name": name, "status": s, "detail": d, "fix": f})
    return out


def login(what):
    if what == "github":
        import repo
        return repo.login()
    if what == "firebase":
        import fire
        c = fire.fb_cmd()
        return subprocess.call(c + ["login", "--no-localhost"]) if c else (print("✖ npm install -g firebase-tools") or 1)
    if what in ("ai", "ant"):
        print("Opening ant: type /setup to pick a provider and paste your key."); return subprocess.call([sys.executable, "-m", "ant"])
    if what == "copilot":
        print("In Neovim run :NebulaCopilot and press s"); return 0
    print("✖ login what? github | firebase | ai | copilot"); return 2


def main():
    argv = sys.argv[1:]
    nhelp.maybe_help("accounts", argv)
    if argv[:1] == ["login"]:
        return login(argv[1] if len(argv) > 1 else "")
    rows = collect()
    if "--json" in argv:
        print(json.dumps(rows, indent=1)); return 0
    mark = {"ok": "✔", "bad": "✖", "warn": "⚠", "none": "○"}
    print("Accounts and logins\n")
    for r in rows:
        print("  %s %-13s %s" % (mark[r["status"]], r["name"], r["detail"]))
        if r["fix"] and r["status"] != "ok":
            print("      → %s" % r["fix"])
    bad = [r for r in rows if r["status"] == "bad"]
    print("\n  %s" % ("All the important logins are fine." if not bad else "%d thing(s) need attention." % len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
