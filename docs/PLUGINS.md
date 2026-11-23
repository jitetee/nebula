# Nebula plugins

Nebula is your own terminal OS: the core stays small and everything new arrives as a plugin. A plugin is a
folder. Drop it in `plugins/` (ships with Nebula) or `$NEBULA_CFG/plugins/` (yours, survives updates).

```
greet/
  plugin.sh     defines cmd::greet                     (required)
  help.txt      the registry entry for it              (required)
  nvim.lua      Neovim code, loaded at startup         (optional)
  skills/*.md   skills Ant can use                     (optional)
```

Start one with `nebula plugin new greet`, edit it, then run `nebula greet`.

## What every plugin gets for free
- `help greet`, `greet --help`, tab-completion, "did you mean", and `:NebulaHelp greet` in Neovim, all read
  from your `help.txt` (merged into the one registry, see `lib/registry.sh`).
- The AI the user chose: `python3 -m nebula_core.ai "question"` (ant with their own key, or tgpt).
  Never call `tgpt` directly.
- `nebula plugin disable greet` / `enable greet`, `nebula plugin list`.

## The rules (`nebula check` enforces them, CI too)
1. `plugin.sh` defines `cmd::<folder name>` and passes `bash -n`.
2. `help.txt` has `@<name>|Category|args|one-line summary` plus indented detail lines.
3. Messages go through `ui::say_status OK|INFO|WARN|ERR`. Settings live in `$NEBULA_CFG/<name>/`.
4. Do not handle `--help` yourself: Nebula answers it from `help.txt`.
5. Python tools import `nebula_core` (`paths`, `help`, `ai`) instead of re-implementing them. Standard library only.

## Registry format
```
@name|Category|args|one-line summary
  detail line
  Example: name something
```

## Shared building blocks
| Need | Use |
|---|---|
| where Nebula lives | `$NEBULA_HOME`, `$NEBULA_CFG`, or `nebula_core.paths` |
| ask an AI | `python3 -m nebula_core.ai "..."` or `from nebula_core import ai; ai.ask(prompt, system)` |
| help for your tool | `from nebula_core import help; help.maybe_help("name", sys.argv[1:])` as the first line |
| icons | `ui::` helpers in the shell, `nebula.icons` in Neovim (Nebula Mono glyphs U+E400 to U+E405) |
