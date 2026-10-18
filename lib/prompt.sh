#!/data/data/com.termux/files/usr/bin/env bash
# nebula — prompt studio: presets, live preview, per-field editor, import/export.
# The zsh engine (zsh/themes/studio.zsh-theme) re-reads data/prompt.conf by itself,
# so every change here shows up in your open shell at the next prompt.

PROMPT_KEYS="layout segments right char sep path_mode git_style time_fmt blank bold responsive c_accent c_path c_git c_time c_user c_error c_dim c_batt"
PROMPT_LEFT="time user host path git venv jobs battery"
PROMPT_RIGHT="status duration battery time jobs venv"
declare -gA PC=()

prompt::defaults() {
  PC=( [layout]=two [segments]="time path git" [right]="status duration" [char]="❯" [sep]=space
       [path_mode]=full [git_style]=dirty [time_fmt]='%H:%M:%S' [blank]=0 [bold]=0 [responsive]=1
       [c_accent]=51 [c_path]=120 [c_git]=120 [c_time]=51 [c_user]=213 [c_error]=203 [c_dim]=245 [c_batt]=221 )
}

# prompt::valid <key> <value> → 0 if allowed (same rules as the zsh engine)
prompt::valid() {
  local k=$1 v=$2 s
  case $k in
    layout)    [[ $v == one || $v == two ]] ;;
    segments)  for s in $v; do [[ " $PROMPT_LEFT " == *" $s "* ]] || return 1; done ;;
    right)     for s in $v; do [[ " $PROMPT_RIGHT " == *" $s "* ]] || return 1; done ;;
    char)      (( ${#v} >= 1 && ${#v} <= 3 )) && [[ $v != *[\`\\%]* ]] ;;
    sep)       [[ $v == @(space|dot|pipe|slash|arrow|none) ]] ;;
    path_mode) [[ $v == @(full|trunc|short|dir) ]] ;;
    git_style) [[ $v == @(dirty|branch|off) ]] ;;
    time_fmt)  [[ $v == '%H:%M:%S' || $v == '%H:%M' || $v == '%I:%M %p' || $v == '%I:%M:%S %p' ]] ;;
    blank|bold|responsive) [[ $v == [01] ]] ;;
    c_accent|c_path|c_git|c_time|c_user|c_error|c_dim|c_batt) [[ $v =~ ^[0-9]{1,3}$ ]] && (( v <= 255 )) ;;
    *) return 1 ;;
  esac
}

# prompt::load [file]  → PC (defaults, then validated lines of the file)
prompt::load() {
  local f=${1:-$NEBULA_CFG/prompt.conf} k v
  prompt::defaults
  [[ -r $f ]] || return 0
  while IFS='=' read -r k v; do
    [[ -z $k || $k == \#* ]] && continue
    prompt::valid "$k" "$v" && PC[$k]=$v
  done < "$f"
}

prompt::save() {
  local k; mkdir -p "$NEBULA_CFG"
  { for k in $PROMPT_KEYS; do printf '%s=%s\n' "$k" "${PC[$k]}"; done; } > "$NEBULA_CFG/prompt.conf.tmp" \
    && mv "$NEBULA_CFG/prompt.conf.tmp" "$NEBULA_CFG/prompt.conf"
  echo studio > "$NEBULA_CFG/theme"
}

prompt::norm() { local f=$1 k; prompt::load "$f"; for k in $PROMPT_KEYS; do printf '%s=%s\n' "$k" "${PC[$k]}"; done; }
prompt::presets() { local f; for f in "$NEBULA_HOME"/assets/prompts/*.conf; do basename "$f" .conf; done; }
prompt::preset_desc() { sed -n '1s/^# *//p' "$NEBULA_HOME/assets/prompts/$1.conf"; }

prompt::current_preset() {
  local cur p; prompt::load; local k; cur=$(for k in $PROMPT_KEYS; do printf '%s=%s\n' "$k" "${PC[$k]}"; done)
  for p in $(prompt::presets); do
    [[ $(prompt::norm "$NEBULA_HOME/assets/prompts/$p.conf") == "$cur" ]] && { echo "$p"; return; }
  done
  echo custom
}

prompt::apply_preset() {
  local p=$1 f="$NEBULA_HOME/assets/prompts/$1.conf"
  [[ -f $f ]] || { ui::say_status ERR "No preset called '$p'. Try: theme list"; return 1; }
  prompt::load "$f"; prompt::save
}

# ── colours ─────────────────────────────────────────────────────────────
prompt::colors() {  # name code
  cat <<'EOF'
red 203
crimson 160
orange 215
amber 214
yellow 221
lime 154
green 120
mint 121
teal 43
cyan 51
sky 75
blue 69
indigo 63
purple 141
violet 135
magenta 213
pink 211
rose 174
white 255
silver 250
gray 245
EOF
}
prompt::color_code() {  # name|number → code
  local q=${1,,} n c
  if [[ $q =~ ^[0-9]{1,3}$ ]] && (( q <= 255 )); then echo "$q"; return 0; fi
  while read -r n c; do [[ $n == "$q" ]] && { echo "$c"; return 0; }; done < <(prompt::colors)
  return 1
}
prompt::pick_color() {  # slot → sets PC
  local slot=$1 sel code
  sel=$( { prompt::colors | awk '{printf "%-9s %s\n", $1, $2}'; echo "number…   type 0-255"; } | pick::choose "Colour for ${slot#c_}") || return 1
  if [[ $sel == number* ]]; then read -r -p "  0-255: " code; else code=${sel##* }; fi
  prompt::valid "$slot" "$code" || { ui::say_status ERR "That isn't a colour (0-255)."; sleep 1; return 1; }
  PC[$slot]=$code
}

# ── preview ─────────────────────────────────────────────────────────────
prompt::preview() {  # prints a 2-3 line preview of the SAVED config
  command -v zsh >/dev/null 2>&1 || { printf '  (install zsh for the live preview)\n'; return; }
  local out left right cols vis pad first rest
  # a short, realistic sample path (~/projects/nebula/src) instead of wherever you happen to be
  local sample="$NEBULA_CFG/.sample"; mkdir -p "$sample/projects/nebula/src" 2>/dev/null
  out=$(HOME="$sample" NEBULA_CFG="$NEBULA_CFG" NEBULA_HOME="$NEBULA_HOME" TERM=xterm-256color zsh -f -c 'cd ~/projects/nebula/src; source "$NEBULA_HOME/zsh/themes/studio.zsh-theme"; _np_preview' 2>/dev/null)
  left=${out%%$'\x1f'*}; right=${out#*$'\x1f'}; right=${right//$'\n'/}
  cols=$(ui::cols)
  left=${left%$'\n'}
  first=${left%%$'\n'*}
  if [[ $left == *$'\n'* ]]; then rest=${left#*$'\n'}; else rest=""; fi
  if [[ -n $right ]]; then
    local plain; plain=$(sed 's/\x1b\[[0-9;]*[a-zA-Z]//g' <<<"$first"); local rp; rp=$(sed 's/\x1b\[[0-9;]*[a-zA-Z]//g' <<<"$right")
    pad=$(( cols - 3 - ${#plain} - ${#rp} ))
    if (( pad >= 2 )); then printf '  %s%*s%s\n' "$first" "$pad" "" "$right"
    else printf '  %s\n%*s%s\n' "$first" $(( cols - ${#rp} - 1 )) "" "$right"; fi
  else printf '  %s\n' "$first"; fi
  if [[ -n $rest ]]; then printf '  %s%sls -la%s\n' "$rest" "$C_DIM" "$C_RESET"
  else printf '%s\r  %s\n' "" "" | head -0; fi
}

# ── segment editor ──────────────────────────────────────────────────────
prompt::seg_editor() {  # left|right
  local side=$1 key known title
  if [[ $side == left ]]; then key=segments; known=$PROMPT_LEFT; title="Left side"; else key=right; known=$PROMPT_RIGHT; title="Right side"; fi
  local cur=0
  while :; do
    local -a on=(${PC[$key]}) items=() kinds=() names=() s
    for s in "${on[@]}"; do items+=("$(( ${#names[@]} + 1 )). $s"$'\tON\tg'); kinds+=(on); names+=("$s"); done
    for s in $known; do
      [[ " ${on[*]} " == *" $s "* ]] && continue
      [[ $s == battery ]] && ! device::cap battery && continue
      items+=("   $s"$'\toff\td'); kinds+=(off); names+=("$s")
    done
    MENU_INFO="$(prompt::preview)"$'\n'; MENU_CUR=$cur
    menu::pick "🎛 $title" "Enter: add / edit · q back" items || { MENU_INFO=""; return; }
    cur=$MENU_IDX; s=${names[cur]}
    if [[ ${kinds[cur]} == off ]]; then PC[$key]="${PC[$key]:+${PC[$key]} }$s"; prompt::save
    else
      local -a opt=($'↑ Move up\t' $'↓ Move down\t' $'✖ Turn off\t' $'← Back\t'); MENU_CUR=0; MENU_INFO="${C_BOLD}$s${C_RESET}"
      menu::pick "Edit '$s'" "Enter to choose" opt || { MENU_INFO=""; continue; }
      local i idx=-1; for i in "${!on[@]}"; do [[ ${on[i]} == "$s" ]] && idx=$i; done
      case $MENU_IDX in
        0) (( idx > 0 )) && { local t=${on[idx-1]}; on[idx-1]=${on[idx]}; on[idx]=$t; } ;;
        1) (( idx < ${#on[@]}-1 )) && { local t=${on[idx+1]}; on[idx+1]=${on[idx]}; on[idx]=$t; } ;;
        2) unset 'on[idx]'; on=("${on[@]}") ;;
      esac
      PC[$key]="${on[*]}"; prompt::save
    fi
    MENU_INFO=""
  done
}

prompt::cycle() {  # prompt::cycle key v1 v2 v3 …
  local key=$1; shift; local -a vals=("$@"); local i
  for i in "${!vals[@]}"; do [[ ${vals[i]} == "${PC[$key]}" ]] && { PC[$key]=${vals[(i+1)%${#vals[@]}]}; return; }; done
  PC[$key]=${vals[0]}
}

# ── the studio ──────────────────────────────────────────────────────────
prompt::studio() {
  [[ -t 0 && -t 1 ]] || { ui::say_status WARN "The studio needs a terminal."; return 1; }
  prompt::load; local cur=0
  [[ -f $NEBULA_CFG/prompt.conf ]] || prompt::save
  while :; do
    prompt::load
    local preset; preset=$(prompt::current_preset)
    local colorsum="accent ${PC[c_accent]} · path ${PC[c_path]} · git ${PC[c_git]}"
    local -a items=(
      "🎨 Preset"$'\t'"$preset"$'\ty'
      "📐 Layout"$'\t'"${PC[layout]}-line"$'\t'
      "◀ Left side"$'\t'"${PC[segments]}"$'\td'
      "▶ Right side"$'\t'"${PC[right]:-nothing}"$'\td'
      "⌨ Prompt character"$'\t'"${PC[char]}"$'\t'
      "📂 Path style"$'\t'"${PC[path_mode]}"$'\t'
      "│ Separator"$'\t'"${PC[sep]}"$'\t'
      "🕐 Time format"$'\t'"${PC[time_fmt]}"$'\t'
      "🌿 Git detail"$'\t'"${PC[git_style]}"$'\t'
      "🎨 Colours"$'\t'"$colorsum"$'\td'
      "␣ Blank line before prompt"$'\t'"$([[ ${PC[blank]} == 1 ]] && echo ON || echo off)"$'\t'
      "𝐁 Bold"$'\t'"$([[ ${PC[bold]} == 1 ]] && echo ON || echo off)"$'\t'
      "📱 Responsive prompt"$'\t'"$([[ ${PC[responsive]} == 1 ]] && echo ON || echo off)"$'\t'
      "📤 Share / export"$'\t\t'
      "📥 Import"$'\t\t'
    )
    MENU_INFO="${C_DIM}Live preview:${C_RESET}"$'\n'"$(prompt::preview)"$'\n'; MENU_CUR=$cur
    menu::pick "🎨 Prompt studio" "Enter: change · q: close" items || break
    cur=$MENU_IDX; MENU_INFO=""
    case $cur in
      0) local p; p=$(for x in $(prompt::presets); do printf '%-10s %s\n' "$x" "$(prompt::preset_desc "$x")"; done | pick::choose "Preset") && prompt::apply_preset "${p%% *}" ;;
      1) prompt::cycle layout two one; prompt::save ;;
      2) prompt::seg_editor left ;;
      3) prompt::seg_editor right ;;
      4) local c; c=$(printf '%s\n' "❯  chevron" "›  light arrow" "➜  arrow" "\$  dollar" "λ  lambda" "⚡ bolt" "»  guillemet" "→  right arrow" "▶  triangle" "·  dot" "custom…" | pick::choose "Prompt character") || continue
         if [[ $c == custom* ]]; then read -r -p "  1-3 characters: " c; else c=${c%% *}; fi
         prompt::valid char "$c" && { PC[char]=$c; prompt::save; } || { ui::say_status ERR "Use 1-3 characters (no % \\ or backticks)."; sleep 1; } ;;
      5) prompt::cycle path_mode full trunc short dir; prompt::save ;;
      6) prompt::cycle sep space dot pipe slash arrow none; prompt::save ;;
      7) prompt::cycle time_fmt '%H:%M:%S' '%H:%M' '%I:%M %p' '%I:%M:%S %p'; prompt::save ;;
      8) prompt::cycle git_style dirty branch off; prompt::save ;;
      9) prompt::colors_page ;;
      10) prompt::cycle blank 0 1; prompt::save ;;
      11) prompt::cycle bold 0 1; prompt::save ;;
      12) prompt::cycle responsive 1 0; prompt::save ;;
      13) printf '\033[H\033[2J'; cmd::theme export; menu::wait ;;
      14) printf '\033[H\033[2J'; read -r -p "  Paste a share code, file path or URL: " c; [[ -n $c ]] && cmd::theme import "$c"; menu::wait ;;
    esac
  done
  printf '\033[H\033[2J'
}

prompt::colors_page() {
  local cur=0 s
  while :; do
    local -a items=() slots=(c_accent c_path c_git c_time c_user c_error c_dim c_batt)
    local labels=("Accent (prompt char, clock)" "Path" "Git" "Time" "User / host" "Errors" "Dim text / separators" "Battery")
    local i; for i in "${!slots[@]}"; do items+=("${labels[i]}"$'\t'"$(printf '\033[38;5;%sm██\033[0m %s' "${PC[${slots[i]}]}" "${PC[${slots[i]}]}")"$'\t'); done
    MENU_INFO="$(prompt::preview)"$'\n'; MENU_CUR=$cur
    menu::pick "🎨 Colours" "Enter: choose · q back" items || { MENU_INFO=""; return; }
    cur=$MENU_IDX; prompt::pick_color "${slots[cur]}" && prompt::save
  done
}

# ── share / import ──────────────────────────────────────────────────────
prompt::share_code() { { echo "# nebula-theme v1"; prompt::norm "$NEBULA_CFG/prompt.conf"; } | base64 -w0 2>/dev/null | sed 's/^/NEBT1:/'; }

prompt::import_text() {  # stdin → validated conf lines on stdout (nothing else survives)
  local k v n=0
  while IFS='=' read -r k v; do
    [[ -z $k || $k == \#* ]] && continue
    prompt::valid "$k" "$v" && { printf '%s=%s\n' "$k" "$v"; n=$((n+1)); }
    (( n > 40 )) && break
  done
}

# ── command ─────────────────────────────────────────────────────────────
cmd::theme() {
  local sub=${1:-list}
  case $sub in
    list|"")
      local cur p; cur=$(prompt::current_preset)
      printf "${C_CYAN}${C_BOLD}🎨 Prompt themes${C_RESET}\n"
      for p in $(prompt::presets); do
        local lab; printf -v lab '%-9s' "$p"
        if [[ $p == "$cur" ]]; then ui::item "${C_GREEN}●${C_RESET} $lab" 11 "$(prompt::preset_desc "$p")"
        else ui::item "${C_DIM}○${C_RESET} $lab" 11 "$(prompt::preset_desc "$p")"; fi
      done
      [[ $cur == custom ]] && ui::item "${C_GREEN}●${C_RESET} custom   " 11 "your own mix"
      ui::hint "theme <name> · theme studio · theme set accent cyan · theme export · theme import <code>" ;;
    studio|edit|builder) prompt::studio ;;
    set)
      local slot=${2:-} col=${3:-} code
      case $slot in accent|path|git|time|user|error|dim) ;; *) ui::say_status ERR "Slots: accent path git time user error dim"; return 1;; esac
      code=$(prompt::color_code "$col") || { ui::say_status ERR "Unknown colour '$col' (name or 0-255)."; return 1; }
      prompt::load; PC[c_$slot]=$code; prompt::save
      printf "  ${C_GREEN}✔${C_RESET} %s → \033[38;5;%sm■■■ %s\033[0m\n" "$slot" "$code" "$code" ;;
    reset) rm -f "$NEBULA_CFG/prompt.conf" "$NEBULA_CFG/theme.conf"; echo studio > "$NEBULA_CFG/theme"; ui::say_status OK "Prompt reset to the default." ;;
    export|share)
      prompt::load; [[ -f $NEBULA_CFG/prompt.conf ]] || prompt::save
      local name=${2:-my-theme}; name=${name//[^A-Za-z0-9._-]/_}
      mkdir -p "$NEBULA_CFG/themes"
      { echo "# nebula-theme v1 — $name"; prompt::norm "$NEBULA_CFG/prompt.conf"; } > "$NEBULA_CFG/themes/$name.nebtheme"
      ui::say_status OK "Saved: $NEBULA_CFG/themes/$name.nebtheme"
      local sd=""; for sd in /sdcard "$HOME/storage/shared"; do [[ -w $sd ]] && break || sd=""; done
      [[ -n $sd ]] && mkdir -p "$sd/Nebula/themes" && cp "$NEBULA_CFG/themes/$name.nebtheme" "$sd/Nebula/themes/" && ui::say_status OK "Copy: $sd/Nebula/themes/$name.nebtheme"
      printf "\n  ${C_BOLD}Share code${C_RESET} ${C_DIM}(paste it into: theme import <code>)${C_RESET}\n  %s\n\n" "$(prompt::share_code)" ;;
    import)
      local src=${2:-} text=""
      [[ -z $src ]] && { ui::say_status WARN "Usage: theme import <NEBT1:code | file | https://url>"; return 1; }
      if   [[ $src == NEBT1:* ]]; then text=$(printf '%s' "${src#NEBT1:}" | base64 -d 2>/dev/null)
      elif [[ -f $src ]]; then text=$(head -c 4096 "$src")
      elif [[ $src == https://* ]] && command -v curl >/dev/null 2>&1; then text=$(curl -fsSL --max-time 10 "$src" 2>/dev/null | head -c 4096)
      else ui::say_status ERR "Not a share code, file or https URL."; return 1; fi
      local clean; clean=$(prompt::import_text <<<"$text")
      [[ -z $clean ]] && { ui::say_status ERR "Nothing valid in that theme (it was ignored — Nebula only accepts known settings)."; return 1; }
      mkdir -p "$NEBULA_CFG/backups"; [[ -f $NEBULA_CFG/prompt.conf ]] && cp "$NEBULA_CFG/prompt.conf" "$NEBULA_CFG/backups/prompt.conf.prev"
      printf '%s\n' "$clean" > "$NEBULA_CFG/prompt.conf.in"; prompt::load "$NEBULA_CFG/prompt.conf.in"; rm -f "$NEBULA_CFG/prompt.conf.in"; prompt::save
      ui::say_status OK "Imported $(wc -l <<<"$clean") settings. Preview:"; prompt::preview; ui::say_status INFO "Undo: theme import $NEBULA_CFG/backups/prompt.conf.prev" ;;
    *)
      if [[ -f $NEBULA_HOME/assets/prompts/$sub.conf ]]; then
        prompt::apply_preset "$sub" && { ui::say_status OK "Theme: $sub"; prompt::preview; }
      else ui::say_status ERR "Unknown theme '$sub'. Try: theme list"; return 1; fi ;;
  esac
}
cmd::prompt() { cmd::theme studio; }
