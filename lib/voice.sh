#!/data/data/com.termux/files/usr/bin/env bash
# nebula — Nebula AI voice: your ONNX (Piper) voice first, then espeak, festival, termux-tts

# Load persisted voice preference (overrides default, but env wins if exported)
if [[ -z ${NEBULA_VOICE+x} && -f $NEBULA_CFG/voice ]]; then
  _v=$(<"$NEBULA_CFG/voice")
  case "$_v" in 0|1) export NEBULA_VOICE=$_v ;; esac
  unset _v
fi

# ── ONNX voice (Piper) ───────────────────────────────────────────────────
# Put a Piper voice (NAME.onnx plus NAME.onnx.json next to it) anywhere and run:  voice model /path/NAME.onnx
# The path is saved in $NEBULA_CFG/voice.model  (NEBULA_VOICE_MODEL overrides it).
# Needs python-numpy + python-onnxruntime + espeak (voice setup installs them) and any audio player.
voice::model() {
  local m=${NEBULA_VOICE_MODEL:-}
  [[ -z $m && -s $NEBULA_CFG/voice.model ]] && m=$(<"$NEBULA_CFG/voice.model")
  [[ -n $m && -r $m ]] && printf '%s' "$m"
}

# Engines, best first: the real `piper` program, the piper-tts python package, or Nebula's own
# lib/piper_lite.py (needs only: pkg install python-numpy python-onnxruntime espeak — no compiling).
voice::_lite_ok() {
  command -v python3 >/dev/null 2>&1 && python3 -c 'import numpy, onnxruntime' >/dev/null 2>&1 \
    && { command -v espeak-ng >/dev/null 2>&1 || command -v espeak >/dev/null 2>&1; }
}
voice::_piper_cmd() {   # → the command that runs a Piper voice, or nothing
  if command -v piper >/dev/null 2>&1; then printf 'piper'
  elif command -v python3 >/dev/null 2>&1 && python3 -c 'import piper' >/dev/null 2>&1; then printf 'python3 -m piper'
  elif voice::_lite_ok; then printf 'python3 %s/lib/piper_lite.py' "$NEBULA_HOME"; fi
}

# voice::why → what is still missing for the ONNX voice (one per line; empty = ready)
voice::why() {
  [[ -z $(voice::model) ]] && echo "no voice selected (run: voice scan)"
  if [[ -z $(voice::_piper_cmd) ]]; then
    command -v python3 >/dev/null 2>&1 && python3 -c 'import numpy' >/dev/null 2>&1 || echo "python-numpy missing"
    command -v python3 >/dev/null 2>&1 && python3 -c 'import onnxruntime' >/dev/null 2>&1 || echo "python-onnxruntime missing"
    command -v espeak-ng >/dev/null 2>&1 || command -v espeak >/dev/null 2>&1 || echo "espeak missing"
  fi
  [[ -z $(voice::_player) ]] && echo "no audio player (sox, mpv or paplay)"
  return 0
}

# voice::setup → install what the ONNX voice needs (Termux packages; no compiling)
voice::setup() {
  if command -v pkg >/dev/null 2>&1; then
    pkg install -y python-numpy python-onnxruntime espeak sox
  else
    echo "Install: python3 numpy onnxruntime espeak-ng and an audio player (sox/mpv)"; return 1
  fi
}

voice::_player() {      # first audio player found
  local p; for p in play paplay aplay mpv ffplay mpg123 termux-media-player; do command -v "$p" >/dev/null 2>&1 && { printf '%s' "$p"; return; }; done
}

voice::dir() { printf '%s' "${NEBULA_CFG:-$NEBULA_HOME/data}/voices"; }

# voice::scan → one Piper voice per line (the .onnx path); needs the .onnx.json that holds "phoneme_id_map".
# Looks through the whole device: home, shared storage, SD cards, Termux prefix.
voice::scan() {
  local roots=() r; for r in "$HOME" /sdcard /storage "${PREFIX:-/usr}/opt" /opt /usr/share; do [[ -d $r ]] && roots+=("$r"); done
  timeout "${NEBULA_SCAN_TIMEOUT:-40}" find "${roots[@]}" \( -path /proc -o -path /sys -o -path /dev -o -path '*/node_modules' -o -path '*/.cache' -o -path "$(voice::dir)" \) -prune -o \
    -type f -name '*.onnx' -size +300k -print 2>/dev/null | sort -u | while IFS= read -r f; do
      j=$f.json; [[ -r $j ]] || j=${f%.onnx}.json
      [[ -r $j ]] && grep -q phoneme_id_map "$j" 2>/dev/null && printf '%s\n' "$f"
    done
}

# voice::install <file.onnx> : copy the model and its json into Nebula's data folder and select it
voice::install() {
  local f=$1 j d base
  j=$f.json; [[ -r $j ]] || j=${f%.onnx}.json
  d=$(voice::dir); mkdir -p "$d" || return 1
  base=$(basename "$f")
  cp -f "$f" "$d/$base" || return 1
  [[ -r $j ]] && cp -f "$j" "$d/$base.json"
  printf '%s\n' "$d/$base" > "$NEBULA_CFG/voice.model"
}

voice::onnx_ready() { [[ -n $(voice::model) && -n $(voice::_piper_cmd) && -n $(voice::_player) ]]; }

voice::_play() {
  case $(voice::_player) in
    play)   play -q "$1" ;;       paplay) paplay "$1" ;;      aplay) aplay -q "$1" ;;
    mpv)    mpv --really-quiet --no-video "$1" ;;             ffplay) ffplay -nodisp -autoexit -loglevel quiet "$1" ;;
    mpg123) mpg123 -q "$1" ;;     termux-media-player) termux-media-player play "$1" >/dev/null ;;
  esac
}

# ── fast path for the built-in engine: keep the model loaded in a background server ──────────────
# Without it every phrase pays for starting Python, importing numpy + onnxruntime and loading the model
# (several seconds on a phone). The server loads once, answers in a moment, speaks long text sentence by
# sentence while the next one is being made, and stops by itself after 15 idle minutes.
voice::_sock() { printf '%s' "${TMPDIR:-/tmp}/nebula-voice-$(id -u).sock"; }
voice::_is_lite() { [[ $(voice::_piper_cmd) == *piper_lite.py ]]; }
voice::_server_start() {
  local sock; sock=$(voice::_sock)
  [[ -S $sock ]] && return 0
  rm -f "$sock"
  ( setsid python3 "$NEBULA_HOME/lib/piper_lite.py" --serve "$sock" --idle "${NEBULA_VOICE_IDLE:-900}" >/dev/null 2>&1 & echo $! > "$sock.pid" )
  local i; for i in $(seq 1 100); do [[ -S $sock ]] && return 0; sleep 0.05; done
  return 1
}
voice::stop() { local sock; sock=$(voice::_sock); [[ -f $sock.pid ]] && kill "$(cat "$sock.pid")" 2>/dev/null; rm -f "$sock" "$sock.pid"; }
voice::warm() {   # start loading the model in the background (call when you know speech is coming)
  [[ ${NEBULA_VOICE:-1} -eq 0 ]] && return 0
  voice::onnx_ready && voice::_is_lite && { voice::_server_start; ( python3 "$NEBULA_HOME/lib/piper_lite.py" --say "$(voice::_sock)" --model "$(voice::model)" --cache "${NEBULA_CFG:-/tmp}/voice-cache" <<< "." >/dev/null 2>&1 & ); }
  return 0
}
voice::_lite_say() {   # voice::_lite_say <text>  → plays each sentence as soon as it is ready
  local msg=$1 model sock dir wav tries=0 got
  model=$(voice::model); sock=$(voice::_sock); dir=${NEBULA_CFG:-/tmp}/voice-cache; mkdir -p "$dir" 2>/dev/null
  while (( tries < 2 )); do
    voice::_server_start || return 1
    got=0
    while IFS= read -r wav; do
      [[ -s $wav ]] && { voice::_play "$wav" >/dev/null 2>&1; got=1; }
    done < <(printf '%s' "$msg" | python3 "$NEBULA_HOME/lib/piper_lite.py" --say "$sock" --model "$model" --cache "$dir" 2>/dev/null; echo)
    (( got )) && { ls -1t "$dir"/*.wav 2>/dev/null | tail -n +81 | xargs rm -f 2>/dev/null; return 0; }
    voice::stop; tries=$((tries+1))      # stale server: restart once
  done
  return 1
}

# voice::_onnx_say <text> : make (or reuse) the wav for this text, then play it. Runs in the foreground.
voice::_onnx_say() {
  local msg=$1 model piper dir wav key
  voice::_is_lite && { voice::_lite_say "$msg"; return; }
  model=$(voice::model); piper=$(voice::_piper_cmd)
  dir=${NEBULA_CFG:-/tmp}/voice-cache; mkdir -p "$dir" 2>/dev/null
  key=$(printf '%s|%s' "$model" "$msg" | cksum | awk '{print $1}'); wav=$dir/$key.wav
  if [[ ! -s $wav ]]; then
    printf '%s' "$msg" | $piper --model "$model" --output_file "$wav" >/dev/null 2>&1 \
      || printf '%s' "$msg" | $piper --model "$model" --output-file "$wav" >/dev/null 2>&1 \
      || { rm -f "$wav"; return 1; }
  fi
  [[ -s $wav ]] || return 1
  voice::_play "$wav" >/dev/null 2>&1
  # keep the cache small
  ls -1t "$dir"/*.wav 2>/dev/null | tail -n +61 | xargs rm -f 2>/dev/null
  return 0
}

voice::available() {
  voice::onnx_ready || \
  command -v espeak >/dev/null 2>&1 || \
  command -v festival >/dev/null 2>&1 || \
  command -v termux-tts-speak >/dev/null 2>&1
}

voice::say() {
  local msg="$*"
  [[ -z $msg ]] && return 0
  [[ ${NEBULA_VOICE:-1} -eq 0 ]] && return 0

  if voice::onnx_ready; then
    # your ONNX voice first; if it fails once, fall through to the old engines
    ( voice::_onnx_say "$msg" || voice::_legacy_say "$msg" ) >/dev/null 2>&1 &
    return 0
  fi
  voice::_legacy_say "$msg" &
}

voice::_legacy_say() {
  local msg=$1
  if command -v espeak >/dev/null 2>&1; then
    espeak -v en-gb -s 150 -p 40 -a 180 "$msg" 2>/dev/null
  elif command -v festival >/dev/null 2>&1; then
    echo "$msg" | festival --tts 2>/dev/null
  elif command -v termux-tts-speak >/dev/null 2>&1; then
    termux-tts-speak -l en -r 0.9 -p 0.9 "$msg" 2>/dev/null
  fi
}

voice::greet() {
  voice::warm
  local hour=$(date +%H)
  local user=${NEBULA_USER:-sir}
  local greeting="Good evening"
  if   (( hour < 12 )); then greeting="Good morning"
  elif (( hour < 18 )); then greeting="Good afternoon"
  fi
  voice::say "$greeting, $user. All systems are online. How may I assist you today?"
}

voice::bye() {
  voice::say "Powering down. Goodbye, ${NEBULA_USER:-sir}."
}
