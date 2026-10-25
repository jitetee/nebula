from .console import Console


class Live:
    def __init__(self, renderable=None, *, console=None, refresh_per_second=4, transient=False, **_):
        self.console, self.r, self.transient = console or Console(), renderable, transient
        self._shown = False

    def update(self, renderable=None, refresh=False, **_):
        if renderable is not None: self.r = renderable
        self._draw()

    def refresh(self): self._draw()

    def _draw(self):
        if self.r is None: return
        self.console.print(self.r)

    def start(self, refresh=False): self._draw(); return self
    def stop(self): pass
    def __enter__(self): return self.start()
    def __exit__(self, *a): return False
