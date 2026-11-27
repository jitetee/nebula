#!/usr/bin/env python3
"""A fake yt-dlp for tests: understands -J and downloads (progress lines + a small file). URLs containing 'private' or 'bad' fail."""
import json, os, sys, time
a = sys.argv[1:]
url = a[-1]
if "private" in url:
    sys.stderr.write("ERROR: [youtube] abc: Private video. Sign in if you've been granted access\n"); sys.exit(1)
if "bad" in url:
    sys.stderr.write("ERROR: Unsupported URL: " + url + "\n"); sys.exit(1)
if "--version" in a:
    print("2099.01.01"); sys.exit(0)
if "-J" in a:
    fm = [{"format_id": str(h), "ext": "mp4", "height": h, "vcodec": "avc1", "acodec": "none", "filesize": h * 40000} for h in (144, 360, 480, 720, 1080)]
    fm.append({"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a", "abr": 128, "filesize": 900000})
    d = {"id": "abc123", "title": "Mock Video Title", "uploader": "Mock Channel", "duration": 83, "extractor_key": "Youtube", "formats": fm}
    if "playlist" in url:
        d = {"_type": "playlist", "title": "Mock Playlist", "entries": [{"id": "1"}, {"id": "2"}]}
    print(json.dumps(d)); sys.exit(0)
tmpl = a[a.index("-o") + 1]
audio = "--audio-format" in a
ext = a[a.index("--audio-format") + 1] if audio else "mp4"
if "--skip-download" in a:
    ext = "jpg"
path = tmpl.replace("%(title).80s", "Mock Video Title").replace("%(id)s", "abc123").replace("%(ext)s", ext).replace("%(title).100s", "Mock Video Title").replace("%(uploader).30s", "Mock Channel").replace("%(title).70s", "Mock Video Title")
os.makedirs(os.path.dirname(path), exist_ok=True)
tpl = a[a.index("--progress-template") + 1] if "--progress-template" in a else ""
for p in range(0, 101, 20):
    print("NEBPROG|%5.1f%%|1.2MiB/s|00:0%d|%d|1000000|NA" % (p, 5 - p // 25, p * 10000), flush=True); time.sleep(0.15)
if audio or "merge" in " ".join(a):
    print("[Merger] Merging formats into \"%s\"" % path, flush=True)
open(path, "wb").write(b"\0" * 20000)
print("NEBFILE|" + path, flush=True)
