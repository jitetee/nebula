"""project: ask the repo you are standing in."""
import os
import sys

from nebula_core import ai, devtools as dt, help as nhelp, tui

SYS = "You are a senior engineer pairing with the user in their terminal. Use ONLY the context given; say plainly what you cannot tell. Be concrete, short, with exact commands when useful."


def ask(question, extra=""):
    ctx = dt.project_context()
    return ai.ask("%s\n\nPROJECT CONTEXT\n%s\n%s\n\nQUESTION\n%s" % ("", ctx, ("\n" + extra) if extra else "", question), SYS)


def diff_text(limit=9000):
    _, d, _ = dt.git(["diff", "HEAD"], dt.repo_root())
    return d[:limit]


def make(kind, arg=""):
    if kind == "next":
        return ask("What should I do next? Give the 3 most valuable next steps in order, each with the exact command or file to touch.")
    if kind == "review":
        d = diff_text()
        if not d.strip():
            return "No uncommitted changes to review."
        return ask("Review these uncommitted changes. List bugs, risks, missing tests and anything that should not be committed. Say 'looks fine' if so.", "CHANGES:\n" + d)
    if kind == "explain":
        return ask("Explain what this project is, how it is laid out, and where to start reading.")
    if kind == "deploy":
        extra = ""
        try:
            import fire
            root = fire.find_root()
            if root:
                extra = "FIREBASE STATUS:\n" + "\n".join(fire.status_lines(root))
        except Exception:
            pass
        return ask("Is it safe to deploy right now? Say yes/no, then exactly what to deploy (hosting, functions, rules) and what to do first.", extra)
    if kind == "merge":
        if not arg:
            return "Which branch? project merge <branch>"
        try:
            import gitx
            ok, lines, conflicts = gitx.merge_check(arg, dt.repo_root())
            _, stat, _ = dt.git(["diff", "--stat", "HEAD...%s" % arg], dt.repo_root())
            extra = "MERGE CHECK for %s: %s\n%s\nCONFLICTS: %s" % (arg, "clean" if ok else "WOULD CONFLICT", "\n".join(lines), ", ".join(conflicts) or "none")
        except Exception as e:
            extra = "merge check unavailable: %s" % e
        return ask("Should I merge branch %s into the current branch? Answer yes/no/wait with reasons, and the exact steps." % arg, extra)
    return ask(arg)


class Menu(tui.App):
    ITEMS = [("What should I do next?", "next", ""), ("Review my uncommitted changes", "review", ""), ("Is it safe to deploy?", "deploy", ""),
             ("Should I merge a branch?", "merge", "?"), ("Explain this project", "explain", ""), ("Ask my own question", "ask", "?")]

    def start(self, ui):
        while True:
            c = ui.choose("Ask your project", [i[0] for i in self.ITEMS])
            if c is None:
                self.quit = True
                return
            _, kind, arg = self.ITEMS[c]
            if arg == "?":
                arg = ui.prompt("Branch name" if kind == "merge" else "Your question")
                if not arg:
                    continue
            ui.redraw()
            ui.text(ui.h // 2, max(0, ui.w // 2 - 8), "Thinking …", "primary"); ui.scr.refresh()
            try:
                ui.pager(self.ITEMS[c][0], make(kind, arg).splitlines())
            except ai.AIError as e:
                ui.message("AI not available", [str(e), "", "Set one up with:  accounts login ai"])

    def draw(self, ui):
        ui.text(0, 0, " " * ui.w, "bar"); ui.text(0, 1, "Project: " + os.path.basename(dt.repo_root() or os.getcwd()), "bar")

    def key(self, ui, k):
        return k not in (ord("q"), 27)


def main():
    argv = sys.argv[1:]
    nhelp.maybe_help("project", argv)
    if not argv:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            print("project needs a terminal for the menu. Try: project next"); return 2
        tui.run(Menu()); return 0
    kind = argv[0]
    try:
        print(make(kind if kind in ("next", "review", "explain", "deploy", "merge") else "ask", " ".join(argv[1:]) if kind != "ask" and kind in ("merge",) else " ".join(argv[1:] if kind == "ask" else argv)))
        return 0
    except ai.AIError as e:
        print("✖ %s" % e); return 1


if __name__ == "__main__":
    sys.exit(main())
