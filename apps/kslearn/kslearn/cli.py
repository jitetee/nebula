#!/usr/bin/env python3
"""
kslearn CLI - Modern Educational Learning System

A comprehensive learning engine with quizzes, notes, and offline AI support.
All content is loaded from JSON files for easy extension.
"""

import sys
import time
import random
from pathlib import Path
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
from rich.prompt import Prompt, Confirm

from kslearn.ui import (
    console,
    get_banner,
    get_small_banner,
    show_panel,
    show_success,
    show_error,
    show_warning,
    show_info,
    LoadingSpinner,
    print_divider,
    clear_screen,
)
from kslearn.config import load_config, init_config, save_config, set_config_value, DEFAULT_CONFIG
from kslearn.config import start_session, end_session, log_activity, generate_session_summary
from kslearn.loader import content_loader, ContentLoader
from kslearn.update_checker import check_updates_async


# ─── Global update state ─────────────────────────────────────────────
_update_result = None


def _on_update_check_complete(result):
    """Callback when update check finishes."""
    global _update_result
    _update_result = result


def _show_update_notification(result):
    """Display update notification in the banner area."""
    if result is None or not result.get("update_available"):
        return

    current = result.get("current_version", "?")
    latest = result.get("latest_version", "?")
    source = result.get("source", "unknown")

    console.print(Panel(
        f"[bold green]🔄 Update available![/bold green] "
        f"v{current} → [bold cyan]v{latest}[/bold cyan] "
        f"(via {source})\n"
        f"[dim]Run: pip install --upgrade kslearn[/dim]",
        box=box.ROUNDED,
        border_style="green",
        padding=(0, 1),
    ))
    console.print()


def get_learning_tracks():
    """Load learning tracks from JSON config file"""
    from kslearn.loader import content_loader
    
    tracks_data = content_loader.load_config("tracks")
    if tracks_data and "tracks" in tracks_data:
        return tracks_data["tracks"]
    
    # Default fallback if JSON not found
    return {
        "programming": {
            "name": "💻 Programming Engine",
            "description": "Master programming fundamentals",
            "systems": {
                "programming": {"name": "Programming Quiz", "description": "Python, OOP, Algorithms, Web Dev"},
                "coding": {"name": "Coding Challenge", "description": "Solve Python coding problems"},
                "linux": {"name": "Linux/Terminal", "description": "Commands, Shell, Permissions"},
            }
        },
        "webdev": {
            "name": "🌐 Web Development Engine",
            "description": "Build modern web applications",
            "systems": {
                "webdev": {"name": "Web Dev Quiz", "description": "HTML, CSS, JavaScript, React"},
                "devops": {"name": "DevOps & Cloud", "description": "CI/CD, Docker, Kubernetes, AWS"},
            }
        },
        "ai": {
            "name": "🤖 AI & Data Science Engine",
            "description": "Learn AI, ML, and data analysis",
            "systems": {
                "ai": {"name": "AI/ML Quiz", "description": "Machine Learning, Neural Networks"},
                "datascience": {"name": "Data Science", "description": "Pandas, Statistics, Visualization"},
            }
        },
        "security": {
            "name": "🔒 Cybersecurity Engine",
            "description": "Understand security principles",
            "systems": {
                "security": {"name": "Cybersecurity Quiz", "description": "Malware, Networks, Cryptography"},
            }
        },
        "general": {
            "name": "🎓 General Knowledge Engine",
            "description": "Broaden your knowledge",
            "systems": {
                "tech": {"name": "Tech Trivia", "description": "Computers, Internet, Gaming, AI"},
                "science": {"name": "Science Quiz", "description": "Physics, Chemistry, Biology"},
                "computer": {"name": "Computer Literacy", "description": "Windows, Office, Basics"},
            }
        },
    }


def get_system_module_map():
    """Load system to module mapping from JSON config"""
    from kslearn.loader import content_loader
    
    map_data = content_loader.load_config("system_map")
    if map_data and "module_map" in map_data:
        return map_data["module_map"]
    
    # Default fallback
    return {
        "programming": "programming_quiz",
        "coding": "coding_challenge",
        "tech": "tech_trivia",
        "science": "science_quiz",
        "webdev": "web_dev_quiz",
        "ai": "ai_ml_quiz",
        "security": "cybersecurity_quiz",
        "computer": "computer_literacy",
        "devops": "devops_cloud",
        "datascience": "data_science",
        "linux": "linux_terminal",
    }


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version information")
@click.pass_context
def main(ctx, version):
    """
    kslearn - Educational Learning System

    Learn anything — math, science, languages, psychology, religion,
    music, business, technology, and more — through interactive quizzes,
    comprehensive notes, and offline AI!

    All content is loaded from JSON files for easy extension.

    Examples:

    \b
        kslearn                 # Launch interactive mode
        kslearn study           # Browse learning notes
        kslearn quiz science    # Start science quiz
        kslearn track math      # Browse math systems
        kslearn brain           # View knowledge brain
        kslearn config          # View/edit settings
    """
    if version:
        from kslearn import __version__
        console.print(f"[bold cyan]kslearn[/bold cyan] v{__version__}")
        console.print("Educational Learning System")
        console.print("\n[dim]JSON-powered • Learn Anything • Offline AI[/dim]")
        ctx.exit()

    if ctx.invoked_subcommand is None:
        ctx.invoke(play)


@main.command()
def play():
    """Launch interactive learning system menu - Learning First!"""
    clear_screen()
    console.print(get_banner())
    console.print()

    with LoadingSpinner("Loading learning content..."):
        time.sleep(0.5)

    # Start a new session
    global _current_session_id
    _current_session_id = start_session()
    session_id = _current_session_id

    from kslearn.ui import COLORS

    def _build_main_menu_table():
        """Rebuild the options table every loop so theme changes apply.
        
        New consistent structure:
        - 1-4: Core learning (Catalog, Notes, Quiz, Verse)
        - 5-7: AI & Progress (AI Chat, Progress, Tools)
        - 8-10: Content & Account (Brain, Store, Profile)
        - F-L-O: Special modes (Study Modes, LearnQuest, Online)
        - S-C-H-0: System (Settings, Support, Help, Exit)
        """
        from kslearn.ui import COLORS
        from kslearn.constants import VERSION
        tbl = Table(
            box=box.ROUNDED,
            border_style=COLORS.get("border", "cyan"),
            show_header=False,
            expand=True,
        )
        tbl.add_column("Option", style=COLORS.get("primary", "cyan"), ratio=1)
        tbl.add_column("Description", style=COLORS.get("muted", "dim"), ratio=2)
        # Core learning
        tbl.add_row("📂 1. Course Catalog", "Hierarchical courses with progression & AI tutor")
        tbl.add_row("📚 2. Study Notes", "Browse comprehensive learning materials")
        tbl.add_row("📝 3. Take Quiz", "Test your knowledge")
        tbl.add_row("🌌 4. KSL-Verse", "Interactive multiverse learning game")
        # AI & Progress
        tbl.add_row("🤖 5. AI Chat", "Chat with AI tutor (online & offline)")
        tbl.add_row("📊 6. My Progress", "Analytics, achievements, quiz scores & export")
        tbl.add_row("🔖 7. Study Tools", "Bookmarks, global search & spaced review")
        # Content & Account
        tbl.add_row("🧠 8. Knowledge Brain", "Offline AI Q&A database")
        tbl.add_row("🏪 9. Data Store", "Download new content (Free & Premium)")
        tbl.add_row("👤 10. Profile & Account", "Login, sync, friends, local profiles")
        # Special modes
        tbl.add_row("🎮 F. Study Modes", "Flashcards, timed quiz & tutorials")
        tbl.add_row("🏆 L. LearnQuest", "Answer quiz → JSON → submit & win rewards")
        tbl.add_row("🌐 O. Online Hub", "Friends, leaderboards, shared worlds (if logged in)")
        # System
        tbl.add_row("⚙️  S. Settings", "Configure your experience")
        tbl.add_row("❤️  H. Support & Help", "Credits, social links, help info")
        tbl.add_row("❌ 0. Exit", "Leave kslearn")
        return tbl

    while True:
        # Redraw menu every loop iteration (streak/goal always fresh)
        clear_screen()
        console.print(get_banner())
        console.print()

        show_panel(
            "📚 Welcome to kslearn - Learn Anything",
            "Study notes first, then test yourself with Quizzes!\n",
        )

        main_menu_table = _build_main_menu_table()
        console.print(main_menu_table)
        console.print()

        # Show daily goal and streak (fresh from config each time)
        from kslearn.config import get_daily_goal_progress
        goal = get_daily_goal_progress()
        config = load_config()
        streak = config.get("study_streak", {})
        streak_count = streak.get("current", 0)
        streak_best = streak.get("best", 0)
        streak_bar = "🔥" * min(streak_count, 10)
        goal_color = COLORS.get("success", "green") if goal["percentage"] >= 100 else COLORS.get("warning", "yellow")
        goal_bar = "█" * int(goal["percentage"] / 5) + "░" * (20 - int(goal["percentage"] / 5))

        console.print(f"[dim]Daily Goal: [{goal_color}]{goal_bar}[/{goal_color}] {goal['minutes']}/{goal['goal']}min ({goal['percentage']:.0f}%)[/dim]")
        console.print(f"[dim]Study Streak: {streak_bar or '—'} {streak_count} days (Best: {streak_best})[/dim]")
        console.print()
        console.print("[dim]Tip: Start with Study Notes for the best learning experience![/dim]\n")

        try:
            prompt_color = COLORS.get("success", "bright_green")
            choice = console.input(f"[bold {prompt_color}]╰─► Your choice (1-10, F, L, O, S, H, 0):[/bold {prompt_color}] ").strip().upper()

            if choice == "0" or choice == "EXIT":
                if Confirm.ask("Are you sure you want to exit?", default=False):
                    end_session(session_id)
                    summary = generate_session_summary(session_id)
                    console.print()
                    from kslearn.ui import show_session_end_card
                    show_session_end_card(summary)
                    show_panel("Thanks for learning!", "Come back soon! 🎓")
                    sys.exit(0)

            elif choice == "1" or choice == "CC" or choice == "CATALOG":
                from kslearn.config import update_study_streak, update_daily_goal
                update_study_streak()
                update_daily_goal(5)
                log_activity(session_id, "notes", {"type": "hierarchical"})
                from kslearn.engines.notes_viewer import run_hierarchical_notes
                run_hierarchical_notes()

            elif choice == "2" or choice == "STUDY" or choice == "N" or choice == "NOTES":
                from kslearn.config import update_study_streak, update_daily_goal
                update_study_streak()
                update_daily_goal(5)
                log_activity(session_id, "notes")
                run_learning_notes()

            elif choice == "3" or choice == "Q" or choice == "QUIZ":
                from kslearn.config import update_study_streak, update_daily_goal
                update_study_streak()
                update_daily_goal(5)
                log_activity(session_id, "quiz")
                _run_quiz_interactive()

            elif choice == "4" or choice == "VERSE" or choice == "V":
                from kslearn.config import update_study_streak, update_daily_goal
                update_study_streak()
                update_daily_goal(5)
                log_activity(session_id, "verse")
                from kslearn.engines.verse_engine import run_verse_interactive
                run_verse_interactive()

            elif choice == "5" or choice == "AI" or choice == "CHAT":
                log_activity(session_id, "ai_chat")
                run_ai_chat()

            elif choice == "6" or choice == "P" or choice == "PROGRESS":
                _run_my_progress()

            elif choice == "7" or choice == "T" or choice == "TOOLS":
                _run_study_tools()

            elif choice == "8" or choice == "B" or choice == "BRAIN":
                show_brain_stats()

            elif choice == "9" or choice == "STORE" or choice == "DATASTORE":
                run_datastore()

            elif choice == "10" or choice == "PROFILE" or choice == "ACCOUNT":
                manage_profiles()

            elif choice == "F" or choice == "M" or choice == "MODES":
                _run_study_modes(session_id)

            elif choice == "L" or choice == "LEARNQUEST":
                _run_learnquest()

            elif choice == "O" or choice == "ONLINE":
                from kslearn.online.online_mode import run_online_mode
                run_online_mode()

            elif choice == "S" or choice == "SETTINGS":
                edit_config_interactive(load_config())

            elif choice == "H" or choice == "HELP" or choice == "?" or choice == "SUPPORT":
                # Show both support and help info
                run_support()
                show_help()

            else:
                show_warning("Invalid option! Choose 1-10, F, L, O, S, H, or 0")
                continue

            # After returning from sub-menu, redraw the main menu
            clear_screen()
            console.print(get_banner())
            console.print()
            show_panel(
                "📚 Welcome to kslearn - Learn Anything",
                "Study notes first, then test yourself with Quizzes!\n",
            )
            main_menu_table = _build_main_menu_table()
            console.print(main_menu_table)
            console.print()
            console.print("[dim]Tip: Start with Study Notes for the best learning experience![/dim]\n")

        except KeyboardInterrupt:
            console.print("\n")
            show_info("Use '0' to exit or Ctrl+C again to quit.")
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                console.print()
                show_panel("Thanks for learning!", "Come back soon! 🎓")
                sys.exit(0)


def _run_quiz_interactive():
    """Run quiz selection without click context dependency - Uses centralized QuizEngine"""
    from kslearn.engines.quiz_engine import run_quiz_interactive
    run_quiz_interactive()
    # Show AI suggestions after quiz
    from kslearn.engines.notes_viewer import HierarchicalNotesViewer
    viewer = HierarchicalNotesViewer()
    viewer.show_ai_suggestions("quiz_done")


def _run_learnquest():
    """LearnQuest: Run quiz → generate answer JSON → submit or download."""
    from kslearn.engines.quiz_engine import QuizEngine
    engine = QuizEngine()
    quizzes = engine.get_available_quizzes()

    if not quizzes:
        clear_screen()
        console.print(get_small_banner())
        console.print()
        show_panel("🏆 LearnQuest", "No quizzes available yet", "yellow")
        console.print()
        console.print("[dim]Check back later or request a KSL file.[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")
        return

    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🏆 LearnQuest Challenge", "Answer quiz → Submit → Win rewards", "cyan")
    console.print()
    console.print("[dim]Select a quiz, answer the questions, then submit your answers.[/dim]")
    console.print("[dim]High scorers win free premium content, badges, and leaderboard spots.[/dim]")
    console.print()

    tbl = Table(box=box.ROUNDED, border_style="cyan")
    tbl.add_column("#", style="yellow", width=4)
    tbl.add_column("Quiz", style="bold white")
    tbl.add_column("Questions", style="dim", width=10)
    for i, q in enumerate(quizzes, 1):
        total_q = 0
        if "questions" in q:
            total_q = sum(len(v) for v in q["questions"].values()) if isinstance(q["questions"], dict) else len(q["questions"])
        tbl.add_row(str(i), q.get("metadata", {}).get("title", q["key"]), str(total_q))
    console.print(tbl)
    console.print()

    try:
        ch = console.input("[bold green]╰─► Select quiz #[/bold green] ").strip()
    except (KeyboardInterrupt, EOFError):
        return
    if not ch or not ch.isdigit():
        return
    idx = int(ch) - 1
    if not (0 <= idx < len(quizzes)):
        return

    selected = quizzes[idx]
    quest_title = selected.get("metadata", {}).get("title", selected["key"])
    quest_id = "LQ-" + str(int(time.time()))

    # Run the quiz and collect answers
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel(f"🏆 LearnQuest: {quest_title}", f"Quest ID: {quest_id}", "cyan")
    console.print()
    console.print("[dim]Answer each question. Your answers will be saved as JSON.[/dim]")
    console.print()

    questions = []
    q_data = selected.get("questions", {})
    if isinstance(q_data, dict):
        for topic_title, topic_qs in q_data.items():
            for q in topic_qs:
                questions.append({"topic": topic_title, **q})
    elif isinstance(q_data, list):
        questions = q_data

    answers = {}
    score = 0
    total = len(questions)

    for i, q in enumerate(questions, 1):
        console.clear()
        console.print()
        console.print(f"[dim]LearnQuest: {quest_title} | Q {i}/{total}[/dim]")
        console.print()

        question = q.get("question", q.get("q", "?"))
        options = q.get("options", [])
        correct_idx = q.get("answer", q.get("correct", 0))
        explanation = q.get("explanation", q.get("exp", ""))

        console.print(Panel(f"[bold white]{question}[/bold white]", box=box.ROUNDED, border_style="cyan"))
        console.print()

        for j, opt in enumerate(options, 1):
            console.print(f"  [green][{j}][/green] [white]{opt}[/white]")
        console.print()

        try:
            ans = console.input("[bold green]╰─► Your answer (1-{}):[/bold green] ".format(len(options))).strip()
        except (KeyboardInterrupt, EOFError):
            break

        chosen = int(ans) - 1 if ans.isdigit() else -1
        is_correct = (chosen == correct_idx)
        if is_correct:
            score += 1
        answers[i - 1] = chosen

        console.print()
        if is_correct:
            console.print(Panel("[bold green]✅ Correct![/bold green]", box=box.ROUNDED, border_style="green"))
        else:
            console.print(Panel(f"[bold red]❌ Wrong![/bold red] Answer: [green]{options[correct_idx]}[/green]", box=box.ROUNDED, border_style="red"))
        if explanation:
            console.print(f"[dim]💡 {explanation}[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter for next...[/bold green]")

    # Generate answer JSON
    percentage = (score / max(total, 1)) * 100
    payload = {
        "questId": quest_id,
        "title": quest_title,
        "answers": answers,
        "score": score,
        "totalQuestions": total,
        "percentage": round(percentage, 1),
        "submittedAt": datetime.now().isoformat()
    }

    # Show results
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("📊 LearnQuest Results", quest_title, "cyan")
    console.print()
    result_table = Table(box=box.ROUNDED, border_style="cyan")
    result_table.add_column("Metric", style="bold white")
    result_table.add_column("Value", style="dim", justify="right")
    result_table.add_row("Quest ID", quest_id)
    result_table.add_row("Score", f"{score}/{total}")
    result_table.add_row("Percentage", f"[{'green' if percentage >= 80 else 'yellow' if percentage >= 60 else 'red'}]{percentage:.0f}%")
    result_table.add_row("Status", "🏆 Reward Eligible!" if percentage >= 80 else "✅ Submitted")
    console.print(result_table)
    console.print()

    # Show JSON
    json_preview = json.dumps(payload, indent=2)
    console.print("[bold cyan]📄 Answer JSON:[/bold cyan]")
    console.print(Panel(f"[dim]{json_preview}[/dim]", box=box.ASCII, border_style="green", title="answers.json"))
    console.print()

    # Save to file
    output_dir = Path.cwd() / "learnquest"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"answers_{quest_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    console.print(f"[dim]Saved to: {output_file}[/dim]")
    console.print()

    # Actions
    console.print("[green][S][/green] [dim]Submit to LearnQuest website[/dim]")
    console.print("[green][D][/green] [dim]Download / view JSON file[/dim]")
    console.print("[green][C][/green] [dim]Copy JSON to clipboard[/dim]")
    console.print("[green][0][/green] [dim]Back to menu[/dim]")
    console.print()
    try:
        act = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return

    if act == "s":
        console.print(Panel(
            "[bold white]To submit your answers:[/bold white]\n\n"
            "1. Go to [cyan]https://kash-sight.web.app/learnquest.html[/cyan]\n"
            "2. Upload the file or drag & drop [cyan]answers_{quest_id}.json[/cyan]\n"
            "3. Click Submit Answers\n\n"
            f"[dim]Your Quest ID: {quest_id}[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
            title="🏆 Submit to LearnQuest",
        ))
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")
    elif act == "d":
        console.print(f"\n[dim]File: {output_file}[/dim]")
        console.print()
    elif act == "c":
        import subprocess
        import sys as _sys
        copied = False
        # Try cross-platform clipboard approaches
        # 1. Try pyperclip first (cross-platform Python library)
        try:
            import pyperclip
            pyperclip.copy(json_preview)
            copied = True
        except ImportError:
            pass
        # 2. Try pbcopy (macOS)
        if not copied:
            try:
                if _sys.platform == "darwin":
                    _p = subprocess.Popen(["pbcopy", "w"], stdin=subprocess.PIPE, text=True)
                    _p.communicate(input=json_preview, timeout=5)
                    copied = True
                # 3. Try clip (Windows)
                elif _sys.platform == "win32":
                    _p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, text=True)
                    _p.communicate(input=json_preview, timeout=5)
                    copied = True
                # 4. Try xclip/xsel (Linux)
                elif _sys.platform.startswith("linux"):
                    for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
                        try:
                            _p = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
                            _p.communicate(input=json_preview, timeout=5)
                            copied = True
                            break
                        except FileNotFoundError:
                            continue
                # 5. Try termux-clipboard-set (Android/Termux)
                if _sys.platform.startswith("android") or not copied:
                    subprocess.run(["termux-clipboard-set", json_preview], timeout=5)
                    copied = True
            except Exception:
                pass
        if copied:
            show_success("JSON copied to clipboard!")
        else:
            show_info("Clipboard not available. Copy from the JSON above.")
        time.sleep(1.5)


def show_track_systems(track_key):
    """Show systems within a track"""
    tracks = get_learning_tracks()
    track = tracks.get(track_key)
    
    if not track:
        show_error(f"Track not found: {track_key}")
        return
    
    clear_screen()
    console.print(get_small_banner())
    console.print()

    show_panel(
        track["name"],
        track["description"],
        "cyan",
    )

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
    )
    table.add_column("#", style="yellow", width=4, justify="center")
    table.add_column("System", style="bold white")
    table.add_column("Description", style="dim")

    system_keys = list(track["systems"].keys())
    for i, (key, (name, desc)) in enumerate(track["systems"].items(), 1):
        table.add_row(str(i), name, desc)

    table.add_row("0", "Back", "Return to tracks")
    table.add_row("R", "🎲 Random Quiz", "Start random quiz from track")
    table.add_row("N", "📚 Notes", "View learning notes for track")

    console.print(table)
    console.print()

    while True:
        try:
            choice = console.input(f"[bold green]Select system (0-{len(system_keys)}, R, N):[/bold green] ").strip().upper()

            if choice == "0":
                return

            elif choice == "R":
                system_key = random.choice(system_keys)
                run_system(system_key)
                return

            elif choice == "N":
                # Open the learning notes browser
                run_learning_notes()
                return

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(system_keys):
                    system_key = system_keys[choice_num - 1]
                    run_system(system_key)
                    return
                else:
                    show_warning("Invalid system number!")
            except ValueError:
                show_warning("Please enter a number, R, or N!")

        except KeyboardInterrupt:
            return


@main.command()
@click.argument("system", required=False)
@click.option("--random", "-r", "random_quiz", is_flag=True, help="Start a random quiz")
def quiz(system, random_quiz):
    """
    Start a specific quiz

    Examples:

    \b
        kslearn quiz            # Browse all quizzes
        kslearn quiz science    # Science quiz
        kslearn quiz --random   # Random quiz
    """
    # Use centralized QuizEngine
    from kslearn.engines.quiz_engine import QuizEngine
    
    engine = QuizEngine()
    quizzes = engine.get_available_quizzes()
    
    if not quizzes:
        show_error("No quiz files found in data/ksl/")
        show_info("Add JSON quiz files to start learning!")
        return
    
    if random_quiz:
        selected = random.choice(quizzes)
        system = selected["key"]
        show_info(f"Random quiz selected: [bold]{system}[/bold]")
    elif system:
        # Find quiz by key or partial match
        selected = None
        for q in quizzes:
            if q["key"].lower() == system.lower() or system.lower() in q["key"].lower():
                selected = q
                break
        
        if not selected:
            show_error(f"Quiz not found: {system}")
            show_info(f"Available: {', '.join(q['key'] for q in quizzes)}")
            return
        system = selected["key"]
    else:
        # Interactive selection via QuizEngine
        run_quiz_interactive()
        return

    # Load and run the quiz
    quiz_data = engine.load_quiz(system)
    if not quiz_data:
        return
    
    topic = engine.select_topic(quiz_data)
    if not topic:
        return

    topic_title = topic.get("title", f"Topic {topic.get('id', '?')}")
    questions = topic.get("questions", [])
    if questions:
        engine.run_quiz(system, topic_title, questions)
    else:
        show_error(f"No questions found for topic: {topic_title}")


@main.command()
@click.argument("topic", type=click.STRING, required=False)
@click.option("--list", "-l", "list_topics", is_flag=True, help="List all study topics")
def study(topic, list_topics):
    """
    Access learning notes and study materials

    Examples:

    \b
        kslearn study           # Browse all topics
        kslearn study --list    # List available topics
    """
    # Use centralized NotesViewer
    from kslearn.engines.notes_viewer import run_notes_interactive
    
    if list_topics:
        console.print()
        show_panel("Learning Topics", "Comprehensive study materials from JSON", "cyan")

        categories = content_loader.get_all_notes_categories()

        if not categories:
            show_warning("No learning materials found!")
            show_info("Make sure .ksl files are in kslearn/data/ksl/")
            return

        table = Table(box=box.ROUNDED, border_style="cyan")
        table.add_column("Category", style="bold white")

        for cat_info in categories:
            cat = cat_info["key"] if isinstance(cat_info, dict) else cat_info
            notes_data = content_loader.load_notes(cat)
            if notes_data:
                metadata = notes_data.get("metadata", {})
                title = metadata.get("title", cat.title())
                table.add_row(title)

        console.print(table)
        console.print()
        show_info("Use 'kslearn study' for interactive browsing")
        return

    run_notes_interactive()


@main.command()
def track():
    """Browse learning tracks interactively"""
    clear_screen()
    console.print(get_small_banner())
    console.print()

    show_panel(
        "📚 Learning Tracks",
        "Organized learning paths for different skills\n",
        "cyan",
    )

    tracks = get_learning_tracks()
    
    for key, track_data in tracks.items():
        console.print(f"\n[bold cyan]{track_data['name']}[/bold cyan]")
        console.print(f"[dim]{track_data['description']}[/dim]")
        console.print()

        for system_key, system_info in track_data["systems"].items():
            name = system_info.get("name", system_key.replace("_", " ").title())
            desc = system_info.get("description", "")
            console.print(f"  • [white]{name}[/white] - [dim]{desc}[/dim]")

    console.print()
    print_divider()
    console.print()
    show_info("Use 'kslearn play' to start learning!")


@main.command()
def brain():
    """View and manage the JSON Brain (offline AI knowledge)"""
    show_brain_stats()


def show_brain_stats():
    """Display JSON Brain statistics"""
    stats = content_loader.get_brain_stats()

    clear_screen()
    console.print(get_small_banner())
    console.print()

    show_panel("🧠 JSON Brain Stats", "Offline AI Knowledge Base", "cyan")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Metric", style="yellow")
    table.add_column("Value", style="cyan")

    table.add_row("Total Q&A Pairs", str(stats["total_qa_pairs"]))
    table.add_row("Conversations", str(stats["total_conversations"]))
    table.add_row("Categories", ", ".join(stats["categories"]) if stats["categories"] else "None")
    table.add_row("Last Updated", stats["last_updated"])

    console.print(table)
    console.print()

    # Per-category breakdown
    brain_data = content_loader.load_brain_qa()
    if brain_data and "categories" in brain_data:
        categories = brain_data["categories"]
        if categories:
            console.print("[bold]By Category:[/bold]\n")
            cat_table = Table(box=box.ROUNDED, border_style="green")
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Entries", style="yellow")
            cat_table.add_column("Last Updated", style="dim")
            for cat_key, cat_data in sorted(categories.items()):
                cat_table.add_row(
                    cat_key.replace("_", " ").title(),
                    str(cat_data.get("count", 0)),
                    cat_data.get("last_updated", ""),
                )
            console.print(cat_table)
            console.print()

    console.print("  [green][E][/green] Export Brain")
    console.print("  [green][I][/green] Import Brain")
    console.print("  [green][C][/green] Clear Brain")
    console.print("  [green][0][/green] Back")
    console.print()

    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()
    except KeyboardInterrupt:
        return

    if choice == "E":
        try:
            filename = console.input("[bold yellow]Export filename:[/bold yellow] ").strip()
        except KeyboardInterrupt:
            return
        if filename:
            if content_loader.export_brain(filename):
                show_success(f"Brain exported to {filename}!")
            else:
                show_error("Export failed!")
            time.sleep(2)

    elif choice == "I":
        try:
            console.print()
            console.print("  [dim]Enter a file path (.json) or a directory path[/dim]")
            console.print("  [dim]containing .json brain files to import them all.[/dim]")
            console.print("  [dim]Imported files are backed up to brain/imported/[/dim]")
            console.print()
            filepath = console.input("[bold yellow]File or directory path:[/bold yellow] ").strip()
        except KeyboardInterrupt:
            return
        if filepath:
            # Expand ~ to home dir
            filepath = str(Path(filepath).expanduser())
            import os
            if not os.path.exists(filepath):
                show_error(f"Path not found: {filepath}")
                time.sleep(2)
            else:
                is_dir = os.path.isdir(filepath)
                if is_dir:
                    json_count = len(list(Path(filepath).glob("*.json")))
                    show_info(f"Found {json_count} JSON file(s) in directory")
                merge = Confirm.ask("Merge with existing brain?", default=True)
                if content_loader.import_brain(filepath, merge):
                    if is_dir:
                        show_success(f"Brain files imported from directory!")
                    else:
                        show_success(f"Brain imported from {Path(filepath).name}!")
                    show_info("Backup saved to brain/imported/")
                else:
                    show_error("Import failed! Check the file format.")
                time.sleep(2)

    elif choice == "C":
        if Confirm.ask("Clear entire brain? This cannot be undone!", default=False):
            from kslearn.loader import KSL_DIR
            brain_file = KSL_DIR / "brain.ksl"
            default_brain = {
                "metadata": {"created": time.time(), "version": "1.0"},
                "categories": {},
                "conversations": [],
                "qa_pairs": []
            }
            content_loader._save_json(brain_file, default_brain)
            content_loader.clear_cache()
            show_success("Brain cleared!")
            time.sleep(2)


@main.command()
@click.option("--reset", is_flag=True, help="Reset to default settings")
@click.option("--init", "init_only", is_flag=True, help="Initialize config file")
@click.option("--edit", "edit_mode", is_flag=True, help="Edit configuration interactively")
def config(reset, init_only, edit_mode):
    """
    View and edit configuration

    Examples:

    \b
        kslearn config          # View current settings
        kslearn config --reset  # Reset to defaults
        kslearn config --edit   # Edit settings interactively
    """
    if init_only:
        cfg = init_config()
        show_success("Configuration initialized!")
        display_config(cfg)
        return

    if reset:
        if Confirm.ask("Reset all settings to defaults?", default=False):
            from kslearn.config import reset_config
            cfg = reset_config()
            show_success("Configuration reset to defaults!")
            display_config(cfg)
        return

    # Show current config
    cfg = load_config()
    display_config(cfg)
    
    # Ask if user wants to edit
    if edit_mode or Confirm.ask("\nWould you like to edit these settings?", default=False):
        edit_config_interactive(cfg)


def display_config(cfg: dict):
    """Display configuration in a table"""
    table = Table(title="Current Configuration", box=box.ROUNDED, border_style="cyan")
    table.add_column("Setting", style="yellow")
    table.add_column("Value", style="cyan")

    for key, value in cfg.items():
        if key == "api_key" and value:
            value = "****" * 8
        table.add_row(key, str(value))

    console.print(table)


def edit_config_interactive(cfg: dict):
    """Interactive config editor"""
    from kslearn.config import save_config, DEFAULT_CONFIG
    
    clear_screen()
    show_panel("Edit Configuration", "Change settings (press Enter to keep current value)", "cyan")
    console.print()
    
    new_config = cfg.copy()
    
    for key, default_value in DEFAULT_CONFIG.items():
        current_value = new_config.get(key, default_value)
        console.print(f"[yellow]{key}[/yellow]: [cyan]{current_value}[/cyan] (default: {default_value})")
        
        new_value = console.input(f"[bold green]╰─► New value (or Enter to keep):[/bold green] ").strip()
        
        if new_value:
            # Try to convert to appropriate type
            if isinstance(default_value, bool):
                new_config[key] = new_value.lower() in ("true", "yes", "1", "on")
            elif isinstance(default_value, int):
                try:
                    new_config[key] = int(new_value)
                except ValueError:
                    show_warning(f"Invalid number, keeping {current_value}")
            else:
                new_config[key] = new_value
    
    # Save configuration
    if Confirm.ask("\nSave these settings?", default=True):
        save_config(new_config)
        show_success("Configuration saved!")
        display_config(new_config)
        # Apply theme changes immediately
        from kslearn.ui import reload_theme
        reload_theme()
    else:
        show_info("Changes discarded")


def show_help():
    """Show help and usage information"""
    from kslearn import __version__

    clear_screen()
    console.print(get_small_banner())
    console.print()

    show_panel("❓ Help & Usage", f"kslearn v{__version__} - Educational Learning System", "cyan")
    console.print()

    # Menu shortcuts
    help_table = Table(box=box.ROUNDED, border_style="cyan", title="Menu Shortcuts")
    help_table.add_column("Key", style="yellow", width=8)
    help_table.add_column("Action", style="white")
    help_table.add_row("1 / CC", "Course Catalog (w/ AI tutor)")
    help_table.add_row("2 / N", "Study Notes")
    help_table.add_row("3 / Q", "Take a Quiz")
    help_table.add_row("4", "AI Chat (online/offline)")
    help_table.add_row("5 / P", "📊 My Progress (Analytics + Scores + Achievements + Export)")
    help_table.add_row("6 / T", "🔖 Study Tools (Bookmarks + Search + Spaced Review)")
    help_table.add_row("7 / B", "Knowledge Brain")
    help_table.add_row("8", "🏪 Data Store")
    help_table.add_row("S", "❤️  Support kslearn")
    help_table.add_row("F / M", "🎮 Study Modes (Flashcards + Timed Quiz + Tutorials)")
    help_table.add_row("L", "🏆 LearnQuest (Quiz → JSON → Submit & Win)")
    help_table.add_row("D", "👤 Profiles")
    help_table.add_row("C", "Settings")
    help_table.add_row("H / ?", "This help screen")
    help_table.add_row("0", "Exit")
    console.print(help_table)
    console.print()

    # CLI commands
    cli_table = Table(box=box.ROUNDED, border_style="green", title="CLI Commands")
    cli_table.add_column("Command", style="yellow")
    cli_table.add_column("Description", style="white")
    cli_table.add_row("kslearn", "Launch interactive menu")
    cli_table.add_row("kslearn study", "Browse learning notes")
    cli_table.add_row("kslearn quiz <topic>", "Start a specific quiz")
    cli_table.add_row("kslearn quiz --random", "Random quiz")
    cli_table.add_row("kslearn chat", "AI chat (powered by tgpt)")
    cli_table.add_row("kslearn ai-config", "Configure AI provider & API key")
    cli_table.add_row("kslearn brain", "View knowledge brain stats")
    cli_table.add_row("kslearn track", "Browse learning tracks")
    cli_table.add_row("kslearn daily", "Today's recommended lesson")
    cli_table.add_row("kslearn config", "View/edit settings")
    cli_table.add_row("kslearn config --edit", "Edit settings interactively")
    cli_table.add_row("kslearn config --reset", "Reset to defaults")
    cli_table.add_row("kslearn --version", "Show version")
    cli_table.add_row("kslearn --help", "Show CLI help")
    console.print(cli_table)
    console.print()
    
    # AI Providers
    show_panel("🤖 AI Providers", "Powered by tgpt (termux-ai)", "cyan")
    console.print()
    console.print("[bold]Free Providers:[/bold]")
    console.print("  [green]• sky[/green] - Free, uses gpt-4.1-mini (default)")
    console.print("  [green]• phind[/green] - Great for coding questions")
    console.print("  [green]• ollama[/green] - Local models (no internet)")
    console.print("  [green]• kimi[/green] - Moonshot AI assistant")
    console.print("  [green]• isou[/green] - Search-powered AI")
    console.print("  [green]• pollinations[/green] - Free text generation")
    console.print()
    console.print("[bold]API Key Required:[/bold]")
    console.print("  [yellow]• openai[/yellow] - https://platform.openai.com/api-keys")
    console.print("  [yellow]• groq[/yellow] - https://console.groq.com/keys (fast & free tier)")
    console.print("  [yellow]• gemini[/yellow] - https://aistudio.google.com/apikey")
    console.print("  [yellow]• deepseek[/yellow] - https://platform.deepseek.com/api-keys")
    console.print()

    # Themes
    show_panel("🎨 Themes", "Customize the look and feel", "cyan")
    console.print()
    console.print("[bold]Available Themes:[/bold]")
    console.print("  [bright_cyan]• sky_blue[/bright_cyan] — Clean, bright blue tones (default)")
    console.print("  [bright_green]• green[/bright_green] — Forest green, nature-inspired")
    console.print("  [bright_white]• grey[/bright_white] — Minimalist monochrome")
    console.print()
    console.print("[bold]Change Theme:[/bold]")
    console.print("  Go to [yellow]Settings (C)[/yellow] in the main menu → edit [yellow]theme[/yellow]")
    console.print("  Or run: [dim]kslearn config --edit[/dim] → change [dim]color_scheme[/dim]")
    console.print()

    console.print()

    # Quiz topics - load from available JSON files
    from kslearn.engines.quiz_engine import QuizEngine
    engine = QuizEngine()
    quizzes = engine.get_available_quizzes()
    
    if quizzes:
        console.print("[bold cyan]Available Quiz Topics:[/bold cyan]")
        topics = [q["key"] for q in quizzes]
        console.print(f"  [dim]{', '.join(topics)}[/dim]")
        console.print()
        console.print("[dim]Example: kslearn quiz science[/dim]")

    console.print()

    try:
        console.input("[dim]Press Enter to go back...[/dim]")
    except KeyboardInterrupt:
        pass


def show_analytics():
    """Visual analytics dashboard with charts and insights."""
    from kslearn.config import load_config
    from datetime import datetime as _dt

    clear_screen()
    console.print(get_small_banner())
    console.print()

    show_panel("📊 Analytics Dashboard", "Comprehensive learning insights", "magenta")
    console.print()

    config = load_config()
    progress = config.get("learning_progress", {})
    streak = config.get("study_streak", {})
    achievements = config.get("achievements", [])
    bookmarks = config.get("bookmarks", [])
    daily = config.get("daily_goal", {})
    daily_goal_minutes = config.get("daily_goal_minutes", 30)
    tutorial_progress = config.get("tutorial_progress", {})
    timed_quiz_best = config.get("timed_quiz_best", 0)
    review_queue = config.get("review_queue", {})
    verse_progress = config.get("verse_progress", {})

    # ─── Aggregate Metrics ─────────────────────────────────────────
    quizzes_completed = len(progress)
    total_correct = sum(p.get("correct", p.get("last_score", 0)) for p in progress.values())
    total_questions = sum(p.get("questions", 0) for p in progress.values())
    total_wrong = total_questions - total_correct
    overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
    best_streak = streak.get("best", 0)
    current_streak = streak.get("current", 0)
    last_study_date = streak.get("last_study_date", "Never")

    # Verse metrics
    verse_xp = verse_progress.get("total_xp", 0)
    verse_worlds = verse_progress.get("worlds", {})
    verse_achievements = verse_progress.get("achievements", [])
    verse_items = verse_progress.get("inventory", [])
    verse_combo = verse_progress.get("combo_multiplier", 1.0)
    verse_secrets = len(verse_progress.get("secrets_found", []))
    verse_lore = len(verse_progress.get("lore_unlocked", []))
    verse_prestige = verse_progress.get("prestige_level", 0)

    # Tutorial metrics
    tutorials_completed = sum(1 for v in tutorial_progress.values() if v.get("completed"))
    tutorials_in_progress = sum(1 for v in tutorial_progress.values() if v.get("started") and not v.get("completed"))

    # ─── SECTION 1: Overall Stats ──────────────────────────────────
    stats_table = Table(box=box.DOUBLE_EDGE, border_style="magenta")
    stats_table.add_column("Metric", style="bold white", ratio=2)
    stats_table.add_column("Value", style="cyan", ratio=1, justify="right")
    stats_table.add_row("📝 Quizzes Completed", str(quizzes_completed))
    stats_table.add_row("❓ Questions Answered", str(total_questions))
    stats_table.add_row("✅ Correct Answers", f"[green]{total_correct}[/green]")
    stats_table.add_row("❌ Wrong Answers", f"[red]{total_wrong}[/red]")
    acc_color = "green" if overall_accuracy >= 70 else "yellow" if overall_accuracy >= 50 else "red"
    stats_table.add_row("🎯 Overall Accuracy", f"[{acc_color}]{overall_accuracy:.0f}%[/{acc_color}]")
    stats_table.add_row("🔥 Current Streak", f"{current_streak} days")
    stats_table.add_row("🏆 Best Streak", f"{best_streak} days")
    stats_table.add_row("📅 Last Studied", last_study_date)
    stats_table.add_row("🏅 Achievements", f"{len(achievements)}/24")
    stats_table.add_row("🔖 Bookmarks", str(len(bookmarks)))
    stats_table.add_row("📚 Tutorials Completed", str(tutorials_completed))
    stats_table.add_row("⏱️  Timed Quiz Best", f"{timed_quiz_best} questions")
    console.print(stats_table)
    console.print()

    # ─── SECTION 1b: KSL-Verse Stats ──────────────────────────────
    if verse_xp > 0:
        from kslearn.engines.verse_engine import get_rank
        rank_title, _, next_xp = get_rank(verse_xp)
        total_worlds = sum(1 for w in verse_worlds.values() if w.get("world_completed"))
        total_bosses = sum(1 for w in verse_worlds.values() if w.get("boss_defeated"))

        console.print("[bold magenta]🌌  KSL-Verse Progress:[/bold magenta]\n")
        verse_table = Table(box=box.ROUNDED, border_style="magenta")
        verse_table.add_column("Metric", style="bold white", ratio=2)
        verse_table.add_column("Value", style="cyan", ratio=1, justify="right")
        verse_table.add_row("⭐ Total XP", str(verse_xp))
        verse_table.add_row("🎖️  Rank", rank_title)
        verse_table.add_row("🔄 Combo Multiplier", f"{verse_combo:.1f}x")
        verse_table.add_row("🌍 Worlds Completed", f"{total_worlds}")
        verse_table.add_row("🏆 Bosses Defeated", f"{total_bosses}")
        verse_table.add_row("🎒 Inventory Items", str(len(verse_items)))
        verse_table.add_row("🕵️  Secrets Found", str(verse_secrets))
        verse_table.add_row("📜 Lore Entries", str(verse_lore))
        verse_table.add_row("🏅 Verse Achievements", str(len(verse_achievements)))
        if verse_prestige > 0:
            verse_table.add_row("✨ Prestige Level", str(verse_prestige))
        console.print(verse_table)
        console.print()

    # ─── SECTION 2: Accuracy by Category (Bar Chart) ───────────────
    categories = {}
    if progress:
        for key, data in progress.items():
            cat = data.get("category", "unknown")
            if cat not in categories:
                categories[cat] = {"correct": 0, "total": 0, "sessions": 0, "accuracies": []}
            categories[cat]["correct"] += data.get("correct", data.get("last_score", 0))
            categories[cat]["total"] += data.get("questions", 0)
            categories[cat]["sessions"] += 1
            acc = data.get("last_accuracy", 0)
            if acc > 0:
                categories[cat]["accuracies"].append(acc)

        console.print("[bold]📈 Accuracy by Category:[/bold]\n")
        for cat, vals in sorted(categories.items(), key=lambda x: x[1]["correct"] / max(x[1]["total"], 1) * 100, reverse=True):
            acc = (vals["correct"] / vals["total"] * 100) if vals["total"] > 0 else 0
            bar_len = int(acc / 2.5)
            color = "green" if acc >= 70 else "yellow" if acc >= 50 else "red"
            bar = f"[{color}]{'█' * bar_len}[/{color}][dim]{'░' * (40 - bar_len)}[/dim]"
            cat_label = cat.replace("_", " ").title().ljust(20)
            avg_acc = (sum(vals["accuracies"]) / len(vals["accuracies"])) if vals["accuracies"] else 0
            trend = "📈" if avg_acc > acc else "📉" if avg_acc < acc else "➡️"
            console.print(f"  {cat_label} [{color}]{acc:5.0f}%[/{color}] {bar}  ({vals['sessions']} sessions) {trend}")
        console.print()

    # ─── SECTION 3: Session Volume (Horizontal Bar) ────────────────
    if categories:
        console.print("[bold]📊 Session Volume by Category:[/bold]\n")
        total_sessions = sum(v["sessions"] for v in categories.values())
        sorted_cats = sorted(categories.items(), key=lambda x: x[1]["sessions"], reverse=True)
        max_sessions = max(v["sessions"] for v in categories.values()) if categories else 1
        bar_max = 30

        for cat, vals in sorted_cats:
            pct = (vals["sessions"] / max(total_sessions, 1)) * 100
            bar_len = int((vals["sessions"] / max(max_sessions, 1)) * bar_max)
            cat_label = cat.replace("_", " ").title().ljust(20)
            bar = f"[blue]{'█' * bar_len}[/{'blue'}][dim]{'░' * (bar_max - bar_len)}[/dim]"
            console.print(f"  {cat_label} [blue]{pct:5.0f}%[/blue] [{bar}] ({vals['sessions']})")
        console.print()

    # ─── SECTION 4: Performance Distribution (ASCII Histogram) ─────
    if progress:
        console.print("[bold]📉 Score Distribution:[/bold]\n")
        buckets = {"0-20%": 0, "21-40%": 0, "41-60%": 0, "61-80%": 0, "81-100%": 0}
        for _, data in progress.items():
            acc = data.get("last_accuracy", 0)
            if acc <= 20: buckets["0-20%"] += 1
            elif acc <= 40: buckets["21-40%"] += 1
            elif acc <= 60: buckets["41-60%"] += 1
            elif acc <= 80: buckets["61-80%"] += 1
            else: buckets["81-100%"] += 1

        max_bucket = max(buckets.values()) if buckets else 1
        bar_width = 25
        for range_label, count in buckets.items():
            bar_len = int((count / max(max_bucket, 1)) * bar_width)
            color = "red" if "0-" in range_label or "21" in range_label else "yellow" if "41" in range_label else "green"
            bar = f"[{color}]{'█' * bar_len}[/{color}][dim]{'░' * (bar_width - bar_len)}[/dim]"
            console.print(f"  {range_label:>8} [{color}]{count:3d}[/{color}] {bar}")
        console.print()

    # ─── SECTION 5: Study Streak Heatmap ───────────────────────────
    console.print("[bold]📅 Study Activity (Last 28 Days):[/bold]\n")
    week_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    console.print("       " + " ".join(f"[dim]{d}[/dim]" for d in week_labels))

    activity_days = set()
    for p in progress.values():
        ts = p.get("completed_at", 0)
        if ts > 0:
            day_str = _dt.fromtimestamp(ts).strftime("%Y-%m-%d")
            activity_days.add(day_str)
    # Also include streak calendar from verse
    streak_cal = verse_progress.get("streak_calendar", {})
    for d in streak_cal:
        if streak_cal[d]:
            activity_days.add(d)

    today = datetime.now()
    for week in range(4):
        week_row = ""
        for day in range(7):
            day_offset = week * 7 + day
            check_date = today - timedelta(days=(27 - day_offset))
            day_str = check_date.strftime("%Y-%m-%d")
            active = day_str in activity_days
            cell_color = "bright_green" if active else "dim"
            cell = "🟩" if active else "⬛"
            week_row += f"[{cell_color}]{cell}[/{cell_color}] "
        label = f"  W{week+1}"
        console.print(f"{label} {week_row}")
    console.print("       🟩 Active  ⬛ Rest")
    console.print()

    # ─── SECTION 6: Daily Goal Progress ────────────────────────────
    from kslearn.config import get_daily_goal_progress
    goal = get_daily_goal_progress()
    console.print("[bold]🎯 Daily Goal Progress:[/bold]\n")
    goal_pct = goal.get("percentage", 0)
    goal_bar_len = int(goal_pct / 4)
    goal_color = "green" if goal_pct >= 100 else "yellow" if goal_pct >= 50 else "red"
    goal_bar = f"[{goal_color}]{'█' * goal_bar_len}[/{goal_color}][dim]{'░' * (25 - goal_bar_len)}[/dim]"
    console.print(f"  {goal_bar} {goal['minutes']}/{goal['goal']}min ({goal_pct:.0f}%)")
    console.print()

    # ─── SECTION 7: Recent Quiz Scores (Timeline) ──────────────────
    if len(progress) >= 2:
        console.print("[bold]📈 Recent Quiz Scores (Last 10):[/bold]\n")
        sorted_items = sorted(progress.items(), key=lambda x: x[1].get("completed_at", 0), reverse=True)[:10]
        sorted_items.reverse()

        max_score = max((p.get("last_accuracy", 0) for _, p in sorted_items), default=100)
        max_bar = 30

        for key, data in sorted_items:
            topic = data.get("topic", key)
            acc = data.get("last_accuracy", 0)
            score_color = "green" if acc >= 70 else "yellow" if acc >= 50 else "red"
            bar_len = int((acc / max(max_score, 1)) * max_bar)
            bar = f"[{score_color}]{'█' * bar_len}[/{score_color}][dim]{'░' * (max_bar - bar_len)}[/dim]"
            topic_short = (topic[:18] + "..") if len(topic) > 18 else topic
            ts = data.get("completed_at", 0)
            date_str = ""
            if ts > 0:
                date_str = _dt.fromtimestamp(ts).strftime("%m/%d")
            console.print(f"  {topic_short.ljust(20)} [{score_color}]{acc:5.0f}%[/{score_color}] {bar}  [dim]{date_str}[/dim]")
        console.print()

    # ─── SECTION 8: Improvement Trend ──────────────────────────────
    if len(progress) >= 3:
        console.print("[bold]📊 Improvement Trend:[/bold]\n")
        sorted_by_time = sorted(progress.items(), key=lambda x: x[1].get("completed_at", 0))
        # Split into thirds
        third = max(len(sorted_by_time) // 3, 1)
        early = sorted_by_time[:third]
        recent = sorted_by_time[-third:]

        early_avg = (sum(d.get("last_accuracy", 0) for _, d in early) / len(early)) if early else 0
        recent_avg = (sum(d.get("last_accuracy", 0) for _, d in recent) / len(recent)) if recent else 0
        diff = recent_avg - early_avg

        trend_icon = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
        trend_color = "green" if diff > 0 else "red" if diff < 0 else "white"
        console.print(f"  Early avg:  [dim]{early_avg:.0f}%[/dim]")
        console.print(f"  Recent avg: [{trend_color}]{recent_avg:.0f}%[/{trend_color}]")
        console.print(f"  Change:     [{trend_color}]{trend_icon} {diff:+.0f}pp[/{trend_color}]")
        if diff > 10:
            console.print(f"  [bold green]🌟 Excellent improvement![/bold green]")
        elif diff < -5:
            console.print(f"  [bold yellow]⚠️  Performance declining — try reviewing weak areas[/bold yellow]")
        else:
            console.print(f"  [dim]Steady progress[/dim]")
        console.print()

    # ─── SECTION 9: Mastery Levels ─────────────────────────────────
    if progress:
        console.print("[bold]🎖️  Mastery Levels:[/bold]\n")
        mastery_items = []
        for key, data in progress.items():
            acc = data.get("last_accuracy", 0)
            topic = data.get("topic", key)
            if acc >= 90: icon, color = "💎", "magenta"
            elif acc >= 75: icon, color = "🥇", "yellow"
            elif acc >= 60: icon, color = "🥈", "white"
            elif acc >= 40: icon, color = "🥉", "dim"
            else: icon, color = "⬜", "red"
            mastery_items.append((acc, icon, topic, color))
        mastery_items.sort(reverse=True)

        for acc, icon, topic, color in mastery_items[:12]:
            topic_short = (topic[:22] + "..") if len(topic) > 22 else topic
            console.print(f"  {icon} [{color}]{topic_short.ljust(24)} {acc:.0f}%[/{color}]")
        if len(mastery_items) > 12:
            console.print(f"  [dim]+ {len(mastery_items) - 12} more...[/dim]")
        console.print()

    # ─── SECTION 10: Weak Areas ────────────────────────────────────
    if progress:
        weak_areas = []
        for key, data in progress.items():
            acc = data.get("last_accuracy", 0)
            if acc < 60:
                weak_areas.append((data.get("topic", key), acc, data.get("sessions", 1)))
        if weak_areas:
            weak_areas.sort(key=lambda x: x[1])
            console.print("[bold red]⚠️  Areas Needing Review (Accuracy < 60%):[/bold red]\n")
            for topic, acc, sessions in weak_areas:
                urgency = "🔴" if acc < 30 else "🟡"
                console.print(f"  {urgency} {topic} — [red]{acc:.0f}%[/red] ({sessions} sessions)")
            console.print()
        else:
            console.print("[bold green]✅ All topics above 60%! No weak areas.[/bold green]\n")

    # ─── SECTION 11: Achievements Progress ─────────────────────────
    console.print("[bold]🏅 Achievement Progress:[/bold]\n")
    ach_rarity_counts = {"common": 0, "uncommon": 0, "rare": 0, "legendary": 0}
    for ach in achievements:
        r = ach.get("rarity", "common")
        if r in ach_rarity_counts:
            ach_rarity_counts[r] += 1

    ach_total = 24  # 15 original + 9 verse
    ach_earned = len(achievements)
    ach_pct = (ach_earned / ach_total * 100) if ach_total > 0 else 0
    ach_bar_len = int(ach_pct / 4)
    ach_bar = f"[magenta]{'█' * ach_bar_len}[/{'magenta'}][dim]{'░' * (25 - ach_bar_len)}[/dim]"
    console.print(f"  {ach_bar} {ach_earned}/{ach_total} ({ach_pct:.0f}%)\n")
    for rarity, count in ach_rarity_counts.items():
        r_icon = {"common": "⚪", "uncommon": "🟢", "rare": "🔵", "legendary": "🟣"}.get(rarity, "⚪")
        r_total = sum(1 for a in __import__("kslearn.engines.achievements", fromlist=["ACHIEVEMENTS"]).ACHIEVEMENTS.values() if a.get("rarity") == rarity)
        console.print(f"  {r_icon} {rarity.title():12s} {count}/{r_total}")
    console.print()

    # ─── SECTION 12: Study Time Estimates ──────────────────────────
    console.print("[bold]⏱️  Study Time Estimates:[/bold]\n")
    if progress:
        timestamps = [p.get("completed_at", 0) for p in progress.values() if p.get("completed_at", 0) > 0]
        if len(timestamps) >= 2:
            timestamps.sort()
            first_session = datetime.fromtimestamp(timestamps[0])
            last_session = datetime.fromtimestamp(timestamps[-1])
            span_days = (last_session - first_session).days + 1
            avg_per_week = (quizzes_completed / max(span_days / 7, 1))
            console.print(f"  First session:  {first_session.strftime('%Y-%m-%d')}")
            console.print(f"  Latest session: {last_session.strftime('%Y-%m-%d')}")
            console.print(f"  Active span:    {span_days} days")
            console.print(f"  Avg quizzes/week: [cyan]{avg_per_week:.1f}[/cyan]")
        else:
            console.print("  [dim]Need at least 2 sessions for time estimates[/dim]")
    else:
        console.print("  [dim]No quiz data yet[/dim]")
    console.print()

    # ─── SECTION 13: Predictions ───────────────────────────────────
    console.print("[bold]🔮 Predictions:[/bold]\n")
    predictions = []
    if quizzes_completed > 0:
        quizzes_to_next_achievement = max(0, 25 - quizzes_completed)
        if quizzes_to_next_achievement > 0:
            predictions.append(f"📅 {quizzes_to_next_achievement} more quizzes for 'Quiz Master' achievement")
        if current_streak > 0 and current_streak < 5:
            predictions.append(f"🔥 {5 - current_streak} more day(s) for 'Hot Streak' achievement")
        if overall_accuracy < 100:
            predictions.append("💎 100% accuracy on your next quiz would earn 'Perfectionist'")
    if verse_xp > 0:
        next_rank_xp = 200 if verse_xp < 200 else 500 if verse_xp < 500 else 1000 if verse_xp < 1000 else 2000 if verse_xp < 2000 else 3500
        remaining = next_rank_xp - verse_xp
        predictions.append(f"⭐ {remaining} more XP for next Verse rank")
    if not predictions:
        predictions.append("Start studying to see predictions here!")
    for pred in predictions:
        console.print(f"  {pred}")
    console.print()

    # ─── SECTION 14: Insights ──────────────────────────────────────
    console.print("[bold]💡 Insights:[/bold]\n")
    insights = []
    if total_questions > 0:
        if overall_accuracy >= 80:
            insights.append("🌟 You're performing at an excellent level!")
        elif overall_accuracy >= 60:
            insights.append("📈 Good progress — review weak areas to improve.")
        else:
            insights.append("📚 Consider reviewing fundamentals before advancing.")
    if current_streak >= 7:
        insights.append(f"🔥 {current_streak}-day streak! Consistent learning builds mastery.")
    elif current_streak == 0:
        insights.append("💪 Start a study session today to build your streak!")
    if len(achievements) >= 10:
        insights.append(f"🏆 {len(achievements)} achievements — you're a dedicated learner!")
    if bookmarks:
        insights.append(f"🔖 {len(bookmarks)} bookmarked topics ready for review.")
    if verse_xp > 0:
        insights.append(f"🌌 You have {verse_xp} XP in the KSL-Verse!")
    if timed_quiz_best >= 10:
        insights.append(f"⚡ Timed quiz best: {timed_quiz_best} — quick thinker!")
    if tutorials_completed > 0:
        insights.append(f"📚 {tutorials_completed} tutorial(s) completed!")
    if not insights:
        insights.append("Start your first quiz to see analytics here!")
    for insight in insights:
        console.print(f"  {insight}")
    console.print()

    # ─── Footer ────────────────────────────────────────────────────
    console.print("  [green][0][/green] Back")
    console.print()

    try:
        console.input("[bold green]╰─► Press Enter to continue...[/bold green] ")
    except KeyboardInterrupt:
        return


def _run_my_progress():
    """Merged menu: Analytics + Quiz Scores + Achievements + Export Report."""
    while True:
        clear_screen()
        console.print(get_small_banner())
        console.print()
        show_panel("📊 My Progress", "Choose what to view", "cyan")
        console.print()
        tbl = Table(box=box.ROUNDED, border_style="cyan")
        tbl.add_column("#", style="yellow", width=4)
        tbl.add_column("Option", style="bold white")
        tbl.add_column("Description", style="dim")
        tbl.add_row("1", "📈 Analytics Dashboard", "Visual charts, heatmaps, weak areas, insights")
        tbl.add_row("2", "📋 Quiz Scores", "Detailed quiz history & accuracy")
        tbl.add_row("3", "🏆 Achievements", "Badges, milestones, rarity breakdown")
        tbl.add_row("4", "📄 Export Report", "Generate Markdown progress summary")
        tbl.add_row("5", "🕒 Session History", "View past sessions & resume")
        tbl.add_row("0", "Back", "Return to main menu")
        console.print(tbl)
        console.print()
        try:
            ch = console.input("[bold green]╰─► Your choice:[/bold green] ").strip()
        except KeyboardInterrupt:
            return
        if ch == "0":
            return
        elif ch == "1":
            show_analytics()
        elif ch == "2":
            show_progress()
        elif ch == "3":
            show_achievements()
        elif ch == "4":
            export_progress_report()
        elif ch == "5":
            _run_session_history()


def _run_global_search():
    """Search all notes across every category with AI suggestions."""
    from kslearn.engines.notes_viewer import HierarchicalNotesViewer
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🔍 Global Search", "Search all notes at once", "cyan")
    console.print()
    try:
        query = console.input("[bold green]╰─► Search term:[/bold green] ").strip()
    except (KeyboardInterrupt, EOFError):
        return
    if not query:
        return
    viewer = HierarchicalNotesViewer()
    results = viewer.search_all_notes(query)
    if not results:
        console.print(Panel("[yellow]No results found.[/yellow]", box=box.ROUNDED, border_style="yellow"))
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")
        return
    console.print()
    console.print(f"[bold green]Found {len(results)} result(s):[/bold green]\n")
    for i, r in enumerate(results[:10], 1):
        cat = r.get("category", "").replace("_", " ").title()
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        # Highlight search term
        import re
        highlighted = re.sub(
            re.escape(query),
            f"[bold yellow]\\g<0>[/bold yellow]",
            snippet[:150],
            flags=re.IGNORECASE,
        )
        console.print(f"  [yellow]{i}.[/yellow] [bold white]{cat} > {title}[/bold white]")
        console.print(f"     [dim]{highlighted}[/dim]")
        console.print()
    console.print("[green][1-9][/green] [dim]Open topic[/dim]")
    console.print("[green][A][/green] [dim]Ask AI about results[/dim]")
    console.print("[green][0][/green] [dim]Back[/dim]")
    console.print()
    try:
        ch = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return
    if ch == "a":
        viewer.show_ai_suggestions("search", title=query, tags=[query])
    elif ch.isdigit():
        idx = int(ch) - 1
        if 0 <= idx < len(results):
            r = results[idx]
            run_learning_notes_with_category(r.get("category", ""), r.get("title", ""))
    console.print()
    # AI suggestions after search
    viewer.show_ai_suggestions("search", title=query, tags=[query])


def _run_study_tools():
    """Merged menu: Bookmarks + Global Search + Spaced Review."""
    while True:
        clear_screen()
        console.print(get_small_banner())
        console.print()
        show_panel("🔖 Study Tools", "Find and review content", "cyan")
        console.print()
        tbl = Table(box=box.ROUNDED, border_style="cyan")
        tbl.add_column("#", style="yellow", width=4)
        tbl.add_column("Option", style="bold white")
        tbl.add_column("Description", style="dim")
        tbl.add_row("1", "🔖 Bookmarks", "Saved topics for quick review")
        tbl.add_row("2", "🔍 Global Search", "Search all notes at once")
        tbl.add_row("3", "📅 Spaced Review", "Revisit topics you struggled with")
        tbl.add_row("0", "Back", "Return to main menu")
        console.print(tbl)
        console.print()
        try:
            ch = console.input("[bold green]╰─► Your choice:[/bold green] ").strip()
        except KeyboardInterrupt:
            return
        if ch == "0":
            return
        elif ch == "1":
            show_bookmarks()
        elif ch == "2":
            _run_global_search()
        elif ch == "3":
            from kslearn.engines.notes_viewer import run_spaced_review
            run_spaced_review()


# Global current session ID
_current_session_id = None


def _run_study_modes(session_id=None):
    """Merged menu: Flashcards + Timed Quiz + Tutorials + LearnQuest."""
    sid = session_id or _current_session_id
    while True:
        clear_screen()
        console.print(get_small_banner())
        console.print()
        show_panel("🎮 Study Modes", "Alternative learning methods", "cyan")
        console.print()
        tbl = Table(box=box.ROUNDED, border_style="cyan")
        tbl.add_column("#", style="yellow", width=4)
        tbl.add_column("Option", style="bold white")
        tbl.add_column("Description", style="dim")
        tbl.add_row("1", "🃏 Flashcards", "Card-based review with flip reveal")
        tbl.add_row("2", "⚡ Timed Quiz", "60-second speed challenge")
        tbl.add_row("3", "🎓 Tutorials", "Interactive step-by-step lessons")
        tbl.add_row("4", "🏆 LearnQuest", "Complete course assessments & export results")
        tbl.add_row("0", "Back", "Return to main menu")
        console.print(tbl)
        console.print()
        try:
            ch = console.input("[bold green]╰─► Your choice:[/bold green] ").strip()
        except KeyboardInterrupt:
            return
        if ch == "0":
            return
        elif ch == "1":
            from kslearn.engines.notes_viewer import run_flashcards
            log_activity(sid, "notes", {"type": "flashcards"})
            run_flashcards()
        elif ch == "2":
            log_activity(sid, "quiz", {"type": "timed"})
            _run_timed_quiz()
        elif ch == "3":
            from kslearn.engines.tutorials import run_tutorials_interactive
            log_activity(sid, "tutorial")
            run_tutorials_interactive()
        elif ch == "4" or ch == "Q" or ch == "QUEST":
            _run_learnquest()


def _collect_assessments_recursive(subtopics, course_id, unit_id, outcome_id=None):
    """Walk through subtopics and collect assessment quizzes."""
    assessments = []
    for subtopic in subtopics:
        st_type = subtopic.get("type", "content")
        st_title = subtopic.get("title", "Untitled")
        st_id = subtopic.get("id", "")

        if st_type == "assessment":
            quiz_questions = subtopic.get("quiz", [])
            if quiz_questions:
                assessments.append({
                    "subtopic_id": st_id,
                    "subtopic_title": st_title,
                    "unit_id": unit_id,
                    "outcome_id": outcome_id,
                    "questions": quiz_questions,
                })
        elif st_type in ("content", "activity"):
            pass
        # Recurse into nested subtopics if any
        nested = subtopic.get("subtopics", [])
        if nested:
            parent_outcome = outcome_id or st_id
            assessments.extend(_collect_assessments_recursive(nested, course_id, unit_id, parent_outcome))

    return assessments


def _run_learnquest():
    """LearnQuest: Complete hierarchical course assessments and export JSON results."""
    from kslearn.loader import content_loader
    from pathlib import Path
    import json

    while True:
        clear_screen()
        console.print(get_small_banner())
        console.print()
        show_panel("🏆 LearnQuest", "Complete course assessments & track progress", "magenta")
        console.print()

        # Load available hierarchical courses
        courses = content_loader.load_hierarchical_courses()

        if not courses:
            console.print(Panel(
                "[yellow]No hierarchical courses found.[/yellow]\n"
                "[dim]Add hierarchical .ksl files to data/ksl/ to use LearnQuest.[/dim]",
                box=box.ROUNDED,
                border_style="yellow",
            ))
            console.print()
            console.print("  [green][0][/green] Back")
            console.print()
            try:
                console.input("[bold green]╰─► Press Enter to continue...[/bold green] ")
            except KeyboardInterrupt:
                return
            return

        # Show available courses
        tbl = Table(box=box.ROUNDED, border_style="magenta")
        tbl.add_column("#", style="yellow", width=4)
        tbl.add_column("Course", style="bold white")
        tbl.add_column("Description", style="dim")
        tbl.add_column("Units", style="cyan", width=6)
        tbl.add_column("Difficulty", style="green", width=12)

        for i, course in enumerate(courses, 1):
            title = course.get("title", "Untitled")
            desc = course.get("description", "")
            difficulty = course.get("difficulty", "beginner").title()
            categories = course.get("categories", [])
            unit_count = len(categories)
            tbl.add_row(str(i), title, desc[:50], str(unit_count), difficulty)

        tbl.add_row("0", "Back", "Return to Study Modes", "", "")
        console.print(tbl)
        console.print()

        try:
            choice = console.input("[bold green]╰─► Select a course (0 to go back):[/bold green] ").strip()
        except KeyboardInterrupt:
            return

        if choice == "0":
            return

        try:
            course_idx = int(choice) - 1
            if not (0 <= course_idx < len(courses)):
                show_warning("Invalid course number!")
                time.sleep(1)
                continue
        except ValueError:
            show_warning("Please enter a number!")
            time.sleep(1)
            continue

        selected_course = courses[course_idx]
        _execute_learnquest(selected_course)


def _execute_learnquest(course):
    """Execute the LearnQuest for a specific course."""
    from pathlib import Path
    import json

    course_id = course.get("id", course.get("code", "unknown"))
    course_title = course.get("title", "Unknown Course")
    categories = course.get("categories", [])

    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel(f"🏆 LearnQuest: {course_title}", "Complete all assessments to earn your quest completion", "magenta")
    console.print()

    # Collect all assessments from the course
    all_assessments = []
    for category in categories:
        cat_title = category.get("title", "Untitled")
        units = category.get("units", [])
        for unit in units:
            unit_title = unit.get("title", "Untitled")
            unit_id = unit.get("id", "")
            outcomes = unit.get("learning_outcomes", [])
            for outcome in outcomes:
                outcome_title = outcome.get("title", "Untitled")
                outcome_id = outcome.get("id", "")
                subtopics = outcome.get("subtopics", [])
                assessments = _collect_assessments_recursive(subtopics, course_id, unit_id, outcome_id)
                for a in assessments:
                    a["category_title"] = cat_title
                    a["unit_title"] = unit_title
                    a["outcome_title"] = outcome_title
                all_assessments.extend(assessments)

    if not all_assessments:
        console.print(Panel(
            "[yellow]No assessments found in this course.[/yellow]\n"
            "[dim]This course may not have any assessment sub-topics yet.[/dim]",
            box=box.ROUNDED,
            border_style="yellow",
        ))
        console.print()
        console.print("  [green][0][/green] Back")
        console.print()
        try:
            console.input("[bold green]╰─► Press Enter to continue...[/bold green] ")
        except KeyboardInterrupt:
            pass
        return

    console.print(f"[bold]Assessments Found:[/bold] {len(all_assessments)}\n")

    # Show assessment overview
    assess_tbl = Table(box=box.ROUNDED, border_style="cyan")
    assess_tbl.add_column("#", style="yellow", width=4)
    assess_tbl.add_column("Assessment", style="bold white")
    assess_tbl.add_column("Section", style="dim")
    assess_tbl.add_column("Questions", style="cyan", width=10)

    for i, assessment in enumerate(all_assessments, 1):
        assess_tbl.add_row(
            str(i),
            assessment["subtopic_title"],
            f"{assessment.get('unit_title', '')[:25]}",
            str(len(assessment["questions"])),
        )
    console.print(assess_tbl)
    console.print()

    if not Confirm.ask("Start the LearnQuest?", default=True):
        return

    # Walk through assessments and collect answers
    all_answers = []
    total_correct = 0
    total_questions = 0

    for assessment_idx, assessment in enumerate(all_assessments, 1):
        clear_screen()
        console.print()
        console.print(Panel(
            f"[bold magenta]Assessment {assessment_idx}/{len(all_assessments)}[/bold magenta]\n"
            f"[white]{assessment['subtopic_title']}[/white]\n"
            f"[dim]{assessment.get('category_title', '')} > {assessment.get('unit_title', '')} > {assessment.get('outcome_title', '')}[/dim]",
            box=box.ROUNDED,
            border_style="magenta",
        ))
        console.print()

        questions = assessment["questions"]
        for q_idx, question_data in enumerate(questions, 1):
            question_text = question_data.get("question", "")
            options = question_data.get("options", [])
            correct_answer = question_data.get("answer", -1)
            explanation = question_data.get("explanation", "")

            # Display question
            console.print(f"[bold yellow]Question {q_idx}/{len(questions)}:[/bold yellow]")
            console.print(f"[bold white]{question_text}[/bold white]\n")

            # Display options
            opt_tbl = Table(box=box.ROUNDED, border_style="cyan")
            opt_tbl.add_column("#", style="yellow", width=4)
            opt_tbl.add_column("Option", style="white")
            for opt_idx, option in enumerate(options, 1):
                opt_tbl.add_row(str(opt_idx), option)
            console.print(opt_tbl)
            console.print()

            # Get user answer
            while True:
                try:
                    answer = console.input(
                        f"[bold green]╰─► Your answer (1-{len(options)}, or 0 to skip):[/bold green] "
                    ).strip()
                except KeyboardInterrupt:
                    answer = "0"

                if answer == "0":
                    selected = -1
                    break
                try:
                    selected = int(answer) - 1
                    if 0 <= selected < len(options):
                        break
                    else:
                        show_warning(f"Please enter 1-{len(options)} or 0 to skip!")
                except ValueError:
                    show_warning(f"Please enter a number (1-{len(options)}) or 0 to skip!")

            # Evaluate answer
            is_correct = (selected == correct_answer)
            if is_correct:
                total_correct += 1
            total_questions += 1

            # Show feedback
            if selected == -1:
                feedback_color = "dim"
                feedback = "Skipped"
            elif is_correct:
                feedback_color = "green"
                feedback = "Correct!"
            else:
                feedback_color = "red"
                feedback = f"Incorrect (Correct: {correct_answer + 1})"

            console.print(f"\n[{feedback_color}]{feedback}[/{feedback_color}]")
            if explanation:
                console.print(f"[dim]💡 {explanation}[/dim]")
            console.print()

            # Store answer
            all_answers.append({
                "question": question_text,
                "selected": selected + 1 if selected >= 0 else 0,  # 1-based, 0 = skipped
                "correct": is_correct,
                "explanation": explanation,
                "assessment": assessment["subtopic_title"],
                "category": assessment.get("category_title", ""),
                "unit": assessment.get("unit_title", ""),
                "outcome": assessment.get("outcome_title", ""),
            })

            if q_idx < len(questions):
                try:
                    console.input("[dim]Press Enter for next question...[/dim]")
                except KeyboardInterrupt:
                    pass

        if assessment_idx < len(all_assessments):
            console.print()
            try:
                console.input("[dim]Press Enter to continue to next assessment...[/dim]")
            except KeyboardInterrupt:
                pass

    # Calculate results
    accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
    timestamp = datetime.now().isoformat()
    quest_id = f"LQ-{int(datetime.now().timestamp())}"

    # Generate JSON result
    result = {
        "questId": quest_id,
        "courseId": course_id,
        "courseTitle": course_title,
        "answers": all_answers,
        "score": total_correct,
        "total": total_questions,
        "accuracy": round(accuracy, 1),
        "completedAt": timestamp,
    }

    # Show results
    clear_screen()
    console.print(get_small_banner())
    console.print()
    show_panel("🏆 LearnQuest Complete!", f"Course: {course_title}", "magenta")
    console.print()

    results_tbl = Table(box=box.ROUNDED, border_style="magenta")
    results_tbl.add_column("Metric", style="yellow")
    results_tbl.add_column("Value", style="cyan")
    results_tbl.add_row("Quest ID", quest_id)
    results_tbl.add_row("Score", f"[green]{total_correct}[/green] / [white]{total_questions}[/white]")
    acc_color = "green" if accuracy >= 70 else "yellow" if accuracy >= 50 else "red"
    results_tbl.add_row("Accuracy", f"[{acc_color}]{accuracy:.1f}%[/{acc_color}]")
    results_tbl.add_row("Completed At", timestamp)
    console.print(results_tbl)
    console.print()

    # Show JSON preview
    console.print("[bold]JSON Output Preview:[/bold]")
    json_preview = json.dumps(result, indent=2, ensure_ascii=False)
    # Show truncated preview if too long
    if len(json_preview) > 800:
        console.print(f"[dim]{json_preview[:800]}[/dim]")
        console.print(f"[dim]... ({len(json_preview) - 800} more characters)[/dim]")
    else:
        console.print(f"[dim]{json_preview}[/dim]")
    console.print()

    # Save JSON file
    learnquest_dir = Path("data/learnquest")
    learnquest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"LQ-{timestamp.replace(':', '-').replace('+', '-')}.json"
    filepath = learnquest_dir / filename

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        show_success(f"Results saved to {filepath}")
    except IOError as e:
        show_error(f"Failed to save results: {e}")

    console.print()
    console.print("  [green][S][/green] Submit to website (copy tracking code)")
    console.print("  [green][E][/green] Export JSON file")
    console.print("  [green][R][/green] Retry this course")
    console.print("  [green][0][/green] Back to Study Modes")
    console.print()

    try:
        action = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()
    except KeyboardInterrupt:
        return

    if action == "S":
        # Copy tracking code
        tracking_code = f"{quest_id}|{course_id}|{total_correct}/{total_questions}|{accuracy:.1f}%"
        console.print(f"\n[bold]Tracking Code:[/bold]")
        console.print(Panel(
            f"[cyan]{tracking_code}[/cyan]",
            box=box.ROUNDED,
            border_style="cyan",
            title="Copy this code and submit on the website",
        ))
        console.print()
        console.print("[dim]Visit the kslearn website and enter this code to record your progress.[/dim]")
        console.print()
        try:
            console.input("[dim]Press Enter to continue...[/dim]")
        except KeyboardInterrupt:
            pass
        # Retry the menu
        _execute_learnquest(course)

    elif action == "E":
        console.print(f"\n[bold]JSON File Location:[/bold]")
        console.print(f"  [cyan]{filepath.absolute()}[/cyan]")
        console.print()
        console.print("[dim]You can share this file or upload it to the website manually.[/dim]")
        console.print()
        try:
            console.input("[dim]Press Enter to continue...[/dim]")
        except KeyboardInterrupt:
            pass
        # Retry the menu
        _execute_learnquest(course)

    elif action == "R":
        # Retry the same course
        _execute_learnquest(course)


def show_progress():
    """Show user learning progress"""
    from kslearn.config import load_config

    clear_screen()
    console.print(get_small_banner())
    console.print()

    show_panel("📊 My Learning Progress", "Track your learning journey", "cyan")

    # Load progress from config
    config = load_config()
    learning_progress = config.get("learning_progress", {})

    # Calculate total stats
    quizzes_completed = len(learning_progress)
    total_correct = sum(p.get("correct", p.get("last_score", 0)) for p in learning_progress.values())
    total_questions = sum(p.get("questions", 0) for p in learning_progress.values())
    overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
    best_streak_all = max((p.get("best_streak", 0) for p in learning_progress.values()), default=0)

    # Get last study session
    last_study = "Never"
    if learning_progress:
        last_timestamp = max(p.get("completed_at", 0) for p in learning_progress.values())
        if last_timestamp > 0:
            from datetime import datetime
            last_study = datetime.fromtimestamp(last_timestamp).strftime("%Y-%m-%d %H:%M")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Metric", style="yellow")
    table.add_column("Value", style="cyan")

    table.add_row("Quizzes Completed", str(quizzes_completed))
    table.add_row("Questions Answered", str(total_questions))
    table.add_row("Correct Answers", f"[green]{total_correct}[/green]")
    table.add_row("Overall Accuracy", f"[cyan]{overall_accuracy:.0f}%[/cyan]")
    table.add_row("Best Streak", f"[red]{best_streak_all} 🔥[/red]")
    table.add_row("Last Study Session", last_study)

    console.print(table)
    console.print()

    # Category progress from learning_progress
    if learning_progress:
        console.print("[bold]Recent Activity:[/bold]\n")

        # Group by category
        categories = {}
        for key, data in learning_progress.items():
            cat = data.get("category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(data)

        for cat, items in categories.items():
            latest = max(items, key=lambda x: x.get("completed_at", 0))
            topic = latest.get("topic", "Unknown")
            correct = latest.get("correct", latest.get("last_score", 0))
            questions = latest.get("questions", 0)
            accuracy = latest.get("last_accuracy", 0)
            streak = latest.get("best_streak", 0)
            streak_str = f" [red]🔥{streak}[/red]" if streak > 0 else ""
            console.print(f"  [cyan]{cat}[/cyan]: [white]{topic}[/white] - {correct}/{questions} ([dim]{accuracy:.0f}%[/dim]){streak_str}")

    console.print()
    console.print("  [green][R][/green] Reset Progress")
    console.print("  [green][0][/green] Back")
    console.print()

    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().lower()
    except KeyboardInterrupt:
        return

    if choice == "r":
        if Confirm.ask("Reset all progress? This cannot be undone!"):
            from kslearn.config import set_config_value
            set_config_value("learning_progress", {})
            show_success("Progress reset!")
            time.sleep(1)


def export_progress_report():
    """Generate a text/Markdown progress report and save to file."""
    from kslearn.config import load_config

    config = load_config()
    progress = config.get("learning_progress", {})
    streak = config.get("study_streak", {})
    achievements = config.get("achievements", [])
    bookmarks = config.get("bookmarks", [])
    daily = config.get("daily_goal", {})
    brain_stats = content_loader.get_brain_stats()

    # Gather hierarchical course progress
    hier_completed = 0
    hier_total = 0
    hier_outcomes_done = 0
    hier_courses_seen = set()
    hier_units_seen = set()
    for key, data in progress.items():
        if key.startswith("hier_") and data.get("completed", False):
            hier_completed += 1
            if data.get("course_title"):
                hier_courses_seen.add(data["course_title"])
            if data.get("unit_title"):
                hier_units_seen.add(data["unit_title"])
        if key.startswith("hier_outcome_") and data.get("completed", False):
            hier_outcomes_done += 1
            hier_total += 1

    lines = [
        "# kslearn Progress Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Overview",
        f"- Quizzes Completed: {len(progress)}",
        f"- Study Streak: {streak.get('current', 0)} days (Best: {streak.get('best', 0)})",
        f"- Brain Entries: {brain_stats['total_qa_pairs']}",
        f"- Bookmarks: {len(bookmarks)}",
        f"- Achievements: {len(achievements)}/15",
        "",
    ]

    # Hierarchical course progress section
    if hier_completed > 0 or hier_courses_seen:
        lines.append("## Course Progress (Hierarchical)")
        lines.append("")
        lines.append(f"- Courses Started: {len(hier_courses_seen)}")
        lines.append(f"- Units Explored: {len(hier_units_seen)}")
        lines.append(f"- Outcomes Completed: {hier_outcomes_done}")
        lines.append(f"- Sub-topics Completed: {hier_completed}")
        lines.append("")

    # Per-category breakdown
    categories = {}
    for key, data in progress.items():
        cat = data.get("category", "unknown")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(data)

    for cat, items in sorted(categories.items()):
        total_correct = sum(i.get("correct", 0) for i in items)
        total_questions = sum(i.get("questions", 1) for i in items)
        avg_acc = sum(i.get("last_accuracy", 0) for i in items) / len(items)
        best_streak = max(i.get("best_streak", 0) for i in items)

        lines.append(f"### {cat.replace('_', ' ').title()}")
        lines.append(f"- Sessions: {len(items)}")
        lines.append(f"- Correct: {total_correct}/{total_questions} ({avg_acc:.0f}%)")
        lines.append(f"- Best Streak: {best_streak}")
        lines.append("")

    if achievements:
        lines.append("## Achievements Earned")
        lines.append("")
        for a in achievements:
            lines.append(f"- {a.get('icon', '⭐')} **{a.get('name', 'Unknown')}** — {a.get('description', '')}")
        lines.append("")

    if bookmarks:
        lines.append("## Bookmarked Topics")
        lines.append("")
        for b in bookmarks:
            lines.append(f"- {b.get('category', '').replace('_', ' ').title()} > {b.get('topic', '')}")
        lines.append("")

    report = "\n".join(lines)

    console.clear()
    console.print()
    show_panel("📄 Export Progress Report", "Generate a summary of your learning", "cyan")
    console.print()

    try:
        filename = console.input("[bold yellow]╰─► Save as (default: kslearn_report.md):[/bold yellow] ").strip()
    except KeyboardInterrupt:
        return

    if not filename:
        filename = "kslearn_report.md"

    try:
        from pathlib import Path
        path = Path(filename).expanduser()
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)

        show_panel(
            f"[green]✓ Report saved![/green]\n"
            f"[dim]{path} ({len(lines)} lines)[/dim]",
            "green",
        )
    except IOError as e:
        show_error(f"Could not save report: {e}")

    console.print()
    console.input("[bold green]╰─► Press Enter to continue...[/bold green]")


def _run_session_history():
    """View session history and resume past sessions."""
    from kslearn.config import get_sessions, get_session_stats, resume_session, generate_session_summary
    from kslearn.ui import show_session_end_card

    while True:
        clear_screen()
        console.print(get_small_banner())
        console.print()
        show_panel("🕒 Session History", "View and resume past sessions", "cyan")
        console.print()

        # Show overall stats
        stats = get_session_stats()
        if stats["total_sessions"] > 0:
            console.print(f"[dim]Total Sessions: {stats['total_sessions']} | Total Time: {stats['total_duration_minutes']:.1f}m | Avg: {stats['avg_duration_minutes']:.1f}m[/dim]")
            console.print(f"[dim]Quizzes: {stats['total_quizzes']} | Notes: {stats['total_notes']} | AI Chats: {stats['total_ai_chats']} | Verse: {stats['total_verse_sessions']}[/dim]")
            console.print()

        # Get recent sessions
        sessions = get_sessions(10)
        if not sessions:
            console.print(Panel("[yellow]No sessions recorded yet.[/yellow]", box=box.ROUNDED, border_style="yellow"))
            console.print()
            console.input("[bold green]╰─► Press Enter to continue...[/bold green]")
            return

        # Display sessions table
        tbl = Table(box=box.ROUNDED, border_style="cyan")
        tbl.add_column("#", style="yellow", width=4)
        tbl.add_column("Session ID", style="cyan", width=12)
        tbl.add_column("Date", style="white", width=12)
        tbl.add_column("Duration", style="green", width=10)
        tbl.add_column("Activities", style="dim", width=20)
        tbl.add_column("Status", style="white", width=10)

        for i, session in enumerate(sessions, 1):
            session_id = session.get("id", "")
            session_id_short = session_id[:8] if session_id else "N/A"

            start_time = session.get("start_time", "N/A")
            date_str = start_time.split(" ")[0] if start_time != "N/A" else "N/A"

            duration = session.get("duration_minutes", 0)
            if duration > 0:
                duration_str = f"{duration:.1f}m"
            else:
                duration_str = "Active"

            activities = []
            if session.get("quizzes_taken", 0) > 0:
                activities.append(f"Q:{session['quizzes_taken']}")
            if session.get("notes_viewed", 0) > 0:
                activities.append(f"N:{session['notes_viewed']}")
            if session.get("ai_chats", 0) > 0:
                activities.append(f"AI:{session['ai_chats']}")
            if session.get("verse_sessions", 0) > 0:
                activities.append(f"V:{session['verse_sessions']}")
            activities_str = " ".join(activities) if activities else "—"

            is_ended = session.get("end_time") is not None
            status = "Ended" if is_ended else "[green]Active[/green]"

            resumed_from = session.get("resumed_from")
            if resumed_from:
                status += " ↩️"

            tbl.add_row(str(i), session_id_short, date_str, duration_str, activities_str, status)

        console.print(tbl)
        console.print()
        console.print("[green][1-10][/green] [dim]View session details[/dim]")
        console.print("[green][R][/green] [dim]Resume a session[/dim]")
        console.print("[green][0][/green] [dim]Back[/dim]")
        console.print()

        try:
            ch = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            return

        if ch == "0":
            return
        elif ch == "R":
            # Resume a session
            try:
                session_num = console.input("[bold green]╰─► Session number to resume:[/bold green] ").strip()
                if session_num.isdigit():
                    idx = int(session_num) - 1
                    if 0 <= idx < len(sessions):
                        session = sessions[idx]
                        session_id_to_resume = session.get("id")
                        new_session_id = resume_session(session_id_to_resume)
                        if new_session_id:
                            show_panel(f"[green]✓ Session resumed![/green]", f"New session ID: {new_session_id[:8]}", "green")
                        else:
                            show_error("Failed to resume session")
            except (KeyboardInterrupt, EOFError, ValueError):
                pass
        elif ch.isdigit():
            idx = int(ch) - 1
            if 0 <= idx < len(sessions):
                session = sessions[idx]
                summary = generate_session_summary(session.get("id"))
                console.print()
                show_session_end_card(summary)
                console.input("[bold green]╰─► Press Enter to continue...[/bold green]")


def show_bookmarks():
    """Show bookmarked topics"""
    from kslearn.config import load_config, set_config_value

    clear_screen()
    console.print(get_small_banner())
    console.print()

    show_panel("🔖 My Bookmarks", "Saved topics for quick access", "cyan")

    # Load bookmarks from config
    config = load_config()
    bookmarks = config.get("bookmarks", [])

    if not bookmarks:
        console.print()
        console.print(Panel(
            "[yellow]No bookmarks yet.[/yellow]\n[dim]Tip: While viewing a topic, press 'B' to bookmark it[/dim]",
            box=box.ROUNDED,
            border_style="yellow",
        ))
    else:
        table = Table(box=box.ROUNDED, border_style="cyan")
        table.add_column("#", style="yellow", width=4)
        table.add_column("Category", style="bold white")
        table.add_column("Topic", style="cyan")
        table.add_column("Saved", style="dim")

        for i, bm in enumerate(bookmarks, 1):
            saved_at = bm.get("bookmarked_at", "")
            table.add_row(
                str(i),
                bm.get("category", "Unknown").replace("_", " ").title(),
                bm.get("topic", "Unknown"),
                saved_at if saved_at else "",
            )

        console.print(table)

    console.print()
    console.print("  [green][1-9][/green] [dim]Open bookmark[/dim]")
    console.print("  [green][R][/green] [dim]Remove bookmark[/dim]")
    console.print("  [green][0][/green] [dim]Back[/dim]")
    console.print()

    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip()
    except KeyboardInterrupt:
        return

    if choice == "0":
        return
    elif choice.lower() == "r" and bookmarks:
        try:
            idx = int(console.input("Remove bookmark # (1-9): ").strip()) - 1
            if 0 <= idx < len(bookmarks):
                removed = bookmarks.pop(idx)
                set_config_value("bookmarks", bookmarks)
                console.print(Panel(
                    f"[green]✓ Removed:[/green] {removed.get('topic', 'Unknown')}",
                    box=box.ROUNDED,
                    border_style="green",
                ))
                time.sleep(1.5)
                show_bookmarks()  # Refresh display
        except (ValueError, KeyboardInterrupt):
            pass
    elif choice.isdigit() and bookmarks:
        idx = int(choice) - 1
        if 0 <= idx < len(bookmarks):
            bm = bookmarks[idx]
            from kslearn.engines.notes_viewer import NotesViewer
            viewer = NotesViewer()
            notes_data = viewer.load_notes(bm.get("category", ""))
            if notes_data:
                viewer.show_topics(bm.get("category", ""), notes_data)


@main.command()
def daily():
    """Show today's recommended lesson"""
    from datetime import datetime
    import hashlib
    
    clear_screen()
    console.print(get_small_banner())
    console.print()
    
    show_panel("📅 Today's Lesson", "Daily recommended learning", "cyan")
    
    # Get config for focus track
    config = load_config()
    focus = config.get("focus_track", "general")
    daily_minutes = config.get("daily_goal_minutes", 30)
    
    # Generate daily topic based on date and focus
    today = datetime.now().strftime("%Y-%m-%d")
    day_hash = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)
    
    # Load notes for focus track
    notes = content_loader.load_notes(focus)
    
    if notes and "topics" in notes:
        topics = notes["topics"]
        topic_idx = day_hash % len(topics)
        topic = topics[topic_idx]
        
        console.print(f"\n[bold cyan]Category:[/bold cyan] {notes['metadata'].get('title', focus)}")
        console.print(f"[bold yellow]Today's Topic:[/bold yellow] {topic.get('title', 'Unknown')}")
        console.print(f"[bold green]Estimated Time:[/bold green] {daily_minutes} minutes")
        console.print()

        # Show brief content preview
        content = topic.get("content", "")[:500]
        console.print(f"[dim]{content}...[/dim]\n")

        console.print("  [green][S][/green] Start this lesson")
        console.print("  [green][Q][/green] Take related quiz")
        console.print("  [green][N][/green] New random lesson")
        console.print("  [green][0][/green] Back")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().lower()
        except KeyboardInterrupt:
            return

        if choice == "s":
            run_learning_notes_with_category(focus)
        elif choice == "q":
            # Use QuizEngine to find and run quiz
            from kslearn.engines.quiz_engine import QuizEngine
            engine = QuizEngine()
            quiz_data = engine.load_quiz(focus)
            if quiz_data:
                topic = engine.select_topic(quiz_data)
                if topic:
                    topic_title = topic.get("title", f"Topic {topic.get('id', '?')}")
                    questions = topic.get("questions", [])
                    if questions:
                        engine.run_quiz(focus, topic_title, questions)
                        return
            show_warning(f"No quiz found for track '{focus}'")
            time.sleep(1)
        elif choice == "n":
            rand_topic = random.choice(topics)
            console.print(f"\n[yellow]Random topic:[/yellow] {rand_topic.get('title')}")
            time.sleep(2)
    else:
        show_warning(f"No learning materials found for {focus}")
        console.print("\n[dim]Set your focus track in settings or run 'kslearn study'[/dim]")
        time.sleep(2)


@main.command()
def notes():
    """Quick access to learning notes (alias for 'study')"""
    run_learning_notes()


@main.command()
def today():
    """Alias for daily lesson"""
    ctx = click.get_current_context()
    ctx.invoke(daily)


@main.command()
def support():
    """Show support options and social links"""
    run_support()


@main.command()
def list_systems():
    """List all available learning systems"""
    console.print()
    show_panel("Available Learning Systems", "All quiz systems organized by track", "cyan")

    tracks = get_learning_tracks()
    
    for track_key, track in tracks.items():
        console.print(f"\n[bold cyan]{track['name']}[/bold cyan]")
        console.print(f"[dim]{track['description']}[/dim]\n")

        table = Table(box=box.ROUNDED, border_style="cyan", show_header=False)
        table.add_column("System", style="bold white")
        table.add_column("Description", style="dim")

        for system_key, system_info in track["systems"].items():
            name = system_info.get("name", system_key.replace("_", " ").title())
            desc = system_info.get("description", "")
            table.add_row(name, desc)

        console.print(table)

    console.print()
    show_info("Use 'kslearn quiz' to browse and start quizzes")
    show_info("Content is loaded from JSON files in kslearn/data/")


def run_system(system_key: str):
    """Import and run a learning system module - Uses centralized QuizEngine instead"""
    # Redirect to QuizEngine for JSON-based quizzes
    from kslearn.engines.quiz_engine import QuizEngine

    engine = QuizEngine()
    quiz_data = engine.load_quiz(system_key)

    if quiz_data:
        topic = engine.select_topic(quiz_data)
        if topic:
            # topic is a dict from the topics array
            topic_title = topic.get("title", f"Topic {topic.get('id', '?')}")
            questions = topic.get("questions", [])
            if questions:
                engine.run_quiz(system_key, topic_title, questions)
                return

    show_error(f"Quiz not found or has no questions: {system_key}")
    show_info("Make sure .ksl files exist in kslearn/data/ksl/")


def run_learning_notes():
    """Run the learning notes engine"""
    try:
        from kslearn.engines.notes_viewer import run_notes_interactive
        run_notes_interactive()
    except Exception as e:
        show_error(f"Failed to load learning notes: {e}")
        console.input("\n[bold yellow]Press Enter to continue...[/bold yellow]")


def run_learning_notes_with_category(category: str):
    """Run learning notes starting at a specific category"""
    try:
        from kslearn.main.learning_notes import show_topic_menu
        show_topic_menu(category)
    except Exception as e:
        show_error(f"Failed to load learning notes: {e}")
        run_learning_notes()


def run_ai_chat():
    """Run the AI chat interface"""
    try:
        # Check if tgpt is available before launching chat
        import shutil
        tgpt_path = shutil.which("tgpt")
        if not tgpt_path:
            # Check common Termux paths
            import os
            termux_paths = [
                "/data/data/com.termux/files/usr/bin/tgpt",
                "/data/data/com.termux/files/usr/bin/termux-ai",
            ]
            for path in termux_paths:
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    tgpt_path = path
                    break
        
        if not tgpt_path:
            show_error("tgpt/termux-ai not found!")
            show_info("Install with: pkg install termux-ai")
            show_info("Or visit: https://github.com/Anon4You/Termux-Ai")
            console.input("\n[bold yellow]Press Enter to continue...[/bold yellow]")
            return
        
        from kslearn.main.ai_chat import ai_chat_interface
        ai_chat_interface()
    except Exception as e:
        show_error(f"Failed to load AI chat: {e}")


def run_ai_config():
    """Run the AI configuration menu"""
    try:
        # Check if tgpt is available
        import shutil
        import os
        tgpt_path = shutil.which("tgpt")
        if not tgpt_path:
            termux_paths = [
                "/data/data/com.termux/files/usr/bin/tgpt",
                "/data/data/com.termux/files/usr/bin/termux-ai",
            ]
            for path in termux_paths:
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    tgpt_path = path
                    break
        
        if not tgpt_path:
            show_error("tgpt/termux-ai not found!")
            show_info("Install with: pkg install termux-ai")
            console.input("\n[bold yellow]Press Enter to continue...[/bold yellow]")
            return
        
        from kslearn.main.ai_chat import ai_config_menu
        ai_config_menu()
    except Exception as e:
        show_error(f"Failed to load AI config: {e}")


def run_datastore():
    """Open kslearn Data Store in browser"""
    try:
        import webbrowser
        
        console.print()
        console.print(Panel(
            "[bold cyan]🏪 Opening kslearn Data Store...[/bold cyan]\n\n"
            "[dim]Browse free & premium learning content[/dim]\n"
            "[green]💝 Support kslearn while learning![/green]",
            box=box.ROUNDED,
            border_style="cyan",
            title="📦",
        ))
        console.print()
        
        # Open the official store URL
        store_url = "https://kashsight-4cbb8.web.app/kslearn.html"
        webbrowser.open(store_url)
        
        console.print("[dim]Opening in your default browser...[/dim]\n")
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")
        
    except Exception as e:
        show_error(f"Failed to open data store: {e}")
        console.input("\n[bold yellow]Press Enter to continue...[/bold yellow]")


def run_support():
    """Run the support module"""
    try:
        from kslearn.main import support
        if hasattr(support, "main"):
            support.main()
    except Exception as e:
        show_error(f"Failed to load support menu: {e}")


def _run_timed_quiz():
    """Run a 60-second timed quiz challenge."""
    from kslearn.engines.quiz_engine import QuizEngine, run_timed_quiz
    from kslearn.loader import content_loader

    engine = QuizEngine()
    quizzes = engine.get_available_quizzes()
    if not quizzes:
        show_error("No quizzes available!")
        time.sleep(2)
        return

    console.clear()
    console.print()
    show_panel("⚡ Speed Quiz Challenge", "Choose a quiz and answer as many as you can in 60 seconds!", "yellow")
    console.print()

    for i, q in enumerate(quizzes, 1):
        desc = q.get("description", q.get("key", ""))
        console.print(f"  [green]{i}.[/green] {q['title']} — [dim]{desc}[/dim]")

    console.print()
    try:
        choice = int(console.input("[bold green]╰─► Select quiz (1-{}):[/bold green] ".format(len(quizzes))).strip()) - 1
        if 0 <= choice < len(quizzes):
            selected = quizzes[choice]
            quiz_data = content_loader.load_quiz(selected["key"])
            if quiz_data and "topics" in quiz_data:
                all_questions = []
                for topic_item in quiz_data["topics"]:
                    all_questions.extend(topic_item.get("questions", []))
                import random
                random.shuffle(all_questions)
                run_timed_quiz(engine, selected["key"], all_questions)
        else:
            show_error("Invalid selection!")
            time.sleep(1)
    except (ValueError, KeyboardInterrupt):
        pass


def _run_global_search():
    """Search across all notes."""
    from kslearn.engines.notes_viewer import global_notes_search

    console.clear()
    console.print()
    try:
        query = console.input("[bold yellow]╰─► Search all notes for:[/bold yellow] ").strip()
        if query:
            global_notes_search(query)
    except KeyboardInterrupt:
        pass


def show_achievements():
    """Display achievements and badges."""
    from kslearn.engines.achievements import check_achievements, get_achievement_summary, ACHIEVEMENTS, RARITY_COLORS

    clear_screen()
    console.print(get_small_banner())
    console.print()

    show_panel("🏆 Achievements & Badges", "Your learning milestones", "magenta")
    console.print()

    # Check for new achievements
    config = load_config()
    progress = config.get("learning_progress", {})
    new_achs = check_achievements(config, progress, content_loader.get_brain_stats().get("total_qa_pairs", 0))

    if new_achs:
        for ach in new_achs:
            console.print(Panel(
                f"[bold green]🎉 New Achievement Unlocked![/bold green]\n\n"
                f"{ach.get('icon', '⭐')} [bold]{ach.get('name', '')}[/bold]\n"
                f"[dim]{ach.get('description', '')}[/dim]",
                box=box.ROUNDED,
                border_style="green",
            ))
            console.print()
            time.sleep(1)

    # Summary
    summary = get_achievement_summary(config)

    console.print(f"[bold]Progress:[/bold] {summary['earned']}/{summary['total']} ({summary['percentage']:.0f}%)")
    console.print()

    # By rarity
    for rarity, color in RARITY_COLORS.items():
        count = summary["by_rarity"].get(rarity, 0)
        total_r = sum(1 for a in ACHIEVEMENTS.values() if a.get("rarity") == rarity)
        console.print(f"  [{'bright_' + color if color != 'white' else 'white'}]{rarity.title()}:[/{'bright_' + color if color != 'white' else 'white'}] {count}/{total_r}")

    console.print()

    # List all
    console.print("[bold]All Achievements:[/bold]\n")
    table = Table(box=box.ROUNDED, border_style="magenta")
    table.add_column("", style="white", width=4)
    table.add_column("Achievement", style="bold white")
    table.add_column("Description", style="dim")
    table.add_column("Rarity", style="yellow")

    earned_ids = set(a.get("id", "") for a in config.get("achievements", []))

    for ach_id, ach in ACHIEVEMENTS.items():
        earned = ach_id in earned_ids
        icon = ach.get("icon", "⭐") if earned else "🔒"
        name = ach.get("name", "") if earned else "[dim]???[/dim]"
        desc = ach.get("description", "") if earned else "[dim]???[/dim]"
        rarity_color = RARITY_COLORS.get(ach.get("rarity", "common"), "white")
        table.add_row(icon, name, desc, f"[{rarity_color}]{ach.get('rarity', '').title()}[/{rarity_color}]")

    console.print(table)
    console.print()
    console.input("[bold green]╰─► Press Enter to continue...[/bold green]")


def manage_profiles():
    """Manage user profiles — login online or manage local profiles."""
    from kslearn.config import list_profiles, create_profile, switch_profile, get_active_profile, load_config
    from kslearn.online.online_mode import run_online_mode
    from kslearn.online.firebase_rtdb import get_firebase

    clear_screen()
    console.print(get_small_banner())
    console.print()

    show_panel("👤 Profile & Account", "Login online or manage local profiles", "cyan")
    console.print()

    firebase = get_firebase()
    is_logged_in = firebase.load_session() and firebase.is_logged_in()

    if is_logged_in:
        console.print(f"[bold cyan]🌐 Online:[/bold cyan] Logged in as [bold white]{firebase.user_data.get('username', 'User')}[/bold white]")
        console.print(f"[dim]   XP: {firebase.user_data.get('total_xp', 0)} | Level: {firebase.user_data.get('level', 1)}[/dim]\n")
    else:
        console.print("[yellow]🌐 Online:[/yellow] Not logged in")
        console.print("[dim]   Login to sync stats, play with friends, share worlds[/dim]\n")

    # Show local profiles
    profiles = list_profiles()
    active = get_active_profile()
    cfg = load_config()

    if profiles:
        console.print(f"[bold]Active Local Profile:[/bold] [cyan]{cfg.get('profiles', {}).get(cfg.get('active_profile', 'default'), {}).get('name', 'Default User')}[/cyan]\n")
        table = Table(box=box.ROUNDED, border_style="dim")
        table.add_column("#", style="yellow", width=4)
        table.add_column("Name", style="white")
        table.add_column("Created", style="dim")
        table.add_column("Active", style="green")

        for i, (key, prof) in enumerate(profiles.items(), 1):
            is_active = "◄ HERE" if key == cfg.get("active_profile", "default") else ""
            table.add_row(str(i), prof.get("name", key), prof.get("created", ""), is_active)

        console.print(table)

    console.print()
    console.print("  [green][1][/green] [dim]Login to online account (sync stats, play online)[/dim]")
    console.print("  [green][2][/green] [dim]Create new online account[/dim]")
    if is_logged_in:
        console.print("  [green][3][/green] [dim]Open online menu[/dim]")
        console.print("  [green][4][/green] [dim]Logout from online[/dim]")
        start_local = 5
    else:
        console.print("  [green][3][/green] [dim]Continue as guest[/dim]")
        start_local = 4

    if profiles:
        console.print(f"  [green][{start_local}][/green] [dim]Switch local profile[/dim]")
        console.print(f"  [green][{start_local+1}][/green] [dim]Create local profile[/dim]")

    console.print("  [green][0][/green] Back")
    console.print()

    try:
        choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()
    except KeyboardInterrupt:
        return

    if choice == "0":
        return
    elif choice == "1":
        from kslearn.online.online_mode import run_online_mode
        run_online_mode()
    elif choice == "2":
        from kslearn.online.firebase_rtdb import FirebaseRTDB, read_password_masked
        from rich.prompt import Prompt
        fb = get_firebase()
        username = Prompt.ask("Username").strip()
        email = Prompt.ask("Email").strip()
        password = read_password_masked("Password").strip()
        confirm = read_password_masked("Confirm").strip()
        if password != confirm:
            show_error("Passwords do not match")
            console.input("[dim]Press Enter...[/dim]")
            return
        if len(password) < 6:
            show_error("Password must be at least 6 characters")
            console.input("[dim]Press Enter...[/dim]")
            return
        with console.status("[bold cyan]Creating account...", spinner="dots"):
            ok = fb.signup(email, password, username)
        if ok:
            with console.status("[bold cyan]Syncing offline stats...", spinner="dots"):
                fb.sync_offline_stats()
            show_success(f"Account created! Welcome {username}!")
        console.input("[dim]Press Enter...[/dim]")
    elif choice == "3" and is_logged_in:
        run_online_mode()
    elif choice == "4" and is_logged_in:
        firebase.logout()
        show_info("Logged out successfully")
        console.input("[dim]Press Enter...[/dim]")
    elif choice == "3" and not is_logged_in:
        firebase.login_anonymous()
        show_info(f"Guest mode: {firebase.user_data.get('username', 'Guest')}")
        console.input("[dim]Press Enter...[/dim]")
    else:
        idx_map = {}
        if profiles:
            if is_logged_in:
                idx_map[str(5)] = "switch"
                idx_map[str(6)] = "create"
            else:
                idx_map[str(4)] = "switch"
                idx_map[str(5)] = "create"

        if choice in idx_map:
            action = idx_map[choice]
            if action == "switch":
                profile_keys = list(profiles.keys())
                try:
                    idx = int(console.input("[bold green]╰─► Profile number:[/bold green] ").strip()) - 1
                    if 0 <= idx < len(profile_keys):
                        key = profile_keys[idx]
                        if switch_profile(key):
                            show_success(f"Switched to '{profiles[key]['name']}'!")
                        else:
                            show_error("Failed to switch!")
                except ValueError:
                    show_error("Invalid selection!")
                console.input("[dim]Press Enter...[/dim]")
            elif action == "create":
                try:
                    name = console.input("[bold yellow]Profile ID (no spaces):[/bold yellow] ").strip().lower()
                    display = console.input("[bold yellow]Display Name:[/bold yellow] ").strip()
                    if name and display:
                        result = create_profile(name, display)
                        if result:
                            show_success(f"Profile '{display}' created!")
                        else:
                            show_error("Profile already exists!")
                    else:
                        show_error("Name and display name required!")
                except KeyboardInterrupt:
                    pass
                console.input("[dim]Press Enter...[/dim]")
        else:
            show_error("Invalid selection!")
            console.input("[dim]Press Enter...[/dim]")


@main.command(name="chat")
def chat_cmd():
    """Start AI chat (online or offline)"""
    run_ai_chat()


@main.command(name="ai-config")
def ai_config_cmd():
    """Configure AI chat provider and API key"""
    run_ai_config()


@main.command(name="protect")
@click.option("--key", "-k", type=str, help="Set the master access key")
def protect_cmd(key):
    """
    Protect content files with access key verification.

    This signs all JSON content files and requires the master key
    for any future modifications. Prevents unauthorized tampering
    of notes, quizzes, and configuration data.

    Examples:

    \b
        kslearn protect              # Interactive key prompt
        kslearn protect --key SECRET # Set key directly
    """
    from kslearn.protector import (
        has_master_key,
        protect_content_with_key,
        verify_all_content,
        authorize_content_edit,
    )

    if has_master_key():
        console.print()
        show_warning("A master key is already set!")
        console.print("[dim]To re-sign content with the existing key, use: kslearn verify[/dim]")
        console.print("[dim]Key changes are not supported for security reasons.[/dim]")
        return

    console.clear()
    console.print()
    show_panel("🔐 Protect Content Files", "Set a master access key to sign all content", "magenta")
    console.print()
    console.print("[bold white]This will:[/bold white]")
    console.print("  [green]✓[/green] Sign all notes, quizzes, and config JSON files")
    console.print("  [green]✓[/green] Require the key for future content modifications")
    console.print("  [green]✓[/green] Detect any unauthorized tampering")
    console.print()

    if key:
        secret = key.strip()
    else:
        console.print("[bold yellow]Choose a strong passphrase or secret key:[/bold yellow]")
        secret = Prompt.ask("[bold green]╰─► Master access key[/bold green]", password=True)
        console.print()
        confirm = Prompt.ask("[bold yellow]╰─► Confirm key[/bold yellow]", password=True)
        if secret != confirm:
            show_error("Keys do not match!")
            return
        if len(secret) < 4:
            show_error("Key must be at least 4 characters!")
            return

    if protect_content_with_key(secret):
        console.print()
        show_success("Content files protected!")
        console.print("[dim]Your key has been saved. Run 'kslearn verify' anytime to check file integrity.[/dim]")
    else:
        show_error("Failed to set master key.")


@main.command(name="verify")
def verify_cmd():
    """Verify content file integrity — check for tampering"""
    from kslearn.protector import has_master_key, verify_all_content

    console.print()
    show_panel("🔍 Content Integrity Check", "Verifying all JSON content files", "cyan")
    console.print()

    if not has_master_key():
        show_warning("No master key is set. Run 'kslearn protect' first.")
        return

    all_valid, issues = verify_all_content()

    if all_valid:
        show_success("All content files verified — no tampering detected!")
    else:
        console.print()
        show_error(f"Integrity issues found ({len(issues)}):")
        console.print()
        for issue in issues:
            if "TAMPERED" in issue:
                console.print(f"  [bold red]🚫 {issue}[/bold red]")
            elif "MISSING" in issue:
                console.print(f"  [bold yellow]📁 {issue}[/bold yellow]")
            else:
                console.print(f"  [dim]• {issue}[/dim]")
        console.print()
        show_info("Run 'kslearn protect' to re-sign content if you made legitimate changes.")


@main.command(name="verse")
def verse_cmd():
    """Launch the KSL-Verse interactive learning game"""
    from kslearn.engines.verse_engine import run_verse_interactive
    run_verse_interactive()


@main.command(name="online")
@click.argument("action", required=False)
@click.argument("session_id", required=False)
def online_cmd(action, session_id):
    """
    Online mode - Connect with friends and compete globally.
    
    Actions:
      (none)  - Open online mode menu
      join    - Join a game session
      status  - Show online status
    """
    if action == "join":
        if not session_id:
            from rich.prompt import Prompt
            session_id = Prompt.ask("Enter session ID")
        
        if not session_id:
            show_error("Session ID required")
            return
        
        from kslearn.online.firebase_rtdb import get_firebase
        from kslearn.online.online_mode import _join_game_session
        
        firebase = get_firebase()
        if not firebase.load_session():
            show_error("Not logged in. Run 'kslearn online' to login first.")
            return
        
        _join_game_session(firebase)
    elif action == "status":
        from kslearn.online.firebase_rtdb import get_firebase
        firebase = get_firebase()
        
        if firebase.load_session():
            show_success(f"Logged in as: {firebase.user_data.get('username', 'Unknown')}")
            console.print(f"[dim]User ID: {firebase.user_id}[/dim]")
            console.print(f"[dim]Status: {firebase.user_data.get('status', 'offline')}[/dim]")
        else:
            show_warning("Not logged in")
    else:
        from kslearn.online.online_mode import run_online_mode
        run_online_mode()


@main.command(name="share")
@click.option("--world", "-w", type=str, help="World ID to share")
def share_world_cmd(world):
    """Upload a world to the ksverse for others to download"""
    from kslearn.online.firebase_rtdb import get_firebase
    from kslearn.online.online_mode import _upload_world
    
    firebase = get_firebase()
    if not firebase.load_session():
        show_error("Not logged in. Run 'kslearn online' to login first.")
        return
    
    if world:
        # Upload specific world
        from pathlib import Path
        data_dir = Path.home() / ".kslearn" / "data" / "ksl"
        world_file = data_dir / f"{world}_verse.json"
        
        if not world_file.exists():
            show_error(f"World file not found: {world_file}")
            return
        
        from rich.prompt import Prompt
        title = Prompt.ask("World title")
        description = Prompt.ask("Description", default="")
        
        import json
        with open(world_file, "r") as f:
            world_data = json.load(f)
        
        with console.status("[bold cyan]Uploading world...", spinner="dots"):
            success = firebase.upload_world(world, world_data, title, description)
        
        if success:
            show_success(f"World '{title}' uploaded to ksverse!")
        else:
            show_error("Failed to upload world")
    else:
        _upload_world(firebase)


@main.command(name="leaderboard")
@click.option("--xp", is_flag=True, help="Show XP leaderboard")
@click.option("--scores", is_flag=True, help="Show scores leaderboard")
def leaderboard_cmd(xp, scores):
    """View global leaderboards"""
    from kslearn.online.firebase_rtdb import get_firebase
    from kslearn.online.online_mode import _show_xp_leaderboard, _show_scores_leaderboard
    
    firebase = get_firebase()
    if not firebase.load_session():
        show_error("Not logged in. Run 'kslearn online' to login first.")
        return
    
    if xp:
        _show_xp_leaderboard(firebase)
    elif scores:
        _show_scores_leaderboard(firebase)
    else:
        from kslearn.online.online_mode import _show_leaderboards
        _show_leaderboards(firebase)


# Entry point
if __name__ == "__main__":
    main()
