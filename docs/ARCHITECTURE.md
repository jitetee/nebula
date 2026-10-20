# nebula Architecture

```
nebula/
├── bin/
│   └── nebula                  # entrypoint: one-shots OR boot → login → REPL
├── lib/
│   ├── ui.sh                 # colors, banners, ls/ll wrappers, status ticks
│   ├── voice.sh              # espeak / festival / termux-tts abstraction
│   ├── sound.sh              # sox-synthesized beeps / chime / power sweeps
│   ├── auth.sh               # first-run setup + login (sha256, 0600 file)
│   └── commands.sh           # REPL command implementations
├── assets/
│   ├── banner.txt            # small nebula ASCII logo
│   ├── colors.properties     # Nebula-blue Termux theme
│   ├── termux.properties     # 3-row extra-keys layout
│   ├── memes.txt             # bundled meme URLs (offline fallback)
│   └── fonts/FIRACODE_NERD.md # pointer to the Nerd Font upstream
├── motd/
│   ├── init.sh               # runs motd.d/NN-* in order
│   └── motd.d/
│       ├── 10-nebula-logo      # big Nebula banner
│       ├── 20-sysinfo        # distro/host/kernel/load/mem/cpu
│       └── 35-diskspace      # filtered disk-usage (compact)
├── zsh/
│   ├── nsh.zsh               # the NSH framework (replaces oh-my-zsh)
│   ├── zshrc.template        # the managed # nebula-BEGIN/END block
│   ├── plugins/
│   │   ├── autosuggestions/  # → / Ctrl-F to accept
│   │   ├── syntax-highlighting/ # token-classifying highlighter
│   │   ├── nebula-pick/      # Tab picker (our own fuzzy finder, no fzf)
│   │   └── z/                # frecent directory jump
│   └── themes/
│       └── studio.zsh-theme  # configurable prompt (`theme studio`)
├── install/
│   ├── install.sh            # non-destructive installer
│   └── uninstall.sh          # safe uninstall (restores backups)
└── docs/
    ├── ARCHITECTURE.md       # this file
    └── CHANGELOG.md
```

## Design principles

1. **Non-destructive by default.** The installer only installs *missing*
   packages; the uninstaller only removes nebula's own files and restores
   `.nebula-backup` files. Shared tools are never touched because other
   projects on the user's machine may depend on them.

2. **Vendor everything.** No runtime dependency on external git repos
   (oh-my-zsh, powerlevel10k, termux-motd, zsh-autosuggestions,
   zsh-syntax-highlighting, z). We own the code, users get fewer
   surprises, updates are atomic via `nebula update`.

3. **Degrade gracefully.** Every optional dependency is gated by
   `command -v`. If `espeak` isn't present, the UI is silent but still
   works. If `tgpt` isn't present, AI commands print a helpful hint.
   If `fzf` isn't present, Ctrl-R falls back to zsh default.

4. **Stay out of the user's way.** Unknown REPL input is passed straight
   to the shell via `eval`, so nebula never blocks a workflow the user
   already has.

5. **Local-only auth.** Passwords are sha256-hashed and stored at
   `$PREFIX/opt/nebula/data/auth` with `0600`. No network, no telemetry.

6. **Managed .zshrc block.** Everything the installer adds lives inside
   `# nebula-BEGIN ... # nebula-END`. The uninstaller removes the block
   cleanly, including its header comments.

## Launch flow

### Interactive (`nebula`)
```
nebula
  ├─ boot sequence  (motd banner + power-on sweep + fake init ticks, 1s)
  ├─ auth::login    (first run → auth::setup; 3 attempts → lockout)
  ├─ post-login     (motd banner + voice::greet + maker intro)
  └─ REPL           (dispatch → command modules → shell fallthrough)
```

### One-shot (`nebula ask <q>`, `nebula joke`, …)
```
nebula <subcommand> [args...]
  └─ skip boot/login/REPL → run one command → exit
```

## Extending nebula

Add a new command:

1. Add a `cmd::mything()` function to `lib/commands.sh`.
2. Add a dispatch case to `nebula::repl` in `bin/nebula` (for the REPL).
3. If the command should also work as a one-shot, add a case to the
   `main()` switch in `bin/nebula`.
4. Add the command to `cmd::help` and the README.

Add a new prompt theme:

1. Drop `assets/prompts/<name>.conf` (see the existing ones for the keys).
2. Users switch via `theme <name>`.
