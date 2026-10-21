#!/data/data/com.termux/files/usr/bin/env bash
# nebula — dev shortcuts: background servers/bots, error-only logs, Firebase deploy
#   dev start|stop|restart|ls|logs|errors|deploy      (state in $NEBULA_CFG/dev/<name>.*)

DEV_ERR_RE='error|exception|fail|fatal|unhandled|panic|traceback|econn|eaddr|enoent|eacces|cannot find module|not defined|denied|timed? ?out|crash|rejected|stream errored|logged out|disconnected'

dev::_dir() { local d="$NEBULA_CFG/dev"; mkdir -p "$d"; chmod 700 "$d" 2>/dev/null; printf '%s' "$d"; }
dev::_name_ok() { [[ $1 =~ ^[A-Za-z0-9._-]{1,32}$ ]]; }

dev::_alive() {   # is <name> running?
  local f; f="$(dev::_dir)/$1.pid"; [[ -s $f ]] || return 1
  local pid; pid=$(<"$f"); [[ $pid =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null
}

dev::_tree() {    # pid + all descendants (walks ps, so it works without setsid)
  local root=$1 out="$1" cur="$1" next p c
  while [[ -n $cur ]]; do
    next=""
    for p in $cur; do
      for c in $(ps -e -o pid=,ppid= 2>/dev/null | awk -v p="$p" '$2==p{print $1}'); do next+="$c "; out+=" $c"; done
    done
    cur=$next
  done
  printf '%s' "$out"
}

dev::_detect() {  # guess a start command from the current folder
  if [[ -f package.json ]] && grep -q '"start"' package.json 2>/dev/null; then echo "npm start"
  elif [[ -f index.js ]]; then echo "node index.js"
  elif [[ -f bot.js ]]; then echo "node bot.js"
  elif [[ -f main.js ]]; then echo "node main.js"
  elif [[ -f app.py ]]; then echo "python3 app.py"
  elif [[ -f main.py ]]; then echo "python3 main.py"
  elif [[ -f bot.py ]]; then echo "python3 bot.py"
  else echo "static"
  fi
}

dev::_start() {
  local name="" port="" cmd=""
  while (( $# )); do
    case $1 in
      --port|-p) port=${2:-}; shift 2 || break ;;
      --) shift; cmd="$*"; break ;;
      *) if [[ -z $name ]]; then name=$1; else cmd+="${cmd:+ }$1"; fi; shift ;;
    esac
  done
  [[ -n $name ]] || name=$(basename "$PWD")
  name=$(printf '%s' "$name" | tr -c 'A-Za-z0-9._\n-' '-' | cut -c1-32)
  dev::_name_ok "$name" || { ui::say_status ERR "Bad name. Use letters, digits, . _ -"; return 1; }
  if [[ -n $port ]]; then [[ $port =~ ^[0-9]+$ ]] && (( port >= 1024 && port <= 65535 )) || { ui::say_status ERR "Port must be 1024-65535"; return 1; }; fi
  if dev::_alive "$name"; then ui::say_status WARN "'$name' is already running. Use: dev restart $name"; return 1; fi
  local d; d=$(dev::_dir)
  if [[ -z $cmd ]]; then
    cmd=$(dev::_detect)
    if [[ $cmd == static ]]; then
      local py; py=$(command -v python3 || command -v python) || { ui::say_status ERR "Nothing to run here and python is missing."; return 1; }
      port=${port:-8000}; cmd="$py -m http.server $port --bind 0.0.0.0"
      ui::say_status INFO "No app found here, serving this folder as a website."
    fi
  fi
  [[ -s $d/$name.log ]] && mv -f "$d/$name.log" "$d/$name.log.old"
  printf '%s\n' "$cmd" > "$d/$name.cmd"; printf '%s\n' "$PWD" > "$d/$name.dir"; date +%s > "$d/$name.start"
  if [[ -n $port ]]; then printf '%s\n' "$port" > "$d/$name.port"; else rm -f "$d/$name.port"; fi
  rm -f "$d/$name.pid"
  ( [[ -n $port ]] && export PORT=$port
    nohup bash -c "$cmd" >"$d/$name.log" 2>&1 </dev/null &
    echo $! >"$d/$name.pid" )
  sleep 1
  if dev::_alive "$name"; then
    ui::say_status OK "Started '$name' (pid $(<"$d/$name.pid"))"
    if [[ -n $port ]]; then
      local ip; ip=$(ui::lan_ip 2>/dev/null)
      printf '  %b%s%b\n' "$C_CYAN" "http://localhost:$port${ip:+   or   http://$ip:$port}" "$C_RESET"
    fi
    printf '  %bdev logs %s -f · dev errors %s · dev stop %s%b\n' "$C_DIM" "$name" "$name" "$name" "$C_RESET"
  else
    ui::say_status ERR "'$name' stopped right away. Last lines:"
    tail -n 8 "$d/$name.log" 2>/dev/null | sed 's/^/    /'
    rm -f "$d/$name.pid"; return 1
  fi
}

dev::_stop() {
  local name=${1:-}; [[ -n $name ]] || { ui::say_status ERR "Usage: dev stop <name|all>"; return 1; }
  local d; d=$(dev::_dir)
  if [[ $name == all ]]; then
    local f n any=0
    for f in "$d"/*.pid; do [[ -e $f ]] || continue; n=$(basename "$f" .pid); dev::_stop "$n"; any=1; done
    (( any )) || ui::say_status INFO "Nothing is running."
    return 0
  fi
  dev::_name_ok "$name" || { ui::say_status ERR "Bad name"; return 1; }
  if ! dev::_alive "$name"; then rm -f "$d/$name.pid"; ui::say_status INFO "'$name' is not running."; return 0; fi
  local pid pids; pid=$(<"$d/$name.pid"); pids=$(dev::_tree "$pid")
  kill $pids 2>/dev/null
  local i; for i in 1 2 3 4 5 6; do dev::_alive "$name" || break; sleep 0.5; done
  dev::_alive "$name" && kill -9 $pids 2>/dev/null
  rm -f "$d/$name.pid"; ui::say_status OK "Stopped '$name'"
}

dev::_ls() {
  local d f n any=0 cols w; d=$(dev::_dir); cols=$(ui::cols); w=$(( cols - 8 )); (( w < 10 )) && w=10
  for f in "$d"/*.cmd; do
    [[ -e $f ]] || continue; n=$(basename "$f" .cmd); any=1
    local st="${C_DIM}stopped${C_RESET}" up=""
    if dev::_alive "$n"; then
      local s now e; s=$(<"$d/$n.start"); now=$(date +%s); e=$(( now - s ))
      if (( e >= 3600 )); then up="$((e/3600))h$((e%3600/60))m"; elif (( e >= 60 )); then up="$((e/60))m"; else up="${e}s"; fi
      st="${C_GREEN}running${C_RESET} $up"
    fi
    local ec; ec=$(grep -ciE "$DEV_ERR_RE" "$d/$n.log" 2>/dev/null); ec=${ec:-0}
    printf '  %b●%b %-12s %b' "$C_CYAN" "$C_RESET" "$(viz::trunc "$n" 12)" "$st"
    (( ec > 0 )) && printf '  %b%s err%b' "$C_RED" "$ec" "$C_RESET"
    printf '\n      %b%s%b\n' "$C_DIM" "$(viz::trunc "$(<"$f")" "$w")" "$C_RESET"
  done
  (( any )) || ui::say_status INFO "Nothing started yet. Try: dev start   (inside an app or website folder)"
}

dev::_logfile() {
  local name=${1:-}; dev::_name_ok "$name" || { ui::say_status ERR "Usage: dev $2 <name>" >&2; return 1; }
  local f; f="$(dev::_dir)/$name.log"; [[ -f $f ]] || { ui::say_status ERR "No log for '$name'. See: dev ls" >&2; return 1; }
  printf '%s' "$f"
}

dev::_logs() {
  local name=${1:-} follow=0 n=40 f; shift || true
  while (( $# )); do case $1 in -f|--follow) follow=1 ;; [0-9]*) n=$1 ;; esac; shift; done
  f=$(dev::_logfile "$name" logs) || return 1
  if (( follow )); then ui::say_status INFO "Following '$name' (Ctrl+C to stop)"; tail -n "$n" -f "$f"; else tail -n "$n" "$f"; fi
}

# error-only view: matching lines plus two lines of stack context, wrapped to the screen
dev::_errors() {
  local name=${1:-} n=20 follow=0 f; shift || true
  while (( $# )); do case $1 in -f|--follow) follow=1 ;; [0-9]*) n=$1 ;; esac; shift; done
  f=$(dev::_logfile "$name" errors) || return 1
  local cols; cols=$(ui::cols)
  if (( follow )); then
    ui::say_status INFO "Errors from '$name' as they happen (Ctrl+C to stop)"
    tail -n 0 -f "$f" | grep --line-buffered -iE "$DEV_ERR_RE" | while IFS= read -r l; do
      printf '%b✖%b %s\n' "$C_RED" "$C_RESET" "$l" | ui::wrap "$((cols-1))" 2
    done
    return 0
  fi
  local out; out=$(sed 's/\x1b\[[0-9;]*m//g' "$f" | grep -iE -A2 "$DEV_ERR_RE" | grep -v '^--$' | tail -n "$n")
  if [[ -z $out ]]; then ui::say_status OK "No errors in the log of '$name'"; return 0; fi
  printf '%s\n' "$out" | while IFS= read -r l; do
    if grep -qiE "$DEV_ERR_RE" <<<"$l"; then printf '%b✖%b %s\n' "$C_RED" "$C_RESET" "$l"
    else printf '  %b%s%b\n' "$C_DIM" "$l" "$C_RESET"; fi
  done | ui::wrap "$((cols-1))" 2
  printf '%b  last %s lines · dev logs %s for everything%b\n' "$C_DIM" "$n" "$name" "$C_RESET"
}

dev::_deploy() {
  [[ -f firebase.json ]] || { ui::say_status ERR "No firebase.json here. Run this inside your Firebase site folder."; return 1; }
  command -v firebase >/dev/null 2>&1 || { ui::say_status ERR "Firebase CLI missing. Run: nebula install firebase-tools"; return 1; }
  local only=""; [[ ${1:-} == --only && -n ${2:-} ]] && only="--only $2"
  local proj; proj=$(grep -o '"default" *: *"[^"]*"' .firebaserc 2>/dev/null | head -1 | sed 's/.*: *"//;s/"//')
  ui::say_status WARN "This publishes to the live site${proj:+ ($proj)}."
  ui::confirm "Deploy now?" N || { ui::say_status INFO "Cancelled."; return 0; }
  firebase deploy $only
}

dev::_restart() {
  local n=${1:-} d c p pt
  [[ -n $n ]] || { ui::say_status ERR "Usage: dev restart <name>"; return 1; }
  dev::_name_ok "$n" || { ui::say_status ERR "Bad name"; return 1; }
  d=$(dev::_dir)
  [[ -f $d/$n.cmd ]] || { ui::say_status ERR "Unknown '$n'. See: dev ls"; return 1; }
  c=$(<"$d/$n.cmd"); p=$(<"$d/$n.dir"); pt=""; [[ -f $d/$n.port ]] && pt=$(<"$d/$n.port")
  dev::_stop "$n"
  cd "$p" 2>/dev/null || { ui::say_status ERR "Folder is gone: $p"; return 1; }
  if [[ -n $pt ]]; then dev::_start "$n" --port "$pt" -- "$c"; else dev::_start "$n" -- "$c"; fi
}

cmd::dev() {
  local sub=${1:-ls}; shift || true
  case $sub in
    start|run|up)       dev::_start "$@" ;;
    stop|down|kill)     dev::_stop "$@" ;;
    restart|re)         dev::_restart "$@" ;;
    ls|list|status)     dev::_ls ;;
    logs|log)           dev::_logs "$@" ;;
    errors|err|errs)    dev::_errors "$@" ;;
    deploy)             dev::_deploy "$@" ;;
    *) ui::say_status ERR "Unknown: dev $sub"; printf '  dev start|stop|restart|ls|logs|errors|deploy\n'; return 1 ;;
  esac
}

cmd::deploy() { dev::_deploy "$@"; }
