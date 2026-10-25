#!/data/data/com.termux/files/usr/bin/env bash
# nebula — Mingle: a dating app for the terminal, on the same Firebase project as bug reports and online games.
# Sign in with email + password, or with a username + key (a generated password; no email needed).
# Everything lives under mingle/ in the Realtime Database; the rules are in docs/rtdb-additions.json.
# Needs: curl and python3.  Optional: tgpt (the "wingman" that suggests opening lines).

m::j() { python3 "$NEBULA_HOME/lib/mj.py" "$@"; }   # JSON helper (standard library only)
M_TOK=""; M_EXP=0; M_UID=""; M_EMAIL=""; M_USER=""; M_RT=""; M_BODY=""; M_CODE=0
M_ME="{}"; M_W=60; K=""; M_MATCH=0; M_ONLYCITY=""; M_UNDERAGE=0
M_DOMAIN="mingle.jitetee.app"          # username accounts get <username>@this as their (private) sign-in address

# ── small helpers ──────────────────────────────────────────────────────────
m::ms()  { local t=${EPOCHREALTIME:-}; if [[ -n $t ]]; then t=${t/[.,]/}; printf '%s' "$(( t / 1000 ))"; else printf '%s' "$(( $(date +%s) * 1000 ))"; fi; }
m::say() { ui::say_status "$@"; }
m::cols() { local c; c=$(ui::cols 2>/dev/null || echo 60); (( c > 70 )) && c=70; (( c < 30 )) && c=30; M_W=$c; }
m::hr()  { local s; printf -v s '%*s' "$M_W" ''; printf '%s%s%s\n' "$C_DIM" "${s// /─}" "$C_RESET"; }
m::clear() { printf '\033[H\033[2J\033[3J'; }
m::wrap() {   # wrap to the screen; lines starting with "• " get a hanging indent
  if [[ $1 == "• "* ]]; then fold -s -w "$(( M_W - 6 ))" <<<"$1" | sed '1s/^/  /; 2,$s/^/    /'
  else fold -s -w "$(( M_W - 4 ))" <<<"$1" | sed 's/^/  /'; fi
}
m::cleanup() { printf '\033[?25h'; }
m::ago() {   # ms → "5m", "2h", "3d"
  local s=$(( ( $(m::ms) - ${1:-0} ) / 1000 ))
  (( s < 0 )) && s=0
  if (( s < 60 )); then printf 'now'; elif (( s < 3600 )); then printf '%sm' $((s/60)); elif (( s < 86400 )); then printf '%sh' $((s/3600)); else printf '%sd' $((s/86400)); fi
}

# m::key [timeout] → K = up|down|left|right|enter|esc|<char>; returns 1 on timeout
m::key() {
  local t=${1:-} k r
  if [[ -n $t ]]; then IFS= read -rsn1 -t "$t" k || return 1; else IFS= read -rsn1 k || { K=esc; return 0; }; fi
  if [[ $k == $'\033' ]]; then
    IFS= read -rsn2 -t 0.05 r || r=""
    case $r in '[A') K=up ;; '[B') K=down ;; '[C') K=right ;; '[D') K=left ;; *) K=esc ;; esac
  elif [[ -z $k ]]; then K=enter
  elif [[ $k == $'\177' || $k == $'\b' ]]; then K=bksp
  else K=$k; fi
}
m::wait() { printf '\n%s  press any key…%s' "$C_DIM" "$C_RESET"; IFS= read -rsn1 _; }
m::ask() {   # m::ask "label" [default] → REPLY
  local def=${2:-} v
  if [[ -n $def ]]; then read -r -e -p "  $1 [$def]: " v || return 1; REPLY=${v:-$def}
  else read -r -e -p "  $1: " v || return 1; REPLY=$v; fi
}
m::secret() { local v; read -r -s -p "  $1: " v || return 1; printf '\n'; REPLY=$v; }
m::rand_key() { local a=abcdefghjkmnpqrstuvwxyz23456789 out="" i; for i in {1..16}; do out+=${a:RANDOM%${#a}:1}; (( i % 4 == 0 && i < 16 )) && out+=-; done; printf '%s' "$out"; }

# ── auth (Firebase REST) ───────────────────────────────────────────────────
m::idurl() { printf '%s' "${NEBULA_CLOUD_IDURL:-https://identitytoolkit.googleapis.com}"; }
m::tkurl() { printf '%s' "${NEBULA_CLOUD_TOKURL:-https://securetoken.googleapis.com}"; }

m::authcall() {   # endpoint json → body in M_BODY; 0 on 2xx
  local out
  out=$(curl -sS --max-time 20 -w $'\n%{http_code}' -X POST -H 'Content-Type: application/json' -d "$2" "$(m::idurl)/v1/accounts:$1?key=$CLOUD_KEY" 2>&1) || { M_CODE=0; M_BODY=$out; return 1; }
  M_CODE=${out##*$'\n'}; M_BODY=${out%$'\n'*}; [[ $M_CODE == 2* ]]
}
m::authmsg() {   # friendly text for the last auth failure
  local e; e=$(m::j get error.message <<<"$M_BODY" 2>/dev/null)
  case $e in
    EMAIL_EXISTS) echo "That email or username is already taken." ;;
    INVALID_EMAIL) echo "That email address doesn't look right." ;;
    WEAK_PASSWORD*) echo "Password too short. Use at least 6 characters." ;;
    EMAIL_NOT_FOUND|INVALID_PASSWORD|INVALID_LOGIN_CREDENTIALS) echo "Wrong email/username or password/key." ;;
    USER_DISABLED) echo "This account has been disabled." ;;
    TOO_MANY_ATTEMPTS*) echo "Too many attempts. Wait a few minutes and try again." ;;
    OPERATION_NOT_ALLOWED|ADMIN_ONLY_OPERATION) echo "Email/Password sign-in is switched off. The owner must enable it in Firebase Authentication." ;;
    CREDENTIAL_TOO_OLD*|TOKEN_EXPIRED|INVALID_ID_TOKEN) echo "Your session expired. Sign in again." ;;
    "") [[ $M_CODE == 0 ]] && echo "Can't reach the server. Check your internet connection." || echo "Server error ($M_CODE)." ;;
    *) echo "Sign-in failed ($e)." ;;
  esac
}
m::setsess() {   # from an auth response in $1
  local j=$1 t
  t=$(m::j get idToken id_token <<<"$j"); [[ -n $t ]] || return 1
  M_TOK=$t; M_RT=$(m::j get refreshToken refresh_token <<<"$j")
  M_UID=$(m::j get localId user_id <<<"$j")
  M_EXP=$(( $(date +%s) + 3300 ))
}
m::SESS() { printf '%s' "$NEBULA_CFG/mingle.sess"; }
m::save() { mkdir -p "$NEBULA_CFG"; ( umask 077; printf '%s|%s|%s|%s\n' "$M_UID" "$M_EMAIL" "$M_USER" "$M_RT" > "$(m::SESS)" ); }
m::fresh() {   # make sure the token is valid
  (( $(date +%s) < M_EXP )) && return 0
  [[ -n $M_RT ]] || return 1
  local out
  out=$(curl -sS --max-time 20 -X POST "$(m::tkurl)/v1/token?key=$CLOUD_KEY" -d "grant_type=refresh_token&refresh_token=$M_RT" 2>/dev/null) || return 1
  m::setsess "$out" || return 1
  m::save; return 0
}
m::signin() {   # m::signin email password
  local j; j=$(m::j obj email="$1" password="$2" returnSecureToken:=true)
  m::authcall signInWithPassword "$j" || return 1
  m::setsess "$M_BODY"; M_EMAIL=$1
}
m::signup() {
  local j; j=$(m::j obj email="$1" password="$2" returnSecureToken:=true)
  m::authcall signUp "$j" || return 1
  m::setsess "$M_BODY"; M_EMAIL=$1
}

# ── database requests ──────────────────────────────────────────────────────
# m::req METHOD path[?query] [json] → M_BODY / M_CODE; 0 on 2xx. Queries must already be URL-encoded.
m::req() {
  local m=$1 path=$2 body=${3:-} base qs="" url out
  m::fresh || { M_CODE=401; M_BODY="session expired"; return 3; }
  base=${path%%\?*}; [[ $path == *\?* ]] && qs="&${path#*\?}"
  url="$CLOUD_DB/$base.json?auth=$M_TOK$qs"
  local -a a=(-sS --max-time 20 -X "$m" -w $'\n%{http_code}')
  [[ -n $body ]] && a+=(-H 'Content-Type: application/json' -d "$body")
  out=$(curl "${a[@]}" "$url" 2>&1) || { M_CODE=0; M_BODY=$out; return 1; }
  M_CODE=${out##*$'\n'}; M_BODY=${out%$'\n'*}; [[ $M_CODE == 2* ]]
}
m::get() { m::req GET "mingle/$1" && printf '%s' "$M_BODY"; }
m::put() { m::req PUT "mingle/$1" "$2"; }
m::patch() { m::req PATCH "mingle/$1" "$2"; }
m::del() { m::req DELETE "mingle/$1"; }
m::post() { m::req POST "mingle/$1" "$2"; }
m::fail() {   # explain the last database failure
  case $M_CODE in
    0) m::say ERR "Can't reach the server. Check your internet connection." ;;
    401|403) m::say ERR "The server refused that. If this keeps happening, the owner needs to publish the Mingle rules (docs/rtdb-additions.json)." ;;
    *) m::say ERR "Server error ($M_CODE)." ;;
  esac
}
m::sv() { printf '{".sv":"timestamp"}'; }

# ── profile ────────────────────────────────────────────────────────────────
m::load_me() { local b; b=$(m::get "profiles/$M_UID") || return 1; [[ -n $b && $b != null ]] && M_ME=$b || M_ME="{}"; }
m::me() { m::j get "$1" <<<"$M_ME"; }

m::profile_form() {   # create or edit; returns 1 if cancelled
  m::clear; m::cols
  local name age gender seeking city bio interests vibe vis first=0
  [[ $M_ME == "{}" ]] && first=1
  printf '%s%s%s\n' "$C_BOLD$C_MAGENTA" "  ❤  Your Mingle profile" "$C_RESET"; m::hr
  (( first )) && printf '%s  Mingle is for adults only (18+). Keep it kind and honest.%s\n\n' "$C_DIM" "$C_RESET"
  m::ask "First name or nickname" "$(m::me name)" || return 1; name=${REPLY:0:30}; [[ -n ${name// } ]] || { m::say WARN "A name is needed."; return 1; }
  while :; do
    m::ask "Age" "$(m::me age)" || return 1; age=$REPLY
    [[ $age =~ ^[0-9]+$ ]] || { m::say WARN "Numbers only."; continue; }
    (( age < 18 )) && { m::say ERR "Mingle is only for people 18 and over."; M_UNDERAGE=1; return 1; }
    (( age > 99 )) && { m::say WARN "Enter a real age (18-99)."; continue; }
    break
  done
  local g; g=$(m::me gender); printf '  Gender: 1) man  2) woman  3) nonbinary  4) other'; [[ -n $g ]] && printf '   (now: %s)' "$g"; printf '\n'
  while :; do m::ask "Choose 1-4" ""  || return 1; case $REPLY in 1) gender=man ;; 2) gender=woman ;; 3) gender=nonbinary ;; 4) gender=other ;; "") [[ -n $g ]] && { gender=$g; } ;; esac; [[ -n ${gender:-} ]] && break; done
  local s; s=$(m::me seeking); printf '  Interested in: 1) men  2) women  3) everyone'; [[ -n $s ]] && printf '   (now: %s)' "$s"; printf '\n'
  while :; do m::ask "Choose 1-3" "" || return 1; case $REPLY in 1) seeking=men ;; 2) seeking=women ;; 3) seeking=everyone ;; "") [[ -n $s ]] && seeking=$s ;; esac; [[ -n ${seeking:-} ]] && break; done
  m::ask "City or town" "$(m::me city)" || return 1; city=${REPLY:0:40}; [[ -n ${city// } ]] || { m::say WARN "A city is needed so we can find people near you."; return 1; }
  m::ask "About you (max 300 characters)" "$(m::me bio)" || return 1; bio=${REPLY:0:300}
  m::ask "Interests, comma separated (music, football, hiking)" "$(m::me interests)" || return 1; interests=$(tr 'A-Z' 'a-z' <<<"${REPLY:0:120}")
  m::ask "A mood emoji (optional)" "$(m::me vibe)" || return 1; vibe=${REPLY:0:8}
  local ts; ts=$(m::me ts); vis=$(m::j get -d true visible <<<"$M_ME")
  local j
  j=$(m::j obj name="$name" username="$M_USER" age:="$age" gender="$gender" seeking="$seeking" city="$city" bio="$bio" \
       interests="$interests" vibe="$vibe" visible:="$vis" ts=@ts seen=@ts)
  m::put "profiles/$M_UID" "$j" || { m::fail; m::wait; return 1; }
  m::load_me; m::say OK "Profile saved."; return 0
}

# ── sign in / sign up screens ──────────────────────────────────────────────
m::claim_username() {   # m::claim_username name → 0 if claimed (or already ours)
  local n=$1 cur
  cur=$(m::get "usernames/$n") && [[ $cur == "\"$M_UID\"" ]] && return 0
  m::put "usernames/$n" "\"$M_UID\""
}

m::pick_username() {   # for email accounts: choose a unique public username
  local u
  while :; do
    m::ask "Pick a username (3-20: a-z 0-9 _)" "" || return 1; u=$(tr 'A-Z' 'a-z' <<<"$REPLY")
    [[ $u =~ ^[a-z0-9_]{3,20}$ ]] || { m::say WARN "3-20 letters, numbers or underscore."; continue; }
    if m::claim_username "$u"; then M_USER=$u; return 0; fi
    [[ $M_CODE == 401 || $M_CODE == 403 ]] && m::say WARN "That username is taken. Try another." || { m::fail; return 1; }
  done
}

m::terms() {
  m::clear; m::cols
  printf '%s%s%s\n' "$C_BOLD$C_MAGENTA" "  ❤  Welcome to Mingle" "$C_RESET"; m::hr
  m::wrap "Mingle helps people meet and chat. Before you start:"
  printf '\n'
  m::wrap "• You must be 18 or older."
  m::wrap "• Be honest and respectful. No harassment, hate, scams or explicit photos/links."
  m::wrap "• Never send money or share passwords, ID or bank details with someone you met here."
  m::wrap "• Meet in a public place and tell a friend. Block and report anyone who makes you uneasy."
  m::wrap "• Your profile (name, age, city, bio) is visible to other Mingle members. Your sign-in details are not."
  printf '\n'
  ui::confirm "I am 18 or older and agree" N
}

m::auth_screen() {   # returns 0 when signed in
  while :; do
    m::clear; m::cols
    printf '%s%s%s\n' "$C_BOLD$C_MAGENTA" "  ❤  Mingle" "$C_RESET"; m::hr
    printf '  1) Sign in with email\n  2) Sign in with username + key\n  3) Create account with email\n  4) Create account with username + key (no email needed)\n  5) Forgot password (email accounts)\n  0) Back\n\n'
    printf '  Choose: '; m::key; printf '%s\n' "$K"
    case $K in
      1) m::ask "Email" || continue; local e=$REPLY; m::secret "Password" || continue
         if m::signin "$e" "$REPLY"; then M_USER=""; return 0; fi; m::say ERR "$(m::authmsg)"; m::wait ;;
      2) m::ask "Username" || continue; local u; u=$(tr 'A-Z' 'a-z' <<<"$REPLY"); m::secret "Key" || continue
         if m::signin "$u@$M_DOMAIN" "$REPLY"; then M_USER=$u; return 0; fi; m::say ERR "$(m::authmsg)"; m::wait ;;
      3) m::terms || continue
         m::ask "Email" || continue; local e=$REPLY; m::secret "Password (6+ characters)" || continue; local p=$REPLY; m::secret "Repeat password" || continue
         [[ $REPLY == "$p" ]] || { m::say ERR "Passwords don't match."; m::wait; continue; }
         if m::signup "$e" "$p"; then M_USER=""; m::say OK "Account created."; return 0; fi; m::say ERR "$(m::authmsg)"; m::wait ;;
      4) m::terms || continue
         local u
         while :; do m::ask "Choose a username (3-20: a-z 0-9 _)" || continue 2; u=$(tr 'A-Z' 'a-z' <<<"$REPLY"); [[ $u =~ ^[a-z0-9_]{3,20}$ ]] && break; m::say WARN "3-20 letters, numbers or underscore."; done
         local key; m::ask "Your key (press Enter to generate one)" || continue; key=$REPLY
         if [[ -z $key ]]; then key=$(m::rand_key); elif (( ${#key} < 8 )); then m::say WARN "A key needs at least 8 characters."; m::wait; continue; fi
         if m::signup "$u@$M_DOMAIN" "$key"; then
           M_USER=$u
           if ! m::claim_username "$u"; then m::say ERR "That username is taken."; m::delete_auth; m::wait; continue; fi
           printf '\n  %sYour key:%s %s%s%s\n' "$C_BOLD" "$C_RESET" "$C_GREEN" "$key" "$C_RESET"
           m::wrap "Write it down now. Username accounts have no email, so a lost key cannot be recovered."
           m::wait; return 0
         fi
         m::say ERR "$(m::authmsg)"; m::wait ;;
      5) m::ask "Email you signed up with" || continue
         if m::authcall sendOobCode "$(m::j obj requestType=PASSWORD_RESET email="$REPLY")"; then m::say OK "If that email has an account, a reset link is on its way."; else m::say ERR "$(m::authmsg)"; fi; m::wait ;;
      0|q|esc) return 1 ;;
    esac
  done
}

m::delete_auth() { m::authcall delete "$(m::j obj idToken="$M_TOK")"; M_TOK=""; M_EXP=0; M_RT=""; rm -f "$(m::SESS)"; }

m::resume() {   # saved session → 0 if still good
  local f; f=$(m::SESS); [[ -f $f ]] || return 1
  IFS='|' read -r M_UID M_EMAIL M_USER M_RT < "$f"; [[ -n $M_RT ]] || return 1
  M_EXP=0; m::fresh || { rm -f "$f"; return 1; }
  return 0
}

# ── discover ───────────────────────────────────────────────────────────────
m::keys() { m::j keys <<<"$1" 2>/dev/null; }

m::rescore() {   # add score/shared to one profile JSON
  m::j rescore "$M_ME" <<<"$1"
}

m::candidates() {   # → JSON lines (one per profile), best matches first
  local likes passes blocks blockedby profs
  likes=$(m::get "likes/$M_UID") || likes="{}"; passes=$(m::get "passes/$M_UID") || passes="{}"
  blocks=$(m::get "blocks/$M_UID") || blocks="{}"; blockedby=$(m::get "blockedBy/$M_UID") || blockedby="{}"
  profs=$(m::req GET "mingle/profiles?orderBy=%22ts%22&limitToLast=200" && printf '%s' "$M_BODY") || return 1
  m::j candidates "$M_UID" "$M_ME" "${likes:-}" "${passes:-}" "${blocks:-}" "${blockedby:-}" "${M_ONLYCITY:+x}" <<<"${profs:-}"
}

m::card() {   # m::card profileJSON [mine]
  local p=$1 own=${2:-0} name age city bio int vibe score shared
  IFS=$'\x1f' read -r name age city vibe score shared < <(m::j fields name age city vibe score=0 shared=0 <<<"$p")
  bio=$(m::j get bio <<<"$p"); int=$(m::j get interests <<<"$p")
  m::clear; m::cols
  printf '%s%s%s' "$C_BOLD$C_MAGENTA" "  ❤  Mingle" "$C_RESET"
  if (( own )); then printf '   %sthis is how others see you%s\n' "$C_DIM" "$C_RESET"; else printf '   %s%s%% match%s\n' "$C_GREEN" "$score" "$C_RESET"; fi; m::hr
  printf '\n  %s%s, %s%s %s\n' "$C_BOLD" "$name" "$age" "$C_RESET" "$vibe"
  printf '  %s📍 %s%s\n\n' "$C_DIM" "$city" "$C_RESET"
  [[ -n $bio ]] && { m::wrap "$bio"; printf '\n'; }
  if [[ -n $int ]]; then
    local mine; mine=$(m::j get interests <<<"$M_ME" | tr 'A-Z' 'a-z'); local chips="" t
    IFS=',' read -ra arr <<<"$int"
    for t in "${arr[@]}"; do t=${t#"${t%%[![:space:]]*}"}; t=${t%"${t##*[![:space:]]}"}; [[ -z $t ]] && continue
      if [[ ",${mine// /}," == *",${t// /},"* ]]; then chips+="${C_GREEN}#${t}${C_RESET} "; else chips+="${C_DIM}#${t}${C_RESET} "; fi; done
    m::wrap "$chips"; printf '\n'
  fi
  m::hr
  (( own )) && return 0
  printf '  %s→ like%s  %s← pass%s  %s↑ super%s\n  %sb block  r report  q back%s\n' "$C_GREEN" "$C_RESET" "$C_DIM" "$C_RESET" "$C_YELLOW" "$C_RESET" "$C_DIM" "$C_RESET"
}

m::like() {   # m::like uid [star] → sets M_MATCH=1 if it became a match
  local to=$1 star=${2:-0} j; M_MATCH=0
  if [[ $star == 1 ]]; then j=$(m::j obj ts=@ts star:=true); else j=$(m::j obj ts=@ts); fi
  m::put "likes/$M_UID/$to" "$j" || return 1
  m::put "likedBy/$to/$M_UID" "$j" || return 1
  local back; back=$(m::get "likedBy/$M_UID/$to") || return 0
  if [[ -n $back && $back != null ]]; then m::make_match "$to" && M_MATCH=1; fi
  return 0
}
m::pair() { local a=$M_UID b=$1; if [[ $(printf '%s\n%s\n' "$a" "$b" | LC_ALL=C sort | head -1) == "$a" ]]; then printf '%s_%s' "$a" "$b"; else printf '%s_%s' "$b" "$a"; fi; }
m::make_match() {
  local o=$1 pair a b ex
  pair=$(m::pair "$o"); a=${pair%%_*}; b=${pair#*_}
  ex=$(m::get "matches/$pair"); if [[ -z $ex || $ex == null ]]; then
    m::put "matches/$pair" "$(m::j obj a="$a" b="$b" ts=@ts)" || return 1
  fi
  local rec; rec=$(m::j obj pair="$pair" ts=@ts)
  m::put "users/$M_UID/matches/$o" "$rec" && m::put "users/$o/matches/$M_UID" "$rec"
}
m::pass()  { m::put "passes/$M_UID/$1" "$(m::ms)"; }
m::block() {
  local o=$1 pair
  m::put "blocks/$M_UID/$o" "$(m::ms)" || return 1
  m::put "blockedBy/$o/$M_UID" "$(m::ms)"
  pair=$(m::pair "$o")
  m::del "chats/$pair"; m::del "matches/$pair"; m::del "users/$M_UID/matches/$o"; m::del "users/$o/matches/$M_UID"
  m::del "likes/$M_UID/$o"; m::del "likedBy/$o/$M_UID"
  return 0
}
m::report() {   # m::report uid
  m::ask "What happened? (max 300 characters)" || return 1; local r=${REPLY:0:300}
  [[ -n ${r// } ]] || { m::say WARN "Nothing sent."; return 1; }
  m::post "userReports" "$(m::j obj about="$1" by="$M_UID" reason="$r" ts=@ts status=open)" && m::say OK "Report sent. Thank you." || m::fail
}

m::discover() {
  m::say INFO "Finding people…"
  local -a list=(); local l
  while IFS= read -r l; do [[ -n $l ]] && list+=("$l"); done < <(m::candidates)
  if (( ! ${#list[@]} )); then
    m::clear; m::cols; printf '%s  ❤  Mingle%s\n' "$C_BOLD$C_MAGENTA" "$C_RESET"; m::hr
    printf '\n'; m::wrap "No new people right now. Check back later, widen your search in Settings, or invite a friend."
    [[ -n ${M_ONLYCITY:-} ]] && m::wrap "(Showing only people in your city. Turn that off in Settings.)"
    m::wait; return 0
  fi
  local i=0 p uid nm
  while (( i < ${#list[@]} )); do
    p=${list[i]}; uid=$(m::j get uid <<<"$p"); nm=$(m::j get name <<<"$p")
    m::fresh
    m::card "$p"
    m::key || break
    case $K in
      right|l) m::like "$uid" 0 || { m::fail; m::wait; }
               (( M_MATCH )) && m::itsmatch "$p"; i=$((i+1)) ;;
      up|s)    m::like "$uid" 1 || { m::fail; m::wait; }
               (( M_MATCH )) && m::itsmatch "$p"; i=$((i+1)) ;;
      left|p)  m::pass "$uid" || m::fail; i=$((i+1)) ;;
      b)       if ui::confirm "Block $nm? They will not see you and you will not see them." N; then m::block "$uid" && m::say OK "Blocked." || m::fail; i=$((i+1)); fi ;;
      r)       m::report "$uid"; m::wait ;;
      q|esc)   break ;;
    esac
  done
}
m::itsmatch() {
  local nm; nm=$(m::j get name <<<"$1")
  m::clear; m::cols; printf '\n\n'
  printf '%s%s' "$C_BOLD$C_MAGENTA" "    ❤  It's a match!"; printf '%s\n\n' "$C_RESET"
  printf '    You and %s%s%s like each other.\n' "$C_BOLD" "$nm" "$C_RESET"
  printf '    %sOpen Matches to say hi.%s\n' "$C_DIM" "$C_RESET"; m::wait
}

# ── likes me ───────────────────────────────────────────────────────────────
m::likesme() {
  local lb; lb=$(m::get "likedBy/$M_UID") || { m::fail; m::wait; return; }
  local -a ids=(); local u
  while IFS= read -r u; do [[ -n $u ]] && ids+=("$u"); done < <(m::keys "${lb:-{\}}")
  local mine; mine=$(m::get "likes/$M_UID") || mine="{}"; local blocks; blocks=$(m::get "blocks/$M_UID") || blocks="{}"
  local -a list=(); local p
  for u in "${ids[@]}"; do
    [[ -n $(m::j get "$u" <<<"${mine:-}") ]] && continue
    [[ -n $(m::j get "$u" <<<"${blocks:-}") ]] && continue
    p=$(m::get "profiles/$u") || continue; [[ -n $p && $p != null ]] || continue
    list+=("$(m::rescore "$(m::j set uid="$u" star:="$(m::j get -d false "$u.star" <<<"$lb")" <<<"$p")")")
  done
  if (( ! ${#list[@]} )); then m::clear; m::cols; printf '%s  ❤  Likes you%s\n' "$C_BOLD$C_MAGENTA" "$C_RESET"; m::hr; printf '\n'; m::wrap "Nobody new yet. Keep your profile fresh and check back soon."; m::wait; return; fi
  local i=0 uid nm
  while (( i < ${#list[@]} )); do
    p=${list[i]}; uid=$(m::j get uid <<<"$p"); nm=$(m::j get name <<<"$p")
    m::card "$p"; [[ $(m::j get star <<<"$p") == true ]] && printf '  %s★ sent you a super like%s\n' "$C_YELLOW" "$C_RESET"
    m::key || break
    case $K in
      right|l) m::like "$uid" 0 || { m::fail; m::wait; }; (( M_MATCH )) && m::itsmatch "$p"; i=$((i+1)) ;;
      left|p)  m::pass "$uid"; i=$((i+1)) ;;
      b)       ui::confirm "Block $nm?" N && { m::block "$uid"; i=$((i+1)); } ;;
      r)       m::report "$uid"; m::wait ;;
      q|esc)   break ;;
    esac
  done
}

# ── matches and chat ───────────────────────────────────────────────────────
m::matches() {
  while :; do
    local ms; ms=$(m::req GET "mingle/users/$M_UID/matches" && printf '%s' "$M_BODY") || { m::fail; m::wait; return; }
    [[ -z $ms || $ms == null ]] && ms="{}"
    local -a ids=(); local u line sel=0
    while IFS= read -r u; do [[ -n $u ]] && ids+=("$u"); done < <(m::j matches sort <<<"$ms")
    m::clear; m::cols; printf '%s  ❤  Matches%s\n' "$C_BOLD$C_MAGENTA" "$C_RESET"; m::hr
    if (( ! ${#ids[@]} )); then printf '\n'; m::wrap "No matches yet. Like someone in Discover. When they like you back, they appear here."; m::wait; return; fi
    local -a names=() pairs=(); local n i=0 last lf lts seen unread
    for u in "${ids[@]}"; do
      n=$(m::get "profiles/$u" | m::j get -d "(gone)" name 2>/dev/null); names+=("${n:-?}"); pairs+=("$(m::j get "$u.pair" <<<"$ms")")
      IFS=$'\x1f' read -r last lf lts seen _ < <(m::j matches row "$u" <<<"$ms")
      unread=""; [[ -n $lf && $lf != "$M_UID" ]] && (( lts > seen )) && unread="${C_GREEN}●${C_RESET}"
      printf '  %s%2d%s %s%-14.14s%s %s %s%s%s\n' "$C_DIM" $((i+1)) "$C_RESET" "$C_BOLD" "${names[i]}" "$C_RESET" "$unread" "$C_DIM" "${last:0:$((M_W-26))}" "$C_RESET"
      i=$((i+1)); (( i >= 9 )) && break
    done
    m::hr; printf '  %sPress 1-%d to chat · q back%s ' "$C_DIM" "$i" "$C_RESET"
    m::key || return
    case $K in q|esc) return ;; [1-9]) (( K <= i )) && m::chat "${ids[K-1]}" "${pairs[K-1]}" "${names[K-1]}" ;; esac
  done
}

m::chat() {   # m::chat otherUid pair name
  local o=$1 pair=$2 name=$3 buf="" sig="" msgs n i redraw=1
  [[ -n $pair ]] || pair=$(m::pair "$o")
  local -a wing=()
  printf '\033[?25l'
  while :; do
    m::fresh
    msgs=$(m::req GET "mingle/chats/$pair/messages?orderBy=%22ts%22&limitToLast=30" && printf '%s' "$M_BODY") || msgs="{}"
    [[ -z $msgs || $msgs == null ]] && msgs="{}"
    n=$(m::j messages sig <<<"$msgs" 2>/dev/null)
    if [[ $n != "$sig" || ${redraw:-1} == 1 ]]; then
      sig=$n; redraw=0
      m::patch "users/$M_UID/matches/$o" '{"seen":{".sv":"timestamp"}}' >/dev/null 2>&1
      m::clear; m::cols; printf '%s  ❤  %s%s\n' "$C_BOLD$C_MAGENTA" "$name" "$C_RESET"; m::hr
      local rows; rows=$(ui::rows 2>/dev/null || echo 24); local keep=$(( rows - 8 )); (( keep < 4 )) && keep=4
      local f t ts; while IFS=$'\x1f' read -r f t ts; do
        if [[ $f == "$M_UID" ]]; then printf '%s%s%s\n' "$C_GREEN" "$(fold -s -w "$((M_W-6))" <<<"you: $t" | sed '2,$s/^/     /')" "$C_RESET"
        else fold -s -w "$((M_W-4))" <<<"$name: $t" | sed '2,$s/^/  /'; fi
      done < <(m::j messages rows "$keep" <<<"$msgs")
      (( ${#wing[@]} )) && { local w; i=1; for w in "${wing[@]}"; do printf '%s  /%d  %s%s\n' "$C_YELLOW" "$i" "$w" "$C_RESET"; i=$((i+1)); done; }
      printf '\n'; m::hr; printf '%s  /q back  /wing  /unmatch  /block  /report%s\n' "$C_DIM" "$C_RESET"
    fi
    printf '\r\033[K  > %s' "$buf"; printf '\033[?25h'
    if m::key 3; then
      case $K in
        enter)
          if [[ $buf == /* ]]; then
            case $buf in
              /q|/quit) printf '\033[?25h'; return ;;
              /wing) printf '\n'; wing=(); local w; while IFS= read -r w; do [[ -n $w ]] && wing+=("$w"); done < <(m::wingman "$o"); (( ${#wing[@]} )) || { m::say INFO "Wingman needs tgpt (nebula install tgpt)."; sleep 1.5; }; sig="" ;;
              /1|/2|/3) local idx=${buf#/}; [[ -n ${wing[idx-1]:-} ]] && { buf=${wing[idx-1]}; continue; } ;;
              /unmatch) printf '\n'; if ui::confirm "Unmatch $name? The chat will be deleted." N; then m::unmatch "$o" "$pair"; return; fi; sig="" ;;
              /block) printf '\n'; if ui::confirm "Block $name?" N; then m::block "$o" && { m::say OK "Blocked."; m::wait; return; }; fi; sig="" ;;
              /report) printf '\n'; m::report "$o"; m::wait; sig="" ;;
              *) printf '\n'; m::say WARN "Unknown command."; sleep 1; sig="" ;;
            esac
            buf=""
          elif [[ -n ${buf// } ]]; then
            m::send "$o" "$pair" "$buf" || { printf '\n'; m::fail; sleep 1.5; }
            buf=""; sig=""
          fi ;;
        bksp) buf=${buf%?} ;;
        esc|up|down|left|right) : ;;
        *) (( ${#buf} < 480 )) && buf+=$K ;;
      esac
    fi
  done
}
m::send() {   # other pair text
  local o=$1 pair=$2 text=$3 j
  j=$(m::j obj from="$M_UID" text="$text" ts=@ts)
  m::post "chats/$pair/messages" "$j" || return 1
  local last=${text:0:100} up
  up=$(m::j obj last="$last" lastFrom="$M_UID" lastTs=@ts)
  m::patch "users/$M_UID/matches/$o" "$(m::j set seen=@ts <<<"$up")"
  m::patch "users/$o/matches/$M_UID" "$up"
  return 0
}
m::unmatch() {
  local o=$1 pair=$2
  m::del "chats/$pair"; m::del "matches/$pair"; m::del "users/$M_UID/matches/$o"; m::del "users/$o/matches/$M_UID"
  m::del "likes/$M_UID/$o"; m::del "likedBy/$o/$M_UID"
  m::put "passes/$M_UID/$o" "$(m::ms)"
  m::say OK "Unmatched."
}
m::wingman() {   # prints up to 3 opening lines
  command -v tgpt >/dev/null 2>&1 || return 0
  local p; p=$(m::get "profiles/$1") || return 0
  local info; info=$(m::j wing "$M_ME" <<<"$p"); local mine=""   # (includes my interests)
  tgpt -q "Suggest exactly 3 short, friendly, respectful opening messages (max 15 words each) to send to this person on a dating app. $info $mine Output only the 3 lines, no numbering, no quotes." 2>/dev/null | sed 's/^[0-9.\-\* ]*//' | grep -v '^$' | head -3
}

# ── my profile / settings ──────────────────────────────────────────────────
m::myprofile() {
  m::load_me; m::card "$M_ME" 1
  printf '\n  %se%s edit   %sv%s %s   %sq%s back\n' "$C_GREEN" "$C_RESET" "$C_GREEN" "$C_RESET" "$([[ $(m::j get -d true visible <<<"$M_ME") == true ]] && echo 'hide me' || echo 'show me')" "$C_DIM" "$C_RESET"
  m::key || return
  case $K in
    e) m::profile_form; m::wait ;;
    v) local v; v=$(m::j get -d true visible <<<"$M_ME"); m::patch "profiles/$M_UID" "{\"visible\":$([[ $v == true ]] && echo false || echo true)}" && m::say OK "Updated." || m::fail; m::load_me; m::wait ;;
  esac
}

m::settings() {
  while :; do
    m::clear; m::cols; printf '%s  ❤  Settings & safety%s\n' "$C_BOLD$C_MAGENTA" "$C_RESET"; m::hr
    printf '  Signed in as %s%s%s\n\n' "$C_BOLD" "$([[ -n $M_USER ]] && echo "@$M_USER" || echo "$M_EMAIL")" "$C_RESET"
    printf '  1) Only show people in my city: %s\n  2) Blocked people\n  3) Change %s\n  4) Safety tips\n  5) Sign out\n  6) Delete my account and data\n  0) Back\n\n  Choose: ' "$([[ -n ${M_ONLYCITY:-} ]] && echo ON || echo off)" "$([[ $M_EMAIL == *@$M_DOMAIN ]] && echo 'key' || echo 'password')"
    m::key; printf '\n'
    case $K in
      1) if [[ -n ${M_ONLYCITY:-} ]]; then M_ONLYCITY=""; else M_ONLYCITY=1; fi ;;
      2) m::blocked ;;
      3) m::secret "New $([[ $M_EMAIL == *@$M_DOMAIN ]] && echo key || echo password) (8+ characters)" || continue; local np=$REPLY
         if (( ${#np} < 8 )); then m::say WARN "Use at least 8 characters."; m::wait; continue; fi
         if m::authcall update "$(m::j obj idToken="$M_TOK" password="$np" returnSecureToken:=true)"; then m::setsess "$M_BODY"; m::save; m::say OK "Changed."; else m::say ERR "$(m::authmsg)"; fi; m::wait ;;
      4) m::tips; m::wait ;;
      5) rm -f "$(m::SESS)"; M_TOK=""; M_EXP=0; M_RT=""; m::say OK "Signed out."; return 9 ;;
      6) m::delete_account && return 9 ;;
      0|q|esc) return 0 ;;
    esac
  done
}
m::tips() {
  printf '\n'; m::wrap "• Meet in a public place and tell a friend where you are."
  m::wrap "• Never send money, even in an emergency. Report anyone who asks."
  m::wrap "• Don't share your address, workplace, ID or passwords early."
  m::wrap "• Use /block and /report in a chat, or b and r on a profile. Reports go to the J.I.T.E.T.E.E. team."
  m::wrap "• Trust your gut. You never owe anyone a reply."
}
m::blocked() {
  local b; b=$(m::get "blocks/$M_UID") || { m::fail; m::wait; return; }
  local -a ids=(); local u n i=0
  while IFS= read -r u; do [[ -n $u ]] && ids+=("$u"); done < <(m::keys "${b:-{\}}")
  m::clear; m::cols; printf '%s  ❤  Blocked%s\n' "$C_BOLD$C_MAGENTA" "$C_RESET"; m::hr
  (( ${#ids[@]} )) || { printf '\n'; m::wrap "You haven't blocked anyone."; m::wait; return; }
  for u in "${ids[@]}"; do n=$(m::get "profiles/$u" | m::j get -d "(unknown)" name 2>/dev/null); i=$((i+1)); printf '  %d) %s\n' "$i" "$n"; (( i >= 9 )) && break; done
  printf '\n  Press a number to unblock, q to go back '; m::key
  [[ $K =~ ^[1-9]$ && -n ${ids[K-1]:-} ]] && { m::del "blocks/$M_UID/${ids[K-1]}"; m::del "blockedBy/${ids[K-1]}/$M_UID"; m::say OK "Unblocked."; m::wait; }
}

m::purge() {   # remove everything this account owns in the database (not the sign-in)
  local ms u pair
  ms=$(m::get "users/$M_UID/matches") || ms="{}"
  for u in $(m::keys "${ms:-{\}}"); do pair=$(m::pair "$u"); m::del "chats/$pair"; m::del "matches/$pair"; m::del "users/$u/matches/$M_UID"; m::del "users/$M_UID/matches/$u"; done
  local lk; lk=$(m::get "likes/$M_UID") || lk="{}"; for u in $(m::keys "${lk:-{\}}"); do m::del "likes/$M_UID/$u"; m::del "likedBy/$u/$M_UID"; done
  local bl; bl=$(m::get "blocks/$M_UID") || bl="{}"; for u in $(m::keys "${bl:-{\}}"); do m::del "blockedBy/$u/$M_UID"; done
  m::del "passes/$M_UID"; m::del "blocks/$M_UID"; m::del "profiles/$M_UID"
  [[ -n $M_USER ]] && m::del "usernames/$M_USER"
}

m::delete_account() {
  printf '\n'; m::wrap "This permanently deletes your profile, likes, matches, chats and sign-in. It cannot be undone."
  ui::confirm "Delete everything?" N || return 1
  m::ask "Type DELETE to confirm" || return 1; [[ $REPLY == DELETE ]] || { m::say INFO "Cancelled."; return 1; }
  m::say INFO "Removing your data…"
  m::purge
  m::delete_auth && m::say OK "Your account and data are deleted." || m::say WARN "Data removed, but the sign-in could not be deleted ($(m::authmsg))."
  m::wait; return 0
}

# ── admin: reports and bans ────────────────────────────────────────────────
m::admin() {
  local r; r=$(m::req GET "mingle/userReports" && printf '%s' "$M_BODY") || { m::say ERR "Only JITETEE admins can open this (role admin or superadmin)."; return 1; }
  [[ -z $r || $r == null ]] && r="{}"
  while :; do
    m::clear; m::cols; printf '%s  ❤  Mingle admin%s\n' "$C_BOLD$C_MAGENTA" "$C_RESET"; m::hr
    local -a ids=(); local k i=0
    while IFS= read -r k; do ids+=("$k"); done < <(m::j reports open <<<"$r")
    (( ${#ids[@]} )) || { printf '\n  No open reports.\n'; m::wait; return 0; }
    for k in "${ids[@]}"; do
      i=$((i+1)); printf '  %d) %s\n' "$i" "$(m::j reports line "$k" "$(( M_W - 22 ))" <<<"$r")"; (( i >= 9 )) && break
    done
    printf '\n  Number = open · q back '; m::key
    [[ $K == q || $K == esc ]] && return 0
    [[ $K =~ ^[1-9]$ && -n ${ids[K-1]:-} ]] || continue
    local id=${ids[K-1]} about; about=$(m::j reports field "$id" about <<<"$r")
    m::clear; printf '\n  About: %s\n  By:    %s\n' "$about" "$(m::j reports field "$id" by <<<"$r")"; m::wrap "$(m::j reports field "$id" reason <<<"$r")"
    local pf; pf=$(m::get "profiles/$about") && { IFS=$'\x1f' read -r pn pa pc pu < <(m::j fields name=? age=? city=? username=? <<<"$pf"); printf '\n  Profile: %s, %s, %s @%s\n' "$pn" "$pa" "$pc" "$pu"; }
    printf '\n  b) ban user   u) unban   d) mark done   x) delete profile   q) back: '; m::key; printf '\n'
    case $K in
      b) m::put "banned/$about" "$(m::ms)" && m::patch "userReports/$id" '{"status":"done"}' && m::say OK "Banned." || m::fail; m::wait ;;
      u) m::del "banned/$about" && m::say OK "Unbanned." || m::fail; m::wait ;;
      d) m::patch "userReports/$id" '{"status":"done"}' && m::say OK "Marked done." || m::fail; m::wait ;;
      x) ui::confirm "Delete this profile?" N && { m::del "profiles/$about"; m::say OK "Deleted."; m::wait; } ;;
    esac
    r=$(m::req GET "mingle/userReports" && printf '%s' "$M_BODY"); [[ -z $r || $r == null ]] && r="{}"
  done
}

# ── main menu ──────────────────────────────────────────────────────────────
m::unread() {
  local ms; ms=$(m::get "users/$M_UID/matches") || return 0
  m::j unread "$M_UID" <<<"${ms:-}" 2>/dev/null
}

m::home() {
  while :; do
    m::fresh; local un lk; un=$(m::unread); lk=$(m::get "likedBy/$M_UID" | m::j len 2>/dev/null)
    m::clear; m::cols
    printf '%s  ❤  Mingle%s   %s%s%s\n' "$C_BOLD$C_MAGENTA" "$C_RESET" "$C_DIM" "$(m::me name)" "$C_RESET"; m::hr
    printf '\n  %s1%s  Discover\n  %s2%s  Matches %s\n  %s3%s  Likes you %s\n  %s4%s  My profile\n  %s5%s  Settings & safety\n  %s0%s  Exit\n\n' \
      "$C_GREEN" "$C_RESET" "$C_GREEN" "$C_RESET" "$([[ ${un:-0} -gt 0 ]] && printf '%s(%s new)%s' "$C_GREEN" "$un" "$C_RESET")" "$C_GREEN" "$C_RESET" "$([[ ${lk:-0} -gt 0 ]] && printf '%s(%s)%s' "$C_YELLOW" "$lk" "$C_RESET")" "$C_GREEN" "$C_RESET" "$C_GREEN" "$C_RESET" "$C_GREEN" "$C_RESET"
    printf '  Choose: '; m::key; printf '\n'
    case $K in
      1) m::discover ;;
      2) m::matches ;;
      3) m::likesme ;;
      4) m::myprofile ;;
      5) m::settings; (( $? == 9 )) && return 9 ;;
      0|q|esc) return 0 ;;
    esac
  done
}

m::banned() { local b; b=$(m::get "banned/$M_UID") && [[ -n $b && $b != null ]]; }

cmd::mingle() {
  case ${1:-} in
    help|-h|--help) cat <<'EOF'
mingle  - dating in your terminal (18+)
  mingle            open the app (sign in or create an account)
  mingle logout     forget this device's sign-in
  mingle admin      review reports and ban users (JITETEE admins only)
Sign in with email + password, or a username + key.
EOF
      return 0 ;;
    logout) rm -f "$(m::SESS)"; ui::say_status OK "Signed out of Mingle on this device."; return 0 ;;
  esac
  command -v curl >/dev/null 2>&1 || { ui::say_status ERR "curl is needed. Run: nebula install curl"; return 1; }
  apps::need python3 python || { ui::say_status ERR "Mingle needs Python 3. Run: nebula install python"; return 1; }
  [[ -t 0 && -t 1 ]] || { ui::say_status WARN "Mingle needs an interactive terminal."; return 1; }
  cloud::cfg || { ui::say_status ERR "Mingle isn't set up in this build."; return 1; }
  M_ME="{}"; M_TOK=""; M_EXP=0; M_UID=""; M_USER=""; M_ONLYCITY=""
  trap 'm::cleanup' INT
  local rc=0
  while :; do
    if ! { m::resume || { m::auth_screen && m::save; }; }; then m::cleanup; trap - INT; return 0; fi
    if [[ ${1:-} == admin ]]; then m::save; m::admin; m::cleanup; trap - INT; return 0; fi
    if m::banned; then m::clear; m::say ERR "This account has been suspended."; m::wait; rm -f "$(m::SESS)"; m::cleanup; trap - INT; return 1; fi
    if [[ -z $M_USER ]]; then   # email account: find its username (profile) or make one
      M_USER=$(m::get "profiles/$M_UID" | m::j get username 2>/dev/null)
    fi
    m::load_me
    if [[ $M_ME == "{}" ]]; then
      [[ -z $M_USER ]] && { m::pick_username || { m::cleanup; trap - INT; return 1; }; }
      m::save
      m::profile_form || {
        if (( M_UNDERAGE )); then m::purge; m::delete_auth; m::say INFO "Your sign-up was removed."; M_UNDERAGE=0
        else m::say WARN "Profile not saved. Open mingle again to finish."; rm -f "$(m::SESS)"; fi
        m::wait; m::cleanup; trap - INT; return 1; }
    fi
    m::save
    m::patch "profiles/$M_UID" '{"seen":{".sv":"timestamp"}}' >/dev/null 2>&1
    m::home; rc=$?
    (( rc == 9 )) && continue
    break
  done
  m::cleanup; trap - INT; m::clear
  ui::say_status OK "See you soon."
}
