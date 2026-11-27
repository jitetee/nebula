"""Shared pieces for Nebula's developer plugins (repo, gitx, fire, accounts, project): GitHub client, git helpers, project context.

Token sources for GitHub, in order: $GITHUB_TOKEN / $GH_TOKEN, $NEBULA_CFG/auth/github (set by `repo login`), `gh auth token`.
The token is only ever sent to the GitHub API host, never printed, and stored with mode 600.
"""
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request

from . import paths


class GitHubError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def api_base():
    return os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")


def _token_file():
    return os.path.join(paths.cfg(), "auth", "github")


def token():
    """(token, source) or (None, None)."""
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var].strip(), "$" + var
    try:
        t = open(_token_file(), encoding="utf-8").read().strip()
        if t:
            return t, "saved by `repo login`"
    except OSError:
        pass
    if shutil.which("gh"):
        try:
            t = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5).stdout.strip()
            if t:
                return t, "gh CLI"
        except Exception:
            pass
    return None, None


def save_token(t):
    d = os.path.dirname(_token_file())
    os.makedirs(d, exist_ok=True)
    os.chmod(d, 0o700)
    with open(_token_file(), "w", encoding="utf-8") as f:
        f.write(t.strip() + "\n")
    os.chmod(_token_file(), 0o600)


def forget_token():
    try:
        os.remove(_token_file())
        return True
    except OSError:
        return False


def gh(method, path, body=None, tok=None, want_headers=False):
    """Call the GitHub REST API. Returns parsed JSON (or (json, headers)). Raises GitHubError with a human message."""
    t = tok or token()[0]
    if not t:
        raise GitHubError(401, "Not logged in to GitHub. Run:  repo login")
    url = path if path.startswith("http") else api_base() + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + t, "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "nebula-devtools", **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode() or "null"
            out = json.loads(raw)
            return (out, dict(r.headers)) if want_headers else out
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("message", "")
        except Exception:
            msg = ""
        hint = {401: "The token is invalid or expired. Run:  repo login", 403: "Not allowed: your token lacks permission for this (check its scopes).",
                404: "Not found (or the token cannot see it).", 422: "GitHub rejected that: " + msg, 409: "Conflict: " + msg}.get(e.code, msg or "HTTP %d" % e.code)
        if e.code == 403 and "rate limit" in msg.lower():
            hint = "GitHub rate limit reached. Try again later."
        raise GitHubError(e.code, hint)
    except (urllib.error.URLError, OSError) as e:
        raise GitHubError(0, "No connection to GitHub (%s)" % getattr(e, "reason", e))


# ── git ──
def git(args, cwd=None, check=False, timeout=60):
    """(returncode, stdout, stderr)"""
    r = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip())
    return r.returncode, r.stdout, r.stderr


def in_repo(cwd=None):
    return git(["rev-parse", "--is-inside-work-tree"], cwd)[0] == 0


def repo_root(cwd=None):
    rc, out, _ = git(["rev-parse", "--show-toplevel"], cwd)
    return out.strip() if rc == 0 else None


def remote_slug(cwd=None):
    """owner/name of origin if it is a GitHub remote."""
    rc, out, _ = git(["remote", "get-url", "origin"], cwd)
    if rc:
        return None
    u = out.strip()
    for pre in ("https://github.com/", "git@github.com:", "ssh://git@github.com/"):
        if u.startswith(pre):
            return u[len(pre):].removesuffix(".git").strip("/")
    return None


def project_context(cwd=None, max_chars=9000):
    """A compact, factual snapshot of the project for the AI: git state, tree, README, config files, TODOs."""
    cwd = cwd or os.getcwd()
    root = repo_root(cwd) or cwd
    parts = ["Project folder: %s" % os.path.basename(root)]
    if in_repo(root):
        _, br, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], root)
        _, st, _ = git(["status", "--short", "--branch"], root)
        _, lg, _ = git(["log", "--oneline", "-8"], root)
        _, ds, _ = git(["diff", "--stat", "HEAD"], root)
        parts += ["Git branch: %s" % br.strip(), "Git status:\n%s" % st.strip(), "Recent commits:\n%s" % lg.strip()]
        if ds.strip():
            parts.append("Uncommitted changes (stat):\n%s" % ds.strip()[:1500])
        slug = remote_slug(root)
        if slug:
            parts.append("GitHub: %s" % slug)
    tree = []
    for r, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "venv", ".venv", "dist", "build"))
        depth = r[len(root):].count(os.sep)
        if depth >= 2:
            dirs[:] = []
        for f in sorted(files)[:15]:
            tree.append(os.path.relpath(os.path.join(r, f), root))
        if len(tree) > 120:
            break
    parts.append("Files (first levels):\n" + "\n".join(tree[:120]))
    for name in ("README.md", "readme.md", "package.json", "firebase.json", "pyproject.toml", "requirements.txt", "Makefile"):
        p = os.path.join(root, name)
        if os.path.isfile(p):
            try:
                parts.append("%s:\n%s" % (name, open(p, errors="replace").read()[:1500]))
            except OSError:
                pass
    try:
        r = subprocess.run(["grep", "-rIn", "-E", "TODO|FIXME", "--include=*.py", "--include=*.js", "--include=*.ts", "--include=*.sh", "--include=*.lua", root],
                           capture_output=True, text=True, timeout=8)
        todos = [l.replace(root + "/", "") for l in r.stdout.splitlines()[:12]]
        if todos:
            parts.append("TODO/FIXME:\n" + "\n".join(todos))
    except Exception:
        pass
    ctx = "\n\n".join(parts)
    return ctx[:max_chars]


def which(*names):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None
