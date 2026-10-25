"""Chat providers: OpenAI-compatible (most of them) and Anthropic. urllib only, retry with backoff."""
import json
import random
import socket
import sys
import time
import urllib.error
import urllib.request

from .store import get_key, PROVIDERS
from .tools import TOOL_SCHEMAS

MAX_RETRIES = 5
BASE_DELAY = 0.5
MAX_WAIT = 60

BASES = {"openrouter": "https://openrouter.ai/api/v1", "openai": "https://api.openai.com/v1",
         "mistral": "https://api.mistral.ai/v1", "codestral": "https://codestral.mistral.ai/v1",
         "deepseek": "https://api.deepseek.com/v1", "google": "https://generativelanguage.googleapis.com/v1beta/openai",
         "bonsai": "https://api.trybonsai.com/v1"}


class ProviderError(Exception):
    pass


def _retry_after(headers):
    ra = headers.get("retry-after")
    if ra:
        try:
            return max(0.0, float(ra))
        except ValueError:
            pass
    return None


def _post(url, headers, body):
    attempt, wait = 0, BASE_DELAY
    data = json.dumps(body).encode()
    hdr = dict({"Content-Type": "application/json"}, **headers)
    while True:
        try:
            req = urllib.request.Request(url, data=data, headers=hdr, method="POST")
            with urllib.request.urlopen(req, timeout=300) as r:
                text = r.read().decode("utf-8", "replace")
            try:
                return json.loads(text)
            except ValueError:
                raise ProviderError("bad response: " + text[:200])
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            try:
                j = json.loads(text)
            except ValueError:
                j = None
            msg = None
            if isinstance(j, dict):
                err = j.get("error")
                if isinstance(err, dict):
                    msg = (err.get("metadata") or {}).get("raw") if isinstance(err.get("metadata"), dict) else None
                    msg = msg or err.get("message")
                elif isinstance(err, str):
                    msg = err
                msg = msg or j.get("message")
            code = e.code
            if code == 404:
                raise ProviderError("model not found: %s — try /model to pick another" % (msg or text[:200]))
            if code in (401, 403):
                raise ProviderError("auth failed: %s" % (msg or "check your API key with /key"))
            if code in (429, 408, 425) or 500 <= code < 600:
                attempt += 1
                if attempt > MAX_RETRIES:
                    raise ProviderError("HTTP %d after %d retries: %s" % (code, MAX_RETRIES, msg or text[:200]))
                ra = _retry_after(e.headers)
                delay = min(MAX_WAIT, ra if ra is not None else wait)
                sys.stderr.write("\n  ⟳ %s — retry %d/%d in %ds\n" % ("rate limited" if code == 429 else "HTTP %d" % code, attempt, MAX_RETRIES, round(delay)))
                time.sleep(delay)
                wait = min(wait * 2 + random.random() * 0.5, MAX_WAIT)
                continue
            raise ProviderError("HTTP %d: %s" % (code, msg or text[:400]))
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as e:
            attempt += 1
            if attempt > MAX_RETRIES:
                raise ProviderError("network error: %s" % getattr(e, "reason", e))
            delay = min(MAX_WAIT, wait)
            sys.stderr.write("\n  ⟳ network error — retry %d/%d in %ds\n" % (attempt, MAX_RETRIES, round(delay)))
            time.sleep(delay)
            wait = min(wait * 2 + random.random() * 0.5, MAX_WAIT)


def _safe(s):
    if s is None:
        return {}
    if isinstance(s, dict):
        return s
    try:
        v = json.loads(s)
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


def _openai(cfg, key, messages, with_tools):
    provider = cfg["provider"]
    base = BASES.get(provider) or cfg.get("baseUrl") or ""
    if not base:
        raise ProviderError("No base URL configured for generic provider. Use /baseurl <url>.")
    base = base.rstrip("/")
    headers = {"Authorization": "Bearer " + key}
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/jitetee/nebula"
        headers["X-Title"] = "Ant CLI"
    oa = []
    if cfg.get("systemPrompt"):
        oa.append({"role": "system", "content": cfg["systemPrompt"]})
    for m in messages:
        r = m.get("role")
        if r == "assistant":
            o = {"role": "assistant", "content": m.get("content") or ""}
            if m.get("tool_calls"):
                o["tool_calls"] = [{"id": tc["id"], "type": "function", "function": {
                    "name": tc["name"], "arguments": tc["args"] if isinstance(tc.get("args"), str) else json.dumps(tc.get("args") or {})}}
                    for tc in m["tool_calls"]]
            oa.append(o)
        elif r == "tool":
            c = m.get("content")
            oa.append({"role": "tool", "tool_call_id": m.get("tool_call_id"), "content": c if isinstance(c, str) else json.dumps(c)})
        else:
            oa.append({"role": r, "content": m.get("content") or ""})
    body = {"model": cfg["model"], "messages": oa}
    if with_tools:
        body["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in TOOL_SCHEMAS]
        body["tool_choice"] = "auto"
    if cfg.get("maxTokens"):
        body["max_tokens"] = cfg["maxTokens"]
    elif provider == "openrouter":
        body["max_tokens"] = 2048
    data = _post(base + "/chat/completions", headers, body)
    ch = (data.get("choices") or [None])[0]
    if not ch:
        raise ProviderError("Empty response: " + json.dumps(data)[:400])
    m = ch.get("message") or {}
    return {"role": "assistant", "content": m.get("content") or "",
            "tool_calls": [{"id": tc.get("id"), "name": (tc.get("function") or {}).get("name"),
                            "args": _safe((tc.get("function") or {}).get("arguments"))} for tc in (m.get("tool_calls") or [])],
            "finish_reason": ch.get("finish_reason"), "usage": data.get("usage") or {}}


def _to_anthropic(messages):
    out = []
    for m in messages:
        r = m.get("role")
        if r == "system":
            continue
        if r == "user":
            out.append({"role": "user", "content": [{"type": "text", "text": m.get("content") or ""}]})
        elif r == "assistant":
            blocks = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m.get("tool_calls") or []:
                blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc.get("args") or {}})
            out.append({"role": "assistant", "content": blocks})
        elif r == "tool":
            blk = {"type": "tool_result", "tool_use_id": m.get("tool_call_id"), "content": m.get("content") or "", "is_error": bool(m.get("is_error"))}
            last = out[-1] if out else None
            if last and last["role"] == "user" and all(b["type"] == "tool_result" for b in last["content"]):
                last["content"].append(blk)
            else:
                out.append({"role": "user", "content": [blk]})
    return out


def _anthropic(cfg, key, messages, with_tools):
    body = {"model": cfg["model"], "max_tokens": cfg.get("maxTokens") or 4096, "messages": _to_anthropic(messages)}
    if cfg.get("systemPrompt"):
        body["system"] = cfg["systemPrompt"]
    if with_tools:
        body["tools"] = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in TOOL_SCHEMAS]
    base = (cfg.get("baseUrl") or "https://api.anthropic.com").rstrip("/") if cfg.get("anthropicBase") else "https://api.anthropic.com"
    data = _post(base + "/v1/messages", {"x-api-key": key, "anthropic-version": "2023-06-01"}, body)
    text, calls = "", []
    for b in data.get("content") or []:
        if b.get("type") == "text":
            text += b.get("text", "")
        elif b.get("type") == "tool_use":
            calls.append({"id": b.get("id"), "name": b.get("name"), "args": b.get("input") or {}})
    u = data.get("usage") or {}
    if u.get("input_tokens") is not None and u.get("output_tokens") is not None:
        u["total_tokens"] = (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0)
    return {"role": "assistant", "content": text, "tool_calls": calls, "finish_reason": data.get("stop_reason"), "usage": u}


def chat(cfg, messages, with_tools=True):
    provider = cfg["provider"]
    key = get_key(cfg, provider)
    if not key:
        raise ProviderError("Missing API key for %s. Use /key %s." % (provider, provider))
    if provider == "anthropic":
        return _anthropic(cfg, key, messages, with_tools)
    return _openai(cfg, key, messages, with_tools)
