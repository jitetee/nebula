#!/usr/bin/env python3
"""A fake `firebase` CLI for tests."""
import json, os, sys
a = sys.argv[1:]
if a[:1] == ["login:list"]:
    print("Logged in as dev@example.com" if not os.environ.get("MOCK_FB_LOGGED_OUT") else "No authorized accounts, run \"firebase login\""); sys.exit(0)
if a[:1] == ["projects:list"]:
    print(json.dumps({"status": "success", "result": [{"projectId": "my-site-prod", "displayName": "My Site"}, {"projectId": "my-site-staging", "displayName": "Staging"}]})); sys.exit(0)
if a[:1] == ["deploy"]:
    only = a[a.index("--only") + 1] if "--only" in a else "all"
    proj = a[a.index("--project") + 1] if "--project" in a else "default"
    print("=== Deploying to '%s'..." % proj); print("i  deploying %s" % only)
    if "functions" in only and os.environ.get("MOCK_FB_FAIL"):
        print("Error: functions failed to deploy"); sys.exit(1)
    print("✔  Deploy complete!"); print("Hosting URL: https://%s.web.app" % proj); sys.exit(0)
if a[:1] == ["hosting:channel:deploy"]:
    print("✔  Channel URL (%s): https://%s--%s-abc123.web.app [expires in 7 days]" % (a[1], a[a.index("--project") + 1] if "--project" in a else "p", a[1])); sys.exit(0)
print("mock firebase: unknown command %s" % a); sys.exit(1)
