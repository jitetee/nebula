#!/data/data/com.termux/files/usr/bin/env bash
# nebula — device awareness: scan hardware/OS/Termux, decide which features
# work, hide the ones that can't, and explain why (see `settings`).
#
#   data/device.conf   cached scan result (key=value)
#   data/hidden.txt    commands the device can't run (zsh completion reads it)

device::_conf() { printf '%s' "$NEBULA_CFG/device.conf"; }

device::get() {  # device::get <key>
  local f; f=$(device::_conf); [[ -f $f ]] || return 1
  awk -F= -v k="$1" '$1==k{sub(/^[^=]*=/,""); print; exit}' "$f"
}

device::_prop() { command -v getprop >/dev/null 2>&1 && getprop "$1" 2>/dev/null; }

# ── scan ────────────────────────────────────────────────────────────────
device::scan() {
  local quiet=0; [[ ${1:-} == --quiet ]] && quiet=1
  (( ! quiet )) && [[ -t 1 ]] && printf '  🔍 Scanning your device…\r'
  mkdir -p "$NEBULA_CFG"

  local arch bits android sdk brand model cores ram_kb free_mb
  arch=$(uname -m 2>/dev/null); bits=$(getconf LONG_BIT 2>/dev/null || echo 64)
  android=$(device::_prop ro.build.version.release); sdk=$(device::_prop ro.build.version.sdk)
  brand=$(device::_prop ro.product.brand); model=$(device::_prop ro.product.model)
  [[ -z $model ]] && model=$(uname -n 2>/dev/null)
  cores=$(nproc 2>/dev/null || echo 1)
  ram_kb=$(awk '/^MemTotal:/{print $2}' /proc/meminfo 2>/dev/null)
  free_mb=$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2{printf "%d", $4/1024}')

  local src=${TERMUX_APK_RELEASE:-unknown}
  case $src in F_DROID) src=F-Droid;; GITHUB) src=GitHub;; GOOGLE_PLAY) src="Google Play";; *) src=unknown;; esac

  # Termux:API = package + Android app. Probe it for real (6s cap).
  local api_pkg=0 api_ok=0 api_reason=nopkg out
  if command -v termux-battery-status >/dev/null 2>&1; then
    api_pkg=1; api_reason=noapp
    out=$(timeout 6 termux-battery-status 2>/dev/null)
    [[ $out == *percentage* ]] && { api_ok=1; api_reason=ok; }
  fi

  local storage_ok=0 online=0 rooted=0 weak=0
  [[ -w /sdcard || -w $HOME/storage/shared ]] && storage_ok=1
  command -v curl >/dev/null 2>&1 && curl -sI --max-time 4 https://1.1.1.1 >/dev/null 2>&1 && online=1
  command -v su >/dev/null 2>&1 && rooted=1
  [[ $ram_kb =~ ^[0-9]+$ ]] && (( ram_kb < 1500000 )) && weak=1

  {
    echo "scanned=$(date +%s)"
    echo "arch=$arch"; echo "bits=$bits"; echo "android=$android"; echo "sdk=$sdk"
    echo "model=${brand:+$brand }$model"; echo "cores=$cores"; echo "ram_kb=${ram_kb:-0}"
    echo "free_mb=${free_mb:-0}"; echo "termux_version=${TERMUX_VERSION:-unknown}"
    echo "termux_source=$src"; echo "api_pkg=$api_pkg"; echo "api_ok=$api_ok"
    echo "api_reason=$api_reason"; echo "storage_ok=$storage_ok"; echo "online=$online"
    echo "rooted=$rooted"; echo "weak=$weak"
  } > "$(device::_conf).tmp" && mv "$(device::_conf).tmp" "$(device::_conf)"

  # Weak device? Switch to the compact startup once (user can turn it off).
  if (( weak )) && [[ ! -f $NEBULA_CFG/.compact_auto ]]; then
    touch "$NEBULA_CFG/compact" "$NEBULA_CFG/.compact_auto"
  fi
  device::refresh_hidden
  (( ! quiet )) && [[ -t 1 ]] && printf '\033[2K\r'
  return 0
}

# Rescan when there's no cache, it's >1 day old, or the API package appeared/vanished.
device::ensure_scan() {
  local t now; now=$(date +%s); t=$(device::get scanned)
  local had; had=$(device::get api_pkg); local has=0
  command -v termux-battery-status >/dev/null 2>&1 && has=1
  if [[ -z $t ]] || (( now - t > 86400 )) || [[ $had != "$has" ]]; then
    device::scan "$@"
    return 0
  fi
  return 1
}

# ── capabilities ────────────────────────────────────────────────────────
device::_api_ok() { [[ $(device::get api_ok) == 1 ]] && command -v termux-battery-status >/dev/null 2>&1; }

device::cap() {  # device::cap <name> → 0 if this device can do it
  case $1 in
    ai)          command -v tgpt >/dev/null 2>&1 ;;
    tts)         voice::onnx_ready 2>/dev/null || command -v espeak >/dev/null 2>&1 || command -v festival >/dev/null 2>&1 || { device::_api_ok && command -v termux-tts-speak >/dev/null 2>&1; } ;;
    sound)       command -v play >/dev/null 2>&1 ;;
    serve)       command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 ;;
    qr)          command -v qrencode >/dev/null 2>&1 ;;
    json)        command -v python3 >/dev/null 2>&1 ;;
    net)         command -v curl >/dev/null 2>&1 ;;
    storage)     [[ -w /sdcard || -w $HOME/storage/shared ]] ;;
    fingerprint) device::_api_ok && command -v termux-fingerprint >/dev/null 2>&1 ;;
    notify)      device::_api_ok && command -v termux-notification >/dev/null 2>&1 ;;
    battery)     device::_api_ok || [[ -r /sys/class/power_supply/battery/capacity ]] ;;
    *)           return 0 ;;
  esac
}

# command → capability it needs ('' = always available)
device::cmd_cap() {
  case $1 in
    ask|joke|fact|chat|explain|fix|summarize|translate|tell) echo ai ;;
    voice)                                              echo tts ;;
    serve)                                              echo serve ;;
    qr)                                                 echo qr ;;
    crypto|sports)                                      echo json ;;
    weather|news|ip|define|meme|bible)                  echo net ;;
    backup|restore)                                     echo storage ;;
    fingerprint)                                        echo fingerprint ;;
    *) echo "" ;;
  esac
}
DEVICE_GATED="ask joke fact chat explain fix summarize translate tell voice serve qr weather news crypto sports ip define meme bible backup restore fingerprint"

# One-line "what's missing" for a capability: <reason>|<package or empty>|<fix command or empty>
device::cap_help() {
  case $1 in
    ai)          echo "needs the tgpt package|tgpt|pkg install -y tgpt" ;;
    tts)         echo "needs a voice engine (espeak)|espeak|pkg install -y espeak" ;;
    sound)       echo "needs sox for UI sounds|sox|pkg install -y sox" ;;
    serve)       echo "needs python|python|pkg install -y python" ;;
    qr)          echo "needs qrencode|qrencode|pkg install -y qrencode" ;;
    net)         echo "needs curl|curl|pkg install -y curl" ;;
    json)        echo "needs python|python|pkg install -y python" ;;
    storage)     echo "needs storage permission||termux-setup-storage" ;;
    fingerprint) echo "needs Termux:API (package + Android app)|termux-api|@api" ;;
    notify)      echo "needs Termux:API (package + Android app)|termux-api|@api" ;;
    battery)     echo "needs Termux:API (package + Android app)|termux-api|@api" ;;
    *)           echo "||" ;;
  esac
}

# Is this command blocked on this device? Prints why and returns 1 if so.
device::gate() {
  local c=$1 cap why
  cap=$(device::cmd_cap "$c"); [[ -z $cap ]] && return 0
  device::cap "$cap" && return 0
  why=$(device::cap_help "$cap"); why=${why%%|*}
  printf '  %s⚠ "%s" isn'"'"'t available on this device — %s.%s\n' "${C_YELLOW:-}" "$c" "$why" "${C_RESET:-}" | ui::wrap "$(( $(ui::cols) - 1 ))" 4
  printf '  %sOpen Settings to fix it:%s settings\n' "${C_DIM:-}" "${C_RESET:-}"
  return 1
}

# Names of commands that can't run here (space separated)
device::hidden() {
  local c cap out=""
  for c in $DEVICE_GATED; do
    cap=$(device::cmd_cap "$c"); device::cap "$cap" || out+="$c "
  done
  printf '%s' "$out"
}
device::refresh_hidden() { mkdir -p "$NEBULA_CFG"; device::hidden > "$NEBULA_CFG/hidden.txt"; }

# Battery without hard-requiring Termux:API → "pct|status|temp" or return 1
device::battery() {
  local json pct st temp
  if device::_api_ok; then
    json=$(timeout 6 termux-battery-status 2>/dev/null)
    pct=$(grep -o '"percentage": *[0-9]*' <<<"$json" | grep -o '[0-9]*$')
    st=$(grep -o '"status": *"[A-Z_]*"' <<<"$json" | cut -d'"' -f4)
    temp=$(grep -o '"temperature": *[0-9.]*' <<<"$json" | grep -o '[0-9.]*$')
    [[ -n $pct ]] && { echo "$pct|${st,,}|$temp"; return 0; }
  fi
  local d=/sys/class/power_supply/battery
  if [[ -r $d/capacity ]]; then
    pct=$(<"$d/capacity"); st=$(cat "$d/status" 2>/dev/null); temp=$(cat "$d/temp" 2>/dev/null)
    [[ $temp =~ ^[0-9]+$ ]] && temp=$(awk -v t="$temp" 'BEGIN{printf "%.1f", t/10}')
    echo "$pct|${st,,}|$temp"; return 0
  fi
  return 1
}

# ── human text ──────────────────────────────────────────────────────────
device::arch_label() {
  case $(device::get arch) in
    aarch64|arm64) echo "arm64 (aarch64, 64-bit ARM)" ;;
    armv7l|armv8l|arm) echo "armv7l (32-bit ARM)" ;;
    x86_64) echo "x86_64 (Intel/AMD or emulator)" ;;
    i686|i386) echo "x86 (32-bit)" ;;
    *) echo "$(device::get arch)" ;;
  esac
}
device::apk_arch() {
  case $(device::get arch) in
    aarch64|arm64) echo arm64-v8a ;; armv7l|armv8l|arm) echo armeabi-v7a ;;
    x86_64) echo x86_64 ;; i686|i386) echo x86 ;; *) echo "your CPU's build" ;;
  esac
}
device::summary_line() {
  printf '%s · Android %s · %s' "$(device::get model)" "$(device::get android)" "$(device::get arch)"
}

# ── issues: sev|id|title|why|hint|fixcmd|pkg ────────────────────────────
# sev: error | warn | info.  fixcmd "@api" opens the Termux:API guide.
device::issues() {
  local arch bits sdk src ram free
  arch=$(device::get arch); bits=$(device::get bits); sdk=$(device::get sdk)
  src=$(device::get termux_source); ram=$(device::get ram_kb); free=$(device::get free_mb)

  command -v zsh >/dev/null 2>&1 || echo "error|zsh|zsh is not installed|Nebula's shell UI runs on zsh.|Install zsh, then restart Termux.|pkg install -y zsh|zsh"
  local p
  for p in git curl openssl-tool gawk; do
    local bin=$p; [[ $p == openssl-tool ]] && bin=openssl; [[ $p == gawk ]] && bin=awk
    command -v "$bin" >/dev/null 2>&1 || echo "warn|core-$p|$p is missing|Needed for updates, web commands or password hashing.|Install it.|pkg install -y $p|$p"
  done
  command -v tgpt >/dev/null 2>&1 || {
    if command -v apt-cache >/dev/null 2>&1 && apt-cache policy tgpt 2>/dev/null | grep -q 'Candidate: (none)'; then
      echo "info|tgpt-arch|Nebula AI isn't packaged for $arch|The tgpt package has no build for this CPU in your repo.|Nebula AI commands stay hidden. Try: pkg update, or a different mirror (termux-change-repo).|termux-change-repo|"
    else
      echo "warn|tgpt|Nebula AI is off (tgpt not installed)|ask, chat, explain, fix, summarize and translate need tgpt.|Install tgpt to switch them on.|pkg install -y tgpt|tgpt"
    fi
  }

  # Termux:API
  local reason; reason=$(device::get api_reason)
  case $reason in
    nopkg) echo "warn|api|Termux:API isn't set up|Battery, notifications and fingerprint need it. Nebula works without them (see No-API mode).|Install the termux-api package AND the Termux:API Android app (same source as Termux).|@api|termux-api" ;;
    noapp) echo "warn|api-app|Termux:API app not responding|The package is installed but the Android app isn't answering. It's missing, or lacks permission.|Install the Termux:API app from the SAME source as Termux, open it once, then re-scan.|@api|" ;;
  esac
  [[ $src == "Google Play" ]] && echo "info|play|Termux is the Google Play build|Play builds are a separate, restricted variant and Termux:API must come from the same store.|If something behaves oddly, the F-Droid or GitHub build is the reference one.|@api|"
  [[ $src == unknown ]] && echo "info|source|Can't tell where Termux came from|Termux and Termux:API must be from the same source or Android treats them as strangers.|Check in the Termux:API guide.|@api|"

  [[ $(device::get storage_ok) == 1 ]] || echo "warn|storage|Shared storage isn't accessible|backup and restore save to /sdcard/Nebula.|Grant the storage permission.|termux-setup-storage|"
  [[ $(device::get online) == 1 ]] || echo "info|offline|No internet right now|Weather, news and Nebula AI need a connection.|Check Wi-Fi or mobile data.||"
  [[ $free =~ ^[0-9]+$ ]] && (( free < 500 )) && echo "warn|lowdisk|Low storage (${free} MB free)|Packages and backups may fail.|Free some space or run: pkg clean|pkg clean|"

  [[ $sdk =~ ^[0-9]+$ ]] && (( sdk < 24 )) && echo "warn|oldandroid|Android $(device::get android) is very old|Current Termux builds need Android 7+.|Use the legacy Termux builds, or upgrade the phone.||"
  (( bits == 32 )) && echo "info|arch32|32-bit CPU ($arch)|Some packages have no build for 32-bit ARM and everything is slower.|Missing packages are flagged in the picker (nebula deps).||"
  [[ $ram =~ ^[0-9]+$ ]] && (( ram < 2000000 )) && echo "info|lowram|Low memory ($((ram/1024)) MB)|Heavy tools (ffmpeg, proot-distro) may be killed by Android.|Keep the package list small.||"

  # Can't be detected from inside Termux, so always offer it
  echo "info|battopt|Android may stop Termux in the background|Reminders and servers die when the phone sleeps or Termux is 'optimized'.|Settings → Apps → Termux → Battery → Unrestricted. Also run: termux-wake-lock|termux-wake-lock|"
}

# Issue counts → "errors warns infos"
device::issue_counts() {
  device::issues | awk -F'|' '{c[$1]++} END{printf "%d %d %d", c["error"], c["warn"], c["info"]}'
}

# Packages that would fix issues (comma list)
device::fix_packages() {
  device::issues | awk -F'|' '$7!=""{print $7}' | sort -u | paste -sd, -
}
