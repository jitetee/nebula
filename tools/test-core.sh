#!/usr/bin/env bash
# Nebula core tests: help everywhere, plugins, one AI backend. Run: bash tools/test-core.sh   (CI runs it too)
set -u
H="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T=$(mktemp -d); trap 'kill ${MOCK:-0} 2>/dev/null; rm -rf "$T"' EXIT
export NEBULA_HOME=$H NEBULA_CFG=$T/cfg HOME=$T/home NO_COLOR=1 NEBULA_NO_AUTH=1 NEBULA_VOICE=0 NEBULA_SOUNDS=0
mkdir -p "$NEBULA_CFG" "$HOME/.ant"
pass=0; fail=0
t() { local name=$1; shift; if "$@" >"$T/out" 2>&1; then pass=$((pass+1)); printf '  ✔ %s\n' "$name"; else fail=$((fail+1)); printf '  ✖ %s\n' "$name"; sed 's/^/      /' "$T/out" | head -6; fi; }
has() { grep -q -- "$1" "$T/out"; }
N() { bash "$H/bin/nebula" "$@"; }

echo "consistency"
t "nebula check is clean"            bash "$H/lib/check.sh"

echo "help everywhere"
t "nebula ask --help"                bash -c "bash '$H/bin/nebula' ask --help | grep -q 'Ask Nebula AI'"
t "nebula play --help (not sox)"     bash -c "bash '$H/bin/nebula' play --help | grep -qi 'music'"
t "nebula ant --help (registry)"     bash -c "bash '$H/bin/nebula' ant --help | grep -q 'coding agent'"
t "ant -h"                           bash -c "cd '$H/apps/ant' && PYTHONPATH='$H/apps/ant:$H/lib' python3 -m ant -h | grep -q 'terminal coding agent'"
t "ant help"                         bash -c "cd '$H/apps/ant' && PYTHONPATH='$H/apps/ant:$H/lib' python3 -m ant help | grep -q 'terminal coding agent'"
t "jtlearn -h"                       bash -c "cd '$H/apps/jtlearn' && PYTHONPATH='$H/apps/jtlearn:$H/lib' python3 -m jtlearn -h | grep -qi 'learning'"
t "jtlearn help"                     bash -c "cd '$H/apps/jtlearn' && PYTHONPATH='$H/apps/jtlearn:$H/lib' python3 -m jtlearn help | grep -qi 'learn'"
t "python core: help render"         bash -c "PYTHONPATH='$H/lib' python3 -m nebula_core.help ai | grep -q 'backend'"

echo "plugins"
t "plugin new greet"                 N plugin new greet
t "check stays clean with a new plugin" bash "$H/lib/check.sh"
t "plugin runs"                      bash -c "bash '$H/bin/nebula' greet | grep -q 'greet works'"
t "plugin --help from its help.txt"  bash -c "bash '$H/bin/nebula' greet --help | grep -q 'What it does'"
t "plugin in help <name>"            bash -c "bash '$H/bin/nebula' help greet | grep -q 'greet'"
t "plugin in registry/python"        bash -c "PYTHONPATH='$H/lib' python3 -m nebula_core.help --names | grep -qw greet"
t "plugin name clash refused"        bash -c "! bash '$H/bin/nebula' plugin new ask"
t "plugin disable hides it"          bash -c "bash '$H/bin/nebula' plugin disable greet >/dev/null && ! PYTHONPATH='$H/lib' python3 -m nebula_core.help --names | grep -qw greet"
t "plugin enable brings it back"     bash -c "bash '$H/bin/nebula' plugin enable greet >/dev/null && PYTHONPATH='$H/lib' python3 -m nebula_core.help --names | grep -qw greet"

echo "one AI backend"
PORT=$((20000 + RANDOM % 20000))
python3 "$H/tools/mock_ai_server.py" $PORT & MOCK=$!; sleep 1
printf '{"provider":"generic","model":"mock","keys":{"generic":"k"},"baseUrl":"http://127.0.0.1:%s/v1"}' $PORT >"$HOME/.ant/config.json"
t "status shows ant"                 bash -c "bash '$H/bin/nebula' ai status | grep -q 'ant (generic, mock)'"
t "core answers through ant"         bash -c "PYTHONPATH='$H/lib' python3 -m nebula_core.ai 'two plus two' | grep -q 'MOCK: two plus two'"
t "shell AI path uses ant"           bash -c "source '$H/lib/ui.sh'; source '$H/lib/ai.sh'; NEBULA_HOME='$H'; ai::_complete 'ping shell' | grep -q 'MOCK: ping shell'"
t "ai backend tgpt is honoured"      bash -c "bash '$H/bin/nebula' ai backend tgpt >/dev/null; PYTHONPATH='$H/lib' python3 -m nebula_core.ai backend-name | grep -qv ant; bash '$H/bin/nebula' ai backend auto >/dev/null"
t "jtlearn tutor bridge uses ant"    bash -c "cd '$H/apps/jtlearn' && PYTHONPATH='$H/apps/jtlearn:$H/lib' python3 -c \"from jtlearn.main.ai_chat import _nebula_answer; r=_nebula_answer('hello jt','sys'); assert r and r.startswith('MOCK: hello jt'), r\""
t "ant --ask uses same config"       bash -c "cd '$H/apps/ant' && PYTHONPATH='$H/apps/ant:$H/lib' python3 -m ant --ask 'one shot' | grep -q 'MOCK: one shot'"

if command -v nvim >/dev/null 2>&1 && nvim --version | head -1 | grep -qE 'v0\.(9|1[0-9])'; then
  echo "neovim"
  mkdir -p "$NEBULA_CFG/plugins/greet" && echo 'vim.g.greet_plugin_loaded = 1' >"$NEBULA_CFG/plugins/greet/nvim.lua"
  t ":NebulaHelp + plugin nvim.lua"  bash -c "cd '$T' && NVIM_APPNAME=nebtest XDG_CONFIG_HOME='$T/xdg' bash -c 'mkdir -p $T/xdg && ln -sfn $H/assets/nvim $T/xdg/nebtest && nvim --headless -c \"lua local h=require(\\\"nebula.help\\\"); local e=h.load(); io.stdout:write((e.greet and \\\"greet-in-nvim \\\" or \\\"\\\")..(e.ant and \\\"ant-in-nvim \\\" or \\\"\\\")..tostring(vim.g.greet_plugin_loaded)..\\\"\\\\n\\\")\" -c qa 2>&1' | grep -q 'greet-in-nvim ant-in-nvim 1'"
fi

echo; echo "  $pass passed, $fail failed"; (( fail == 0 ))
