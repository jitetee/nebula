"""Config, sessions, memory and model lists. Everything lives in ~/.ant (same format as before)."""
import json
import os
import random
import string
import time

DIR = os.path.join(os.path.expanduser("~"), ".ant")
FILE = os.path.join(DIR, "config.json")
SESSIONS = os.path.join(DIR, "sessions")
SKILLS = os.path.join(DIR, "skills")
CONFIG_PATH = FILE

PROVIDERS = ["openrouter", "anthropic", "openai", "generic", "mistral", "codestral", "google", "deepseek", "bonsai"]
ENV = {"openrouter": "OPENROUTER_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
       "mistral": "MISTRAL_API_KEY", "codestral": "CODESTRAL_API_KEY", "deepseek": "DEEPSEEK_API_KEY",
       "google": "GOOGLE_API_KEY", "bonsai": "BONSAI_API_KEY", "generic": "ANT_API_KEY"}

DEFAULTS = {"provider": "openrouter", "model": "openrouter/free", "keys": {}, "baseUrl": "",
            "systemPrompt": "", "maxSteps": 25, "maxTokens": 4096}


def env_name(p):
    return ENV.get(p, "ANT_API_KEY")


def load():
    cfg = dict(DEFAULTS, keys={})
    try:
        with open(FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update(data)
    except (OSError, ValueError):
        pass
    if not isinstance(cfg.get("keys"), dict):
        cfg["keys"] = {}
    return cfg


def save(cfg):
    os.makedirs(DIR, mode=0o700, exist_ok=True)
    tmp = FILE + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, FILE)
    os.chmod(FILE, 0o600)


def set_key(provider, key):
    if provider not in PROVIDERS:
        raise ValueError("Unsupported provider %s" % provider)
    cfg = load()
    cfg["keys"][provider] = key
    save(cfg)


def get_key(cfg, provider):
    return (cfg.get("keys") or {}).get(provider) or os.environ.get(env_name(provider), "")


def has_key(cfg, provider):
    return bool(get_key(cfg, provider))


MODES = ["default", "yolo", "plan", "acceptEdits"]


# ---------------- sessions ----------------

def new_session_id():
    r = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    return "ant-%d-%s" % (int(time.time() * 1000), r)


def session_path(sid):
    return os.path.join(SESSIONS, "%s.json" % os.path.basename(sid))


def save_session(sid, data):
    os.makedirs(SESSIONS, mode=0o700, exist_ok=True)
    payload = {"id": sid, "cwd": data.get("cwd") or os.getcwd(), "provider": data.get("provider", ""),
               "model": data.get("model", ""), "history": data.get("history", []),
               "firstMessage": data.get("firstMessage", ""), "createdAt": data.get("createdAt") or int(time.time() * 1000),
               "updatedAt": int(time.time() * 1000)}
    fd = os.open(session_path(sid), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_session(sid):
    try:
        with open(session_path(sid), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def list_sessions(limit=5):
    items = []
    try:
        names = [n for n in os.listdir(SESSIONS) if n.endswith(".json")]
    except OSError:
        return []
    for n in names:
        try:
            with open(os.path.join(SESSIONS, n), encoding="utf-8") as f:
                items.append(json.load(f))
        except (OSError, ValueError):
            pass
    items.sort(key=lambda j: j.get("updatedAt") or 0, reverse=True)
    return items[:limit]


def latest_session_id():
    l = list_sessions(1)
    return l[0].get("id") if l else None


def rel_time(ts):
    if not ts:
        return ""
    s = round(max(0, time.time() * 1000 - ts) / 1000)
    if s < 60:
        return "%ds ago" % s
    m = round(s / 60)
    if m < 60:
        return "%dm ago" % m
    h = round(m / 60)
    if h < 24:
        return "%dh ago" % h
    return "%dd ago" % round(h / 24)


# ---------------- models ----------------

def _m(i, n=""):
    return {"id": i, "note": n}


MODELS = {
    "openrouter": [_m("openrouter/free", "default · free"), _m("openai/gpt-oss-120b:free", "free · strong tool use"),
                   _m("openai/gpt-oss-20b:free", "free · faster"), _m("qwen/qwen3-coder:free", "free · coder"),
                   _m("qwen/qwen3-next-80b-a3b-instruct:free", "free · 80B"), _m("z-ai/glm-4.5-air:free", "free"),
                   _m("meta-llama/llama-3.3-70b-instruct:free", "free · 70B"), _m("nvidia/nemotron-nano-9b-v2:free", "free · small"),
                   _m("google/gemma-3-27b-it:free", "free · 27B"), _m("anthropic/claude-sonnet-4.5", "paid · Anthropic via OR"),
                   _m("openai/gpt-4o-mini", "paid · cheap"), _m("openai/gpt-4o", "paid")],
    "anthropic": [_m("claude-sonnet-4-5", "default · Sonnet 4.5"), _m("claude-sonnet-4-6", "Sonnet 4.6"),
                  _m("claude-haiku-4-5", "Haiku 4.5 · fast"), _m("claude-opus-4-7", "Opus 4.7 · most capable")],
    "openai": [_m("gpt-4o-mini", "default · cheap"), _m("gpt-4o"), _m("gpt-4.1"), _m("gpt-4.1-mini"), _m("gpt-5"), _m("o4-mini", "reasoning")],
    "generic": [_m("deepseek-chat", "DeepSeek native API"), _m("gpt-4o-mini")],
    "mistral": [_m("mistral-tiny", "Tiny model"), _m("mistral-small", "Small model"), _m("mistral-medium", "Medium model")],
    "codestral": [_m("codestral-latest", "Latest model")],
    "google": [_m("gemini-1.5-pro", "Pro model"), _m("gemini-1.5-flash", "Flash model")],
    "deepseek": [_m("deepseek-chat", "Chat model"), _m("deepseek-coder", "Coder model")],
}


def list_for(provider):
    return MODELS.get(provider, [])


def default_model(provider):
    if provider == "openrouter":
        return "openrouter/free"
    l = MODELS.get(provider)
    return l[0]["id"] if l else ""


# ---------------- memory ----------------

def load_memory(cwd=None):
    def rd(p):
        try:
            with open(p, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""
    g = rd(os.path.join(DIR, "MEMORY.md")).strip()
    p = rd(os.path.join(cwd or os.getcwd(), "ANT.md")).strip()
    parts = []
    if g:
        parts.append("# Global memory (~/.ant/MEMORY.md)\n" + g)
    if p:
        parts.append("# Project memory (./ANT.md)\n" + p)
    return "\n\n".join(parts)
