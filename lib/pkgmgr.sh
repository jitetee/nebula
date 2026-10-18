#!/data/data/com.termux/files/usr/bin/env bash
# nebula — `nebula install <tool>`: finds the best way to install something
# (pkg, pip, npm, cargo, go, gem), installs prerequisites, shows live progress,
# self-heals common failures and falls back to the next method.

PM_VERBOSE=0; PM_YES=0; PM_FORCE=0; PM_VIA=""

pm::registry() { grep -v '^#' "$NEBULA_HOME/assets/registry.txt"; }

pm::find() {  # pm::find <name-or-alias> → sets PM_NAME PM_ALIASES PM_METHODS PM_CAT PM_DESC
  local q=${1,,} n al m c d
  while IFS='|' read -r n al m c d; do
    if [[ $q == "${n,,}" ]] || [[ " ${al,,} " == *" $q "* ]]; then
      PM_NAME=$n; PM_ALIASES=$al; PM_METHODS=$m; PM_CAT=$c; PM_DESC=$d; return 0
    fi
  done < <(pm::registry)
  return 1
}

declare -gA PM_HAVE_CACHE=()
pm::have() {  # does this manager actually RUN here? (cached; pm::rehash clears it)
  local m=$1
  [[ -n ${PM_HAVE_CACHE[$m]:-} ]] && return $(( 1 - PM_HAVE_CACHE[$m] ))
  local ok=1
  case $m in
    pkg)   command -v pkg >/dev/null 2>&1 || command -v apt-get >/dev/null 2>&1 && ok=0 ;;
    pip)   python3 -m pip --version >/dev/null 2>&1 && ok=0 ;;
    npm)   command -v npm >/dev/null 2>&1 && npm --version >/dev/null 2>&1 && ok=0 ;;
    cargo) command -v cargo >/dev/null 2>&1 && cargo --version >/dev/null 2>&1 && ok=0 ;;
    go)    command -v go >/dev/null 2>&1 && go version >/dev/null 2>&1 && ok=0 ;;
    gem)   command -v gem >/dev/null 2>&1 && gem --version >/dev/null 2>&1 && ok=0 ;;
  esac
  PM_HAVE_CACHE[$m]=$(( 1 - ok ))
  return $ok
}
pm::rehash() { PM_HAVE_CACHE=(); hash -r; }
pm::prereq() {  # manager → package that provides it
  case $1 in pip) echo python-pip;; npm) echo nodejs-lts;; cargo) echo rust;; go) echo golang;; gem) echo ruby;; esac
}

pm::cmd() {  # pm::cmd <mgr> <target> [extra]
  local t=${2//+/ }
  case $1 in
    pkg)   echo "pkg install -y $t" ;;
    pip)   echo "python3 -m pip install $t ${3:-}" ;;
    npm)   echo "npm install -g $t ${3:-}" ;;
    cargo) echo "cargo install $t" ;;
    go)    echo "go install $t@latest" ;;
    gem)   echo "gem install $t" ;;
  esac
}
pm::uncmd() {
  local t=${2//+/ }
  case $1 in
    pkg) echo "pkg uninstall -y $t" ;; pip) echo "python3 -m pip uninstall -y $t ${3:-}" ;;
    npm) echo "npm uninstall -g $t" ;; cargo) echo "cargo uninstall $t" ;; gem) echo "gem uninstall -x $t" ;;
  esac
}

pm::is_installed() {  # pm::is_installed <mgr> <target>
  local t=${2%%+*}
  case $1 in
    pkg) local p; for p in ${2//+/ }; do dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q 'install ok installed' || return 1; done; return 0 ;;
    pip) pm::have pip && python3 -m pip show "$t" >/dev/null 2>&1 ;;
    npm) pm::have npm && npm ls -g --depth=0 "$t" >/dev/null 2>&1 ;;
    *)   return 1 ;;
  esac
}

# ── live progress runner ────────────────────────────────────────────────
# pm::run <label> <logfile> <command>   → exit code of the command
pm::run() {
  local label=$1 log=$2 cmd=$3
  mkdir -p "$(dirname "$log")"; printf '$ %s\n' "$cmd" >> "$log"
  if (( PM_VERBOSE )); then
    printf "  ${C_DIM}\$ %s${C_RESET}\n" "$cmd"
    DEBIAN_FRONTEND=noninteractive bash -c "$cmd" 2>&1 | tee -a "$log"; return "${PIPESTATUS[0]}"
  fi
  if [[ ! -t 1 ]]; then DEBIAN_FRONTEND=noninteractive bash -c "$cmd" >>"$log" 2>&1; return $?; fi

  DEBIAN_FRONTEND=noninteractive bash -c "$cmd" >>"$log" 2>&1 &
  local pid=$! f=0 start=$SECONDS pct="" last="" cols sp=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏') el
  cols=$(ui::cols)
  printf '\033[?25l\n\n\033[2A'
  while kill -0 "$pid" 2>/dev/null; do
    if (( f % 4 == 0 )); then
      local tail_; tail_=$(tail -c 700 "$log" 2>/dev/null | tr '\r' '\n' | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g')
      last=$(grep -v '^[[:space:]]*$' <<<"$tail_" | tail -1)
      pct=$(grep -o '[0-9]\{1,3\}%' <<<"$tail_" | tail -1 | tr -d %)
    fi
    el=$(( SECONDS - start ))
    local bar=""; [[ -n $pct && $pct -le 100 ]] && bar=" $(viz::bar "$pct" 100 12 "$C_CYAN") ${pct}%"
    printf '\r\033[2K  %s%s%s %s%s  %s%d:%02d%s\n\033[2K  %s↳ %s%s\033[1A\r' \
      "$C_CYAN" "${sp[f % 10]}" "$C_RESET" "$label" "$bar" "$C_DIM" $((el/60)) $((el%60)) "$C_RESET" \
      "$C_DIM" "$(viz::trunc "$last" $((cols-6)))" "$C_RESET"
    f=$((f+1)); sleep 0.12
  done
  wait "$pid"; local rc=$?
  printf '\r\033[2K\n\033[2K\033[1A\r\033[?25h'
  return $rc
}

# ── self-healing ────────────────────────────────────────────────────────
# pm::heal <mgr> <log> → 0 if something was fixed and a retry makes sense
pm::heal() {
  local mgr=$1 log=$2 txt; txt=$(tail -n 60 "$log" 2>/dev/null)
  case $mgr in
    pkg)
      if (( ! ${PM_REFRESHED:-0} )) && grep -qiE 'unable to locate package|404|failed to fetch|hash sum mismatch|no such file or directory.*lists' <<<"$txt"; then
        PM_REFRESHED=1
        ui::say_status INFO "Package lists look stale — refreshing, then retrying"
        pm::run "Refreshing package lists" "$log" "pkg update -y"; return 0
      fi
      if grep -qi 'dpkg was interrupted' <<<"$txt"; then
        ui::say_status INFO "Repairing an interrupted install"; pm::run "Repairing dpkg" "$log" "dpkg --configure -a"; return 0
      fi
      if grep -qi 'could not get lock' <<<"$txt"; then ui::say_status INFO "Another package job is running — waiting"; sleep 4; return 0; fi ;;
    pip)
      if grep -qi 'externally-managed-environment' <<<"$txt"; then
        ui::say_status INFO "Python is 'externally managed' — retrying with --break-system-packages"; PM_EXTRA="--break-system-packages"; return 0
      fi
      if grep -qiE 'failed building wheel|command .*(clang|gcc).* failed|error: .*compil|could not build wheels' <<<"$txt"; then
        ui::say_status INFO "A native build failed — installing build tools, then retrying"
        pm::run "Installing build tools" "$log" "pkg install -y clang make pkg-config libffi openssl"; return 0
      fi ;;
    npm)
      if grep -qiE 'gyp ERR|node-gyp' <<<"$txt"; then
        ui::say_status INFO "node-gyp needs build tools — installing, then retrying"
        pm::run "Installing build tools" "$log" "pkg install -y python make clang binutils"; return 0
      fi
      if grep -qE 'EEXIST|ENOTEMPTY' <<<"$txt"; then ui::say_status INFO "Leftover files — retrying with --force"; PM_EXTRA="--force"; return 0; fi ;;
  esac
  return 1
}

# ── discovery for tools not in the database ─────────────────────────────
pm::closest() {  # word → up to 4 close names from the registry
  pm::registry | awk -F'|' -v w="$1" '
    function lev(a,b,  la,lb,i,j,c,p,m,cur) { la=length(a); lb=length(b); for(j=0;j<=lb;j++)p[j]=j
      for(i=1;i<=la;i++){cur[0]=i; for(j=1;j<=lb;j++){c=(substr(a,i,1)==substr(b,j,1))?0:1; m=p[j]+1; if(cur[j-1]+1<m)m=cur[j-1]+1; if(p[j-1]+c<m)m=p[j-1]+c; cur[j]=m} for(j=0;j<=lb;j++)p[j]=cur[j]} return p[lb] }
    { n=$1; if (index(n,w) || index(w,n) || lev(w,n)<=2) print n }' | head -4 | paste -sd' ' -
}

pm::discover() {  # unknown name → sets PM_METHODS (or returns 1)
  local n=$1 found=() note=""
  ui::say_status INFO "'$n' isn't in Nebula's database — searching pkg, pip and npm…"
  if command -v apt-cache >/dev/null 2>&1 && apt-cache show "$n" >/dev/null 2>&1; then found+=("pkg:$n"); printf "    ${C_GREEN}✔${C_RESET} pkg\n"; else printf "    ${C_DIM}✖ pkg${C_RESET}\n"; fi
  if pm::have pip; then
    if timeout 25 python3 -m pip index versions "$n" >/dev/null 2>&1; then found+=("pip:$n"); printf "    ${C_GREEN}✔${C_RESET} pip\n"; else printf "    ${C_DIM}✖ pip${C_RESET}\n"; fi
  else printf "    ${C_DIM}– pip (not installed)${C_RESET}\n"; fi
  if pm::have npm; then
    if timeout 25 npm view "$n" version >/dev/null 2>&1; then found+=("npm:$n"); printf "    ${C_GREEN}✔${C_RESET} npm\n"; else printf "    ${C_DIM}✖ npm${C_RESET}\n"; fi
  else printf "    ${C_DIM}– npm (not installed)${C_RESET}\n"; fi
  if (( ${#found[@]} == 0 )); then
    ui::say_status ERR "Couldn't find '$n' anywhere."
    local c; c=$(pm::closest "$n"); [[ -n $c ]] && ui::say_status INFO "Did you mean: $c"
    return 1
  fi
  PM_NAME=$n; PM_METHODS=$(IFS=';'; echo "${found[*]}"); PM_DESC="found by search"; PM_CAT=""; return 0
}

# ── install one tool ────────────────────────────────────────────────────
pm::install_one() {
  local name=$1
  PM_EXTRA=""; PM_REFRESHED=0
  if ! pm::find "$name"; then pm::discover "$name" || return 1; fi

  local methods=() m
  IFS=';' read -ra methods <<<"$PM_METHODS"
  if [[ -n $PM_VIA ]]; then
    local f=(); for m in "${methods[@]}"; do [[ ${m%%:*} == "$PM_VIA" ]] && f+=("$m"); done
    (( ${#f[@]} )) || { ui::say_status ERR "$PM_NAME isn't available via $PM_VIA (options: ${methods[*]%%:*})"; return 1; }
    methods=("${f[@]}")
  fi

  # already there?
  if (( ! PM_FORCE )); then
    for m in "${methods[@]}"; do
      if pm::is_installed "${m%%:*}" "${m#*:}"; then
        ui::say_status OK "$PM_NAME is already installed (via ${m%%:*}). Use --force to reinstall."; return 0
      fi
    done
  fi

  # plan card
  local first=${methods[0]} mgr=${methods[0]%%:*}
  printf "\n${C_CYAN}${C_BOLD}📦 %s${C_RESET}  ${C_DIM}%s${C_RESET}\n" "$PM_NAME" "$PM_DESC"
  local why
  if (( ${#methods[@]} == 1 )); then why="only available as a $mgr package"
  elif [[ $mgr == pkg ]]; then why="pkg is prebuilt for your CPU — fastest, and updated by pkg upgrade"
  else why="best option on this device"; fi
  printf "   ${C_DIM}Plan:${C_RESET} %s ${C_DIM}(%s)${C_RESET}\n" "$(pm::cmd "$mgr" "${first#*:}")" "$why"
  (( ${#methods[@]} > 1 )) && printf "   ${C_DIM}Fallbacks:${C_RESET} %s\n" "$(for m in "${methods[@]:1}"; do printf '%s ' "${m%%:*}"; done)"

  # prerequisites for every method we might need
  local missing=()
  for m in "${methods[@]}"; do
    local mg=${m%%:*}
    pm::have "$mg" || { local pq; pq=$(pm::prereq "$mg"); [[ -n $pq ]] && [[ " ${missing[*]} " != *" $pq "* ]] && missing+=("$pq"); }
  done
  # only the *first* missing manager is required up-front; others are fallbacks
  local need_first=""; pm::have "$mgr" || need_first=$(pm::prereq "$mgr")
  [[ -n $need_first ]] && printf "   ${C_YELLOW}Needs first:${C_RESET} %s ${C_DIM}(provides %s)${C_RESET}\n" "$need_first" "$mgr"

  (( PM_YES )) || ui::confirm "Install now?" Y || { ui::say_status INFO "Skipped."; return 0; }

  local ts; ts=$(date +%Y%m%d-%H%M%S); local log="$NEBULA_CFG/logs/install-${PM_NAME//[^A-Za-z0-9._-]/_}-$ts.log"
  mkdir -p "$NEBULA_CFG/logs"; : > "$log"
  local t0=$SECONDS ok=0 attempt=0

  for m in "${methods[@]}"; do
    mgr=${m%%:*}; local target=${m#*:}
    if ! pm::have "$mgr"; then
      local pq; pq=$(pm::prereq "$mgr")
      if [[ -n $pq ]]; then
        ui::say_status INFO "Installing $pq first (provides $mgr)"
        pm::run "Installing $pq" "$log" "pkg install -y $pq" || { ui::say_status WARN "Couldn't install $pq — trying the next method"; continue; }
        pm::rehash
        pm::have "$mgr" || { ui::say_status WARN "$mgr still not available"; continue; }
      else continue; fi
    fi
    attempt=$((attempt+1)); PM_EXTRA=""
    (( attempt > 1 )) && ui::say_status INFO "Trying another way: $mgr"
    local tries=0 rc
    while (( tries < 3 )); do
      tries=$((tries+1))
      pm::run "$PM_NAME via $mgr" "$log" "$(pm::cmd "$mgr" "$target" "$PM_EXTRA")"; rc=$?
      (( rc == 0 )) && { ok=1; break; }
      pm::heal "$mgr" "$log" || break
    done
    (( ok )) && break
    ui::say_status WARN "$mgr failed for $PM_NAME"
  done

  local el=$(( SECONDS - t0 ))
  if (( ok )); then
    ui::say_status OK "$PM_NAME installed via $mgr in $((el/60))m$((el%60))s"
    printf '%s|%s|%s|ok\n' "$(date '+%F %T')" "$PM_NAME" "$mgr" >> "$NEBULA_CFG/installs.log"
    return 0
  fi
  printf '%s|%s|%s|FAILED\n' "$(date '+%F %T')" "$PM_NAME" "${methods[*]}" >> "$NEBULA_CFG/installs.log"
  ui::say_status ERR "Couldn't install $PM_NAME."
  printf "\n${C_DIM}Last output:${C_RESET}\n"; tail -n 12 "$log" | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g; s/^/   /' | cut -c1-$(( $(ui::cols) - 2 ))
  printf "\n  ${C_DIM}Full log:${C_RESET} %s\n  ${C_DIM}Try:${C_RESET} nebula install %s -v   ${C_DIM}(live output)${C_RESET}\n" "$log" "$name"
  printf "  ${C_DIM}Common fixes:${C_RESET} pkg update · termux-change-repo · free storage\n\n"
  return 1
}

# ── commands ────────────────────────────────────────────────────────────
pm::list() {
  local filter=${1:-} cat="" n al m c d inst=""
  inst=$(dpkg-query -W -f='${Package}\n' 2>/dev/null)
  printf "${C_CYAN}${C_BOLD}📚 Installable tools${C_RESET} ${C_DIM}(%s)${C_RESET}\n" "$(pm::registry | wc -l)"; ui::hint "install <name> to install one"
  while IFS='|' read -r n al m c d; do
    [[ -n $filter && ${c,,} != "${filter,,}" && ${n,,} != *"${filter,,}"* && ${d,,} != *"${filter,,}"* && " ${al,,} " != *"${filter,,}"* ]] && continue
    if [[ $c != "$cat" ]]; then cat=$c; printf '\n%s%s%s\n' "$C_BOLD$C_CYAN" "$c" "$C_RESET"; fi
    local mark=" "; local first=${m%%;*}; first=${first#*:}; first=${first%%+*}
    grep -qxF -- "$first" <<<"$inst" && mark="${C_GREEN}✔${C_RESET}"
    printf " %s %-15s ${C_DIM}%-4s %s${C_RESET}\n" "$mark" "$n" "${m%%:*}" "$(viz::trunc "$d" $(( $(ui::cols) - 26 )))"
  done < <(pm::registry)
  printf '\n'
}

cmd::install() {
  PM_VERBOSE=0; PM_YES=0; PM_FORCE=0; PM_VIA=""
  local names=() sub=""
  while (( $# )); do
    case "$1" in
      -v|--verbose) PM_VERBOSE=1 ;;
      -y|--yes)     PM_YES=1 ;;
      -f|--force)   PM_FORCE=1 ;;
      --via)        PM_VIA=${2:-}; shift ;;
      --via=*)      PM_VIA=${1#--via=} ;;
      list|ls)      sub=list ;;
      search|find)  sub=search ;;
      info)         sub=info ;;
      log|logs)     sub=log ;;
      *)            names+=("$1") ;;
    esac; shift
  done
  case $sub in
    list)   pm::list "${names[0]:-}"; return ;;
    search) pm::list "${names[*]}"; return ;;
    log)    local lf; lf=$(ls -1t "$NEBULA_CFG"/logs/install-* 2>/dev/null | head -1)
            [[ -z $lf ]] && { ui::say_status INFO "No install logs yet."; return; }
            printf "${C_DIM}%s${C_RESET}\n" "$lf"; sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' "$lf" | tail -n 40; return ;;
    info)   local n=${names[0]:-}; pm::find "$n" || { ui::say_status ERR "Not in the database: $n"; return 1; }
            printf "\n${C_BOLD}%s${C_RESET}  ${C_DIM}%s · %s${C_RESET}\n" "$PM_NAME" "$PM_CAT" "$PM_DESC"
            [[ -n $PM_ALIASES ]] && printf "  aliases: %s\n" "$PM_ALIASES"
            local m; IFS=';' read -ra ms <<<"$PM_METHODS"
            for m in "${ms[@]}"; do printf "  %s %s\n" "$(pm::have "${m%%:*}" && echo "${C_GREEN}✔${C_RESET}" || echo "${C_DIM}–${C_RESET}")" "$(pm::cmd "${m%%:*}" "${m#*:}")"; done; echo; return ;;
  esac
  if (( ${#names[@]} == 0 )); then
    if declare -F pick::choose >/dev/null 2>&1 && [[ -t 1 ]]; then
      local sel; sel=$(pm::registry | awk -F'|' '{printf "%-16s %s\n", $1, $5}' | pick::choose "Install which tool?") || return 0
      names=("${sel%% *}")
    else
      ui::say_status WARN "Usage: install <tool>   (try: install list)"; return 1
    fi
  fi
  local n rc=0
  for n in "${names[@]}"; do pm::install_one "$n" || rc=1; done
  return $rc
}

cmd::uninstall() {
  PM_YES=0; local names=() a
  for a in "$@"; do case $a in -y|--yes) PM_YES=1;; *) names+=("$a");; esac; done
  (( ${#names[@]} )) || { ui::say_status WARN "Usage: uninstall <tool>"; return 1; }
  local n m
  for n in "${names[@]}"; do
    pm::find "$n" || { ui::say_status ERR "Not in the database: $n"; continue; }
    local done_=0 ms; IFS=';' read -ra ms <<<"$PM_METHODS"
    for m in "${ms[@]}"; do
      pm::is_installed "${m%%:*}" "${m#*:}" || continue
      local c; c=$(pm::uncmd "${m%%:*}" "${m#*:}")
      printf "  ${C_DIM}Will run:${C_RESET} %s\n" "$c"
      (( PM_YES )) || ui::confirm "Remove $PM_NAME?" N || { done_=1; break; }
      pm::run "Removing $PM_NAME" "$NEBULA_CFG/logs/uninstall.log" "$c" && ui::say_status OK "$PM_NAME removed." || ui::say_status ERR "Removal failed (see $NEBULA_CFG/logs/uninstall.log)"
      done_=1; break
    done
    (( done_ )) || ui::say_status INFO "$PM_NAME doesn't look installed."
  done
}
