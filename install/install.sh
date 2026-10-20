#!/data/data/com.termux/files/usr/bin/env bash
# Nebula installer
#
# Usage:
#   bash install.sh              interactive (pick dependencies in a menu)
#   bash install.sh --basic      install the Basic set without asking
#   bash install.sh --skip-deps  install Nebula only, no packages
#   bash install.sh --deps-only  just open the dependency menu (no file copy)
#   bash install.sh --deps-only --want a,b   ...with those packages pre-selected
#   bash install.sh --update     used by `nebula update` (copy files, keep data, no menus)
#   NEBULA_KEEP_SOURCE=1         keep the download folder after installing
#   bash install.sh --help
#
# Everything Nebula owns lives in ONE place, outside $HOME:
#   $PREFIX/opt/nebula          app
#   $PREFIX/opt/nebula/data     credentials, notes, theme (kept on upgrade)
# (Termux itself still reads font/colors from ~/.termux and the zsh hook
#  from ~/.zshrc — those stay in $HOME because Termux requires it.)
set -u
umask 077     # everything Nebula creates is private to your Termux user

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)"
INSTALL_DIR="${NEBULA_INSTALL_DIR:-${NEBULA_HOME:-$PREFIX/opt/nebula}}"
DATA_DIR="$INSTALL_DIR/data"
BIN_LINK="$PREFIX/bin/nebula"
TERMUX_DIR="${TERMUX_DIR:-$HOME/.termux}"
REPO="${NEBULA_REPO:-https://github.com/jitetee/nebula}"
BOOTSTRAPPED="${NEBULA_BOOTSTRAPPED:-0}"

NEBULA_SKIP_FONT="${NEBULA_SKIP_FONT:-0}"
NEBULA_SKIP_COLORS="${NEBULA_SKIP_COLORS:-0}"
NEBULA_SKIP_KEYS="${NEBULA_SKIP_KEYS:-0}"
NEBULA_SKIP_NSH="${NEBULA_SKIP_NSH:-0}"
NEBULA_SKIP_MOTD="${NEBULA_SKIP_MOTD:-0}"
NEBULA_UPDATE_MODE="${NEBULA_UPDATE_MODE:-0}"

ORIG_ARGS=("$@")
DEPS_MODE=ask        # ask | basic | skip
DEPS_ONLY=0
WANT=""
while (( $# )); do
  case "$1" in
    --basic|-y|--yes) DEPS_MODE=basic ;;
    --skip-deps)      DEPS_MODE=skip ;;
    --deps-only)      DEPS_ONLY=1 ;;
    --update)         NEBULA_UPDATE_MODE=1; DEPS_MODE=skip ;;
    --keep-source)    NEBULA_KEEP_SOURCE=1 ;;
    --want)           WANT=${2:-}; shift ;;
    --want=*)         WANT=${1#--want=} ;;
    -h|--help)        sed -n '2,16p' "${BASH_SOURCE[0]}"; exit 0 ;;
  esac
  shift
done

say()  { printf "\033[38;5;120m✔\033[0m %s\n" "$*"; }
warn() { printf "\033[38;5;221m⚠\033[0m %s\n" "$*"; }
err()  { printf "\033[38;5;203m✖\033[0m %s\n" "$*" >&2; }
info() { printf "\033[38;5;75mℹ\033[0m %s\n" "$*"; }
hr()   { printf '\033[2m%s\033[0m\n' "────────────────────────────────────"; }
need_cmd() { command -v "$1" >/dev/null 2>&1; }

HAS_TTY=0
if [[ -r /dev/tty ]] && { : </dev/tty; } 2>/dev/null; then HAS_TTY=1; fi

ask_yn() {  # ask_yn "question" default(Y|N)  → 0 yes / 1 no
  local q=$1 def=${2:-Y} ans hint="[Y/n]"
  [[ $def == N ]] && hint="[y/N]"
  (( HAS_TTY )) || { [[ $def == Y ]]; return; }
  read -r -p "$q $hint " ans </dev/tty || ans=""
  ans=${ans:-$def}
  [[ ${ans,,} == y* ]]
}

banner() {
  if [[ -r $SRC_DIR/assets/banner.txt ]]; then
    printf '\033[38;5;51m'; cat "$SRC_DIR/assets/banner.txt"; printf '\033[0m'
  else
    printf 'NEBULA\n'
  fi
  printf '                 installer\n'
}

# ═════════════════════════════════════════════════════════════════════════
#  Dependency menu
# ═════════════════════════════════════════════════════════════════════════
NAMES=(); TIERS=(); DESCS=(); SEL=(); HAVE=(); NA=()

load_packages() {
  local f=$SRC_DIR/install/packages.list n t d
  [[ -f $f ]] || f=$INSTALL_DIR/install/packages.list
  [[ -f $f ]] || return 1
  while IFS='|' read -r n t d; do
    [[ -z $n || $n == \#* ]] && continue
    NAMES+=("$n"); TIERS+=("$t"); DESCS+=("$d")
  done <"$f"
}

detect_installed() {
  local inst i
  inst=$(dpkg-query -W -f='${Package} ${db:Status-Abbrev}\n' 2>/dev/null | awk '$2=="ii"{print $1}')
  for i in "${!NAMES[@]}"; do
    if [[ -n $inst ]] && grep -qxF -- "${NAMES[i]}" <<<"$inst"; then HAVE[i]=1
    elif [[ -z $inst ]] && need_cmd "${NAMES[i]}"; then HAVE[i]=1
    else HAVE[i]=0; fi
    SEL[i]=0
  done
}

# Flag packages the repo has no build of for this CPU (e.g. 32-bit ARM).
# Only trusted when the package lists are populated.
detect_availability() {
  local i out seen=0 line p c
  for i in "${!NAMES[@]}"; do NA[i]=0; done
  need_cmd apt-cache || return 0
  out=$(apt-cache policy "${NAMES[@]}" 2>/dev/null | awk '/^[^ ]/{gsub(":","",$1); p=$1} /Candidate:/{print p, $2}')
  [[ -z $out ]] && return 0
  grep -qv '(none)$' <<<"$out" || return 0          # lists empty → don't flag anything
  for i in "${!NAMES[@]}"; do
    if grep -qx "${NAMES[i]} (none)" <<<"$out"; then NA[i]=1
    elif ! grep -q "^${NAMES[i]} " <<<"$out"; then NA[i]=1; fi
  done
}

sel_tier() {   # sel_tier <regex of tiers>
  local i
  for i in "${!NAMES[@]}"; do
    SEL[i]=0
    (( HAVE[i] || NA[i] )) && continue
    [[ ${TIERS[i]} =~ ^($1)$ ]] && SEL[i]=1
  done
}
sel_count() { local i c=0; for i in "${!NAMES[@]}"; do (( SEL[i] )) && c=$((c+1)); done; echo "$c"; }

# term_size → "rows cols" of the real terminal (stty on /dev/tty works inside $(…), unlike tput)
term_size() {
  local sz r c; sz=$(stty size </dev/tty 2>/dev/null)
  r=${sz% *}; c=${sz#* }
  [[ $r =~ ^[0-9]+$ && $r -gt 0 ]] || r=$(tput lines 2>/dev/null || echo 24)
  [[ $c =~ ^[0-9]+$ && $c -gt 0 ]] || c=$(tput cols 2>/dev/null || echo 40)
  printf '%s %s' "$r" "$c"
}

# Returns 0 = proceed to install selection, 1 = skip
deps_menu() {
  local N=${#NAMES[@]} total cur=0 top=0 H rows cols key rest drawn=0 LINES_OUT rc
  total=$((N + 2))
  read -r rows cols < <(term_size)
  H=$(( rows - 7 )); (( H > 14 )) && H=14; (( H < 5 )) && H=5; (( H > total )) && H=$total
  LINES_OUT=$(( H + 3 ))

  if [[ -n $WANT ]]; then
    sel_tier 'none'
    local w j; for w in ${WANT//,/ }; do
      for j in "${!NAMES[@]}"; do [[ ${NAMES[j]} == "$w" ]] && (( ! HAVE[j] && ! NA[j] )) && SEL[j]=1; done
    done
  else
    sel_tier 'b'          # start from the Basic set
  fi
  printf '\033[?25l'
  trap 'printf "\033[?25h"' EXIT INT TERM
  trap ':' WINCH                                   # a resize interrupts the key read → redraw

  local B=$'\033[1m' DIM=$'\033[2m' CY=$'\033[38;5;51m' GR=$'\033[38;5;120m' YL=$'\033[38;5;221m' RS=$'\033[0m'

  draw() {
    local nh nr; read -r nr cols < <(term_size)
    nh=$(( nr - 7 )); (( nh > 14 )) && nh=14; (( nh < 5 )) && nh=5; (( nh > total )) && nh=$total
    if (( drawn && nh != H )); then                # screen height changed: wipe the old block, redraw at the new size
      printf '\033[%dA\033[J' "$LINES_OUT"; drawn=0; H=$nh; LINES_OUT=$(( H + 3 ))
    fi
    (( cur < top )) && top=$cur
    (( cur >= top + H )) && top=$(( cur - H + 1 ))
    (( drawn )) && printf '\033[%dA' "$LINES_OUT"
    drawn=1
    local plain r idx color box nm
    printf '\r\033[2K%s%s%s\n' "$B$CY" "Nebula · choose dependencies" "$RS"
    plain="↑↓ move · Enter select · b basic · a all · n none · q skip"
    printf '\r\033[2K%s%s%s\n' "$DIM" "${plain:0:cols-1}" "$RS"
    for (( r=0; r<H; r++ )); do
      idx=$(( top + r ))
      if (( idx < N )); then
        nm=${NAMES[idx]}
        if   (( NA[idx] ));   then box="✖ "; color=$DIM
        elif (( HAVE[idx] )); then box="✔ "; color=$DIM
        elif (( SEL[idx]  )); then box="■ "; color=$GR
        else                       box="□ "; color=""; fi
        printf -v plain '%s %s %-15s %s' "$([[ $idx == "$cur" ]] && echo '❯' || echo ' ')" "$box" "$nm" \
          "$( if (( NA[idx] )); then echo "(no build for $(uname -m))"; elif (( HAVE[idx] )); then echo '(installed)'; else echo "${DESCS[idx]}"; fi )"
      elif (( idx == N )); then
        printf -v plain '%s ▶ Install %d selected' "$([[ $idx == "$cur" ]] && echo '❯' || echo ' ')" "$(sel_count)"
        color=$YL
      else
        printf -v plain '%s ✖ Skip — install nothing' "$([[ $idx == "$cur" ]] && echo '❯' || echo ' ')"
        color=$YL
      fi
      [[ $idx == "$cur" ]] && color=$B$CY
      printf '\r\033[2K%s%s%s\n' "$color" "${plain:0:cols-1}" "$RS"
    done
    printf -v plain '%d/%d · %d to install' "$((cur+1))" "$total" "$(sel_count)"
    printf '\r\033[2K%s%s%s\n' "$DIM" "$plain" "$RS"
  }

  local result=1
  while :; do
    draw
    IFS= read -rsn1 key </dev/tty; rc=$?
    (( rc > 128 )) && continue                     # resize
    (( rc != 0 )) && break
    if [[ $key == $'\033' ]]; then
      IFS= read -rsn2 -t 0.05 rest </dev/tty || rest=""
      key+=$rest
    fi
    case "$key" in
      $'\033[A'|$'\033OA'|k) cur=$(( (cur - 1 + total) % total )) ;;
      $'\033[B'|$'\033OB'|j) cur=$(( (cur + 1) % total )) ;;
      b) sel_tier 'b' ;;
      a) sel_tier 'b|e|h' ;;
      n) sel_tier 'none' ;;
      q|Q) result=1; break ;;
      ''|' ')
        if (( cur < N )); then
          (( HAVE[cur] || NA[cur] )) || SEL[cur]=$(( 1 - SEL[cur] ))
        elif (( cur == N )); then result=0; break
        else result=1; break; fi ;;
    esac
  done
  printf '\033[?25h'; trap - EXIT INT TERM WINCH
  echo
  return $result
}

install_selected() {
  local i list=() failed=() log="$PREFIX/tmp/nebula-install.log"
  for i in "${!NAMES[@]}"; do (( SEL[i] )) && list+=("${NAMES[i]}"); done
  if (( ${#list[@]} == 0 )); then info "Nothing selected — skipping packages."; return 0; fi
  mkdir -p "$(dirname "$log")"; : >"$log"

  info "Will install: ${list[*]}"
  ask_yn "Proceed?" Y || { warn "Skipped package install."; return 0; }

  if need_cmd pkg; then
    info "Refreshing package lists…"; pkg update -y >>"$log" 2>&1 || warn "pkg update failed (continuing)"
  fi
  local p
  for p in "${list[@]}"; do
    printf '  ⬇ %-16s' "$p"
    if { need_cmd pkg && pkg install -y "$p"; } >>"$log" 2>&1 \
       || { ! need_cmd pkg && need_cmd apt-get && apt-get install -y "$p"; } >>"$log" 2>&1; then
      printf '\033[38;5;120mok\033[0m\n'
    else
      printf '\033[38;5;203mfailed\033[0m\n'; failed+=("$p")
    fi
  done
  if (( ${#failed[@]} )); then warn "Failed: ${failed[*]}  (log: $log)"
  else say "All selected packages installed"; fi
}

run_dependencies() {
  case $DEPS_MODE in
    skip) info "Skipping dependencies (--skip-deps)"; return ;;
  esac
  load_packages || { warn "packages.list not found — skipping dependencies"; return; }
  detect_installed
  detect_availability
  case $DEPS_MODE in
    basic) sel_tier 'b'; install_selected ;;
    ask)
      if (( HAS_TTY )); then
        if deps_menu; then install_selected; else info "Dependencies skipped."; fi
      else
        info "No terminal to ask on — skipping packages."
        info "Run later:  bash $INSTALL_DIR/install/install.sh --deps-only"
      fi ;;
  esac
}

# ═════════════════════════════════════════════════════════════════════════
#  Nebula files
# ═════════════════════════════════════════════════════════════════════════
backup_file() {  # keeps ONE original copy under data/backups (never next to the file)
  local f=$1
  [[ -e $f && ! -L $f ]] || return 0
  local d="$DATA_DIR/backups/files"; mkdir -p "$d"
  local key; key=$(printf '%s' "$f" | sed 's|/|__|g')
  [[ -e $d/$key ]] && { info "Original already saved: $d/$key"; return 0; }
  cp -a "$f" "$d/$key" && say "Saved your original $(basename "$f") → data/backups/files"
}

copy_app() {
  mkdir -p "$INSTALL_DIR" "$DATA_DIR" || { err "Cannot create $INSTALL_DIR"; exit 1; }
  chmod 700 "$DATA_DIR"
  if [[ -f $SRC_DIR/bin/nebula && -f $SRC_DIR/install/install.sh && $SRC_DIR != "$INSTALL_DIR" ]]; then
    local keep_banner=""
    [[ -s $INSTALL_DIR/assets/banner.txt ]] && keep_banner=$(<"$INSTALL_DIR/assets/banner.txt")
    ( cd "$SRC_DIR" && tar --exclude=./data --exclude=./.git --exclude=./.github -cf - . ) \
      | ( cd "$INSTALL_DIR" && tar -xf - ) || { err "Copy failed"; exit 1; }
    # a banner customised in the old place (assets/) moves into data/ so updates never overwrite it
    if [[ -n $keep_banner && ! -s $DATA_DIR/banner.txt && $keep_banner != "$(<"$INSTALL_DIR/assets/banner.txt")" ]]; then
      printf '%s\n' "$keep_banner" > "$DATA_DIR/banner.txt"; say "Kept your custom banner (now stored in data/)"
    fi
    say "Copied Nebula → $INSTALL_DIR"
  elif [[ ! -f $INSTALL_DIR/bin/nebula ]]; then
    if [[ -n $REPO ]] && need_cmd git; then
      git clone --depth 1 "$REPO" "$INSTALL_DIR.tmp" && cp -a "$INSTALL_DIR.tmp/." "$INSTALL_DIR/" && rm -rf "$INSTALL_DIR.tmp"
    else
      err "Run this script from inside the Nebula folder (or set NEBULA_REPO)."; exit 1
    fi
  fi
  # lock the folder: only your Termux user can read or enter it
  chmod -R go-rwx "$INSTALL_DIR" 2>/dev/null; chmod 700 "$INSTALL_DIR" "$DATA_DIR" 2>/dev/null
  chmod +x "$INSTALL_DIR/bin/nebula" "$INSTALL_DIR/motd/init.sh" "$INSTALL_DIR/motd/motd.d/"* \
           "$INSTALL_DIR"/lib/*.sh 2>/dev/null || true
}

migrate_old_cvui() {
  local old_cfg="$HOME/.cvui" old_app="$HOME/.cvui-app" moved=0
  [[ -d $old_cfg || -d $old_app || -L $PREFIX/bin/cvui ]] || return 0
  info "Found an old cvui install."
  if [[ -d $old_cfg ]] && ask_yn "Move its login/notes into Nebula's data folder?" Y; then
    cp -an "$old_cfg/." "$DATA_DIR/" 2>/dev/null && { [[ -f $DATA_DIR/auth ]] && sed -i 's/^cvui_/NEBULA_/' "$DATA_DIR/auth"; rm -rf "$old_cfg"; } && say "Migrated $old_cfg → $DATA_DIR" && moved=1
  fi
  if ask_yn "Remove old cvui app ($old_app), command and shell hook?" Y; then
    rm -f "$PREFIX/bin/cvui"; rm -rf "$old_app"
    if [[ -f $HOME/.zshrc ]] && grep -q '# cvui-BEGIN' "$HOME/.zshrc"; then
      backup_file "$HOME/.zshrc"
      awk '/# cvui-BEGIN/{s=1;next} /# cvui-END/{s=0;next} !s{print}' "$HOME/.zshrc" > "$HOME/.zshrc.tmp" \
        && mv "$HOME/.zshrc.tmp" "$HOME/.zshrc"
    fi
    say "Removed old cvui"
  fi
}

# Termux only reads font/colors/keys from ~/.termux, so that folder gets tiny
# LINKS to the real files, which stay inside Nebula's own folder.
link_termux_file() {  # link_termux_file <real file> <path in ~/.termux>
  local src=$1 dst=$2
  [[ -f $src ]] || return 0
  if [[ -L $dst && $(readlink "$dst") == "$src" ]]; then return 0; fi
  backup_file "$dst"
  rm -f "$dst"; ln -s "$src" "$dst" && say "Linked $(basename "$dst") → $src"
}

install_look() {
  (( NEBULA_UPDATE_MODE )) && return 0
  (( NEBULA_SKIP_FONT && NEBULA_SKIP_COLORS && NEBULA_SKIP_KEYS )) && return
  if ! ask_yn "Apply Nebula font, colors & extra-keys to Termux?" Y; then
    info "Skipped Termux look (font/colors/keys)"; return
  fi
  info "The files stay in $INSTALL_DIR/assets — ~/.termux only gets links (Termux requires that path)."
  mkdir -p "$TERMUX_DIR"
  (( NEBULA_SKIP_FONT ))   || link_termux_file "$INSTALL_DIR/assets/fonts/nebula.ttf" "$TERMUX_DIR/font.ttf"
  (( NEBULA_SKIP_COLORS )) || link_termux_file "$INSTALL_DIR/assets/colors.properties" "$TERMUX_DIR/colors.properties"
  (( NEBULA_SKIP_KEYS ))   || link_termux_file "$INSTALL_DIR/assets/termux.properties" "$TERMUX_DIR/termux.properties"
  if need_cmd termux-reload-settings; then termux-reload-settings 2>/dev/null && say "Reloaded Termux settings"
  else info "Restart Termux to apply font/colors"; fi
}

install_nsh() {
  (( NEBULA_SKIP_NSH )) && { info "Skipping shell framework"; return; }
  if ! need_cmd zsh; then
    warn "zsh is not installed — skipping the zsh hook and shell auto-start."
    warn "Install it later:  pkg install zsh  then re-run this installer."
    return 1
  fi
  local zshrc="$HOME/.zshrc" tmpl="$INSTALL_DIR/zsh/zshrc.template" rendered block
  [[ -f $tmpl ]] || return 0
  rendered=$(sed "s|__NEBULA_INSTALL_DIR__|$INSTALL_DIR|g" "$tmpl")
  block=$(awk '/# nebula-BEGIN/,/# nebula-END/' <<<"$rendered")

  if [[ -f $zshrc ]] && grep -q '# nebula-BEGIN' "$zshrc"; then
    awk -v block="$block" '
      /# nebula-BEGIN/ { in_block=1; print block; next }
      /# nebula-END/   { in_block=0; next }
      !in_block        { print }' "$zshrc" > "$zshrc.nebula.tmp" && mv "$zshrc.nebula.tmp" "$zshrc"
    say "Refreshed Nebula block in $zshrc"
  elif [[ -s $zshrc ]]; then
    backup_file "$zshrc"; printf '\n%s\n' "$block" >> "$zshrc"
    say "Appended Nebula block to your existing $zshrc"
  else
    printf '%s\n' "$rendered" > "$zshrc"; say "Created $zshrc"
  fi

  # Termux motd: only silence it if Nebula's own is enabled
  if (( ! NEBULA_SKIP_MOTD )); then
    local zp="$PREFIX/etc/zprofile"
    if [[ -f $zp ]] && grep -qE '^[^#]*etc/motd/init\.sh' "$zp"; then
      backup_file "$zp"
      sed -i -E 's|^([^#]*etc/motd/init\.sh.*)$|# \1  # disabled by nebula|' "$zp"
    fi
    [[ -f $PREFIX/etc/motd && ! -e $HOME/.hushlogin ]] && : > "$HOME/.hushlogin"
  fi

  # Make zsh the login shell — guarded so a missing zsh can never lock you out
  [[ $SHELL != */zsh ]] && need_cmd chsh && chsh -s zsh 2>/dev/null && say "Default shell → zsh"
  if [[ ! -f $HOME/.bashrc ]] || ! grep -q 'exec zsh' "$HOME/.bashrc"; then
    printf '\n# Auto-start zsh (only if installed)\nif [[ -t 0 && $- == *i* ]] && command -v zsh >/dev/null 2>&1; then\n    exec zsh\nfi\n' >> "$HOME/.bashrc"
    say "Configured .bashrc to start zsh"
  fi
}

link_bin() {
  if [[ -w $(dirname "$BIN_LINK") ]]; then
    ln -sf "$INSTALL_DIR/bin/nebula" "$BIN_LINK" && say "Linked nebula → $BIN_LINK"
  else
    warn "Cannot write $BIN_LINK — add to PATH:  export PATH=\"$INSTALL_DIR/bin:\$PATH\""
  fi
}

# Run via `curl … | bash` (or from a lone file): fetch the project, then continue from it
bootstrap() {
  [[ -f $SRC_DIR/bin/nebula && -f $SRC_DIR/install/install.sh ]] && return 0
  need_cmd curl && need_cmd tar || { err "curl and tar are required:  pkg install curl tar"; exit 1; }
  local r=${REPO%.git}; r=${r#https://github.com/}
  info "Downloading Nebula from github.com/$r …"
  mkdir -p "$PREFIX/tmp"
  local tmp; tmp=$(mktemp -d "$PREFIX/tmp/nebula-src.XXXXXX") || { err "Can't create a temp folder"; exit 1; }
  local -a hdr=(); [[ -n ${NEBULA_TOKEN:-} ]] && hdr=(-H "Authorization: token $NEBULA_TOKEN")
  if ! curl -fsSL "${hdr[@]}" "https://codeload.github.com/$r/tar.gz/refs/heads/${NEBULA_BRANCH:-main}" | tar -xz -C "$tmp" --strip-components=1 2>/dev/null \
     || [[ ! -f $tmp/install/install.sh ]]; then
    err "Download failed. Check your connection and that github.com/$r exists (private repo? set NEBULA_TOKEN)."; rm -rf "$tmp"; exit 1
  fi
  NEBULA_BOOTSTRAPPED=1 exec bash "$tmp/install/install.sh" "${ORIG_ARGS[@]}"
}

# After installing, the folder you cloned/unzipped is just a duplicate — offer to remove it.
cleanup_source() {
  [[ $SRC_DIR == "$INSTALL_DIR" || ${NEBULA_KEEP_SOURCE:-0} == 1 ]] && return 0
  [[ -f $SRC_DIR/bin/nebula && -f $SRC_DIR/install/install.sh ]] || return 0
  # our own temporary download (curl | bash, nebula update) → always clean up
  if [[ $SRC_DIR == "$PREFIX"/tmp/nebula-src.* ]]; then cd "$HOME" 2>/dev/null || cd /; rm -rf "$SRC_DIR"; say "Removed the temporary download"; return 0; fi
  case "$SRC_DIR" in ""|/|"$HOME"|"$PREFIX"|"$PREFIX"/*|/data|/data/data|/data/data/com.termux|/data/data/com.termux/files) return 0 ;; esac
  [[ $INSTALL_DIR == "$SRC_DIR"/* || $HOME == "$SRC_DIR"/* ]] && return 0      # never delete a parent of anything that matters
  local pretty=${SRC_DIR/#$HOME/\~}
  if (( BOOTSTRAPPED )); then
    cd "$HOME" 2>/dev/null; rm -rf "$SRC_DIR"; say "Removed the temporary download"; return 0
  fi
  info "Nebula now lives in $INSTALL_DIR."
  if ask_yn "Delete the download folder $pretty? (update any time with: nebula update)" Y; then
    cd "$HOME" 2>/dev/null || cd /
    rm -rf "$SRC_DIR" && say "Removed $pretty"
    local z; for z in "$SRC_DIR.zip" "$(dirname "$SRC_DIR")/$(basename "$SRC_DIR").zip"; do
      [[ -f $z ]] && ask_yn "Also delete $(basename "$z")?" Y && rm -f "$z" && say "Removed $(basename "$z")"
    done
  else info "Kept $pretty — you can delete it yourself later."; fi
}

# ═════════════════════════════════════════════════════════════════════════
#  main
# ═════════════════════════════════════════════════════════════════════════
if (( DEPS_ONLY )); then
  [[ -d $INSTALL_DIR/install ]] && SRC_DIR=$INSTALL_DIR
  DEPS_MODE=ask; run_dependencies; exit 0
fi

bootstrap

if (( NEBULA_UPDATE_MODE )); then          # nebula update: copy new files, keep everything else
  copy_app
  install_nsh >/dev/null 2>&1 || true
  link_bin >/dev/null 2>&1 || true
  NEBULA_HOME="$INSTALL_DIR" NEBULA_CFG="$DATA_DIR" bash "$INSTALL_DIR/bin/nebula" scan --quiet >/dev/null 2>&1 || true
  exit 0
fi

banner; hr
say "Install location : $INSTALL_DIR"
say "User data        : $DATA_DIR"
say "Command          : $BIN_LINK"
hr

run_dependencies
copy_app
migrate_old_cvui
install_look
install_nsh
link_bin

cleanup_source
mkdir -p "$DATA_DIR" && touch "$DATA_DIR/.setup_done"

# Look at the device now so Settings, hidden commands and warnings are ready
info "Checking your device…"
NEBULA_HOME="$INSTALL_DIR" NEBULA_CFG="$DATA_DIR" bash "$INSTALL_DIR/bin/nebula" scan 2>/dev/null || true

hr
say "Nebula installed!"
printf "\n  Run it with:   \033[1;36mnebula\033[0m\n"
printf "  Add packages:  \033[1;36mnebula deps\033[0m\n"
printf "  Device & fixes:\033[1;36m nebula settings\033[0m\n"
printf "  Uninstall:     \033[1;36mbash %s/install/uninstall.sh\033[0m\n" "$INSTALL_DIR"
