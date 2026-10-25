class Spinner:
    def __init__(self, name="dots", text="", style=None, **_):
        self.text = text
    def _spans(self):
        from ._core import parse_markup
        return parse_markup("⠋ " + str(self.text))
