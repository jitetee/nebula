// Slash commands for the ant REPL (/help, /model, /key, /run, ...). Zero dependencies.
// handleCommand(text, ctx) → true when the command was recognised.
// ctx = { rl, arg, sessionId, history, cfg, reset(), resume(id) } supplied by index.js.
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { load, save, setKey, hasKey, CONFIG_PATH } from "./config.js";
import { PROVIDERS } from "./providers.js";
import { listFor, defaultModel } from "./models.js";
import { listSessions, relTime } from "./sessions.js";
import { requestAbort } from "./agent.js";
import { isReadOnlyBash } from "./tools.js";
import { pick, prompt } from "./picker.js";
import { C, rule } from "./ui.js";

const HELP = [
  ["navigation", [["/help", "show this help"], ["/exit", "quit"]]],
  ["session control", [["/cancel", "abort the running turn (or press ESC)"], ["/reset", "clear conversation history (new session)"], ["/sessions", "list recent saved sessions"], ["/resume [id]", "resume session (or last if omitted)"]]],
  ["configuration", [["/provider", "pick provider (interactive)"], ["/model", "pick model (interactive)"], ["/key [provider]", "set API key (interactive)"], ["/baseurl <url>", "set base URL (generic provider)"], ["/system <text|default>", "set/clear custom system prompt"], ["/setup", "re-run first-run setup"]]],
  ["filesystem", [["/cd <path>", "change working directory"], ["/pwd", "show working directory"], ["/show", "show current config"], ["/clear", "clear screen"]]],
  ["shell", [["/run <cmd>", "execute a shell command (safety checked)"], ["!<cmd>", "shortcut for /run"]]],
];

const DANGEROUS = [/\brm\s+(-[a-zA-Z]*\s+)*(\/|~|\$HOME|\*)(\s|$)/, /\bmkfs\b/, /\bdd\s+.*of=\/dev\//, /:\(\)\s*\{/, />\s*\/dev\/(sd|mmcblk|nvme)/, /\bchmod\s+-R\s+0?777\s+\//, /\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z)?sh\b/];

function help() {
  console.log("");
  for (const [section, rows] of HELP) { console.log(rule(section)); for (const [c, d] of rows) console.log(`  ${C.cyan(c.padEnd(24))} ${d}`); }
  console.log("");
}

async function pickProvider(cfg) {
  const items = PROVIDERS.map((p) => ({ id: p, label: p, note: hasKey(cfg, p) ? "key set" : "no key" }));
  const sel = await pick({ title: "Select provider", items, initial: Math.max(0, PROVIDERS.indexOf(cfg.provider)) });
  return sel ? sel.id : null;
}
async function pickModel(provider, current) {
  const list = listFor(provider);
  if (!list.length) return (await prompt(C.dim(`Enter model id for ${provider}: `))) || null;
  const sel = await pick({ title: `Select model for ${provider}`, items: list.map((m) => ({ id: m.id, label: m.id, note: m.note })), initial: Math.max(0, list.findIndex((m) => m.id === current)) });
  return sel ? sel.id : null;
}
async function askKey(provider) {
  const k = await prompt(C.dim(`Paste API key for ${provider} (input hidden): `), { hide: true });
  if (!k) { console.log(C.yellow("no key entered")); return false; }
  setKey(provider, k); console.log(C.green(`✓ key saved for ${provider}`)); return true;
}
const sync = (cfg, fresh) => { Object.assign(cfg, fresh); };

async function runShell(cmd) {
  if (!cmd) { console.log(C.yellow("Usage: /run <shell command>")); return; }
  if (DANGEROUS.some((re) => re.test(cmd))) { console.log(C.red("refused: that command looks destructive. Run it yourself if you are sure.")); return; }
  if (!isReadOnlyBash(cmd)) {
    const a = await prompt(C.yellow(`run \`${cmd}\`? (y/N) `));
    if (!/^y/i.test(a)) { console.log(C.dim("cancelled")); return; }
  }
  await new Promise((resolve) => {
    const sh = process.env.SHELL || "/bin/sh";
    const child = spawn(sh, ["-c", cmd], { cwd: process.cwd(), stdio: "inherit" });
    const t = setTimeout(() => { console.log(C.yellow("\n(timed out after 120s, stopping)")); child.kill("SIGTERM"); }, 120000);
    child.on("close", (code) => { clearTimeout(t); if (code) console.log(C.dim(`exit ${code}`)); resolve(); });
    child.on("error", (e) => { clearTimeout(t); console.log(C.red(`error: ${e.message}`)); resolve(); });
  });
}

export async function handleCommand(text, ctx = {}) {
  const [name, ...rest] = text.trim().split(/\s+/);
  const arg = (ctx.arg !== undefined && name !== "/run" ? ctx.arg : rest.join(" ")).trim();
  const cfg = ctx.cfg || load();
  switch (name) {
    case "/help": case "/?": help(); return true;
    case "/exit": case "/quit": case "/q": ctx.rl && ctx.rl.close(); return true;
    case "/cancel": requestAbort(); console.log(C.dim("cancel requested")); return true;
    case "/reset": ctx.reset ? ctx.reset() : (ctx.history && (ctx.history.length = 0)); console.log(C.dim("✓ conversation cleared")); return true;
    case "/sessions": {
      const list = listSessions(10);
      if (!list.length) console.log(C.dim("no saved sessions yet"));
      list.forEach((s) => console.log(`  ${C.cyan(s.id)}  ${C.dim(relTime(s.updatedAt || s.createdAt))}  ${(s.firstMessage || "").slice(0, 60)}`));
      if (list.length) console.log(C.dim("  resume one with /resume <id>"));
      return true;
    }
    case "/resume": {
      const id = arg || listSessions(1)[0]?.id;
      if (!id) { console.log(C.yellow("no session to resume")); return true; }
      if (!(ctx.resume && ctx.resume(id))) console.log(C.yellow(`could not find session: ${id}`));
      return true;
    }
    case "/provider": {
      const p = await pickProvider(load()); if (!p) return true;
      const c = load(); c.provider = p; c.model = defaultModel(p) || c.model; save(c); sync(cfg, c);
      console.log(C.green(`✓ provider=${p}  model=${c.model}`));
      if (!hasKey(c, p)) console.log(C.yellow(`no key for ${p} yet: use /key`));
      return true;
    }
    case "/model": {
      const c = load(); const m = await pickModel(c.provider, c.model); if (!m) return true;
      c.model = m; save(c); sync(cfg, c); console.log(C.green(`✓ model=${m}`)); return true;
    }
    case "/key": {
      const p = arg || (await pickProvider(load())); if (!p) return true;
      if (!PROVIDERS.includes(p)) { console.log(C.yellow(`unknown provider: ${p}`)); return true; }
      await askKey(p); sync(cfg, load()); return true;
    }
    case "/baseurl": {
      if (!arg) { console.log(C.dim(`base url: ${load().baseUrl || "(none)"}`)); return true; }
      if (!/^https?:\/\//i.test(arg)) { console.log(C.yellow("must start with http:// or https://")); return true; }
      const c = load(); c.baseUrl = arg; save(c); sync(cfg, c); console.log(C.green("✓ base url saved")); return true;
    }
    case "/system": {
      const c = load();
      if (!arg) { console.log(C.dim(c.systemPrompt ? `custom prompt: ${c.systemPrompt.slice(0, 200)}` : "using the built-in prompt")); return true; }
      c.systemPrompt = arg === "default" ? "" : arg; save(c); sync(cfg, c); console.log(C.green(arg === "default" ? "✓ back to the built-in prompt" : "✓ custom prompt saved")); return true;
    }
    case "/setup": {
      const c = load(); const p = await pickProvider(c); if (!p) return true;
      c.provider = p; save(c);
      if (!hasKey(load(), p)) await askKey(p);
      const c2 = load(); const m = await pickModel(p, defaultModel(p)); if (m) c2.model = m; save(c2); sync(cfg, c2);
      console.log(C.green(`✓ provider=${c2.provider}  model=${c2.model}`)); return true;
    }
    case "/cd": {
      if (!arg) { console.log(C.yellow("Usage: /cd <path>")); return true; }
      const target = path.resolve(arg.replace(/^~(?=$|\/)/, os.homedir()));
      try { process.chdir(target); console.log(C.dim(process.cwd())); } catch (e) { console.log(C.red(`cannot cd: ${e.message}`)); }
      return true;
    }
    case "/pwd": console.log(process.cwd()); return true;
    case "/show": {
      const c = load(); const keys = Object.fromEntries(PROVIDERS.filter((p) => hasKey(c, p)).map((p) => [p, "••••"]));
      console.log(JSON.stringify({ provider: c.provider, model: c.model, baseUrl: c.baseUrl || "", maxSteps: c.maxSteps, maxTokens: c.maxTokens, keys, config: CONFIG_PATH }, null, 2)); return true;
    }
    case "/clear": process.stdout.write("\x1b[2J\x1b[H"); return true;
    case "/run": await runShell(ctx.arg !== undefined ? ctx.arg : rest.join(" ")); return true;
    default: return false;
  }
}

export async function commandPalette(ctx = {}) {
  const items = HELP.flatMap(([, rows]) => rows).filter(([c]) => c.startsWith("/")).map(([c, d]) => ({ id: c.split(" ")[0], label: c.split(" ")[0], note: d }));
  const sel = await pick({ title: "Commands", items, initial: 0 });
  if (sel) await handleCommand(sel.id, { ...ctx, arg: "" });
}
