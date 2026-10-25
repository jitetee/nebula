#!/usr/bin/env python3
"""Support jtlearn - Donations, Social Media, and Credits"""

import os
import sys
import time
import subprocess
from typing import Dict, List

from jtlearn._rich.console import Console
from jtlearn._rich.panel import Panel
from jtlearn._rich.table import Table
from jtlearn._rich.rule import Rule
from jtlearn._rich import box

from jtlearn.ui import console, clear_screen, show_panel, show_success, show_info


def open_url(url: str) -> bool:
    """Open a URL in the device's default browser (cross-platform).

    Detects the OS and uses the appropriate method:
    - Android/Termux: am start intent or termux-open-url
    - Linux: xdg-open
    - macOS: open
    - Windows: start
    """
    platform = sys.platform.lower()

    def _is_android():
        """Detect Android/Termux environment."""
        return ("android" in platform or
                os.path.exists("/dev/socket/qemud") or
                os.environ.get("TERMUX_VERSION") is not None or
                os.path.exists("/data/data/com.termux"))

    # Android / Termux
    if _is_android():
        # Try termux-open-url first (termux-api package)
        try:
            result = subprocess.run(
                ["termux-open-url", url],
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback: Android am start intent via termux-ai or direct am
        try:
            subprocess.run(
                ["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # macOS
    elif platform == "darwin":
        subprocess.run(["open", url], timeout=10)
        return True

    # Windows
    elif platform == "win32" or platform == "cygwin":
        subprocess.run(["start", url], shell=True, timeout=10)
        return True

    # Linux (and fallback for most Unix-like systems)
    else:
        try:
            subprocess.run(["xdg-open", url], timeout=10)
            return True
        except FileNotFoundError:
            # Final fallback: Python's webbrowser module
            import webbrowser
            return webbrowser.open(url)

    # If all native methods failed, try webbrowser module
    import webbrowser
    return webbrowser.open(url)


# Social Media Links
SOCIAL_MEDIA = {
    "email": {
        "name": "Official Email",
        "url": "mailto:kashsight@gmail.com",
        "icon": "📧",
        "handle": "kashsight@gmail.com",
        "color": "red"
    },
    "website": {
        "name": "Official Website",
        "url": "https://kash-sight.web.app",
        "icon": "🌐",
        "handle": "kash-sight.web.app",
        "color": "cyan"
    },
    "github": {
        "name": "GitHub Repository",
        "url": "https://github.com/jitetee/nebula",
        "icon": "💻",
        "handle": "@kashsight",
        "color": "white"
    },
}

# Project Credits
PROJECT_INFO = {
    "name": "jtlearn",
    "version": "2.0.0",
    "tagline": "JSON-Powered Educational Learning System",
    "description": "Learn anything — math, science, psychology, religion, music, technology, and more. jtlearn combines comprehensive learning notes, interactive quizzes, and offline AI to help you truly understand any subject.",
    "license": "MIT License",
    "author": "KashSight Platform",
    "year": "2026",
    "website": "https://kash-sight.web.app",
    "email": "kashsight@gmail.com",
}

def show_credits():
    """Display project credits"""
    console.clear()
    console.print()
    
    # Main credits panel
    credits_content = f"""[bold cyan]{PROJECT_INFO['name']} v{PROJECT_INFO['version']}[/bold cyan]
[dim]{PROJECT_INFO['tagline']}[/dim]

[white]{PROJECT_INFO['description']}[/white]

[bold yellow]Created by:[/bold yellow] [cyan]{PROJECT_INFO['author']}[/cyan]
[bold yellow]License:[/bold yellow] [green]{PROJECT_INFO['license']}[/green]
[bold yellow]Year:[/bold yellow] [dim]{PROJECT_INFO['year']}[/dim]

[bold cyan]Website:[/bold cyan] [blue underline]{PROJECT_INFO['website']}[/blue underline]
[bold cyan]Email:[/bold cyan] [blue]{PROJECT_INFO['email']}[/blue]
"""
    
    console.print(Panel(
        credits_content,
        box=box.ROUNDED,
        border_style="cyan",
        title="📜 Project Credits",
        title_align="left",
    ))
    console.print()
    
    # Features table
    features_table = Table(
        box=box.ROUNDED,
        border_style="green",
        show_header=True,
        expand=True,
    )
    features_table.add_column("Feature", style="bold white")
    features_table.add_column("Description", style="dim")
    
    features_table.add_row("📚 Learning Notes", "Comprehensive study materials from JSON")
    features_table.add_row("📝 Interactive Quizzes", "Test your knowledge with auto-graded quizzes")
    features_table.add_row("🤖 Offline AI Chat", "Powered by tgpt (termux-ai)")
    features_table.add_row("🧠 Knowledge Brain", "100+ pre-loaded Q&A pairs")
    features_table.add_row("📊 Progress Tracking", "Track your learning journey")
    features_table.add_row("🎨 Modern UI", "Beautiful terminal interface with Rich")
    
    console.print(features_table)
    console.print()
    
    console.print(f"  [bold green][0][/bold green] [dim]Back[/dim]")
    console.print()
    
    console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

def show_support_menu():
    """Display support and social media menu with modern UI"""
    while True:
        console.clear()
        console.print()

        # Header
        console.print(Panel(
            "[bold cyan]❤️ Support jtlearn[/bold cyan]\n[dim]Connect with us and help us keep learning free![/dim]",
            box=box.ROUNDED,
            border_style="cyan",
            title="💝",
            title_align="left",
        ))
        console.print()

        # Contact & Social Media Section
        console.print("[bold yellow]📢 Connect With Us:[/bold yellow]\n")

        social_table = Table(
            box=box.ROUNDED,
            border_style="blue",
            show_header=True,
            expand=True,
        )
        social_table.add_column("Platform", style="bold white", width=20)
        social_table.add_column("Handle", style="cyan", width=25)
        social_table.add_column("URL", style="dim")

        for key, info in SOCIAL_MEDIA.items():
            social_table.add_row(
                f"{info['icon']} {info['name']}",
                info.get('handle', '-'),
                info['url']
            )

        console.print(social_table)
        console.print()

        # Impact section
        impact_content = """[white]Your support helps us:[/white]
[green]✓[/green] Add new learning content
[green]✓[/green] Improve existing features
[green]✓[/green] Keep jtlearn free for everyone
[green]✓[/green] Support the open-source community"""

        console.print(Panel(
            impact_content,
            box=box.ROUNDED,
            border_style="yellow",
            title="🎯 Impact",
        ))
        console.print()

        # Actions
        actions_table = Table(
            box=None,
            show_header=False,
            expand=True,
            padding=(0, 1),
        )
        actions_table.add_column("Key", style="green")
        actions_table.add_column("Action", style="white")

        actions_table.add_row("[O]", "Open Link in Browser")
        actions_table.add_row("[C]", "Copy Links Info")
        actions_table.add_row("[V]", "View Project Credits")
        actions_table.add_row("[0]", "Back to Main Menu")

        console.print(actions_table)
        console.print()

        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().lower()

        if choice == "0":
            break
        elif choice == "o":
            open_link_menu()
        elif choice == "c":
            copy_links_info()
        elif choice == "v":
            show_credits()

def open_link_menu():
    """Menu to open specific links with modern UI"""
    while True:
        console.clear()
        console.print()

        console.print(Panel(
            "[bold cyan]Open Links[/bold cyan]\n[dim]Select a link to open in your browser[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
            title="🔗",
            title_align="left",
        ))
        console.print()

        # Contact & Social Links
        console.print("[bold yellow]Contact & Social:[/bold yellow]\n")

        social_table = Table(
            box=box.ROUNDED,
            border_style="blue",
            show_header=True,
        )
        social_table.add_column("#", style="yellow", width=4)
        social_table.add_column("Platform", style="bold white")
        social_table.add_column("URL", style="dim")

        social_keys = list(SOCIAL_MEDIA.keys())
        for i, key in enumerate(social_keys, 1):
            info = SOCIAL_MEDIA[key]
            social_table.add_row(
                str(i),
                f"{info['icon']} {info['name']}",
                info['url']
            )

        console.print(social_table)
        console.print()
        console.print(f"  [bold green][0][/bold green] [dim]Back[/dim]")
        console.print()

        choice = console.input("[bold green]╰─► Select to open:[/bold green] ").strip()

        if choice == "0":
            break

        try:
            choice_num = int(choice)
            total_options = len(social_keys)

            if 1 <= choice_num <= len(social_keys):
                key = social_keys[choice_num - 1]
                url = SOCIAL_MEDIA[key]["url"]
            else:
                console.print(Panel(
                    "[yellow]Invalid selection![/yellow]",
                    box=box.ROUNDED,
                    border_style="yellow",
                ))
                time.sleep(1)
                continue

            # Try to open in browser
            try:
                if open_url(url):
                    console.print(Panel(
                        f"[green]✓ Link opened in default browser![/green]\n[dim]{url}[/dim]",
                        box=box.ROUNDED,
                        border_style="green",
                    ))
                else:
                    raise RuntimeError("No browser found")
            except Exception:
                console.print(Panel(
                    "[yellow]Could not open browser. Copy the URL manually.[/yellow]",
                    box=box.ROUNDED,
                    border_style="yellow",
                ))

            time.sleep(2)

        except ValueError:
            pass

def copy_links_info():
    """Display all links for easy copying"""
    console.clear()
    console.print()

    console.print(Panel(
        "[bold cyan]All Links[/bold cyan]\n[dim]Long-press to select and copy URLs[/dim]",
        box=box.ROUNDED,
        border_style="cyan",
        title="📋",
        title_align="left",
    ))
    console.print()

    # Contact & Social Links
    console.print("[bold yellow]Contact & Social Links:[/bold yellow]\n")

    for key, info in SOCIAL_MEDIA.items():
        link_panel = f"""[bold white]{info['icon']} {info['name']}[/bold white]
[cyan]URL:[/cyan] [blue underline]{info['url']}[/blue underline]"""
        if info.get('handle'):
            link_panel += f"\n[cyan]Handle:[/cyan] [green]{info['handle']}[/green]"

        console.print(Panel(
            link_panel,
            box=box.ASCII,
            border_style="blue",
        ))

    console.print()

    console.print(Panel(
        "[green]💡 Tip:[/green] Long-press to select and copy URLs",
        box=box.ROUNDED,
        border_style="green",
    ))
    console.print()

    console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

def show_donation_message():
    """Show a brief support message"""
    console.print()
    console.print(Panel(
        """[bold yellow]💝 Love jtlearn? Support us![/bold yellow]

[white]Your support helps us:[/white]
[green]✓[/green] Add new learning content
[green]✓[/green] Improve existing features
[green]✓[/green] Keep jtlearn free for everyone

[bold cyan]Visit the Support menu to connect with us![/bold cyan]""",
        box=box.ROUNDED,
        border_style="yellow",
        title="❤️",
    ))
    console.print()

def main():
    """Main function for support menu"""
    try:
        show_support_menu()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted. Returning to menu...[/yellow]")

if __name__ == "__main__":
    main()
