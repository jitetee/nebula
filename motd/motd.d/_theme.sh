#!/data/data/com.termux/files/usr/bin/env bash
# Shared theme palette for nebula motd scripts. Sourced (not executed)
# by 10-nebula-logo / 20-sysinfo / 35-diskspace so the banner subtitle,
# label colors, and disk-bar tones all stay in sync with $PREFIX/opt/nebula/data/theme.
#
# Themes:
#   nebula     (default)  sky-blue / cyan
#   forest              dark green
#   sky                 sky-blue
#   minimal             monochrome grey (everything dim/grey)
#
# Exports: T_PRIMARY, T_SECONDARY, T_ACCENT, T_OK, T_WARN, T_BAD,
#          T_LABEL, T_VALUE, T_DIM, T_BOLD, T_RESET

_t="nebula"
[[ -r "$NEBULA_CFG/theme" ]] && _t=$(<"$NEBULA_CFG/theme")

case "$_t" in
  forest)
    T_PRIMARY=$'\e[38;5;34m'    # bright green
    T_SECONDARY=$'\e[38;5;28m'  # dark green
    T_ACCENT=$'\e[38;5;220m'    # gold
    T_OK=$'\e[38;5;34m'         # numeric values follow theme
    ;;
  sky)
    T_PRIMARY=$'\e[38;5;117m'   # sky blue
    T_SECONDARY=$'\e[38;5;111m' # softer blue
    T_ACCENT=$'\e[38;5;223m'    # warm cream
    T_OK=$'\e[38;5;117m'        # numeric values follow theme
    ;;
  minimal)
    T_PRIMARY=$'\e[38;5;250m'   # light grey
    T_SECONDARY=$'\e[38;5;244m' # mid grey
    T_ACCENT=$'\e[38;5;245m'    # grey accent (no pop)
    T_OK=$'\e[38;5;250m'        # numeric values stay grey too
    ;;
  *)
    # nebula (default) — cyan / blue
    T_PRIMARY=$'\e[38;5;51m'    # cyan
    T_SECONDARY=$'\e[38;5;39m'  # blue
    T_ACCENT=$'\e[38;5;215m'    # orange
    T_OK=$'\e[38;5;51m'         # numeric values follow theme
    ;;
esac

T_WARN=$'\e[38;5;214m'   # deep amber (disk-bar 75-94%)
T_BAD=$'\e[38;5;196m'    # deep red   (disk-bar >=95%)
T_LABEL=$T_PRIMARY       # field labels (Distro/Host/Kernel/...)
T_VALUE=$'\e[38;5;250m'  # neutral grey for values after the colon
T_DIM=$'\e[2m'
T_BOLD=$'\033[1m'
T_RESET=$'\033[0m'

# minimal theme: even values lean grey (already 250)
unset _t
