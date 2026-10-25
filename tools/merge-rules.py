#!/usr/bin/env python3
"""Add Nebula's rules (site, nebula, mingle) to the rules you already have.

Your live rules protect your existing app (users, orders, courses ...). This tool
leaves every one of those nodes exactly as it is and only adds three new top-level
nodes: site, nebula and mingle. Admins are the accounts whose users/<uid>/role is
'admin' or 'superadmin' (and not disabled), the same as in your app.

  1. Firebase console -> Realtime Database -> Rules -> copy everything into current.json
  2. python3 tools/merge-rules.py current.json > merged.json
  3. Paste merged.json back into the console and Publish.
Use --replace to overwrite site/nebula/mingle if they already exist in current.json.
"""
import json, sys, os, re

here = os.path.dirname(os.path.abspath(__file__))
add = json.load(open(os.path.join(here, '..', 'docs', 'rtdb-additions.json')))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
replace = '--replace' in sys.argv
if not args:
    sys.exit(__doc__)
raw = open(args[0]).read()
raw = re.sub(r'^\s*//.*$', '', raw, flags=re.M)           # the console allows // comments
raw = re.sub(r'/\*.*?\*/', '', raw, flags=re.S)
cur = json.loads(raw)
rules = cur.get('rules')
if not isinstance(rules, dict):
    sys.exit('current.json has no "rules" object')
for k, v in add.items():
    if k in rules and not replace:
        print(f'note: "{k}" already exists in your rules, left as is (use --replace to overwrite)', file=sys.stderr)
        continue
    rules[k] = v
    print(f'added: {k}', file=sys.stderr)
json.dump(cur, sys.stdout, indent=2); print()
