"""
Navigation Utilities for kslearn

Provides consistent menu navigation with breadcrumbs and back/home support.
"""

from typing import List, Optional, Tuple
from rich.panel import Panel
from rich import box

from kslearn.ui import console, COLORS

# Breadcrumb separator
BREADCRUMB_SEP = " > "


def build_breadcrumb(parts: List[str]) -> str:
    """Build a breadcrumb string from parts.

    Example: build_breadcrumb(["Home", "Profile", "Edit"]) → "Home > Profile > Edit"
    """
    return BREADCRUMB_SEP.join(parts)


def show_breadcrumb(parts: List[str]) -> None:
    """Display a breadcrumb panel at the top of a menu."""
    if not parts:
        return
    breadcrumb = BREADCRUMB_SEP.join(parts)
    console.print(f"[dim]📍 {breadcrumb}[/dim]")
    console.print()


def render_menu_table(
    title: str,
    options: List[Tuple[str, str, str]],
    footer: Optional[str] = None,
) -> None:
    """Render a consistent menu table.

    Args:
        title: Menu title for the panel
        options: List of (key, label, description) tuples
        footer: Optional footer text displayed below the table
    """
    from kslearn.ui import show_panel

    show_panel(title, "", "cyan")
    console.print()

    tbl = __import__("rich.table", fromlist=["Table"]).Table(
        box=box.ROUNDED,
        border_style=COLORS.get("border", "cyan"),
        show_header=False,
        expand=True,
    )
    tbl.add_column("Option", style=COLORS.get("primary", "cyan"), ratio=1)
    tbl.add_column("Description", style=COLORS.get("muted", "dim"), ratio=2)

    for key, label, desc in options:
        tbl.add_row(label, desc)

    console.print(tbl)
    console.print()

    if footer:
        console.print(f"[dim]{footer}[/dim]")
        console.print()


def prompt_choice(hint: str) -> str:
    """Prompt the user for a menu choice with consistent formatting.

    Args:
        hint: The list of valid choices for the prompt, e.g. "1-3, B"

    Returns:
        The stripped, uppercased user input.
    """
    prompt_color = COLORS.get("success", "bright_green")
    return console.input(
        f"[bold {prompt_color}]╰─► Your choice ({hint}):[/bold {prompt_color}] "
    ).strip().upper()


def handle_back(choice: str) -> bool:
    """Check if the choice is a back/home/quit command.

    Returns True if the caller should return to the parent menu.
    """
    if choice in ("B", "BACK", "Q", "QUIT"):
        return True
    return False


def handle_home(choice: str) -> bool:
    """Check if the choice is a home command (return to main menu).

    Returns True if the caller should signal a return to the main loop.
    """
    if choice in ("H", "HOME", "M", "MAIN"):
        return True
    return False
