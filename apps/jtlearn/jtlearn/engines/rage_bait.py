#!/usr/bin/env python3
"""
Rage Bait - a trick-question game that learns at you.

Every round is a little unfair on purpose: popular myths, misleading wording,
a bar that never quite finishes, a computer that cheats at guessing. The twist is
that each one teaches something true once you are done being annoyed.
Fill the rage meter to 100 and you lose. Your best run is saved.
"""
import random
import select
import sys
import time

from jtlearn.ui import console
from jtlearn.config import get_config_value, set_config_value

MAX_RAGE = 100

TAUNTS_WRONG = [
    "Wrong. So wrong. Beautifully wrong.",
    "Incorrect. Bold of you, though.",
    "Nope. Everyone says that.",
    "Close! (It wasn't close.)",
    "Hm. Interesting. Wrong, but interesting.",
    "That is what most people pick. Most people are wrong.",
]
TAUNTS_RIGHT = [
    "Fine. You got it. Don't let it go to your head.",
    "Correct. Lucky guess?",
    "Right. Annoyingly right.",
    "Yes. Moving on before you celebrate.",
]

# (statement, is_true, explanation)
MYTHS = [
    ("The Great Wall of China is visible from space with the naked eye.", False,
     "It is long but only a few metres wide. Astronauts say they cannot pick it out unaided."),
    ("Humans only use 10% of their brains.", False,
     "Brain imaging shows activity across the whole brain; different regions just work at different times."),
    ("Tomatoes are botanically a fruit.", True,
     "A fruit is the seed-bearing part of a plant. Tomatoes, cucumbers and peppers all qualify."),
    ("Lightning never strikes the same place twice.", False,
     "It does, all the time. The Empire State Building is hit about 20 times a year."),
    ("The capital of Australia is Sydney.", False, "It is Canberra, chosen as a compromise between Sydney and Melbourne."),
    ("Goldfish have a 3-second memory.", False, "They can remember things for months and can be trained."),
    ("Bats are blind.", False, "All bats can see; many also use echolocation in the dark."),
    ("Water conducts electricity because of the impurities in it.", True,
     "Pure water barely conducts. Dissolved ions (salts, minerals) are what carry the current."),
    ("Shaving makes hair grow back thicker.", False, "Hair is just cut blunt, which feels coarser. Growth rate does not change."),
    ("A day on Venus is longer than its year.", True,
     "Venus spins so slowly (243 Earth days) that it orbits the Sun (225 days) faster than it rotates."),
    ("You lose most of your body heat through your head.", False,
     "Roughly in proportion to its surface area, about 7-10%. Any uncovered skin loses heat."),
    ("Cracking your knuckles causes arthritis.", False, "Studies found no link. The pop is gas bubbles in the joint fluid."),
    ("Honey never spoils.", True, "Its low water content and acidity stop microbes; edible honey has been found in ancient tombs."),
    ("Sound travels faster in space than in air.", False, "Space is a near-vacuum, so sound cannot travel through it at all."),
]

LETTER_SENTENCES = [
    "Eleven elephants eat eggs every evening",
    "Seven secret seekers seldom see seashells",
    "Coffee keeps cheerful chefs feeling fresh",
    "Teresa the teacher tested three tired tutors",
]


class Rage:
    def __init__(self):
        self.rage = 0
        self.score = 0
        self.round = 0
        self.myths = list(MYTHS)
        self.best = int(get_config_value("rage_best", 0) or 0)

    # -- ui helpers --
    def meter(self):
        filled = min(20, self.rage * 20 // MAX_RAGE)
        bar = "█" * filled + "░" * (20 - filled)
        colour = "green" if self.rage < 40 else ("yellow" if self.rage < 75 else "red")
        return f"[{colour}]{bar}[/{colour}] {self.rage}%"

    def header(self, title):
        self.round += 1
        console.print()
        console.print(f"[bold cyan]── Round {self.round}: {title} ──[/bold cyan]")
        console.print(f"[dim]Rage {self.meter()}   Score {self.score}   Best {self.best}[/dim]")

    def good(self, pts=10):
        self.score += pts
        console.print(f"[green]✓ {random.choice(TAUNTS_RIGHT)}[/green] [dim](+{pts})[/dim]")

    def bad(self, rage=20, why=""):
        self.rage = min(MAX_RAGE, self.rage + rage)
        console.print(f"[red]✗ {random.choice(TAUNTS_WRONG)}[/red] [dim](+{rage} rage)[/dim]")
        if why:
            console.print(f"[dim]  {why}[/dim]")

    def ask(self, text):
        try:
            return console.input(text).strip()
        except (EOFError, KeyboardInterrupt):
            raise SystemExit_()

    # -- rounds --
    def r_myth(self):
        self.header("Myth or fact?")
        if not self.myths:
            self.myths = list(MYTHS)
        item = random.choice(self.myths)
        self.myths.remove(item)
        text, truth, why = item
        console.print(f"[bold]{text}[/bold]")
        a = self.ask("[yellow]╰─► true or false (t/f): [/yellow]").lower()
        if a[:1] not in ("t", "f"):
            console.print("[red]That was not true or false. Counting it as wrong.[/red]")
            self.bad(15, why)
        elif (a[0] == "t") == truth:
            self.good()
            console.print(f"[dim]  {why}[/dim]")
        else:
            self.bad(20, why)

    def r_letters(self):
        self.header("Count carefully")
        s = random.choice(LETTER_SENTENCES)
        letter = random.choice("est")
        console.print(f'How many times does the letter [bold]{letter}[/bold] appear in:')
        console.print(f'  [italic]"{s}"[/italic]')
        a = self.ask("[yellow]╰─► number: [/yellow]")
        n = s.lower().count(letter)
        if a.isdigit() and int(a) == n:
            self.good(15)
        else:
            self.bad(20, f"It appears {n} times. Counting upper and lower case.")

    def r_patience(self):
        self.header("The Patience Test")
        console.print("Do NOT type anything and do NOT press Enter for 5 seconds.")
        console.print("[dim]Starting... now.[/dim]")
        t0 = time.time()
        broke = False
        try:
            if sys.stdin.isatty():
                import termios
                termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
            while time.time() - t0 < 5:
                r, _, _ = select.select([sys.stdin], [], [], 0.1)
                if r:
                    sys.stdin.readline()
                    broke = True
                    break
        except (KeyboardInterrupt, ValueError, OSError):
            broke = True
        if broke:
            self.bad(25, "You caved at %.1fs. Waiting is a skill." % (time.time() - t0))
        else:
            self.good(20)

    def r_loading(self):
        self.header("Please wait while we load")
        console.print("[dim]Loading your reward...[/dim]")
        width = 30
        for pct in range(0, 100):
            done = pct * width // 100
            sys.stdout.write("\r[%s%s] %d%%" % ("█" * done, "░" * (width - done), pct))
            sys.stdout.flush()
            time.sleep(0.015 if pct < 90 else 0.06)
            if pct == 99:
                break
        sys.stdout.write("\r[%s] 99%%\n" % ("█" * (width - 1) + "░"))
        time.sleep(1.2)
        console.print("[red]Error: reward could not be loaded. Restarting from 0%.[/red]")
        a = self.ask("[yellow]╰─► Press Enter to try again, or type 'skip' to move on: [/yellow]").lower()
        if a == "skip":
            self.bad(10, "Skipping is allowed. It just costs rage. (The reward was a gold star.)")
        else:
            console.print("[dim]Loading... Loading... ok it finished this time.[/dim]")
            self.good(10)
            console.print("[dim]  You waited. The 'reward' is the satisfaction. And 10 points.[/dim]")

    def r_rigged(self):
        self.header("Guess my number (1-10)")
        console.print("I am thinking of a number. I will definitely not change it.")
        for attempt in range(1, 4):
            a = self.ask("[yellow]╰─► guess: [/yellow]")
            if not a.isdigit() or not 1 <= int(a) <= 10:
                console.print("[red]1 to 10. It is in the title.[/red]")
                self.rage = min(MAX_RAGE, self.rage + 5)
                continue
            g = int(a)
            if attempt < 3:
                other = random.choice([n for n in range(1, 11) if n != g])
                console.print(f"[red]No! It was {other}.[/red] [dim](It was {g} until you said it.)[/dim]")
                self.rage = min(MAX_RAGE, self.rage + 10)
            else:
                console.print(f"[green]Ok ok. {g}. Fine. You win this one.[/green]")
                self.score += 15
                console.print("[dim]  Lesson: a computer only picks 'randomly' if it commits before you answer. Cheat check: pass.[/dim]")
                return
        console.print("[dim]  Three tries, no luck. Fairness not included.[/dim]")

    def r_math(self):
        self.header("Quick maths")
        console.print("[bold]6 ÷ 2(1+2) = ?[/bold]")
        a = self.ask("[yellow]╰─► answer: [/yellow]")
        if a in ("1", "9"):
            console.print("[red]Wrong.[/red] [dim](Whichever one you said.)[/dim]")
            self.rage = min(MAX_RAGE, self.rage + 15)
            console.print("[dim]  Truth: the expression is ambiguous. Calculators and conventions disagree on whether 2(1+2) binds tighter than ÷."
                          " Good writing uses brackets so nobody argues. 9 if you go strictly left to right.[/dim]")
        else:
            self.bad(15, "Neither 1 nor 9. Even the wrong answers were more reasonable.")

    ROUNDS = ["r_myth", "r_myth", "r_letters", "r_patience", "r_rigged", "r_myth", "r_loading", "r_math", "r_myth"]

    def play(self):
        console.print("[bold magenta]😤 RAGE BAIT[/bold magenta]  [dim]trick questions that teach. Rage hits 100 = you lose. Ctrl-C quits.[/dim]")
        try:
            for name in self.ROUNDS:
                getattr(self, name)()
                if self.rage >= MAX_RAGE:
                    console.print()
                    console.print("[bold red]💥 You rage-quit. The game wins.[/bold red]")
                    break
            else:
                console.print()
                console.print("[bold green]🏆 You survived with a calm mind.[/bold green]")
                self.score += (MAX_RAGE - self.rage) // 5
        except SystemExit_:
            console.print("\n[dim]Walked away. Wise.[/dim]")
        self.finish()

    def finish(self):
        title = ("Zen Master" if self.rage < 20 else "Level-headed" if self.rage < 50 else
                 "Slightly Steamed" if self.rage < 80 else "Volcano")
        console.print()
        console.print(f"[bold]Final: score {self.score}  ·  rage {self.rage}%  ·  {title}[/bold]")
        if self.score > self.best:
            console.print("[green]🎉 New personal best![/green]")
            try:
                set_config_value("rage_best", self.score)
            except Exception:
                pass
        console.print()


class SystemExit_(Exception):
    pass


def run_rage_bait():
    Rage().play()
    try:
        console.input("[dim]Press Enter to return...[/dim]")
    except (EOFError, KeyboardInterrupt):
        pass
