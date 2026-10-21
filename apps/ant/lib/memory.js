// Memory: per-project ANT.md (cwd) + global ~/.ant/MEMORY.md
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const HOME_DIR = path.join(os.homedir(), ".ant");
const HOME_FILE = path.join(HOME_DIR, "MEMORY.md");

export function projectMemoryPath(cwd = process.cwd()) {
  return path.join(cwd, "ANT.md");
}

export function globalMemoryPath() {
  return HOME_FILE;
}

function readSafe(p) {
  try { return fs.readFileSync(p, "utf8"); } catch { return ""; }
}

export function loadAllMemory(cwd = process.cwd()) {
  const proj = readSafe(projectMemoryPath(cwd));
  const glob = readSafe(HOME_FILE);
  const parts = [];
  if (glob.trim()) parts.push(`# Global memory (~/.ant/MEMORY.md)\n${glob.trim()}`);
  if (proj.trim()) parts.push(`# Project memory (./ANT.md)\n${proj.trim()}`);
  return parts.join("\n\n");
}

export function appendGlobal(line) {
  fs.mkdirSync(HOME_DIR, { recursive: true, mode: 0o700 });
  const cur = readSafe(HOME_FILE);
  const stamp = new Date().toISOString().slice(0, 10);
  const next = (cur ? cur.trimEnd() + "\n" : "") + `- (${stamp}) ${line}\n`;
  fs.writeFileSync(HOME_FILE, next, { mode: 0o600 });
}

export function appendProject(cwd, line) {
  const p = projectMemoryPath(cwd);
  const cur = readSafe(p);
  const stamp = new Date().toISOString().slice(0, 10);
  const next = (cur ? cur.trimEnd() + "\n" : "# Project memory for ant\n\n") + `- (${stamp}) ${line}\n`;
  fs.writeFileSync(p, next);
}

export function removeContaining(scope, needle, cwd = process.cwd()) {
  const p = scope === "project" ? projectMemoryPath(cwd) : HOME_FILE;
  const cur = readSafe(p);
  if (!cur) return 0;
  const before = cur.split("\n");
  const after = before.filter((ln) => !ln.toLowerCase().includes(String(needle).toLowerCase()));
  fs.writeFileSync(p, after.join("\n"));
  return before.length - after.length;
}
