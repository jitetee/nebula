// Small built-in replacements for `ora` (spinner) and `cli-highlight` (syntax colours), so ant needs no npm packages.
const FR = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export function ora(text = "") {
  const tty = process.stdout.isTTY;
  const sp = { text, _t: null, _i: 0,
    start() {
      if (!tty) { process.stdout.write(`${this.text}\n`); return this; }
      process.stdout.write("\x1b[?25l");
      this._t = setInterval(() => { process.stdout.write(`\r\x1b[2K\x1b[36m${FR[this._i++ % FR.length]}\x1b[0m ${this.text}`); }, 80);
      return this;
    },
    stop() { if (this._t) { clearInterval(this._t); this._t = null; process.stdout.write("\r\x1b[2K\x1b[?25h"); } return this; },
  };
  return sp;
}

const KW = new Set(("abstract as async await break case catch class const continue debugger default def del delete do elif else enum except export extends false finally fn for from function global if import in instanceof is lambda let match new nonlocal None not null of or pass print raise return self static struct super switch this throw true True try typeof undefined var void while with yield and echo fi then done esac").split(" "));
const RE = /(#[^\n]*|\/\/[^\n]*|\/\*[\s\S]*?\*\/)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)/g;
export function highlight(code) {
  if (process.env.NO_COLOR) return code;
  return code.replace(RE, (m, cm, str, num, id) => {
    if (cm) return `\x1b[2m${cm}\x1b[0m`;
    if (str) return `\x1b[32m${str}\x1b[0m`;
    if (num) return `\x1b[33m${num}\x1b[0m`;
    if (id && KW.has(id)) return `\x1b[1;36m${id}\x1b[0m`;
    return m;
  });
}
