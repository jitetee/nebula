#!/usr/bin/env python3
"""A tiny in-memory GitHub API for tests: python3 tools/mock_github.py PORT   (token: mocktoken, user: mockuser)."""
import json, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

REPOS = {"hello": dict(name="hello", full_name="mockuser/hello", private=False, description="First repo", default_branch="main", stargazers_count=3, forks_count=1,
                       open_issues_count=1, language="Python", archived=False, html_url="https://github.com/mockuser/hello", pushed_at="2026-11-20T10:00:00Z", topics=[], homepage=""),
         "secret": dict(name="secret", full_name="mockuser/secret", private=True, description="", default_branch="main", stargazers_count=0, forks_count=0,
                        open_issues_count=0, language=None, archived=False, html_url="https://github.com/mockuser/secret", pushed_at="2026-10-01T10:00:00Z", topics=[], homepage="")}
PRS = {"hello": [dict(number=7, title="Add feature", state="open", user={"login": "mockuser"}, head={"ref": "feat"}, base={"ref": "main"}, mergeable=True, mergeable_state="clean", commits=2, changed_files=3, additions=40, deletions=5, merged=False)]}
ISSUES = {"hello": [dict(number=1, title="Bug: crash", state="open", user={"login": "friend"}, body="It crashes")]}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body=None, headers=None):
        out = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n)) if n else {}

    def handle_any(self, m):
        if self.headers.get("Authorization") != "Bearer mocktoken":
            return self.send(401, {"message": "Bad credentials"})
        p = self.path.split("?")[0]
        if p == "/user":
            return self.send(200, {"login": "mockuser", "name": "Mock User", "email": "mock@example.com"}, {"X-OAuth-Scopes": "repo, delete_repo", "X-RateLimit-Remaining": "4990"})
        if p == "/user/repos" and m == "GET":
            return self.send(200, list(REPOS.values()))
        if p == "/user/repos" and m == "POST":
            b = self.body()
            if b["name"] in REPOS:
                return self.send(422, {"message": "name already exists on this account"})
            REPOS[b["name"]] = dict(name=b["name"], full_name="mockuser/" + b["name"], private=bool(b.get("private")), description=b.get("description", ""), default_branch="main",
                                    stargazers_count=0, forks_count=0, open_issues_count=0, language=None, archived=False, html_url="https://github.com/mockuser/" + b["name"], pushed_at="2026-11-25T10:00:00Z", topics=[], homepage="")
            return self.send(201, REPOS[b["name"]])
        r = re.match(r"^/repos/mockuser/([^/]+)(/.*)?$", p)
        if not r:
            return self.send(404, {"message": "Not Found"})
        name, rest = r.group(1), r.group(2) or ""
        if name not in REPOS:
            return self.send(404, {"message": "Not Found"})
        repo = REPOS[name]
        if rest == "":
            if m == "GET":
                return self.send(200, repo)
            if m == "PATCH":
                b = self.body()
                if "name" in b and b["name"] != name:
                    REPOS[b["name"]] = REPOS.pop(name); repo = REPOS[b["name"]]; repo["full_name"] = "mockuser/" + b["name"]
                repo.update({k: v for k, v in b.items() if k in ("description", "private", "archived", "homepage", "default_branch", "name")})
                return self.send(200, repo)
            if m == "DELETE":
                del REPOS[name]; return self.send(204)
        if rest == "/branches":
            return self.send(200, [{"name": "main", "protected": True}, {"name": "feat", "protected": False}])
        if rest == "/pulls" and m == "GET":
            return self.send(200, PRS.get(name, []))
        mm = re.match(r"^/pulls/(\d+)(/merge)?$", rest)
        if mm:
            pr = next((x for x in PRS.get(name, []) if x["number"] == int(mm.group(1))), None)
            if not pr:
                return self.send(404, {"message": "Not Found"})
            if mm.group(2) and m == "PUT":
                pr["state"], pr["merged"] = "closed", True; return self.send(200, {"merged": True, "message": "Pull Request successfully merged"})
            if m == "PATCH":
                pr["state"] = self.body().get("state", pr["state"]); return self.send(200, pr)
            return self.send(200, pr)
        if rest == "/issues" and m == "GET":
            return self.send(200, [i for i in ISSUES.get(name, []) if i["state"] == "open"])
        if rest == "/issues" and m == "POST":
            b = self.body(); it = dict(number=len(ISSUES.setdefault(name, [])) + 1, title=b["title"], state="open", user={"login": "mockuser"}, body=b.get("body", "")); ISSUES[name].append(it)
            return self.send(201, it)
        mm = re.match(r"^/issues/(\d+)$", rest)
        if mm and m == "PATCH":
            it = next(x for x in ISSUES.get(name, []) if x["number"] == int(mm.group(1))); it["state"] = self.body().get("state", it["state"]); return self.send(200, it)
        return self.send(404, {"message": "Not Found"})

    def do_GET(self): self.handle_any("GET")
    def do_POST(self): self.handle_any("POST")
    def do_PATCH(self): self.handle_any("PATCH")
    def do_PUT(self): self.handle_any("PUT")
    def do_DELETE(self): self.handle_any("DELETE")


HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
