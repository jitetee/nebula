// Unified chat-completion abstraction.
// All providers normalize to OpenAI-style {role, content, tool_calls} messages internally.
// Anthropic is converted at the boundary.

import { TOOL_SCHEMAS } from "./tools.js";

// Retry configuration
const MAX_RETRIES = 5;
const BASE_DELAY_MS = 500; // initial backoff delay

async function sleepAbortable(ms) {
  const start = Date.now();
  while (Date.now() - start < ms) {
    if (globalThis.__ANT_ABORT) throw new Error("Aborted by user");
    await new Promise(r => setTimeout(r, Math.min(100, ms - (Date.now() - start))));
  }
}

function openaiTools() {
  return TOOL_SCHEMAS.map((t) => ({
    type: "function",
    function: { name: t.name, description: t.description, parameters: t.parameters },
  }));
}

function anthropicTools() {
  return TOOL_SCHEMAS.map((t) => ({
    name: t.name,
    description: t.description,
    input_schema: t.parameters,
  }));
}

function parseRetryAfter(headers) {
  const ra = headers.get("retry-after");
  if (ra) {
    const n = Number(ra);
    if (Number.isFinite(n)) return Math.max(0, n * 1000);
    const t = Date.parse(ra);
    if (!Number.isNaN(t)) return Math.max(0, t - Date.now());
  }
  const reset = headers.get("x-ratelimit-reset") || headers.get("x-ratelimit-reset-requests") || headers.get("x-ratelimit-reset-tokens");
  if (reset) {
    const n = Number(reset);
    if (Number.isFinite(n)) {
      const ms = n > 1e10 ? n - Date.now() : n > 1e9 ? n * 1000 - Date.now() : n * 1000;
      return Math.max(0, ms);
    }
  }
  return null;
}

function isNetworkError(e) {
  const code = e?.cause?.code || e?.code || "";
  if (["ECONNRESET", "ETIMEDOUT", "ECONNREFUSED", "EAI_AGAIN", "ENETUNREACH", "EPIPE", "UND_ERR_SOCKET"].includes(code)) return true;
  const m = String(e?.message || "").toLowerCase();
  return m.includes("fetch failed") || m.includes("network") || m.includes("socket hang up");
}

async function postJSON(url, headers, body) {
  let attempt = 0;
  let wait = BASE_DELAY_MS;
  const MAX_WAIT = 60_000;
  while (attempt <= MAX_RETRIES) {
    if (globalThis.__ANT_ABORT) throw new Error("Aborted by user");
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify(body),
      });
      const text = await res.text();
      if (!res.ok) {
        let parsed;
        try { parsed = JSON.parse(text); } catch {}
        const apiMsg = parsed?.error?.metadata?.raw || parsed?.error?.message || parsed?.message;
        if (res.status === 404) {
          throw new Error(`model not found: ${apiMsg || text.slice(0, 200)} — try /model to pick another`);
        }
        if (res.status === 401 || res.status === 403) {
          throw new Error(`auth failed: ${apiMsg || "check your API key with /key"}`);
        }
        // Retryable: 429 (rate limit), 408, 425, 5xx
        if (res.status === 429 || res.status === 408 || res.status === 425 || (res.status >= 500 && res.status < 600)) {
          attempt++;
          if (attempt > MAX_RETRIES) {
            throw new Error(`HTTP ${res.status} after ${MAX_RETRIES} retries: ${apiMsg || text.slice(0, 200)}`);
          }
          const retryAfter = parseRetryAfter(res.headers);
          const delay = Math.min(MAX_WAIT, retryAfter ?? wait);
          const reason = res.status === 429 ? "rate limited" : `HTTP ${res.status}`;
          process.stderr.write(`\n  ⟳ ${reason} — retry ${attempt}/${MAX_RETRIES} in ${Math.round(delay/1000)}s\n`);
          await sleepAbortable(delay);
          wait = Math.min(wait * 2 + Math.floor(Math.random() * 500), MAX_WAIT);
          continue;
        }
        throw new Error(`HTTP ${res.status}: ${apiMsg || text.slice(0, 400)}`);
      }
      try { return JSON.parse(text); } catch { return text; }
    } catch (e) {
      if (e.message === "Aborted by user") throw e;
      if (!isNetworkError(e) && !/HTTP \d+/.test(e.message)) throw e;
      if (attempt >= MAX_RETRIES) throw e;
      attempt++;
      const delay = Math.min(MAX_WAIT, wait);
      process.stderr.write(`\n  ⟳ network error — retry ${attempt}/${MAX_RETRIES} in ${Math.round(delay/1000)}s\n`);
      await sleepAbortable(delay);
      wait = Math.min(wait * 2 + Math.floor(Math.random() * 500), MAX_WAIT);
    }
  }
  throw new Error(`Failed after ${MAX_RETRIES} retries`);
}

// ---------- OpenAI-compatible (OpenRouter, OpenAI, generic) ----------

function openaiCompatBase(provider, baseUrl) {
  if (provider === "openrouter") return "https://openrouter.ai/api/v1";
  if (provider === "openai") return "https://api.openai.com/v1";
  if (provider === "mistral") return "https://api.mistral.ai/v1";
  if (provider === "codestral") return "https://codestral.mistral.ai/v1";
  if (provider === "deepseek") return "https://api.deepseek.com/v1";
  if (provider === "google") return "https://generativelanguage.googleapis.com/v1beta/openai";
  if (provider === "bonsai") return "https://api.trybonsai.com/v1";
  return baseUrl || ""; // generic
}

async function callOpenAICompat({ provider, baseUrl, key, model, messages, systemPrompt, maxTokens }) {
  const base = openaiCompatBase(provider, baseUrl);
  if (!base) throw new Error("No base URL configured for generic provider. Use /baseurl <url>.");
  const headers = { Authorization: `Bearer ${key}` };
  if (provider === "openrouter") {
    headers["HTTP-Referer"] = "https://github.com/ant-cli";
    headers["X-Title"] = "Ant CLI";
  }
  const oaMessages = [];
  if (systemPrompt) oaMessages.push({ role: "system", content: systemPrompt });
  for (const m of messages) {
    if (m.role === "assistant") {
      const out = { role: "assistant", content: m.content || "" };
      if (m.tool_calls && m.tool_calls.length) {
        out.tool_calls = m.tool_calls.map((tc) => ({
          id: tc.id,
          type: "function",
          function: {
            name: tc.name,
            arguments: typeof tc.args === "string" ? tc.args : JSON.stringify(tc.args || {}),
          },
        }));
      }
      oaMessages.push(out);
    } else if (m.role === "tool") {
      oaMessages.push({
        role: "tool",
        tool_call_id: m.tool_call_id,
        content: typeof m.content === "string" ? m.content : JSON.stringify(m.content),
      });
    } else {
      oaMessages.push({ role: m.role, content: m.content || "" });
    }
  }

  const body = {
    model,
    messages: oaMessages,
    tools: openaiTools(),
    tool_choice: "auto",
  };
  if (maxTokens) body.max_tokens = maxTokens;
  else if (provider === "openrouter") body.max_tokens = 2048;
  const data = await postJSON(`${base}/chat/completions`, headers, body);
  const choice = data.choices?.[0];
  if (!choice) throw new Error(`Empty response: ${JSON.stringify(data).slice(0, 400)}`);
  const m = choice.message || {};
  return {
    role: "assistant",
    content: m.content || "",
    tool_calls: (m.tool_calls || []).map((tc) => ({
      id: tc.id,
      name: tc.function?.name,
      args: safeJSON(tc.function?.arguments),
    })),
    finish_reason: choice.finish_reason,
    usage: data.usage || {},
    raw: m,
  };
}

function safeJSON(s) {
  if (s == null) return {};
  if (typeof s === "object") return s;
  try {
    return JSON.parse(s);
  } catch {
    return {};
  }
}

// ---------- Anthropic ----------

function toAnthropic(messages, systemPrompt) {
  // Convert OA-style {role, content, tool_calls, tool_call_id, name} into Anthropic content blocks.
  const out = [];
  for (const m of messages) {
    if (m.role === "system") continue; // handled separately
    if (m.role === "user") {
      out.push({ role: "user", content: [{ type: "text", text: m.content || "" }] });
    } else if (m.role === "assistant") {
      const blocks = [];
      if (m.content) blocks.push({ type: "text", text: m.content });
      for (const tc of m.tool_calls || []) {
        blocks.push({ type: "tool_use", id: tc.id, name: tc.name, input: tc.args || {} });
      }
      out.push({ role: "assistant", content: blocks });
    } else if (m.role === "tool") {
      // Anthropic groups tool results in a user message
      const last = out[out.length - 1];
      const block = {
        type: "tool_result",
        tool_use_id: m.tool_call_id,
        content: m.content || "",
        is_error: !!m.is_error,
      };
      if (last && last.role === "user" && Array.isArray(last.content) && last.content.every((b) => b.type === "tool_result")) {
        last.content.push(block);
      } else {
        out.push({ role: "user", content: [block] });
      }
    }
  }
  return out;
}

async function callAnthropic({ key, model, messages, systemPrompt }) {
  const headers = {
    "x-api-key": key,
    "anthropic-version": "2023-06-01",
  };
  const body = {
    model,
    max_tokens: 4096,
    system: systemPrompt || undefined,
    tools: anthropicTools(),
    messages: toAnthropic(messages, systemPrompt),
  };
  const data = await postJSON("https://api.anthropic.com/v1/messages", headers, body);
  let text = "";
  const tool_calls = [];
  for (const b of data.content || []) {
    if (b.type === "text") text += b.text;
    else if (b.type === "tool_use")
      tool_calls.push({ id: b.id, name: b.name, args: b.input || {} });
  }
  // Anthropic usage may be in data.usage
  const usage = data.usage || {};
  // Ensure total_tokens is present for consistent reporting
  if (usage.input_tokens != null && usage.output_tokens != null) {
    usage.total_tokens = (usage.input_tokens || 0) + (usage.output_tokens || 0);
  }
  return {
    role: "assistant",
    content: text,
    tool_calls,
    finish_reason: data.stop_reason,
    usage,
    raw: data,
  };
}

// ---------- Dispatch ----------

export async function chat(cfg, messages) {
  const provider = cfg.provider;
  const key = (cfg.keys && cfg.keys[provider]) || process.env[envFor(provider)] || "";
  if (!key) throw new Error(`Missing API key for ${provider}. Use /key ${provider} <KEY>.`);
  const args = {
    provider,
    baseUrl: cfg.baseUrl,
    key,
    model: cfg.model,
    messages,
    systemPrompt: cfg.systemPrompt,
    maxTokens: cfg.maxTokens,
  };
  if (provider === "anthropic") return callAnthropic(args);
  return callOpenAICompat(args);
}

function envFor(p) {
  return (
    {
      openrouter: "OPENROUTER_API_KEY",
      anthropic: "ANTHROPIC_API_KEY",
      openai: "OPENAI_API_KEY",
      mistral: "MISTRAL_API_KEY",
      codestral: "CODESTRAL_API_KEY",
      deepseek: "DEEPSEEK_API_KEY",
      google: "GOOGLE_API_KEY",
      bonsai: "BONSAI_API_KEY",
      generic: "ANT_API_KEY",
    }[p] || "ANT_API_KEY"
  );
}

export const PROVIDERS = ["openrouter", "anthropic", "openai", "generic", "mistral", "codestral", "google", "deepseek", "bonsai"];
