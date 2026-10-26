#!/usr/bin/env python3
"""JSON helper for Mingle (the standard library only). Usage:  mj.py <op> [args]  with JSON on stdin.

  get [-d DEFAULT] path...    first value found, printed plain (true/false for booleans)
  keys | len                  keys one per line | number of children
  obj k=v k:=json k=@ts       build a JSON object (empty strings are left out; @ts = server timestamp)
  set k=v ...                 add/replace fields in the JSON on stdin
  fields a b=0 c              chosen fields joined with \\x1f (so empty values keep their place)
  candidates ...  rescore ...  matches ...  messages ...  reports ...  (Mingle's own lists)
"""
import json
import sys

US = "\x1f"


def load():
    t = sys.stdin.read().strip()
    if not t:
        return None
    try:
        return json.loads(t)
    except ValueError:
        return None


def dig(o, path):
    for k in path.split("."):
        if isinstance(o, dict):
            o = o.get(k)
        elif isinstance(o, list) and k.isdigit() and int(k) < len(o):
            o = o[int(k)]
        else:
            return None
    return o


def s(v):
    if v is None:
        return ""
    if v is True:
        return "true"
    if v is False:
        return "false"
    return str(v)


def parse_kv(args):
    import re
    out = {}
    for a in args:
        m = re.match(r"^([^=:]+):=(.*)$", a, re.S)
        if m:
            out[m.group(1)] = json.loads(m.group(2))
            continue
        k, v = a.split("=", 1)
        if v == "@ts":
            out[k] = {".sv": "timestamp"}
        elif v != "":
            out[k] = v
    return out


def words(x):
    return [w.strip() for w in (x or "").lower().split(",") if w.strip()]


def score(me, p):
    mine, theirs = words(me.get("interests")), words(p.get("interests"))
    shared = len([w for w in mine if w in theirs])
    union = len(set(mine) | set(theirs)) or 1
    sc = shared * 100 // union
    if (p.get("city") or "").lower() == (me.get("city") or "").lower():
        sc += 25
    return min(sc, 99), shared


def wants(gender, seeking):
    return seeking == "everyone" or (seeking == "men" and gender == "man") or (seeking == "women" and gender == "woman")


def main():
    a = sys.argv[1:]
    op = a[0] if a else ""
    rest = a[1:]
    if op == "obj":
        print(json.dumps(parse_kv(rest), separators=(",", ":"), ensure_ascii=False)); return
    d = load()
    if op == "get":
        default = ""
        if rest[:1] == ["-d"]:
            default, rest = rest[1], rest[2:]
        for p in rest:
            v = dig(d, p)
            if v is not None and v != "":
                print(s(v)); return
        print(default); return
    if op == "keys":
        if isinstance(d, dict):
            print("\n".join(d.keys()))
        return
    if op == "len":
        print(len(d) if isinstance(d, (dict, list)) else 0); return
    if op == "set":
        d = dict(d or {}); d.update(parse_kv(rest)); print(json.dumps(d, separators=(",", ":"), ensure_ascii=False)); return
    if op == "fields":
        out = []
        for f in rest:
            k, _, dv = f.partition("=")
            v = dig(d, k)
            out.append(s(v) if v is not None else dv)
        print(US.join(x.replace("\n", " ") for x in out)); return
    if op == "rescore":
        me = json.loads(rest[0]); d = dict(d or {})
        d["score"], d["shared"] = score(me, d)
        print(json.dumps(d, separators=(",", ":"), ensure_ascii=False)); return
    if op == "candidates":
        uid, me, likes, passes, blocks, bb, onlycity = rest[0], json.loads(rest[1]), *[json.loads(x) if x else {} for x in rest[2:6]], rest[6] if len(rest) > 6 else ""
        likes, passes, blocks, bb = (x or {} for x in (likes, passes, blocks, bb))
        out = []
        for k, p in (d or {}).items():
            if k == uid or k.startswith("_") or not isinstance(p, dict) or p.get("visible", True) is False:
                continue
            if k in likes or k in passes or k in blocks or k in bb:
                continue
            if not (wants(p.get("gender"), me.get("seeking")) and wants(me.get("gender"), p.get("seeking"))):
                continue
            if onlycity and (p.get("city") or "").lower() != (me.get("city") or "").lower():
                continue
            q = dict(p); q["uid"] = k; q["score"], q["shared"] = score(me, p)
            out.append(q)
        out.sort(key=lambda q: (-q["score"], -(q.get("ts") or 0)))
        for q in out:
            print(json.dumps(q, separators=(",", ":"), ensure_ascii=False))
        return
    if op == "matches":      # matches <sort|row KEY>
        d = d or {}
        if rest[0] == "sort":
            ks = sorted(d, key=lambda k: -(d[k].get("lastTs") or d[k].get("ts") or 0))
            print("\n".join(ks))
        else:
            m = d.get(rest[1]) or {}
            print(US.join([s(m.get("last") or ""), s(m.get("lastFrom") or ""), s(m.get("lastTs") or 0), s(m.get("seen") or 0), s(m.get("pair") or "")]))
        return
    if op == "unread":
        me = rest[0]
        print(len([1 for m in (d or {}).values() if m.get("lastFrom") and m.get("lastFrom") != me and (m.get("lastTs") or 0) > (m.get("seen") or 0)])); return
    if op == "messages":     # messages sig | rows KEEP
        items = sorted((d or {}).items(), key=lambda kv: kv[1].get("ts") or 0)
        if rest[0] == "sig":
            print(str(len(items)) + (items[-1][0] if items else ""))
        else:
            keep = int(rest[1])
            for _, m in items[-keep:]:
                t = (m.get("text") or "").replace("\t", " ").replace("\n", " ").replace(US, " ")
                print(US.join([s(m.get("from")), t, s(m.get("ts") or 0)]))
        return
    if op == "reports":      # reports open | line KEY WIDTH | field KEY FIELD
        d = d or {}
        if rest[0] == "open":
            ks = [k for k, v in d.items() if not k.startswith("_") and isinstance(v, dict) and v.get("status") != "done"]
            ks.sort(key=lambda k: -(d[k].get("ts") or 0))
            print("\n".join(ks))
        elif rest[0] == "line":
            r = d.get(rest[1]) or {}; w = int(rest[2])
            print(f"{(r.get('about') or '')[:8]}… {(r.get('reason') or '')[:w]} ({r.get('status') or 'open'})")
        else:
            print(s((d.get(rest[1]) or {}).get(rest[2])))
        return
    if op == "wing":         # wing me   (stdin = their profile)
        me = json.loads(rest[0]); p = d or {}
        print(f"Name: {p.get('name')}. Age: {p.get('age')}. City: {p.get('city')}. Bio: {p.get('bio') or 'none'}. Interests: {p.get('interests') or 'none'}. My interests: {me.get('interests') or 'none'}.")
        return
    sys.exit("mj.py: unknown op " + op)


main()
