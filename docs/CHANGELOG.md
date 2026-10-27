# Changelog

## 0.9.11
- voice engine update and ui improvements

## 0.9.7

- **Your own voice (ONNX).** `voice scan` (or plain `voice` when none is set) searches the whole device for Piper voices (a `.onnx` with its `.onnx.json`), lists them, and copies the one you pick into Nebula's data folder (`data/voices`, kept across updates). `voice model /path/voice.onnx` also makes Nebula speak with a Piper voice (`.onnx` plus its `.onnx.json`); `voice test` tries it, `voice model clear` goes back. It needs the `piper` program (or `pip install piper-tts`) and any audio player (sox, mpv, paplay…). Spoken phrases are cached, and if the ONNX voice fails it falls back to espeak, festival or Termux TTS.
- Game headers use a `◆ Title` bar, slow network fetches and Mingle discover show a spinner, and `.github/workflows/ci.yml` checks syntax, rules, `.jif` files and the shared look on every push.
- **One look everywhere.** Nebula, the games, Mingle and ant now share jtlearn's style: green rounded panels with titles, big block-letter banners in a double frame, two-column menus, framed tables, chat bubbles in Mingle, a `└─➤ Your choice:` prompt and framed game-over cards. It comes from one small helper (`lib/skin.py` + `lib/skin.sh`); under 40 columns, with `NO_COLOR` or `NEBULA_PLAIN=1` it falls back to simple lines. See `docs/UI_STYLE.md`.
- **Extra keys:** the bottom-right `lock` button is now a real **ENTER** key (swipe up for `lock`). `^D` is still CTRL then `d`.
- **New: JIF Store.** Browse, rate, download and submit `.jif` packages on the website; jtlearn's Data Store (menu 9) now reads the same online store (`jifStore`), installs binary `.jif` files, and shows ratings. The rules and seed cover the store and every other node used by Nebula, Mingle, games and jtlearn (empty collections hold a `_schema` placeholder that all clients skip). Screenshots of the CLI and website are in `docs/screenshots/`.
- **New: `mingle`**, a dating app for the terminal (18+): sign in with email and password, or a username and a key; discover people with a match percentage, like, pass or super like; chat when you both like each other (live updates); see who liked you; block, report, unmatch; delete your account and all your data. Admins (role `admin` or `superadmin` in your database) can review reports and ban with `mingle admin`. Nothing extra to install.
- **New complete database rules and seed.** `docs/database.rules.json` is the full rule set (default-deny; admins are accounts whose `users/<uid>/role` is `admin` or `superadmin`), and the website repo ships a matching `seed.json`. The old merge script and partial rules file are gone.

- **New: `ant`**, an AI coding agent for your terminal. It works in the folder you start it in, can read and edit files and run commands (asking first for risky ones), and talks to OpenAI-compatible providers. It is pure Python 3 (standard library only): no Node.js, no npm. Config and sessions stay in `~/.ant`.
- **New file type: `.jif` (JITETEE Import File)** replaces the old lesson-package format. Same simple layout (128-byte header + JSON) with a `JIF` header. All bundled courses were converted; make your own with `python3 apps/jtlearn/jif_tool.py pack notes.json -o my_course.jif`. The "Verse" game is now called JT-Verse. Online store paths use `jif` names too.
- **New: `jtlearn`** (alias `learn`), a learning system with study notes, quizzes, tracks and offline AI. Pure Python 3: no `click` or `rich` to install, and it uses Nebula's green look. Settings are kept in Nebula's data folder, so updates do not reset them; data from an old `~/.jtlearn` is moved to `~/.jtlearn` the first time you run it.
- **New: Rage Bait** in jtlearn (menu `R`, or `jtlearn rage`): trick questions that teach. Myth-or-fact rounds, a letter-counting trap, a patience test, a loading bar that restarts at 99%, and a computer that cheats at guessing. Keep your rage meter under 100%; your best score is saved.
- **No more `jq`:** crypto, sports and the home dashboard use a small Python helper (`lib/jx.py`) instead. Nebula now needs only bash, awk, python3 and curl for everything in the box (zsh stays optional for the fancy prompt).

- **Rebrand:** Nebula now uses the same phosphor-green look as the J.I.T.E.T.E.E. website (colours, prompt defaults, credits line). Set `NEBULA_BRAND=classic` to get the old cyan back. Saved prompt settings are not changed.
- **Fixed:** `nebula sysinfo` crashed when `$USER` is not set (common on Termux). The startup screen no longer needs a Termux-only interpreter path. `nebula <command> --help` and `--version` now reach the command instead of Nebula's own help.
- **Security:** the jtlearn Firebase key is no longer written in plain text in the source (GitHub flagged it). It now lives in a packed file, and environment variables override it. Restrict or rotate the key in Google Cloud (see the README).
- Added a proper `.gitignore` (local data, caches, editor files; per-user jtlearn settings).

## 0.9.6

- **New: `report`** sends a bug report or idea to the developer through Firebase. It shows exactly what will be sent (your message, Nebula and Android version, phone model) and asks first.
- **New: `game versus`** is online tic-tac-toe: one player hosts and gets a room code, the friend joins with it.
- The Firebase settings are not stored as readable text. They are split into scrambled chunks in `assets/cloud/` and rebuilt in memory (`tools/pack-cloud.py` re-packs them). This hides them from casual reading only; the real protection is the security rules in `docs/RTDB_RULES.json`.

## 0.9.5

- **New: `game`** adds 18 games (drawing uses no subprocesses, so Snake and Tetris stay smooth on phones; the game rules are covered by tests) with saved scores. Puzzle: 2048, Wordle, Hangman, Number guess, Mastermind, Memory, Minesweeper. Action: Snake, Tetris. Simulations: Game of Life, Ecosystem (grass, rabbits, foxes), Café Tycoon (run a cyber café for 30 days), plus Matrix rain and Fireplace screensavers. Extras: Quest (an AI text adventure that saves your progress), Quiz (Kenya, coding, Bible, general), Typing test, and a Daily puzzle with a streak. `game` opens a menu, `game <name>` starts one, `game scores` lists your bests. Boards adapt to the screen size.

## 0.9.4

- **New: `dev`** runs a bot or site in the background: `dev start [name] [--port N]` (finds `npm start`, `index.js`, `app.py`… or serves the folder), `dev stop|restart|ls`, `dev logs <name> [-f]`, and `dev errors <name>` which shows only the errors with a little stack context. `deploy` publishes a Firebase site after asking.
- **Security: salted password hashing.** Logins now use PBKDF2-SHA256 with a random salt (120,000 rounds). Old SHA-256 logins keep working and are upgraded automatically the first time you log in. Going back to an older Nebula needs `nebula --reset-auth`.

## 0.9.1
- **Updates no longer time out on mobile data** (download limit raised from 15 s to 4 min, with retries), and `nebula update` / `nebula` move to your home folder when started from a deleted one, instead of printing `chdir: error retrieving current directory` at every step.
- **`nebula update` now sees new commits, not just a new version number.** It said "up to date" whenever `VERSION` matched, even if the repo had newer commits pushed without a version bump. It now also compares the latest commit on GitHub with the one you installed (`data/.installed_sha`), shows `v0.9.1 → newer commit abc1234`, and the background notice says `New changes on GitHub`.
- **Update notice that actually shows.** Nebula checks GitHub for a newer version in the background every 4 hours (never delaying startup) and shows `⚠ Update available: Nebula vX (you have vY)` after the home screen. Before, the check ran in the foreground once a day and its message was wiped by the screen clear after login. `nebula update --notice` prints it on demand.
- `push.sh` bumps `VERSION` by one patch step per push (and the README badge and a CHANGELOG line) so that notice reaches everyone.
- **Fixed `shell-init: error retrieving current directory`** after the session's folder was deleted: the zsh config and `.bashrc` now move to `$HOME` when the current folder no longer exists.
- **Fixed the prompt jumping to a new line every time the Android keyboard opens or closes.** The prompt's resize trap (`TRAPWINCH`) returned a non-zero status when the width hadn't changed, which makes zsh abort the line and print a fresh prompt. It (and the idle-lock trap) now return 0.
- **New extra-keys layout** (`keys` shows a cheat sheet, `keys reload` applies it): the old `VOL+` / `VOL-` / `MUTE` buttons are not real Termux keys and just typed their own names. They are replaced by useful keys: `^C`, `^D`, `hist` (Ctrl-R), `file` (Ctrl-T), `dir` (Alt-C), `clr`, a `KEYBOARD` toggle, brackets and quotes, and swipe-up popups (PgUp/PgDn/Home/End, `| _ * ; ~`, `^Z`, `status`, `help`, `cd ..`). Needs Termux 0.118+.
- **Fixed `todo done N`** marking the wrong task (or none) once any item was already done: it now uses the same numbering the list shows, and validates the number (`todo rm` too).
- **Fixed the `home` command always clearing the screen**, and the editor's "Preview now" printing an error (`HC[clear]=0 cmd` is not valid bash). `home::render noclear` replaces it.
- **Fixed `status` / `dash` top-processes bars** being far too wide on phones (variable used before it was set), which cut off the memory column.
- **Fixed home-screen news refresh** (`local … t l d` ran `t` as a command and leaked variables). Headlines are now cached raw and formatted to your screen width at display time.
- **Responsive fixes:** grid columns are clipped to their own width (no more chopped right column), greeting/todo/reminders/tip/news adapt to width, tips wrap, `help <cmd>`, `help search`, `doctor`, `tour`, `todo`, `notes`, `logins`, `reminders` and every status message (`ui::say_status`) now word-wrap with a hanging indent, install spinner no longer wraps (and follows resizes), menus count emoji as 2 cells, and the installer's package picker re-measures on resize.
- `doctor` now recognises mpv or mpg123, and sox or play.
- `README` trimmed to the essentials; `ARCHITECTURE.md` file tree corrected.

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
