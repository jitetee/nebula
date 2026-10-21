#!/usr/bin/env python3
"""Interactive Tutorials — step-by-step guided lessons loaded from notes JSON files"""

import time
from typing import Dict, List, Optional

from kslearn.loader import content_loader
from kslearn.ui import console, show_panel, show_success, show_error, show_info, print_divider
from kslearn.config import load_config, save_config
from rich.panel import Panel
from rich.table import Table
from rich import box


def build_tutorials_from_notes() -> List[Dict]:
    """Build tutorial definitions dynamically from notes JSON files.

    Each notes topic becomes a tutorial step.
    key_points become quiz questions.
    """
    tutorials = []
    categories = content_loader.get_all_notes_categories()

    for cat_info in categories:
        cat = cat_info["key"] if isinstance(cat_info, dict) else cat_info
        notes_data = content_loader.load_notes(cat)
        if not notes_data:
            continue

        metadata = notes_data.get("metadata", {})
        cat_title = metadata.get("title", cat.replace("_", " ").title())
        cat_icon = metadata.get("icon", "📖")
        cat_desc = metadata.get("description", "")

        # Each topic becomes a tutorial
        topics = notes_data.get("topics", [])
        for topic in topics:
            topic_title = topic.get("title", "")
            topic_icon = topic.get("icon", "📄")
            topic_content = topic.get("content", "")
            key_points = topic.get("key_points", [])
            examples = topic.get("examples", [])

            # Build quiz from key_points (turn each key point into a question)
            tutorial_quiz = []
            for i, kp in enumerate(key_points[:5]):  # Max 5 quiz questions per topic
                # Generate a question from the key point
                tutorial_quiz.append({
                    "question": f"True or False: {kp}",
                    "options": ["True", "False"],
                    "answer": 0,  # All key points are true facts
                    "note": kp
                })

            # Also add example-based questions
            for ex in examples[:2]:
                if ex.get("title") and ex.get("explanation"):
                    tutorial_quiz.append({
                        "question": f"What is true about: {ex['title']}?",
                        "options": [
                            ex.get("explanation", "")[:100],
                            "Not related to this topic",
                            "An advanced feature",
                            "A deprecated feature"
                        ],
                        "answer": 0,
                    })

            tutorial = {
                "key": f"{cat}_{topic.get('id', topics.index(topic)+1)}",
                "category": cat,
                "category_title": cat_title,
                "category_icon": cat_icon,
                "topic_id": topic.get("id", topics.index(topic) + 1),
                "title": f"{topic_icon} {topic_title}",
                "description": cat_desc,
                "content": topic_content,
                "key_points": key_points,
                "examples": examples,
                "quiz": tutorial_quiz,
            }
            tutorials.append(tutorial)

    return tutorials


def list_tutorials() -> List[Dict]:
    """List all available tutorials from notes."""
    tutorials = build_tutorials_from_notes()
    config = load_config()
    progress = config.get("tutorial_progress", {})

    result = []
    # Group by category
    cats = {}
    for t in tutorials:
        cat = t["category"]
        if cat not in cats:
            cats[cat] = {
                "title": t["category_title"],
                "icon": t["category_icon"],
                "tutorials": [],
            }
        tp = progress.get(t["key"], {})
        cats[cat]["tutorials"].append({
            **t,
            "completed": tp.get("completed", False),
            "current_step": tp.get("current_step", 0),
        })

    for cat, data in cats.items():
        result.append({
            "type": "category",
            "key": cat,
            "title": data["title"],
            "icon": data["icon"],
            "count": len(data["tutorials"]),
            "tutorials": data["tutorials"],
        })

    return result


def run_tutorial(tutorial: Dict):
    """Run an interactive tutorial for a single topic."""
    config = load_config()
    tutorial_key = tutorial["key"]
    progress = config.get("tutorial_progress", {}).get(tutorial_key, {})
    already_completed = progress.get("completed", False)

    content = tutorial.get("content", "")
    key_points = tutorial.get("key_points", [])
    examples = tutorial.get("examples", [])
    quiz = tutorial.get("quiz", [])

    console.clear()
    console.print()

    # Header
    show_panel(
        f"{tutorial['title']}\n"
        f"[dim]{tutorial['description']}[/dim]",
        "cyan",
    )
    console.print()

    if already_completed:
        console.print("[dim]✅ Already completed. Re-reading...[/dim]")
        console.print()

    # Split content into readable chunks
    chunks = content.split("\n\n")
    chunk_size = 5  # Show ~5 paragraphs at a time
    for i in range(0, len(chunks), chunk_size):
        chunk = "\n\n".join(chunks[i:i + chunk_size])
        console.clear()
        console.print()
        console.print(f"[dim]Part {i // chunk_size + 1}/{(len(chunks) + chunk_size - 1) // chunk_size}[/dim]")
        console.print()
        for line in chunk.split("\n"):
            console.print(f"  {line}")
        console.print()
        if i + chunk_size < len(chunks):
            console.input("[bold green]╰─► Press Enter to continue reading...[/bold green]")

    # Show key points summary
    if key_points:
        console.clear()
        console.print()
        console.print(Panel(
            "[bold cyan]✓ Key Points Summary[/bold cyan]",
            box=box.ROUNDED,
            border_style="cyan",
        ))
        console.print()
        for kp in key_points:
            console.print(f"  [green]•[/green] [white]{kp}[/white]")
        console.print()
        console.input("[bold green]╰─► Press Enter when ready for the quiz...[/bold green]")

    # Quiz section
    correct = 0
    total_quiz = len(quiz)

    if total_quiz > 0:
        for i, q in enumerate(quiz, 1):
            console.clear()
            console.print()
            console.print(f"[dim]Quiz {i}/{total_quiz}[/dim]")
            console.print()
            console.print(Panel(
                f"[bold white]{q['question']}[/bold white]",
                box=box.ROUNDED,
                border_style="yellow",
                title="❓ Quick Check",
            ))
            console.print()

            for j, opt in enumerate(q["options"], 1):
                console.print(f"  [green][{j}][/green] {opt}")
            console.print()

            try:
                answer = console.input("[bold green]╰─► Your answer:[/bold green] ").strip()
                if answer.lower() == "q":
                    console.print("\n[yellow]Quiz skipped.[/yellow]")
                    total_quiz -= 1
                    break
                answer_num = int(answer) - 1

                if answer_num == q["answer"]:
                    correct += 1
                    console.print(Panel("[bold green]✓ Correct![/bold green]", box=box.ROUNDED, border_style="green"))
                else:
                    correct_text = q["options"][q["answer"]]
                    explanation = q.get("note", "")
                    console.print(Panel(
                        f"[bold red]✗ Wrong![/bold red]\n[cyan]Correct: {correct_text}[/cyan]"
                        + (f"\n[dim]{explanation}[/dim]" if explanation else ""),
                        box=box.ROUNDED, border_style="red"
                    ))
            except (ValueError, IndexError):
                console.print("[red]Invalid — counted as wrong[/red]")
                total_quiz += 0  # Don't double-count

            time.sleep(1.5)

    # Save progress
    config = load_config()
    if "tutorial_progress" not in config:
        config["tutorial_progress"] = {}
    config["tutorial_progress"][tutorial_key] = {
        "current_step": len(chunks),
        "completed": True,
        "quiz_correct": correct,
        "quiz_total": total_quiz,
        "completed_at": time.time(),
    }
    save_config(config)

    # Summary
    console.clear()
    console.print()
    pct = (correct / total_quiz * 100) if total_quiz > 0 else 0
    show_panel(
        f"[bold green]🎓 Tutorial Complete![/bold green]\n"
        f"Topic: {tutorial['title']}\n"
        f"Quiz: {correct}/{total_quiz} correct ({pct:.0f}%)",
        "green",
    )
    console.print()

    # Check achievements
    from kslearn.engines.achievements import check_achievements
    from kslearn.loader import content_loader
    brain_qa_count = len(content_loader.load_brain_qa())
    check_achievements(config, config.get("learning_progress", {}), brain_qa_count)

    console.input("[bold green]╰─► Press Enter to continue...[/bold green]")


def run_tutorials_interactive():
    """Interactive tutorial selection menu — loads from notes JSON."""
    while True:
        console.clear()
        console.print()
        show_panel("🎓 Interactive Tutorials", "Step-by-step guided lessons from your notes", "cyan")
        console.print()

        cats = list_tutorials()

        if not cats:
            show_error("No tutorials found. Make sure notes JSON files exist.")
            console.input("\nPress Enter to continue...")
            return

        # Display categories with tutorial counts
        table = Table(box=box.ROUNDED, border_style="cyan")
        table.add_column("#", style="yellow", width=4)
        table.add_column("Category", style="bold white")
        table.add_column("Lessons", style="dim", width=10)
        table.add_column("Progress", style="green")

        for i, cat in enumerate(cats, 1):
            completed = sum(1 for t in cat["tutorials"] if t.get("completed"))
            total = cat["count"]
            table.add_row(
                str(i),
                f"{cat['icon']} {cat['title']}",
                f"{total}",
                f"{completed}/{total}"
            )

        console.print(table)
        console.print()
        console.print("  [yellow]D[/yellow] [white]Show All Lessons (detailed)[/white]")
        console.print("  [green][0][/green] [dim]Back to Main Menu[/dim]")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Select category:[/bold green] ").strip().upper()
        except KeyboardInterrupt:
            return

        if choice == "0":
            return

        if choice == "D":
            # Show detailed lesson list
            _show_detailed_lessons(cats)
            continue

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(cats):
                _show_category_lessons(cats[idx])
            else:
                show_error("Invalid selection!")
                time.sleep(1)
        except ValueError:
            show_error("Please enter a number!")
            time.sleep(1)


def _show_detailed_lessons(cats: List[Dict]):
    """Show every single lesson across all categories."""
    while True:
        console.clear()
        console.print()
        show_panel("📚 All Lessons", "Every lesson from all categories", "cyan")
        console.print()

        table = Table(box=box.ROUNDED, border_style="green")
        table.add_column("#", style="yellow", width=4)
        table.add_column("Lesson", style="bold white")
        table.add_column("Status", style="dim")

        all_tutorials = []
        for cat in cats:
            for t in cat["tutorials"]:
                all_tutorials.append(t)

        for i, t in enumerate(all_tutorials, 1):
            status = "✅ Done" if t.get("completed") else "Not started"
            table.add_row(str(i), t["title"], status)

        console.print(table)
        console.print()
        console.print("  [green][0][/green] [dim]Back[/dim]")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Select lesson:[/bold green] ").strip()
        except KeyboardInterrupt:
            return

        if choice == "0":
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(all_tutorials):
                run_tutorial(all_tutorials[idx])
            else:
                show_error("Invalid selection!")
                time.sleep(1)
        except ValueError:
            show_error("Please enter a number!")
            time.sleep(1)


def _show_category_lessons(cat: Dict):
    """Show lessons within a single category."""
    while True:
        console.clear()
        console.print()
        show_panel(f"{cat['icon']} {cat['title']}", "Select a lesson to study", "cyan")
        console.print()

        table = Table(box=box.ROUNDED, border_style="green")
        table.add_column("#", style="yellow", width=4)
        table.add_column("Lesson", style="bold white")
        table.add_column("Status", style="dim")

        for i, t in enumerate(cat["tutorials"], 1):
            status = "✅ Done" if t.get("completed") else "Not started"
            table.add_row(str(i), t["title"], status)

        console.print(table)
        console.print()
        console.print("  [green][0][/green] [dim]Back to Categories[/dim]")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Select lesson:[/bold green] ").strip()
        except KeyboardInterrupt:
            return

        if choice == "0":
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(cat["tutorials"]):
                run_tutorial(cat["tutorials"][idx])
            else:
                show_error("Invalid selection!")
                time.sleep(1)
        except ValueError:
            show_error("Please enter a number!")
            time.sleep(1)
