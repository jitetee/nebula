#!/data/data/com.termux/files/usr/bin/env bash
# nebula — nv: make plain `nvim` look and work the Nebula way (config in assets/nvim)
#   nvim / nv [files]       open Neovim (same thing once set up)
#   nv setup                install Nebula as your Neovim config (backs up the old one first)
#   nv doctor | copilot     find out why Copilot (or anything else) is not working
#   nv plugins              install/update plugins        nv reset      forget plugins
#   nv uninstall            remove Nebula's config and bring your old one back
# `~/.config/nvim` becomes a link to Nebula's folder, so `nebula update` updates it too.
# Your own tweaks:  $NEBULA_CFG/nvim/user.lua   (kept across updates)
# Side by side instead (keeps your own nvim untouched): export NEBULA_NVIM_APPNAME=nebula, then use `nv`.

NV_APP="${NEBULA_NVIM_APPNAME:-nvim}"

nv::_cfg()   { printf '%s/%s' "${XDG_CONFIG_HOME:-$HOME/.config}" "$NV_APP"; }
nv::_data()  { printf '%s/%s' "${XDG_DATA_HOME:-$HOME/.local/share}" "$NV_APP"; }
nv::_src()   { printf '%s/assets/nvim' "$NEBULA_HOME"; }
nv::_safe_app() { [[ -n $NV_APP && $NV_APP != */* && $NV_APP != .* ]]; }

nv::_run() {   # run Neovim as the Nebula setup
  if [[ $NV_APP != nvim ]]; then export NVIM_APPNAME="$NV_APP"; fi
  NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" command nvim "$@"
}

nv::_linked() { local c; c=$(nv::_cfg); [[ -L $c && $(readlink -f "$c" 2>/dev/null) == "$(readlink -f "$(nv::_src)" 2>/dev/null)" ]]; }

nv::_latest_backup() { ls -dt "$(nv::_cfg)".nebula-backup-* 2>/dev/null | head -1; }

nv::_link() {
  nv::_safe_app || { ui::say_status ERR "NEBULA_NVIM_APPNAME must be a plain name."; return 1; }
  nv::_linked && return 0
  local c; c=$(nv::_cfg)
  if [[ -e $c || -L $c ]]; then
    local bak="$c.nebula-backup-$(date +%Y%m%d-%H%M%S)"
    ui::say_status INFO "You already have a Neovim config at $c."
    ui::confirm "Move it to $(basename "$bak") and use Nebula's instead? (nv uninstall brings it back)" Y || {
      ui::say_status INFO "Left as is. For side by side:  export NEBULA_NVIM_APPNAME=nebula  then  nv setup"; return 1; }
    mv -- "$c" "$bak" || return 1
    ui::say_status OK "Backed up to $bak"
  fi
  mkdir -p "$(dirname "$c")" && ln -s "$(nv::_src)" "$c" && ui::say_status OK "Neovim now uses Nebula's setup ($c → assets/nvim)"
}

nv::_node_major() { command -v node >/dev/null 2>&1 || return 1; node --version 2>/dev/null | sed -n 's/^v\([0-9]\+\).*/\1/p'; }

nv::_pkg_install() {   # nv::_pkg_install <pkg>...  (Termux/apt aware, asks first)
  local missing=("$@")
  ui::confirm "Install ${missing[*]}?" Y || return 1
  if command -v pkg >/dev/null 2>&1; then pkg install -y "${missing[@]}"
  elif command -v apt-get >/dev/null 2>&1; then
    if [[ $(id -u) == 0 ]]; then apt-get install -y "${missing[@]}"
    elif command -v sudo >/dev/null 2>&1; then sudo apt-get install -y "${missing[@]}"
    else ui::say_status WARN "Install ${missing[*]} as root (no sudo here)."; return 1; fi
  else ui::say_status WARN "Install ${missing[*]} with your package manager."; return 1; fi
}

nv::setup() {
  local need=()
  command -v nvim >/dev/null 2>&1 || need+=(neovim)
  command -v git  >/dev/null 2>&1 || need+=(git)
  (( ${#need[@]} )) && { nv::_pkg_install "${need[@]}" || return 1; }
  command -v nvim >/dev/null 2>&1 || { ui::say_status ERR "Neovim is still missing."; return 1; }
  nv::_link || return 1
  local opt=()
  command -v node >/dev/null 2>&1 || opt+=(nodejs)
  command -v rg   >/dev/null 2>&1 || opt+=(ripgrep)
  command -v cc >/dev/null 2>&1 || command -v clang >/dev/null 2>&1 || command -v gcc >/dev/null 2>&1 || opt+=(clang)
  if (( ${#opt[@]} )); then
    ui::say_status INFO "Optional: nodejs (Copilot), ripgrep (text search), clang (syntax colours)."
    nv::_pkg_install "${opt[@]}" || ui::say_status INFO "Skipped. Nebula nvim works without them."
  fi
  nv::plugins
  ui::say_status OK "Done. Just type  nvim  ·  keys: Space ?  ·  AI: Space a a  ·  Copilot: nv doctor"
}

nv::plugins() {
  command -v nvim >/dev/null 2>&1 || { ui::say_status ERR "Neovim is not installed (nv setup)."; return 1; }
  nv::_link || return 1
  mkdir -p "$NEBULA_CFG"
  ui::say_status INFO "Fetching plugins (first run takes a minute)…"
  nv::_run --headless "+Lazy! sync" +qa >"$NEBULA_CFG/nvim-plugins.log" 2>&1
  local rc=$?
  if (( rc == 0 )) && { command -v cc >/dev/null 2>&1 || command -v clang >/dev/null 2>&1 || command -v gcc >/dev/null 2>&1; }; then
    ui::say_status INFO "Building syntax colours (one time)…"
    nv::_run --headless "+lua local ok,p=pcall(require,'nebula.plugins'); if ok and p.install_parsers then p.install_parsers() end" +qa >>"$NEBULA_CFG/nvim-plugins.log" 2>&1
  fi
  if (( rc == 0 )); then ui::say_status OK "Plugins are up to date."
  else ui::say_status WARN "Plugin sync had problems. Log: $NEBULA_CFG/nvim-plugins.log"; fi
  return $rc
}

nv::doctor() {
  ui::say_status INFO "Nebula nvim · doctor"
  local ok=1 major v
  if command -v nvim >/dev/null 2>&1; then
    v=$(nvim --version 2>/dev/null | head -1); ui::say_status OK "$v"
  else ui::say_status ERR "Neovim is not installed.  → pkg install neovim"; return 1; fi
  if nv::_linked; then ui::say_status OK "Plain nvim uses Nebula's setup ($(nv::_cfg))"
  else ui::say_status ERR "Nebula's nvim config is not active.  → nv setup"; ok=0; fi
  command -v git >/dev/null 2>&1 && ui::say_status OK "git found" || { ui::say_status ERR "git missing (plugins need it).  → pkg install git"; ok=0; }

  major=$(nv::_node_major)
  if [[ -z $major ]]; then ui::say_status ERR "Node.js missing (Copilot's server runs on it).  → pkg install nodejs"; ok=0
  elif (( major < 20 )); then ui::say_status ERR "Node $major is too old.  → pkg upgrade nodejs"; ok=0
  else ui::say_status OK "Node $major"; fi

  if [[ -d $(nv::_data)/lazy/copilot.vim ]]; then ui::say_status OK "copilot.vim installed by Nebula's plugin manager"
  else ui::say_status ERR "copilot.vim not installed yet.  → nv plugins"; ok=0; fi

  local bak; bak=$(nv::_latest_backup)
  [[ -n $bak ]] && ui::say_status INFO "Your old config is kept at $bak"
  ui::say_status INFO "Icon test: $(printf '\ue400 \ue401 \ue402 \ue403 \ue404 \ue405 | \ue0a0 \uf057 \uf4b8')   (first six are Nebula's own; boxes mean the font is not Nebula Mono: NEBULA_ICONS=nerd|plain nvim)"

  local auth="$HOME/.config/github-copilot"
  if [[ -s $auth/apps.json || -s $auth/hosts.json ]]; then ui::say_status OK "Signed in to GitHub Copilot"
  else ui::say_status WARN "Not signed in. Open nvim, run  :NebulaCopilot  and press  s ."; fi

  if command -v curl >/dev/null 2>&1; then
    local code; code=$(curl -s --max-time 8 -o /dev/null -w '%{http_code}' https://api.github.com 2>/dev/null)
    if [[ $code =~ ^[1-5][0-9][0-9]$ ]]; then ui::say_status OK "GitHub is reachable (HTTP $code)"
    else ui::say_status ERR "Cannot reach api.github.com (check Wi-Fi/data, VPN, DNS)."; ok=0; fi
  fi

  if nv::_linked && [[ -d $(nv::_data)/lazy/copilot.vim ]]; then
    local log; log=$(nv::_run --headless "+lua vim.cmd('enew | setfiletype lua | startinsert')" "+sleep 1500m" \
      "+lua local s=vim.api.nvim_exec2('Copilot status',{output=true}).output; io.stdout:write('SERVER: '..s..'\n')" +qa 2>&1 | tr -d '\r' | grep '^SERVER:' | head -1)
    case $log in
      *Ready*) ui::say_status OK "Copilot server starts (Ready)" ;;
      *) ui::say_status ERR "Copilot server did not start: ${log:-no answer}. In nvim run  :Copilot log"; ok=0 ;;
    esac
  fi
  (( ok )) && ui::say_status OK "Looks good. In insert mode: type a comment and wait a second; Tab accepts." \
           || ui::say_status INFO "Fix the ✖ items above, then run  nv doctor  again."
  return $(( 1 - ok ))
}

nv::reset() {
  nv::_safe_app || { ui::say_status ERR "Unsafe app name."; return 1; }
  ui::confirm "Delete Nebula's downloaded plugins (your config, files and user.lua stay)?" N || return 1
  rm -rf -- "$(nv::_data)/lazy" "$(nv::_data)/lazy-lock.json"
  ui::say_status OK "Cleared. Run  nv plugins  to fetch them again."
}

nv::uninstall() {
  nv::_safe_app || return 1
  local c bak; c=$(nv::_cfg); bak=$(nv::_latest_backup)
  if nv::_linked; then rm -f -- "$c"; ui::say_status OK "Removed Nebula's link $c"
  else ui::say_status INFO "Nebula is not active at $c"; return 0; fi
  if [[ -n $bak ]] && ui::confirm "Bring back your old config ($(basename "$bak"))?" Y; then
    mv -- "$bak" "$c" && ui::say_status OK "Restored $c"
  fi
  ui::confirm "Also delete downloaded plugins?" N && { rm -rf -- "$(nv::_data)/lazy" "$(nv::_data)/lazy-lock.json"; ui::say_status OK "Deleted plugins."; }
  return 0
}

cmd::nv() {
  case "${1:-}" in
    setup|install)        shift; nv::setup "$@" ;;
    doctor|copilot|check) shift; nv::doctor "$@" ;;
    plugins|sync|update)  shift; nv::plugins "$@" ;;
    reset)                shift; nv::reset "$@" ;;
    uninstall)            shift; nv::uninstall "$@" ;;
    help|--help|-h)
      printf '%s\n' "  nvim              plain nvim is the Nebula setup after: nv setup" "  nv setup          install it (backs up your old config)" \
        "  nv doctor         check Copilot / node / git / sign-in" "  nv plugins        install or update plugins" \
        "  nv reset          forget downloaded plugins" "  nv uninstall      remove it, restore your old config" \
        "  Space ?           key cheat sheet inside nvim" "  Space a a         ask the AI (Ant)  ·  Space a g  agent" "  Your tweaks:      \$NEBULA_CFG/nvim/user.lua" ;;
    --) shift; nv::_run "$@" ;;
    *)
      command -v nvim >/dev/null 2>&1 || { ui::say_status ERR "Neovim is not installed.  → nv setup"; return 1; }
      if ! nv::_linked; then
        ui::say_status INFO "First run: setting up Nebula's Neovim…"
        nv::setup || return 1
      fi
      nv::_run "$@" ;;
  esac
}
