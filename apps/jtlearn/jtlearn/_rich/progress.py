from .console import Console


class SpinnerColumn:
    def __init__(self, *a, **k): pass


class TextColumn:
    def __init__(self, fmt="", *a, **k): self.fmt = fmt


class BarColumn(SpinnerColumn): pass
class TimeElapsedColumn(SpinnerColumn): pass


class Progress:
    def __init__(self, *columns, console=None, transient=False, **_):
        self.console, self.columns, self.tasks, self._n = console or Console(), columns, {}, 0

    def add_task(self, description="", total=100, **_):
        self._n += 1
        self.tasks[self._n] = [description, total, 0]
        self.console.print(f"[cyan]…[/] {description}")
        return self._n

    def update(self, task_id, description=None, advance=None, completed=None, **_):
        t = self.tasks.get(task_id)
        if not t: return
        if description and description != t[0]:
            t[0] = description; self.console.print(f"[cyan]…[/] {description}")
        if advance: t[2] += advance
        if completed is not None: t[2] = completed

    def advance(self, task_id, advance=1):
        self.update(task_id, advance=advance)

    def start(self): return self
    def stop(self): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
