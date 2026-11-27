#!/usr/bin/env python3
"""GUI and dev-plugin tests: drives every full-screen app in a pseudo-terminal and the dev plugins against mock GitHub / Firebase / AI.
   python3 tools/test_gui.py        (needs: pip install pyte; the player test also needs mpv and is skipped without it)"""
import json, os, shutil, socket, subprocess, sys, tempfile, time

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(H, "tools"))
from drive import Session  # noqa

T = tempfile.mkdtemp(prefix="nebgui")
PASS = FAIL = 0
procs = []


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def ok(name, cond):
    global PASS, FAIL
    PASS += bool(cond); FAIL += (not cond)
    print(("  ✔ " if cond else "  ✖ ") + name)


def section(t):
    print("\n" + t)


def start(*a):
    p = subprocess.Popen(list(a), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); procs.append(p); return p


def gone(s, secs=6):
    end = time.time() + secs
    while time.time() < end:
        s.pump(0.2)
        if not s.alive():
            return True
    return False


def seen(s, text, secs=4):
    """Poll the screen for text (slow phones and busy CI need a moment)."""
    end = time.time() + secs
    while time.time() < end:
        if s.has(text):
            return True
        s.pump(0.2)
    return s.has(text)


def base_env(extra=None):
    e = dict(NEBULA_CFG=os.path.join(T, "cfg"), NEBULA_HOME=H, HOME=os.path.join(T, "home"), PYTHONPATH=":".join([os.path.join(H, "lib"), os.path.join(H, "apps/gui")] + [os.path.join(H, "plugins", p) for p in ("repo", "gitx", "fire", "accounts", "project")]),
             GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@x", GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@x")
    e.update(extra or {})
    return e


os.makedirs(os.path.join(T, "home", ".ant"), exist_ok=True)
PY = sys.executable
try:
    section("Files")
    ft = os.path.join(T, "ft")
    for d in ("Documents", "Music", "Pictures"):
        os.makedirs(os.path.join(ft, d))
    open(os.path.join(ft, "notes.txt"), "w").write("hello"); open(os.path.join(ft, "Documents", "a.md"), "w").write("x")
    env = base_env()
    s = Session([PY, "-m", "nebula_gui.files", ft], cols=100, rows=28, env=env, cwd=ft)
    ok("lists folders and files", s.has("Documents/") and s.has("notes.txt"))
    s.keys("j"); s.keys("j"); s.keys(" "); ok("space ticks a row", s.has("1 selected"))
    s.click(30, 4, 0.05); s.click(30, 4); ok("double-tap opens a folder", s.has("a.md"))
    s.keys("\x7f"); s.keys("n"); s.keys("fresh.txt"); s.keys("\r"); ok("new file", os.path.exists(os.path.join(ft, "fresh.txt")))
    s.keys("d"); s.keys("\r"); ok("delete goes to the trash", not os.path.exists(os.path.join(ft, "fresh.txt")) and any(f.endswith(".info") for f in os.listdir(os.path.join(T, "cfg", "trash"))))
    s.keys("t"); s.keys("R"); ok("restore from trash", os.path.exists(os.path.join(ft, "fresh.txt")))
    s.keys("\x7f"); s.keys("/"); s.keys("note"); s.keys("\r"); ok("filter", s.has("notes.txt") and not s.has("Documents/"))
    s.keys("?"); ok("help pager", s.has("Files help")); s.keys("q"); s.keys("q"); s.keys("q"); ok("q quits", gone(s)); s.close()
    n = Session([PY, "-m", "nebula_gui.files", ft], cols=56, rows=26, env=env, cwd=ft); ok("phone width renders", n.has("Files") and n.has("notes.txt")); n.close()

    section("Monitor")
    s = Session([PY, "-m", "nebula_gui.monitor"], cols=64, rows=26, env=env, wait=2.0)
    ok("overview", s.has("CPU") and s.has("Memory")); s.keys("\t"); ok("processes tab", seen(s, "COMMAND")); s.keys("5"); ok("nebula tab", seen(s, "Version"))
    s.keys("q"); ok("q quits", gone(s)); s.close()

    section("Launcher")
    s = Session([PY, "-m", "nebula_gui.launcher"], cols=56, rows=26, env=env)
    ok("tiles", s.has("Files") and s.has("Save media") and s.has("GitHub") and s.has("Firebase")); s.keys("q"); ok("q quits", gone(s)); s.close()

    if shutil.which("mpv"):
        section("Player")
        mus = os.path.join(T, "mus"); os.makedirs(mus)
        import wave, struct, math
        for nme, f in (("Alpha Song", 440), ("Beta Song", 523)):
            w = wave.open(os.path.join(mus, nme + ".wav"), "w"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
            w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * f * i / 22050))) for i in range(22050 * 6))); w.close()
        s = Session([PY, "-m", "nebula_gui.player", mus], cols=64, rows=24, env=base_env({"NEBULA_PLAYER_AO": "null"}), wait=2.0)
        ok("library", s.has("Alpha Song") and s.has("2 tracks")); s.keys("\r", 1.5); ok("playback starts", s.has("Alpha Song") and not s.has("Nothing playing"))
        time.sleep(1.5); s.pump(0.6); ok("progress advances", s.has("0:01") or s.has("0:02") or s.has("0:03"))
        s.keys("+", 0.4); ok("volume", s.has("75%")); s.keys("\t", 0.4); ok("queue tab", s.has("Queue (2)")); s.keys("q"); ok("q quits", gone(s, 8)); s.close()
    else:
        print("\nPlayer: skipped (mpv not installed)")

    section("svn (mock yt-dlp)")
    sh = os.path.join(T, "svnhome"); os.makedirs(os.path.join(sh, "storage", "movies"))
    e = base_env({"HOME": sh, "NEBULA_SVN_YTDLP": "%s %s" % (PY, os.path.join(H, "tools", "mock_ytdlp.py"))})
    URL = "https://youtube.com/shorts/6xhyB8Hlznc?si=e_Wmk5RLZ-I4FYkC"
    s = Session([PY, "-m", "nebula_gui.svn", URL], cols=56, rows=24, env=e, wait=2.0)
    ok("found card", s.has("Found it") and s.has("Mock Video Title")); s.keys("\r"); ok("type step", s.has("What do you want to save?"))
    s.keys("1"); ok("quality list", s.has("1080p") and s.has("720p")); s.keys("j"); s.keys("j"); s.keys("\r"); ok("save-to step", s.has("Where should it go?"))
    s.keys("\r", 0.8); time.sleep(2.5); s.pump(0.8); ok("done screen", s.has("Saved"))
    ok("mp4 written", any(f.endswith(".mp4") for r, _, fs in os.walk(sh) for f in fs)); s.keys("q"); gone(s); s.close()
    s = Session([PY, "-m", "nebula_gui.svn", "https://instagram.com/p/private123"], cols=56, rows=24, env=e, wait=2.0)
    ok("private link gives a friendly error", s.has("needs a login")); s.close()
    out = subprocess.run([PY, "-m", "nebula_gui.svn", URL, "-a", "-o", os.path.join(T, "aud")], env=dict(os.environ, **e), capture_output=True, text=True, timeout=60)
    ok("non-interactive audio (-a)", out.returncode == 0 and any(f.endswith(".mp3") for f in os.listdir(os.path.join(T, "aud"))))

    section("repo (mock GitHub)")
    gp = free_port(); start(PY, os.path.join(H, "tools", "mock_github.py"), str(gp)); time.sleep(1)
    re_ = base_env({"GITHUB_API_URL": "http://127.0.0.1:%d" % gp})

    def run(script, *a, cwd=None, env_=None, inp=None):
        r = subprocess.run([PY, os.path.join(H, "plugins", script, script + ".py"), *a], cwd=cwd or T, capture_output=True, text=True, env=dict(os.environ, **(env_ or re_)), input=inp, timeout=60)
        return r.returncode, r.stdout + r.stderr
    rc, o = run("repo", "list"); ok("not logged in is explained", rc != 0 and "repo login" in o)
    rc, o = run("repo", "login", "badtoken"); ok("bad token rejected", rc != 0)
    rc, o = run("repo", "login", "mocktoken"); ok("login", rc == 0 and "mockuser" in o)
    ok("token file is private (600)", oct(os.stat(os.path.join(T, "cfg", "auth", "github")).st_mode & 0o777) == "0o600")
    rc, o = run("repo", "whoami"); ok("whoami shows scopes", "delete_repo" in o)
    rc, o = run("repo", "create", "newrepo", "--private", "--desc", "x"); ok("create", rc == 0)
    rc, o = run("repo", "edit", "newrepo", "--desc", "Changed", "--public"); rc2, o2 = run("repo", "view", "newrepo"); ok("edit", rc == 0 and "Changed" in o2)
    rc, o = run("repo", "delete", "newrepo", "--confirm", "wrong"); ok("delete refused on wrong name", rc != 0)
    rc, o = run("repo", "delete", "newrepo", "--confirm", "mockuser/newrepo"); ok("delete with typed full name", rc == 0)
    rc, o = run("repo", "merge", "hello", "7", "--yes"); ok("PR merge with checks", rc == 0 and "merged #7" in o)
    s = Session([PY, os.path.join(H, "plugins/repo/repo.py")], cols=100, rows=26, env=dict(os.environ, **re_), wait=2.0)
    ok("full-screen repo list", s.has("hello") and s.has("secret")); s.keys("d"); ok("delete asks to type the full name", s.has("Type")); s.keys("\x1b"); s.keys("q"); s.close()

    section("gitx (real git)")
    wd = os.path.join(T, "gx"); os.makedirs(wd)
    ge = dict(os.environ, **base_env())
    def g(c, cwd=wd): return subprocess.run(c, shell=True, cwd=cwd, capture_output=True, text=True, env=ge)
    g("git init -q --bare remote.git -b main; git clone -q remote.git a; git clone -q remote.git b")
    for d in ("a", "b"):
        g("git config user.name T; git config user.email t@x", os.path.join(wd, d))
    A = os.path.join(wd, "a"); B = os.path.join(wd, "b")
    open(os.path.join(A, "f.txt"), "w").write("one\n"); g("git add -A; git commit -qm init; git push -q -u origin main", A)
    def gx(*a, cwd=A): return run("gitx", *a, cwd=cwd, env_=base_env())
    open(os.path.join(A, "f.txt"), "a").write("two\n"); g("git add f.txt", A); open(os.path.join(A, "key.txt"), "w").write("AWS=AKIAABCDEFGHIJKLMNOP\n"); g("git add key.txt", A)
    rc, o = gx("advise"); ok("advisor spots a secret in staged files", "secret" in o.lower() and "key.txt" in o)
    rc, o = gx("commit", "-m", "bad"); ok("commit refuses a secret", rc != 0)
    g("git reset -q key.txt; rm key.txt", A); rc, o = gx("commit", "-a", "-m", "add two"); ok("commit", rc == 0)
    rc, o = gx("push"); ok("push", rc == 0)
    open(os.path.join(B, "g.txt"), "w").write("g\n"); g("git pull -q; git add -A; git commit -qm bchange; git push -q", B)
    open(os.path.join(A, "h.txt"), "w").write("h\n"); gx("commit", "-a", "-m", "local"); g("git fetch -q", A)
    rc, o = gx("push"); ok("push refused when behind", rc != 0 and "Pull first" in o)
    rc, o = gx("force", "--confirm", "nope"); ok("force-push needs the typed branch name", rc != 0 and "cancelled" in o)
    g("git pull -q --rebase; git switch -q -c feat", A); open(os.path.join(A, "f.txt"), "w").write("feat\n"); g("git commit -qam f", A)
    g("git switch -q main", A); open(os.path.join(A, "f.txt"), "w").write("main\n"); g("git commit -qam m", A)
    rc, o = gx("merge", "feat", "--check"); ok("merge check predicts a conflict and changes nothing", rc != 0 and "f.txt" in o and g("git status --porcelain", A).stdout.strip() == "")

    section("fire, accounts, project (mock Firebase + AI)")
    ap = free_port(); start(PY, os.path.join(H, "tools", "mock_ai_server.py"), str(ap)); time.sleep(0.8)
    open(os.path.join(T, "home", ".ant", "config.json"), "w").write('{"provider":"generic","model":"mock","keys":{"generic":"k"},"baseUrl":"http://127.0.0.1:%d/v1"}' % ap)
    pj = os.path.join(T, "proj"); os.makedirs(os.path.join(pj, "public")); os.makedirs(os.path.join(pj, "functions"))
    json.dump({"hosting": {"public": "public"}, "firestore": {"rules": "firestore.rules"}}, open(os.path.join(pj, "firebase.json"), "w")); json.dump({"projects": {"default": "my-site-prod"}}, open(os.path.join(pj, ".firebaserc"), "w"))
    open(os.path.join(pj, "public", "index.html"), "w").write("hi"); open(os.path.join(pj, "firestore.rules"), "w").write("rules")
    g("git init -q -b main; git config user.name T; git config user.email t@x; git add -A; git commit -qm init", pj)
    fe = base_env({"GITHUB_API_URL": "http://127.0.0.1:%d" % gp, "GITHUB_TOKEN": "mocktoken", "FIREBASE_BIN": "%s %s" % (PY, os.path.join(H, "tools", "mock_firebase.py"))})
    rc, o = run("fire", "status", cwd=pj, env_=fe); ok("fire status", "dev@example.com" in o and "my-site-prod" in o and "Firestore rules" in o)
    rc, o = run("fire", "deploy", "hosting", "--yes", cwd=pj, env_=fe); ok("deploy hosting", rc == 0 and "my-site-prod.web.app" in o)
    rc, o = run("fire", "deploy", "firestore", cwd=pj, env_=fe, inp=""); ok("rules deploy needs typed confirmation", rc != 0 and "cancelled" in o)
    rc, o = run("fire", "deploy", "hosting", "--yes", cwd=pj, env_=dict(fe, MOCK_FB_LOGGED_OUT="1")); ok("deploy refuses when logged out", rc != 0 and "Not logged in" in o)
    rc, o = run("accounts", cwd=pj, env_=fe); ok("accounts checklist", "mockuser" in o and "dev@example.com" in o and "AI backend" in o)
    rc, o = run("project", "next", cwd=pj, env_=fe); ok("project next answers via the AI backend", rc == 0 and "MOCK" in o)
    s = Session([PY, os.path.join(H, "plugins/fire/fire.py")], cols=70, rows=24, env=dict(os.environ, **fe), cwd=pj, wait=2.5)
    ok("fire dashboard", s.has("Firebase") and s.has("WHAT TO DEPLOY")); s.keys("q"); s.close()
finally:
    for p in procs:
        p.terminate()
    shutil.rmtree(T, ignore_errors=True)
print("\n  %d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
