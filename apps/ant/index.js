#!/usr/bin/env node
import readline from "node:readline";
import path from "node:path";
import { load, save, setKey, CONFIG_PATH, envName, hasKey, MODES, nextMode } from "./lib/config.js";
import { commandPalette, handleCommand } from "./lib/commands.js";
import { PROVIDERS } from "./lib/providers.js";
import { runTurn, requestAbort, clearAbort } from "./lib/agent.js";
import { C, welcomeBanner, rule, userPrefix, inputBoxTop, inputBoxBottom, exitSummary, makeBottomBar } from "./lib/ui.js";
import { MODELS, listFor, defaultModel } from "./lib/models.js";
import { pick, prompt } from "./lib/picker.js";
import {
  newSessionId,
  saveSession,
  loadSession,
  listSessions,
  latestSessionId,
  relTime,
} from "./lib/sessions.js";

// Set terminal session title (works in Termux, xterm, etc.)
function setTerminalTitle(title) {
  process.stdout.write(`\x1b]0;${title}\x07`);
}
// Reset title on exit
function resetTerminalTitle() {
  process.stdout.write(`\x1b]0;\x07`);
}

const VERSION = "0.1.0";

function parseArgs(argv) {
  const out = { resume: null, continueLast: false, help: false };
  const a = argv.slice(2);
  for (let i = 0; i < a.length; i++) {
    const t = a[i];
    if (t === "--session" || t === "-s") out.resume = a[++i];
    else if (t === "-c" || t === "--continue" || t === "--resume") out.continueLast = true;
    else if (t === "-h" || t === "--help") out.help = true;
    else if (t.startsWith("--session=")) out.resume = t.slice("--session=".length);
  }
  return out;
}

function buildSystemPrompt() {
  return `You are Ant, a terminal coding agent running on the user's device.
- Working directory: ${process.cwd()}
- Platform: ${process.platform} (Termux/Android-friendly, zsh available)
- File tools: read_file, list_dir, glob, search.
- Edit tools: write_file (create/rewrite), edit_file (single surgical edit), apply_patch (multiple edits to one file atomically).
- Exec tools: bash, run_code (python/node/bash), git (refuses destructive subcommands without confirm=true).
- Net tools: http_get for fetching docs or public APIs.
- Skills: call skill_list to see available playbooks, then skill_get <name> to load one — follow the loaded markdown as instructions for the current task. Skills live at ~/.ant/skills/.

ACT, DON'T HESITATE. When the user asks a question that a shell command can answer, run the command immediately — don't ask permission, don't speculate, don't suggest the user run it. Examples:
- "am I logged in to github?" → run \`gh auth status\`
- "what npm account am I on?" → run \`npm whoami\`
- "is the dev server running?" → run \`ps aux | grep -i node\` or check the port
- "any errors in the logs?" → \`tail -n 200\` the log file, or \`journalctl\`/\`logcat\` if relevant
- "what node version?" → \`node -v\`
- "is X installed?" → \`which X\` or \`command -v X\`
Read-only inspection commands (\`gh auth status\`, \`npm whoami\`, \`git status/log/diff/branch\`, \`ls\`, \`cat\`, \`which\`, \`env\`, \`ps\`, \`tail\`, \`head\`, \`wc\`, \`node -v\`, \`npm -v\`, \`pwd\`) auto-approve — just run them.

When a command times out, you'll see partial stdout/stderr captured up to the kill — use it. Re-run with a longer timeout_ms or a narrower invocation if needed.

Prefer reading before editing. Prefer apply_patch over multiple edit_file calls when changing several spots in one file. Be concise. After finishing a task, give a one or two sentence summary.`;
}

function helpText() {
  return [
    rule("navigation"),
    `  ${C.cyan("/help")}                   show this help`,
    `  ${C.cyan("/exit")}                   quit`,
    rule("session control"),
    `  ${C.cyan("/cancel")}                 abort the running turn (or press ESC)`,
    `  ${C.cyan("/reset")}                  clear conversation history (new session)`,
    `  ${C.cyan("/sessions")}               list recent saved sessions`,
    `  ${C.cyan("/resume")} [id]            resume session (or last if omitted)`,
    rule("configuration"),
    `  ${C.cyan("/provider")}               pick provider (interactive)`,
    `  ${C.cyan("/model")}                  pick model (interactive)`,
    `  ${C.cyan("/key")} [provider]         set API key (interactive)`,
    `  ${C.cyan("/baseurl")} <url>          set base URL (generic provider)`,
    `  ${C.cyan("/system")} <text|default>  set/clear custom system prompt`,
    `  ${C.cyan("/setup")}                  re-run first-run setup`,
    rule("filesystem"),
    `  ${C.cyan("/cd")} <path>              change working directory`,
    `  ${C.cyan("/pwd")}                    show working directory`,
    `  ${C.cyan("/show")}                   show current config`,
    `  ${C.cyan("/clear")}                  clear screen`,
  rule("shell"),
  `  ${C.cyan("/run")} <cmd>                execute a shell command (safety checked)`,
  `  ${C.cyan("!")}<cmd>                   shortcut for /run`,
  ].join("\n");
}

async function pickProviderInteractive(currentCfg) {
  const items = PROVIDERS.map((p) => ({ id: p, label: p, note: hasKey(currentCfg, p) ? "key set" : "no key" }));
  const sel = await pick({ title: "Select provider", items, initial: Math.max(0, PROVIDERS.indexOf(currentCfg.provider)) });
  return sel ? sel.id : currentCfg.provider;
}

async function pickModelInteractive(provider, currentModel) {
  const list = listFor(provider);
  if (!list.length) {
    const id = await prompt(C.dim(`Enter model id for ${provider}: `));
    return id || null;
  }
  const items = list.map((m) => ({ id: m.id, label: m.id, note: m.note }));
  const initial = Math.max(0, list.findIndex((m) => m.id === currentModel));
  const sel = await pick({ title: `Select model for ${provider}`, items, initial });
  return sel ? sel.id : null;
}

async function promptKey(provider) {
  const k = await prompt(C.dim(`Paste API key for ${provider} (input hidden): `), { hide: true });
  return k;
}

async function ensureSetup(cfg) {
  // Auto-default to openrouter if invalid
  if (!PROVIDERS.includes(cfg.provider)) {
    cfg.provider = "openrouter";
    save(cfg);
  }
  if (hasKey(cfg, cfg.provider) && cfg.model && listFor(cfg.provider).some((m) => m.id === cfg.model)) {
    return cfg;
  }
  console.log(rule("first-time setup"));
  if (!hasKey(cfg, cfg.provider)) {
    const k = await promptKey(cfg.provider);
    if (k) {
      setKey(cfg.provider, k);
      console.log(C.dim(`saved key for ${cfg.provider}`));
    } else {
      console.log(C.yellow("no key entered — you can set one later with /key"));
    }
  }
  if (!cfg.model || !listFor(cfg.provider).some((m) => m.id === cfg.model)) {
    cfg.model = defaultModel(cfg.provider);
  }
  const sel = await pickModelInteractive(cfg.provider, cfg.model);
  if (sel) cfg.model = sel;
  save(cfg);
  console.log(C.dim(`✓ provider=${cfg.provider}  model=${cfg.model}`));
  console.log("");
  return cfg;
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    console.log(`ant — terminal coding agent

Usage:
  ant                       start a new session
  ant -c, --continue        resume the most recent session
  ant --session <id>        resume a specific session
  ant -h, --help            show this help`);
    return;
  }

  let cfg = load();

  // Recent activity for banner
  const recent = listSessions(4).map((s) => ({
    id: s.id,
    firstMessage: s.firstMessage || "",
    relTime: relTime(s.updatedAt),
  }));

  // Resume target
  let resumeId = null;
  if (args.resume) resumeId = args.resume;
  else if (args.continueLast) resumeId = latestSessionId();

  console.log(welcomeBanner(cfg, VERSION, recent));
  console.log("");

  cfg = await ensureSetup(cfg);
  // Update terminal title to show program name and cwd
  setTerminalTitle(`ant•${path.basename(process.cwd()) || "/"}`);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: userPrefix(cfg),
    terminal: true,
    historySize: 500,
  });

  // Bracketed paste — terminal wraps pastes in \e[200~ ... \e[201~.
  if (process.stdout.isTTY) process.stdout.write("\x1b[?2004h");
  const disablePaste = () => { if (process.stdout.isTTY) process.stdout.write("\x1b[?2004l"); };
  process.on("exit", disablePaste);

  const NL_PLACEHOLDER = "\u2424"; // ␤ — visible newline placeholder

  if (process.stdin.isTTY) {
    const PASTE_START = Buffer.from("\x1b[200~");
    const PASTE_END = Buffer.from("\x1b[201~");
    let pasting = false;
    let pasteBuf = [];

    const origStdinEmit = process.stdin.emit.bind(process.stdin);
    process.stdin.emit = function (event, ...args) {
      if (event !== "data") return origStdinEmit(event, ...args);
      let chunk = args[0];
      if (!Buffer.isBuffer(chunk)) chunk = Buffer.from(chunk);

      while (chunk.length > 0) {
        if (!pasting) {
          const i = chunk.indexOf(PASTE_START);
          if (i === -1) {
            return origStdinEmit("data", chunk);
          }
          if (i > 0) origStdinEmit("data", chunk.slice(0, i));
          pasting = true;
          pasteBuf = [];
          chunk = chunk.slice(i + PASTE_START.length);
        } else {
          const j = chunk.indexOf(PASTE_END);
          if (j === -1) {
            pasteBuf.push(chunk);
            return;
          }
          pasteBuf.push(chunk.slice(0, j));
          const full = Buffer.concat(pasteBuf).toString("utf8");
          pasting = false;
          pasteBuf = [];
          chunk = chunk.slice(j + PASTE_END.length);

          const cleaned = full.replace(/\r?\n|\r/g, NL_PLACEHOLDER);
          if (rl) {
            const lines = full.split(/\r?\n|\r/).length;
            if (lines > 1) {
              process.stdout.write("\r\x1b[2K" + C.dim(`  [pasted ${full.length} chars, ${lines} lines — press Enter to send, edit before Enter]`) + "\n");
              rl.prompt(true);
            }
            rl.write(cleaned);
          }
        }
      }
    };
  }

  let sigintArmed = false;
  let turnActive = false;

  // ESC: cancel in-flight turn, OR clear current input when idle.
  if (process.stdin.isTTY) {
    readline.emitKeypressEvents(process.stdin);
    process.stdin.on("keypress", (_str, key) => {
      if (!key || key.name !== "escape") return;
      if (turnActive) {
        requestAbort();
        process.stdout.write("\n" + C.yellow("(cancelling…)") + "\n");
      } else if (rl && rl.line && rl.line.length > 0) {
        rl.line = "";
        rl.cursor = 0;
        rl._refreshLine();
      }
    });
  }
  rl.on("SIGINT", () => {
    if (sigintArmed) {
      rl.close();
      exitWithSummary(0);
      return;
    }
    sigintArmed = true;
    setTimeout(() => { sigintArmed = false; }, 2000);
    process.stdout.write("\n" + C.dim("(ctrl-c again to quit)") + "\n");
    rl.prompt();
  });

  const askConfirm = async (msg) => {
    const a = await prompt(C.yellow(`${msg} (y/N) `));
    return /^y/i.test(a);
  };

  let history = [];
  let sessionId = newSessionId();
  let sessionFirstMessage = "";
  let sessionCreatedAt = Date.now();
  const sessionStartTime = Date.now();
  const stats = { tokens: 0, turns: 0, toolCalls: 0 };

  const useBottomBar = process.env.ANT_BOTTOM_BAR === "1" && process.stdout.isTTY && (process.stdout.rows || 0) >= 8;
  const bar = useBottomBar ? makeBottomBar() : null;

  const printExitSummary = () => {
    if (bar) bar.uninstall();
    console.log("");
    console.log(exitSummary({
      sessionId,
      model: cfg.model,
      provider: cfg.provider,
      cwd: process.cwd(),
      tokens: stats.tokens,
      elapsedMs: Date.now() - sessionStartTime,
      turns: stats.turns,
      toolCalls: stats.toolCalls,
      firstMessage: sessionFirstMessage,
    }));
  };

  let summaryShown = false;
  const exitWithSummary = (code = 0) => {
    if (summaryShown) process.exit(code);
    summaryShown = true;
    resetTerminalTitle();
    printExitSummary();
    process.exit(code);
  };

  if (resumeId) {
    const s = loadSession(resumeId);
    if (s) {
      sessionId = s.id;
      history = s.history || [];
      sessionFirstMessage = s.firstMessage || "";
      sessionCreatedAt = s.createdAt || Date.now();
      console.log(C.dim(`↺ resumed session ${C.cyan(sessionId)} (${history.length} messages)`));
      console.log("");
    } else {
      console.log(C.yellow(`could not find session: ${resumeId}`));
    }
  }

  const persist = (h, firstUser) => {
    if (!sessionFirstMessage && firstUser) sessionFirstMessage = firstUser.slice(0, 120);
    saveSession(sessionId, {
      cwd: process.cwd(),
      provider: cfg.provider,
      model: cfg.model,
      history: h,
      firstMessage: sessionFirstMessage,
      createdAt: sessionCreatedAt,
    });
  };

  const showBox = () => {
    if (bar) {
      bar.install();
      bar.redraw();
      rl.setPrompt(""); 
    } else {
      console.log(inputBoxTop());
      rl.setPrompt(userPrefix());
      rl.prompt();
    }
  };
  const closeBox = () => {
    if (bar) {
      // no-op
    } else {
      console.log(inputBoxBottom(load(), stats));
    }
  };

  if (bar) {
    process.stdout.on("resize", () => bar.onResize());
    bar.install();
    bar.redraw();
  } else {
    showBox();
  }

  const cmdCtx = () => ({
    rl, sessionId, history, cfg,
    reset: () => { history = []; sessionId = newSessionId(); sessionFirstMessage = ""; sessionCreatedAt = Date.now(); },
    resume: (id) => {
      const s = loadSession(id);
      if (!s) return false;
      sessionId = s.id; history = s.history || []; sessionFirstMessage = s.firstMessage || ""; sessionCreatedAt = s.createdAt || Date.now();
      console.log(C.dim(`↺ resumed session ${C.cyan(sessionId)} (${history.length} messages)`));
      return true;
    },
  });

  for await (const rawLine of rl) {
    const line = rawLine.replace(new RegExp(NL_PLACEHOLDER, "g"), "\n");
    const text = line.trim();
    closeBox();
    if (!text) {
      showBox();
      continue;
    }
    
    if (text === "/") {
      rl.pause();
      await commandPalette(cmdCtx());
      rl.resume();
      showBox();
      continue;
    } else if (text.startsWith("/")) {
      const handled = await handleCommand(text, { ...cmdCtx(), arg: text.split(" ").slice(1).join(" ") });
      if (!handled) console.log(C.yellow("unknown command — /help"));
      showBox();
      continue;
    }
    
    if (text.startsWith("!")) {
      const cmd = text.slice(1).trim();
      if (!cmd) {
        console.log(C.yellow("Usage: !<shell command>"));
        showBox();
        continue;
      }
      const fakeSlash = "/run " + cmd;
      await handleCommand(fakeSlash, { ...cmdCtx(), arg: cmd });
      showBox();
      continue;
    }
    try {
      const liveCfg = load();
      liveCfg.systemPrompt = liveCfg.systemPrompt || buildSystemPrompt();
      turnActive = true;
      try {
        await runTurn({
          cfg: liveCfg,
          history,
          userInput: text,
          askConfirm,
          sessionId,
          onPersist: persist,
          stats,
        });
      } finally {
        turnActive = false;
      }
    } catch (e) {
      console.error(C.red(`error: ${e.message}`));
    }
    showBox();
  }
  printExitSummary();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
