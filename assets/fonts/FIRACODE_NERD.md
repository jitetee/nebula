# Fonts

`nebula.ttf` is **Nebula Mono**: FiraCode Nerd Font Mono plus Nebula's own icons, built by
`tools/make-font.py` (see the top of that file). The installer links it as Termux's font.

| Glyph | Code | Use |
|---|---|---|
| logo | U+E400 | Nebula mark (statusline, start screen) |
| bolt | U+E401 | speed / AI |
| sparkle | U+E402 | Copilot / suggestions |
| prompt | U+E403 | prompts |
| face | U+E404 | the friendly face |
| planet | U+E405 | space theme |

All Nerd Font icons (lsd, git, etc.) and FiraCode's ligatures are still in it. Rebuild with your own icons:

```bash
curl -fsSLO https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FiraCode.zip
unzip FiraCode.zip FiraCodeNerdFontMono-Regular.ttf
pip install fonttools
python3 tools/make-font.py --base FiraCodeNerdFontMono-Regular.ttf
```

Without this font Nebula still works: the banner uses plain box-drawing and `NEBULA_ICONS=plain` swaps icons for symbols any font has.
