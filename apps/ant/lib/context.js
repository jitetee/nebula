// Token estimation + history trimming. Keeps prompts under provider limits
// without making any extra API calls.

// Per-model context windows (input tokens). Used to compute the working budget.
const MODEL_LIMITS = [
  [/claude-(sonnet|opus|haiku)-4/i, 200_000],
  [/claude-3/i, 200_000],
  [/gpt-5/i, 200_000],
  [/gpt-4\.1/i, 1_000_000],
  [/gpt-4o/i, 128_000],
  [/o4-mini|o3/i, 200_000],
  [/gemini-1\.5/i, 1_000_000],
  [/gemini/i, 128_000],
  [/deepseek/i, 128_000],
  [/llama-3\.3/i, 128_000],
  [/qwen3/i, 128_000],
  [/glm-4\.5/i, 128_000],
  [/gpt-oss/i, 32_000],
  [/gemma/i, 8_000],
  [/nemotron/i, 32_000],
  [/mistral|codestral/i, 32_000],
];

export function modelLimit(model) {
  if (!model) return 32_000;
  for (const [re, n] of MODEL_LIMITS) if (re.test(model)) return n;
  return 32_000; // conservative default for unknown models
}

// 75% of the limit, leaving headroom for the model's response and tool schemas.
export function workingBudget(model) {
  const lim = modelLimit(model);
  return Math.max(4096, Math.floor(lim * 0.75));
}

// Cheap estimator: chars/4 ≈ tokens. Off by ±15% but adequate for budget gating.
export function estimateTokens(text) {
  if (!text) return 0;
  if (typeof text !== "string") text = JSON.stringify(text);
  return Math.ceil(text.length / 4);
}

export function estimateMessageTokens(m) {
  let n = 4; // role/structural overhead
  if (m.content) n += estimateTokens(m.content);
  if (m.tool_calls) {
    for (const tc of m.tool_calls) {
      n += estimateTokens(tc.name || "") + estimateTokens(JSON.stringify(tc.args || {}));
    }
  }
  if (m.tool_call_id) n += estimateTokens(m.tool_call_id);
  if (m.name) n += estimateTokens(m.name);
  return n;
}

export function estimateHistoryTokens(history, systemPrompt = "") {
  let n = estimateTokens(systemPrompt);
  for (const m of history) n += estimateMessageTokens(m);
  return n;
}

// Truncate a single tool-result message in-place when its content is huge.
// Keeps head/tail so the model still sees the shape of the output.
const PER_TOOL_CHAR_CAP = 8_000; // ~2000 tokens per tool result max in history
export function capToolResult(msg, cap = PER_TOOL_CHAR_CAP) {
  if (msg.role !== "tool") return msg;
  const c = typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content);
  if (c.length <= cap) return msg;
  const head = c.slice(0, Math.floor(cap * 0.7));
  const tail = c.slice(-Math.floor(cap * 0.2));
  const dropped = c.length - head.length - tail.length;
  return {
    ...msg,
    content: `${head}\n…[${dropped} chars truncated to fit context]…\n${tail}`,
  };
}

// Trim history so total tokens (including system prompt) stay under budget.
// Strategy:
//   1. Cap any oversized tool results.
//   2. If still over, drop oldest message pairs (user+assistant), but never
//      the most recent user turn or any pending tool_use/tool_result chain.
// Returns { history, trimmed, beforeTokens, afterTokens }.
export function trimHistory(history, systemPrompt, budget) {
  const before = estimateHistoryTokens(history, systemPrompt);
  let work = history.map((m) => capToolResult(m));
  let after = estimateHistoryTokens(work, systemPrompt);
  let dropped = 0;

  // Drop from the front until under budget. Keep at least the last 4 messages
  // (typically: latest user → assistant → tool_result → assistant) intact so
  // tool_use/tool_result IDs stay paired.
  const minKeep = 4;
  while (after > budget && work.length > minKeep) {
    // Drop messages until we land on a clean boundary (next user message).
    work.shift();
    dropped++;
    while (work.length > minKeep && work[0] && work[0].role !== "user") {
      work.shift();
      dropped++;
    }
    after = estimateHistoryTokens(work, systemPrompt);
  }

  return {
    history: work,
    trimmed: dropped,
    beforeTokens: before,
    afterTokens: after,
    overBudget: after > budget,
  };
}

// Aggressive trim used as recovery when the provider rejects the request
// with a context-length error. Halves the budget repeatedly.
export function emergencyTrim(history, systemPrompt, model) {
  let budget = Math.floor(workingBudget(model) / 2);
  let result = trimHistory(history, systemPrompt, budget);
  while (result.overBudget && budget > 4096) {
    budget = Math.floor(budget / 2);
    result = trimHistory(result.history, systemPrompt, budget);
  }
  return result;
}

export function isContextLengthError(err) {
  const m = String(err?.message || err || "").toLowerCase();
  return (
    m.includes("maximum context length") ||
    m.includes("context_length_exceeded") ||
    m.includes("too many tokens") ||
    m.includes("prompt is too long") ||
    (m.includes("400") && m.includes("token"))
  );
}
