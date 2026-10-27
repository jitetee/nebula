#!/data/data/com.termux/files/usr/bin/env bash
# nebula — games (part 1: menu, shared helpers, puzzle / word / card games)
#   game              pick a game from a menu         game <name>   start one directly
#   Real-time and simulation games live in lib/arcade.sh.

GAME_DIR="${NEBULA_CFG:-/tmp}/games"
K=""; F=""; GW=()

# ── shared helpers ───────────────────────────────────────────────────────
g::best() { local f="$GAME_DIR/scores"; [[ -f $f ]] && awk -F'|' -v k="$1" '$1==k{v=$2} END{if(v!="")print v}' "$f"; }

# g::record <name> <value> [low]  → 0 when it is a new best (lower is better with "low")
g::record() {
  [[ $2 =~ ^[0-9]+$ ]] && (( $2 > 0 )) || return 1
  mkdir -p "$GAME_DIR"; local old new=0; old=$(g::best "$1")
  if [[ -z $old ]]; then new=1
  elif [[ ${3:-} == low ]]; then (( $2 < old )) && new=1
  else (( $2 > old )) && new=1; fi
  (( new )) || return 1
  { grep -v "^$1|" "$GAME_DIR/scores" 2>/dev/null; printf '%s|%s\n' "$1" "$2"; } > "$GAME_DIR/scores.tmp" && mv "$GAME_DIR/scores.tmp" "$GAME_DIR/scores"
}

# g::key [timeout] → sets K to up|down|left|right|enter|space|esc|<char>; returns 1 on timeout
g::key() {
  local t=${1:-} c r rc; K=""
  if [[ -n $t ]]; then
    IFS= read -rsn1 -t "$t" c; rc=$?
    (( rc > 128 )) && return 1
    (( rc )) && { K=q; return 0; }
  else
    IFS= read -rsn1 c || { K=q; return 0; }
  fi
  case $c in
    $'\033') IFS= read -rsn2 -t 0.03 r
             case $r in '[A'|OA) K=up ;; '[B'|OB) K=down ;; '[C'|OC) K=right ;; '[D'|OD) K=left ;; '') K=esc ;; *) K=other ;; esac ;;
    '') K=enter ;;
    ' ') K=space ;;
    *) K=$c ;;
  esac
  return 0
}
g::norm() { case $K in w|k|W|K) K=up ;; s|j|S|J) K=down ;; a|h|A|H) K=left ;; d|l|D|L) K=right ;; esac; }
g::now_ms() { local t=${EPOCHREALTIME:-}; if [[ -n $t ]]; then t=${t/[.,]/}; printf '%s' "$(( t / 1000 ))"; else printf '%s' "$(( $(date +%s) * 1000 ))"; fi; }
g::ln() { F+="$1"$'\033[K\n'; }
g::paint() { printf '\033[H%s\033[J' "$F"; F=""; }
# colour escapes as lookup tables, so drawing a frame never forks a subshell (forks are slow on phones)
BGC=(); FGC=(); for _i in {0..255}; do BGC[_i]=$'\033[48;5;'${_i}m; FGC[_i]=$'\033[38;5;'${_i}m; done; unset _i
g::bg() { printf '%s' "${BGC[$1]}"; }
g::fg() { printf '%s' "${FGC[$1]}"; }
g::rule() { printf -v REPLY '%*s' "$2" ''; REPLY=${REPLY// /$1}; }   # g::rule <char> <count> → REPLY
g::wait() { printf '\n%s  press any key…%s' "${C_DIM:-}" "${C_RESET:-}"; IFS= read -rsn1; }
g::rows() { ui::rows 2>/dev/null || echo 24; }
g::cols() { ui::cols 2>/dev/null || echo 60; }

# Run a game in a subshell that always restores the cursor and survives Ctrl+C
g::run() {
  local fn=$1; shift
  [[ -t 0 && -t 1 ]] || { ui::say_status ERR "Games need an interactive terminal."; return 1; }
  trap ':' INT
  ( printf '\033[?25l\033[H\033[2J'
    trap 'printf "\033[?25h\033[0m\n"' EXIT
    trap 'exit 0' INT
    "$fn" "$@" )
  trap - INT
  printf '\033[?25h\033[0m'
}

g::words() { mapfile -t GW < "$NEBULA_HOME/assets/words.txt"; }
g::rand_word() { (( ${#GW[@]} )) || g::words; printf '%s' "${GW[RANDOM % ${#GW[@]}]}"; }

g::over() {   # g::over "title" "detail"   (centered-ish end screen line)
  printf '\n'; printf '%s\n' "${2:-}" | skin::box "$1"
}

# ── 2048 ─────────────────────────────────────────────────────────────────
_2048_cols=(238 223 222 215 209 203 197 227 226 220 214 208 202)
_2048_idx() {
  local d=$1 r=$2 k; IDX=()
  for k in 0 1 2 3; do
    case $d in
      left)  IDX+=($((r*4+k))) ;;  right) IDX+=($((r*4+3-k))) ;;
      up)    IDX+=($((k*4+r))) ;;  down)  IDX+=($(((3-k)*4+r))) ;;
    esac
  done
}
_2048_add() {
  local -a free=(); local i
  for ((i=0;i<16;i++)); do (( b[i] == 0 )) && free+=("$i"); done
  (( ${#free[@]} )) || return 1
  b[${free[RANDOM % ${#free[@]}]}]=$(( RANDOM % 10 == 0 ? 4 : 2 ))
}
_2048_move() {
  local d=$1 r k moved=0 v
  for r in 0 1 2 3; do
    _2048_idx "$d" "$r"
    local -a t=() out=(); for k in 0 1 2 3; do v=${b[IDX[k]]}; (( v )) && t+=("$v"); done
    local i=0 n=${#t[@]}
    while (( i < n )); do
      if (( i+1 < n && t[i] == t[i+1] )); then out+=($(( t[i]*2 ))); (( score += t[i]*2 )); (( t[i]*2 == 2048 )) && won=$((won+1)); i=$((i+2))
      else out+=("${t[i]}"); i=$((i+1)); fi
    done
    while (( ${#out[@]} < 4 )); do out+=(0); done
    for k in 0 1 2 3; do (( b[IDX[k]] != out[k] )) && moved=1; b[IDX[k]]=${out[k]}; done
  done
  (( moved ))
}
_2048_stuck() {
  local i
  for ((i=0;i<16;i++)); do
    (( b[i] == 0 )) && return 1
    (( i % 4 < 3 && b[i] == b[i+1] )) && return 1
    (( i < 12 && b[i] == b[i+4] )) && return 1
  done
  return 0
}
_2048_draw() {
  local r c v lg p tall=1 s
  (( $(g::rows) < 17 )) && tall=0
  g::ln "${C_CYAN}◆${C_RESET} ${C_BOLD}${C_CYAN}2048${C_RESET} ${C_BLUE}─${C_RESET} score $score  best $best"
  g::ln "${C_DIM}arrows/wasd move · r restart · q quit${C_RESET}"
  for r in 0 1 2 3; do
    for p in 0 1 2; do
      (( tall == 0 && p != 1 )) && continue
      s=""
      for c in 0 1 2 3; do
        v=${b[r*4+c]}; lg=0; local x=$v; while (( x > 1 )); do x=$((x/2)); lg=$((lg+1)); done
        (( lg > 12 )) && lg=12
        s+="${BGC[${_2048_cols[lg]}]}${FGC[16]}"
        if (( p == 1 && v )); then s+="$(printf '%5s ' "$v")"; elif (( p == 1 )); then s+="  .   "; else s+="      "; fi
        s+=$'\033[0m '
      done
      g::ln "$s"
    done
    (( tall )) && g::ln ""
  done
  g::paint
}
game::2048() {
  local -a b=(); local i score=0 won=0 best; best=$(g::best 2048); best=${best:-0}
  for ((i=0;i<16;i++)); do b[i]=0; done; _2048_add; _2048_add
  local shown=0
  while :; do
    (( score > best )) && best=$score
    _2048_draw
    if (( won == 1 && shown == 0 )); then shown=1; printf '  %sYou made 2048!%s keep going or press q\n' "$C_GREEN" "$C_RESET"; fi
    if _2048_stuck; then g::record 2048 "$score"; g::over "Game over" "score $score"; g::wait; return; fi
    g::key; g::norm
    case $K in
      up|down|left|right) _2048_move "$K" && _2048_add ;;
      r) for ((i=0;i<16;i++)); do b[i]=0; done; score=0; won=0; shown=0; _2048_add; _2048_add ;;
      q|esc) break ;;
    esac
  done
  g::record 2048 "$score"
}

# ── Wordle ───────────────────────────────────────────────────────────────
# g::wscore <secret> <guess> → "gyx.."  (g green, y yellow, x grey)
g::wscore() {
  local s=$1 g=$2 i res="" used=""; local -a st=()
  for ((i=0;i<5;i++)); do
    if [[ ${g:i:1} == "${s:i:1}" ]]; then st[i]=g; else st[i]=x; fi
  done
  local rest=""; for ((i=0;i<5;i++)); do [[ ${st[i]} != g ]] && rest+=${s:i:1}; done
  for ((i=0;i<5;i++)); do
    if [[ ${st[i]} == x && $rest == *"${g:i:1}"* ]]; then st[i]=y; rest=${rest/"${g:i:1}"/}; fi
  done
  for ((i=0;i<5;i++)); do res+=${st[i]}; done
  printf '%s' "$res"
}
g::wcell() { local ch=$1 st=$2 c=240; case $st in g) c=34 ;; y) c=178 ;; esac; printf '%s%s %s %s' "${BGC[c]}" "${FGC[231]}" "${ch^^}" $'\033[0m'; }
game::wordle() {
  local secret; secret=$(g::rand_word)
  local -a hist=() res=(); local tries=0 guess i line
  local -A seen=()
  printf '\033[?25h'
  while (( tries < 6 )); do
    printf '\033[H\033[2J%sWordle%s  guess the 5-letter word in 6 tries  %s(q to quit)%s\n\n' "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET"
    for ((i=0;i<tries;i++)); do
      line="  "; local j; for ((j=0;j<5;j++)); do line+="$(g::wcell "${hist[i]:j:1}" "${res[i]:j:1}") "; done; printf '%s\n' "$line"
    done
    for ((i=tries;i<6;i++)); do printf '  %s· · · · ·%s\n' "$C_DIM" "$C_RESET"; done
    local kb="" ch; for ch in {a..z}; do case ${seen[$ch]:-} in g) kb+="$C_GREEN$ch$C_RESET " ;; y) kb+="${FGC[178]}$ch$C_RESET " ;; x) kb+="$C_DIM·$C_RESET " ;; *) kb+="$ch " ;; esac; done
    printf '\n  %s\n\n' "$kb"
    while :; do
      IFS= read -r -p "  guess ${C_DIM}(5 letters)${C_RESET}: " guess || return
      guess=${guess,,}; [[ $guess == q ]] && return
      [[ $guess =~ ^[a-z]{5}$ ]] && break
      printf '  %sFive letters, a-z only.%s\n' "$C_YELLOW" "$C_RESET"
    done
    hist[tries]=$guess; res[tries]=$(g::wscore "$secret" "$guess")
    for ((i=0;i<5;i++)); do
      ch=${guess:i:1}; local st=${res[tries]:i:1}
      if [[ $st == g ]] || [[ $st == y && ${seen[$ch]:-} != g ]] || [[ -z ${seen[$ch]:-} ]]; then seen[$ch]=$st; fi
    done
    tries=$((tries+1))
    if [[ $guess == "$secret" ]]; then
      printf '\033[H\033[2J%sWordle%s\n\n' "$C_BOLD" "$C_RESET"
      for ((i=0;i<tries;i++)); do line="  "; local j; for ((j=0;j<5;j++)); do line+="$(g::wcell "${hist[i]:j:1}" "${res[i]:j:1}") "; done; printf '%s\n' "$line"; done
      g::over "Solved in $tries!" "${C_GREEN}well done${C_RESET}"; g::record wordle "$((7-tries))"; g::wait; return
    fi
  done
  g::over "Out of tries" "the word was ${C_BOLD}${secret^^}${C_RESET}"; g::wait
}

# ── Hangman ──────────────────────────────────────────────────────────────
game::hangman() {
  local word; word=$(g::rand_word); local -A tried=(); local wrong=0 i ch shown ok
  local -a art=(
"




" "




 ___" "
   |
   |
   |
   |
 __|__" "
   +---+
   |
   |
   |
 __|__" "
   +---+
   |   O
   |
   |
 __|__" "
   +---+
   |   O
   |  /|\\
   |
 __|__" "
   +---+
   |   O
   |  /|\\
   |  / \\
 __|__")
  while :; do
    shown=""; ok=1
    for ((i=0;i<5;i++)); do ch=${word:i:1}; if [[ -n ${tried[$ch]:-} ]]; then shown+="$ch "; else shown+="_ "; ok=0; fi; done
    printf '\033[H\033[2J%sHangman%s  %s(type a letter, 1 to quit)%s\n%s\n\n  %s%s%s\n\n' "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET" "${art[wrong]}" "$C_CYAN$C_BOLD" "${shown^^}" "$C_RESET"
    local used=""; for ch in "${!tried[@]}"; do [[ $word != *"$ch"* ]] && used+="$ch "; done
    printf '  wrong: %s%s%s   (%s left)\n' "$C_RED" "$used" "$C_RESET" "$((6-wrong))"
    (( ok )) && { g::over "You got it!" "${word^^}"; g::record hangman "$((6-wrong))"; g::wait; return; }
    (( wrong >= 6 )) && { g::over "Hanged" "the word was ${C_BOLD}${word^^}${C_RESET}"; g::wait; return; }
    g::key
    [[ $K == 1 || $K == esc ]] && return
    [[ $K =~ ^[a-zA-Z]$ ]] || continue
    ch=${K,,}; [[ -n ${tried[$ch]:-} ]] && continue
    tried[$ch]=1; [[ $word == *"$ch"* ]] || wrong=$((wrong+1))
  done
}

# ── Number guess ─────────────────────────────────────────────────────────
game::guess() {
  local max=100 secret tries=0 g lo=1 hi
  secret=$(( RANDOM % max + 1 )); hi=$max
  printf '\033[?25h\033[H\033[2J%sNumber guess%s  I picked a number from 1 to %s. You have 7 tries.\n\n' "$C_BOLD" "$C_RESET" "$max"
  while (( tries < 7 )); do
    IFS= read -r -p "  [$((7-tries)) left, range $lo-$hi] your guess: " g || return
    [[ $g == q ]] && return
    [[ $g =~ ^[0-9]+$ ]] || { printf '  %sA whole number please.%s\n' "$C_YELLOW" "$C_RESET"; continue; }
    tries=$((tries+1))
    if (( g == secret )); then g::over "Correct!" "in $tries tries"; g::record guess "$((8-tries))"; g::wait; return
    elif (( g < secret )); then printf '  %s↑ higher%s\n' "$C_CYAN" "$C_RESET"; (( g >= lo )) && lo=$((g+1))
    else printf '  %s↓ lower%s\n' "$C_CYAN" "$C_RESET"; (( g <= hi )) && hi=$((g-1)); fi
  done
  g::over "Out of tries" "it was $secret"; g::wait
}

# g::mmscore <secret> <guess> → MM_EXACT MM_PART
g::mmscore() {
  local sec=$1 g=$2 i sr="" gr=""; MM_EXACT=0; MM_PART=0
  for ((i=0;i<${#sec};i++)); do
    if [[ ${g:i:1} == "${sec:i:1}" ]]; then MM_EXACT=$((MM_EXACT+1)); else sr+=${sec:i:1}; gr+=${g:i:1}; fi
  done
  for ((i=0;i<${#gr};i++)); do if [[ $sr == *"${gr:i:1}"* ]]; then MM_PART=$((MM_PART+1)); sr=${sr/"${gr:i:1}"/}; fi; done
}

# ── Mastermind ───────────────────────────────────────────────────────────
game::mastermind() {
  local secret="" i; for i in 1 2 3 4; do secret+=$(( RANDOM % 6 + 1 )); done
  local -a hist=() fb=(); local tries=0 g
  printf '\033[?25h'
  while (( tries < 10 )); do
    printf '\033[H\033[2J%sMastermind%s  crack the 4-digit code (digits 1-6, repeats allowed)\n%s●%s right digit & place   %s○%s right digit, wrong place   (q quits)\n\n' "$C_BOLD" "$C_RESET" "$C_GREEN" "$C_RESET" "$C_YELLOW" "$C_RESET"
    for ((i=0;i<tries;i++)); do printf '  %2d.  %s   %s\n' "$((i+1))" "${hist[i]}" "${fb[i]}"; done
    printf '\n'
    while :; do
      IFS= read -r -p "  guess: " g || return
      [[ $g == q ]] && return
      [[ $g =~ ^[1-6]{4}$ ]] && break
      printf '  %sFour digits, each 1-6.%s\n' "$C_YELLOW" "$C_RESET"
    done
    g::mmscore "$secret" "$g"; local exact=$MM_EXACT part=$MM_PART
    local pegs=""; for ((i=0;i<exact;i++)); do pegs+="${C_GREEN}●${C_RESET} "; done; for ((i=0;i<part;i++)); do pegs+="${C_YELLOW}○${C_RESET} "; done
    hist[tries]=$g; fb[tries]=$pegs; tries=$((tries+1))
    if (( exact == 4 )); then g::over "Cracked in $tries!" "$secret"; g::record mastermind "$((11-tries))"; g::wait; return; fi
  done
  g::over "Out of tries" "the code was $secret"; g::wait
}

# ── Memory match ─────────────────────────────────────────────────────────
game::memory() {
  local -a card=() st=(); local i j t n=16 cur=0 first=-1 moves=0 found=0
  local -a syms=(A B C D E F G H)
  for ((i=0;i<n;i++)); do card[i]=${syms[i/2]}; st[i]=0; done
  for ((i=n-1;i>0;i--)); do j=$((RANDOM % (i+1))); t=${card[i]}; card[i]=${card[j]}; card[j]=$t; done
  local draw=1 k r c line cell mbest; mbest=$(g::best memory); [[ -n $mbest ]] && mbest="best: $mbest moves"
  while :; do
    g::ln "${C_CYAN}◆${C_RESET} ${C_BOLD}${C_CYAN}Memory${C_RESET} ${C_BLUE}─${C_RESET} moves $moves  pairs $found/8  ${C_DIM}$mbest${C_RESET}"
    g::ln "${C_DIM}arrows move · enter flips · q quits${C_RESET}"
    g::ln ""
    for r in 0 1 2 3; do
      line="  "
      for c in 0 1 2 3; do
        k=$((r*4+c))
        case ${st[k]} in
          0) cell=" ? " ;;
          *) cell=" ${card[k]} " ;;
        esac
        local bgc=238; [[ ${st[k]} == 2 ]] && bgc=34; [[ ${st[k]} == 1 ]] && bgc=178
        local pre="${BGC[bgc]}${FGC[231]}"; (( k == cur )) && pre=$'\033[7m'"$pre"
        line+="$pre$cell"$'\033[0m  '
      done
      g::ln "$line"; g::ln ""
    done
    g::paint
    if (( found == 8 )); then g::over "Cleared in $moves moves" ""; g::record memory "$moves" low; g::wait; return; fi
    g::key; g::norm
    case $K in
      left)  (( cur % 4 > 0 )) && cur=$((cur-1)) ;;  right) (( cur % 4 < 3 )) && cur=$((cur+1)) ;;
      up)    (( cur >= 4 )) && cur=$((cur-4)) ;;     down)  (( cur < 12 )) && cur=$((cur+4)) ;;
      q|esc) return ;;
      enter|space)
        (( st[cur] != 0 )) && continue
        st[cur]=1
        if (( first < 0 )); then first=$cur
        else
          moves=$((moves+1))
          if [[ ${card[cur]} == "${card[first]}" ]]; then st[cur]=2; st[first]=2; found=$((found+1))
          else
            # draw the mismatch for a moment, then hide again
            for r in 0; do :; done
            F=""; local rr cc kk ll cl
            g::ln "${C_CYAN}◆${C_RESET} ${C_BOLD}${C_CYAN}Memory${C_RESET} ${C_BLUE}─${C_RESET} moves $moves  pairs $found/8"; g::ln ""; g::ln ""
            for rr in 0 1 2 3; do ll="  "; for cc in 0 1 2 3; do kk=$((rr*4+cc)); cl=" ? "; [[ ${st[kk]} != 0 ]] && cl=" ${card[kk]} "
              local b2=238; [[ ${st[kk]} == 1 ]] && b2=160; [[ ${st[kk]} == 2 ]] && b2=34; ll+="${BGC[b2]}${FGC[231]}$cl"$'\033[0m  '; done; g::ln "$ll"; g::ln ""; done
            g::paint; sleep 0.9; st[cur]=0; st[first]=0
          fi
          first=-1
        fi ;;
    esac
  done
}

# (uses W H M mine cnt st opened from the calling game)
ms::neigh() { local p=$1 px py dx dy; px=$((p%W)); py=$((p/W)); NB=(); for dy in -1 0 1; do for dx in -1 0 1; do (( dx||dy )) || continue
    (( px+dx>=0 && px+dx<W && py+dy>=0 && py+dy<H )) && NB+=($(( (py+dy)*W + px+dx ))); done; done; }
ms::place() {
  local safe=" $1 " n=0 p q; ms::neigh "$1"; for q in "${NB[@]}"; do safe+="$q "; done
  while (( n < M )); do p=$(( RANDOM % (W*H) )); [[ $safe == *" $p "* || ${mine[p]} == 1 ]] && continue; mine[p]=1; n=$((n+1)); done
  for ((p=0;p<W*H;p++)); do ms::neigh "$p"; local c=0; for q in "${NB[@]}"; do (( mine[q] )) && c=$((c+1)); done; cnt[p]=$c; done
}
ms::open() {
  local -a stack=("$1"); local p q
  while (( ${#stack[@]} )); do
    p=${stack[-1]}; unset 'stack[-1]'
    (( st[p] != 0 )) && continue
    st[p]=1; opened=$((opened+1))
    if (( cnt[p] == 0 && mine[p] == 0 )); then ms::neigh "$p"; for q in "${NB[@]}"; do (( st[q] == 0 )) && stack+=("$q"); done; fi
  done
}

# ── Minesweeper ──────────────────────────────────────────────────────────
game::minesweeper() {
  local cols rows W H M; cols=$(g::cols); rows=$(g::rows)
  W=$(( (cols - 4) / 2 )); (( W > 12 )) && W=12; (( W < 6 )) && W=6
  H=$(( rows - 6 )); (( H > 10 )) && H=10; (( H < 5 )) && H=5
  M=$(( W * H / 6 ))
  local -a mine=() cnt=() st=(); local i x y cx=0 cy=0 first=1 flags=0 opened=0 dead=0
  for ((i=0;i<W*H;i++)); do mine[i]=0; cnt[i]=0; st[i]=0; done
  local t0=$SECONDS
  local numc=(0 75 76 203 99 124 37 241 250) line
  while :; do
    g::ln "${C_CYAN}◆${C_RESET} ${C_BOLD}${C_CYAN}Minesweeper${C_RESET} ${C_BLUE}─${C_RESET} mines $((M-flags))  time $((SECONDS-t0))s"
    g::ln "${C_DIM}arrows move · space/enter open · f flag · q quit${C_RESET}"
    for ((y=0;y<H;y++)); do
      line=" "
      for ((x=0;x<W;x++)); do
        i=$((y*W+x)); local s="" ch="· " col=245
        if (( st[i] == 1 )); then
          if (( mine[i] )); then ch="* "; col=203
          elif (( cnt[i] == 0 )); then ch="  "; else ch="${cnt[i]} "; col=${numc[cnt[i]]}; fi
        elif (( st[i] == 2 )); then ch="F "; col=221
        elif (( dead && mine[i] )); then ch="* "; col=203; fi
        s="${FGC[col]}$ch"$'\033[0m'
        (( !dead && x == cx && y == cy )) && s=$'\033[7m'"$s"
        line+="$s"
      done
      g::ln "$line"
    done
    g::paint
    if (( dead )); then g::over "Boom." ""; g::wait; return; fi
    if (( opened == W*H - M )); then
      local secs=$((SECONDS-t0)); g::over "Cleared!" "in ${secs}s"; g::record minesweeper "$secs" low; g::wait; return
    fi
    g::key; g::norm
    case $K in
      left)  (( cx > 0 )) && cx=$((cx-1)) ;;   right) (( cx < W-1 )) && cx=$((cx+1)) ;;
      up)    (( cy > 0 )) && cy=$((cy-1)) ;;   down)  (( cy < H-1 )) && cy=$((cy+1)) ;;
      f|F)   i=$((cy*W+cx)); if (( st[i] == 0 )); then st[i]=2; flags=$((flags+1)); elif (( st[i] == 2 )); then st[i]=0; flags=$((flags-1)); fi ;;
      enter|space)
        i=$((cy*W+cx)); (( st[i] != 0 )) && continue
        (( first )) && { ms::place "$i"; first=0; t0=$SECONDS; }
        if (( mine[i] )); then dead=1; st[i]=1; else ms::open "$i"; fi ;;
      q|esc) return ;;
    esac
  done
}

# ── Quiz ─────────────────────────────────────────────────────────────────
game::quiz() {
  local f="$NEBULA_HOME/assets/quiz.txt" cat=${1:-} pool
  [[ -f $f ]] || { ui::say_status ERR "quiz.txt is missing"; return 1; }
  if [[ -z $cat ]]; then
    printf '\033[?25h\033[H\033[2J%sQuiz%s  pick a topic\n\n' "$C_BOLD" "$C_RESET"
    printf '  1  Kenya\n  2  Coding\n  3  Bible\n  4  General\n  5  Everything\n\n'
    local p; IFS= read -r -p "  topic (1-5): " p || return
    case $p in 1) cat=Kenya ;; 2) cat=Coding ;; 3) cat=Bible ;; 4) cat=General ;; *) cat=all ;; esac
  fi
  if [[ ${cat,,} == all ]]; then pool=$(cat "$f"); else pool=$(grep -i "^$cat|" "$f"); fi
  [[ -n $pool ]] || { ui::say_status ERR "No questions for '$cat'"; return 1; }
  local picked; picked=$(printf '%s\n' "$pool" | (shuf 2>/dev/null || sort -R) | head -5)
  local score=0 n=0 total; total=$(printf '%s\n' "$picked" | grep -c '')
  local c q a b cc d ans
  while IFS='|' read -r c q a b cc d ans; do
    n=$((n+1))
    printf '\033[H\033[2J%sQuiz%s  %s  question %s of %s   score %s\n\n  %s%s%s\n\n' "$C_BOLD" "$C_RESET" "$c" "$n" "$total" "$score" "$C_BOLD" "$q" "$C_RESET"
    printf '  A  %s\n  B  %s\n  C  %s\n  D  %s\n\n  %spress a, b, c or d (q quits)%s\n' "$a" "$b" "$cc" "$d" "$C_DIM" "$C_RESET"
    while :; do g::key; [[ $K == q ]] && return; [[ ${K^^} =~ ^[ABCD]$ ]] && break; done
    if [[ ${K^^} == "$ans" ]]; then score=$((score+1)); printf '\n  %s✔ Correct%s\n' "$C_GREEN" "$C_RESET"
    else printf '\n  %s✖ Not quite.%s Answer: %s\n' "$C_RED" "$C_RESET" "$ans"; fi
    sleep 1.1
  done <<<"$picked"
  g::over "Score $score/$total" ""; g::record "quiz-${cat,,}" "$score"; g::wait
}

# ── Typing test ──────────────────────────────────────────────────────────
game::typing() {
  g::words
  local -a pick=(); local i
  for ((i=0;i<12;i++)); do pick+=("${GW[RANDOM % ${#GW[@]}]}"); done
  local text="${pick[*]}" typed
  printf '\033[?25h\033[H\033[2J%sTyping test%s  type this, then press Enter. The clock starts when you do.\n\n  %s%s%s\n\n' "$C_BOLD" "$C_RESET" "$C_CYAN" "$text" "$C_RESET"
  printf '  %sready…%s' "$C_DIM" "$C_RESET"; sleep 1.2; printf '\r  %sGO!%s   \n\n' "$C_GREEN" "$C_RESET"
  local t0; t0=$(g::now_ms)
  IFS= read -r -p "  > " typed || return
  local ms=$(( $(g::now_ms) - t0 )); (( ms < 1 )) && ms=1
  local -a tw=($typed) ow=("${pick[@]}"); local ok=0
  for ((i=0;i<${#ow[@]};i++)); do [[ ${tw[i]:-} == "${ow[i]}" ]] && ok=$((ok+1)); done
  local chars=0; for ((i=0;i<${#ow[@]};i++)); do [[ ${tw[i]:-} == "${ow[i]}" ]] && chars=$((chars + ${#ow[i]} + 1)); done
  local wpm=$(( chars * 12000 / ms )); local acc=$(( ok * 100 / ${#ow[@]} ))
  g::over "$wpm WPM" "accuracy ${acc}%  ·  $ok/${#ow[@]} words right  ·  $((ms/1000)).$((ms%1000/100))s"
  g::record typing "$wpm" && printf '  %s★ new best!%s\n' "$C_YELLOW" "$C_RESET"
  g::wait
}

# ── Daily puzzle (same for everyone each day, with a streak) ─────────────
game::daily() {
  mkdir -p "$GAME_DIR"; local sf="$GAME_DIR/daily" today day idx kind q a
  today=$(date +%Y%m%d); day=$(( 10#$(date +%j) )); idx=$(( day % 3 ))
  local last=0 streak=0 done_=0
  [[ -f $sf ]] && IFS='|' read -r last streak done_ < "$sf"
  last=${last:-0}; streak=${streak:-0}
  if [[ $last == "$today" && ${done_:-0} == 1 ]]; then
    printf '\033[H\033[2J%sDaily puzzle%s\n\n  %sSolved already today.%s Streak: %s day(s). Come back tomorrow!\n' "$C_BOLD" "$C_RESET" "$C_GREEN" "$C_RESET" "$streak"; g::wait; return
  fi
  local yday; yday=$(date -d yesterday +%Y%m%d 2>/dev/null || echo 0)
  [[ $last != "$today" && $last != "$yday" ]] && streak=0
  RANDOM=$today
  case $idx in
    0) kind="Riddle"; local line; line=$(sed -n "$(( day % $(grep -c '' "$NEBULA_HOME/assets/riddles.txt") + 1 ))p" "$NEBULA_HOME/assets/riddles.txt"); q=${line%%|*}; a=${line##*|} ;;
    1) kind="Quick maths"; local x=$((RANDOM%40+10)) y=$((RANDOM%9+3)) z=$((RANDOM%50+5)); q="$x × $y + $z = ?"; a=$((x*y+z)) ;;
    *) kind="Unscramble"; g::words; local w=${GW[RANDOM % ${#GW[@]}]} sc="" i j t; local -a ch=(); for ((i=0;i<5;i++)); do ch[i]=${w:i:1}; done
       for ((i=4;i>0;i--)); do j=$((RANDOM%(i+1))); t=${ch[i]}; ch[i]=${ch[j]}; ch[j]=$t; done
       sc=$(printf '%s' "${ch[@]}"); [[ $sc == "$w" ]] && sc=$(printf '%s' "${ch[4]}${ch[0]}${ch[1]}${ch[2]}${ch[3]}"); q="Unscramble: ${sc^^}"; a=$w ;;
  esac
  printf '\033[?25h\033[H\033[2J%sDaily puzzle%s  %s  ·  streak %s\n\n  %s\n\n' "$C_BOLD" "$C_RESET" "$kind" "$streak" "$q"
  local tries=0 g
  while (( tries < 3 )); do
    IFS= read -r -p "  answer ($((3-tries)) tries, q quits): " g || return
    [[ $g == q ]] && return
    g=${g,,}; g=${g//[[:space:]]/}
    if [[ $g == "${a,,}" ]]; then
      streak=$((streak+1)); printf '%s|%s|1\n' "$today" "$streak" > "$sf"
      g::over "Correct!" "streak: $streak day(s)"; g::record daily-streak "$streak"; g::wait; return
    fi
    tries=$((tries+1)); printf '  %sNo.%s\n' "$C_RED" "$C_RESET"
  done
  printf '%s|%s|0\n' "$today" "$streak" > "$sf"
  g::over "Answer" "$a"; g::wait
}

# ── Quest: AI text adventure (needs tgpt) ────────────────────────────────
game::quest() {
  cmd::_need_tgpt || return 1
  mkdir -p "$GAME_DIR"; local sv="$GAME_DIR/quest.save" theme turn=0 line reply
  printf '\033[?25h'
  if [[ -s $sv && ${1:-} != new ]]; then
    printf '\033[H\033[2J%sQuest%s  an adventure told by the Nebula AI\n\n  You have a saved adventure.\n' "$C_BOLD" "$C_RESET"
    if ui::confirm "Continue it?" Y; then :; else : > "$sv"; fi
  fi
  if [[ ! -s $sv ]]; then
    printf '\033[H\033[2J%sQuest%s\n\n  Pick a world (or type your own):\n   1 Fantasy kingdom   2 Space station   3 Nairobi heist   4 Haunted village\n\n' "$C_BOLD" "$C_RESET"
    IFS= read -r -p "  world: " theme || return
    case $theme in 1) theme="a fantasy kingdom" ;; 2) theme="an abandoned space station" ;; 3) theme="a daring heist in Nairobi" ;; 4) theme="a haunted village" ;; "") theme="a fantasy kingdom" ;; esac
    printf 'WORLD: %s\n' "$theme" > "$sv"
    printf '\n  %sThe story begins…%s\n' "$C_DIM" "$C_RESET"
    reply=$(ai::_complete "You are the game master of a text adventure set in $theme. Open the story in under 80 words, describe where the player is, and end with a question about what they do. Do not use markdown.")
    printf 'GM: %s\n' "$reply" >> "$sv"
  fi
  local cols; cols=$(ui::cols)
  while :; do
    printf '\033[H\033[2J%sQuest%s  %s(type what you do · save = leave · new = restart)%s\n\n' "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET"
    tail -n 6 "$sv" | grep -v '^WORLD:' | sed 's/^GM: //' | ui::wrap "$((cols-1))" 0
    printf '\n'
    IFS= read -r -p "  ${C_CYAN}›${C_RESET} " line || return
    case $line in
      "") continue ;;
      save|q|quit|exit) printf '  %sSaved. Continue anytime with: game quest%s\n' "$C_GREEN" "$C_RESET"; sleep 1; return ;;
      new) : > "$sv"; game::quest new; return ;;
    esac
    printf 'PLAYER: %s\n' "$line" >> "$sv"
    local ctx; ctx=$(tail -n 10 "$sv")
    printf '  %s…%s' "$C_DIM" "$C_RESET"
    reply=$(ai::_complete "You are the game master of an ongoing text adventure. Recent history (GM = you, PLAYER = the player):
$ctx

Continue the story in under 80 words in response to the player's last action. Keep it fun and fair. End with what the player can do next. No markdown.")
    printf '\r\033[2K'
    [[ -z $reply ]] && reply="The world is silent for a moment. (The AI did not answer, try again.)"
    printf 'GM: %s\n' "$reply" >> "$sv"
  done
}

# ── menu ─────────────────────────────────────────────────────────────────
GAME_LIST=(
"2048|2048|slide and merge tiles"
"wordle|Wordle|guess the 5-letter word"
"hangman|Hangman|save the stick figure"
"guess|Number guess|higher or lower"
"mastermind|Mastermind|crack the code"
"memory|Memory|match the pairs"
"minesweeper|Minesweeper|clear the field"
"snake|Snake|eat, grow, don't crash"
"tetris|Tetris|stack the blocks"
"life|Game of Life|watch cells evolve"
"ecosystem|Ecosystem|grass, rabbits and foxes"
"tycoon|Café Tycoon|run a cyber café for 30 days"
"versus|Versus (online)|tic-tac-toe against a friend"
"quest|Quest|AI text adventure"
"quiz|Quiz|Kenya, coding, Bible, general"
"typing|Typing test|how fast are you"
"daily|Daily puzzle|one a day, keep the streak"
"rain|Matrix rain|screensaver"
"fire|Fireplace|screensaver"
)
GAME_BEST_LABEL=( "2048|score" "wordle|" "hangman|" "snake|score" "tetris|score" "typing|wpm" "tycoon|KES" "minesweeper|s" "memory|moves" )

game::_label_best() {
  local n=$1 b; b=$(g::best "$n"); [[ -z $b ]] && return
  case $n in
    typing) printf 'best %s wpm' "$b" ;; tycoon) printf 'best KES %s' "$b" ;;
    minesweeper) printf 'best %ss' "$b" ;; memory) printf 'best %s moves' "$b" ;;
    wordle|hangman|guess|mastermind) printf 'won' ;;
    daily-streak) printf 'streak %s' "$b" ;;
    *) printf 'best %s' "$b" ;;
  esac
}

cmd::game() {
  local want=${1:-}
  if [[ -n $want ]]; then
    shift
    case ${want,,} in
      ls|list) local e n=0; for e in "${GAME_LIST[@]}"; do IFS='|' read -r k t d <<<"$e"; n=$((n+1)); printf '%s\t🎮\t%s\t%s\n' "$k" "$t" "$d"; done | skin::menu "Nebula games" --nodot; return 0 ;;
      scores)  if [[ -s $GAME_DIR/scores ]]; then { printf 'Game\tBest\n'; awk -F'|' '{printf "%s\t%s\n",$1,$2}' "$GAME_DIR/scores"; } | skin::table "High scores"; else ui::say_status INFO "No scores yet. Play something!"; fi; return 0 ;;
      2048|wordle|hangman|guess|mastermind|memory|minesweeper|quiz|typing|daily|quest|versus|snake|tetris|life|ecosystem|tycoon|rain|fire)
        g::run "game::${want,,}" "$@"; return ;;
      *) ui::say_status ERR "No game called '$want'. Try: game ls"; return 1 ;;
    esac
  fi
  [[ -t 0 && -t 1 ]] || { cmd::game ls; return 0; }
  local -a items=(); local e k t d
  while :; do
    items=(); for e in "${GAME_LIST[@]}"; do IFS='|' read -r k t d <<<"$e"; items+=("$t"$'\t'"$(game::_label_best "$k")"$'\t'"d"); done
    MENU_INFO=""; MENU_CUR=${MENU_CUR:-0}
    menu::pick "Nebula games" "↑/↓ choose · Enter play · q leave" items || break
    IFS='|' read -r k t d <<<"${GAME_LIST[MENU_IDX]}"
    g::run "game::$k"
  done
  printf '\033[H\033[2J'
}
