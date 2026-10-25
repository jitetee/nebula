# 🎨 jtlearn UI Design Specification

> **Canonical reference** for all UI patterns, colors, components, and conventions used across the jtlearn codebase.

<p align="center">
  <sub>🎨 Design System • Version 1.0 • jtlearn 2.0.0</sub>
</p>

---

## 📋 Table of Contents

- [⚙️ Technology Stack](#%EF%B8%8F-technology-stack)
- [🎨 Color Palette](#-color-palette)
- [✏️ Typography & Text Formatting](#%EF%B8%8F-typography--text-formatting)
- [🧩 Component Library](#-component-library)
- [⌨️ Input Prompts](#%EF%B8%8F-input-prompts)
- [📢 Status Messages](#-status-messages)
- [🖥️ Screen Management](#%EF%B8%8F-screen-management)
- [📐 Layout Conventions](#-layout-conventions)
- [📁 File Organization](#-file-organization)
- [📦 Box Styles Reference](#-box-styles-reference)
- [⏳ Loading & Progress Indicators](#-loading--progress-indicators)
- [🏆 Achievement & Notification Patterns](#-achievement--notification-patterns)
- [🚫 Anti-Patterns](#-anti-patterns)
- [🎭 Theme Configuration](#-theme-configuration)

---

## ⚙️ Technology Stack

| Layer | Library | Purpose |
|:---|:---|:---|
| **CLI Framework** | Click (`click>=8.0.0`) | Command routing, argument parsing |
| **Terminal UI** | Rich (`rich>=12.0.0`) | All terminal formatting, panels, tables |
| **Console** | `rich.console.Console` | Single shared console instance |

> ⚠️ **No HTML, CSS, or web frameworks.** This is a pure terminal application.

---

## 🎨 Color Palette

### Canonical Colors (defined in `jtlearn/ui.py`)

```python
COLORS = {
    "primary":   "cyan",         # Default content, headers, borders
    "secondary": "green",        # Success, free content, confirmations
    "accent":    "yellow",       # Warnings, numbering, hints
    "danger":    "red",          # Errors, incorrect answers, hard mode
    "info":      "blue",         # Informational messages, links
    "success":   "bright_green", # Streaks, achievements
    "warning":   "orange1",      # Cautions, hints
    "muted":     "dim white",    # Descriptions, secondary text
}
```

### Semantic Color Mapping

| Context | Color | Usage |
|:---|:---|:---|
| Default panels | `cyan` | Content panels, menus, headers |
| Success | `green` | Correct answers, saved confirmations |
| Warning | `yellow` | Hints, cautions, achievements |
| Error | `red` | Wrong answers, invalid input |
| Info | `blue` | Social media, links, help text |
| Premium | `magenta` | Premium content, bookmarks |
| Streaks | `bright_yellow` | Streak notifications |
| Descriptions | `dim white` | Subtitles, secondary info |

### Border Style by Component

| Component | Border Style | Box Style |
|:---|:---|:---|
| Content panels | `cyan` | `ROUNDED` |
| Success messages | `green` | `ROUNDED` |
| Warning panels | `yellow` | `ROUNDED` |
| Error panels | `red` | `ROUNDED` |
| Code blocks | `green` | `ASCII` |
| Links display | `blue` | `ASCII` |
| Main banner | `bright_cyan` | `DOUBLE` |
| Achievements | `bright_yellow` | `DOUBLE` |
| Daily challenges | `bright_cyan` | `DOUBLE` |

---

## ✏️ Typography & Text Formatting

### Rich Markup Patterns

```python
# Bold colored text (headers, titles)
"[bold cyan]Title[/bold cyan]"
"[bold green]Success[/bold green]"
"[bold red]Error[/bold red]"

# Dim text (descriptions, subtitles)
"[dim]Description text[/dim]"

# Colored body text
"[cyan]Content[/cyan]"
"[white]Important text[/white]"
"[yellow]Warning text[/yellow]"

# Links
"[blue underline]https://example.com[/blue underline]"

# Icons
"[bold green]✓[/bold green]"   # Success checkmark
"[bold red]✗[/bold red]"       # Error X
"[bold yellow]![/bold yellow]"  # Warning exclamation
"[bold blue]●[/bold blue]"      # Info bullet
```

### Emoji Prefix Convention

Every section header MUST have a leading emoji:

| Emoji | Section | Emoji | Section |
|:---:|:---|:---:|:---|
| 📚 | Study Notes, Learning | 🔑 | Key Concepts, API Keys |
| 📝 | Quizzes, Quiz Results | 🎯 | Goals, Impact |
| 🤖 | AI Chat | 📜 | Credits |
| 📊 | Progress, Statistics | 📋 | Links List |
| 🔖 | Bookmarks | 🔗 | Open Links |
| 🧠 | Knowledge Brain | 📦 | Bundles, ZIP |
| 🏪 | Data Store | 🎲 | Random |
| ❤️ | Support, Donations | 💡 | Hints, Tips |
| ⚙️ | Settings | 📥 | Downloads |
| ❓ | Help | 💝 | Donations |
| ❌ | Exit | 📢 | Social Media |
| 🔥 | Streaks | ⭐ | Achievements |

---

## 🧩 Component Library

> All components are defined in `jtlearn/ui.py` and MUST be imported from there.  
> **No duplicate component definitions in other files.**

### Panels

```python
# Standard content panel
Panel(
    content,
    title=f"[bold {style}]{title}[/bold {style}]",
    border_style=style,
    box=box.ROUNDED,
)

# Panel with padding
Panel(content, box=box.ROUNDED, border_style="cyan", padding=(1, 2))

# Panel with title alignment
Panel(content, box=box.ROUNDED, border_style="cyan", title="📚 Title", title_align="left")
```

### Tables

```python
# Standard menu table (no header)
table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, expand=True)
table.add_column("Option", style="bold white", ratio=1)
table.add_column("Description", style="dim", ratio=2)

# Table with headers
table = Table(box=box.ROUNDED, border_style="cyan", show_header=True)
table.add_column("#", style="yellow", width=4, justify="center")
table.add_column("Name", style="bold white")
table.add_column("Description", style="dim")
```

### Dividers

```python
from jtlearn.ui import print_divider

print_divider()                  # Simple line
print_divider("Section", "dim")  # Labeled divider
```

### Rules (Horizontal Lines)

```python
from rich.rule import Rule
console.print(Rule("[dim]Navigation[/dim]", style="cyan"))
```

---

## ⌨️ Input Prompts

### Standard Prompt Style

ALL interactive prompts MUST use this exact format:

```python
console.input("[bold green]╰─► Your choice:[/bold green] ")
console.input("[bold green]╰─► Select topic:[/bold green] ")
console.input("[bold green]╰─► Your answer:[/bold green] ")
console.input("[bold green]╰─► Press Enter to continue...[/bold green] ")
```

### Numbered Option Lists

```python
# Standard numbered options
for i, option in enumerate(options, 1):
    console.print(f"  [yellow]{i:02d}[/yellow] [white]{option}[/white]")

# With description
for i, (name, desc) in enumerate(options, 1):
    console.print(f"  [yellow]{i:02d}[/yellow] [white]{name}[/white] [dim]({desc})[/dim]")

# Back option
console.print(f"  [yellow] 0[/yellow] [white]Back[/white]")
```

---

## 📢 Status Messages

Use the canonical functions from `ui.py`:

```python
from jtlearn.ui import show_success, show_error, show_warning, show_info

show_success("File saved successfully!")
show_error("Failed to load quiz data.")
show_warning("This action cannot be undone.")
show_info("Use 'jtlearn study' to browse notes.")
```

| Type | Format | Icon |
|:---|:---|:---:|
| Success | `✓ message` (green) | ✓ |
| Error | `✗ message` (red) | ✗ |
| Warning | `! message` (yellow) | ! |
| Info | `● message` (blue) | ● |

---

## 🖥️ Screen Management

### Clear Screen

```python
from jtlearn.ui import clear_screen
clear_screen()
```

> ⚠️ **DO NOT** define `clear_screen()` in any other file.

### Console Instance

There is exactly **ONE** `Console` instance, defined in `jtlearn/ui.py`:

```python
# In jtlearn/ui.py
from rich.console import Console
console = Console()
```

All other files MUST import and use this shared instance:

```python
from jtlearn.ui import console
console.print("...")
console.input("...")
```

> ⚠️ **DO NOT** create `console = Console()` in any other file.

---

## 📐 Layout Conventions

### Standard Screen Flow

```
1. clear_screen()
2. console.print(banner or header panel)
3. console.print()                         # Blank line
4. console.print(content panel/table)      # Main content
5. console.print()                         # Blank line
6. console.print(actions/navigation table) # Options
7. console.print()                         # Blank line
8. choice = console.input("[bold green]╰─► ...[/bold green] ")
```

### Panel Spacing

- Always print a blank `console.print()` before and after panels
- Tables should have a blank line above and below

### Navigation Pattern

```python
nav_table = Table(box=None, show_header=False, expand=True, padding=(0, 1))
nav_table.add_column("Key", style="green")
nav_table.add_column("Action", style="white")

nav_table.add_row("[N]", "Next Topic")
nav_table.add_row("[P]", "Previous Topic")
nav_table.add_row("[0]", "Back to Topics")
```

---

## 📁 File Organization

### UI Component Ownership

| File | Responsibility |
|:---|:---|
| `jtlearn/ui.py` | **All** UI components, colors, prompts, panels, tables, status messages, clear_screen |
| `jtlearn/cli.py` | Main menu, command routing, interactive flow |
| `jtlearn/engines/quiz_engine.py` | Quiz-specific UI (uses ui.py components) |
| `jtlearn/engines/notes_viewer.py` | Notes-specific UI (uses ui.py components) |
| `jtlearn/main/ai_chat.py` | Chat UI (uses ui.py components) |
| `jtlearn/main/datastore.py` | Store UI (uses ui.py components) |
| `jtlearn/main/support.py` | Support UI (uses ui.py components) |

### Import Pattern

Every file that produces UI output MUST import from `ui.py`:

```python
from jtlearn.ui import (
    console, show_panel, show_success, show_error,
    show_warning, show_info, print_divider, clear_screen, LoadingSpinner,
)
```

---

## 📦 Box Styles Reference

| Box Style | Import | Usage |
|:---|:---|:---|
| `box.ROUNDED` | `from rich import box` | Default for all panels |
| `box.ASCII` | `from rich import box` | Code blocks, link displays |
| `box.DOUBLE` | `from rich import box` | Main banner, achievements, daily challenges |

---

## ⏳ Loading & Progress Indicators

### Loading Spinner

```python
from jtlearn.ui import LoadingSpinner

with LoadingSpinner("Loading content..."):
    time.sleep(0.5)  # Simulate work
```

### Progress Bar

```python
from jtlearn.ui import create_progress

progress = create_progress()
with progress:
    task = progress.add_task("Loading...", total=100)
    progress.update(task, advance=50)
```

---

## 🏆 Achievement & Notification Patterns

```python
from jtlearn.ui import show_achievement, show_hint, show_streak

show_achievement("Perfect Score", "Answered all questions correctly", "🏆")
show_hint("The answer relates to Python decorators", 3)
show_streak(7)  # Shows "⭐ On a roll! [7x streak bonus!]"
```

---

## 🚫 Anti-Patterns (DO NOT DO THESE)

| # | Anti-Pattern | Correct Approach |
|:---:|:---|:---|
| 1 | Create `console = Console()` outside of `ui.py` | Import from `jtlearn.ui` |
| 2 | Define `clear_screen()` outside of `ui.py` | Import from `jtlearn.ui` |
| 3 | Define `print_divider()` outside of `ui.py` | Import from `jtlearn.ui` |
| 4 | Hardcode color literals | Use `COLORS` dict or semantic colors |
| 5 | Mix prompt styles | Always use `╰─►` unicode arrow |
| 6 | Use raw ANSI escape codes | Use Rich markup |
| 7 | Create duplicate panel/table helpers | Import from `jtlearn.ui` |
| 8 | Use `input()` | Always use `console.input()` |
| 9 | Use `print()` | Always use `console.print()` |

---

## 🎭 Theme Configuration

The file `data/config/theme.json` defines color schemes for future use:

| Theme | Description |
|:---|:---|
| `cyan` | Default — bright, clean terminal experience |
| `blue` | Cool, professional |
| `green` | Nature-inspired, calming |
| `purple` | Creative, unique |
| `orange` | Warm, energetic |

> Currently, colors are hardcoded via the `COLORS` dict in `ui.py`. The `theme.json` file is reserved for future theme-switching functionality.

---

## 📊 Version History

| Property | Value |
|:---|:---|
| **Document Version** | 1.0.0 |
| **jtlearn Version** | 2.0.0 |
| **Last Updated** | 2026-04-09 |
| **Author** | jtlearn Team |

---

<p align="center">
  <sub>📚 jtlearn Documentation • <a href="https://github.com/jitetee/nebula">GitHub</a> • <a href="https://kash-sight.web.app">Website</a></sub>
</p>
