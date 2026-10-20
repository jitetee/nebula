#!/usr/bin/env bash
# nebula — "did you mean?"  Usage: suggest.sh [--nebula] <word>
# --nebula limits suggestions to Nebula's own commands.
only=0; [[ ${1:-} == --nebula ]] && { only=1; shift; }
w=${1:-}; [[ -z $w ]] && exit 1
NEBULA_HOME="${NEBULA_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NEBULA_CFG="${NEBULA_CFG:-$NEBULA_HOME/data}"
hide=" "; [[ -s $NEBULA_CFG/hidden.txt ]] && hide=" $(<"$NEBULA_CFG/hidden.txt") "
{
  awk -F'|' -v hide="$hide" '/^@/{n=substr($1,2); if (!index(hide," " n " ")) print n}' "$NEBULA_HOME/assets/help.txt"
  (( only )) || compgen -c 2>/dev/null
} | sort -u | awk -v w="$w" '
function lev(a,b,   la,lb,i,j,cost,p,c,m) {
  la=length(a); lb=length(b)
  for (j=0;j<=lb;j++) p[j]=j
  for (i=1;i<=la;i++) { c[0]=i
    for (j=1;j<=lb;j++) { cost=(substr(a,i,1)==substr(b,j,1))?0:1
      m=p[j]+1; if (c[j-1]+1<m) m=c[j-1]+1; if (p[j-1]+cost<m) m=p[j-1]+cost; c[j]=m }
    for (j=0;j<=lb;j++) p[j]=c[j] }
  return p[lb] }
function adj(a,b,   i,n) { if (length(a)!=length(b)) return 0; n=length(a)
  for (i=1;i<n;i++) if (substr(a,1,i-1)==substr(b,1,i-1) && substr(a,i,1)==substr(b,i+1,1) && substr(a,i+1,1)==substr(b,i,1) && substr(a,i+2)==substr(b,i+2)) return 1
  return 0 }
{ d=length($0)-length(w); if (d<0) d=-d; if (d>2) next
  l=adj(w,$0)?1:lev(w,$0); lim=(length(w)<=3)?1:2
  if (l>0 && l<=lim) print l "\t" $0 }' \
  | sort -n | head -3 | cut -f2 | paste -sd' ' - | {
    read -r out
    [[ -n $out ]] && printf '  \033[38;5;221m💡 Did you mean:\033[0m %s\n' "${out// /  ·  }"
  }
