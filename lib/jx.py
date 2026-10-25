#!/usr/bin/env python3
"""jx.py - JSON reshaping for the crypto and sports dashboards (replaces jq; stdlib only).

Usage: <json on stdin> | jx.py <op> [arg]
Rows are printed with the unit separator (0x1f) between fields, like the old jq programs.
"""
import json
import sys

SEP = "\x1f"


def ts(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() and abs(v) < 1e17 else repr(v)
    return str(v)


def alt(*vals, default=""):
    for v in vals:
        if v is not None and v is not False:
            return v
    return default


def g(o, *path):
    for p in path:
        if isinstance(o, dict):
            o = o.get(p)
        elif isinstance(o, list) and isinstance(p, int):
            try:
                o = o[p]
            except IndexError:
                return None
        else:
            return None
    return o


def out(fields):
    print(SEP.join(ts(f) for f in fields))


def sides(ev):
    c = g(ev, "competitions", 0, "competitors") or []
    home = next((x for x in c if x.get("homeAway") == "home"), None) or (c[0] if c else {})
    away = next((x for x in c if x.get("homeAway") == "away"), None) or (c[1] if len(c) > 1 else {})
    return home or {}, away or {}


def main():
    op = sys.argv[1] if len(sys.argv) > 1 else ""
    raw = sys.stdin.read()
    try:
        d = json.loads(raw)
    except ValueError:
        sys.exit(1)
    if op == "is-array":
        sys.exit(0 if isinstance(d, list) else 1)
    if op == "coin-id":
        c = g(d, "coins", 0, "id")
        if c:
            print(c)
    elif op == "market-total":
        print(ts(sum((x.get("market_cap") or 0) for x in d)))
    elif op == "market-rows":
        for x in d:
            sp = g(x, "sparkline_in_7d", "price") or []
            out([x.get("symbol"), x.get("current_price"), alt(x.get("price_change_percentage_24h")), x.get("market_cap"),
                 " ".join(ts(p) for p in sp)])
    elif op == "market-top5":
        for x in d[:5]:
            out([x.get("symbol"), x.get("market_cap")])
    elif op == "home-crypto":
        for x in d:
            sp = g(x, "sparkline_in_7d", "price") or []
            out([x.get("symbol"), x.get("current_price"), alt(x.get("price_change_percentage_24h")), " ".join(ts(p) for p in sp)])
    elif op == "coin-row":
        x = d[0] if isinstance(d, list) and d else {}
        out([x.get("name"), x.get("symbol"), x.get("market_cap_rank"), x.get("current_price"),
             alt(x.get("price_change_percentage_24h_in_currency")), alt(x.get("price_change_percentage_7d_in_currency")),
             alt(x.get("price_change_percentage_30d_in_currency")), x.get("high_24h"), x.get("low_24h"),
             x.get("market_cap"), x.get("total_volume"), x.get("ath")])
    elif op == "chart-t0":
        print(int((d["prices"][0][0]) / 1000))
    elif op == "chart-t1":
        print(int((d["prices"][-1][0]) / 1000))
    elif op == "chart-prices":
        for p in d["prices"]:
            print(ts(p[1]))
    elif op in ("sports-rows", "home-sports"):
        for ev in d.get("events") or []:
            h, a = sides(ev)
            ht, at = h.get("team") or {}, a.get("team") or {}
            st = g(ev, "status", "type") or {}
            if op == "sports-rows":
                out([ev.get("date"), st.get("state"), alt(st.get("shortDetail")), alt(g(ev, "status", "displayClock")),
                     alt(ht.get("displayName"), g(h, "athlete", "displayName"), default="?"),
                     alt(ht.get("abbreviation"), g(h, "athlete", "shortName")), alt(h.get("score")),
                     alt(at.get("displayName"), g(a, "athlete", "displayName"), default="?"),
                     alt(at.get("abbreviation"), g(a, "athlete", "shortName")), alt(a.get("score")), alt(ev.get("name"))])
            else:
                out([st.get("state"), alt(st.get("shortDetail")),
                     alt(ht.get("abbreviation"), g(h, "athlete", "shortName"), default="?"), alt(h.get("score")),
                     alt(at.get("abbreviation"), g(a, "athlete", "shortName"), default="?"), alt(a.get("score")), ev.get("date")])
    elif op == "standings":
        for grp in (d.get("children") or [d]):
            gname = alt(grp.get("name"))
            for e in g(grp, "standings", "entries") or []:
                s = {}
                for st in e.get("stats") or []:
                    s[st.get("name")] = alt(st.get("value"), default=0)
                gv = lambda k: alt(s.get(k), default=0)
                out([gname, g(e, "team", "displayName"), gv("rank"), gv("gamesPlayed"), gv("wins"), gv("ties"), gv("losses"),
                     gv("pointDifferential"), gv("points"), gv("winPercent")])
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
