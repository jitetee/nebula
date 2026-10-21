#!/usr/bin/env python3
"""
kslearn Online Mode - Terminal-based Online Features

Features:
- User authentication (signup/login)
- Friend system
- Global leaderboards
- Content sharing (worlds as JSON text in RTDB)
- Multiplayer KSL-Verse sessions
"""

import json
import time
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.prompt import Prompt, Confirm

from kslearn.ui import (
    console,
    get_small_banner,
    show_panel,
    show_error,
    show_info,
    show_success,
    show_warning,
    clear_screen,
    COLORS,
)
from kslearn.online.firebase_rtdb import get_firebase, FirebaseRTDB, read_password_masked


def run_online_mode():
    """Main online mode menu and entry point"""
    firebase = get_firebase()
    
    # Try to load existing session
    if not firebase.load_session():
        _show_login_menu(firebase)
    
    # Main online loop
    while firebase.is_logged_in():
        clear_screen()
        console.print(get_small_banner())
        console.print()
        show_panel("🌐 ksverse Online", f"Logged in as {firebase.user_data.get('username', 'User')}", "cyan")
        console.print()

        # Build online menu table
        tbl = Table(
            box=box.ROUNDED,
            border_style=COLORS.get("border", "cyan"),
            show_header=False,
            expand=True,
        )
        tbl.add_column("Option", style=COLORS.get("primary", "cyan"), ratio=1)
        tbl.add_column("Description", style=COLORS.get("muted", "dim"), ratio=2)

        # Get online friends count
        online_friends = firebase.get_online_friends()
        total_friends = len(firebase.get_friends())

        tbl.add_row("👤 1. My Profile", "View and edit your profile")
        tbl.add_row(f"👥 2. Friends ({len(online_friends)}/{total_friends} online)", "Manage friends list")
        tbl.add_row("🏆 3. Leaderboards", "Global XP and score rankings")
        tbl.add_row("🌍 4. Browse Worlds", "Online worlds (play virtually, no download)")
        tbl.add_row("🔍 5. Search World by ID", "Find a specific world")
        tbl.add_row("📤 6. Upload World", "Share your KSL-Verse worlds")
        tbl.add_row("📚 7. Sync Notes", "Upload/download notes to cloud")
        tbl.add_row("🎓 8. Sync Courses", "Upload/download courses to cloud")
        tbl.add_row("🎮 9. Multiplayer Verse", "Play KSL-Verse with friends")
        tbl.add_row("🕹️ 10. Open Sessions", "See available game sessions")
        tbl.add_row("⚙️ S. Settings", "Sync preferences and config")
        tbl.add_row("❌ L. Logout", "Return to offline mode")
        tbl.add_row("B. Back", "Back to main menu")

        console.print(tbl)
        console.print()

        try:
            prompt_color = COLORS.get("success", "bright_green")
            choice = console.input(f"[bold {prompt_color}]╰─► Your choice (1-10, S, L, B):[/bold {prompt_color}] ").strip().upper()

            if choice == "B" or choice == "BACK":
                break
            elif choice == "L" or choice == "LOGOUT":
                if Confirm.ask("Are you sure you want to logout?", default=False):
                    firebase.logout()
                    show_info("Logged out. You can login again anytime.")
                    break
            elif choice == "1":
                _show_profile(firebase)
            elif choice == "2":
                _manage_friends(firebase)
            elif choice == "3":
                _show_leaderboards(firebase)
            elif choice == "4":
                _browse_worlds(firebase)
            elif choice == "5":
                _search_world_by_id(firebase)
            elif choice == "6":
                _upload_world(firebase)
            elif choice == "7":
                _sync_notes(firebase)
            elif choice == "8":
                _sync_courses(firebase)
            elif choice == "9":
                _multiplayer_verse(firebase)
            elif choice == "10":
                _open_game_sessions(firebase)
            elif choice == "S" or choice == "SETTINGS":
                _online_settings(firebase)
            else:
                show_warning("Invalid option!")
                time.sleep(1)

        except KeyboardInterrupt:
            console.print("\n")
            show_info("Use 'B' to go back or 'L' to logout")
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break


def _show_login_menu(firebase: FirebaseRTDB):
    """Show login/signup menu"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🌐 Welcome to ksverse Online", "Connect with friends, compete globally, share worlds", "cyan")
    console.print()
    
    console.print("[bold white]Choose an option:[/bold white]\n")
    console.print("[green][1][/green] [dim]Login with email/password[/dim]")
    console.print("[green][2][/green] [dim]Create new account[/dim]")
    console.print("[green][3][/green] [dim]Continue as guest (limited features)[/dim]")
    console.print("[green][0][/green] [dim]Back to main menu[/dim]")
    console.print()
    
    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip()
        
        if choice == "0":
            return
        elif choice == "1":
            _login(firebase)
        elif choice == "2":
            _signup(firebase)
        elif choice == "3":
            firebase.login_anonymous()
        else:
            show_warning("Invalid option!")
            time.sleep(1)
    except (KeyboardInterrupt, EOFError):
        return


def _login(firebase: FirebaseRTDB):
    """Login with email/password"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🔐 Login to ksverse", "Enter your credentials", "cyan")
    console.print()

    try:
        email = Prompt.ask("Email").strip()
        password = read_password_masked("Password").strip()

        if not email or not password:
            show_error("Email and password required")
            return

        console.print()
        with console.status("[bold cyan]Logging in...", spinner="dots"):
            success = firebase.login(email, password)

        if success:
            # Auto-sync offline stats to Firebase (if enabled)
            sync_settings = firebase.get_sync_settings()
            console.print()
            
            if sync_settings.get("auto_sync_stats", True):
                with console.status("[bold cyan]Syncing offline stats...", spinner="dots"):
                    stats_ok = firebase.sync_offline_stats()
                if stats_ok:
                    console.print("[dim green]✓ Stats synced to cloud[/dim green]")
                else:
                    console.print("[dim yellow]⚠ Stats sync failed (will retry later)[/dim yellow]")
            
            if sync_settings.get("auto_sync_notes", True):
                with console.status("[bold cyan]Syncing notes...", spinner="dots"):
                    notes_ok = firebase.sync_notes_to_cloud()
                if notes_ok:
                    console.print("[dim green]✓ Notes synced to cloud[/dim green]")
            
            if sync_settings.get("auto_sync_courses", True):
                with console.status("[bold cyan]Syncing courses...", spinner="dots"):
                    courses_ok = firebase.sync_courses_to_cloud()
                if courses_ok:
                    console.print("[dim green]✓ Courses synced to cloud[/dim green]")
            
            console.input("\n[dim]Press Enter to continue...[/dim]")
        else:
            console.print()
            console.print("[yellow]Tip: Check your email and password[/yellow]")
            console.input("\n[dim]Press Enter to continue...[/dim]")

    except (KeyboardInterrupt, EOFError):
        return


def _signup(firebase: FirebaseRTDB):
    """Create new account"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("📝 Create ksverse Account", "Join the community!", "cyan")
    console.print()

    try:
        username = Prompt.ask("Username").strip()
        email = Prompt.ask("Email").strip()
        password = read_password_masked("Password").strip()
        confirm_password = read_password_masked("Confirm Password").strip()

        if not username or not email or not password:
            show_error("All fields are required")
            return

        if password != confirm_password:
            show_error("Passwords do not match")
            return

        if len(password) < 6:
            show_error("Password must be at least 6 characters")
            return

        console.print()
        with console.status("[bold cyan]Creating account...", spinner="dots"):
            success = firebase.signup(email, password, username)

        if success:
            # Auto-sync offline stats to Firebase
            console.print()
            with console.status("[bold cyan]Syncing offline stats...", spinner="dots"):
                sync_ok = firebase.sync_offline_stats()
            
            if sync_ok:
                console.print("[dim green]✓ Stats synced to cloud[/dim green]")
            
            console.input("\n[dim]Press Enter to continue...[/dim]")
        else:
            console.input("\n[dim]Press Enter to continue...[/dim]")

    except (KeyboardInterrupt, EOFError):
        return


def _show_profile(firebase: FirebaseRTDB):
    """Show user profile"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    
    profile = firebase.user_data
    
    # Calculate level from XP
    xp = profile.get("xp", 0)
    level = 1
    xp_needed = 200
    if xp >= 200:
        level = 2
        xp_needed = 500
    if xp >= 500:
        level = 3
        xp_needed = 1000
    if xp >= 1000:
        level = 5
        xp_needed = 2000
    if xp >= 2000:
        level = 7
        xp_needed = 5500
    if xp >= 5500:
        level = 10
    
    # Build profile panel
    profile_text = f"""
[dim]Username:[/dim] [bold white]{profile.get('username', 'Unknown')}[/bold white]
[dim]Email:[/dim] {profile.get('email', 'Guest')}
[dim]Level:[/dim] {level}
[dim]XP:[/dim] {xp} / {xp_needed}
[dim]Member since:[/dim] {profile.get('created_at', 'Unknown')[:10]}
[dim]Last seen:[/dim] {profile.get('last_seen', 'Unknown')[:19]}
"""
    
    console.print(Panel(profile_text, box=box.ROUNDED, border_style="cyan", title="👤 Your Profile"))
    console.print()
    
    console.print("[green][E][/green] [dim]Edit profile[/dim]")
    console.print("[green][B][/green] [dim]Back[/dim]")
    console.print()
    
    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()
        
        if choice == "E":
            _edit_profile(firebase)
    except (KeyboardInterrupt, EOFError):
        return


def _edit_profile(firebase: FirebaseRTDB):
    """Edit user profile"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("✏️ Edit Profile", "Update your information", "cyan")
    console.print()

    try:
        new_username = Prompt.ask("Username (leave blank to keep current)",
                                  default=firebase.user_data.get("username", "")).strip()

        updates = {}
        if new_username:
            updates["username"] = new_username

        if updates:
            success = firebase.update_profile(updates)
            if success:
                show_success("Profile updated!")
            else:
                show_error("Failed to update profile. Check your connection and try again.")
        else:
            show_info("No changes made")

        console.input("\n[dim]Press Enter to continue...[/dim]")

    except (KeyboardInterrupt, EOFError):
        return


def _manage_friends(firebase: FirebaseRTDB):
    """Manage friends list"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("👥 Friends", "Connect with other learners", "cyan")
    console.print()
    
    friends = firebase.get_friends()
    
    if not friends:
        console.print("[yellow]No friends yet. Add friends by their user ID![/yellow]\n")
    else:
        # Build friends table
        tbl = Table(box=box.ROUNDED, border_style="cyan")
        tbl.add_column("Status", width=8)
        tbl.add_column("Username", style="bold white")
        tbl.add_column("User ID", style="dim")
        tbl.add_column("Added", style="dim", width=12)
        
        for fid, fdata in friends.items():
            status = "🟢" if fdata.get("status") == "online" else "⚫"
            added = fdata.get("added_at", "")[:10]
            tbl.add_row(status, fdata.get("username", "Unknown"), fid[:12] + "...", added)
        
        console.print(tbl)
        console.print()
    
    console.print("[green][1][/green] [dim]Add friend by user ID[/dim]")
    console.print("[green][2][/green] [dim]Remove friend[/dim]")
    console.print("[green][B][/green] [dim]Back[/dim]")
    console.print()
    
    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()
        
        if choice == "1":
            friend_id = Prompt.ask("Enter friend's user ID").strip()
            if friend_id:
                with console.status("[bold cyan]Adding friend...", spinner="dots"):
                    firebase.add_friend(friend_id)
                console.input("\n[dim]Press Enter to continue...[/dim]")
        elif choice == "2":
            friend_id = Prompt.ask("Enter friend's user ID to remove").strip()
            if friend_id:
                firebase.remove_friend(friend_id)
            console.input("\n[dim]Press Enter to continue...[/dim]")
            
    except (KeyboardInterrupt, EOFError):
        return


def _show_leaderboards(firebase: FirebaseRTDB):
    """Show global leaderboards"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🏆 Global Leaderboards", "Top learners worldwide", "cyan")
    console.print()
    
    console.print("[green][1][/green] [dim]XP Leaderboard (All-time)[/dim]")
    console.print("[green][2][/green] [dim]Recent Scores[/dim]")
    console.print("[green][B][/green] [dim]Back[/dim]")
    console.print()
    
    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()
        
        if choice == "1":
            _show_xp_leaderboard(firebase)
        elif choice == "2":
            _show_scores_leaderboard(firebase)
            
    except (KeyboardInterrupt, EOFError):
        return


def _show_xp_leaderboard(firebase: FirebaseRTDB):
    """Show XP-based leaderboard"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🏆 XP Leaderboard", "All-time rankings", "cyan")
    console.print()
    
    with console.status("[bold cyan]Loading leaderboard...", spinner="dots"):
        leaderboard = firebase.get_xp_leaderboard(limit=20)
    
    if not leaderboard:
        show_info("No data yet. Be the first!")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return
    
    # Build leaderboard table
    tbl = Table(box=box.ROUNDED, border_style="yellow")
    tbl.add_column("Rank", style="bold yellow", width=6)
    tbl.add_column("Player", style="bold white")
    tbl.add_column("Level", style="cyan", width=8)
    tbl.add_column("XP", style="green", justify="right")
    
    for i, entry in enumerate(leaderboard, 1):
        rank = f"#{i}"
        if i == 1:
            rank = "🥇 #1"
        elif i == 2:
            rank = "🥈 #2"
        elif i == 3:
            rank = "🥉 #3"
        
        tbl.add_row(
            rank,
            entry.get("username", "Unknown"),
            str(entry.get("level", 1)),
            str(entry.get("xp", 0))
        )
    
    console.print(tbl)
    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


def _show_scores_leaderboard(firebase: FirebaseRTDB):
    """Show recent scores leaderboard"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🏆 Score Leaderboard", "Recent high scores", "cyan")
    console.print()
    
    with console.status("[bold cyan]Loading scores...", spinner="dots"):
        scores = firebase.get_leaderboard("all", limit=20)
    
    if not scores:
        show_info("No scores submitted yet!")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return
    
    # Build scores table
    tbl = Table(box=box.ROUNDED, border_style="yellow")
    tbl.add_column("Rank", style="bold yellow", width=6)
    tbl.add_column("Player", style="bold white")
    tbl.add_column("Game Mode", style="cyan")
    tbl.add_column("Score", style="green", justify="right")
    tbl.add_column("Date", style="dim", width=12)
    
    for i, entry in enumerate(scores, 1):
        rank = f"#{i}"
        if i == 1:
            rank = "🥇 #1"
        elif i == 2:
            rank = "🥈 #2"
        elif i == 3:
            rank = "🥉 #3"
        
        date = entry.get("timestamp", "")[:10]
        tbl.add_row(
            rank,
            entry.get("username", "Unknown"),
            entry.get("game_mode", "ksverse"),
            str(entry.get("score", 0)),
            date
        )
    
    console.print(tbl)
    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


def _browse_worlds(firebase: FirebaseRTDB):
    """Browse online worlds (play virtually only, no download)"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🌍 Browse Worlds", "Online worlds — play virtually, no download", "cyan")
    console.print()

    with console.status("[bold cyan]Loading online worlds...", spinner="dots"):
        online_worlds = firebase.list_worlds("all")

    # Also show local worlds
    from kslearn.loader import KSL_DIR
    local_worlds = []
    if KSL_DIR.exists():
        for wf in sorted(KSL_DIR.glob("*_verse.json")):
            try:
                with open(wf, "r") as f:
                    data = json.load(f)
                local_worlds.append({
                    "id": wf.stem.replace("_verse", ""),
                    "title": data.get("title", data.get("verse", {}).get("title", wf.stem)),
                    "source": "local",
                })
            except Exception:
                pass

    if not online_worlds and not local_worlds:
        show_info("No worlds available. Upload a world to be the first!")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return

    # Build worlds table
    tbl = Table(box=box.ROUNDED, border_style="cyan")
    tbl.add_column("#", style="yellow", width=4)
    tbl.add_column("World", style="bold white")
    tbl.add_column("Source", style="dim", width=8)
    tbl.add_column("Author", style="cyan")
    if online_worlds:
        tbl.add_column("Downloads", style="green", justify="right")
        tbl.add_column("Likes", style="green", justify="right")

    row_num = 0
    # Local worlds first
    for lw in local_worlds:
        row_num += 1
        tbl.add_row(str(row_num), lw["title"], "[yellow]Local[/yellow]", "-", "-", "-")
    
    # Online worlds
    for ow in online_worlds:
        row_num += 1
        tbl.add_row(
            str(row_num),
            ow.get("title", "Unknown"),
            "[cyan]Online[/cyan]",
            ow.get("author", "Unknown"),
            str(ow.get("downloads", 0)),
            str(ow.get("likes", 0))
        )

    console.print(tbl)
    console.print()

    console.print("[green][1-9][/green] [dim]Select world to PLAY (online worlds play virtually, local worlds open normally)[/dim]")
    console.print("[green][L][/green] [dim]Like an online world[/dim]")
    console.print("[green][B][/green] [dim]Back[/dim]")
    console.print()

    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()

        if choice == "B":
            return
        elif choice == "L":
            world_num = Prompt.ask("World number to like").strip()
            if world_num.isdigit():
                idx = int(world_num) - 1
                # Adjust for local worlds
                if idx < len(local_worlds):
                    show_info("Cannot like local worlds")
                else:
                    online_idx = idx - len(local_worlds)
                    if 0 <= online_idx < len(online_worlds):
                        firebase.like_world(online_worlds[online_idx]["world_id"])
                        show_success("World liked!")
        elif choice.isdigit():
            idx = int(choice) - 1
            if idx < len(local_worlds):
                # Open local world normally
                show_info(f"Opening local world: {local_worlds[idx]['title']}")
                from kslearn.engines.verse_engine import run_verse_interactive
                run_verse_interactive()
            else:
                # Play online world virtually
                online_idx = idx - len(local_worlds)
                if 0 <= online_idx < len(online_worlds):
                    _play_world_virtually(firebase, online_worlds[online_idx])

    except (KeyboardInterrupt, EOFError):
        return


def _play_world_virtually(firebase: FirebaseRTDB, world_info: dict):
    """Play an online world virtually (no download)"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel(f"🎮 Playing: {world_info['title']}", f"By {world_info['author']} — Virtual Session", "cyan")
    console.print()

    with console.status("[bold cyan]Loading world data...", spinner="dots"):
        world_data = firebase.download_world(world_info["world_id"])

    if not world_data:
        show_error("Failed to load world")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return

    # Play the world in verse engine
    from kslearn.engines.verse_engine import VerseEngine
    engine = VerseEngine()
    
    # Inject the online world data temporarily
    world_id = world_info["world_id"]
    engine.worlds_data = {world_id: world_data.get("verse", world_data)}
    
    show_info(f"Playing '{world_info['title']}' — changes are local only")
    console.input("\n[dim]Press Enter to start...[/dim]")
    
    engine.show_verse_menu()


def _search_world_by_id(firebase: FirebaseRTDB):
    """Search for a specific world by ID"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🔍 Search World by ID", "Find a specific world", "cyan")
    console.print()

    try:
        world_id = Prompt.ask("Enter World ID").strip()
        if not world_id:
            return

        console.print()
        with console.status("[bold cyan]Searching...", spinner="dots"):
            world = firebase.search_world_by_id(world_id)

        if not world:
            show_error(f"World '{world_id}' not found")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        # Show world info
        console.print(Panel(
            f"[bold white]Title:[/bold white] {world.get('title', 'Unknown')}\n"
            f"[bold white]Author:[/bold white] {world.get('author', 'Unknown')}\n"
            f"[bold white]Description:[/bold white] {world.get('description', 'No description')}\n"
            f"[bold white]Downloads:[/bold white] {world.get('downloads', 0)}\n"
            f"[bold white]Likes:[/bold white] {world.get('likes', 0)}",
            box=box.ROUNDED,
            border_style="cyan",
            title=f"🌍 World: {world_id}"
        ))
        console.print()

        console.print("[green][P][/green] [dim]Play virtually[/dim]")
        console.print("[green][B][/green] [dim]Back[/dim]")
        console.print()

        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()

        if choice == "P":
            _play_world_virtually(firebase, {
                "world_id": world_id,
                "title": world.get("title", world_id),
                "author": world.get("author", "Unknown"),
            })

    except (KeyboardInterrupt, EOFError):
        return


def _sync_notes(firebase: FirebaseRTDB):
    """Sync individual notes to/from cloud with selection"""
    while True:
        clear_screen()
        console.print(get_small_banner())
        console.print()
        show_panel("📚 Sync Notes", "Select individual notes to upload/download", "cyan")
        console.print()

        # Load local notes
        local_notes = firebase.get_local_notes_categories()
        cloud_notes = firebase.list_cloud_notes()

        if not local_notes and not cloud_notes:
            show_info("No notes found locally or in cloud")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        # Build notes table
        tbl = Table(box=box.ROUNDED, border_style="cyan")
        tbl.add_column("#", style="yellow", width=4)
        tbl.add_column("Category", style="bold white")
        tbl.add_column("Local", width=8)
        tbl.add_column("Cloud", width=8)
        tbl.add_column("Action", width=12)

        # Collect all unique IDs
        all_ids = {}
        for r in local_notes:
            all_ids[r["id"]] = {"local": True, "cloud": False, "title": r["title"]}
        for cid, cdata in cloud_notes.items():
            if cid not in all_ids:
                all_ids[cid] = {"local": False, "cloud": True, "title": cdata.get("title", cid)}
            else:
                all_ids[cid]["cloud"] = True

        for i, (nid, info) in enumerate(all_ids.items(), 1):
            local_icon = "✅" if info["local"] else "❌"
            cloud_icon = "☁️" if info["cloud"] else "— "
            if info["local"] and info["cloud"]:
                action = "[dim]Both[/dim]"
            elif info["local"]:
                action = "[green]Upload[/green]"
            elif info["cloud"]:
                action = "[blue]Download[/blue]"
            else:
                action = "—"
            tbl.add_row(str(i), info["title"], local_icon, cloud_icon, action)

        console.print(tbl)
        console.print()

        console.print("[green][1-N][/green] [dim]Select note(s) to sync (comma-separated, e.g. 1,3,5)[/dim]")
        console.print("[green][A][/green]    [dim]Sync ALL notes[/dim]")
        console.print("[green][B][/green]    [dim]Back[/dim]")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()

            if choice == "B":
                return
            elif choice == "A":
                uploaded = 0
                downloaded = 0
                with console.status("[bold cyan]Syncing all notes...", spinner="dots"):
                    for r in local_notes:
                        if firebase.sync_single_note_to_cloud(r["id"]):
                            uploaded += 1
                    for cid in cloud_notes:
                        is_local = any(r["id"] == cid for r in local_notes)
                        if not is_local and firebase.sync_single_note_from_cloud(cid):
                            downloaded += 1
                show_success(f"Uploaded {uploaded}, Downloaded {downloaded} new note(s)")
                console.input("\n[dim]Press Enter to continue...[/dim]")
            else:
                # Parse comma-separated numbers
                try:
                    indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
                    all_ids_list = list(all_ids.keys())
                    uploaded = 0
                    downloaded = 0
                    for idx in indices:
                        if 1 <= idx <= len(all_ids_list):
                            nid = all_ids_list[idx - 1]
                            info = all_ids[nid]
                            if info["local"]:
                                with console.status(f"[bold cyan]Uploading {info['title']}...", spinner="dots"):
                                    if firebase.sync_single_note_to_cloud(nid):
                                        uploaded += 1
                            if info["cloud"] and not info["local"]:
                                with console.status(f"[bold cyan]Downloading {info['title']}...", spinner="dots"):
                                    if firebase.sync_single_note_from_cloud(nid):
                                        downloaded += 1
                    show_success(f"Uploaded {uploaded}, Downloaded {downloaded} note(s)")
                except ValueError:
                    show_warning("Invalid selection! Use numbers like 1,3,5 or A for all")
                console.input("\n[dim]Press Enter to continue...[/dim]")

        except (KeyboardInterrupt, EOFError):
            return


def _sync_courses(firebase: FirebaseRTDB):
    """Sync individual courses to/from cloud with selection"""
    while True:
        clear_screen()
        console.print(get_small_banner())
        console.print()
        show_panel("🎓 Sync Courses", "Select individual courses to upload/download", "cyan")
        console.print()

        # Load local and cloud courses
        local_courses = firebase.get_local_courses()
        cloud_courses = firebase.list_cloud_courses()

        if not local_courses and not cloud_courses:
            show_info("No courses found locally or in cloud")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        # Build courses table
        tbl = Table(box=box.ROUNDED, border_style="cyan")
        tbl.add_column("#", style="yellow", width=4)
        tbl.add_column("Course", style="bold white")
        tbl.add_column("Local", width=8)
        tbl.add_column("Cloud", width=8)
        tbl.add_column("Action", width=12)

        # Collect all unique IDs
        all_ids = {}
        for r in local_courses:
            all_ids[r["id"]] = {"local": True, "cloud": False, "title": r["title"], "icon": r.get("icon", "📚")}
        for cid, cdata in cloud_courses.items():
            if cid not in all_ids:
                all_ids[cid] = {"local": False, "cloud": True, "title": cdata.get("title", cid), "icon": "📦"}
            else:
                all_ids[cid]["cloud"] = True

        for i, (nid, info) in enumerate(all_ids.items(), 1):
            local_icon = "✅" if info["local"] else "❌"
            cloud_icon = "☁️" if info["cloud"] else "— "
            if info["local"] and info["cloud"]:
                action = "[dim]Both[/dim]"
            elif info["local"]:
                action = "[green]Upload[/green]"
            elif info["cloud"]:
                action = "[blue]Download[/blue]"
            else:
                action = "—"
            tbl.add_row(str(i), f"{info['icon']} {info['title']}", local_icon, cloud_icon, action)

        console.print(tbl)
        console.print()

        console.print("[green][1-N][/green] [dim]Select course(s) to sync (comma-separated, e.g. 1,3)[/dim]")
        console.print("[green][A][/green]    [dim]Sync ALL courses[/dim]")
        console.print("[green][B][/green]    [dim]Back[/dim]")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()

            if choice == "B":
                return
            elif choice == "A":
                uploaded = 0
                downloaded = 0
                with console.status("[bold cyan]Syncing all courses...", spinner="dots"):
                    for r in local_courses:
                        if firebase.sync_single_course_to_cloud(r["id"]):
                            uploaded += 1
                    for cid in cloud_courses:
                        is_local = any(r["id"] == cid for r in local_courses)
                        if not is_local and firebase.sync_single_course_from_cloud(cid):
                            downloaded += 1
                show_success(f"Uploaded {uploaded}, Downloaded {downloaded} new course(s)")
                console.input("\n[dim]Press Enter to continue...[/dim]")
            else:
                # Parse comma-separated numbers
                try:
                    indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
                    all_ids_list = list(all_ids.keys())
                    uploaded = 0
                    downloaded = 0
                    for idx in indices:
                        if 1 <= idx <= len(all_ids_list):
                            nid = all_ids_list[idx - 1]
                            info = all_ids[nid]
                            if info["local"]:
                                with console.status(f"[bold cyan]Uploading {info['title']}...", spinner="dots"):
                                    if firebase.sync_single_course_to_cloud(nid):
                                        uploaded += 1
                            if info["cloud"] and not info["local"]:
                                with console.status(f"[bold cyan]Downloading {info['title']}...", spinner="dots"):
                                    if firebase.sync_single_course_from_cloud(nid):
                                        downloaded += 1
                    show_success(f"Uploaded {uploaded}, Downloaded {downloaded} course(s)")
                except ValueError:
                    show_warning("Invalid selection! Use numbers like 1,3 or A for all")
                console.input("\n[dim]Press Enter to continue...[/dim]")

        except (KeyboardInterrupt, EOFError):
            return


def _download_world(firebase: FirebaseRTDB, world_info: dict):
    """Download a world"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel(f"📥 Downloading: {world_info['title']}", f"By {world_info['author']}", "cyan")
    console.print()
    
    with console.status("[bold cyan]Downloading world...", spinner="dots"):
        world_data = firebase.download_world(world_info["world_id"])
    
    if not world_data:
        show_error("Failed to download world")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return
    
    # Save world to local data directory
    data_dir = Path.home() / ".kslearn" / "data" / "ksl"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    world_id = world_info["world_id"]
    world_file = data_dir / f"{world_id}_verse.json"
    
    with open(world_file, "w", encoding="utf-8") as f:
        json.dump(world_data, f, indent=2)
    
    show_success(f"World downloaded and saved to: {world_file}")
    console.print(f"\n[dim]You can now play it in KSL-Verse![/dim]")
    console.input("\n[dim]Press Enter to continue...[/dim]")


def _upload_world(firebase: FirebaseRTDB):
    """Upload a world to RTDB"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("📤 Upload World", "Share your KSL-Verse world with the community", "cyan")
    console.print()

    # List available worlds from KSL_DIR (same source as verse engine)
    from kslearn.loader import KSL_DIR
    
    if not KSL_DIR.exists():
        show_error("No worlds found. Create a world in KSL-Verse first!")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return

    world_files = list(KSL_DIR.glob("*_verse.json"))
    if not world_files:
        show_error("No worlds found to upload. Create a world in KSL-Verse first!")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return
    
    console.print("[bold white]Available worlds:[/bold white]\n")
    for i, wf in enumerate(world_files, 1):
        console.print(f"[green][{i}][/green] [dim]{wf.stem.replace('_verse', '')}[/dim]")
    console.print()
    
    try:
        choice = console.input("[bold green]╰─► Select world to upload:[/bold green] ").strip()
        if not choice.isdigit():
            return
        
        idx = int(choice) - 1
        if not (0 <= idx < len(world_files)):
            return
        
        world_file = world_files[idx]
        
        # Load world JSON
        with open(world_file, "r") as f:
            world_data = json.load(f)
        
        title = Prompt.ask("World title").strip()
        description = Prompt.ask("Description").strip()
        
        if not title:
            show_error("Title required")
            return
        
        world_id = world_file.stem.replace("_verse", "")
        
        with console.status("[bold cyan]Uploading world...", spinner="dots"):
            success = firebase.upload_world(world_id, world_data, title, description)
        
        if success:
            show_success("World uploaded to ksverse!")
        else:
            show_error("Failed to upload world")
        
        console.input("\n[dim]Press Enter to continue...[/dim]")
            
    except (KeyboardInterrupt, EOFError):
        return


def _multiplayer_verse(firebase: FirebaseRTDB):
    """Multiplayer KSL-Verse mode"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🎮 Multiplayer KSL-Verse", "Play with friends in real-time", "cyan")
    console.print()

    console.print("[green][1][/green] [dim]Create game session[/dim]")
    console.print("[green][2][/green] [dim]Join game session[/dim]")
    console.print("[green][3][/green] [dim]Close game session[/dim]")
    console.print("[green][B][/green] [dim]Back[/dim]")
    console.print()

    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()

        if choice == "1":
            _create_game_session(firebase)
        elif choice == "2":
            _join_game_session(firebase)
        elif choice == "3":
            _close_game_session(firebase)

    except (KeyboardInterrupt, EOFError):
        return


def _create_game_session(firebase: FirebaseRTDB):
    """Create a new multiplayer game session"""
    import random
    import string
    
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🎮 Create Game Session", "Your friends can join with this code", "cyan")
    console.print()
    
    # Generate session ID
    session_id = "ksverse_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    game_data = {
        "status": "waiting",
        "players": {
            firebase.user_id: {
                "username": firebase.user_data.get("username", "Unknown"),
                "score": 0,
                "ready": False
            }
        }
    }
    
    with console.status("[bold cyan]Creating session...", spinner="dots"):
        success = firebase.create_game_session(session_id, firebase.user_id, game_data)
    
    if success:
        console.print(Panel(
            f"[bold green]Game session created![/bold green]\n\n"
            f"Session ID: [bold yellow]{session_id}[/bold yellow]\n\n"
            f"Share this code with friends so they can join!",
            box=box.ROUNDED,
            border_style="green",
            title="🎮 Ready to Play"
        ))
        console.print()
        console.print("[dim]Waiting for players... (Press Enter to start solo)[/dim]")
        console.print("[dim]Friends can join using: kslearn online join <session_id>[/dim]")
        console.print()
        
        try:
            console.input("[bold green]╰─► Press Enter to start...[/bold green]")
        except (KeyboardInterrupt, EOFError):
            pass
        
        # Launch verse with multiplayer flag
        from kslearn.engines.verse_engine import run_verse_interactive
        run_verse_interactive(multiplayer=True, session_id=session_id, firebase=firebase)
    else:
        show_error("Failed to create game session")
        console.input("\n[dim]Press Enter to continue...[/dim]")


def _join_game_session(firebase: FirebaseRTDB):
    """Join an existing game session"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🎮 Join Game Session", "Enter the session code from your friend", "cyan")
    console.print()
    
    try:
        session_id = Prompt.ask("Session ID").strip()
        if not session_id:
            return
        
        with console.status("[bold cyan]Joining session...", spinner="dots"):
            success = firebase.join_game_session(session_id)
        
        if success:
            show_success("Joined game session!")
            console.input("\n[dim]Press Enter to start playing...[/dim]")
            
            # Launch verse with multiplayer flag
            from kslearn.engines.verse_engine import run_verse_interactive
            run_verse_interactive(multiplayer=True, session_id=session_id, firebase=firebase)
        else:
            show_error("Failed to join session. Check the session ID.")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            
    except (KeyboardInterrupt, EOFError):
        return


def _open_game_sessions(firebase: FirebaseRTDB):
    """Show all open game sessions waiting for players"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🕹️ Open Game Sessions", "Join an active session", "cyan")
    console.print()

    with console.status("[bold cyan]Loading open sessions...", spinner="dots"):
        open_sessions = firebase.get_open_game_sessions()

    if not open_sessions:
        show_info("No open sessions right now. Create one or come back later!")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return

    # Build sessions table
    tbl = Table(box=box.ROUNDED, border_style="cyan")
    tbl.add_column("#", style="yellow", width=4)
    tbl.add_column("Session Name", style="bold white")
    tbl.add_column("Players", style="cyan", justify="center")
    tbl.add_column("Description", style="dim", max_width=40)

    session_list = list(open_sessions.items())
    for i, (sid, sdata) in enumerate(session_list, 1):
        tbl.add_row(
            str(i),
            sdata.get("name", sid[:16]),
            str(sdata.get("players", 0)),
            sdata.get("description", "No description"),
        )

    console.print(tbl)
    console.print()

    console.print("[green][1-9][/green] [dim]Join a session[/dim]")
    console.print("[green][D][/green] [dim]Session details[/dim]")
    console.print("[green][B][/green] [dim]Back[/dim]")
    console.print()

    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()

        if choice == "B":
            return
        elif choice == "D":
            snum = Prompt.ask("Session number").strip()
            if snum.isdigit():
                idx = int(snum) - 1
                if 0 <= idx < len(session_list):
                    sid, sdata = session_list[idx]
                    console.print(Panel(
                        f"[bold white]Session:[/bold white] {sdata.get('name', sid)}\n"
                        f"[bold white]ID:[/bold white] {sid}\n"
                        f"[bold white]Players:[/bold white] {sdata.get('players', 0)}\n"
                        f"[bold white]Description:[/bold white] {sdata.get('description', 'N/A')}\n"
                        f"[bold white]Created:[/bold white] {sdata.get('created_at', '')[:19]}",
                        box=box.ROUNDED,
                        border_style="cyan",
                        title="🕹️ Session Details"
                    ))
                    console.print()
                    if Confirm.ask("Join this session?", default=False):
                        _join_session_by_id(firebase, sid)
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(session_list):
                sid, _ = session_list[idx]
                _join_session_by_id(firebase, sid)

    except (KeyboardInterrupt, EOFError):
        return


def _join_session_by_id(firebase: FirebaseRTDB, session_id: str):
    """Join a specific game session by ID"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel(f"🎮 Joining Session", f"ID: {session_id}", "cyan")
    console.print()

    with console.status("[bold cyan]Joining session...", spinner="dots"):
        success = firebase.join_game_session(session_id)

    if success:
        show_success("Joined game session!")
        console.input("\n[dim]Press Enter to start playing...[/dim]")
        from kslearn.engines.verse_engine import run_verse_interactive
        run_verse_interactive(multiplayer=True, session_id=session_id, firebase=firebase)
    else:
        show_error("Failed to join session")
        console.input("\n[dim]Press Enter to continue...[/dim]")


def _close_game_session(firebase: FirebaseRTDB):
    """Close your active game session"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🚪 Close Game Session", "End your current session", "cyan")
    console.print()

    if not firebase.is_logged_in():
        show_error("Not logged in")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return

    # Find user's sessions
    all_sessions = firebase._get("game_sessions")
    if not all_sessions:
        show_info("No active sessions found")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return

    # Find sessions where user is a player
    user_sessions = {}
    for sid, sdata in all_sessions.items():
        players = sdata.get("players", {})
        if firebase.user_id in players:
            user_sessions[sid] = sdata

    if not user_sessions:
        show_info("You're not in any active sessions")
        console.input("\n[dim]Press Enter to continue...[/dim]")
        return

    console.print("[bold white]Your active sessions:[/bold white]\n")
    tbl = Table(box=box.ROUNDED, border_style="cyan")
    tbl.add_column("#", style="yellow", width=4)
    tbl.add_column("Session", style="bold white")
    tbl.add_column("Status", style="dim")
    tbl.add_column("Players", style="cyan", justify="center")

    for i, (sid, sdata) in enumerate(user_sessions.items(), 1):
        is_creator = sdata.get("creator_uid") == firebase.user_id
        status = sdata.get("status", "unknown")
        players_count = len(sdata.get("players", {}))
        tbl.add_row(
            str(i),
            f"{sdata.get('session_name', sid[:16])} {'[yellow](host)[/yellow]' if is_creator else ''}",
            f"[{'green' if status == 'waiting' else 'yellow'}]{status}[/]",
            str(players_count),
        )

    console.print(tbl)
    console.print()

    console.print("[green][1-9][/green] [dim]Select session to close[/dim]")
    console.print("[green][A][/green] [dim]Close all sessions[/dim]")
    console.print("[green][B][/green] [dim]Back[/dim]")
    console.print()

    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()

        if choice == "B":
            return
        elif choice == "A":
            if Confirm.ask(f"Close all {len(user_sessions)} sessions?", default=False):
                closed = 0
                for sid in user_sessions:
                    if firebase._delete(f"game_sessions/{sid}"):
                        closed += 1
                show_success(f"Closed {closed} session(s)")
        elif choice.isdigit():
            idx = int(choice) - 1
            session_list = list(user_sessions.keys())
            if 0 <= idx < len(session_list):
                sid = session_list[idx]
                if Confirm.ask(f"Close session '{sid}'?", default=False):
                    if firebase._delete(f"game_sessions/{sid}"):
                        show_success(f"Session closed")
                    else:
                        show_error("Failed to close session")

        console.input("\n[dim]Press Enter to continue...[/dim]")

    except (KeyboardInterrupt, EOFError):
        return


def _online_settings(firebase: FirebaseRTDB):
    """Online mode settings with auto-sync toggles"""
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("⚙️ Online Settings", "Configure your online experience", "cyan")
    console.print()

    from kslearn.config import load_config, save_config
    config = load_config()
    online_config = config.get("online", {})

    # Get sync settings from Firebase
    sync_settings = firebase.get_sync_settings()
    
    console.print(f"[dim]Firebase Project:[/dim] [cyan]{firebase.project_id}[/dim]")
    console.print()

    # Auto-sync toggles
    console.print("[bold white]Auto-Sync Settings:[/bold white]\n")
    
    stats_on = sync_settings.get("auto_sync_stats", True)
    notes_on = sync_settings.get("auto_sync_notes", True)
    courses_on = sync_settings.get("auto_sync_courses", True)
    
    console.print(f"  [green][1][/green] Auto-sync stats on login:    [{'[bold green]ON[/bold green]' if stats_on else '[bold red]OFF[/bold red]'}]")
    console.print(f"  [green][2][/green] Auto-sync notes on login:    [{'[bold green]ON[/bold green]' if notes_on else '[bold red]OFF[/bold red]'}]")
    console.print(f"  [green][3][/green] Auto-sync courses on login:  [{'[bold green]ON[/bold green]' if courses_on else '[bold red]OFF[/bold red]'}]")
    console.print()

    console.print("[bold white]Other:[/bold white]\n")
    console.print("[green][4][/green] [dim]Clear cached session[/dim]")
    console.print("[green][5][/green] [dim]Reset online settings[/dim]")
    console.print("[green][B][/green] [dim]Back[/dim]")
    console.print()

    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()

        if choice == "1":
            new_val = not stats_on
            firebase.update_sync_setting("auto_sync_stats", new_val)
            show_success(f"Auto-sync stats turned {'ON' if new_val else 'OFF'}")
        elif choice == "2":
            new_val = not notes_on
            firebase.update_sync_setting("auto_sync_notes", new_val)
            show_success(f"Auto-sync notes turned {'ON' if new_val else 'OFF'}")
        elif choice == "3":
            new_val = not courses_on
            firebase.update_sync_setting("auto_sync_courses", new_val)
            show_success(f"Auto-sync courses turned {'ON' if new_val else 'OFF'}")
        elif choice == "4":
            session_file = Path.home() / ".kslearn" / "online_session.json"
            if session_file.exists():
                session_file.unlink()
                show_success("Session cleared")
            else:
                show_info("No cached session found")
        elif choice == "5":
            config["online"] = {}
            save_config(config)
            show_success("Online settings reset")
        elif choice != "B":
            show_warning("Invalid option!")
            time.sleep(1)
            return

        if choice != "B":
            console.input("\n[dim]Press Enter to continue...[/dim]")

    except (KeyboardInterrupt, EOFError):
        return
