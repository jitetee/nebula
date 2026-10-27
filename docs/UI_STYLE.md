# The Nebula look

Everything in the terminal codebase uses the same style as jtlearn: phosphor-green palette, rounded titled panels,
a double-frame block-letter banner, two-column menus and a `└─➤ Your choice:` prompt.

Bash (Nebula, games, Mingle) calls `lib/skin.sh`, which runs `lib/skin.py` (Python standard library only):

| Helper | Use |
|---|---|
| `skin::box "Title"` | stdin lines -> rounded panel |
| `skin::menu "Title" [--nodot]` | stdin `key<TAB>icon<TAB>label<TAB>description` -> menu panel |
| `skin::table "Title"` | stdin TSV, first line = header |
| `skin::kv "Title"` | stdin `key<TAB>value` |
| `skin::banner NAME "tag"...` | big letters in a double frame |
| `skin::bubble [--right] name [time]` | chat bubble |
| `skin::prompt "Your choice"` | the prompt |
| `skin::bar PCT`, `skin::spin`, `skin::load` | progress, spinner, loading bar |

Arrow-key menus (`lib/menu.sh`) draw the same frame. ant has its own Python equivalents in `apps/ant/ant/ui.py`; jtlearn in `apps/jtlearn/jtlearn/ui.py`.
Panels measure emoji and wide characters, shrink to the terminal, and become plain rules under 40 columns. `NO_COLOR=1` or `NEBULA_PLAIN=1` turns colours and boxes off.
