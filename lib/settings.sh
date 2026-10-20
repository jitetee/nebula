#!/data/data/com.termux/files/usr/bin/env bash
# nebula — settings: device info, health, feature switches, Termux:API guide

settings::_flag_on()  { [[ -f $NEBULA_CFG/$1 ]]; }
settings::_state() {  # settings::_state on|off → "ON\tg" / "off\td"
  [[ $1 == on ]] && printf 'ON\tg' || printf 'off\td'
}
settings::_autolock_min() { local m=10; [[ -f $NEBULA_CFG/autolock ]] && m=$(<"$NEBULA_CFG/autolock"); [[ $m =~ ^[0-9]+$ ]] || m=10; echo "$m"; }
settings::_voice_on()  { [[ ${NEBULA_VOICE:-1} -eq 1 ]]; }
settings::_sound_on()  { [[ ${NEBULA_SOUNDS:-1} -eq 1 ]]; }

settings::_say_fix_result() { menu::wait; device::scan --quiet; }

# Run a fix command (after asking). "@api" opens the Termux:API guide instead.
settings::run_fix() {
  local cmd=$1
  [[ $cmd == @api ]] && { settings::guide_api; return; }
  [[ -z $cmd ]] && return
  printf '\033[H\033[2J'
  printf "  ${C_BOLD}Run:${C_RESET} %s\n\n" "$cmd"
  ui::confirm "Go ahead?" Y || return
  printf '\n'
  eval "$cmd"
  settings::_say_fix_result
}

# ── device ──────────────────────────────────────────────────────────────
device::info_text() {
  local arch bits ram free api reason online src
  arch=$(device::get arch); bits=$(device::get bits)
  ram=$(device::get ram_kb); free=$(device::get free_mb)
  reason=$(device::get api_reason); online=$(device::get online); src=$(device::get termux_source)
  case $reason in
    ok)    api="${C_GREEN}✔ working${C_RESET}" ;;
    noapp) api="${C_YELLOW}⚠ package installed, app not responding${C_RESET}" ;;
    *)     api="${C_RED}✖ not installed${C_RESET}" ;;
  esac
  printf "${C_CYAN}${C_BOLD}📱 Device${C_RESET}\n"
  local _r
  _kv() { local lab; printf -v lab '%-11s' "$1"; viz::wrap "$(( $(ui::cols) - 1 ))" "  ${lab} " "              " "$2"; }
  _kv "Model"   "$(device::get model)"
  _kv "Android" "$(device::get android) (API $(device::get sdk))"
  _kv "CPU"     "$(device::arch_label) · $(device::get cores) cores"
  _kv "Memory"  "$(ui::human_kb "${ram:-0}") RAM"
  _kv "Storage" "$(ui::human_kb $(( ${free:-0} * 1024 ))) free"
  _kv "Termux"  "$(device::get termux_version) · from $src"
  _kv "Termux:API" "$api"
  _kv "Internet" "$([[ $online == 1 ]] && echo yes || echo no)"
  _kv "Startup" "$(settings::_flag_on compact && echo compact || echo full)"
  _kv "Screen"  "$(ui::cols)×$(ui::rows) ($(ui::bp)) · layout ${NEBULA_LAYOUT:-auto}"
  unset -f _kv
  local notes=""
  (( bits == 32 )) && notes+="  • 32-bit CPU: some packages have no build for it. The package picker (deps) marks those.\n"
  [[ $ram =~ ^[0-9]+$ ]] && (( ram < 2000000 )) && notes+="  • Low memory: heavy tools can be killed by Android.\n"
  settings::_flag_on compact && notes+="  • Compact startup is on to keep things light (Settings → Features).\n"
  [[ -n $notes ]] && printf "\n${C_DIM}Notes${C_RESET}\n%b" "$notes"
}

settings::page_device() {
  printf '\033[H\033[2J'; device::info_text; menu::wait
}

# ── health ──────────────────────────────────────────────────────────────
settings::_sev_icon() { case $1 in error) printf '✖';; warn) printf '⚠';; *) printf 'ℹ';; esac; }
settings::_sev_col()  { case $1 in error) printf r;; warn) printf y;; *) printf d;; esac; }

settings::page_health() {
  local cur=0
  while :; do
    local -a items=() ids=() lines=()
    local sev id title why hint fix pkg
    while IFS='|' read -r sev id title why hint fix pkg; do
      [[ -z $sev ]] && continue
      items+=("$(settings::_sev_icon "$sev") $title"$'\t'"$sev"$'\t'"$(settings::_sev_col "$sev")")
      lines+=("$sev|$id|$title|$why|$hint|$fix|$pkg")
    done < <(device::issues)
    if (( ${#items[@]} == 0 )); then
      printf '\033[H\033[2J'; printf "${C_GREEN}✔ No problems found.${C_RESET}\n"; menu::wait; return
    fi
    MENU_INFO=""; MENU_CUR=$cur
    menu::pick "🩺 Health" "Enter for details and fixes · q back" items || return
    cur=$MENU_IDX
    IFS='|' read -r sev id title why hint fix pkg <<<"${lines[cur]}"
    settings::issue_detail "$title" "$why" "$hint" "$fix"
  done
}

settings::issue_detail() {
  local title=$1 why=$2 hint=$3 fix=$4
  local -a opts=() acts=()
  if [[ $fix == @api ]]; then opts+=($'📖 Open the Termux:API guide\t\tg'); acts+=(guide)
  elif [[ -n $fix ]]; then opts+=($'▶ Run fix\t'"$fix"$'\tg'); acts+=(fix); fi
  opts+=($'← Back\t\td'); acts+=(back)
  MENU_INFO="${C_BOLD}$title${C_RESET}"$'\n'"  ${C_DIM}Why:${C_RESET} $why"$'\n'"  ${C_DIM}Fix:${C_RESET} $hint"
  MENU_CUR=0
  menu::pick "Details" "Enter to choose · q back" opts || { MENU_INFO=""; return; }
  MENU_INFO=""
  case ${acts[MENU_IDX]} in
    guide) settings::guide_api ;;
    fix)   settings::run_fix "$fix" ;;
  esac
}

# Explain an unavailable feature (capability name)
settings::explain_cap() {
  local cap=$1 h reason pkg fix
  h=$(device::cap_help "$cap"); IFS='|' read -r reason pkg fix <<<"$h"
  local nice
  case $cap in ai) nice="Nebula AI";; tts) nice="Voice";; sound) nice="UI sounds";; serve) nice="serve";; qr) nice="QR codes";;
    net) nice="Web commands";; storage) nice="Backup & restore";; fingerprint) nice="Fingerprint unlock";; *) nice=$cap;; esac
  settings::issue_detail "Unavailable: $nice" "This feature $reason." "${fix:+Run: $fix}" "$fix"
}

# ── features ────────────────────────────────────────────────────────────
settings::page_features() {
  local cur=0
  while :; do
    local -a items=() keys=()
    if device::cap tts; then
      items+=("🗣 Nebula AI voice"$'\t'"$(settings::_voice_on && settings::_state on || settings::_state off)"); keys+=(voice)
    else items+=("🗣 Nebula AI voice"$'\t'"unavailable — needs espeak"$'\td'); keys+=(cap:tts); fi
    if device::cap sound; then
      items+=("🔔 UI sounds"$'\t'"$(settings::_sound_on && settings::_state on || settings::_state off)"); keys+=(sounds)
    else items+=("🔔 UI sounds"$'\t'"unavailable — needs sox"$'\td'); keys+=(cap:sound); fi
    if device::cap ai; then items+=("💬 Plain-English commands"$'\t'"$(nl::mode)"$'\t'"$([[ $(nl::mode) == off ]] && echo d || echo g)"); keys+=(nl)
    else items+=("💬 Plain-English commands"$'\t'"unavailable — needs tgpt"$'\td'); keys+=(cap:ai); fi
    items+=("📐 Layout"$'\t'"${NEBULA_LAYOUT:-auto} · $(ui::cols)×$(ui::rows)"$'\t'); keys+=(layout)
    items+=("⚡ Compact startup"$'\t'"$(settings::_flag_on compact && settings::_state on || settings::_state off)"); keys+=(compact)
    items+=("🧭 Show tour next start"$'\t'"$([[ -f $NEBULA_CFG/.toured ]] && echo no || echo yes)"$'\td'); keys+=(tour)
    MENU_INFO=""; MENU_CUR=$cur
    menu::pick "🔧 Features" "Enter toggles · q back" items || return
    cur=$MENU_IDX
    case ${keys[cur]} in
      voice)   if settings::_voice_on; then export NEBULA_VOICE=0; echo 0 > "$NEBULA_CFG/voice"; else export NEBULA_VOICE=1; echo 1 > "$NEBULA_CFG/voice"; fi ;;
      sounds)  if settings::_sound_on; then export NEBULA_SOUNDS=0; echo 0 > "$NEBULA_CFG/sounds"; else export NEBULA_SOUNDS=1; echo 1 > "$NEBULA_CFG/sounds"; fi ;;
      nl)      case $(nl::mode) in ask) cmd::nl auto >/dev/null;; auto) cmd::nl off >/dev/null;; *) cmd::nl ask >/dev/null;; esac ;;
      layout)  case ${NEBULA_LAYOUT:-auto} in auto) cmd::layout phone >/dev/null;; phone) cmd::layout wide >/dev/null;; *) cmd::layout auto >/dev/null;; esac ;;
      compact) if settings::_flag_on compact; then rm -f "$NEBULA_CFG/compact"; else touch "$NEBULA_CFG/compact"; fi ;;
      tour)    if [[ -f $NEBULA_CFG/.toured ]]; then rm -f "$NEBULA_CFG/.toured"; else touch "$NEBULA_CFG/.toured"; fi ;;
      cap:*)   settings::explain_cap "${keys[cur]#cap:}" ;;
    esac
  done
}

# ── customize ───────────────────────────────────────────────────────────
settings::page_customize() {
  local cur=0
  while :; do
    local -a items=(
      "🎨 Prompt studio"$'\t'"$(prompt::current_preset)"$'\ty'
      "🏠 Home screen"$'\t'"$(home::load; echo "${HC[widgets]}" | cut -c1-24)"$'\td'
      "👤 Profile"$'\t'"$(profile::current)"$'\tg'
      "📊 Live status"$'\t\t'
    )
    MENU_INFO=""; MENU_CUR=$cur
    menu::pick "🎨 Customize" "Enter opens · q back" items || return
    cur=$MENU_IDX
    case $cur in
      0) prompt::studio ;;
      1) home::editor ;;
      2) local p; p=$(for x in $(profile::names); do printf '%-9s %s\n' "$x" "$(profile::desc "$x")"; done | pick::choose "Switch profile") && { printf '\033[H\033[2J'; profile::apply "${p%% *}"; menu::wait; } ;;
      3) printf '\033[H\033[2J'; cmd::status --live ;;
    esac
  done
}

# ── security ────────────────────────────────────────────────────────────
settings::page_security() {
  local cur=0
  while :; do
    local -a items=() keys=()
    local m; m=$(settings::_autolock_min)
    items+=("🔒 Login lock"$'\t'"$(settings::_flag_on no-lock && settings::_state off || settings::_state on)"); keys+=(lock)
    items+=("⏱ Auto-lock after idle"$'\t'"$([[ $m == 0 ]] && echo off || echo "$m min")"$'\t'"$([[ $m == 0 ]] && echo d || echo g)"); keys+=(autolock)
    if device::cap fingerprint; then
      items+=("👆 Fingerprint unlock"$'\t'"$(settings::_flag_on fingerprint && settings::_state on || settings::_state off)"); keys+=(fp)
    else items+=("👆 Fingerprint unlock"$'\t'"unavailable — needs Termux:API"$'\td'); keys+=(cap:fingerprint); fi
    items+=("🔑 Change password"$'\t\t'); keys+=(passwd)
    items+=("📜 Login history"$'\t\t'); keys+=(logins)
    MENU_INFO=""; MENU_CUR=$cur
    menu::pick "🔐 Security" "Enter toggles / opens · q back" items || return
    cur=$MENU_IDX
    case ${keys[cur]} in
      lock)
        if settings::_flag_on no-lock; then rm -f "$NEBULA_CFG/no-lock"
        else printf '\033[H\033[2J'; auth::confirm && { mkdir -p "$NEBULA_CFG"; touch "$NEBULA_CFG/no-lock"; }; fi ;;
      autolock)
        case $m in 0) m=1;; 1) m=5;; 5) m=10;; 10) m=30;; *) m=0;; esac
        echo "$m" > "$NEBULA_CFG/autolock" ;;
      fp)
        if settings::_flag_on fingerprint; then rm -f "$NEBULA_CFG/fingerprint"
        else printf '\033[H\033[2J'; cmd::fingerprint on; menu::wait; fi ;;
      passwd)  printf '\033[H\033[2J'; cmd::passwd; menu::wait ;;
      logins)  printf '\033[H\033[2J'; cmd::logins 20; menu::wait ;;
      cap:*)   settings::explain_cap "${keys[cur]#cap:}" ;;
    esac
  done
}

# ── Termux:API guide (for when the Play Store isn't an option) ──────────
settings::guide_api() {
  local cur=0 src arch_apk
  src=$(device::get termux_source); arch_apk=$(device::apk_arch)
  while :; do
    local -a items=(
      $'1  What Termux:API gives you\t'
      $'2  Get the app (F-Droid / GitHub / Play)\t'
      $'3  Phone blocks APK installs? Options\t'
      $'4  After installing: finish setup\t'
      $'5  No-API mode: what still works\t'
      $'🔄 Re-scan now\t'
    )
    MENU_INFO="${C_DIM}Your Termux: ${src}  ·  CPU: $(device::get arch)${C_RESET}"; MENU_CUR=$cur
    menu::pick "📖 Termux:API without the Play Store" "Enter to read · q back" items || { MENU_INFO=""; return; }
    cur=$MENU_IDX; MENU_INFO=""
    printf '\033[H\033[2J'
    case $cur in
      0) cat <<EOF
${C_CYAN}${C_BOLD}What Termux:API gives you${C_RESET}

It's two pieces: the ${C_BOLD}termux-api${C_RESET} package and the
separate ${C_BOLD}Termux:API${C_RESET} Android app. Together they let
Termux use:

  🔋 battery info
  🔔 phone notifications (reminders)
  👆 fingerprint unlock
  📶 Wi-Fi details · 🗣 phone voice · 📋 clipboard

Without it Nebula still works. Those features just stay
hidden (see item 5).
EOF
        ;;
      1) cat <<EOF
${C_CYAN}${C_BOLD}Get the app${C_RESET}

${C_YELLOW}Rule #1:${C_RESET} Termux:API must come from the ${C_BOLD}same source${C_RESET}
as Termux (yours: ${C_BOLD}${src}${C_RESET}). Android treats apps
signed differently as strangers, so mixing sources fails.

  • F-Droid   f-droid.org/packages/com.termux.api
  • GitHub    github.com/termux/termux-api/releases
              pick the .apk for your CPU: ${C_BOLD}${arch_apk}${C_RESET}
              (or the universal one)
  • Google Play: only if your Termux is the Play build

Then in Termux:  ${C_GREEN}pkg install termux-api${C_RESET}
EOF
        ;;
      2) cat <<EOF
${C_CYAN}${C_BOLD}Phone blocks APK installs?${C_RESET}

Some phones only allow the Play Store (school/work
profiles, parental controls, some carrier locks).

 1. Settings → Apps → Special access → Install unknown
    apps → allow your browser/file manager once.
    If that's missing or greyed out, a policy manages
    the phone and only the options below can work.

 2. ${C_BOLD}ADB from a computer${C_RESET} (Developer options → USB
    debugging):   adb install termux-api.apk
    Often works even when unknown-sources is hidden.

 3. ${C_BOLD}No computer:${C_RESET} on Android 11+ turn on Wireless
    debugging, then in Termux:
      pkg install android-tools
    and use adb against your own phone.

 4. Can't do any of these? Use No-API mode (item 5).
EOF
        ;;
      3) cat <<EOF
${C_CYAN}${C_BOLD}After installing${C_RESET}

 1. In Termux:      pkg install termux-api
 2. Open the ${C_BOLD}Termux:API${C_RESET} app once.
 3. Android Settings → Apps → Termux:API → Permissions
    → allow what you need (notifications, etc.).
 4. Back here: pick ${C_BOLD}Re-scan now${C_RESET}.

Battery, notifications and fingerprint switch on by
themselves once the scan sees the app answering.
EOF
        ;;
      4) cat <<EOF
${C_CYAN}${C_BOLD}No-API mode${C_RESET}

Nebula adapts instead of breaking:

  ${C_GREEN}✔${C_RESET} Status: battery is read from the system if
    Android lets Termux see it; otherwise that row is
    simply left out.
  ${C_GREEN}✔${C_RESET} Network row uses system tools for your IP.
  ${C_GREEN}✔${C_RESET} Reminders: no phone notification, but they pop
    up (and speak, with espeak) at your next prompt.
  ${C_GREEN}✔${C_RESET} Voice: espeak instead of phone TTS.
  ${C_RED}✖${C_RESET} Fingerprint unlock: hidden. Your password works.
EOF
        ;;
      5) device::scan; printf "  ${C_GREEN}✔${C_RESET} Scan complete: %s\n" "$(device::summary_line)" ;;
    esac
    menu::wait
  done
}

# ── install missing ─────────────────────────────────────────────────────
settings::page_install() {
  local pk; pk=$(device::fix_packages)
  printf '\033[H\033[2J'
  if [[ -z $pk ]]; then printf "${C_GREEN}✔ Nothing missing — all fixable packages are installed.${C_RESET}\n"; menu::wait; return; fi
  printf "${C_BOLD}Missing:${C_RESET} %s\n\n" "${pk//,/, }"
  bash "$NEBULA_HOME/install/install.sh" --deps-only --want "$pk"
  device::scan --quiet; menu::wait
}

# ── main ────────────────────────────────────────────────────────────────
cmd::settings() {
  if [[ ! -t 0 || ! -t 1 ]]; then cmd::device; return; fi
  device::ensure_scan --quiet
  local cur=0
  while :; do
    local -a items=() keys=()
    local e w i; read -r e w i < <(device::issue_counts)
    local health="all good" hcol=g
    (( e + w > 0 )) && { health="${e} error(s) · ${w} warning(s)"; hcol=y; (( e > 0 )) && hcol=r; }
    local m; m=$(settings::_autolock_min)
    local pk; pk=$(device::fix_packages)

    items+=("📱 Device"$'\t'"$(device::summary_line)"$'\td'); keys+=(device)
    items+=("🩺 Health"$'\t'"$health"$'\t'"$hcol"); keys+=(health)
    items+=("🎨 Customize"$'\t'"prompt · home · profiles"$'\td'); keys+=(customize)
    items+=("🔧 Features"$'\t\t'); keys+=(features)
    items+=("🔐 Security"$'\t'"lock $(settings::_flag_on no-lock && echo off || echo on) · auto $([[ $m == 0 ]] && echo off || echo "${m}m")"$'\td'); keys+=(security)
    [[ -n $pk ]] && { items+=("📦 Install missing"$'\t'"$(tr ',' '\n' <<<"$pk" | grep -c '') package(s)"$'\ty'); keys+=(install); }
    device::_api_ok || { items+=("📖 Get Termux:API"$'\t'"without the Play Store"$'\td'); keys+=(guide); }
    items+=("🔄 Re-scan device"$'\t\t'); keys+=(scan)

    MENU_INFO=""; MENU_CUR=$cur
    menu::pick "⚙ Nebula Settings" "↑↓ move · Enter open · q close" items || break
    cur=$MENU_IDX
    case ${keys[cur]} in
      device)   settings::page_device ;;
      health)   settings::page_health ;;
      customize) settings::page_customize ;;
      features) settings::page_features ;;
      security) settings::page_security ;;
      install)  settings::page_install ;;
      guide)    settings::guide_api ;;
      scan)     printf '\033[H\033[2J'; device::scan; printf "  ${C_GREEN}✔${C_RESET} Scan complete.\n"; sleep 0.8 ;;
    esac
  done
  printf '\033[H\033[2J'
}

# Plain-text device report (non-interactive / `nebula device`)
cmd::device() {
  device::ensure_scan --quiet
  device::info_text
  local e w i; read -r e w i < <(device::issue_counts)
  printf "\n"
  if (( e + w + i == 0 )); then printf "${C_GREEN}✔ No issues.${C_RESET}\n"
  else
    local sev id title why hint fix pkg
    while IFS='|' read -r sev id title why hint fix pkg; do
      [[ -z $sev ]] && continue
      viz::wrap "$(( $(ui::cols) - 1 ))" "  $(settings::_sev_icon "$sev") " "    " "$title"
    done < <(device::issues)
    ui::hint "Run: settings   to fix these."
  fi
}

cmd::scan() {
  device::scan
  local e w i; read -r e w i < <(device::issue_counts)
  ui::say_status OK "Scan complete: $(device::summary_line)"
  (( e + w > 0 )) && ui::say_status WARN "$e error(s), $w warning(s). Run: settings" || ui::say_status OK "No problems found."
}
