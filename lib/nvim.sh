#!/data/data/com.termux/files/usr/bin/env bash
# nebula — nv: Neovim in the Nebula look (assets/nvim) + a Copilot doctor
#   nv [files]              open Neovim with the Nebula setup
#   nv setup                link the config, fetch plugins (asks before installing packages)
#   nv doctor | copilot     find out why Copilot (or anything else) is not working
#   nv plugins              install/update plugins        nv reset      forget plugins + state
#   nv uninstall            remove the link (and your plugin data, if you say yes)
# It never touches ~/.config/nvim: Nebula's setup lives under its own name (NVIM_APPNAME).
# Your own tweaks:  $NEBULA_CFG/nvim/user.lua   (kept across updates)

NV_APP="${NEBULA_NVIM_APPNAME:-nebula}"

nv::_cfg()   { printf '%s/%s' "${XDG_CONFIG_HOME:-$HOME/.config}" "$NV_APP"; }
nv::_data()  { printf '%s/%s' "${XDG_DATA_HOME:-$HOME/.local/share}" "$NV_APP"; }
nv::_state() { printf '%s/%s' "${XDG_STATE_HOME:-$HOME/.local/state}" "$NV_APP"; }
nv::_cache() { printf '%s/%s' "${XDG_CACHE_HOME:-$HOME/.cache}" "$NV_APP"; }
nv::_src()   { printf '%s/assets/nvim' "$NEBULA_HOME"; }

nv::_safe_app() { [[ -n $NV_APP && $NV_APP != nvim && $NV_APP != */* && $NV_APP != .* ]]; }

nv::_run() {   # run Neovim as the Nebula setup
  NVIM_APPNAME="$NV_APP" NEBULA_HOME="$NEBULA_HOME" NEBULA_CFG="$NEBULA_CFG" command nvim "$@"
}

nv::_linked() { local c; c=$(nv::_cfg); [[ -L $c && $(readlink -f "$c" 2>/dev/null) == "$(readlink -f "$(nv::_src)" 2>/dev/null)" ]]; }

nv::_link() {
  nv::_safe_app || { ui::say_status ERR "NEBULA_NVIM_APPNAME must be a plain name (not 'nvim')."; return 1; }
  local c; c=$(nv::_cfg)
  if nv::_linked; then return 0; fi
  if [[ -e $c || -L $c ]]; then
    ui::say_status ERR "$c already exists and is not Nebula's. Set NEBULA_NVIM_APPNAME to another name, or move it."
    return 1
  fi
  mkdir -p "$(dirname "$c")" && ln -s "$(nv::_src)" "$c" && ui::say_status OK "Linked $c → Nebula's nvim setup"
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
  ui::say_status OK "Done. Open it with:  nv   ·  keys: Space ?  ·  Copilot: nv doctor"
}

nv::plugins() {
  command -v nvim >/dev/null 2>&1 || { ui::say_status ERR "Neovim is not installed (nv setup)."; return 1; }
  nv::_link || return 1
  ui::say_status INFO "Fetching plugins (first run takes a minute)…"
  nv::_run --headless "+Lazy! sync" +qa >"$NEBULA_CFG/nvim-plugins.log" 2>&1
  local rc=$?
  if (( rc == 0 )); then ui::say_status OK "Plugins are up to date."
  else ui::say_status WARN "Plugin sync had problems. Log: $NEBULA_CFG/nvim-plugins.log"; fi
  return $rc
}

nv::doctor() {
  ui::say_status INFO "Nebula nvim · Copilot doctor"
  local ok=1 major v
  if command -v nvim >/dev/null 2>&1; then
    v=$(nvim --version 2>/dev/null | head -1); ui::say_status OK "$v"
  else ui::say_status ERR "Neovim is not installed.  → pkg install neovim"; return 1; fi
  if nv::_linked; then ui::say_status OK "Config linked: $(nv::_cfg)"
  else ui::say_status ERR "Nebula's nvim config is not linked.  → nv setup"; ok=0; fi
  command -v git >/dev/null 2>&1 && ui::say_status OK "git found" || { ui::say_status ERR "git missing (plugins need it).  → pkg install git"; ok=0; }

  major=$(nv::_node_major)
  if [[ -z $major ]]; then ui::say_status ERR "Node.js missing (Copilot's server runs on it).  → pkg install nodejs"; ok=0
  elif (( major < 20 )); then ui::say_status ERR "Node $major is too old.  → pkg upgrade nodejs"; ok=0
  else ui::say_status OK "Node $major"; fi

  if [[ -d $(nv::_data)/lazy/copilot.vim ]]; then ui::say_status OK "copilot.vim installed by Nebula's plugin manager"
  else ui::say_status ERR "copilot.vim not installed yet.  → nv plugins"; ok=0; fi

  local stray="${XDG_CONFIG_HOME:-$HOME/.config}/nvim/pack/github/start/copilot.vim"
  if [[ -e $stray ]]; then
    ui::say_status WARN "Found $stray. A plain Neovim loads it, Nebula's setup does not (it uses its own name). Nothing to do unless you use plain nvim too."
  fi

  local auth="$HOME/.config/github-copilot"
  if [[ -s $auth/apps.json || -s $auth/hosts.json ]]; then ui::say_status OK "Signed in to GitHub Copilot"
  else ui::say_status WARN "Not signed in. Open nv, run  :Copilot setup , open the link, type the code."; fi

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
  ui::confirm "Delete Nebula nvim's plugins, state and cache? (your files and user.lua stay)" N || return 1
  rm -rf -- "$(nv::_data)" "$(nv::_state)" "$(nv::_cache)"
  ui::say_status OK "Cleared. Run  nv plugins  to fetch them again."
}

nv::uninstall() {
  nv::_safe_app || return 1
  local c; c=$(nv::_cfg)
  if nv::_linked; then rm -f -- "$c"; ui::say_status OK "Removed link $c"; else ui::say_status INFO "No Nebula link at $c"; fi
  ui::confirm "Also delete plugins and state?" N && { rm -rf -- "$(nv::_data)" "$(nv::_state)" "$(nv::_cache)"; ui::say_status OK "Deleted plugin data."; }
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
      printf '%s\n' "  nv [files]        open Neovim (Nebula look)" "  nv setup          link config + fetch plugins" \
        "  nv doctor         check Copilot / node / git / sign-in" "  nv plugins        install or update plugins" \
        "  nv reset          clear plugins + state" "  nv uninstall      remove the link" \
        "  Space ?           key cheat sheet inside nvim" "  Your tweaks:      \$NEBULA_CFG/nvim/user.lua" ;;
    --) shift; nv::_link && nv::_run "$@" ;;
    *)
      command -v nvim >/dev/null 2>&1 || { ui::say_status ERR "Neovim is not installed.  → nv setup"; return 1; }
      if ! nv::_linked; then
        ui::say_status INFO "First run: setting up Nebula's Neovim…"
        nv::setup || return 1
      fi
      nv::_run "$@" ;;
  esac
}
