# UI and plugin ideas for Nebula

Everything below fits the existing building blocks: `nebula_core.tui` (mouse/touch screens), `nebula_core.devtools`
(GitHub, git, project context), the plugin system (`docs/PLUGINS.md`), and `nebula_core.ai` (one AI for everything).

## UI improvements, roughly by value
1. **Command palette everywhere.** One key (Ctrl-P) opens a fuzzy list of every command in the registry, from any GUI app and from Neovim. The registry already knows every command and its summary.
2. **Notification centre.** One place for things that finished while you were elsewhere (a download from `svn`, a deploy, a failed CI run). Apps push a line into `$NEBULA_CFG/inbox.jsonl`; the launcher shows the unread count.
3. **Home screen widgets.** The launcher gets live cards: battery and storage from Monitor, the current git branch and what `gitx advise` says, the last `svn` saves, the AI backend in use.
4. **Image and album-art previews.** Files shows pictures with `chafa` (pkg install chafa) in its details pane; Player shows cover art and lyrics.
5. **Workspaces.** `workspace save work` remembers a tmux layout (Neovim + gitx + a shell) and `workspace work` brings it back with one tap.
6. **Swipe and long-press.** Long-press on a row opens a context menu (Open with, Share, Rename, Info); swipe between Monitor tabs. The toolkit already receives the mouse events.
7. **Global search.** One box that searches files, commands, notes, git history and chat history.
8. **Clipboard history** (Termux:API) with a picker, and `svn` picks up the last copied link automatically.
9. **Auto palette by time** (`nebula palette auto`: amber at night, nebula green by day).
10. **Prompt dock.** A one-line status in the zsh prompt: branch, ahead/behind, battery, AI, running downloads.

## Developer plugins worth adding next
| Plugin | What it does | Built on |
|---|---|---|
| `ci` | GitHub Actions at a glance: last runs, which step failed, the log tail, re-run failed jobs. Would have explained the red-X emails in one screen. | `devtools.gh` |
| `pr` | Open a pull request from `gitx` with an AI-written title and description from the diff | gitx + ai |
| `release` | Tag, create a GitHub release, and generate the changelog from commits | devtools + ai |
| `db` | Browse and edit Realtime Database / Firestore data and security rules, with diffs before publishing | fire |
| `env` | Secrets manager: encrypted `.env` files, warns before they are committed | gitx |
| `api` | A small HTTP client (like Postman) with saved requests per project | tui |
| `deps` | Outdated and vulnerable packages (`npm audit`, `pip list --outdated`) with one-tap upgrade | project |
| `rollback` | Roll Firebase Hosting back to a previous release | fire |
| `host` | Same guided deploy for Cloudflare Pages, Netlify and Vercel | fire as a template |
| `ssh` | Saved servers, one-tap connect, key setup | tui |
| `todo` | Turn TODO/FIXME comments into a checklist per project | project |
| `snip` | Snippet and command-notes manager with search and AI explain | tui + ai |
| `cron` | Friendly manager for Termux scheduled jobs | tui |
| `backup` | One-tap backup of a project or `~/storage` folder to a zip or to Google Drive | files |

## How to start one
`nebula plugin new ci` scaffolds the folder; then copy `plugins/repo/` as a pattern for a full-screen app.
`nebula check` tells you what is still missing (help entry, `--help`, consistency).
