#!/usr/bin/env python3
"""Rich UI components for kslearn CLI"""

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.box import DOUBLE, ROUNDED, HEAVY
from rich.style import Style
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box

console = Console()

# Default color palette (fallback if theme loading fails)
DEFAULT_COLORS = {
    "primary": "cyan",
    "secondary": "green",
    "accent": "yellow",
    "danger": "red",
    "info": "blue",
    "success": "bright_green",
    "warning": "orange1",
    "muted": "dim white",
    "banner": "bright_cyan",
    "border": "cyan",
    "header": "bold cyan",
    "menu_number": "yellow",
    "menu_text": "white",
    "table_header": "bold cyan",
    "panel_title": "bold cyan",
}

# Active colors (will be loaded from theme)
COLORS = DEFAULT_COLORS.copy()


def show_session_end_card(session_summary):
    """Display a session summary end card similar to agent interaction summary."""
    if not session_summary:
        return

    from datetime import datetime

    # Calculate duration display
    duration_mins = session_summary.get("duration_minutes", 0)
    if duration_mins < 60:
        duration_display = f"{duration_mins:.1f}m"
    else:
        hours = int(duration_mins // 60)
        mins = int(duration_mins % 60)
        duration_display = f"{hours}h {mins}m"

    # Build activities summary
    activities = []
    if session_summary.get("quizzes_taken", 0) > 0:
        activities.append(f"Quizzes: {session_summary['quizzes_taken']}")
    if session_summary.get("notes_viewed", 0) > 0:
        activities.append(f"Notes: {session_summary['notes_viewed']}")
    if session_summary.get("ai_chats", 0) > 0:
        activities.append(f"AI Chats: {session_summary['ai_chats']}")
    if session_summary.get("verse_sessions", 0) > 0:
        activities.append(f"Verse: {session_summary['verse_sessions']}")
    if session_summary.get("tutorials_completed", 0) > 0:
        activities.append(f"Tutorials: {session_summary['tutorials_completed']}")

    activities_str = ", ".join(activities) if activities else "No activities recorded"

    # Session ID (shortened)
    session_id = session_summary.get("session_id", "N/A")
    session_id_short = session_id[:8] if len(session_id) > 8 else session_id

    # Resumed from
    resumed_from = session_summary.get("resumed_from")
    resumed_line = f"\n[dim]Resumed from: {resumed_from[:8] if resumed_from else 'N/A'}[/dim]" if resumed_from else ""

    # Start/end times
    start_time = session_summary.get("start_time", "N/A")
    end_time = session_summary.get("end_time", "N/A")

    card_content = (
        f"[bold green]🎓 Session Summary[/bold green]\n"
        f"[dim]{start_time} → {end_time}[/dim]\n"
        f"\n"
        f"[bold]Session ID:[/bold]     {session_id_short}\n"
        f"[bold]Duration:[/bold]        {duration_display}\n"
        f"[bold]Activities:[/bold]      {activities_str}{resumed_line}"
    )

    console.print(Panel(
        card_content,
        box=box.ROUNDED,
        border_style="green",
        padding=(1, 2),
    ))
    console.print()


def _get_theme_config_path():
    """Get path to theme configuration file"""
    # Try multiple locations
    theme_paths = [
        Path(__file__).parent.parent / "data" / "config" / "theme.json",
        Path(__file__).parent / "data" / "config" / "theme.json",
        Path.cwd() / "data" / "config" / "theme.json",
    ]
    for path in theme_paths:
        if path.exists():
            return path
    return None


def _get_settings_path():
    """Get path to user settings file"""
    from kslearn.loader import CONFIG_DIR
    settings_path = CONFIG_DIR / "settings.json"
    if settings_path.exists():
        return settings_path
    return None


def load_theme(theme_name=None):
    """Load theme colors from theme.json based on user settings or specified theme"""
    global COLORS
    
    # If no theme specified, try to load from settings
    if theme_name is None:
        settings_path = _get_settings_path()
        if settings_path and settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                theme_name = settings.get("theme", "sky_blue")
            except (json.JSONDecodeError, IOError):
                theme_name = "sky_blue"
        else:
            theme_name = "sky_blue"
    
    # Load theme from theme.json
    theme_config_path = _get_theme_config_path()
    if not theme_config_path or not theme_config_path.exists():
        COLORS = DEFAULT_COLORS.copy()
        return COLORS
    
    try:
        with open(theme_config_path, 'r', encoding='utf-8') as f:
            theme_config = json.load(f)
        
        themes = theme_config.get("themes", {})
        if theme_name in themes:
            theme = themes[theme_name]
            # Map theme colors to COLORS dict
            COLORS = {
                "primary": theme.get("primary", DEFAULT_COLORS["primary"]),
                "secondary": theme.get("secondary", DEFAULT_COLORS["secondary"]),
                "accent": theme.get("accent", DEFAULT_COLORS["accent"]),
                "danger": theme.get("danger", DEFAULT_COLORS["danger"]),
                "info": theme.get("info", DEFAULT_COLORS["info"]),
                "success": theme.get("success", DEFAULT_COLORS["success"]),
                "warning": theme.get("warning", DEFAULT_COLORS["warning"]),
                "muted": theme.get("muted", DEFAULT_COLORS["muted"]),
                "banner": theme.get("banner", DEFAULT_COLORS["banner"]),
                "border": theme.get("border", DEFAULT_COLORS["border"]),
                "header": theme.get("header", DEFAULT_COLORS["header"]),
                "menu_number": theme.get("menu_number", DEFAULT_COLORS["menu_number"]),
                "menu_text": theme.get("menu_text", DEFAULT_COLORS["menu_text"]),
                "table_header": theme.get("table_header", DEFAULT_COLORS["table_header"]),
                "panel_title": theme.get("panel_title", DEFAULT_COLORS["panel_title"]),
            }
        else:
            COLORS = DEFAULT_COLORS.copy()
    except (json.JSONDecodeError, IOError, KeyError):
        COLORS = DEFAULT_COLORS.copy()
    
    return COLORS


def get_available_themes():
    """Get list of available themes from theme.json"""
    theme_config_path = _get_theme_config_path()
    if not theme_config_path or not theme_config_path.exists():
        return ["sky_blue", "green", "grey"]
    
    try:
        with open(theme_config_path, 'r', encoding='utf-8') as f:
            theme_config = json.load(f)
        themes = theme_config.get("themes", {})
        return list(themes.keys())
    except (json.JSONDecodeError, IOError):
        return ["sky_blue", "green", "grey"]


def get_theme_info(theme_name=None):
    """Get theme name and display info"""
    if theme_name is None:
        settings_path = _get_settings_path()
        if settings_path and settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                theme_name = settings.get("theme", "sky_blue")
            except (json.JSONDecodeError, IOError):
                theme_name = "sky_blue"
        else:
            theme_name = "sky_blue"
    
    theme_config_path = _get_theme_config_path()
    if theme_config_path and theme_config_path.exists():
        try:
            with open(theme_config_path, 'r', encoding='utf-8') as f:
                theme_config = json.load(f)
            themes = theme_config.get("themes", {})
            if theme_name in themes:
                return themes[theme_name].get("name", theme_name)
        except (json.JSONDecodeError, IOError):
            pass
    
    return theme_name


def reload_theme():
    """Force reload theme from settings. Call this after user changes theme."""
    global COLORS
    # Reset to defaults first so stale colors don't persist
    COLORS = DEFAULT_COLORS.copy()
    return load_theme()

# Load theme on module import
load_theme()


def clear_screen():
    """Clear terminal screen - cross-platform compatible."""
    import sys
    import os
    try:
        if sys.platform == "win32":
            os.system("cls")
        else:
            # Use ANSI escape for better compatibility on Unix-like systems
            print("\033[2J\033[H", end="")
    except Exception:
        # Last resort fallback
        try:
            os.system("cls" if os.name == "nt" else "clear")
        except Exception:
            pass
    console.file.flush()


def get_banner() -> Panel:
    """Return the kslearn banner panel with ASCII art"""
    banner_color = COLORS.get("banner", "bright_cyan")
    primary_color = COLORS.get("primary", "cyan")
    accent_color = COLORS.get("accent", "yellow")
    border_color = COLORS.get("border", "cyan")
    
    banner_text = Text.assemble(
        (f"██╗  ██╗███████╗██╗     ███████╗ █████╗ ██████╗ ███╗   ██╗\n", banner_color),
        (f"██║ ██╔╝██╔════╝██║     ██╔════╝██╔══██╗██╔══██╗████╗  ██║\n", banner_color),
        (f"█████╔╝ ███████╗██║     █████╗  ███████║██████╔╝██╔██╗ ██║\n", banner_color),
        (f"██╔═██╗ ╚════██║██║     ██╔══╝  ██╔══██║██╔══██╗██║╚██╗██║\n", banner_color),
        (f"██║  ██╗███████║███████╗███████╗██║  ██║██║  ██║██║ ╚████║\n", banner_color),
        (f"╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝\n", banner_color),
        ("\n", ""),
        (f"📚 Learn Anything       |  ", COLORS.get("secondary", "green")),
        (f"v2.0.0 - Math, Science, Tech & More!\n", accent_color),
        (f"🚀 Works on: Termux • Linux • macOS • Windows", primary_color),
    )
    return Panel(
        banner_text,
        box=box.DOUBLE,
        border_style=border_color,
        padding=(1, 2),
    )


def get_small_banner() -> Panel:
    """Compact banner for sub-menus"""
    banner_color = COLORS.get("banner", "bright_cyan")
    border_color = COLORS.get("border", "cyan")
    
    return Panel(
        Text.assemble(
            (f"██╗  ██╗███████╗██╗     ███████╗ █████╗ ██████╗ ███╗   ██╗\n", banner_color),
            (f"██║ ██╔╝██╔════╝██║     ██╔════╝██╔══██╗██╔══██╗████╗  ██║\n", banner_color),
            (f"█████╔╝ ███████╗██║     █████╗  ███████║██████╔╝██╔██╗ ██║\n", banner_color),
            (f"██╔═██╗ ╚════██║██║     ██╔══╝  ██╔══██║██╔══██╗██║╚██╗██║\n", banner_color),
            (f"██║  ██╗███████║███████╗███████╗██║  ██║██║  ██║██║ ╚████║\n", banner_color),
            (f"╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝\n", banner_color),
        ),
        box=box.ROUNDED,
        border_style=border_color,
        padding=(0, 1),
    )


def show_panel(title: str, content: str, style: str = None):
    """Show a styled panel with title and content"""
    if style is None:
        style = COLORS.get("primary", "cyan")
    panel_title_style = COLORS.get("panel_title", f"bold {style}")
    border_style = COLORS.get("border", style)
    
    panel = Panel(
        content,
        title=f"[{panel_title_style}]{title}[/{panel_title_style}]",
        border_style=border_style,
        box=ROUNDED,
    )
    console.print(panel)


def show_success(message: str):
    """Show success message"""
    success_color = COLORS.get("success", "bright_green")
    console.print(f"[bold {success_color}]✓[/bold {success_color}] {message}")


def show_error(message: str):
    """Show error message"""
    danger_color = COLORS.get("danger", "red")
    console.print(f"[bold {danger_color}]✗[/bold {danger_color}] {message}")


def show_warning(message: str):
    """Show warning message"""
    warning_color = COLORS.get("warning", "yellow")
    console.print(f"[bold {warning_color}]![/bold {warning_color}] {message}")


def show_info(message: str):
    """Show info message"""
    info_color = COLORS.get("info", "blue")
    console.print(f"[bold {info_color}]●[/bold {info_color}] {message}")


class LoadingSpinner:
    """Context manager for loading spinner"""

    def __init__(self, message: str = "Loading..."):
        self.message = message
        spinner_style = COLORS.get("primary", "cyan")
        self.spinner = Spinner("dots", style=spinner_style)
        self.text = Text(f" {message}", style=spinner_style)

    def __enter__(self):
        self.live = Live(
            self.spinner,
            console=console,
            transient=True,
        )
        self.live.start()
        return self

    def __exit__(self, *args):
        self.live.stop()
        success_color = COLORS.get("success", "bright_green")
        console.print(f"[bold {success_color}]✓[/bold {success_color}] [{success_color}]{self.message}[/{success_color}]")


def create_progress():
    """Create a progress bar for loading"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


def create_menu_table(options: list, title: str = "Menu") -> Table:
    """Create a styled menu table"""
    primary_color = COLORS.get("primary", "cyan")
    border_color = COLORS.get("border", "cyan")
    header_style = COLORS.get("header", "bold cyan")
    muted_style = COLORS.get("muted", "dim")
    
    table = Table(
        title=title,
        box=ROUNDED,
        border_style=border_color,
        header_style=header_style,
        show_header=True,
        show_lines=True,
    )

    table.add_column("#", style=primary_color, width=4, justify="center")
    table.add_column("Option", style=primary_color, ratio=1)
    table.add_column("Description", style=muted_style, ratio=2)

    for idx, (name, desc) in enumerate(options, 1):
        table.add_row(str(idx), name, desc)

    return table


def create_study_grid(activities: list) -> Table:
    """Create a 2-column study activity grid"""
    primary_color = COLORS.get("primary", "cyan")
    border_color = COLORS.get("border", "cyan")

    table = Table(
        box=ROUNDED,
        border_style=border_color,
        show_header=False,
        expand=True,
    )

    table.add_column("Activity", style=primary_color, ratio=1)
    table.add_column("Activity", style=primary_color, ratio=1)

    # Pad with empty string if odd number
    if len(activities) % 2 == 1:
        activities = activities + [""]

    for i in range(0, len(activities), 2):
        num_style = primary_color
        num1 = f"[{num_style}]{i+1:02d}[/{num_style}]"
        num2 = f"[{num_style}]{i+2:02d}[/{num_style}]" if i+1 < len(activities) else ""
        item1 = f"{num1} {activities[i]}" if activities[i] else ""
        item2 = f"{num2} {activities[i+1]}" if i+1 < len(activities) and activities[i+1] else ""
        table.add_row(item1, item2)

    return table


def show_quiz_header(topic: str, question_num: int, total: int):
    """Show quiz question header"""
    panel = Panel(
        Text.assemble(
            (f"Question {question_num}/{total}", COLORS.get("header", "bold cyan")),
            ("\n\n", ""),
            (topic, COLORS.get("accent", "yellow")),
        ),
        box=ROUNDED,
        border_style=COLORS.get("border", "cyan"),
        padding=(1, 2),
    )
    console.print(panel)


def show_result_panel(score: int, total: int, topic: str = "Quiz"):
    """Show quiz results"""
    percentage = (score / total) * 100

    if percentage >= 80:
        style = COLORS.get("success", "bright_green")
        emoji = "🎉"
        message = "Excellent!"
    elif percentage >= 60:
        style = COLORS.get("warning", "yellow")
        emoji = "👍"
        message = "Good job!"
    else:
        style = "orange1"
        emoji = "📚"
        message = "Keep learning!"

    result_text = Text.assemble(
        (f"{emoji} {message}\n\n", style),
        ("Topic: ", COLORS.get("muted", "dim")),
        (f"{topic}\n", COLORS.get("menu_text", "white")),
        ("Score: ", COLORS.get("muted", "dim")),
        (f"{score}/{total}", f"bold {COLORS.get('primary', 'cyan')}"),
        (" (", COLORS.get("muted", "dim")),
        (f"{percentage:.0f}%", style),
        (")", COLORS.get("muted", "dim")),
    )

    panel = Panel(
        result_text,
        box=ROUNDED,
        border_style=style,
        padding=(1, 2),
    )
    console.print(panel)


def print_divider(text: str = "", style: str = "dim"):
    """Print a styled divider"""
    if text:
        console.print(f"[{style}]{'─' * 40} {text} {'─' * 40}[/{style}]")
    else:
        console.print(f"[{style}]{'─' * 40}[/{style}]")


def prompt_choice(prompt_text: str, options: list) -> int:
    """Show numbered options and get user choice"""
    console.print()
    primary_color = COLORS.get("primary", "cyan")
    for i, opt in enumerate(options, 1):
        console.print(f"  [{primary_color}]{i:02d}[/{primary_color}] {opt}")
    console.print()

    while True:
        try:
            choice = console.input(f"[bold {primary_color}]{prompt_text}[/bold {primary_color}] ")
            choice_num = int(choice.strip())
            if 1 <= choice_num <= len(options):
                return choice_num
            danger_color = COLORS.get("danger", "red")
            console.print(f"[bold {danger_color}]Invalid option. Please try again.[/bold {danger_color}]")
        except ValueError:
            danger_color = COLORS.get("danger", "red")
            console.print(f"[bold {danger_color}]Please enter a number.[/bold {danger_color}]")
        except KeyboardInterrupt:
            warning_color = COLORS.get("warning", "yellow")
            console.print(f"\n[{warning_color}]Cancelled.[/{warning_color}]")
            return 0


def prompt_text(prompt_text: str, default: str = "") -> str:
    """Get text input with optional default"""
    prompt_color = COLORS.get("success", "bright_green")
    muted_style = COLORS.get("muted", "dim")
    
    if default:
        prompt = f"[bold {prompt_color}]{prompt_text}[/bold {prompt_color}] [{muted_style}](default: {default})[/{muted_style}]: "
    else:
        prompt = f"[bold {prompt_color}]{prompt_text}[/bold {prompt_color}]: "

    try:
        result = console.input(prompt).strip()
        return result if result else default
    except KeyboardInterrupt:
        warning_color = COLORS.get("warning", "yellow")
        console.print(f"\n[{warning_color}]Cancelled.[/{warning_color}]")
        return default


def prompt_confirm(prompt_text: str, default: bool = True) -> bool:
    """Get yes/no confirmation"""
    default_str = "Y/n" if default else "y/N"
    prompt_color = COLORS.get("success", "bright_green")
    
    try:
        result = console.input(f"[bold {prompt_color}]{prompt_text}[/bold {prompt_color}] [{default_str}]: ").strip().lower()
        if not result:
            return default
        return result in ("y", "yes")
    except KeyboardInterrupt:
        warning_color = COLORS.get("warning", "yellow")
        console.print(f"\n[{warning_color}]Cancelled.[/{warning_color}]")
        return False


def show_achievement(name: str, description: str, icon: str = "🏆"):
    """Show achievement unlocked notification"""
    panel = Panel(
        Text.assemble(
            (f"{icon} ACHIEVEMENT UNLOCKED!\n\n", f"bold {COLORS.get('accent', 'bright_yellow')}"),
            (f"{name}\n", f"bold {COLORS.get('primary', 'cyan')}"),
            (description, COLORS.get("muted", "dim")),
        ),
        box=box.DOUBLE,
        border_style=COLORS.get("accent", "bright_yellow"),
        padding=(1, 2),
    )
    console.print(panel)


def show_hint(hint_text: str, remaining: int):
    """Show hint with remaining count"""
    warning_color = COLORS.get("warning", "yellow")
    muted_style = COLORS.get("muted", "dim")
    
    console.print()
    console.print(Panel(
        Text.assemble(
            ("💡 HINT: ", f"bold {warning_color}"),
            (hint_text, warning_color),
            ("\n\n", ""),
            (f"Hints remaining: {remaining}", muted_style),
        ),
        box=box.ROUNDED,
        border_style=warning_color,
        padding=(1, 2),
    ))


def show_streak(count: int):
    """Show streak bonus notification"""
    if count >= 10:
        emoji = "🔥"
        text = "ON FIRE!"
    elif count >= 5:
        emoji = "⭐"
        text = "On a roll!"
    elif count >= 3:
        emoji = "✨"
        text = "Great streak!"
    else:
        return

    console.print(f"  [{emoji}] {text} [{count}x streak bonus!]", style="bold bright_yellow")


def show_timer(seconds: int):
    """Show countdown timer"""
    minutes = seconds // 60
    secs = seconds % 60
    console.print(f"  [dim]Time: {minutes:02d}:{secs:02d}[/dim]", end="\r")


def show_daily_challenge_info(topic: str, day: str):
    """Show daily challenge header"""
    banner_color = COLORS.get("banner", "bright_cyan")
    muted_style = COLORS.get("muted", "dim")
    menu_txt = COLORS.get("menu_text", "white")
    accent_color = COLORS.get("accent", "bright_yellow")
    secondary_color = COLORS.get("secondary", "green")
    border_color = COLORS.get("border", "cyan")
    
    panel = Panel(
        Text.assemble(
            ("📅 DAILY CHALLENGE\n\n", f"bold {banner_color}"),
            ("Date: ", muted_style),
            (f"{day}\n", menu_txt),
            ("Topic: ", muted_style),
            (f"{topic}\n", accent_color),
            ("\nComplete today's challenge for bonus points!", secondary_color),
        ),
        box=box.DOUBLE,
        border_style=border_color,
        padding=(1, 2),
    )
    console.print(panel)


def show_stats_table(stats: dict):
    """Show player statistics in a table"""
    primary_color = COLORS.get("primary", "cyan")
    border_color = COLORS.get("border", "cyan")
    muted_style = COLORS.get("muted", "dim")
    
    table = Table(
        title="📊 Your Statistics",
        box=box.ROUNDED,
        border_style=border_color,
        show_header=True,
    )
    table.add_column("Category", style=primary_color)
    table.add_column("Played", style=primary_color, justify="center")
    table.add_column("Correct", style=primary_color, justify="center")
    table.add_column("Accuracy", style=primary_color, justify="center")
    table.add_column("Best Streak", style=primary_color, justify="center")

    for category, data in stats.items():
        accuracy = f"{data['accuracy']:.0f}%" if data['played'] > 0 else "N/A"
        table.add_row(
            category,
            str(data['played']),
            str(data['correct']),
            accuracy,
            str(data.get('best_streak', 0)),
        )

    console.print(table)


def show_hard_mode_warning():
    """Show warning for hard mode"""
    danger_color = COLORS.get("danger", "red")
    menu_txt = COLORS.get("menu_text", "white")
    accent_color = COLORS.get("accent", "bright_yellow")
    
    panel = Panel(
        Text.assemble(
            ("⚠️  HARD MODE ENABLED\n\n", f"bold {danger_color}"),
            ("Questions will be more challenging.\n", menu_txt),
            ("Bonus points for correct answers!", accent_color),
        ),
        box=box.ROUNDED,
        border_style=danger_color,
        padding=(1, 2),
    )
    console.print(panel)
