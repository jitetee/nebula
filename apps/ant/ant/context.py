"""Token estimation and history trimming (no extra API calls)."""
import json
import math
import re

_LIMITS = [(r"claude-(sonnet|opus|haiku)-4", 200000), (r"claude-3", 200000), (r"gpt-5", 200000), (r"gpt-4\.1", 1000000),
           (r"gpt-4o", 128000), (r"o4-mini|o3", 200000), (r"gemini-1\.5", 1000000), (r"gemini", 128000),
           (r"deepseek", 128000), (r"llama-3\.3", 128000), (r"qwen3", 128000), (r"glm-4\.5", 128000),
           (r"gpt-oss", 32000), (r"gemma", 8000), (r"nemotron", 32000), (r"mistral|codestral", 32000)]


def model_limit(model):
    for pat, n in _LIMITS:
        if model and re.search(pat, model, re.I):
            return n
    return 32000


def working_budget(model):
    return max(4096, int(model_limit(model) * 0.75))


def est(text):
    if not text:
        return 0
    if not isinstance(text, str):
        text = json.dumps(text)
    return math.ceil(len(text) / 4)


def est_msg(m):
    n = 4 + est(m.get("content"))
    for tc in m.get("tool_calls") or []:
        n += est(tc.get("name") or "") + est(json.dumps(tc.get("args") or {}))
    return n + est(m.get("tool_call_id")) + est(m.get("name"))


def est_history(history, system=""):
    return est(system) + sum(est_msg(m) for m in history)


def cap_tool_result(m, cap=8000):
    if m.get("role") != "tool":
        return m
    c = m.get("content")
    c = c if isinstance(c, str) else json.dumps(c)
    if len(c) <= cap:
        return m
    head, tail = c[: int(cap * 0.7)], c[-int(cap * 0.2):]
    return dict(m, content="%s\n…[%d chars truncated to fit context]…\n%s" % (head, len(c) - len(head) - len(tail), tail))


def trim_history(history, system, budget):
    before = est_history(history, system)
    work = [cap_tool_result(m) for m in history]
    after = est_history(work, system)
    dropped, keep = 0, 4
    while after > budget and len(work) > keep:
        work.pop(0); dropped += 1
        while len(work) > keep and work[0].get("role") != "user":
            work.pop(0); dropped += 1
        after = est_history(work, system)
    return {"history": work, "trimmed": dropped, "before": before, "after": after, "over": after > budget}


def emergency_trim(history, system, model):
    budget = working_budget(model) // 2
    r = trim_history(history, system, budget)
    while r["over"] and budget > 4096:
        budget //= 2
        r = trim_history(r["history"], system, budget)
    return r


def is_context_error(err):
    m = str(err).lower()
    return ("maximum context length" in m or "context_length_exceeded" in m or "too many tokens" in m
            or "prompt is too long" in m or ("400" in m and "token" in m))
