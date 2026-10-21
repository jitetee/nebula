#!/data/data/com.termux/files/usr/bin/env bash
# nebula — games (part 2: real-time games, simulations, screensavers, tycoon)
# Needs the helpers from lib/games.sh (g::key, g::paint, g::record, …).

# g::tick <ms> : read keys until the deadline, calling g::onkey for each. Sets QUIT=1 on q.
g::tick() {
  local end rem now ms
  now=${EPOCHREALTIME/[.,]/}; end=$(( now / 1000 + $1 ))
  while :; do
    now=${EPOCHREALTIME/[.,]/}; rem=$(( end - now / 1000 )); (( rem <= 0 )) && return 0
    printf -v ms '%d.%03d' "$(( rem / 1000 ))" "$(( rem % 1000 ))"
    if g::key "$ms"; then
      g::norm
      case $K in q|esc) QUIT=1; return 0 ;; esac
      g::onkey
    fi
  done
}

# ── Snake ────────────────────────────────────────────────────────────────
game::snake() {
  local cols rows W H; cols=$(g::cols); rows=$(g::rows)
  W=$(( (cols - 2) / 2 )); (( W > 24 )) && W=24; (( W < 8 )) && W=8
  H=$(( rows - 5 )); (( H > 16 )) && H=16; (( H < 8 )) && H=8
  local -a body=(); local -A occ=(); local dir=right ndir=right score=0 food speed=170 QUIT=0 best i x y hd
  best=$(g::best snake); best=${best:-0}; g::rule ─ $((W*2)); local HR=$REPLY
  x=$((W/2)); y=$((H/2)); for i in 0 1 2; do body+=($(( y*W + x - 2 + i ))); occ[$((y*W + x - 2 + i))]=1; done
  _sn_food() { local p; while :; do p=$(( RANDOM % (W*H) )); [[ -z ${occ[$p]:-} ]] && { food=$p; return; }; done; }
  _sn_food
  g::onkey() {
    case $K in
      up)    [[ $dir != down ]]  && ndir=up ;;    down)  [[ $dir != up ]]    && ndir=down ;;
      left)  [[ $dir != right ]] && ndir=left ;;  right) [[ $dir != left ]]  && ndir=right ;;
    esac
  }
  [[ ${SNAKE_FOOD:-} =~ ^[0-9]+$ ]] && food=$SNAKE_FOOD
  while (( ! QUIT )); do
    g::ln "${C_BOLD}Snake${C_RESET}  score $score  best $best   ${C_DIM}arrows/wasd · q quits${C_RESET}"
    g::ln "┌${HR}┐"
    local r c s line
    for ((r=0;r<H;r++)); do
      line="│"
      for ((c=0;c<W;c++)); do
        i=$((r*W+c))
        if (( i == food )); then line+="${BGC[196]}  "$'\033[0m'
        elif [[ -n ${occ[$i]:-} ]]; then if (( i == body[-1] )); then line+="${BGC[46]}  "$'\033[0m'; else line+="${BGC[34]}  "$'\033[0m'; fi
        else line+="  "; fi
      done
      g::ln "$line│"
    done
    g::ln "└${HR}┘"
    g::paint
    g::tick "$speed"; (( QUIT )) && break
    dir=$ndir; hd=${body[-1]}; x=$((hd%W)); y=$((hd/W))
    case $dir in up) y=$((y-1)) ;; down) y=$((y+1)) ;; left) x=$((x-1)) ;; right) x=$((x+1)) ;; esac
    if (( x < 0 || x >= W || y < 0 || y >= H )); then break; fi
    local np=$(( y*W + x )) tail=${body[0]}
    # the tail cell is free this move unless we are eating
    if [[ -n ${occ[$np]:-} && $np != "$tail" ]]; then break; fi
    body+=("$np"); occ[$np]=1
    if (( np == food )); then score=$((score+10)); (( speed > 70 )) && speed=$((speed-4)); _sn_food
    else unset "occ[$tail]"; body=("${body[@]:1}"); occ[$np]=1; fi
  done
  g::record snake "$score" && printf '\n  %s★ new best!%s' "$C_YELLOW" "$C_RESET"
  g::over "Game over" "score $score"; g::wait
}

# ── Tetris ───────────────────────────────────────────────────────────────
_t_rot() { local s="" p x y; for p in $1; do x=${p%,*}; y=${p#*,}; s+="$((-y)),$x "; done; printf '%s' "${s% }"; }
_t_fits() {   # px py "shape"
  local p x y
  for p in $3; do x=$(( $1 + ${p%,*} )); y=$(( $2 + ${p#*,} )); (( x < 0 || x >= W || y >= H )) && return 1; (( y >= 0 && bd[y*W+x] )) && return 1; done
  return 0
}
game::tetris() {
  local rows W=10 H; rows=$(g::rows); H=$(( rows - 5 )); (( H > 20 )) && H=20
  if (( H < 12 )); then printf '  %sScreen too short for Tetris.%s Close the keyboard or rotate the phone.\n' "$C_YELLOW" "$C_RESET"; g::wait; return; fi
  local -a bd=() shapes=("-1,0 0,0 1,0 2,0" "0,0 1,0 0,1 1,1" "-1,0 0,0 1,0 0,1" "0,0 1,0 -1,1 0,1" "-1,0 0,0 0,1 1,1" "-1,0 0,0 1,0 -1,1" "-1,0 0,0 1,0 1,1")
  local -a tcol=(51 226 129 46 196 21 208)
  local i; for ((i=0;i<W*H;i++)); do bd[i]=0; done
  local cur nxt px py ct score=0 lines=0 level=1 QUIT=0 best over=0 delay; best=$(g::best tetris); best=${best:-0}; g::rule ─ $((W*2)); local HR=$REPLY
  local seqi=0; local -a fseq=(${TETRIS_SEQ:-})
  _t_next() { if (( ${#fseq[@]} )); then nxt=${fseq[seqi % ${#fseq[@]}]}; seqi=$((seqi+1)); else nxt=$((RANDOM%7)); fi; }
  _t_spawn() { ct=$nxt; _t_next; cur=${shapes[ct]}; px=$((W/2-1)); py=0; _t_fits "$px" "$py" "$cur" || over=1; }
  _t_lock() {
    local p x y full r c cleared=0
    for p in $cur; do x=$(( px + ${p%,*} )); y=$(( py + ${p#*,} )); (( y >= 0 )) && bd[y*W+x]=$((ct+1)); done
    for ((r=H-1;r>=0;r--)); do
      full=1; for ((c=0;c<W;c++)); do (( bd[r*W+c] )) || { full=0; break; }; done
      if (( full )); then
        cleared=$((cleared+1))
        for ((y=r;y>0;y--)); do for ((c=0;c<W;c++)); do bd[y*W+c]=${bd[(y-1)*W+c]}; done; done
        for ((c=0;c<W;c++)); do bd[c]=0; done
        r=$((r+1))
      fi
    done
    if (( cleared )); then
      local pts=(0 100 300 500 800); score=$(( score + ${pts[cleared]} * level )); lines=$((lines+cleared)); level=$(( lines/10 + 1 ))
    fi
    _t_spawn
  }
  g::onkey() {
    local t
    case $K in
      left)  _t_fits "$((px-1))" "$py" "$cur" && px=$((px-1)) ;;
      right) _t_fits "$((px+1))" "$py" "$cur" && px=$((px+1)) ;;
      down)  if _t_fits "$px" "$((py+1))" "$cur"; then py=$((py+1)); score=$((score+1)); fi ;;
      up|x)  (( ct == 1 )) && return; t=$(_t_rot "$cur")
             if _t_fits "$px" "$py" "$t"; then cur=$t
             elif _t_fits "$((px-1))" "$py" "$t"; then cur=$t; px=$((px-1))
             elif _t_fits "$((px+1))" "$py" "$t"; then cur=$t; px=$((px+1)); fi ;;
      space) while _t_fits "$px" "$((py+1))" "$cur"; do py=$((py+1)); score=$((score+2)); done; _t_lock ;;
    esac
  }
  _t_next; _t_spawn
  while (( ! QUIT && ! over )); do
    delay=$(( 520 - (level-1)*45 )); (( delay < 90 )) && delay=90
    local -A ov=(); local p r c line
    for p in $cur; do ov[$(( (py + ${p#*,}) * W + px + ${p%,*} ))]=$((ct+1)); done
    g::ln "${C_BOLD}Tetris${C_RESET}  score $score  best $best  lines $lines  lvl $level"
    g::ln "${C_DIM}←→ move · ↑ rotate · ↓ drop · space slam · q${C_RESET}   next: ${BGC[${tcol[nxt]}]}  ${C_RESET}"
    g::ln "┌${HR}┐"
    for ((r=0;r<H;r++)); do
      line="│"
      for ((c=0;c<W;c++)); do
        i=$((r*W+c)); local v=${ov[$i]:-${bd[i]}}
        if (( v )); then line+="${BGC[${tcol[v-1]}]}  "$'\033[0m'; else line+="${FGC[238]}· "$'\033[0m'; fi
      done
      g::ln "$line│"
    done
    g::ln "└${HR}┘"
    g::paint
    g::tick "$delay"; (( QUIT )) && break
    if _t_fits "$px" "$((py+1))" "$cur"; then py=$((py+1)); else _t_lock; fi
  done
  g::record tetris "$score" && printf '\n  %s★ new best!%s' "$C_YELLOW" "$C_RESET"
  g::over "Game over" "score $score · $lines lines"; g::wait
}

# (uses W H S gen from the calling game)
life::step() {
  S=$(awk -v W="$W" -v H="$H" -v s="$S" 'BEGIN{for(i=0;i<W*H;i++)a[i]=substr(s,i+1,1)+0
    for(y=0;y<H;y++)for(x=0;x<W;x++){n=0;for(dy=-1;dy<=1;dy++)for(dx=-1;dx<=1;dx++)if(dx||dy)n+=a[((y+dy+H)%H)*W+(x+dx+W)%W]
      c=a[y*W+x]; r=r ((n==3||(c&&n==2))?1:0)} print r}')
  gen=$((gen+1))
}

# ── Game of Life ─────────────────────────────────────────────────────────
game::life() {
  local cols rows W H S i x y; cols=$(g::cols); rows=$(g::rows)
  W=$(( cols - 2 )); (( W > 60 )) && W=60; (( W < 12 )) && W=12
  H=$(( (rows - 4) )); (( H > 24 )) && H=24; (( H < 6 )) && H=6
  local gen=0 paused=0 speed=120 QUIT=0
  _life_clear() { g::rule 0 $((W*H)); S=$REPLY; gen=0; }
  _life_random() { S=""; for ((i=0;i<W*H;i++)); do (( RANDOM % 4 == 0 )) && S+=1 || S+=0; done; gen=0; }
  _life_stamp() {   # "row|row|row" at center
    local pat=$1 ox oy r row; local -a rowsA; IFS='|' read -ra rowsA <<<"$pat"
    oy=$(( H/2 - ${#rowsA[@]}/2 )); ox=$(( W/2 - ${#rowsA[0]}/2 ))
    for ((r=0;r<${#rowsA[@]};r++)); do row=${rowsA[r]}
      for ((i=0;i<${#row};i++)); do [[ ${row:i:1} == '#' ]] && { local p=$(( (oy+r)*W + ox+i )); (( p >= 0 && p < W*H )) && S="${S:0:p}1${S:p+1}"; }; done; done
  }
  g::onkey() {
    case $K in
      space) paused=$((1-paused)) ;;
      r) _life_random ;;  c) _life_clear ;;
      g) _life_stamp '.#.|..#|###' ;;
      p) _life_stamp '..###...###..|.............|#....#.#....#|#....#.#....#|#....#.#....#|..###...###..|.............|..###...###..|#....#.#....#|#....#.#....#|#....#.#....#|.............|..###...###..' ;;
      e) _life_stamp '.##|##.|.#.' ;;
      +|=) speed=$(( speed > 50 ? speed - 30 : 20 )) ;;
      -|_) speed=$(( speed + 50 )) ;;
      n) (( paused )) && life::step ;;
    esac
  }
  _life_random
  while (( ! QUIT )); do
    local pop=${S//0/}; pop=${#pop}
    local ps=""; (( paused )) && ps="${C_YELLOW}paused${C_RESET}"
    g::ln "${C_BOLD}Life${C_RESET}  gen $gen  alive $pop  $ps"
    g::ln "${C_DIM}space pause · n step · r random · c clear · g glider · e r-pentomino · p pulsar · +/- speed · q${C_RESET}"
    local line
    for ((y=0;y<H;y++)); do
      line=${S:y*W:W}; line=${line//0/ }; line=${line//1/█}
      g::ln " ${FGC[46]}${line}"$'\033[0m'
    done
    g::paint
    g::tick "$speed"
    (( QUIT )) && break
    (( paused )) || life::step
  done
}

# ── awk-driven animations: rain, fire, ecosystem ─────────────────────────
g::anim() {   # g::anim <awk program text> [var=value …]  — runs until a key is pressed
  local prog=$1; shift
  awk -v W="$(( $(g::cols) - 1 ))" -v H="$(( $(g::rows) - 1 ))" "$@" "$prog" &
  local pid=$!
  trap 'kill "$pid" 2>/dev/null' EXIT
  g::key; kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
  trap 'printf "\033[?25h\033[0m\n"' EXIT
}

game::rain() {
  g::anim 'BEGIN{srand(); chars="0123456789abcdefghijklmnopqrstuvwxyz@#$%&*+=<>"; n=length(chars)
    for(x=1;x<=W;x++){y[x]=-int(rand()*H); len[x]=4+int(rand()*(H/2))}
    printf "\033[2J"
    while(1){ out=""
      for(x=1;x<=W;x++){
        if(rand()<0.65){ y[x]++
          if(y[x]>=1&&y[x]<=H) out=out sprintf("\033[%d;%dH\033[97m%s",y[x],x,substr(chars,int(rand()*n)+1,1))
          if(y[x]-1>=1&&y[x]-1<=H) out=out sprintf("\033[%d;%dH\033[92m%s",y[x]-1,x,substr(chars,int(rand()*n)+1,1))
          if(y[x]-3>=1&&y[x]-3<=H) out=out sprintf("\033[%d;%dH\033[32m%s",y[x]-3,x,substr(chars,int(rand()*n)+1,1))
          t=y[x]-len[x]; if(t>=1&&t<=H) out=out sprintf("\033[%d;%dH ",t,x)
          if(t>H){y[x]=-int(rand()*H/2); len[x]=4+int(rand()*(H/2))}
        } }
      printf "%s\033[0m", out; fflush(); system("sleep 0.06") } }'
}

game::fire() {
  g::anim 'BEGIN{srand(); split("16 52 88 124 160 196 202 208 214 220 226 227 228 229 230 231",pal," "); N=16
    for(i=0;i<W*(H+1);i++) h[i]=0; printf "\033[2J"
    while(1){
      for(x=0;x<W;x++) h[H*W+x]=(rand()<0.85)?36:20+int(rand()*10)
      for(y=0;y<H;y++)for(x=0;x<W;x++){ s=x+int(rand()*3)-1; if(s<0)s=0; if(s>=W)s=W-1
        v=h[(y+1)*W+s]-int(rand()*(2*36/H+1)); if(v<0)v=0; h[y*W+x]=v }
      out="\033[H"; last=-1
      for(y=0;y<H;y++){ for(x=0;x<W;x++){ c=int(h[y*W+x]*N/37); if(c!=last){out=out sprintf("\033[48;5;%sm",pal[c+1]); last=c} out=out " " } out=out "\033[0m\n"; last=-1 }
      printf "%s", out; fflush(); system("sleep 0.07") } }'
}

# ── Ecosystem (grass → rabbits → foxes) ──────────────────────────────────
ECO_AWK='
function count(  y,x,v){ gr=0;ra=0;fx=0; for(y=0;y<H;y++)for(x=0;x<W;x++){v=g[y*W+x]; if(v==1)gr++; else if(v==2)ra++; else if(v==3)fx++} }
BEGIN{ srand(seed>0?seed:srand()); split("-1 -1 -1 0 0 1 1 1",dy," "); split("-1 0 1 -1 1 -1 0 1",dx," ")
  for(i=0;i<8;i++){dy[i]=dy[i+1]; dx[i]=dx[i+1]}
  for(i=0;i<W*H;i++){ r=rand(); g[i]=(r<0.45)?1:0; e[i]=0 }
  for(i=0;i<W*H*0.04;i++){ p=int(rand()*W*H); g[p]=2; e[p]=6 }
  for(i=0;i<W*H*0.008+1;i++){ p=int(rand()*W*H); g[p]=3; e[p]=12 }
  if(!maxt) printf "\033[2J"
  for(t=1; !maxt || t<=maxt; t++){
    for(i=0;i<W*H;i++) mv[i]=0
    for(y=0;y<H;y++)for(x=0;x<W;x++){ i=y*W+x; v=g[i]
      if(v==0){ if(rand()<0.05) g[i]=1 }
      else if(v==1){ }
      else if(mv[i]!=t){
        if(v==2){ e[i]--; if(e[i]<=0){g[i]=0; continue}
          best=-1; for(k=0;k<8;k++){ d=(int(rand()*8)+k)%8; ny=(y+dy[d]+H)%H; nx=(x+dx[d]+W)%W; j=ny*W+nx
            if(g[j]==1){best=j;break} if(g[j]==0&&best<0)best=j }
          if(best>=0){ eat=(g[best]==1); g[best]=2; e[best]=e[i]+(eat?3:0); if(e[best]>12)e[best]=12; mv[best]=t; g[i]=0
            if(e[best]>=7 && rand()<0.6){ h2=int(e[best]/2); e[best]=h2; g[i]=2; e[i]=h2; mv[i]=t } } }
        else if(v==3){ e[i]--; if(e[i]<=0){g[i]=0; continue}
          best=-1; prey=-1; for(k=0;k<8;k++){ d=(int(rand()*8)+k)%8; ny=(y+dy[d]+H)%H; nx=(x+dx[d]+W)%W; j=ny*W+nx
            if(g[j]==2&&prey<0)prey=j; else if(g[j]<=1&&best<0)best=j }
          if(prey>=0){ g[prey]=3; e[prey]=e[i]+7; if(e[prey]>22)e[prey]=22; mv[prey]=t; g[i]=0
            if(e[prey]>=16 && rand()<0.5){ h2=int(e[prey]/2); e[prey]=h2; g[i]=3; e[i]=h2; mv[i]=t } }
          else if(best>=0){ g[best]=3; e[best]=e[i]; mv[best]=t; g[i]=0 } }
      } }
    count()
    if(ra==0 && t%12==0){ for(k=0;k<6;k++){ p=int(rand()*W*H); if(g[p]<2){g[p]=2;e[p]=8} } }
    if(fx==0 && t%25==0 && ra>8){ p=int(rand()*W*H); if(g[p]<2){g[p]=3;e[p]=14} }
    if(maxt){ if(t%50==0) printf "t=%d grass=%d rabbits=%d foxes=%d\n",t,gr,ra,fx; continue }
    out="\033[H" sprintf("\033[1mEcosystem\033[0m  day %d   \033[32mgrass %d\033[0m   \033[97mrabbits %d\033[0m   \033[38;5;208mfoxes %d\033[0m   (any key quits)\033[K\n",t,gr,ra,fx)
    for(y=0;y<H-1;y++){ line=""
      for(x=0;x<W;x++){ v=g[y*W+x]
        if(v==0) line=line "\033[48;5;236m "; else if(v==1) line=line "\033[48;5;28m "
        else if(v==2) line=line "\033[48;5;28;97mr"; else line=line "\033[48;5;28;38;5;208;1mF" }
      out=out line "\033[0m\n" }
    printf "%s",out; fflush(); system("sleep 0.18") } }'
game::ecosystem() { g::anim "$ECO_AWK"; }

# ── Café Tycoon ──────────────────────────────────────────────────────────
game::tycoon() {
  local cash=5000 pcs=4 staff=1 price=40 rep=50 ad=0 day=1 days=30 goal=30000 msg="" k
  local rent=150 wage=200
  _ty_fmt() { local n=$1 s=""; while (( ${#n} > 3 )); do s=",${n: -3}$s"; n=${n:0:${#n}-3}; done; printf '%s%s' "$n" "$s"; }
  while (( day <= days )); do
    printf '\033[H\033[2J%sCafé Tycoon%s   day %s/%s   goal: KES %s\n\n' "$C_BOLD" "$C_RESET" "$day" "$days" "$(_ty_fmt $goal)"
    printf '  Cash        %sKES %s%s\n  Reputation  %s/100\n  Computers   %s   (a computer serves 8 customers a day)\n  Staff       %s   (each handles 3 computers; wage %s/day)\n  Price       KES %s per hour\n  Ad budget   KES %s today\n  Fixed costs KES %s rent + %s power per day\n\n' \
      "$C_GREEN" "$(_ty_fmt $cash)" "$C_RESET" "$rep" "$pcs" "$staff" "$wage" "$price" "$ad" "$rent" "$((pcs*20))"
    [[ -n $msg ]] && printf '%s\n\n' "$msg"
    printf '  %s[p]%s price ±5 (p/o)   %s[b]%s buy computer 3000   %s[h]%s hire   %s[f]%s fire   %s[a]%s ads (0/200/500)\n  %s[enter]%s end the day   %s[q]%s quit\n' "$C_CYAN" "$C_RESET" "$C_CYAN" "$C_RESET" "$C_CYAN" "$C_RESET" "$C_CYAN" "$C_RESET" "$C_CYAN" "$C_RESET" "$C_CYAN" "$C_RESET" "$C_CYAN" "$C_RESET"
    g::key; msg=""
    case $K in
      p) (( price < 150 )) && price=$((price+5)) ;;
      o) (( price > 10 )) && price=$((price-5)) ;;
      b) if (( cash >= 3000 && pcs < 20 )); then cash=$((cash-3000)); pcs=$((pcs+1)); else msg="  ${C_YELLOW}Can't buy (need KES 3000, max 20 computers).${C_RESET}"; fi ;;
      h) (( staff < 8 )) && staff=$((staff+1)) ;;
      f) (( staff > 0 )) && staff=$((staff-1)) ;;
      a) case $ad in 0) ad=200 ;; 200) ad=500 ;; *) ad=0 ;; esac ;;
      q|esc) return ;;
      enter)
        local pe cap demand served rev cost profit mult=100 ev=""
        pe=$(awk -v p="$price" 'BEGIN{printf "%d", (40/p)^1.3*100}')
        cap=$(( (pcs < staff*3 ? pcs : staff*3) * 8 ))
        case $(( RANDOM % 12 )) in
          0) mult=30;  ev="${C_RED}Power outage! Few customers today.${C_RESET}" ;;
          1) mult=150; ev="${C_GREEN}Exam season: students flood in!${C_RESET}" ;;
          2) mult=80; rep=$((rep-4)); ev="${C_RED}A rival café opened nearby.${C_RESET}" ;;
          3) mult=130; ev="${C_GREEN}Local festival, more foot traffic.${C_RESET}" ;;
        esac
        demand=$(( (20 + rep/2 + ad/15) * pe / 100 * mult / 100 ))
        served=$(( demand < cap ? demand : cap )); rev=$(( served * price ))
        cost=$(( rent + staff*wage + ad + pcs*20 )); profit=$(( rev - cost )); cash=$(( cash + profit ))
        if (( demand > cap )); then rep=$((rep-2)); else rep=$((rep+1)); fi
        (( price > 70 )) && rep=$((rep-1)); (( ad > 0 )) && rep=$((rep+1))
        (( rep > 100 )) && rep=100; (( rep < 0 )) && rep=0
        local turned=$(( demand > cap ? demand - cap : 0 )) ts=""
        (( turned > 0 )) && ts=", turned away $turned"
        msg="  ${C_BOLD}Day $day:${C_RESET} $demand wanted a PC, served $served$ts. Revenue $(_ty_fmt $rev), costs $(_ty_fmt $cost), "
        if (( profit >= 0 )); then msg+="${C_GREEN}profit $(_ty_fmt $profit)${C_RESET}"; else msg+="${C_RED}loss $(_ty_fmt $((-profit)))${C_RESET}"; fi
        [[ -n $ev ]] && msg+=$'\n'"  $ev"
        ad=0; day=$((day+1))
        if (( cash < 0 )); then printf '\033[H\033[2J'; g::over "Bankrupt on day $((day-1))" "the café closed"; g::wait; return; fi ;;
    esac
  done
  printf '\033[H\033[2J%sCafé Tycoon%s  30 days done\n\n  Final cash: %sKES %s%s\n' "$C_BOLD" "$C_RESET" "$C_GREEN" "$(_ty_fmt $cash)" "$C_RESET"
  (( cash >= goal )) && printf '  %s★ You hit the goal of KES %s!%s\n' "$C_YELLOW" "$(_ty_fmt $goal)" "$C_RESET" || printf '  Goal was KES %s. Try more staff, ads or a lower price.\n' "$(_ty_fmt $goal)"
  g::record tycoon "$cash" && printf '  %s★ new best!%s\n' "$C_YELLOW" "$C_RESET"
  g::wait
}
