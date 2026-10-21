import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const DIR = path.join(os.homedir(), ".ant");
const FILE = path.join(DIR, "config.json");

const DEFAULTS = {
  provider: "openrouter",
  model: "deepseek/deepseek-chat-v3.1:free",
  keys: {},
  baseUrl: "",
  systemPrompt: "", // kept empty unless user customizes; runtime prompt is built in index.js
  maxSteps: 25,
  maxTokens: 4096,
};

export function load() {
  try {
    const raw = fs.readFileSync(FILE, "utf8");
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULTS };
  }
}

export function save(cfg) {
  fs.mkdirSync(DIR, { recursive: true, mode: 0o700 });
  fs.writeFileSync(FILE, JSON.stringify(cfg, null, 2), { mode: 0o600 });
}

export function setKey(provider, key) {
  if (!["openrouter", "anthropic", "openai", "generic", "mistral", "codestral", "google", "deepseek", "bonsai"].includes(provider)) throw new Error(`Unsupported provider ${provider}`);
  const cfg = load();
  cfg.keys[provider] = key;
  save(cfg);
}

export function getKey(provider) {
  const cfg = load();
  return cfg.keys[provider] || process.env[envName(provider)] || "";
}

export function hasKey(cfg, provider) {
  return !!(cfg.keys?.[provider] || process.env[envName(provider)]);
}

export function envName(provider) {
  return (
    {
      openrouter: "OPENROUTER_API_KEY",
      anthropic: "ANTHROPIC_API_KEY",
      openai: "OPENAI_API_KEY",
      mistral: "MISTRAL_API_KEY",
      codestral: "CODESTRAL_API_KEY",
      deepseek: "DEEPSEEK_API_KEY",
      google: "GOOGLE_API_KEY",
      generic: "ANT_API_KEY",
    }[provider] || "ANT_API_KEY"
  );
}

export const CONFIG_PATH = FILE;

export const MODES = {
  default: "default",
  yolo: "yolo",
  plan: "plan",
  acceptEdits: "acceptEdits"
};

export function nextMode(current) {
  const modes = ["default", "yolo", "plan", "acceptEdits"];
  const currentIndex = modes.indexOf(current);
  const nextIndex = (currentIndex + 1) % modes.length;
  return modes[nextIndex];
}
