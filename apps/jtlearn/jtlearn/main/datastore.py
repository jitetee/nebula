#!/usr/bin/env python3
"""
Data Store - Download learning content from URLs or Official jtlearn Store
Download notes, quizzes, or snippets from links and install them automatically
"""

import os
import sys
import json
import time
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from jtlearn._rich.panel import Panel
from jtlearn._rich.table import Table
from jtlearn._rich import box
from jtlearn._rich.prompt import Prompt, Confirm

from jtlearn.ui import console, clear_screen, show_panel, show_success, show_error, show_info, show_warning, print_divider
from jtlearn.loader import JIF_DIR, CONFIG_DIR, DATA_DIR


class DataStore:
    """Download and manage learning content from URLs"""

    def __init__(self):
        self.download_dir = DATA_DIR / "downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.datastore_file = CONFIG_DIR / "datastore.json"

    def load_datastore(self) -> Dict:
        """Load official datastore catalog"""
        if self.datastore_file.exists():
            try:
                with open(self.datastore_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return self._online_catalog()

    def _online_catalog(self) -> Dict:
        """The JIF Store from the community database (public read, no login). Empty catalog if offline."""
        empty = {"categories": {"free": {"items": []}, "premium": {"items": []}}}
        try:
            import urllib.request
            from jtlearn.firebase_config import FIREBASE_RTDB_URL
            if not FIREBASE_RTDB_URL:
                return empty
            def get(path):
                with urllib.request.urlopen(f"{FIREBASE_RTDB_URL.rstrip('/')}/{path}.json", timeout=8) as r:
                    return json.loads(r.read().decode("utf-8") or "null")
            store = get("jifStore") or {}
            try:
                ratings = get("jifRatings") or {}
            except Exception:
                ratings = {}
        except Exception:
            return empty
        rows = []
        for key, it in store.items():
            if key.startswith("_") or not isinstance(it, dict) or not it.get("title") or not it.get("link"):
                continue
            votes = [v.get("rating") for v in (ratings.get(key) or {}).values() if isinstance(v, dict) and isinstance(v.get("rating"), (int, float))]
            rows.append({
                "id": key, "title": it.get("title", ""), "description": it.get("description", ""), "url": it.get("link", ""),
                "topics": [t.strip() for t in str(it.get("tags", "")).split(",") if t.strip()], "estimated_time": it.get("size") or "-",
                "rating": round(sum(votes) / len(votes), 1) if votes else 0, "price": it.get("price", ""), "features": [it.get("category", "")] if it.get("category") else [],
                "paid": it.get("type") == "paid", "ts": it.get("ts", 0),
            })
        rows.sort(key=lambda r: r["ts"], reverse=True)
        return {"categories": {"free": {"items": [r for r in rows if not r["paid"]]}, "premium": {"items": [r for r in rows if r["paid"]]}}}

    def download_file(self, url: str, filename: str = None) -> Optional[Path]:
        """Download file from URL"""
        try:
            import urllib.request

            if not filename:
                filename = url.split('/')[-1].split('?')[0]

            filepath = self.download_dir / filename

            console.print()
            console.print(Panel(
                f"[dim]Downloading: {url}[/dim]\n[cyan]Saving to: {filepath}[/cyan]",
                box=box.ROUNDED,
                border_style="cyan",
                title="📥 Downloading",
            ))
            console.print()

            # Download with progress
            def report_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(100, (downloaded / total_size) * 100)
                    bar = "█" * int(percent / 10) + "░" * (10 - int(percent / 10))
                    console.print(f"\r  Progress: [{bar}] {percent:.1f}%", end="")

            urllib.request.urlretrieve(url, filepath, reporthook=report_progress)
            console.print()  # Newline after progress

            return filepath

        except Exception as e:
            show_error(f"Download failed: {e}")
            return None

    def detect_content_type(self, filepath: Path) -> str:
        """Detect if file is notes, quiz, or snippets"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check structure
            if "topics" in data and "metadata" in data:
                return "notes"
            elif "questions" in data:
                return "quiz"
            elif "snippets" in data:
                return "snippets"
            else:
                return "unknown"

        except:
            return "unknown"

    def install_file(self, filepath: Path, content_type: str = None) -> bool:
        """Install downloaded file to correct directory"""
        try:
            # A .jif package (binary header + JSON): check it and copy it into data/jif as it is
            with open(filepath, 'rb') as f:
                head = f.read(4)
            if head == b"JIF\x01" or str(filepath).lower().endswith(".jif"):
                from jtlearn.jif_loader import load_jif_file, get_jif_info
                info, payload = get_jif_info(filepath), load_jif_file(filepath)
                if not info or payload is None:
                    show_error("That file is not a valid .jif package.")
                    return False
                JIF_DIR.mkdir(parents=True, exist_ok=True)
                dest_file = JIF_DIR / (Path(filepath).stem + ".jif")
                if dest_file.exists():
                    shutil.copy2(dest_file, str(dest_file) + ".bak")
                shutil.copy2(filepath, dest_file)
                show_success(f"Installed {info.get('title') or dest_file.stem} ({info.get('type')}) → {dest_file.name}")
                return True

            # Validate JSON
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Auto-detect type if not specified
            if not content_type or content_type == "auto":
                content_type = self.detect_content_type(filepath)

            # Determine destination (all .jif content goes to JIF_DIR)
            if content_type == "notes":
                dest_dir = JIF_DIR
                category = data.get("metadata", {}).get("category", filepath.stem)
            elif content_type == "quiz":
                dest_dir = JIF_DIR
                category = data.get("metadata", {}).get("category", filepath.stem)
            elif content_type == "snippets":
                dest_dir = JIF_DIR
                category = data.get("metadata", {}).get("category", filepath.stem)
            else:
                show_warning("Unknown content type. Please specify manually.")
                return False

            # Ensure destination exists
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Copy file
            dest_file = dest_dir / f"{category}.json"

            # Backup existing file
            if dest_file.exists():
                backup_file = dest_dir / f"{category}.backup.json"
                shutil.copy2(dest_file, backup_file)
                console.print(Panel(
                    f"[dim]Backed up existing file to: {backup_file}[/dim]",
                    box=box.ROUNDED,
                    border_style="yellow",
                ))

            shutil.copy2(filepath, dest_file)

            console.print(Panel(
                f"[green]✓ Installed successfully![/green]\n"
                f"[cyan]Type:[/cyan] {content_type}\n"
                f"[cyan]Category:[/cyan] {category}\n"
                f"[cyan]Location:[/cyan] {dest_file}",
                box=box.ROUNDED,
                border_style="green",
                title="✅ Installation Complete",
            ))

            return True

        except json.JSONDecodeError as e:
            show_error(f"Invalid JSON file: {e}")
            return False
        except Exception as e:
            show_error(f"Installation failed: {e}")
            return False

    def extract_zip(self, zippath: Path) -> List[Path]:
        """Extract ZIP file and return JSON files found"""
        try:
            extract_dir = self.download_dir / zippath.stem
            extract_dir.mkdir(parents=True, exist_ok=True)

            console.print()
            console.print(Panel(
                f"[dim]Extracting: {zippath}[/dim]\n[cyan]To: {extract_dir}[/cyan]",
                box=box.ROUNDED,
                border_style="cyan",
                title="📦 Extracting ZIP",
            ))

            with zipfile.ZipFile(zippath, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find all JSON files
            json_files = list(extract_dir.rglob("*.json"))

            if json_files:
                console.print(Panel(
                    f"[green]✓ Extracted {len(json_files)} JSON file(s)[/green]",
                    box=box.ROUNDED,
                    border_style="green",
                ))
            else:
                show_warning("No JSON files found in ZIP")

            return json_files

        except zipfile.BadZipFile:
            show_error("Invalid or corrupted ZIP file")
            return []
        except Exception as e:
            show_error(f"Extraction failed: {e}")
            return []

    def download_from_url(self, url: str, content_type: str = "auto"):
        """Main download workflow"""
        console.clear()
        console.print()

        show_panel("📥 Download Content", "Install learning materials from URL", "cyan")
        console.print()

        # Download
        filepath = self.download_file(url)
        if not filepath:
            return

        # Check if ZIP
        if filepath.suffix.lower() == '.zip':
            json_files = self.extract_zip(filepath)

            if not json_files:
                show_warning("No JSON files found in ZIP. Please extract manually.")
                console.print(f"\n[dim]Extracted to: {filepath.parent / filepath.stem}[/dim]")
                console.input("\nPress Enter to continue...")
                return

            # Install each JSON file
            for json_file in json_files:
                console.print()
                console.print(f"[bold]Installing: {json_file.name}[/bold]")
                self.install_file(json_file, content_type)
                time.sleep(1)

            console.print()
            console.print(Panel(
                "[green]✓ All files installed![/green]",
                box=box.ROUNDED,
                border_style="green",
            ))

        else:
            # Install single file
            self.install_file(filepath, content_type)

        console.input("\nPress Enter to continue...")


def show_datastore_catalog():
    """Display official jtlearn Data Store catalog"""
    store = DataStore()
    catalog = store.load_datastore()

    while True:
        console.clear()
        console.print()

        # Header
        console.print(Panel(
            "[bold cyan]🏪 JIF Store[/bold cyan]\n"
            "[dim]Lesson packages (.jif) from the community[/dim]\n"
            "[green]💝 Support jtlearn while learning![/green]",
            box=box.ROUNDED,
            border_style="cyan",
            title="📚",
        ))
        console.print()

        # Free Content
        free_items = catalog.get("categories", {}).get("free", {}).get("items", [])
        if free_items:
            console.print("[bold green]🆓 FREE CONTENT[/bold green]\n")

            free_table = Table(
                box=box.ROUNDED,
                border_style="green",
                show_header=True,
                expand=True,
            )
            free_table.add_column("#", style="yellow", width=4)
            free_table.add_column("Content", style="bold white")
            free_table.add_column("Topics", style="dim")
            free_table.add_column("Time", style="cyan")
            free_table.add_column("⭐", style="yellow", width=5)

            for i, item in enumerate(free_items, 1):
                topics = ", ".join(item.get("topics", [])[:3])
                if len(item.get("topics", [])) > 3:
                    topics += "..."
                free_table.add_row(
                    str(i),
                    f"{item.get('title', 'Unknown')}\n[dim]{item.get('description', '')[:50]}[/dim]",
                    topics,
                    item.get("estimated_time", "?"),
                    f"⭐ {item.get('rating', 0)}"
                )

            console.print(free_table)
            console.print()

        # Premium Content
        premium_items = catalog.get("categories", {}).get("premium", {}).get("items", [])
        if premium_items:
            console.print("[bold magenta]💎 PREMIUM CONTENT[/bold magenta]\n")

            prem_table = Table(
                box=box.ROUNDED,
                border_style="magenta",
                show_header=True,
                expand=True,
            )
            prem_table.add_column("#", style="yellow", width=4)
            prem_table.add_column("Content", style="bold white")
            prem_table.add_column("Features", style="dim")
            prem_table.add_column("Price", style="green", width=10)
            prem_table.add_column("⭐", style="yellow", width=5)

            for i, item in enumerate(premium_items, 1):
                features = "\n".join(item.get("features", [])[:2])
                price = f"${item.get('price', 0)}"
                prem_table.add_row(
                    str(i),
                    f"{item.get('title', 'Unknown')}\n[dim]{item.get('description', '')[:40]}[/dim]",
                    features,
                    f"[bold green]{price}[/bold green]",
                    f"⭐ {item.get('rating', 0)}"
                )

            console.print(prem_table)
            console.print()

        # Bundles
        bundles = catalog.get("bundles", {})
        if bundles:
            console.print("[bold cyan]📦 SPECIAL BUNDLES[/bold cyan]\n")

            for key, bundle in bundles.items():
                console.print(Panel(
                    f"[bold white]{bundle.get('name', '')}[/bold white]\n"
                    f"[dim]{bundle.get('description', '')}[/dim]\n\n"
                    f"[green]Price: ${bundle.get('price', 0)} ({bundle.get('billing', 'one-time')})[/green]\n"
                    f"[cyan]{bundle.get('savings', '')}[/cyan]",
                    box=box.ROUNDED,
                    border_style="cyan",
                ))
                console.print()

        if not free_items and not premium_items:
            console.print("[yellow]The store is empty or you are offline. You can still paste a link with [U].[/yellow]\n")

        # Actions
        console.print("  [green][1-9][/green] [dim]Download free content[/dim]")
        console.print("  [magenta][P1-9][/magenta] [dim]Get premium content[/dim]")
        console.print("  [cyan]\\[B][/cyan] [dim]View bundles[/dim]")
        console.print("  [yellow]\\[U][/yellow] [dim]Paste custom URL[/dim]")
        console.print("  [blue]\\[W][/blue] [dim]Open the JIF Store website (submit your own)[/dim]")
        console.print("  [green][0][/green] [dim]Back to Main Menu[/dim]")
        console.print()

        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().lower()

        if choice == "0":
            return
        elif choice == "w":
            site = "https://jitetee-ke.web.app/jif"
            try:
                import webbrowser
                webbrowser.open(site)
            except Exception:
                pass
            console.print(f"[dim]{site}[/dim]")
            time.sleep(1.5)
        elif choice == "u":
            # Custom URL download
            url = console.input("[bold green]╰─► Paste URL:[/bold green] ").strip()
            if url.startswith(('http://', 'https://')):
                store.download_from_url(url, "auto")
            else:
                show_warning("Invalid URL")
                time.sleep(1)
        elif choice.startswith("p"):
            # Premium content
            try:
                idx = int(choice[1:]) - 1
                if 0 <= idx < len(premium_items):
                    item = premium_items[idx]
                    console.print()
                    console.print(Panel(
                        f"[bold]{item.get('title', '')}[/bold]\n\n"
                        f"[cyan]Price:[/cyan] ${item.get('price', 0)}\n"
                        f"[cyan]URL:[/cyan] [blue underline]{item.get('url', '')}[/blue underline]\n\n"
                        "[dim]Opening in browser...[/dim]",
                        box=box.ROUNDED,
                        border_style="magenta",
                    ))
                    import webbrowser
                    webbrowser.open(item.get('url', ''))
                    time.sleep(2)
            except (ValueError, IndexError):
                pass
        elif choice.isdigit():
            # Free content
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(free_items):
                    item = free_items[idx]
                    url = item.get('url', '')
                    if url:
                        console.print(Panel(
                            f"[green]Downloading: {item.get('title', '')}[/green]",
                            box=box.ROUNDED,
                            border_style="green",
                        ))
                        store.download_from_url(url, "auto")
            except (ValueError, IndexError):
                pass
        elif choice == "b":
            # Show bundles
            console.print()
            for key, bundle in bundles.items():
                console.print(Panel(
                    f"[bold]{bundle.get('name', '')}[/bold]\n"
                    f"{bundle.get('description', '')}\n\n"
                    f"[green]${bundle.get('price', 0)} - {bundle.get('billing', 'one-time')}[/green]\n\n"
                    f"[cyan]Features:[/cyan]\n" +
                    "\n".join([f"  ✓ {f}" for f in bundle.get('features', [])]) +
                    f"\n\n[blue underline]{bundle.get('url', '')}[/blue underline]",
                    box=box.ROUNDED,
                    border_style="cyan",
                ))
                console.print()
            console.input("[bold green]╰─► Press Enter to continue...[/bold green]")


def download_interactive():
    """Interactive download interface"""
    store = DataStore()

    while True:
        console.clear()
        console.print()

        show_panel("📥 Data Store", "Download & Install Learning Content", "cyan")
        console.print()

        # Info table
        info_table = Table(
            box=box.ROUNDED,
            border_style="cyan",
            show_header=True,
            expand=True,
        )
        info_table.add_column("Content Type", style="bold white")
        info_table.add_column("File Location", style="dim")
        info_table.add_column("Format", style="cyan")

        info_table.add_row("📦 .jif Packages", "data/jif/", ".jif files")
        info_table.add_row("📝 Quizzes", "data/jif/", ".jif files")
        info_table.add_row("🧠 Brain", "data/jif/", ".jif files")

        console.print(info_table)
        console.print()

        # Instructions
        console.print("[bold yellow]Supported Sources:[/bold yellow]")
        console.print("  • GitHub raw files")
        console.print("  • Direct JSON/ZIP links")
        console.print("  • Any URL serving JSON/ZIP files")
        console.print()

        console.print("[bold cyan]Examples:[/bold cyan]")
        console.print("  https://raw.githubusercontent.com/user/repo/main/data/jif/content.jif")
        console.print("  https://example.com/content/quiz-pack.zip")
        console.print()

        print_divider()
        console.print()

        # Get URL
        url = console.input("[bold green]╰─► Paste URL (or '0' to cancel):[/bold green] ").strip()

        if url.lower() in ['0', 'cancel', 'q']:
            return

        if not url.startswith(('http://', 'https://')):
            show_warning("URL must start with http:// or https://")
            time.sleep(2)
            continue

        # Get content type
        console.print()
        console.print("[bold]Content Type:[/bold]")
        console.print("  [1] Auto-detect (recommended)")
        console.print("  [2] Notes")
        console.print("  [3] Quiz")
        console.print("  [4] Snippets")
        console.print()

        type_choice = console.input("[bold green]╰─► Select type (1-4):[/bold green] ").strip()

        type_map = {
            '1': 'auto',
            '2': 'notes',
            '3': 'quiz',
            '4': 'snippets',
        }
        content_type = type_map.get(type_choice, 'auto')

        # Download and install
        store.download_from_url(url, content_type)


def main():
    """Main entry point - show catalog by default"""
    show_datastore_catalog()


if __name__ == "__main__":
    main()
