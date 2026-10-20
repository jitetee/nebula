#!/usr/bin/env bash
# push.sh — add, commit and push this folder to GitHub (jitetee/nebula by default).
# If the folder isn't a git repo yet, or has no remote, it sets everything up first.
#
#   bash push.sh                      # asks for a commit message
#   bash push.sh "fix the keyboard"   # commit message as argument
#   NEBULA_REPO_URL=https://github.com/you/other.git bash push.sh
#   BRANCH=dev bash push.sh           # branch to push (default: main)
#   BUMP=minor bash push.sh           # version bump: patch (default) | minor | major | none
#
# Version: every push that has changes raises VERSION by one patch step (0.9.1 → 0.9.2),
# updates the README badge and adds a CHANGELOG line with your commit message, so Nebula's
# "update available" check on every phone notices the new release. (If your VERSION is already
# higher than the one on GitHub it is used as it is. BUMP=none turns this off.)
#
# Login: GitHub no longer accepts account passwords over HTTPS. When asked for a
# password, paste a Personal Access Token (GitHub → Settings → Developer settings →
# Tokens, scope "repo"), or run `gh auth login` first if you use the GitHub CLI.

set -u
REPO_URL="${NEBULA_REPO_URL:-https://github.com/jitetee/nebula.git}"
BRANCH="${BRANCH:-main}"
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1

say()  { printf '\033[38;5;51m▸\033[0m %s\n' "$*"; }
ok()   { printf '\033[38;5;120m✔\033[0m %s\n' "$*"; }
warn() { printf '\033[38;5;221m⚠\033[0m %s\n' "$*"; }
die()  { printf '\033[38;5;203m✖\033[0m %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || die "git is not installed. In Termux: pkg install git"

# 1. repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  say "Not a git repo yet: running git init"
  git init -q -b "$BRANCH" 2>/dev/null || { git init -q && git checkout -q -b "$BRANCH"; }
  ok "Initialised repo on branch $BRANCH"
fi
ROOT=$(git rev-parse --show-toplevel); cd "$ROOT" || exit 1

# 2. identity (commits fail without it)
if [[ -z $(git config user.name) ]]; then
  read -r -p "  Git name  (for commits): " n; [[ -n $n ]] || die "A name is needed."
  git config user.name "$n"
fi
if [[ -z $(git config user.email) ]]; then
  read -r -p "  Git email (for commits): " e; [[ -n $e ]] || die "An email is needed."
  git config user.email "$e"
fi

# 3. remote
if ! git remote get-url origin >/dev/null 2>&1; then
  say "No remote yet: adding origin → $REPO_URL"
  git remote add origin "$REPO_URL"
  ok "Remote origin added"
else
  say "Remote origin → $(git remote get-url origin)"
fi

# 4. branch
CUR=$(git symbolic-ref --short -q HEAD || echo "$BRANCH")
if [[ $CUR != "$BRANCH" ]]; then
  if git rev-parse --verify -q HEAD >/dev/null 2>&1; then BRANCH=$CUR; else git checkout -q -b "$BRANCH" 2>/dev/null || git branch -M "$BRANCH"; fi
fi

# 5. keep secrets and local data out
if [[ ! -f .gitignore ]] || ! grep -q '^data/' .gitignore 2>/dev/null; then
  warn "No ignore rule for data/ (your login hash, notes, backups). Adding it to .gitignore"
  printf '\n# Nebula user data: never commit\ndata/\n' >> .gitignore
fi

# 6. add + commit
if [[ -z $(git status --porcelain) ]]; then
  say "Nothing new to commit."
else
  MSG="${*:-}"
  if [[ -z $MSG ]]; then read -r -p "  Commit message [update $(date '+%Y-%m-%d %H:%M')]: " MSG; fi
  MSG="${MSG:-update $(date '+%Y-%m-%d %H:%M')}"

  # version bump (skipped when there is no VERSION file or BUMP=none)
  BUMP="${BUMP:-patch}"
  if [[ -f VERSION && $BUMP != none ]]; then
    CURV=$(tr -d '[:space:]' < VERSION)
    REMV=""; git fetch -q origin "$BRANCH" 2>/dev/null && REMV=$(git show FETCH_HEAD:VERSION 2>/dev/null | tr -d '[:space:]')
    if [[ $CURV =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      if [[ -n $REMV && $CURV != "$REMV" && $(printf '%s\n%s\n' "$CURV" "$REMV" | sort -V | tail -1) == "$CURV" ]]; then
        NEWV=$CURV; say "VERSION $CURV is already ahead of GitHub ($REMV): keeping it"
      else
        IFS=. read -r MA MI PA <<<"$CURV"
        case $BUMP in major) NEWV="$((MA+1)).0.0" ;; minor) NEWV="$MA.$((MI+1)).0" ;; *) NEWV="$MA.$MI.$((PA+1))" ;; esac
        # never go backwards or sideways of what is on GitHub
        if [[ -n $REMV && $(printf '%s\n%s\n' "$NEWV" "$REMV" | sort -V | tail -1) != "$NEWV" || $NEWV == "$REMV" ]]; then
          IFS=. read -r MA MI PA <<<"$REMV"; NEWV="$MA.$MI.$((PA+1))"
        fi
        echo "$NEWV" > VERSION; ok "Version $CURV → $NEWV"
      fi
      [[ -f README.md ]] && sed -i "s/badge\/version-[0-9.]*-/badge\/version-$NEWV-/" README.md
      if [[ -f docs/CHANGELOG.md ]] && ! grep -q "^## $NEWV\$" docs/CHANGELOG.md; then
        awk -v v="$NEWV" -v m="$MSG" 'NR==1{print; print ""; print "## " v; print "- " m; next} {print}' docs/CHANGELOG.md > docs/CHANGELOG.md.tmp && mv docs/CHANGELOG.md.tmp docs/CHANGELOG.md
      fi
    fi
  fi

  git add -A
  git commit -q -m "$MSG" || die "Commit failed."
  ok "Committed: $MSG"
fi

# 7. push
git rev-parse --verify -q HEAD >/dev/null 2>&1 || die "Nothing committed yet, so there is nothing to push."
say "Pushing $BRANCH to origin…"
if git push -u origin "$BRANCH"; then
  ok "Pushed to $(git remote get-url origin)"
  exit 0
fi

# push was rejected: the remote already has commits we don't have
warn "Push rejected: the remote has commits you don't have locally."
if ! git fetch -q origin "$BRANCH"; then die "Couldn't fetch origin/$BRANCH. Check the repo URL, your login (use a token as the password) and your connection."; fi
if ! git merge-base HEAD FETCH_HEAD >/dev/null 2>&1; then
  # Unrelated histories (e.g. this folder was git-init'ed fresh but the repo on GitHub already has files).
  # Keep your files exactly as they are, but record them as a new commit ON TOP of the remote's history.
  # No conflicts, nothing is force-pushed, and the old history stays in GitHub.
  say "Different history from the remote: putting your files on top of it (no conflicts, no force-push)"
  git reset -q --soft FETCH_HEAD || die "Couldn't line up with the remote."
  git add -A
  git commit -q -m "${MSG:-update $(date '+%Y-%m-%d %H:%M')} (sync with remote)" || warn "Nothing to commit on top of the remote (your files already match it)."
else
  say "Merging the remote's changes first (git pull --rebase)…"
  if ! git pull -q --rebase origin "$BRANCH"; then
    git rebase --abort >/dev/null 2>&1
    die "Conflicting edits on both sides. Run: git pull --rebase origin $BRANCH, fix the conflicted files, git add them, git rebase --continue, then run this script again."
  fi
fi
if git push -u origin "$BRANCH"; then ok "Pushed to $(git remote get-url origin)"; exit 0; fi
die "Still failing. Check: (1) the repo exists and you can write to it, (2) use a Personal Access Token as the password (not your GitHub password)."
