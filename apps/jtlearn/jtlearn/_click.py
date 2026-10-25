"""A small standard-library stand-in for the parts of `click` that jtlearn uses."""
import sys
import textwrap

STRING = str
_ctx_stack = []


class Exit(Exception):
    def __init__(self, code=0):
        self.code = code


class Context:
    def __init__(self, command, parent=None):
        self.command, self.parent, self.invoked_subcommand, self.obj = command, parent, None, None

    def exit(self, code=0):
        raise Exit(code)

    def invoke(self, target, *args, **kwargs):
        cmd = target if isinstance(target, Command) else None
        fn = cmd.callback if cmd else target
        if cmd:                                  # fill unspecified options with defaults, like click does
            for p in cmd.params:
                kwargs.setdefault(p.dest, p.default)
        return fn(*args, **kwargs)


def get_current_context():
    return _ctx_stack[-1]


class Param:
    def __init__(self, names, is_flag=False, type=None, default=None, required=False, help="", argument=False):
        self.names, self.is_flag, self.type, self.default = names, is_flag, type, (False if is_flag and default is None else default)
        self.required, self.help, self.argument = required, help, argument
        longs = [n for n in names if n.startswith("--")]
        plain = [n for n in names if not n.startswith("-")]
        if argument:
            self.dest = names[0]
        elif plain:
            self.dest = plain[0]
        else:
            self.dest = (longs[0] if longs else names[0]).lstrip("-").replace("-", "_")
        self.flags = [n for n in names if n.startswith("-")]


class Command:
    def __init__(self, callback, name=None, help=None, params=None, pass_ctx=False):
        self.callback, self.params, self.pass_ctx = callback, params or [], pass_ctx
        self.name = name or callback.__name__.replace("_", "-")
        self.help = help if help is not None else (callback.__doc__ or "")

    def __call__(self, *a, **k):
        return self.callback(*a, **k)

    def _usage(self, prog):
        opts = " [OPTIONS]" if any(not p.argument for p in self.params) else ""
        args = "".join(f" [{p.dest.upper()}]" if not p.required else f" {p.dest.upper()}" for p in self.params if p.argument)
        return f"Usage: {prog}{opts}{args}"

    def format_help(self, prog):
        out = [self._usage(prog), ""]
        doc = textwrap.dedent(self.help).strip()
        if doc:
            out += ["  " + l if l.strip() else "" for l in doc.replace("\b", "").splitlines()] + [""]
        opts = [p for p in self.params if not p.argument]
        if opts:
            out.append("Options:")
            for p in opts:
                label = ", ".join(p.flags) + ("" if p.is_flag else " TEXT")
                out.append(f"  {label:<24}{p.help}")
            out.append("  --help                  Show this message and exit.")
        else:
            out.append("Options:\n  --help  Show this message and exit.")
        return "\n".join(out)

    def parse(self, argv, prog):
        vals = {p.dest: p.default for p in self.params}
        pos = [p for p in self.params if p.argument]
        pi, i, only_pos = 0, 0, False
        while i < len(argv):
            a = argv[i]
            if not only_pos and a == "--":
                only_pos = True; i += 1; continue
            if not only_pos and a.startswith("-") and len(a) > 1:
                key, eq, val = a.partition("=")
                p = next((q for q in self.params if not q.argument and key in q.flags), None)
                if not p:
                    raise UsageError(f"No such option: {key}", self, prog)
                if p.is_flag:
                    vals[p.dest] = True
                else:
                    if eq: v = val
                    else:
                        i += 1
                        if i >= len(argv): raise UsageError(f"Option '{key}' requires an argument.", self, prog)
                        v = argv[i]
                    vals[p.dest] = p.type(v) if callable(p.type) and p.type not in (None,) else v
            else:
                if pi >= len(pos):
                    raise UsageError(f"Got unexpected extra argument ({a})", self, prog)
                vals[pos[pi].dest] = a; pi += 1
            i += 1
        for p in pos[pi:]:
            if p.required: raise UsageError(f"Missing argument '{p.dest.upper()}'.", self, prog)
        return vals


class UsageError(Exception):
    def __init__(self, msg, cmd, prog):
        super().__init__(msg); self.msg, self.cmd, self.prog = msg, cmd, prog


class Group(Command):
    def __init__(self, callback, invoke_without_command=False, **kw):
        super().__init__(callback, **kw)
        self.commands, self.invoke_without_command = {}, invoke_without_command

    def command(self, name=None, **kw):
        def deco(fn):
            c = make_command(fn, name=name, **kw)
            self.commands[c.name] = c
            return c
        return deco

    def add_command(self, cmd, name=None):
        self.commands[name or cmd.name] = cmd

    def format_help(self, prog):
        base = Command.format_help(self, prog).replace("Usage: " + prog, "Usage: " + prog + " [OPTIONS] COMMAND [ARGS]...", 1)
        base = base.split("\n")
        # insert the command list before the Options block
        idx = base.index("Options:") if "Options:" in base else len(base)
        cmds = ["Commands:"]
        for n, c in sorted(self.commands.items()):
            first = textwrap.dedent(c.help).strip().splitlines()[0] if c.help.strip() else ""
            cmds.append(f"  {n:<14}{first}")
        return "\n".join(base[:idx] + base[idx:] + [""] + cmds)

    def main(self, args=None, prog_name=None, standalone_mode=True):
        argv = list(sys.argv[1:] if args is None else args)
        prog = prog_name or "jtlearn"
        try:
            return self._run(argv, prog, None)
        except Exit as e:
            if standalone_mode: sys.exit(e.code)
            return e.code
        except UsageError as e:
            print(e.cmd._usage(e.prog)); print(f"Try '{e.prog} --help' for help.\n\nError: {e.msg}")
            sys.exit(2)

    __call__ = main

    def _run(self, argv, prog, parent):
        # split group options from the sub-command name
        i = 0
        while i < len(argv) and argv[i].startswith("-"):
            p = next((q for q in self.params if not q.argument and argv[i] in q.flags), None)
            i += 1 if (p is None or p.is_flag or "=" in argv[i] or argv[i] in ("--help", "-h")) else 2
        gargs, rest = argv[:i], argv[i:]
        if "--help" in gargs or "-h" in gargs or (rest and rest[0] in ("--help", "-h") and False):
            print(self.format_help(prog)); raise Exit(0)
        vals = self.parse(gargs, prog)
        ctx = Context(self, parent)
        sub = None
        if rest:
            sub = self.commands.get(rest[0])
            if sub is None:
                raise UsageError(f"No such command '{rest[0]}'.", self, prog)
            ctx.invoked_subcommand = sub.name
        _ctx_stack.append(ctx)
        try:
            kw = dict(vals)
            self.callback(ctx, **kw) if self.pass_ctx else self.callback(**kw)
            if sub is not None:
                sub_argv = rest[1:]
                if "--help" in sub_argv or "-h" in sub_argv:
                    print(sub.format_help(f"{prog} {sub.name}")); raise Exit(0)
                svals = sub.parse(sub_argv, f"{prog} {sub.name}")
                _ctx_stack.append(Context(sub, ctx))
                try:
                    sub.callback(**svals) if not sub.pass_ctx else sub.callback(_ctx_stack[-1], **svals)
                finally:
                    _ctx_stack.pop()
        finally:
            _ctx_stack.pop()


def make_command(fn, name=None, **kw):
    if isinstance(fn, Command):
        return fn
    params = list(reversed(getattr(fn, "_params", [])))
    return Command(fn, name=name, params=params, pass_ctx=getattr(fn, "_pass_ctx", False), **kw)


def _attach(fn, p):
    fn.__dict__.setdefault("_params", []).append(p)
    return fn


def option(*names, is_flag=False, type=None, default=None, required=False, help="", **_):
    def deco(fn):
        return _attach(fn, Param(list(names), is_flag=is_flag, type=type, default=default, required=required, help=help))
    return deco


def argument(name, required=True, type=None, default=None, **_):
    def deco(fn):
        return _attach(fn, Param([name], argument=True, required=required, type=type, default=default))
    return deco


def pass_context(fn):
    fn._pass_ctx = True
    return fn


def group(name=None, invoke_without_command=False, **kw):
    def deco(fn):
        params = list(reversed(getattr(fn, "_params", [])))
        return Group(fn, invoke_without_command=invoke_without_command, name=name or fn.__name__, params=params,
                     pass_ctx=getattr(fn, "_pass_ctx", False), **kw)
    return deco


def command(name=None, **kw):
    def deco(fn):
        return make_command(fn, name=name, **kw)
    return deco


def echo(msg="", nl=True, **_):
    sys.stdout.write(str(msg) + ("\n" if nl else "")); sys.stdout.flush()
