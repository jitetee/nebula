# ant — terminal coding agent

Part of Nebula. Pure Python 3 (standard library only): no Node, no npm, no packages.

```
ant                    start a session in the current folder
ant -c                 resume the latest session
ant --session <id>     resume a specific one
```

Inside: `/help`, `/setup` (provider + key), `/model`, `/mode` (default, acceptEdits, plan, yolo), `/run <cmd>` or `!<cmd>`.
Ctrl-C cancels a running turn; press it twice at the prompt to quit.

Config and sessions live in `~/.ant`. Run directly with `PYTHONPATH=apps/ant python3 -m ant`.
