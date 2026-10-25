import getpass

from . import _core as c


class PromptBase:
    @classmethod
    def ask(cls, prompt="", *, console=None, password=False, choices=None, default=None, show_default=True,
            show_choices=True, **_):
        label = c.markup_to_ansi(str(prompt))
        if choices and show_choices:
            label += " " + c.markup_to_ansi("[" + "/".join(choices) + "]", "magenta bold")
        if default is not None and show_default:
            label += " " + c.markup_to_ansi(f"({default})", "cyan bold")
        label += c.markup_to_ansi(": ")
        while True:
            try:
                if password:
                    v = getpass.getpass(c.strip_ansi(label))
                else:
                    v = input(label)
            except EOFError:
                v = ""
            if v == "" and default is not None:
                return default
            if choices and v not in choices:
                print(c.markup_to_ansi("[prompt.invalid]Please select one of the available options", "red"))
                continue
            return v


class Prompt(PromptBase):
    pass


class Confirm:
    @classmethod
    def ask(cls, prompt="", *, console=None, default=False, **_):
        label = c.markup_to_ansi(str(prompt)) + " " + c.markup_to_ansi("[y/n]", "magenta bold") + " "
        label += c.markup_to_ansi("(y)" if default else "(n)", "cyan bold") + c.markup_to_ansi(": ")
        while True:
            try:
                v = input(label).strip().lower()
            except EOFError:
                v = ""
            if v == "":
                return default
            if v in ("y", "yes"): return True
            if v in ("n", "no"): return False
            print(c.markup_to_ansi("Please enter Y or N", "red"))


class IntPrompt(PromptBase):
    @classmethod
    def ask(cls, prompt="", **kw):
        while True:
            v = PromptBase.ask.__func__(cls, prompt, **kw)
            try:
                return int(v)
            except (TypeError, ValueError):
                print(c.markup_to_ansi("Please enter a valid integer number", "red"))
