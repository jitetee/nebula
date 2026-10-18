# NSH fzf integration — Ctrl-R (history) + Ctrl-T (files)
# Requires `fzf` binary on PATH. Silently no-ops if missing.

command -v fzf >/dev/null 2>&1 || return 0

typeset -g _NSH_FZF_AWK="$(command -v awk 2>/dev/null)"

# ── Ctrl-R: fuzzy history search ─────────────────────────────────────────
_nsh_fzf_history() {
  [[ -x $_NSH_FZF_AWK ]] || { zle -M "fzf-history needs awk (pkg install gawk)"; return; }
  local selected
  selected=$(fc -rl 1 | "$_NSH_FZF_AWK" '{ $1=""; sub(/^ /,""); print }' 2>/dev/null | \
             fzf --height 40% --reverse --no-multi \
                 --prompt='history> ' \
                 --color='bg+:#1a1f2e,fg+:#C8D3F5,hl+:#4FC3F7,prompt:#FF7A93' \
                 --query="$LBUFFER")
  if [[ -n $selected ]]; then
    LBUFFER="$selected"
    CURSOR=${#LBUFFER}
  fi
  zle reset-prompt
}
zle -N _nsh_fzf_history
bindkey '^R' _nsh_fzf_history

# ── Ctrl-T: fuzzy file picker (inserts selected path at cursor) ──────────
_nsh_fzf_file() {
  local selected
  # Prefer fd / rg for speed; fall back to find
  local finder
  if command -v fd >/dev/null 2>&1; then
    finder='fd --type f --hidden --follow --exclude .git'
  elif command -v rg >/dev/null 2>&1; then
    finder='rg --files --hidden --follow -g !.git'
  else
    finder='find . -type f -not -path "*/.git/*"'
  fi
  selected=$(eval "$finder" 2>/dev/null | \
             fzf --height 40% --reverse --multi \
                 --prompt='files> ' \
                 --preview='head -80 {} 2>/dev/null' --preview-window=right:50%:wrap \
                 --color='bg+:#1a1f2e,fg+:#C8D3F5,hl+:#4FC3F7,prompt:#82AAFF')
  if [[ -n $selected ]]; then
    # Quote each selected path, join with spaces
    local quoted=""
    while IFS= read -r line; do
      quoted+="${line@Q} "
    done <<< "$selected"
    LBUFFER="${LBUFFER}${quoted% }"
  fi
  zle reset-prompt
}
zle -N _nsh_fzf_file
bindkey '^T' _nsh_fzf_file

# ── Alt-C: fuzzy cd into directory ───────────────────────────────────────
_nsh_fzf_cd() {
  local dir
  if command -v fd >/dev/null 2>&1; then
    dir=$(fd --type d --hidden --follow --exclude .git 2>/dev/null | \
          fzf --height 40% --reverse --prompt='cd> ' \
              --color='bg+:#1a1f2e,fg+:#C8D3F5,hl+:#C3E88D,prompt:#C3E88D')
  else
    dir=$(find . -type d -not -path '*/.git/*' 2>/dev/null | \
          fzf --height 40% --reverse --prompt='cd> ')
  fi
  if [[ -n $dir ]]; then
    BUFFER="cd ${dir@Q}"
    zle accept-line
  fi
  zle reset-prompt
}
zle -N _nsh_fzf_cd
bindkey '^[c' _nsh_fzf_cd
