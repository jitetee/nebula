import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import os from "node:os";

const READ_ONLY = new Set(["read_file", "list_dir", "search", "glob", "http_get", "skill_list", "skill_get"]);
const WRITE_OR_EXEC = new Set([
  "write_file",
  "edit_file",
  "apply_patch",
  "mkdir",
  "delete_path",
  "bash",
  "run_code",
  "git",
]);

// ---- Helper constants ----
const MAX_OUTPUT = 200_000; // 200KB ~30k tokens
const DEFAULT_BASH_TIMEOUT = 30_000; // 30s
const DEFAULT_GIT_TIMEOUT = 60_000; // 60s

// ---- Read‑only Bash detection (unchanged) ----
const READ_ONLY_BASH_HEADS = new Set([
  "ls", "ll", "la", "cat", "bat", "head", "tail", "wc", "stat", "file",
  "pwd", "whoami", "id", "env", "printenv", "echo", "date", "uptime",
  "uname", "hostname", "which", "type", "command", "compgen",
  "ps", "top", "df", "du", "free", "lsof", "netstat", "ss",
  "node", "npm", "npx", "python", "python3", "pip", "pip3",
  "gh", "git", "yarn", "pnpm", "bun", "deno", "go", "cargo", "rustc",
  "tree", "find", "grep", "rg", "ag", "ack", "fd", "fzf",
  "curl", "wget", "ping", "dig", "nslookup", "host",
  "termux-info", "pkg", "dpkg", "apt",
  "tldr", "man", "help",
  "jq", "yq", "xq",
  "diff", "cmp",
]);

const MUTATING_SUBCMDS = {
  git: new Set(["push", "pull", "fetch", "merge", "rebase", "reset", "checkout", "switch",
                 "commit", "add", "rm", "mv", "stash", "tag", "clone", "init", "clean",
                 "cherry-pick", "revert", "apply", "am", "submodule", "worktree", "config"]),
  npm: new Set(["install", "i", "uninstall", "remove", "rm", "update", "upgrade",
                "publish", "unpublish", "link", "unlink", "init", "run", "start", "test",
                "ci", "audit", "fund", "dedupe", "prune", "rebuild"]),
  yarn: new Set(["add", "remove", "install", "upgrade", "publish", "link", "unlink", "init"]),
  pnpm: new Set(["add", "remove", "install", "i", "update", "publish", "link", "unlink", "init"]),
  pkg: new Set(["install", "i", "uninstall", "remove", "rm", "upgrade", "update"]),
  apt: new Set(["install", "remove", "purge", "upgrade", "update", "autoremove"]),
  pip: new Set(["install", "uninstall", "wheel"]),
  pip3: new Set(["install", "uninstall", "wheel"]),
  go: new Set(["install", "get", "mod", "build", "run", "test", "clean"]),
  cargo: new Set(["install", "uninstall", "publish", "build", "run", "test", "clean", "update"]),
  gh: new Set(["pr-create", "issue-create", "release-create", "repo-create", "repo-delete",
                "auth-login", "auth-logout"]),
};

export function isReadOnlyBash(command) {
  if (!command || typeof command !== "string") return false;
  const cmd = command.trim();
  if (/[`$]\(/.test(cmd)) return false; // command substitution
  if (/(^|[^&])>>?\s*\S/.test(cmd)) return false; // redirection
  if (/[;&]{1,2}/.test(cmd) && !/^\s*[^|;&]+(\s*\|\s*[^|;&]+)*\s*$/.test(cmd)) return false;
  const segments = cmd.split("|").map(s => s.trim()).filter(Boolean);
  if (!segments.length) return false;
  for (const seg of segments) {
    const stripped = seg.replace(/^(\s*[A-Z_][A-Z0-9_]*=\S+\s+)+/i, "");
    const tokens = stripped.split(/\s+/).filter(Boolean);
    if (!tokens.length) return false;
    const head = tokens[0].split("/").pop();
    if (!READ_ONLY_BASH_HEADS.has(head)) return false;
    const sub = (tokens[1] || "").replace(/^-+/, "");
    const mut = MUTATING_SUBCMDS[head];
    if (mut && tokens[1] && !tokens[1].startsWith("-") && mut.has(tokens[1])) return false;
    if (head === "gh" && tokens[1] === "auth" && (tokens[2] === "login" || tokens[2] === "logout")) return false;
  }
  return true;
}

export function isReadOnlyToolCall(name, args) {
  if (READ_ONLY.has(name)) return true;
  if (name === "bash") return isReadOnlyBash(args?.command || "");
  if (name === "git") {
    const sub = (args?.args || [])[0];
    return sub && !MUTATING_SUBCMDS.git.has(sub);
  }
  return false;
}

export const TOOL_SCHEMAS = [
  {
    name: "summarize_text",
    description: "Summarize a large text blob into a concise answer.",
    parameters: {
      type: "object",
      properties: {
        text: { type: "string", description: "The long text to summarise" },
        max_tokens: { type: "integer", default: 300 },
      },
      required: ["text"],
    },
  },
  {
    name: "read_file",
    description: "Read a UTF-8 text file from disk. Returns its full contents.",
    parameters: { type: "object", properties: { path: { type: "string", description: "Absolute or relative path" } }, required: ["path"] },
  },
  {
    name: "list_dir",
    description: "List entries in a directory (non-recursive).",
    parameters: { type: "object", properties: { path: { type: "string" } }, required: ["path"] },
  },
  {
    name: "search",
    description: "Recursively grep a regex in a directory. Returns matching lines with file:line.",
    parameters: { type: "object", properties: { path: { type: "string" }, pattern: { type: "string", description: "JavaScript regex" }, max_results: { type: "integer", default: 200 } }, required: ["path", "pattern"] },
  },
  {
    name: "write_file",
    description: "Create or overwrite a file with the given UTF-8 content. Creates parent directories.",
    parameters: { type: "object", properties: { path: { type: "string" }, content: { type: "string" } }, required: ["path", "content"] },
  },
  {
    name: "edit_file",
    description: "Replace the first occurrence of old_string with new_string in path. old_string must be unique. Set replace_all=true to replace every occurrence.",
    parameters: { type: "object", properties: { path: { type: "string" }, old_string: { type: "string" }, new_string: { type: "string" }, replace_all: { type: "boolean", default: false } }, required: ["path", "old_string", "new_string"] },
  },
  {
    name: "mkdir",
    description: "Create a directory (recursive).",
    parameters: { type: "object", properties: { path: { type: "string" } }, required: ["path"] },
  },
  {
    name: "delete_path",
    description: "Delete a file or directory (recursive).",
    parameters: { type: "object", properties: { path: { type: "string" } }, required: ["path"] },
  },
  {
    name: "bash",
    description: "Run a shell command via /bin/sh. Returns combined stdout+stderr and exit code.",
    parameters: { type: "object", properties: { command: { type: "string" }, cwd: { type: "string", description: "Working directory; defaults to current." }, timeout_ms: { type: "integer", default: 60000 } }, required: ["command"] },
  },
  {
    name: "run_code",
    description: "Execute a snippet in a chosen language. Supported: python, node, bash, sh.",
    parameters: { type: "object", properties: { language: { type: "string", enum: ["python", "node", "bash", "sh"] }, code: { type: "string" }, timeout_ms: { type: "integer", default: 60000 } }, required: ["language", "code"] },
  },
  {
    name: "glob",
    description: "Find files by glob pattern (e.g. \"src/**/*.ts\").",
    parameters: { type: "object", properties: { pattern: { type: "string" }, path: { type: "string", description: "Root dir, default cwd" }, max_results: { type: "integer", default: 200 } }, required: ["pattern"] },
  },
  {
    name: "apply_patch",
    description: "Apply multiple edits to a single file atomically.",
    parameters: { type: "object", properties: { path: { type: "string" }, edits: { type: "array", items: { type: "object", properties: { old_string: { type: "string" }, new_string: { type: "string" }, replace_all: { type: "boolean", default: false } }, required: ["old_string", "new_string"] } } }, required: ["path", "edits"] },
  },
  {
    name: "http_get",
    description: "HTTP GET a URL and return the response body (text). Caps at 200KB.",
    parameters: { type: "object", properties: { url: { type: "string" }, headers: { type: "object" }, timeout_ms: { type: "integer", default: 30000 } }, required: ["url"] },
  },
  {
    name: "git",
    description: "Run a git subcommand in cwd. Refuses destructive actions unless confirm=true.",
    parameters: { type: "object", properties: { args: { type: "array", items: { type: "string" } }, cwd: { type: "string" }, confirm: { type: "boolean", default: false } }, required: ["args"] },
  },
  {
    name: "skill_list",
    description: "List available skills.",
    parameters: { type: "object", properties: {} },
  },
  {
    name: "skill_get",
    description: "Load a skill by name.",
    parameters: { type: "object", properties: { name: { type: "string" } }, required: ["name"] },
  },
];

export function isWriteOrExec(name) { return WRITE_OR_EXEC.has(name); }
export function isReadOnly(name) { return READ_ONLY.has(name); }

function abs(p) { return path.isAbsolute(p) ? p : path.resolve(process.cwd(), p); }

function runProc(cmd, args, { cwd, timeout, input } = {}) {
  return new Promise(resolve => {
    const child = spawn(cmd, args, { cwd: cwd || process.cwd(), env: process.env, stdio: ["pipe", "pipe", "pipe"] });
    let out = "";
    let err = "";
    let killed = false;
    const timer = timeout ? setTimeout(() => { killed = true; child.kill("SIGKILL"); }, timeout) : null;
    child.stdout.on("data", d => { out += d.toString(); });
    child.stderr.on("data", d => { err += d.toString(); });
    child.on("close", (code, signal) => {
      if (timer) clearTimeout(timer);
      resolve({ stdout: out, stderr: err, exit_code: code, signal, timed_out: killed });
    });
    child.on("error", e => {
      if (timer) clearTimeout(timer);
      resolve({ stdout: out, stderr: String(e), exit_code: -1, timed_out: killed });
    });
    if (input != null) child.stdin.write(input);
    child.stdin.end();
  });
}

function formatRun(r) {
  const parts = [];
  parts.push(`exit=${r.exit_code}${r.timed_out ? " (timed out)" : ""}`);
  
  const cap = MAX_OUTPUT;
  const truncate = (s) => (s.length > cap ? s.slice(0, cap) + "\n…[TRUNCATED: Output exceeded token limit. Some data was cut.]" : s);
  
  if (r.stdout) parts.push(`--- stdout ---\n${truncate(r.stdout.trimEnd())}`);
  if (r.stderr) parts.push(`--- stderr ---\n${truncate(r.stderr.trimEnd())}`);
  return parts.join("\n");
}

export async function executeTool(name, args) {
  switch (name) {
    case "read_file": {
      const p = abs(args.path);
      const content = fs.readFileSync(p, "utf8");
      return content.length > MAX_OUTPUT ? content.slice(0, MAX_OUTPUT) + "\n…[TRUNCATED: File too large, only first 200KB shown.]" : content;
    }
    case "list_dir": {
      const p = abs(args.path);
      const entries = fs.readdirSync(p, { withFileTypes: true });
      return entries.map(e => `${e.isDirectory() ? "d" : "f"} ${e.name}`).join("\n");
    }
    case "search": {
      const root = abs(args.path);
      const re = new RegExp(args.pattern);
      const max = args.max_results || 200;
      const out = [];
      const walk = dir => {
        if (out.length >= max) return;
        let items;
        try { items = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
        for (const it of items) {
          if (out.length >= max) return;
          if (it.name.startsWith('.git') || it.name === 'node_modules') continue;
          const full = path.join(dir, it.name);
          if (it.isDirectory()) walk(full);
          else if (it.isFile()) {
            try {
              let text = fs.readFileSync(full, "utf8");
              if (text.length > MAX_OUTPUT) text = text.slice(0, MAX_OUTPUT) + "\n…[TRUNCATED: File too large to search fully.]";
              text.split("\n").forEach((line, i) => {
                if (out.length >= max) return;
                if (re.test(line)) out.push(`${full}:${i+1}: ${line}`);
              });
            } catch {}
          }
        }
      };
      walk(root);
      return out.join("\n") || "(no matches)";
    }
    case "write_file": {
      const p = abs(args.path);
      const existed = fs.existsSync(p);
      fs.mkdirSync(path.dirname(p), { recursive: true });
      fs.writeFileSync(p, args.content, "utf8");
      const lines = (args.content.match(/\n/g)||[]).length + 1;
      return `${existed ? "rewrote" : "created"} ${p} (${lines} lines)`;
    }
    case "edit_file": {
      const p = abs(args.path);
      const orig = fs.readFileSync(p, "utf8");
      let next;
      if (args.replace_all) {
        next = orig.split(args.old_string).join(args.new_string);
        if (next === orig) throw new Error("old_string not found");
      } else {
        const idx = orig.indexOf(args.old_string);
        if (idx === -1) throw new Error("old_string not found");
        if (orig.indexOf(args.old_string, idx+1) !== -1) throw new Error("old_string not unique");
        next = orig.slice(0, idx) + args.new_string + orig.slice(idx + args.old_string.length);
      }
      fs.writeFileSync(p, next, "utf8");
      return `edited ${p}`;
    }
    case "mkdir": {
      const p = abs(args.path);
      fs.mkdirSync(p, { recursive: true });
      return `mkdir ${p}`;
    }
    case "delete_path": {
      const p = abs(args.path);
      fs.rmSync(p, { recursive: true, force: true });
      return `deleted ${p}`;
    }
    case "bash": {
      const sh = { bin: process.env.SHELL || "/bin/sh", flags: ["-c"] };
      const r = await runProc(sh.bin, [...sh.flags, args.command], { cwd: args.cwd ? abs(args.cwd) : process.cwd(), timeout: args.timeout_ms ?? DEFAULT_BASH_TIMEOUT });
      const out = formatRun(r);
      return out.length > MAX_OUTPUT ? out.slice(0, MAX_OUTPUT) + "\n…[truncated]" : out;
    }
    case "run_code": {
      const lang = args.language;
      const tmp = path.join(os.tmpdir(), `ant-${Date.now()}-${Math.random().toString(36).slice(2)}`);
      let file, cmd, cmdArgs;
      if (lang === "python") { file = tmp+".py"; fs.writeFileSync(file, args.code); cmd = "python"; cmdArgs = [file]; }
      else if (lang === "node") { file = tmp+".mjs"; fs.writeFileSync(file, args.code); cmd = "node"; cmdArgs = [file]; }
      else { file = tmp+".sh"; fs.writeFileSync(file, args.code); cmd = "/bin/sh"; cmdArgs = [file]; }
      try {
        const r = await runProc(cmd, cmdArgs, { timeout: args.timeout_ms || 60000 });
        return formatRun(r);
      } finally { try { fs.unlinkSync(file); } catch {} }
    }
    case "glob": {
      const root = abs(args.path || process.cwd());
      const max = args.max_results || 200;
      const re = globToRegex(args.pattern);
      const out = [];
      const walk = dir => {
        if (out.length >= max) return;
        let items;
        try { items = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
        for (const it of items) {
          if (out.length >= max) return;
          if (it.name === ".git" || it.name === "node_modules") continue;
          const full = path.join(dir, it.name);
          if (it.isDirectory()) walk(full);
          else if (it.isFile()) {
            const rel = path.relative(root, full);
            if (re.test(rel)) {
              try { const st = fs.statSync(full); out.push({ path: full, mtime: st.mtimeMs }); } catch {}
            }
          }
        }
      };
      walk(root);
      out.sort((a,b) => b.mtime - a.mtime);
      return out.slice(0, max).map(e=>e.path).join("\n") || "(no matches)";
    }
    case "apply_patch": {
      const p = abs(args.path);
      let text = fs.readFileSync(p, "utf8");
      const edits = Array.isArray(args.edits) ? args.edits : [];
      for (let i = 0; i < edits.length; i++) {
        const e = edits[i];
        if (e.replace_all) {
          if (!text.includes(e.old_string)) throw new Error(`edit ${i}: old_string not found`);
          text = text.split(e.old_string).join(e.new_string);
        } else {
          const idx = text.indexOf(e.old_string);
          if (idx === -1) throw new Error(`edit ${i}: old_string not found`);
          if (text.indexOf(e.old_string, idx+1) !== -1) throw new Error(`edit ${i}: old_string not unique`);
          text = text.slice(0, idx) + e.new_string + text.slice(idx + e.old_string.length);
        }
      }
      fs.writeFileSync(p, text, "utf8");
      return `applied ${edits.length} edit${edits.length===1?"":"s"} to ${p}`;
    }
    case "http_get": {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), args.timeout_ms || 30000);
      try {
        const res = await fetch(args.url, { headers: args.headers || {}, signal: ctrl.signal });
        const txt = await res.text();
        const cap = 200_000;
        const body = txt.length > cap ? txt.slice(0, cap) + "\n…[TRUNCATED: Response too large, only first 200KB shown.]" : txt;
        return `HTTP ${res.status} ${res.statusText}\ncontent-type: ${res.headers.get("content-type")||""}\n\n${body}`;
      } finally { clearTimeout(t); }
    }
    case "git": {
      const argv = Array.isArray(args.args) ? args.args : [];
      const sub = argv[0] || "";
      const destructive = ["push","reset","clean","branch","checkout"].some(op=>{
        if (op==="push") return sub==="push";
        if (op==="reset") return sub==="reset" && argv.includes("--hard");
        if (op==="clean") return sub==="clean" && argv.some(a=>/-.*f/.test(a));
        if (op==="branch") return sub==="branch" && argv.includes("-D");
        if (op==="checkout") return sub==="checkout" && (argv.includes(".")||argv.includes("--"));
        return false;
      });
      if (destructive && !args.confirm) return `refused: destructive git ${sub} requires confirm=true`;
      const r = await runProc("git", argv, { cwd: args.cwd ? abs(args.cwd) : process.cwd(), timeout: args.timeout_ms ?? DEFAULT_GIT_TIMEOUT });
      const out = formatRun(r);
      return out.length > MAX_OUTPUT ? out.slice(0, MAX_OUTPUT) + "\n…[TRUNCATED: Output exceeded token limit. Some data was cut.]" : out;
    }
    case "skill_list": {
      const dir = path.join(os.homedir(), ".ant", "skills");
      if (!fs.existsSync(dir)) return "(no skills directory)";
      const files = fs.readdirSync(dir).filter(f=>f.endsWith('.md'));
      if (!files.length) return "(no skills)";
      return files.map(f=>f.replace(/\.md$/,'')).join("\n");
    }
    case "skill_get": {
      const dir = path.join(os.homedir(), ".ant", "skills");
      const f = path.join(dir, args.name + ".md");
      if (!fs.existsSync(f)) throw new Error(`skill not found: ${args.name}`);
      return fs.readFileSync(f, "utf8");
    }
    case "summarize_text": {
      const prompt = [
        { role: "system", content: "Summarize the following text concisely (max tokens: " + (args.max_tokens||300) + ")." },
        { role: "user", content: args.text }
      ];
      const cfg = { model: "gpt-4o-mini", provider: "openai", maxTokens: args.max_tokens || 300 };
      const resp = await chat(cfg, prompt);
      return resp.content?.trim() || "";
    }
    default:
      throw new Error(`unknown tool: ${name}`);
  }
}

function globToRegex(glob) {
  let re = "^";
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === "*") {
      if (glob[i+1] === "*") { re += ".*"; i++; if (glob[i+1] === "/") i++; }
      else re += "[^/]*";
    } else if (c === "?") re += "[^/]";
    else if ("./+()|^$".includes(c)) re += "\\" + c;
    else re += c;
  }
  re += "$";
  return new RegExp(re);
}

export function summarizeArgs(name, args) {
  if (name === "write_file") {
    const preview = (args.content || "").length > 200 ? `${args.content.slice(0,200)}…` : args.content;
    return `${args.path} (${Buffer.byteLength(preview, "utf8")} bytes)`;
  }
  if (name === "edit_file") {
    const oldStr = (args.old_string||"").slice(0,30);
    const newStr = (args.new_string||"").slice(0,30);
    return `${args.path}  - "${oldStr}…" → "${newStr}…"${args.replace_all?"  [all]":""}`;
  }
  if (name === "apply_patch") return `${args.path}  ${(args.edits||[]).length} edit${(args.edits||[]).length===1?"":"s"}`;
  if (name === "bash") return args.command;
  if (name === "run_code") {
    const preview = (args.code||"").length > 120 ? `${args.code.slice(0,120)}…` : args.code;
    return `${args.language}: ${preview.replace(/\n/g,"⏎").slice(0,100)}`;
  }
  if (name === "git") {
    const list = (args.args||[]).slice(0,5).join(" ");
    return `git ${list}${(args.args||[]).length>5?" …":""}`;
  }
  if (name === "delete_path"||name === "mkdir"||name === "glob"||name === "http_get"||name === "skill_get") return args.path || args.url || args.name || "";
  return JSON.stringify(args);
}
