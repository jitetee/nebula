"""nebula_core: the small shared layer every Nebula tool (shell, ant, jtlearn, plugins) uses.

  paths   where Nebula lives and where its data/plugins are
  help    one registry (assets/help.txt + plugin help) rendered the same way everywhere
  ai      one AI backend choice (ant or tgpt) for the shell, jtlearn and plugins

Standard library only. Import it with `lib/` on PYTHONPATH (the launchers set that up).
"""
VERSION = "1"
