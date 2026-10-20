#!/data/data/com.termux/files/usr/bin/env bash
# nebula — updates straight from GitHub. No git needed, your data/ is never touched.
#
#   nebula update              check, show what's new, install
#   nebula update --check      only check
#   nebula update --force      reinstall the latest even if versions match
#   nebula update --rollback   go back to the version before the last update
#   nebula update --branch dev update from another branch
#
# Source: NEBULA_REPO (default https://github.com/jitetee/nebula)
# Private repo? export NEBULA_TOKEN=<GitHub token with repo read access>

NEBULA_REPO_DEFAULT="https://github.com/jitetee/nebula"

update::_repo() {  # → owner/name
  local r=${NEBULA_REPO:-$NEBULA_REPO_DEFAULT}
  r=${r%.git}; r=${r#https://github.com/}; r=${r#git@github.com:}; printf '%s' "$r"
}
update::_curl() {
  local -a h=(); [[ -n ${NEBULA_TOKEN:-} ]] && h=(-H "Authorization: token $NEBULA_TOKEN")
  curl -fsSL --max-time "${UPDATE_TIMEOUT:-15}" -A nebula-termux "${h[@]}" "$@"
}
update::local_version() { [[ -r $NEBULA_HOME/VERSION ]] && tr -d '[:space:]' < "$NEBULA_HOME/VERSION" || echo 0.0.0; }
update::remote_version() {  # branch → version
  update::_curl "https://raw.githubusercontent.com/$(update::_repo)/${1:-main}/VERSION" 2>/dev/null | tr -d '[:space:]'
}
# true if $1 is newer than $2 (dotted numbers)
update::newer() { [[ $1 != "$2" && $(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -1) == "$1" ]]; }

# Once a day, quietly: tell the user if a newer version exists (never blocks > 3s)
update::check() {
  [[ ${NEBULA_NO_UPDATE_CHECK:-0} == 1 ]] && return 0
  command -v curl >/dev/null 2>&1 || return 0
  local f="$NEBULA_CFG/.update_check" now; now=$(date +%s)
  local last=0 latest=""
  [[ -r $f ]] && IFS='|' read -r last latest < "$f"
  if (( now - ${last:-0} > 86400 )); then
    latest=$(UPDATE_TIMEOUT=3 update::remote_version main)
    [[ $latest =~ ^[0-9][0-9.]*$ ]] || latest=""
    mkdir -p "$NEBULA_CFG"; printf '%s|%s\n' "$now" "$latest" > "$f"
  fi
  if [[ -n $latest ]] && update::newer "$latest" "$(update::local_version)"; then
    printf "  ${C_YELLOW}⬆ Nebula %s is available${C_RESET} ${C_DIM}(you have %s)${C_RESET} — run: ${C_BOLD}%s${C_RESET}\n" "$latest" "$(update::local_version)" "$(update::via_pkg && echo 'pkg upgrade nebula' || echo 'nebula update')"
  fi
}

update::_backup_app() {  # tar the app (not data/) so --rollback works
  local v; v=$(update::local_version); local d="$NEBULA_CFG/backups"; mkdir -p "$d"
  tar -C "$NEBULA_HOME" --exclude=./data -czf "$d/nebula-app-$v.tar.gz" . 2>/dev/null && chmod 600 "$d/nebula-app-$v.tar.gz"
  ls -1t "$d"/nebula-app-*.tar.gz 2>/dev/null | tail -n +4 | while read -r old; do rm -f "$old"; done
}

# installed with `pkg install nebula`?  (then pkg owns the files)
update::via_pkg() { dpkg-query -W -f='${Status}' nebula 2>/dev/null | grep -q 'install ok installed'; }

cmd::update() {
  local check=0 force=0 rollback=0 branch=main a self=0
  while (( $# )); do
    case $1 in
      --self) self=1 ;;
      --check|-c) check=1 ;; --force|-f) force=1 ;; --rollback) rollback=1 ;;
      --branch)   branch=${2:-main}; shift ;; --branch=*) branch=${1#--branch=} ;;
    esac; shift
  done
  if update::via_pkg && (( ! self && ! rollback )); then
    ui::say_status INFO "Nebula was installed with pkg, so pkg keeps it up to date:"
    printf '     %spkg update && pkg upgrade nebula%s\n' "$C_BOLD" "$C_RESET"
    printf '   %s(to update straight from GitHub anyway: nebula update --self)%s\n' "$C_DIM" "$C_RESET"
    return 0
  fi
  command -v curl >/dev/null 2>&1 && command -v tar >/dev/null 2>&1 || { ui::say_status ERR "curl and tar are required: pkg install curl tar"; return 1; }

  if (( rollback )); then
    local last; last=$(ls -1t "$NEBULA_CFG"/backups/nebula-app-*.tar.gz 2>/dev/null | head -1)
    [[ -z $last ]] && { ui::say_status ERR "No earlier version saved yet."; return 1; }
    ui::say_status WARN "This restores $(basename "$last")."
    ui::confirm "Roll back?" N || return 0
    tar -C "$NEBULA_HOME" -xzf "$last" && ui::say_status OK "Rolled back to $(update::local_version). Restart your shell: exec zsh"
    return $?
  fi

  local repo; repo=$(update::_repo)
  ui::say_status INFO "Checking github.com/$repo ($branch)…"
  local latest cur; latest=$(update::remote_version "$branch"); cur=$(update::local_version)
  if [[ ! $latest =~ ^[0-9][0-9.]*$ ]]; then
    ui::say_status ERR "Couldn't read the latest version (offline, wrong repo, or private repo without NEBULA_TOKEN)."
    ui::say_status INFO "Repo: https://github.com/$repo  ·  override with: export NEBULA_REPO=https://github.com/<you>/<repo>"
    return 1
  fi
  if ! update::newer "$latest" "$cur" && (( ! force )); then
    ui::say_status OK "You're up to date (v$cur)."; return 0
  fi
  printf "\n  ${C_BOLD}v%s${C_RESET} ${C_DIM}→${C_RESET} ${C_GREEN}${C_BOLD}v%s${C_RESET}\n" "$cur" "$latest"
  local notes; notes=$(update::_curl "https://raw.githubusercontent.com/$repo/$branch/docs/CHANGELOG.md" 2>/dev/null | awk '/^## /{n++; next} n==1' | grep -v '^[[:space:]]*$' | head -8)
  [[ -n $notes ]] && { printf "  ${C_DIM}What's new:${C_RESET}\n"; sed 's/^/   /' <<<"$notes" | cut -c1-$(( $(ui::cols) - 2 )); }
  (( check )) && { printf "\n  Run ${C_BOLD}nebula update${C_RESET} to install it.\n"; return 0; }
  ui::confirm "Update now?" Y || return 0

  local tmp; tmp=$(mktemp -d "${PREFIX:-/tmp}/tmp/nebula-update.XXXXXX") || { ui::say_status ERR "Can't create a temp folder"; return 1; }
  trap 'rm -rf "$tmp"' RETURN
  ui::say_status INFO "Downloading…"
  update::_curl "https://codeload.github.com/$repo/tar.gz/refs/heads/$branch" -o "$tmp/src.tar.gz" || { ui::say_status ERR "Download failed."; return 1; }
  mkdir -p "$tmp/src"; tar -xzf "$tmp/src.tar.gz" -C "$tmp/src" --strip-components=1 2>/dev/null || { ui::say_status ERR "That download isn't a valid archive."; return 1; }
  if [[ ! -f $tmp/src/bin/nebula || ! -f $tmp/src/install/install.sh || ! -f $tmp/src/VERSION ]] || ! bash -n "$tmp/src/bin/nebula" 2>/dev/null; then
    ui::say_status ERR "The download doesn't look like Nebula — nothing was changed."; return 1
  fi
  update::_backup_app
  ui::say_status INFO "Installing v$latest (your data stays untouched)…"
  if NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" bash "$tmp/src/install/install.sh" --update; then
    ui::say_status OK "Updated to v$(tr -d '[:space:]' < "$NEBULA_HOME/VERSION"). Restart your shell to load it:  exec zsh"
    ui::say_status INFO "Something wrong? nebula update --rollback"
  else
    ui::say_status ERR "The update failed part-way. Restoring the previous version…"
    tar -C "$NEBULA_HOME" -xzf "$NEBULA_CFG/backups/nebula-app-$cur.tar.gz" 2>/dev/null && ui::say_status OK "Restored v$cur."
    return 1
  fi
}

# `nebula setup` — finish a `pkg install nebula` (zsh hook, Termux look, device scan, package picker)
#   nebula setup           run the interactive setup      nebula setup --undo   remove the shell hooks
cmd::setup() {
  case ${1:-} in
    --undo) bash "$NEBULA_HOME/install/uninstall.sh" --hooks-only --yes ;;
    *)      bash "$NEBULA_HOME/install/install.sh" "$@" && { mkdir -p "$NEBULA_CFG"; touch "$NEBULA_CFG/.setup_done"; } ;;
  esac
}
