// Arrow-key picker for TTY, numbered fallback otherwise. Zero deps.
import readline from "node:readline";
import { C } from "./ui.js";

export function pick({ title, items, initial = 0 }) {
  if (!process.stdin.isTTY || !process.stdout.isTTY) {
    return pickNumbered({ title, items, initial });
  }
  return pickArrow({ title, items, initial });
}

function pickArrow({ title, items, initial }) {
  return new Promise((resolve) => {
    let idx = Math.max(0, Math.min(initial, items.length - 1));
    const stdin = process.stdin;
    const stdout = process.stdout;
    const wasRaw = stdin.isRaw;
    readline.emitKeypressEvents(stdin);
    stdin.setRawMode(true);
    stdin.resume();

    let firstDraw = true;
    const draw = () => {
      if (!firstDraw) {
        // move cursor up by lines we previously drew, then clear below
        stdout.write(`\x1b[${items.length + 2}A`);
      }
      firstDraw = false;
      stdout.write("\x1b[J");
      stdout.write(`${C.bold(title)}\n`);
      stdout.write(C.dim("  ↑/↓ select · enter to confirm · esc to cancel\n"));
      for (let i = 0; i < items.length; i++) {
        const it = items[i];
        const label = typeof it === "string" ? it : it.label || it.id || "";
        const note = typeof it === "string" ? "" : it.note || "";
        const sel = i === idx;
        const marker = sel ? C.green("❯") : " ";
        const line = sel
          ? `${marker} ${C.cyan(label)}${note ? "  " + C.dim(note) : ""}`
          : `${marker} ${label}${note ? "  " + C.dim(note) : ""}`;
        stdout.write(line + "\n");
      }
    };

    const cleanup = () => {
      stdin.removeListener("keypress", onKey);
      stdin.setRawMode(wasRaw || false);
      stdin.pause();
    };

    const onKey = (_str, key) => {
      if (!key) return;
      if (key.name === "up" || (key.name === "k" && !key.ctrl)) {
        idx = (idx - 1 + items.length) % items.length;
        draw();
      } else if (key.name === "down" || (key.name === "j" && !key.ctrl)) {
        idx = (idx + 1) % items.length;
        draw();
      } else if (key.name === "return") {
        cleanup();
        resolve(items[idx]);
      } else if (key.name === "escape" || (key.ctrl && key.name === "c")) {
        cleanup();
        resolve(null);
      }
    };

    stdin.on("keypress", onKey);
    draw();
  });
}

function pickNumbered({ title, items, initial }) {
  return new Promise((resolve) => {
    process.stdout.write(`${C.bold(title)}\n`);
    items.forEach((it, i) => {
      const label = typeof it === "string" ? it : it.label || it.id || "";
      const note = typeof it === "string" ? "" : it.note || "";
      process.stdout.write(`  ${C.cyan(String(i + 1).padStart(2))}. ${label}${note ? "  " + C.dim(note) : ""}\n`);
    });
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(C.dim(`pick [1-${items.length}, default ${initial + 1}]: `), (ans) => {
      rl.close();
      const n = parseInt(ans.trim(), 10);
      if (!Number.isFinite(n) || n < 1 || n > items.length) resolve(items[initial]);
      else resolve(items[n - 1]);
    });
  });
}

export function prompt(question, { hide = false } = {}) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    if (hide) {
      // Mute echoed characters by overwriting the line on each keypress.
      const onData = () => {
        readline.clearLine(process.stdout, 1);
        readline.cursorTo(process.stdout, question.length);
      };
      process.stdin.on("data", onData);
      rl.question(question, (a) => {
        process.stdin.removeListener("data", onData);
        rl.close();
        process.stdout.write("\n");
        resolve(a.trim());
      });
    } else {
      rl.question(question, (a) => {
        rl.close();
        resolve(a.trim());
      });
    }
  });
}
