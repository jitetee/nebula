<div align="center">

# ⚡ Nebula

### The AI-powered terminal helper for Termux

Real-time dashboards · an AI that formats its answers properly · one-command installs ·
a fuzzy finder built from scratch · a music player that searches your whole phone ·
a prompt studio, a customizable home screen and profiles

[![Version](https://img.shields.io/badge/version-0.9.0-8A2BE2)](docs/CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-Termux%20(Android%207%2B)-3DDC84)](https://termux.dev)
[![Shell](https://img.shields.io/badge/shell-zsh%20%2B%20bash-informational)](#)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[Install](#-installation) · [Features](#-features) · [Commands](#-command-reference) · [Troubleshooting](#-troubleshooting) · [FAQ](#-faq)

</div>

---

## Contents

1. [What is Nebula?](#-what-is-nebula)
2. [Requirements](#-requirements)
3. [Installation](#-installation)
4. [First run](#-first-run)
5. [Features](#-features)
6. [Command reference](#-command-reference)
7. [Keyboard shortcuts](#-keyboard-shortcuts)
8. [Settings, device checks and the Termux:API guide](#-settings-device-checks-and-the-termuxapi-guide)
9. [Where everything is stored](#-where-everything-is-stored)
10. [Security](#-security)
11. [Updating](#-updating)
12. [Turning things off](#-turning-things-off)
13. [Uninstalling](#-uninstalling)
14. [Troubleshooting](#-troubleshooting)
15. [FAQ](#-faq)
16. [Configuration reference](#-configuration-reference)
17. [Project layout & contributing](#-project-layout--contributing)
18. [Credits & license](#-credits--license)

---

## ✨ What is Nebula?

Nebula turns Termux into a friendlier terminal. It is a zsh/bash shell UI plus a set of helper commands:

- **Ask an AI** and get answers rendered with real **bold, italics, headings, lists, tables and code boxes**, not a wall of asterisks.
- **Install anything the right way.** `nebula install firebase-tools` knows that's an npm package, installs Node first if needed, shows live progress, repairs common failures and falls back to another method.
- **Live dashboards** for crypto, news and sports, drawn with charts you can read on a phone.
- **A terminal that helps as you type**: ghost-text suggestions (`cd` suggests your most-visited folder) and a **Tab picker** (our own fuzzy finder, no fzf).
- **`nebula play summer`** searches your *whole phone* for the song, tolerates typos, and plays it.
- **It knows your phone.** Nebula checks your CPU (e.g. `armv7l`), memory, Android version and whether Termux:API works, hides features your device can't run, and tells you how to fix each one.

## 📋 Requirements

| | |
| :-- | :-- |
| **App** | [Termux](https://github.com/termux/termux-app/releases) from **F-Droid** or **GitHub** (recommended) |
| **Android** | 7.0 or newer |
| **Space** | ~15 MB for Nebula, plus whatever packages you pick |
| **Needed to install** | `curl` and `tar` (already in Termux) |
| **Nice to have** | `zsh`, `git`, `gawk`, `jq`, `tgpt` (the installer offers these), the **Termux:API** app for battery / notifications / fingerprint |

> **Tip:** Termux and Termux:API must come from the **same source** (both F-Droid, or both GitHub). See [Termux:API without the Play Store](#termuxapi-without-the-play-store).

## 🚀 Installation

Pick **one** method.

### Method 0: `pkg install nebula` (once the repository is set up)

```bash
curl -fsSL https://raw.githubusercontent.com/jitetee/nebula/main/install/add-repo.sh | bash
pkg install nebula
nebula setup
```

`pkg upgrade nebula` keeps it updated afterwards. Maintainers: see [docs/PACKAGING.md](docs/PACKAGING.md).

### Method 1: one-liner

```bash
curl -fsSL https://raw.githubusercontent.com/jitetee/nebula/main/install/install.sh | bash
```

### Method 2: git clone

```bash
pkg install git -y
git clone https://github.com/jitetee/nebula.git
cd nebula
bash install/install.sh
```

### Method 3: ZIP download

1. Download the ZIP from the repo page (**Code → Download ZIP**).
2. Extract it in Termux (`pkg install unzip` if needed), `cd` into the folder.
3. `bash install/install.sh`

### What the installer does

| Step | Detail |
| :-- | :-- |
| **1. Pick packages** | An arrow-key menu: **↑/↓** move, **Enter** select/unselect, **b** basic set, **a** all, **n** none, **q** skip. *Nothing is installed without your OK.* Packages with no build for your CPU are greyed out. |
| **2. Install Nebula** | Copies the app to `$PREFIX/opt/nebula` and **locks the folder to your user** (`chmod 700`). |
| **3. Termux look** | Optional font, colors and extra keys. The files stay in `opt`; `~/.termux` only gets small **links** (Termux requires that path). Your originals are saved in `data/backups`. |
| **4. zsh hook** | Appends a managed block to `~/.zshrc` (never overwrites it) and starts zsh from `.bashrc` **only if zsh is installed**. |
| **5. Command** | Links `nebula` into `$PREFIX/bin`. |
| **6. Tidy up** | Offers to **delete the folder you cloned/unzipped**, since Nebula now lives in `opt`. Update any time with `nebula update`. |
| **7. Device scan** | Checks your phone and tells you if anything needs attention. |

**Installer options**

```bash
bash install/install.sh --basic        # install the Basic package set, no questions
bash install/install.sh --skip-deps    # install Nebula only
bash install/install.sh --deps-only    # just open the package picker
NEBULA_KEEP_SOURCE=1 bash install/install.sh   # don't offer to delete the download
```

Restart Termux (or run `exec zsh`) afterwards.

## 🧭 First run

1. Open Termux. On first launch Nebula asks you to **create a username and password** (stored on your phone only, as a SHA-256 hash, never as plain text).
2. A short **tour** is offered (replay any time with `tour`).
3. Run **`settings`** if Nebula reports device warnings.
4. Run **`help`** for everything, or **`help <command>`** for examples.

## 🌟 Features

### 🤖 Nebula AI (needs `tgpt`)

`ask`, `chat` (remembers the conversation), `explain`, `fix`, `summarize`, `translate`, `joke`, `fact`.
Replies are rendered as styled terminal text: headings, **bold**, *italics*, `inline code`, bullet and numbered lists, quotes, links, tables and boxed code blocks, word-wrapped to your screen.

```text
▌ Setting up Python
═══════════════════════════════════════
Use  pkg install python  and then check python --version
 • First item
 1. Update packages: pkg update
┌─ bash ─────────────────────────────
│ pkg install python
└─────────────────────────────────────
```

`fix` reads your last failed command and explains the cause; it **never runs anything for you**.

### 💬 Talk to Termux directly

Nebula never blocks you from running commands. Everything you type goes straight to Termux, and when it can't, Nebula helps instead of just failing:

```text
❯ gh auth login
  📦 gh isn't installed.  Package: gh — GitHub CLI
  Install it now and run your command? [Y/n]        ← installs, then runs `gh auth login`

❯ show me the biggest files here                    ← a sentence, not a command
  Let Nebula AI turn it into commands? [Y/n]
  1 ▸ du -ah . | sort -rh | head -5
  Run it?  [Y]es · [n]o · [s]tep by step · [e]dit
```

- **Missing tool?** Nebula looks it up (its own 130+ tool database, then Termux's package index) and offers to install it. Typos still get "did you mean…?".
- **Plain English** becomes a *plan you approve*. Nothing runs without your OK; `[e]dit` lets you change each command first; the commands run **in your own shell**, so `cd` and `export` stick.
- **Risky commands** (`rm -r`, `dd`, `sudo`, `curl … | sh`, `git push --force`, `chmod -R` …) are marked ⚠ and need you to type `yes`.
- `tell <request>` does it on purpose. **`english auto`** runs only read-only plans (`ls`, `du`, `git status`…) immediately; `english off` turns it off. Also in `settings → Features`.
- In the **nebula shell**: `!command` sends a line to Termux exactly as typed, `?request` is plain English. Names that are also real commands (`install -m 755 …`, `date +%s`, `time ls`, `ip a`) go to the real command automatically.

### 📦 `nebula install`: the smart installer

```bash
nebula install python            # pkg
nebula install firebase-tools    # npm (installs Node first if needed)
nebula install cmatrix           # pkg
nebula install                   # fuzzy-pick from the list
nebula install list              # browse 130+ tools by category
nebula install search video
nebula install info yt-dlp       # how it would be installed
nebula install yt-dlp -v         # show raw terminal output live
nebula install yt-dlp --via pip  # force a method
nebula install log               # show the last log
nebula uninstall cmatrix
```

- **Picks the best method** (pkg first because it's prebuilt for your CPU; pip / npm / cargo / go / gem when that's the right home).
- **Installs prerequisites** (Node for npm tools, Python for pip tools).
- **Live progress**: spinner, a progress bar when the tool reports a percentage, elapsed time and the latest output line.
- **Self-healing**: refreshes stale package lists, repairs interrupted dpkg, retries pip with `--break-system-packages` when Python is "externally managed", installs build tools when a native build fails.
- **Falls back** to the next method if one fails, then shows the log tail and exact next steps.
- **Unknown names** are searched on pkg, pip and npm.

### 📈 Dashboards (need `curl`, `jq`)

| Command | What you get |
| :-- | :-- |
| `crypto` | Top 10 coins: price, 24h change, 7-day sparkline, market-cap share bars |
| `crypto btc --days 90 --kes` | Detail card with an area chart, 24h range bar, volume, all-time high. Currencies: `--usd --eur --gbp --kes --ngn --zar --inr --jpy` |
| `news` / `news tech` / `news africa` | Headline cards with freshness colours and **trending words** bars. Topics: `world africa tech business science health sport hn`, or `--feed <rss-url>` |
| `news 3` · `news open 3` · `news ai 3` | Story details · open the link · Nebula AI explains it |
| `sports` | Asks which league, then shows matches |
| `sports epl` · `sports football match today` | Live / upcoming / finished match cards |
| `sports epl table` · `sports nba next` | League table with points bars · tomorrow's games |
| `weather [city]` | Forecast with hourly charts |

Sports leagues: `epl laliga bundesliga seriea ligue1 ucl uel cafcl afcon worldcup mls nba wnba nfl nhl mlb f1 atp wta`.
Data comes from free public sources (CoinGecko, BBC / Hacker News RSS, ESPN scoreboards). They can rate-limit or change; Nebula shows a clear message instead of failing.

### 🎵 `nebula play`

```bash
nebula play summer            # finds it anywhere on the phone
nebula play sumer vibs        # typos are fine
nebula play                   # fuzzy-pick from your whole library
nebula play summer --all      # queue every match
nebula play --shuffle         # random mix
nebula play --bg summer       # play in the background
nebula play stop
nebula play --reindex         # rescan after adding music
```

Searches internal storage, SD cards, `Music`, `Download` and more (ignores `Android/`, voice notes and tiny ringtones). If several songs match closely you get a picker.
**No player?** Nebula tells you what to install: **lightweight** `mpg123` (MP3 only) or `sox`; **full power** `mpv` (everything). It also tells you when your player can't handle a format (e.g. FLAC with an MP3-only player).

### ⌨️ A terminal that helps as you type

- **Ghost suggestions on every keystroke** (accept with **→**):
  - `cd ` → your **most-visited folder**
  - `cd th` → `thesis` (a folder here, or a frequently used one anywhere, with its path as a hint)
  - `nebula ins` → `install`, `nebula install fire` → `firebase-tools`
  - everything else: history, then command names
- **Tab opens Nebula's own fuzzy picker** and understands context: commands, folders for `cd`, tool names for `install`, songs for `play`, leagues for `sports`, files everywhere else. If there's only one possible completion, it completes without opening anything.
- Written from scratch: **no fzf required**, nothing to install.

### 🎨 Make it yours: prompt studio, home screen, profiles

```bash
theme studio                 # design your prompt with a live preview
theme forest                 # or pick a preset: nebula compact minimal forest sky hacker classic zen
theme set accent magenta     # quick colour change
theme export                 # share code (NEBT1:…) to give to friends
home edit                    # choose and reorder your startup widgets
home preset dashboard        # presets: classic minimal dashboard focus newsroom info clean
profile use work             # switch voice, lock timer, prompt and home screen at once
profile save mine            # snapshot your current setup
```

- **Prompt studio:** 8 segments (time, user, host, path, git, venv, jobs, battery), left and right sides, path styles, separators, prompt character, colours, one- or two-line layout. Changes show in your **open shell** at the next prompt, with no restart.
- **Home screen:** after login the screen clears and shows what you picked: logo, greeting, CPU/RAM bars, storage bars, battery, network, to-do (with priorities), reminders, weather, crypto watchlist, headlines, match scores, a tip, a trend chart. Weather/crypto/news/sports are **cached and refreshed in the background**, so login never waits for the internet.
- **Profiles:** `default`, `work` (quiet, locks sooner), `chill`, `minimal`, `saver` (lightest). Make your own and share them with a code. Imports only accept known settings, never commands.

### 📊 Status dashboard

`status` draws bars and charts for **CPU** (overall and per core), **memory and swap**, **every storage mount**, **battery**, **network** (with speeds), **temperatures**, **top processes** and a **trend history**. `status --live` refreshes continuously (press `q` to quit); `status cpu mem disk` shows only what you pick. Anything Android doesn't let Termux read is skipped.

### 🔐 Security

3 wrong passwords **close the whole Termux session**. `passwd`, `lock`, idle `autolock`, `logins` history (failed attempts are reported at your next login), optional `fingerprint` unlock, a **locked app folder**, and encrypted backups. See [Security](#-security).

### 📱 Device-aware

`settings` scans your phone and explains what's wrong with one-key fixes. Commands your device can't run are **hidden** instead of failing. See [Settings](#-settings-device-checks-and-the-termuxapi-guide).

### More

`status` (battery / RAM / storage / Wi-Fi with 20-cell bars) · `remind 10m call mom` · `todo` with priorities · `notes search` · `serve` (share a folder over Wi-Fi with a QR code) · `backup` / `restore` · `theme builder` · `tour` · `doctor --fix`.

## 📖 Command reference

Run `help` for the live list (it hides commands your device can't run; `help --all` shows everything). Inside plain zsh, type Nebula commands directly (`status`, `backup`…); when a name clashes with a system command (`install`, `play`, `passwd`) use the `nebula` prefix: `nebula install python`.

| Category | Commands |
| :-- | :-- |
| **AI** | `ask` `chat` `tell` `english` `explain` `fix` `summarize` `translate` `joke` `fact` |
| **Info** | `weather` `crypto` `news` `sports` `ip` `define` `bible` `meme` |
| **Tools** | `status` `remind` `timer` `note` `notes` `todo` `calc` `qr` `serve` |
| **System** | `status` `install` `uninstall` `deps` `update` `setup` `settings` `device` `scan` `doctor` `sysinfo` |
| **Media** | `play` |
| **Security** | `passwd` `lock` `autolock` `fingerprint` `logins` `noauth` `reset-auth` `whoami` |
| **Data** | `backup` `restore` |
| **Look** | `theme` `prompt` `home` `profile` `banner` `voice` `sounds` |

`help <command>` shows usage and examples; `help search <word>` finds a command.

## ⌨ Keyboard shortcuts

| Key | Action |
| :-- | :-- |
| **→** / **Ctrl-F** / **End** | Accept the ghost suggestion |
| **Alt-F** | Accept one word of it |
| **Tab** | Context-aware fuzzy picker |
| **Shift-Tab** | Normal zsh completion |
| **Ctrl-R** | Search history |
| **Ctrl-T** | Pick a file and insert it |
| **Alt-C** | Pick a folder and `cd` into it |

**Inside the picker:** type to filter (every word must match) · **↑/↓** or **Ctrl-P/N** move · **PgUp/PgDn** · **Enter** or **Tab** select · **Esc** cancel · **Ctrl-U** clear · **Ctrl-W** delete word.

## 📱 Settings, device checks and the Termux:API guide

```text
nebula settings
```

| Page | What it does |
| :-- | :-- |
| **📱 Device** | Model, Android, CPU (e.g. `armv7l 32-bit`), memory, free storage, Termux version and install source, Termux:API status |
| **🩺 Health** | Every problem found, why it matters, and a **Run fix** button |
| **🔧 Features** | Voice, UI sounds, compact startup, tour. Unavailable features are greyed with the reason |
| **🔐 Security** | Login lock, auto-lock, fingerprint, change password, login history |
| **📦 Install missing** | One picker with everything the scan says is missing, pre-selected |
| **📖 Get Termux:API** | The guide below |

What Nebula adapts to:

- **32-bit / low-RAM phones:** compact startup turns on automatically (just the logo); packages with no build for your CPU are greyed out in the picker.
- **No Termux:API:** battery and fingerprint are hidden, reminders appear in the terminal at your next prompt (and speak with `espeak`) instead of as phone notifications.
- **No tgpt / jq / curl / python / qrencode / espeak / sox / storage permission:** the commands that need them are hidden and Settings offers the fix.
- **Android battery optimization** can't be detected from inside Termux, so Health always shows the tip: *Settings → Apps → Termux → Battery → Unrestricted*, and `termux-wake-lock`.

### Termux:API without the Play Store

Termux:API is **two pieces**: the `termux-api` package **and** the separate **Termux:API Android app**.

1. **Match the source of Termux.** F-Droid Termux → F-Droid Termux:API. GitHub → GitHub. Mixing sources fails because Android signs them differently. (`nebula device` shows where your Termux came from.)
2. **Get the APK:** [F-Droid](https://f-droid.org/packages/com.termux.api) or [GitHub releases](https://github.com/termux/termux-api/releases) (choose `arm64-v8a` for 64-bit phones, `armeabi-v7a` for `armv7l`, or the universal APK).
3. **Phone blocks APK installs** (school/work profile, parental controls, some carrier locks)?
   - *Settings → Apps → Special access → Install unknown apps* → allow your browser/file manager once. If it's missing or greyed out, a policy manages the phone.
   - **ADB from a computer** (Developer options → USB debugging): `adb install termux-api.apk`.
   - **No computer (Android 11+):** enable *Wireless debugging*, `pkg install android-tools`, and use `adb` against your own phone.
4. In Termux: `pkg install termux-api`, open the **Termux:API** app once, grant permissions, then **Settings → Re-scan**.
5. Can't do any of it? **No-API mode** keeps Nebula working (see above).

## 🗂 Where everything is stored

Everything lives in **one** place, outside your home folder:

```text
$PREFIX/opt/nebula/                     (/data/data/com.termux/files/usr/opt/nebula)
├── bin/ lib/ zsh/ motd/ assets/ install/   ← the app
└── data/                                   ← YOUR data (kept on update/uninstall)
    ├── auth, auth.log                      login hash, login history
    ├── notes.md, todo.md, reminders        your content
    ├── chats/  logs/  backups/             AI chats, install logs, app/original-file backups
    ├── prompt.conf, home.conf, profiles/   prompt, home screen, saved profiles
    ├── banner.txt                          your custom logo (survives updates)
    ├── cache/                              home-screen weather/crypto/news/sports
    ├── device.conf, hidden.txt             device scan
    └── .nsh_z, .zsh_history, music.idx     folder frecency, history, music index
```

A few things **must** remain in your home because Termux and your shell read them there:

| File | Why | What's in it |
| :-- | :-- | :-- |
| `~/.zshrc` | zsh reads it | A short block marked `# nebula-BEGIN … # nebula-END` |
| `~/.bashrc` | starts zsh | 3 lines, only if zsh exists |
| `~/.termux/*.properties`, `font.ttf` | Termux reads them | **Links** to files in `opt/nebula/assets` |
| `$PREFIX/bin/nebula` | the command | A link |

If any of these is deleted, you only lose the hook, never your data.

## 🔒 Security

- **Locked folder:** the app and data are `chmod 700`, readable only by your Termux user. Other Android apps can't read Termux's private storage anyway.
- **Login lock:** 3 wrong attempts at login, `lock`, `passwd` or any password confirmation **terminate the Termux session** (the session leader and everything under it). Failed attempts are logged (`logins`) and reported on your next successful login.
- **Idle auto-lock:** default 10 minutes (`autolock 5`, `autolock off`).
- **Fingerprint (optional):** `fingerprint on` (needs Termux:API). The password always works as a fallback.
- **Sensitive actions re-ask your password:** `noauth on`, `reset-auth`, `passwd`, enabling fingerprint.
- **Backups can be encrypted** (AES-256, PBKDF2) with `backup --encrypt`. Restores only accept archives containing Nebula's own files.
- **Updates** download from GitHub over HTTPS, are validated before use, and your previous version is saved for `--rollback`.
- **AI never executes anything on its own.**

> **Be realistic:** this is a *local convenience lock*. Anyone with unrestricted access to your unlocked Termux can bypass a shell-level lock. Nebula's code is plain shell script, and the MIT license lets anyone reuse it. Use your phone's screen lock for real protection.

## 🔄 Updating

```bash
nebula update              # check, show what's new, install
nebula update --check      # only check
nebula update --force      # reinstall the latest
nebula update --rollback   # return to the version before the last update
nebula update --branch dev # try another branch
```

- No git needed. Nebula downloads the latest release from `github.com/jitetee/nebula`, validates it, **keeps your `data/` untouched**, saves the old version, installs, and **deletes its temp files**.
- Once a day Nebula quietly checks and shows `⬆ Nebula X is available` (turn off with `export NEBULA_NO_UPDATE_CHECK=1`).
- Using a fork or private repo?

```bash
export NEBULA_REPO=https://github.com/<you>/<repo>
export NEBULA_TOKEN=<GitHub token with read access>   # private repos only
```

## 🔇 Turning things off

| I want to… | Do this |
| :-- | :-- |
| **Mute the voice** | `nebula voice off` (back on: `voice on`) · or `settings → Features` · or start muted with `nebula --no-voice` · or `export NEBULA_VOICE=0` |
| **Turn off UI sounds** | `nebula sounds off` · or `settings → Features` · `export NEBULA_SOUNDS=0` |
| **Skip the login screen** | `noauth on` (asks for your password) · back: `noauth off` |
| **Stop auto-lock** | `autolock off` |
| **Disable fingerprint** | `fingerprint off` |
| **Lighter / shorter startup** | `settings → Features → Compact startup` |
| **Hide the startup banner** | `export NSH_SKIP_MOTD=1` in `~/.zshrc.local` (or use Compact startup for just the logo) |
| **Stop update notices** | `export NEBULA_NO_UPDATE_CHECK=1` |
| **Plain AI text (no styling)** | `export NEBULA_PLAIN_AI=1` |
| **Turn off the Tab picker** | `export NSH_SKIP_PICK=1` (ghost suggestions stay) |
| **Hide the startup screen** | `home off` (back: `home on`) |
| **Change what it shows** | `home edit` · `home preset minimal` |
| **Plain prompt** | `theme minimal` or `theme reset` |
| **Replay / skip the tour** | `settings → Features → Show tour next start` |

Put exports in `~/.zshrc.local` (Nebula's block never touches it).

## 🗑 Uninstalling

```bash
bash $PREFIX/opt/nebula/install/uninstall.sh              # keeps your data/ folder
bash $PREFIX/opt/nebula/install/uninstall.sh --purge-config   # removes data too
```

Removes the command, the `~/.zshrc` block, the zsh auto-start and the links in `~/.termux`, and **restores your original font/colors/keys**. Installed packages (zsh, git, tgpt…) are left alone.

## 🛠 Troubleshooting

Start with:

```bash
nebula doctor        # health check, add --fix to open the package picker
nebula settings      # device-specific problems with one-key fixes
nebula device        # plain-text device report
nebula install log   # the last install log
```

| Problem | Cause → Fix |
| :-- | :-- |
| `nebula: command not found` | The link in `$PREFIX/bin` is missing. Run `ln -sf $PREFIX/opt/nebula/bin/nebula $PREFIX/bin/nebula`, or re-run the installer. |
| Nebula doesn't start with Termux | zsh isn't installed (`pkg install zsh`) or the `.zshrc` block was removed. Re-run the installer; it re-adds it. |
| Login screen asks me to **create** an account again | The login file wasn't found. If you used the old cvui: `sed -i 's/^cvui_/NEBULA_/' $PREFIX/opt/nebula/data/auth`. Otherwise `restore` a backup. |
| **Forgot my password** | `nebula --reset-auth` (from a shell that isn't locked), then create a new one. Or restore a backup. |
| The session **closed on its own** | 3 wrong passwords. That's by design; see `logins` after you log back in. |
| Locked out and the session keeps closing | Open Termux and quickly run `nebula --reset-auth`, or start a plain shell with `bash --norc` and run it. |
| Battery / fingerprint / notifications missing | Termux:API isn't set up. `settings → Get Termux:API`. |
| `Termux:API app not responding` | The app isn't installed, comes from a different source than Termux, or lacks permission. See [the guide](#termuxapi-without-the-play-store). |
| Reminders don't fire when the phone sleeps | Android is killing Termux. *Settings → Apps → Termux → Battery → Unrestricted*, and run `termux-wake-lock`. |
| `backup` says shared storage isn't accessible | Run `termux-setup-storage` and allow the permission. |
| A command says "not found" and Nebula didn't offer to install it | Nebula only offers when it knows a package for that name. Try `nebula install <name>`, `pkg search <name>`, or `pkg install <package>`. Typing `!command` in the nebula shell always sends it as-is. |
| Typing a sentence just gives a zsh error | Plain-English mode is off or tgpt is missing: `english ask`, `nebula install tgpt`. |
| `ask` / `chat` say they're unavailable | Install tgpt: `nebula install tgpt`. Check your internet. |
| AI output shows `**` asterisks | You're piping it or `NEBULA_PLAIN_AI=1`. Run in the terminal, unset the variable. |
| `crypto` / `sports` say "needs jq" | `nebula install jq` |
| `crypto` says rate-limited | CoinGecko's free tier. Wait a minute and retry. |
| `sports` shows "No matches" | No games on that date. Try `sports <league> next`, `yesterday`, or `table`. |
| `play` can't find a song | `nebula play --reindex`. Make sure storage permission is granted. Files under 120 KB and the `Android/` folder are ignored. |
| `play` says no player | `nebula install mpg123` (light, MP3 only), `sox`, or `mpv` (everything). |
| `install` fails | `nebula install <tool> -v` for live output, `nebula install log` for the log. Try `pkg update`, `termux-change-repo`, free storage. |
| `pip` says *externally-managed-environment* | Nebula retries with `--break-system-packages` automatically. |
| `npm` / `node-gyp` build errors | Nebula installs `python make clang binutils` and retries. |
| Tab doesn't open the picker | `export NSH_SKIP_PICK=1` may be set, or you're not in zsh. Check `echo $SHELL`. |
| Suggestions look wrong / stale | `rm $PREFIX/opt/nebula/data/.nsh_z` resets folder history. |
| Fonts/icons look broken | Restart Termux. If still broken: re-run the installer's Termux look step or uninstall to restore your own font. |
| `nebula update` can't read the version | Offline, wrong repo, or private repo without `NEBULA_TOKEN`. |
| An update broke something | `nebula update --rollback` |
| Lines of `���` instead of `─────` | Fixed in 0.9.0 (Termux's `tr` is byte-based). Update, then restart Termux. |
| `awk: … Invalid collation character` / AI shows nothing | Fixed in 0.9.0 (your `awk` is a UTF-8 gawk). Update; AI output also falls back to plain text now. |
| After login I only see the logo, no bars | Old compact mode. Run `settings → Features → Compact startup` (off) or `home preset classic`. |
| I want a different startup screen | `home edit` or `home preset dashboard`; hide it entirely with `home off`. |
| My prompt looks wrong | `theme reset`, or pick a preset: `theme compact` is best for narrow screens. |
| `profile use` asks for my password | The profile turns the login lock off; Nebula confirms first. |
| Banner too wide on my phone | Lower the Termux font size (pinch to zoom out) or use `settings → Compact startup`. |
| Everything is slow | Turn on Compact startup, `autolock off`, and avoid heavy packages (`ffmpeg`, `proot-distro`) on low-RAM devices. |

**Still stuck?** Open an issue at <https://github.com/jitetee/nebula/issues> and include the output of `nebula --version`, `nebula device` and `nebula doctor`.

## ❓ FAQ

**Does Nebula work offline?** The shell, settings, todo, notes, `play`, `status` and `backup` do. AI, weather, crypto, news, sports and installs need internet.

**Does it send my data anywhere?** Only the requests you trigger go out (e.g. `ask` sends your question through `tgpt`; `crypto` calls CoinGecko). Your login hash, notes and files stay on the phone.

**Why `opt` and not my home folder?** Home is easy to wipe by accident. Nebula keeps everything in `$PREFIX/opt/nebula` and leaves only the few files Termux itself requires in `~`.

**What survives a Termux reinstall?** `$PREFIX` is wiped by a bootstrap reinstall, so use `backup --encrypt` regularly. It saves to `/sdcard/Nebula`, which survives.

**Can I use bash instead of zsh?** The shell UI (suggestions, Tab picker) is zsh. The `nebula` command itself runs on bash and works from any shell.

**Is `fzf` needed?** No. The picker is built into Nebula.

**Can I add my own tools to `nebula install`?** Yes: add a line to `assets/registry.txt` (see below).

**Why is a command missing from `help`?** Your device can't run it. `help --all` shows everything and `settings` shows the fix.

## ⚙ Configuration reference

Environment variables (put them in `~/.zshrc.local`):

| Variable | Effect |
| :-- | :-- |
| `NEBULA_REPO` | Update/install source (default `https://github.com/jitetee/nebula`) |
| `NEBULA_TOKEN` | GitHub token for a private repo |
| `NEBULA_BRANCH` | Branch for the one-liner installer |
| `NEBULA_NO_UPDATE_CHECK=1` | Disable the daily update hint |
| `NEBULA_VOICE=0` / `NEBULA_SOUNDS=0` | Mute voice / UI sounds |
| `NEBULA_PLAIN_AI=1` | Don't style AI output |
| `NEBULA_BACKUP_DIR` | Where `backup` saves (default `/sdcard/Nebula`) |
| `NEBULA_MUSIC_DIRS` | Extra folders for `play` to search |
| `NEBULA_YES=1` | Auto-confirm prompts (automation) |
| `NEBULA_KEEP_SOURCE=1` | Installer: don't offer to delete the download |
| `NSH_SKIP_PICK=1` | Disable the Tab picker |
| `NSH_SKIP_AUTH=1` | Skip the login hook for this shell |

## 🧱 Project layout & contributing

```text
bin/nebula            entry point (REPL + one-shot commands)
lib/                  commands, ai.sh, md.awk (markdown renderer), viz.sh (charts),
                      data.sh (crypto/news/sports), pkgmgr.sh (install), play.sh,
                      pick.sh (fuzzy picker), device.sh + settings.sh, auth.sh, update.sh …
zsh/                  nsh.zsh and plugins (autosuggestions, nebula-pick, z, syntax-highlighting)
assets/               help.txt (command registry), registry.txt (install DB),
                      leagues.txt (sports), banner, fonts, Termux colors/keys
install/              install.sh, uninstall.sh, packages.list
docs/                 CHANGELOG.md, ARCHITECTURE.md
VERSION               current version (read by `nebula update`)
```

- **Add a tool to `nebula install`:** one line in `assets/registry.txt`:
  `name|aliases|method:target;method:target|Category|Description` (first method is preferred; join packages with `+`).
- **Add a league:** one line in `assets/leagues.txt` (`key|Name|sport|espn/path|aliases`).
- **Add a command:** define `cmd::yourcommand` in `lib/`, add a block to `assets/help.txt`. Help, completion and "did you mean" pick it up automatically.
- Check scripts with `bash -n` (and `zsh -n` for `zsh/`), keep the **UTF-8** and **phone-width (≈45 columns)** layout in mind.
- **Releasing:** bump `VERSION`, add a section to `docs/CHANGELOG.md`, push to `main`. `nebula update` reads both.

## 🙏 Credits & license

Nebula is based on **cvui** by cybervaultke (MIT). Thanks to the Termux team, CoinGecko, the BBC and Hacker News feeds, and ESPN's public scoreboards for the data sources.

Released under the [MIT License](LICENSE).

<div align="center">

**Made for people who live in the terminal on their phone.** ⚡

</div>
