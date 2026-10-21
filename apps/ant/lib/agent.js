import fs from "node:fs";
import path from "node:path";
import { executeTool, isReadOnly, isReadOnlyToolCall, summarizeArgs } from "./tools.js";
import { chat } from "./providers.js";
import { C, toolHeader, toolResultLines, assistantBlock, thoughtBlock, rule, statusLine, diffBlock, compactOutput, filePath } from "./ui.js";
import { T } from "./theme.js";
import {
  trimHistory,
  emergencyTrim,
  estimateHistoryTokens,
  workingBudget,
  modelLimit,
  isContextLengthError,
} from "./context.js";

let abortRequested = false;
export function requestAbort() { abortRequested = true; globalThis.__ANT_ABORT = true; }
export function clearAbort() { abortRequested = false; globalThis.__ANT_ABORT = false; }
export function isAborted() { return abortRequested; }
// initialize global flag
globalThis.__ANT_ABORT = false;

export async function runTurn({ cfg, history, userInput, askConfirm, sessionId, onPersist, stats }) {
  clearAbort();
  history.push({ role: "user", content: userInput });
  if (onPersist) try { onPersist(history, userInput); } catch {}

  const maxSteps = cfg.maxSteps || 25;
  sessionId = sessionId || `ant-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const startTime = Date.now();
  let tokensUsed = 0;
  if (stats) stats.turns = (stats.turns || 0) + 1;

  const budget = workingBudget(cfg.model);
  const limit = modelLimit(cfg.model);

  for (let step = 0; step < maxSteps; step++) {
    if (abortRequested) {
      console.log(C.yellow("(cancelled)"));
      return;
    }

    const trim = trimHistory(history, cfg.systemPrompt || "", budget);
    if (trim.trimmed > 0) {
      history.length = 0;
      history.push(...trim.history);
      console.log(C.dim(`  ↺ trimmed ${trim.trimmed} old message${trim.trimmed === 1 ? "" : "s"} to fit ${limit.toLocaleString()}-token window (${trim.beforeTokens.toLocaleString()} → ${trim.afterTokens.toLocaleString()} tok)`));
    }

    const ctxPct = Math.min(100, Math.round((trim.afterTokens / limit) * 100));
    let resp;
    const stop = spinner("thinking", () => ({ tokens: tokensUsed, ctxPct }));
    try {
      resp = await chat(cfg, history);
      const used = resp.usage?.total_tokens || 0;
      tokensUsed += used;
      if (stats) stats.tokens = (stats.tokens || 0) + used;
    } catch (e) {
      stop();
      if (isContextLengthError(e)) {
        console.log(C.yellow(`  ⚠ provider rejected: context too large — auto-compacting and retrying`));
        const er = emergencyTrim(history, cfg.systemPrompt || "", cfg.model);
        history.length = 0;
        history.push(...er.history);
        console.log(C.dim(`  ↺ compacted to ${er.afterTokens.toLocaleString()} tok`));
        const stop2 = spinner("retrying", () => ({ tokens: tokensUsed, ctxPct: Math.round((er.afterTokens / limit) * 100) }));
        try {
          resp = await chat(cfg, history);
          const used = resp.usage?.total_tokens || 0;
          tokensUsed += used;
          if (stats) stats.tokens = (stats.tokens || 0) + used;
          stop2();
        } catch (e2) {
          stop2();
          console.error(C.red(`✗ provider error after retry: ${e2.message}`));
          console.error(C.dim(`  try /reset to clear history, or /model to switch to a larger-window model`));
          return;
        }
      } else {
        console.error(C.red(`✗ provider error: ${e.message}`));
        return;
      }
    }
    stop();
    if (abortRequested) {
      console.log(C.yellow("(cancelled)"));
      return;
    }

    if (resp.content && resp.content.trim()) {
      const thoughtMatch = resp.content.match(/<thought>([\s\S]*?)<\/thought>/g);
      if (thoughtMatch) {
        for (const m of thoughtMatch) {
            const t = m.replace(/<\/?thought>/g, '');
            console.log(thoughtBlock(t));
        }
        resp.content = resp.content.replace(/<thought>[\s\S]*?<\/thought>/g, '').trim();
      }
      if (resp.content.trim()) {
        console.log("");
        console.log(assistantBlock(resp.content.trim()));
      }
    }

    history.push({
      role: "assistant",
      content: resp.content || "",
      tool_calls: resp.tool_calls,
    });

    if (!resp.tool_calls || resp.tool_calls.length === 0) {
      if (onPersist) try { onPersist(history); } catch {}
      console.log(statusLine({
        model: cfg.model,
        provider: cfg.provider,
        tokens: tokensUsed,
        elapsedMs: Date.now() - startTime,
        sessionId,
        mode: cfg.mode,
        costUSD: stats?.costUSD,
        ctxPct,
      }));
      return;
    }

    for (const call of resp.tool_calls) {
      if (abortRequested) {
        console.log(C.yellow("(cancelled)"));
        return;
      }
      const args = call.args || {};
      const summary = summarizeArgs(call.name, args);
      console.log("");
      const headerLine = toolHeader(call.name, summary);
      process.stdout.write(headerLine + "\n");
      if (stats) stats.toolCalls = (stats.toolCalls || 0) + 1;

      const mode = cfg.mode || "default";
      const isWrite = ["write_file", "edit_file", "apply_patch", "mkdir"].includes(call.name);

      let beforeText = "";
      const isDiffable = call.name === "write_file" || call.name === "edit_file" || call.name === "apply_patch";
      if (isDiffable && args.path) {
        try {
          const p = path.isAbsolute(args.path) ? args.path : path.resolve(args.path);
          beforeText = fs.existsSync(p) ? fs.readFileSync(p, "utf8") : "";
        } catch {}
      }

      const tStart = Date.now();
      let result;
      let isError = false;

      const effectivelyReadOnly = isReadOnlyToolCall(call.name, args);
      if (!effectivelyReadOnly) {
        if (mode === "yolo") {
          // auto-approve
        } else if (mode === "plan") {
          result = "blocked: plan mode is read-only — propose a plan first, then ask the user to switch modes";
          isError = true;
          console.log("  " + T.muted("└─ ") + C.yellow("blocked (plan mode)"));
        } else if (mode === "acceptEdits" && isWrite) {
          // auto-approve writes
        } else {
          const ok = await askConfirm(`  ${C.yellow("▸ approve?")}`);
          if (!ok) {
            result = "user denied this action";
            isError = true;
            console.log("  " + T.muted("└─ ") + C.yellow("skipped"));
          }
        }
      }

      if (result === undefined) {
        try {
          result = await executeTool(call.name, args);
        } catch (e) {
          result = `error: ${e.message}`;
          isError = true;
        }
      }
      const ms = Date.now() - tStart;

      if (!isError && isDiffable && args.path) {
        let afterText = "";
        try {
          const p = path.isAbsolute(args.path) ? args.path : path.resolve(args.path);
          afterText = fs.readFileSync(p, "utf8");
        } catch {}
        const rel = (args.path || "").replace(process.env.HOME || "", "~");
        const diff = diffBlock(beforeText, afterText, rel);
        const indented = diff.split("\n").map((l) => "  " + l).join("\n");
        console.log(indented);
        console.log("  " + T.muted(`└─ done in ${ms}ms`));
      } else if (!isError && (call.name === "bash" || call.name === "run_code")) {
        console.log(toolResultLines(compactOutput(result)));
        console.log("  " + T.muted(`└─ exit · ${ms}ms`));
      } else if (isError) {
        console.log("  " + T.muted("└─ ") + T.error(String(result).split("\n")[0]));
      } else {
        console.log(toolResultLines(result));
      }

      history.push({
        role: "tool",
        tool_call_id: call.id || `${call.name}-${step}`,
        name: call.name,
        content: typeof result === "string" ? result : JSON.stringify(result),
        is_error: isError,
      });
      if (onPersist) try { onPersist(history); } catch {}
    }
  }
  console.error(C.yellow(`(reached max ${maxSteps} steps)`));
  console.log(statusLine({
    model: cfg.model,
    provider: cfg.provider,
    tokens: tokensUsed,
    elapsedMs: Date.now() - startTime,
    sessionId,
  }));
}

import { ora } from "./mini.js";
// ... (rest of imports)

function spinner(label, getStats = () => ({})) {
  const sp = ora(label).start();
  const id = setInterval(() => {
    const stats = getStats() || {};
    const tk = stats.tokens && stats.tokens > 0 ? `${stats.tokens.toLocaleString()} tok` : "";
    const ctx = stats.ctxPct != null ? `ctx ${stats.ctxPct}%` : "";
    sp.text = `${label}... ${T.muted([tk, ctx].filter(Boolean).join(" · "))}`;
  }, 100);
  return () => {
    clearInterval(id);
    sp.stop();
  };
}

export { C as colors };
