# Changelog

## 0.9.0
- **Responsive everywhere.** One shared layout layer measures your screen (and re-measures on resize/rotation). Breakpoints xs/sm/md/lg/xl. Dashboards, the home screen, news, sports and crypto lay themselves out in 1–4 columns; bars, tables and charts scale to the space; lists wrap instead of overflowing. Checked at 30, 34, 44, 80, 130 and 200 columns: no overflowing lines.
- **`nebula dash`**: a true full-screen dashboard (alternate screen) that fills the terminal, scrolls, toggles panels and reflows live when you resize. `status --live` opens it.
- **Responsive prompt**: on narrow screens optional segments are dropped and the path shortens; it re-adapts live when the window is resized (toggle in `theme studio`).
- **`layout auto|phone|wide`** setting; menus and the picker redraw instantly on resize; the logo centres on wide screens and falls back to a one-line title on tiny ones.
- Fixed: `crypto <coin>` chart variable collision; emoji counted as 1 cell (misaligned columns).

## 0.8.0
- **Talk to Termux directly.** Type a command that isn't installed (e.g. `gh auth login`): Nebula offers to install the package, then runs what you typed. Type a plain-English sentence and Nebula AI turns it into a plan of commands you review and approve; the commands run in your own shell (so `cd` and `export` stick). Risky commands (rm -r, dd, sudo, curl | sh, force-push…) are marked ⚠ and need you to type `yes`. `tell <request>` does it on purpose; `english ask|auto|off` controls how eager it is.
- **Nebula shell escapes:** `!command` sends a line to Termux exactly as typed, `?request` is plain English. Names that are also real commands (`install -m`, `date +%s`, `time ls`, `ip a`) now go to the real command.
- Fixed: a normal install no longer leaves a "finish setup" hint behind.

## 0.7.0
- **Prompt studio** (`theme studio`): config-driven prompt with 8 segments, 8 presets, live preview, per-field editing, colour chooser, share codes (`theme export/import`). Changes apply to your open shell instantly.
- **Home screen** (`home edit`): choose and order widgets (logo, greeting, CPU/RAM, storage, battery, network, todo, reminders, weather, crypto, news, sports, tip, trend). Network widgets are cached and refreshed in the background. After login the screen clears and the home screen shows.
- **Profiles** (`profile use work`): switch voice, sounds, auto-lock, startup mode, prompt and home screen at once; save, share and import profiles (whitelisted settings only).
- **`status` dashboard**: CPU (overall + per core), memory, swap, every storage mount, battery, network speeds, temperatures, top processes, trend history, and `--live` mode.
- **Installable with pkg**: `.deb` build, APT repository generator, GitHub Actions release, `add-repo.sh`, Termux recipe, `nebula setup`, package-aware `nebula update`. See docs/PACKAGING.md.
- **Fixed**: garbled `─` lines on Termux (`tr` is byte-based); `gawk` "Invalid collation character" error that hid AI replies (and a plain-text fallback if rendering ever fails); logo shown twice and no clear after login; wide logo wrapping on narrow screens; relative-symlink launch from a package; compact startup is no longer triggered by 32-bit alone and still shows status and storage.
- Custom banner now lives in `data/banner.txt` (survives updates and package upgrades).

## 0.6.0
- **AI output** is rendered as styled terminal text (headings, bold, italics, code boxes, lists, tables, links, word-wrap) via a built-in markdown renderer.
- **Dashboards:** `crypto` (top-10 table, sparklines, area charts, ranges, 8 currencies), `news` (cards, freshness colours, trending words, open/ai), `sports` (live/upcoming/finished cards, tables, league picker, 20 leagues).
- **`nebula install`:** 130+ tool database, automatic pkg/pip/npm/cargo/go/gem selection, prerequisites, live progress, self-healing retries, fallbacks, discovery of unknown names, `uninstall`.
- **Own fuzzy picker** (no fzf): Tab, Ctrl-R, Ctrl-T, Alt-C; context-aware candidates. Rewritten pure-zsh suggestion engine: `cd` suggests your most-visited / matching folders, `nebula install <x>` suggests tools.
- **`nebula play`:** device-wide, typo-tolerant music search; player detection with light/heavy install advice.
- **Installer:** curl one-liner bootstrap; folder locked to `700`; Termux files are links to `opt` with originals saved under `data/backups`; offers to delete the clone/ZIP after install; packages with no build for your CPU are flagged.
- **`nebula update`** from GitHub without git: validates the download, keeps `data/`, backs up and supports `--rollback`, daily update hint, cleans temp files.
- New: `voice on/off` and `sounds on/off` from the shell; gawk/jq in the basic package set.
- README rewritten with installation, usage, security, configuration and troubleshooting.


## 0.5.0
- **Device awareness:** `settings` (arrow-key menu: Device, Health, Features, Security, Install missing, Termux:API guide), `device`, `scan`. Detects CPU/bits, Android, RAM, storage, Termux version and install source, Termux:API (probed for real), storage permission, internet.
- **Graceful degradation:** commands the device can't run are hidden from help, completion and suggestions, and explain themselves if typed. Battery falls back to the system file or the row is dropped; reminders fall back to an in-terminal alert when there are no phone notifications; compact startup auto-enables on weak/32-bit devices.
- **Installer:** flags packages with no build for your CPU, and `--want` pre-selects what Settings says is missing.
- **Termux:API guide** for phones that can't use the Play Store or install APKs (source matching, GitHub/F-Droid, ADB, wireless debugging, No-API mode).

## 0.4.0
- **Security:** 3 failed login attempts now close the entire Termux session (was: lock loop). New `passwd`, `lock`, `autolock` (idle lock in zsh and the Nebula shell), `logins` history, optional `fingerprint`. `noauth on` and in-shell `reset-auth` ask for your password.
- **AI:** `chat`, `explain`, `fix`, `summarize`, `translate`.
- **Help:** registry-driven `help`, `help <cmd>`, `help search`, "did you mean", zsh tab-completion; Nebula commands work directly in zsh.
- **Data:** `backup` / `restore` (optional AES-256 encryption, path-safe restore, pre-restore snapshot).
- **Tools:** `status`, `remind`, `serve`, `tour`; `todo pri`, `notes search/rm/edit`; `theme builder`; `doctor --fix`.
- Storage bars in the MOTD are twice as long (20 cells) and adapt to narrow screens.
- Fixed: `note`/`todo` never saved (`printf '- …'` treated as an option); missing `_nsh_accept_line` error on every Enter; `?` in the REPL matching any one-letter command; REPL now has line editing + history.
- zsh history moved to the Nebula data folder.

## Nebula rebrand
- Renamed cvui → **Nebula**, KAI → **Nebula AI**, command is now `nebula`, framework `ksh` → `nsh`.
- New NEBULA logo; fixed `banner.sh` glyph padding so ragged letters (L, A…) no longer collide.
- Everything now installs to `$PREFIX/opt/nebula` (data in `…/nebula/data`) instead of `~/.cvui-app` / `~/.cvui`.
- Installer: arrow-key dependency picker (Basic pre-selected, nothing installed without confirmation); `nebula deps` to reopen it.
- Installer no longer overwrites `~/.zshrc` (appends a managed block) and only auto-starts zsh when zsh exists.
- Detects an old cvui install and offers to migrate login/notes.
- Uninstaller keeps `data/` unless `--purge-config`.

## 0.3.0 — 2026-04-25

### Added
- **Nebula AI** — the AI persona replacing Nebula AI across all user-facing strings
  (commands, banners, voice, docs). `nebula ask` prompts now say `🤖 Nebula AI:`.
- **News** — `nebula news` prints top 5 Hacker News headlines with URLs.
- **Crypto** — `nebula crypto [coin]` shows USD + KES + 24h change via CoinGecko.
  Accepts aliases (btc/eth/sol/doge/…) or any CoinGecko id.
- **IP** — `nebula ip` shows public IP + city/region/country + org (ipinfo.io).
- **Define** — `nebula define <word>` dictionary lookup (dictionaryapi.dev).
- **QR** — `nebula qr <text>` renders an ANSI QR code (requires qrencode).
- **Notes** — `nebula note <text>` appends to `$PREFIX/opt/nebula/data/notes.md`; `nebula notes` lists.
- **Todo** — `nebula todo [text]` / `todo done N` / `todo rm N` / `todo clear`
  against `$PREFIX/opt/nebula/data/todo.md`.
- **Timer** — `nebula timer <minutes>` pomodoro with voice + chime + notification.
- **Doctor** — `nebula doctor` audits every optional dep and nebula file with ✓/✗.
- **Password mask** — auth now echoes `*` per keystroke (backspace supported).
- **Disk bar** — motd disk panel shows `[█████░░] 87%  27G/28G` inline.
- Installer pulls `qrencode` and `termux-api` (optional).

### Changed
- **Compact motd** — removed the `Date & Time:` panel; time now lives on the
  prompt's RPROMPT as `HH:MM:SS`.
- **Prompt** — hides the git branch segment by default (less noise).
- **Joke / fact** — each call picks a random topic + nonce so tgpt stops
  repeating the same punchline.
- **Load-average parsing** — robust against `uptime` format variations.
- Installer / repo URL: `cybervaultke` → `cybervaultke` (username change).
- Socials: X/Twitter → Facebook in the maker intro.

## 0.2.0 — 2026-04-24

### Added
- **One-shot modes** — run commands without entering the REPL:
  `nebula ask <q>`, `nebula joke`, `nebula fact`, `nebula weather [city]`,
  `nebula sysinfo`, `nebula motd`, `nebula update`, `nebula theme [name]`
- **`nebula update`** — self-updates the install via `git pull` + re-runs
  the installer to refresh assets.
- **Prompt themes** — `nebula theme [name]` lists / switches. Three
  built-ins: `nebula` (Nebula-blue, default), `minimal`, `cyberpunk`.
  Selection persisted in `$PREFIX/opt/nebula/data/theme`.
- **fzf integration** in NSH (`zsh/plugins/fzf/`):
  - `Ctrl-R` — fuzzy history search
  - `Ctrl-T` — fuzzy file picker with preview
  - `Alt-C` — fuzzy `cd`
- **Motd date/time panel** (`motd/motd.d/25-datetime`).
- Installer now pulls `fzf` and `fd` (optional).
- REPL commands: `theme`, `update`, `motd`, `time`, `date`.

### Changed
- **Login screen** now uses the full motd (big cybervaultke banner +
  sysinfo + datetime + disk) instead of the Nebula AI-face mini-banner.
- `nebula --help` shows the new usage with one-shot subcommands.

### Removed
- Dropped the old `kai.txt` mini-face from the post-login screen.

## 0.1.0 — 2026-04-24

Initial release.

- ASCII boot banner + fake init sequence
- First-run account setup (sha256-hashed local credentials)
- Login screen with 3-attempt lockout
- Nebula AI voice via `espeak` / `festival` / `termux-tts-speak`
- Maker intro with cybervaultke socials
- Commands: `help`, `about`, `ask`, `joke`, `fact`, `meme`, `weather`,
  `sysinfo`, `ls`, `ll`, `cd`, `clear`, `voice`, `whoami`,
  `reset-auth`, `exit`
- Non-destructive installer + uninstaller
- Vendored NSH framework + motd + prompt theme (no oh-my-zsh / p10k /
  external motd dependency)
