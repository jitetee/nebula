// Curated model lists per provider, used by the /model and /provider pickers.
// Add/remove entries here — index.js auto-discovers them.

export const MODELS = {
  openrouter: [
    { id: "openrouter/free", provider: "openrouter", note: "default · free" },
    { id: "openai/gpt-oss-120b:free", provider: "openai", note: "default · free · strong tool use" },
    { id: "openai/gpt-oss-20b:free", provider: "openai", note: "free · faster" },
    { id: "qwen/qwen3-coder:free", provider: "qwen", note: "free · coder" },
    { id: "qwen/qwen3-next-80b-a3b-instruct:free", provider: "qwen", note: "free · 80B" },
    { id: "z-ai/glm-4.5-air:free", provider: "z-ai", note: "free" },
    { id: "meta-llama/llama-3.3-70b-instruct:free", provider: "meta-llama", note: "free · 70B" },
    { id: "nvidia/nemotron-nano-9b-v2:free", provider: "nvidia", note: "free · small" },
    { id: "google/gemma-3-27b-it:free", provider: "google", note: "free · 27B" },
    { id: "anthropic/claude-sonnet-4.5", provider: "anthropic", note: "paid · Anthropic via OR" },
    { id: "openai/gpt-4o-mini", provider: "openai", note: "paid · cheap" },
    { id: "openai/gpt-4o", provider: "openai", note: "paid" },
  ],
  anthropic: [
    { id: "claude-sonnet-4-5", provider: "anthropic", note: "default · Sonnet 4.5" },
    { id: "claude-sonnet-4-6", provider: "anthropic", note: "Sonnet 4.6" },
    { id: "claude-haiku-4-5", provider: "anthropic", note: "Haiku 4.5 · fast" },
    { id: "claude-opus-4-7", provider: "anthropic", note: "Opus 4.7 · most capable" },
  ],
  openai: [
    { id: "gpt-4o-mini", provider: "openai", note: "default · cheap" },
    { id: "gpt-4o", provider: "openai", note: "" },
    { id: "gpt-4.1", provider: "openai", note: "" },
    { id: "gpt-4.1-mini", provider: "openai", note: "" },
    { id: "gpt-5", provider: "openai", note: "" },
    { id: "o4-mini", provider: "openai", note: "reasoning" },
  ],
  generic: [
    { id: "deepseek-chat", provider: "deepseek", note: "DeepSeek native API" },
    { id: "gpt-4o-mini", provider: "openai", note: "" },
  ],
  mistral: [
    { id: "mistral-tiny", provider: "mistral", note: "Tiny model" },
    { id: "mistral-small", provider: "mistral", note: "Small model" },
    { id: "mistral-medium", provider: "mistral", note: "Medium model" },
  ],
  codestral: [
    { id: "codestral-latest", provider: "codestral", note: "Latest model" },
  ],
  google: [
    { id: "gemini-1.5-pro", provider: "google", note: "Pro model" },
    { id: "gemini-1.5-flash", provider: "google", note: "Flash model" },
  ],
  deepseek: [
    { id: "deepseek-chat", provider: "deepseek", note: "Chat model" },
    { id: "deepseek-coder", provider: "deepseek", note: "Coder model" },
  ],
};

export function defaultModel(provider) {
  const list = MODELS[provider];
  if (provider === "openrouter") {
    return "openrouter/free";
  }
  return list && list[0] ? list[0].id : "";
}

export function listFor(provider) {
  return MODELS[provider] || [];
}
