import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const DIR = path.join(os.homedir(), ".ant", "sessions");

function ensureDir() {
  fs.mkdirSync(DIR, { recursive: true, mode: 0o700 });
}

export function newSessionId() {
  return `ant-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function sessionPath(id) {
  return path.join(DIR, `${id}.json`);
}

export function saveSession(id, data) {
  ensureDir();
  const payload = {
    id,
    cwd: data.cwd ?? process.cwd(),
    provider: data.provider ?? "",
    model: data.model ?? "",
    history: data.history ?? [],
    firstMessage: data.firstMessage ?? "",
    createdAt: data.createdAt ?? Date.now(),
    updatedAt: Date.now(),
  };
  fs.writeFileSync(sessionPath(id), JSON.stringify(payload, null, 2), { mode: 0o600 });
}

export function loadSession(id) {
  try {
    return JSON.parse(fs.readFileSync(sessionPath(id), "utf8"));
  } catch {
    return null;
  }
}

export function listSessions(limit = 5) {
  ensureDir();
  let files;
  try {
    files = fs.readdirSync(DIR).filter((f) => f.endsWith(".json"));
  } catch {
    return [];
  }
  const items = [];
  for (const f of files) {
    try {
      const raw = fs.readFileSync(path.join(DIR, f), "utf8");
      const j = JSON.parse(raw);
      items.push(j);
    } catch {}
  }
  items.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  return items.slice(0, limit);
}

export function latestSessionId() {
  const list = listSessions(1);
  return list[0]?.id || null;
}

export function relTime(ts) {
  if (!ts) return "";
  const diff = Math.max(0, Date.now() - ts);
  const s = Math.round(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}
