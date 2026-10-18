# NSH z — frecent directory jump (our own implementation)
# Tracks directory visits with (frequency × recency) score, jumps to
# the best match for a partial name.
#
# Usage: z <partial-name>     jump to best match
#        z -l <partial>       list candidates with scores
#        z -c                 restrict to children of PWD
#        z -                  previous dir (like `cd -`)

: ${_Z_DATA:=${NEBULA_CFG:-$HOME}/.nsh_z}

# Resolve awk/mv to absolute paths once at load time so a later PATH change
# (or stale zsh command hash) cannot trigger Termux's command-not-found
# handler on every cd / keystroke. Empty string => not available, no-op.
typeset -g _NSH_Z_AWK="$(command -v awk 2>/dev/null)"
typeset -g _NSH_Z_MV="$(command -v mv 2>/dev/null)"

_z_track() {
  # Silently no-op when awk or mv aren't installed (common on stock Termux).
  [[ -x $_NSH_Z_AWK && -x $_NSH_Z_MV ]] || return 0

  local pwd_now=$PWD
  [[ $pwd_now == $HOME ]] && return       # don't track HOME
  [[ -n ${_Z_EXCLUDE_DIRS+x} ]] && {
    for d in "${_Z_EXCLUDE_DIRS[@]}"; do
      [[ $pwd_now == $d/* || $pwd_now == $d ]] && return
    done
  }

  local tmp="${_Z_DATA}.$$"
  local now=$(date +%s) found=0
  : > "$tmp"
  # NB: `path` is a special array tied to $PATH in zsh — never read into it.
  if [[ -f $_Z_DATA ]]; then
    local zpath zrank ztime
    while IFS='|' read -r zpath zrank ztime; do
      [[ -z $zpath ]] && continue
      if [[ $zpath == "$pwd_now" ]]; then
        zrank=$("$_NSH_Z_AWK" "BEGIN{print ${zrank:-0} + 1}" 2>/dev/null)
        ztime=$now
        found=1
      fi
      printf '%s|%s|%s\n' "$zpath" "$zrank" "$ztime" >> "$tmp"
    done < "$_Z_DATA"
  fi
  (( found )) || printf '%s|%s|%s\n' "$pwd_now" "1" "$now" >> "$tmp"
  "$_NSH_Z_MV" -f "$tmp" "$_Z_DATA" 2>/dev/null
}

# Hook into chpwd
chpwd_functions=(${chpwd_functions[@]} _z_track)

unalias z 2>/dev/null
unfunction z 2>/dev/null
z() {
  if [[ ! -x $_NSH_Z_AWK ]]; then
    echo "z: awk is required (pkg install gawk)"; return 1
  fi
  local list=0 children=0 pattern
  while (( $# )); do
    case $1 in
      -l) list=1; shift ;;
      -c) children=1; shift ;;
      -)  cd - >/dev/null; return ;;
      *)  pattern="$1"; shift ;;
    esac
  done

  [[ ! -f $_Z_DATA ]] && { echo "z: no data yet — cd around a bit first"; return 1; }

  local now=$(date +%s)
  local best_path="" best_score=0

  # frecent = rank * 1/(age+1)  (simple version of Z's algorithm)
  "$_NSH_Z_AWK" -F'|' -v pat="$pattern" -v pwd="$PWD" -v children="$children" -v now="$now" -v list="$list" '
    {
      p=$1; rank=$2+0; t=$3+0
      if (!p) next
      if (children && index(p, pwd"/") != 1) next
      if (pat && index(p, pat) == 0) next
      age = now - t
      score = rank * (1 / (1 + age/3600))
      if (list) {
        printf "%8.2f  %s\n", score, p
      } else if (score > best) {
        best = score; best_path = p
      }
    }
    END { if (!list && best_path) print best_path }
  ' "$_Z_DATA" | if (( list )); then sort -rn; else read -r target; [[ -n $target ]] && cd "$target" || { echo "z: no match"; return 1; }; fi
}
