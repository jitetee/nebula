#!/usr/bin/env python3
"""
Notes Viewer - Centralized learning notes reader
Loads study materials dynamically from JSON files with progress tracking
"""

import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box

from kslearn.loader import content_loader, KSL_DIR, CONFIG_DIR
from kslearn.ksl_loader import get_ksl_content_type, get_ksl_metadata, extract_notes, extract_combined_content, TYPE_COMBINED
from kslearn.ui import console, show_panel, show_success, show_error, show_info, show_warning, print_divider, clear_screen
from kslearn.config import load_config, set_config_value, save_config
from datetime import datetime


class NotesViewer:
    """Professional notes viewer with reading progress tracking"""

    def __init__(self):
        self.loader = content_loader
        self.current_category: Optional[str] = None
        self.current_topic: Optional[str] = None
        self.topics_read: int = 0
        self.total_read_time: int = 0

    def get_available_notes(self) -> List[Dict[str, str]]:
        """Get list of all available note categories from .ksl files"""
        return self.loader.get_all_notes_categories()

    def load_notes(self, category: str) -> Optional[Dict]:
        """Load notes data from JSON file"""
        try:
            data = self.loader.load_notes(category)
            if data is None:
                raise FileNotFoundError(f"Notes not found for '{category}'")
            if "topics" not in data:
                raise ValueError(f"Invalid notes format for '{category}'. JSON must have 'topics' key.")
            return data
        except (FileNotFoundError, ValueError) as e:
            show_error(str(e))
            return None

    def show_topics(self, category: str, notes_data: Dict) -> Optional[str]:
        """Show topics within a category and let user select one"""
        metadata = notes_data.get("metadata", {})
        topics = notes_data.get("topics", [])

        if not topics:
            console.print(Panel(
                "[yellow]No topics available in these notes[/yellow]",
                box=box.ROUNDED,
                border_style="yellow",
            ))
            return None

        while True:
            console.clear()
            console.print()
            
            # Header with category info
            title = metadata.get("title", category)
            desc = metadata.get("description", "")
            icon = metadata.get("icon", "📖")
            
            console.print(Panel(
                f"[bold cyan]{title}[/bold cyan]\n[dim]{desc}[/dim]",
                box=box.ROUNDED,
                border_style="cyan",
                title=icon,
                title_align="left",
            ))
            console.print()

            # Topics table
            topics_table = Table(
                box=box.ROUNDED,
                border_style="green",
                show_header=True,
                expand=True,
            )
            topics_table.add_column("#", style="yellow", width=4)
            topics_table.add_column("Topic", style="bold white")
            topics_table.add_column("Icon", style="dim", width=6)

            for i, topic in enumerate(topics, 1):
                topic_icon = topic.get("icon", "📄")
                topic_title = topic.get("title", f"Topic {i}")
                topics_table.add_row(str(i), topic_title, topic_icon)

            console.print(topics_table)
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
            
            actions_table.add_row("[Q]", "Take Quiz")
            actions_table.add_row("[K]", "Key Concepts")
            actions_table.add_row("[A]", "Ask AI (Offline/Online)")
            actions_table.add_row("[0]", "Exit to Main Menu")
            
            console.print(actions_table)
            console.print()

            try:
                choice = console.input("[bold green]╰─► Select topic:[/bold green] ").strip().lower()

                if choice == "0":
                    return None  # Exit to main menu
                elif choice == "q":
                    self.take_quiz(category, notes_data)
                elif choice == "k":
                    self.view_key_concepts(category)
                elif choice == "a":
                    self._choose_ai_mode(category)
                else:
                    try:
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(topics):
                            topic = topics[choice_num - 1]
                            self.display_topic(category, topic, topics, notes_data)
                        else:
                            console.print(Panel(
                                "[yellow]Invalid selection![/yellow]",
                                box=box.ROUNDED,
                                border_style="yellow",
                            ))
                            time.sleep(1)
                    except ValueError:
                        console.print(Panel(
                            "[yellow]Please enter a valid number[/yellow]",
                            box=box.ROUNDED,
                            border_style="yellow",
                        ))
                        time.sleep(1)

            except KeyboardInterrupt:
                return None

    def display_topic(self, category: str, topic: Dict, all_topics: List[Dict], notes_data: Dict):
        """Display a single topic with content and reading time tracking"""
        start_time = time.time()
        console.clear()
        console.print()
        
        title = topic.get("title", "Topic")
        icon = topic.get("icon", "📖")
        
        # Content panel
        content = topic.get("content", "")
        
        console.print(Panel(
            f"[white]{content}[/white]",
            box=box.ROUNDED,
            border_style="cyan",
            title=f"{icon} {title}",
            title_align="left",
        ))
        console.print()

        # Key points
        key_points = topic.get("key_points", [])
        if key_points:
            console.print("[bold cyan]✓ Key Points:[/bold cyan]")
            for point in key_points:
                console.print(f"  [green]•[/green] [white]{point}[/white]")
            console.print()

        # Examples
        examples = topic.get("examples", [])
        if examples:
            console.print("\n[bold cyan]💡 Examples:[/bold cyan]")
            for i, example in enumerate(examples, 1):
                console.print(f"\n  [yellow]Example {i}: {example.get('title', '')}[/yellow]")
                console.print(f"  [dim]{example.get('explanation', '')}[/dim]")

                code = example.get("code", "")
                if code:
                    console.print()
                    console.print(Panel(
                        f"[dim]{code}[/dim]",
                        box=box.ASCII,
                        border_style="green",
                        title="Code",
                    ))

                output = example.get("output", "")
                if output:
                    console.print(f"  [cyan]Output:[/cyan]")
                    console.print(f"  [dim]{output}[/dim]")

        console.print()
        console.print(Rule("[dim]Navigation[/dim]", style="cyan"))
        console.print()
        
        # Navigation
        nav_table = Table(
            box=None,
            show_header=False,
            expand=True,
            padding=(0, 1),
        )
        nav_table.add_column("Key", style="green")
        nav_table.add_column("Action", style="white")

        nav_table.add_row("[N]", "Next Topic")
        nav_table.add_row("[P]", "Previous Topic")
        nav_table.add_row("[Q]", "Take Quiz")
        nav_table.add_row("[A]", "Ask AI")
        nav_table.add_row("[B]", "Bookmark This Topic")
        nav_table.add_row("[0]", "Back to Topics")

        console.print(nav_table)
        console.print()

        while True:
            try:
                choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().lower()

                if choice == "0":
                    # Save reading time
                    elapsed = int(time.time() - start_time)
                    self._save_reading_time(category, topic, elapsed)
                    break
                elif choice == "n":
                    # Save reading time before moving on
                    elapsed = int(time.time() - start_time)
                    self._save_reading_time(category, topic, elapsed)
                    current_idx = all_topics.index(topic)
                    if current_idx < len(all_topics) - 1:
                        self.display_topic(category, all_topics[current_idx + 1], all_topics, notes_data)
                        return
                    else:
                        console.print(Panel(
                            "[dim]This is the last topic[/dim]",
                            box=box.ROUNDED,
                            border_style="yellow",
                        ))
                        time.sleep(1)
                elif choice == "p":
                    current_idx = all_topics.index(topic)
                    if current_idx > 0:
                        self.display_topic(category, all_topics[current_idx - 1], all_topics, notes_data)
                        return
                    else:
                        console.print(Panel(
                            "[dim]This is the first topic[/dim]",
                            box=box.ROUNDED,
                            border_style="yellow",
                        ))
                        time.sleep(1)
                elif choice == "q":
                    self.take_quiz(category, notes_data)
                    break
                elif choice == "a":
                    self._choose_ai_mode(category, topic.get("title"))
                    break
                elif choice == "b":
                    # Bookmark this topic
                    self._bookmark_topic(category, topic)
                    break

            except KeyboardInterrupt:
                break

    def _bookmark_topic(self, category: str, topic: Dict):
        """Save a topic to bookmarks"""
        from kslearn.config import load_config, set_config_value
        
        config = load_config()
        bookmarks = config.get("bookmarks", [])
        
        bookmark = {
            "category": category,
            "topic": topic.get("title", ""),
            "topic_id": topic.get("id", 0),
            "bookmarked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        
        # Check if already bookmarked
        exists = any(
            b.get("category") == category and
            b.get("topic") == topic.get("title")
            for b in bookmarks
        )
        
        if not exists:
            bookmarks.append(bookmark)
            set_config_value("bookmarks", bookmarks)
            console.print(Panel(
                f"[green]✓ Topic bookmarked![/green]\n[dim]{topic.get('title', '')}[/dim]",
                box=box.ROUNDED,
                border_style="green",
            ))
        else:
            console.print(Panel(
                "[yellow]! Already bookmarked[/yellow]",
                box=box.ROUNDED,
                border_style="yellow",
            ))
        
        time.sleep(1.5)

    def _save_reading_time(self, category: str, topic: Dict, seconds: int):
        """Save reading time for a topic to learning_progress."""
        if seconds < 5:
            return  # Ignore very brief views
        config = load_config()
        if "learning_progress" not in config:
            config["learning_progress"] = {}
        topic_title = topic.get("title", "Unknown")
        reading_key = f"reading_{category}_{topic_title}"
        prev = config["learning_progress"].get(reading_key, {})
        prev["total_read_seconds"] = prev.get("total_read_seconds", 0) + seconds
        prev["read_count"] = prev.get("read_count", 0) + 1
        prev["last_read_at"] = time.time()
        prev["topic"] = topic_title
        prev["category"] = category
        prev["type"] = "reading"
        config["learning_progress"][reading_key] = prev
        save_config(config)
        # Also update daily goal
        minutes = max(seconds // 60, 1)
        from kslearn.config import update_daily_goal
        update_daily_goal(minutes)

    def take_quiz(self, category: str, notes_data: Dict):
        """Take a quiz for the category"""
        # Collect quizzes from all topics or use category-level quizzes
        quizzes = notes_data.get("quizzes", [])

        # If no category-level quizzes, gather from all topics
        if not quizzes:
            for topic in notes_data.get("topics", []):
                quizzes.extend(topic.get("quizzes", []))

        if not quizzes:
            console.print(Panel(
                "[yellow]No quiz available for this topic![/yellow]",
                box=box.ROUNDED,
                border_style="yellow",
            ))
            time.sleep(1)
            return

        score = 0
        total = len(quizzes)
        streak = 0
        best_streak = 0

        console.print()
        console.print(Panel(
            f"[bold white]Answer {total} questions[/bold white]",
            box=box.ROUNDED,
            border_style="cyan",
            title="📝 Quick Quiz",
        ))
        console.print()
        console.input("[bold green]╰─► Press Enter to start...[/bold green]")

        for i, quiz in enumerate(quizzes, 1):
            console.clear()
            console.print()

            # Normalize question keys (handle both answer/correct, explanation/exp)
            question = quiz.get("question", quiz.get("q", "Unknown question"))
            options = quiz.get("options", [])
            answer_idx = quiz.get("answer", quiz.get("correct", 0))
            explanation = quiz.get("explanation", quiz.get("exp", "No explanation available."))

            # Progress
            console.print(f"[dim]Question {i}/{total}[/dim]  [yellow]🔥 Streak: {streak}[/yellow]")
            console.print()

            # Question panel
            console.print(Panel(
                f"[bold white]{question}[/bold white]",
                box=box.ROUNDED,
                border_style="cyan",
            ))
            console.print()

            # Options table
            options_table = Table(
                box=None,
                show_header=False,
                expand=True,
            )
            options_table.add_column("#", style="green", width=4)
            options_table.add_column("Option", style="white")

            for j, option in enumerate(options, 1):
                options_table.add_row(str(j), option)

            console.print(options_table)
            console.print()

            try:
                answer = console.input("[bold green]╰─► Your answer:[/bold green] ").strip()
                answer_num = int(answer) - 1

                if answer_num == answer_idx:
                    score += 1
                    streak += 1
                    best_streak = max(streak, best_streak)
                    console.print(Panel(
                        f"[bold green]✓ Correct![/bold green]",
                        box=box.ROUNDED,
                        border_style="green",
                    ))
                    content_loader.add_qa_to_brain(
                        question,
                        explanation,
                        category=category,
                        tags=["quiz", "correct"]
                    )
                else:
                    streak = 0
                    correct_text = options[answer_idx] if answer_idx < len(options) else "Unknown"
                    console.print(Panel(
                        f"[bold red]✗ Wrong![/bold red]\n[cyan]Correct: {correct_text}\n💡 {explanation}[/cyan]",
                        box=box.ROUNDED,
                        border_style="red",
                    ))
                    content_loader.add_qa_to_brain(
                        question,
                        explanation,
                        category=category,
                        tags=["quiz", "review"]
                    )

            except (ValueError, IndexError):
                console.print(Panel(
                    "[red]Invalid input![/red]",
                    box=box.ROUNDED,
                    border_style="red",
                ))
            except KeyboardInterrupt:
                break

            time.sleep(1.5)

        # Show results
        percentage = (score / total) * 100 if total > 0 else 0
        console.clear()
        console.print()

        # Save progress (unique prefix to avoid collision with quiz_engine)
        progress_key = f"notes_quiz_{category}_{int(time.time())}"
        config = load_config()
        if "learning_progress" not in config:
            config["learning_progress"] = {}
        config["learning_progress"][progress_key] = {
            "last_score": score,
            "last_accuracy": percentage,
            "completed_at": time.time(),
            "topic": "Notes Quiz",
            "category": category,
            "questions": total,
            "correct": score,
            "best_streak": best_streak,
        }
        from kslearn.config import save_config
        save_config(config)

        # Check for new achievements
        from kslearn.engines.achievements import check_achievements
        check_achievements(config, config.get("learning_progress", {}), content_loader.get_brain_stats().get("total_qa_pairs", 0))

        # Result panel
        result_content = f"""[bold]Questions:[/bold] {total}
[bold]Correct:[/bold] [green]{score}[/green]
[bold]Score:[/bold] {score}/{total}
[bold]Accuracy:[/bold] [yellow]{percentage:.0f}%[/yellow]
[bold]Best Streak:[/bold] [red]{best_streak} 🔥[/red]"""

        if percentage >= 80:
            result_content += "\n\n[bold green]🎉 Excellent![/bold green]"
        elif percentage >= 60:
            result_content += "\n\n[bold yellow]👍 Good job![/bold yellow]"
        else:
            result_content += "\n\n[bold cyan]📚 Keep studying![/bold cyan]"

        console.print(Panel(
            result_content,
            box=box.ROUNDED,
            border_style="cyan",
            title="📊 Quiz Results",
        ))
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

    def view_key_concepts(self, category: str):
        """View key concepts and important facts for a category"""
        notes_data = self.loader.load_notes(category)

        if not notes_data:
            console.print(Panel(
                "[yellow]No study notes available for this category![/yellow]",
                box=box.ROUNDED,
                border_style="yellow",
            ))
            time.sleep(1)
            return

        # Collect all key points across topics
        topics = notes_data.get("topics", [])
        all_concepts = []

        for topic in topics:
            topic_title = topic.get("title", "Topic")
            icon = topic.get("icon", "📖")
            key_points = topic.get("key_points", [])
            examples = topic.get("examples", [])

            for i, point in enumerate(key_points, 1):
                all_concepts.append({
                    "topic": f"{icon} {topic_title}",
                    "point_num": i,
                    "concept": point,
                    "type": "key_point",
                })

            for ex in examples:
                if ex.get("explanation"):
                    all_concepts.append({
                        "topic": f"{icon} {topic_title}",
                        "point_num": len(key_points) + 1,
                        "concept": f"[bold]{ex.get('title', 'Example')}:[/bold] {ex['explanation']}",
                        "code": ex.get("code", ""),
                        "type": "example",
                    })

        if not all_concepts:
            # Fallback: show topic titles as concepts
            for topic in topics:
                topic_title = topic.get("title", "Topic")
                icon = topic.get("icon", "📖")
                content = topic.get("content", "")[:200]
                all_concepts.append({
                    "topic": f"{icon} {topic_title}",
                    "point_num": 1,
                    "concept": content or "No content available",
                    "type": "summary",
                })

        while True:
            console.clear()
            console.print()

            console.print(Panel(
                f"[bold cyan]{category.replace('_', ' ').title()}[/bold cyan]\n"
                f"[dim]{len(topics)} topics • {len(all_concepts)} key concepts[/dim]",
                box=box.ROUNDED,
                border_style="cyan",
                title="🔑 Key Concepts",
            ))
            console.print()

            # Concepts table
            concepts_table = Table(
                box=box.ROUNDED,
                border_style="green",
                show_header=True,
                expand=True,
            )
            concepts_table.add_column("#", style="yellow", width=4)
            concepts_table.add_column("Topic", style="bold white")
            concepts_table.add_column("Concept", style="dim")

            display_concepts = all_concepts[:20]  # Show first 20
            for i, concept in enumerate(display_concepts, 1):
                concept_preview = concept["concept"][:60] + "..." if len(concept["concept"]) > 60 else concept["concept"]
                # Strip rich formatting for preview
                import re
                clean_preview = re.sub(r'\[/?[^\]]+\]', '', concept_preview)
                concepts_table.add_row(
                    str(i),
                    concept["topic"],
                    clean_preview,
                )

            console.print(concepts_table)
            console.print()
            console.print(f"  [bold green][0][/bold green] [dim]Back[/dim]")
            console.print()

            try:
                choice = console.input("[bold green]╰─► Select concept to expand:[/bold green] ").strip()

                if choice == "0":
                    break

                idx = int(choice) - 1
                if 0 <= idx < len(all_concepts):
                    concept = all_concepts[idx]
                    console.clear()
                    console.print()

                    console.print(Panel(
                        f"[dim]{concept['topic']}[/dim]",
                        box=box.ROUNDED,
                        border_style="cyan",
                        title=f"🔑 Concept #{idx + 1}",
                    ))
                    console.print()

                    console.print(Panel(
                        f"[white]{concept['concept']}[/white]",
                        box=box.ASCII,
                        border_style="green",
                        title="Concept",
                    ))

                    if concept.get("code"):
                        console.print()
                        console.print(Panel(
                            f"[white]{concept['code']}[/white]",
                            box=box.ASCII,
                            border_style="yellow",
                            title="Example",
                        ))

                    console.print()
                    console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

            except (ValueError, KeyboardInterrupt):
                break

    def ask_ai_offline(self, category: str, topic: str = None):
        """Offline AI chat using JSON Brain"""
        console.clear()
        console.print()
        
        console.print(Panel(
            f"[bold cyan]Category: {category}[/bold cyan]\n[dim]Type 'quit' to exit[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
            title="🤖 Ask AI (Offline)",
        ))
        console.print()

        while True:
            try:
                question = console.input("[bold green]╰─► Q:[/bold green] ").strip()

                if question.lower() in ["quit", "exit", "q"]:
                    break

                if not question:
                    continue

                # Search brain for answer
                results = content_loader.search_brain(question, limit=3)

                if results:
                    console.print()
                    console.print("[bold green]A:[/bold green]")
                    for i, result in enumerate(results, 1):
                        answer_panel = Panel(
                            f"[white]{result['answer']}[/white]",
                            box=box.ROUNDED,
                            border_style="green",
                        )
                        console.print(answer_panel)
                        if result.get("similarity_score", 0) > 0.5:
                            break

                    # Save conversation
                    if results:
                        content_loader.add_qa_to_brain(
                            question,
                            results[0]["answer"],
                            category=category,
                            tags=["offline_ai", "correct"]
                        )

                    confirm = console.input("[bold yellow]╰─► Was this helpful? (y/n):[/bold yellow] ").strip().lower()
                    if confirm == "y":
                        console.print(Panel(
                            "[green]✓ Feedback saved![/green]",
                            box=box.ROUNDED,
                            border_style="green",
                        ))
                else:
                    console.print(Panel(
                        "[yellow]No answer found in knowledge brain.[/yellow]\n[dim]The question will be saved for future reference.[/dim]",
                        box=box.ROUNDED,
                        border_style="yellow",
                    ))

                    answer = console.input("[bold yellow]╰─► Provide answer (optional):[/bold yellow] ").strip()
                    if answer and len(answer) >= 10 and answer.lower() not in ("quit", "exit", "q", "none"):
                        content_loader.add_qa_to_brain(question, answer, category=category, tags=["user-provided"])
                        console.print(Panel(
                            "[green]✓ Added to knowledge brain![/green]",
                            box=box.ROUNDED,
                            border_style="green",
                        ))

            except KeyboardInterrupt:
                break

    def _choose_ai_mode(self, category: str, topic: str = None):
        """Show submenu to choose between Offline and Online AI"""
        console.clear()
        console.print()

        console.print(Panel(
            f"[bold cyan]Category: {category}[/bold cyan]\n"
            f"{'[dim]Topic: ' + topic + '[/dim]\n' if topic else ''}"
            "[dim]Select AI mode:[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
            title="🤖 Ask AI",
        ))
        console.print()

        mode_table = Table(
            box=None,
            show_header=False,
            expand=True,
            padding=(0, 2),
        )
        mode_table.add_column("Key", style="green")
        mode_table.add_column("Mode", style="white")
        mode_table.add_column("Description", style="dim")

        mode_table.add_row("[1]", "Offline (JSON Brain)", "Search local knowledge base")
        mode_table.add_row("[2]", "Online (AI Chat)", "Use tgpt-powered AI chat")
        mode_table.add_row("[0]", "Back", "Return to previous menu")

        console.print(mode_table)
        console.print()

        try:
            choice = console.input("[bold green]╰─► Select mode:[/bold green] ").strip().lower()

            if choice == "1":
                self.ask_ai_offline(category, topic)
            elif choice == "2":
                self.ask_ai_online(category, topic)
            # choice == "0" or anything else: just return
        except KeyboardInterrupt:
            pass

    def ask_ai_online(self, category: str, topic: str = None):
        """Online AI chat using AIChat (tgpt-powered)"""
        from kslearn.main.ai_chat import AIChat

        console.clear()
        console.print()

        context_prompt = ""
        if topic:
            context_prompt = f"I'm studying {category} - specifically the topic: {topic}. "

        chat = AIChat()
        chat.system_prompt = (
            f"You are kslearn AI Tutor. The user is currently studying {category}"
            f"{' - ' + topic if topic else ''}. "
            f"kslearn is a general learning platform for learning absolutely anything — "
            f"from math and science to psychology, religion, music, and beyond. "
            f"Be concise, educational, and encouraging. Focus on helping them understand "
            f"this subject area."
        )

        console.print(Panel(
            f"[bold cyan]Category: {category}[/bold cyan]\n"
            f"{'[dim]Topic: ' + topic + ' | [/dim]' if topic else ''}"
            f"[dim]Provider: {chat.provider} | Type 'quit' to exit[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
            title="🤖 Ask AI (Online)",
        ))
        console.print()

        while True:
            try:
                question = console.input("[bold green]╰─► Q:[/bold green] ").strip()

                if question.lower() in ["quit", "exit", "q"]:
                    break

                if not question:
                    continue

                # Build full prompt with context
                full_prompt = context_prompt + question if context_prompt else question

                # Use AIChat to get response
                response = chat.chat(full_prompt)

                if response:
                    console.print()
                    console.print("[bold green]A:[/bold green]")
                    answer_panel = Panel(
                        f"[white]{response}[/white]",
                        box=box.ROUNDED,
                        border_style="green",
                    )
                    console.print(answer_panel)
                    console.print()

                    # Auto-save to knowledge brain for offline reference
                    if chat.auto_save_to_brain:
                        chat._save_to_knowledge_brain(question, response)

                    confirm = console.input("[bold yellow]╰─► Was this helpful? (y/n):[/bold yellow] ").strip().lower()
                    if confirm == "y":
                        console.print(Panel(
                            "[green]✓ Great! Keep learning![/green]",
                            box=box.ROUNDED,
                            border_style="green",
                        ))
                else:
                    console.print(Panel(
                        "[yellow]No response from AI. Check your connection and provider settings.[/yellow]",
                        box=box.ROUNDED,
                        border_style="yellow",
                    ))

            except KeyboardInterrupt:
                break

    def select_topic(self, notes_data: Dict) -> Optional[str]:
        """Let user select a topic within the notes category"""
        topics = notes_data.get("topics", [])

        if not topics:
            show_error("No topics available in these notes")
            return None

        console.print()
        show_panel("Select Topic", f"Choose a topic from {notes_data.get('metadata', {}).get('title', 'these notes')}", "cyan")
        console.print()

        for i, topic in enumerate(topics, 1):
            topic_title = topic.get("title", f"Topic {i}")
            topic_desc = topic.get("description", "")
            content_preview = ""

            # Preview content
            if "content" in topic:
                content = topic["content"]
                if isinstance(content, str):
                    content_preview = content[:100].replace("\n", " ") + "..." if len(content) > 100 else content
                elif isinstance(content, list):
                    content_preview = f"{len(content)} sections"

            console.print(f"  [yellow]{i:02d}[/yellow] [white]{topic_title}[/white]")
            if topic_desc:
                console.print(f"       [dim]{topic_desc}[/dim]")
            if content_preview:
                console.print(f"       [dim]{content_preview}[/dim]")
            console.print()

        console.print(f"  [yellow] 0[/yellow] [white]Back[/white]")
        console.print()

        while True:
            try:
                choice = console.input("[bold green]╰─► Select topic to study:[/bold green] ").strip()

                if choice == "0":
                    return None
                else:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(topics):
                        return topics[choice_num - 1]
                    else:
                        show_warning("Invalid selection!")
            except (ValueError, KeyboardInterrupt):
                show_warning("Please enter a valid number")
                return None


def run_notes_interactive():
    """Main entry point for interactive notes browsing"""
    viewer = NotesViewer()

    while True:
        console.clear()
        console.print()
        
        # Header
        console.print(Panel(
            "[bold cyan]📚 Study Notes[/bold cyan]\n[dim]Browse comprehensive learning materials from JSON files[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
            title="📖",
            title_align="left",
        ))
        console.print()

        notes = viewer.get_available_notes()

        if not notes:
            console.print(Panel(
                "[yellow]No notes files found in data/ksl/[/yellow]\n[dim]Pack your JSON files into .ksl using ksl_tool.py![/dim]",
                box=box.ROUNDED,
                border_style="yellow",
            ))
            console.input("\nPress Enter to continue...")
            return

        # Display note categories in a table
        notes_table = Table(
            box=box.ROUNDED,
            border_style="green",
            show_header=True,
            expand=True,
        )
        notes_table.add_column("#", style="yellow", width=4)
        notes_table.add_column("Category", style="bold white")
        notes_table.add_column("Description", style="dim")
        notes_table.add_column("Topics", style="cyan", justify="right")

        for i, note in enumerate(notes, 1):
            icon = note.get("icon", "📖")
            title = note["title"]
            desc = note.get("description", "")[:50] + "..." if len(note.get("description", "")) > 50 else note.get("description", "")
            topic_count = str(note["topic_count"])
            notes_table.add_row(str(i), f"{icon} {title}", desc, topic_count)

        console.print(notes_table)
        console.print()
        console.print(f"  [bold green][0][/bold green] [dim]Exit to Main Menu[/dim]")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Select category:[/bold green] ").strip()

            if choice == "0":
                return

            choice_num = int(choice)
            if 1 <= choice_num <= len(notes):
                selected = notes[choice_num - 1]

                # Load notes data
                notes_data = viewer.load_notes(selected["key"])
                if not notes_data:
                    console.print(Panel(
                        f"[red]Failed to load notes for {selected['title']}[/red]",
                        box=box.ROUNDED,
                        border_style="red",
                    ))
                    time.sleep(2)
                    continue

                # Show topics for this category
                viewer.show_topics(selected["key"], notes_data)
            else:
                console.print(Panel(
                    "[yellow]Invalid selection![/yellow]",
                    box=box.ROUNDED,
                    border_style="yellow",
                ))
                time.sleep(1)

        except (ValueError, KeyboardInterrupt):
            console.print("\n[yellow]Returning to menu...[/yellow]")
            time.sleep(1)


if __name__ == "__main__":
    run_notes_interactive()


# --- Flashcard Mode ---

def run_flashcards(category: str = None):
    """Study using flashcards — front shows key point, back shows answer."""
    console.clear()
    console.print()

    # Collect all key points and examples
    categories = content_loader.get_all_notes_categories()
    all_cards = []

    # categories is now a list of dicts with 'key' field
    if category:
        target_cats = [category]
    else:
        target_cats = [c["key"] for c in categories] if categories else []

    for cat in target_cats:
        notes_data = content_loader.load_notes(cat)
        if not notes_data:
            continue
        cat_title = notes_data.get("metadata", {}).get("title", cat.replace("_", " ").title())
        for topic in notes_data.get("topics", []):
            topic_title = topic.get("title", "Topic")
            for i, point in enumerate(topic.get("key_points", []), 1):
                all_cards.append({
                    "category": cat,
                    "cat_title": cat_title,
                    "topic": topic_title,
                    "front": point,
                    "back": point,  # Same — self-test by covering and recalling
                    "type": "key_point",
                    "num": i,
                })
            for ex in topic.get("examples", []):
                if ex.get("explanation"):
                    all_cards.append({
                        "category": cat,
                        "cat_title": cat_title,
                        "topic": topic_title,
                        "front": ex.get("title", "Example"),
                        "back": ex.get("explanation", ""),
                        "code": ex.get("code", ""),
                        "type": "example",
                    })

    if not all_cards:
        show_panel("🃏 Flashcards", "No flashcards available. Add notes with key_points first.", "yellow")
        time.sleep(2)
        return

    import random
    random.shuffle(all_cards)

    console.print(Panel(
        f"[bold white]{len(all_cards)} flashcards[/bold white]\n"
        "[dim]Read the front, think of the answer, then reveal[/dim]",
        box=box.ROUNDED,
        border_style="cyan",
        title="🃏 Flashcard Mode",
    ))
    console.print()
    console.input("[bold green]╰─► Press Enter to start...[/bold green]")

    reviewed = 0
    known = 0

    for i, card in enumerate(all_cards, 1):
        console.clear()
        console.print()
        console.print(f"[dim]Card {i}/{len(all_cards)} | {card['cat_title']} > {card['topic']}[/dim]")
        console.print()

        # Front of card
        console.print(Panel(
            f"[bold white]{card['front']}[/bold white]",
            box=box.ROUNDED,
            border_style="yellow",
            title="❓ Front",
        ))
        console.print()
        console.input("[bold green]╰─► Think of your answer, then press Enter to reveal...[/bold green]")

        # Back of card
        console.print()
        console.print(Panel(
            f"[white]{card['back']}[/white]" +
            (f"\n\n[dim]{card['code']}[/dim]" if card.get("code") else ""),
            box=box.ASCII,
            border_style="green",
            title="✅ Back",
        ))
        console.print()

        response = console.input("[bold green]╰─► Did you know it? (y/n/q):[/bold green] ").strip().lower()
        if response == "q":
            break
        reviewed += 1
        if response == "y":
            known += 1

    # Summary
    console.clear()
    console.print()
    pct = (known / reviewed * 100) if reviewed > 0 else 0
    show_panel("🃏 Flashcard Results",
               f"Reviewed: {reviewed} | Known: {known} | Learning: {reviewed - known}\n"
               f"Accuracy: {pct:.0f}%", "cyan")
    console.print()
    console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

    # Track in progress
    config = load_config()
    if "learning_progress" not in config:
        config["learning_progress"] = {}
    config["learning_progress"][f"flashcard_{category or 'all'}"] = {
        "last_score": known,
        "last_accuracy": pct,
        "completed_at": time.time(),
        "topic": "Flashcard Session",
        "category": category or "all",
        "questions": reviewed,
        "correct": known,
        "best_streak": 0,
    }
    save_config(config)

    # Check for new achievements
    from kslearn.engines.achievements import check_achievements
    check_achievements(config, config.get("learning_progress", {}), content_loader.get_brain_stats().get("total_qa_pairs", 0))


# --- Global Notes Search ---

def global_notes_search(query: str):
    """Search across ALL note files for matching topics and content."""
    console.clear()
    console.print()
    show_panel("🔍 Global Notes Search", f"Searching for: '{query}'", "cyan")
    console.print()

    results = []
    categories = content_loader.get_all_notes_categories()

    query_lower = query.lower()

    for cat_info in categories:
        cat = cat_info["key"] if isinstance(cat_info, dict) else cat_info
        notes_data = content_loader.load_notes(cat)
        if not notes_data:
            continue
        cat_title = notes_data.get("metadata", {}).get("title", cat.replace("_", " ").title())

        for topic in notes_data.get("topics", []):
            topic_title = topic.get("title", "")
            content = topic.get("content", "")
            key_points = topic.get("key_points", [])

            # Search in title, content, and key points
            search_text = f"{topic_title} {content} {' '.join(key_points)}".lower()

            if query_lower in search_text:
                # Find matching snippets
                matching_points = [p for p in key_points if query_lower in p.lower()]
                results.append({
                    "category": cat,
                    "cat_title": cat_title,
                    "topic": topic_title,
                    "content_preview": content[:200] + "..." if len(content) > 200 else content,
                    "matching_points": matching_points,
                })

    if not results:
        console.print(Panel(
            f"[yellow]No results found for '{query}'[/yellow]\n[dim]Try different keywords[/dim]",
            box=box.ROUNDED,
            border_style="yellow",
        ))
    else:
        console.print(f"[bold green]{len(results)} result(s) found[/bold green]\n")

        def _highlight(text, q):
            """Highlight search term in text using Rich bold."""
            if not text or not q:
                return text
            import re
            # Case-insensitive replace with bold version
            pattern = re.compile(re.escape(q), re.IGNORECASE)
            return pattern.sub(f"[bold yellow]{q}[/bold yellow]", text)

        for i, r in enumerate(results, 1):
            console.print(f"[bold cyan]{'─' * 50}[/bold cyan]")
            console.print(f"[bold]{i}.[/bold] [white]{r['cat_title']}[/white] > [yellow]{r['topic']}[/yellow]")
            console.print()
            # Highlight search term in content preview
            highlighted_content = _highlight(r["content_preview"], query)
            console.print(f"[dim]{highlighted_content}[/dim]")

            if r["matching_points"]:
                console.print()
                for point in r["matching_points"]:
                    highlighted_point = _highlight(point, query)
                    console.print(f"  [green]•[/green] {highlighted_point}")
            console.print()

    console.print()
    console.input("[bold green]╰─► Press Enter to continue...[/bold green]")


# --- Spaced Repetition Review ---

def run_spaced_review():
    """Review topics you've struggled with, scheduled by spaced repetition."""
    from kslearn.engines.quiz_engine import QuizEngine

    config = load_config()
    review_queue = config.get("review_queue", {})
    progress = config.get("learning_progress", {})

    if not review_queue:
        # Build initial review queue from low-scoring quizzes
        new_queue = {}
        for key, data in progress.items():
            accuracy = data.get("last_accuracy", 100)
            if accuracy < 80 and accuracy > 0:
                category = data.get("category", "")
                topic = data.get("topic", "")
                new_queue[key] = {
                    "category": category,
                    "topic": topic,
                    "accuracy": accuracy,
                    "last_reviewed": None,
                    "review_count": 0,
                    "next_review": time.time(),  # Review immediately
                }

        if not new_queue:
            console.clear()
            console.print()
            show_panel("📅 Spaced Review",
                       "No items need review! All your quizzes are 80%+ or no quizzes taken yet.",
                       "green")
            console.print()
            console.input("[bold green]╰─► Press Enter to continue...[/bold green]")
            return

        config["review_queue"] = new_queue
        save_config(config)
        review_queue = new_queue

    # Filter to items due for review
    now = time.time()
    due_items = {k: v for k, v in review_queue.items() if v.get("next_review", 0) <= now}

    if not due_items:
        console.clear()
        console.print()
        show_panel("📅 Spaced Review",
                   "Nothing due for review right now. Come back later!",
                   "green")
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")
        return

    console.clear()
    console.print()
    show_panel("📅 Spaced Review",
               f"{len(due_items)} item(s) due for review\n"
               "[dim]Spaced repetition resurfaces topics you struggled with at optimal intervals[/dim]",
               "cyan")
    console.print()

    reviewed_items = []
    for key, item in due_items.items():
        cat = item.get("category", "")
        topic = item.get("topic", "")
        accuracy = item.get("accuracy", 0)

        console.print(f"[bold cyan]▶ {cat.replace('_', ' ').title()} > {topic}[/bold cyan]")
        console.print(f"[dim]Last accuracy: {accuracy:.0f}% | Reviews: {item.get('review_count', 0)}[/dim]")
        console.print()

        # Try to load the quiz for this topic
        quiz_data = content_loader.load_quiz(cat)
        if quiz_data and "topics" in quiz_data:
            # Find questions for this topic in the topics array
            for topic_item in quiz_data["topics"]:
                topic_title = topic_item.get("title", "")
                if topic.lower() in topic_title.lower() or topic_title.lower() in topic.lower():
                    # Run a mini review with these questions
                    questions = topic_item.get("questions", [])
                    if questions:
                        # Configurable review limit (default 5)
                        review_limit = config.get("spaced_review_limit", 5)
                        engine = QuizEngine()
                        engine.current_category = cat
                        engine.current_topic = topic_title
                        engine.run_quiz(cat, topic_title, questions[:review_limit])

                        # Mark as spaced review in progress for achievement tracking
                        config = load_config()
                        if "learning_progress" not in config:
                            config["learning_progress"] = {}
                        entry_key = f"spaced_{cat}_{topic_title}"
                        prev = config["learning_progress"].get(entry_key, {})
                        prev["spaced_review"] = True
                        prev["review_count"] = prev.get("review_count", 0) + 1
                        prev["topic"] = topic_title
                        prev["category"] = cat
                        config["learning_progress"][entry_key] = prev
                        save_config(config)

                        reviewed_items.append(key)
                        break

        console.print()
        pause = console.input("[bold green]╰─► Continue? (y/n):[/bold green] ").strip().lower()
        if pause == "n":
            break
        console.print()

    # Update review queue with new intervals
    for key in reviewed_items:
        if key in review_queue:
            item = review_queue[key]
            item["review_count"] = item.get("review_count", 0) + 1
            item["last_reviewed"] = datetime.now().strftime("%Y-%m-%d")

            # Spaced intervals: 1 day → 3 days → 7 days → 14 days → 30 days
            intervals = [86400, 259200, 604800, 1209600, 2592000]
            count = min(item["review_count"], len(intervals) - 1)
            item["next_review"] = now + intervals[count]

    config["review_queue"] = review_queue
    save_config(config)

    console.print(Panel(
        f"[green]✓ Reviewed {len(reviewed_items)} item(s)[/green]\n"
        "[dim]Next review scheduled automatically[/dim]",
        box=box.ROUNDED,
        border_style="green",
    ))
    console.print()
    console.input("[bold green]╰─► Press Enter to continue...[/bold green]")


# ═══════════════════════════════════════════════════════════════════
#  Hierarchical Notes Viewer — 6-Level Navigation with Progression
#  Course → Category → Unit → Learning Outcome → Sub-topic → Content
#  LOCKING: Can't advance until min_score met on previous level
# ═══════════════════════════════════════════════════════════════════

from kslearn.loader import (
    format_duration, difficulty_icon,
    check_prerequisites, is_unit_unlocked, is_outcome_unlocked,
    get_all_hierarchical_courses, load_hierarchical_course, get_course_stats,
)


class HierarchicalNotesViewer:
    """Navigate hierarchical course content with breadcrumb navigation and progression gating."""

    def __init__(self):
        self.loader = content_loader

    def show_courses(self, filter_difficulty=None, search_query=None):
        courses = get_all_hierarchical_courses()
        if not courses:
            show_warning("No hierarchical courses found!")
            show_info("Add .ksl files with 'courses' key to data/ksl/")
            return None

        # Apply filters
        if filter_difficulty:
            courses = [c for c in courses if c.get("difficulty", "beginner").lower() == filter_difficulty.lower()]
        if search_query:
            q = search_query.lower()
            courses = [c for c in courses if q in c.get("title", "").lower() or
                       q in c.get("description", "").lower() or
                       any(q in t.lower() for t in c.get("tags", []))]

        if not courses:
            show_warning("No courses match your filters!")
            console.print()
            console.print("  [green][F][/green] Change difficulty filter")
            console.print("  [green][S][/green] Search courses")
            console.print("  [green][R][/green] Reset filters")
            console.print("  [green][0][/green] Back")
            console.print()
            try:
                ch = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()
            except KeyboardInterrupt:
                return
            if ch == "F":
                return self.show_courses()
            elif ch == "S":
                try:
                    sq = console.input("[bold yellow]Search:[/bold yellow] ").strip()
                except KeyboardInterrupt:
                    return
                return self.show_courses(search_query=sq if sq else None)
            elif ch == "R":
                return self.show_courses()
            return

        while True:
            clear_screen()
            console.print()
            hdr = "📚 Course Catalog"
            sub = "Select a course — progression locks ensure mastery before advancing"
            if filter_difficulty or search_query:
                filters = []
                if filter_difficulty:
                    filters.append(f"Difficulty: {filter_difficulty}")
                if search_query:
                    filters.append(f"Search: '{search_query}'")
                sub += " | " + " | ".join(filters)
            show_panel(hdr, sub, "cyan")
            console.print()
            table = Table(box=box.ROUNDED, border_style="cyan")
            table.add_column("#", style="yellow", width=4)
            table.add_column("Course", style="bold white")
            table.add_column("Difficulty", style="dim", width=6)
            table.add_column("Duration", style="dim", width=8)
            table.add_column("Credits", style="dim", width=8)
            table.add_column("Lock", style="dim", width=6)
            config = load_config()
            completed = config.get("learning_progress", {})
            for i, course in enumerate(courses, 1):
                di = difficulty_icon(course.get("difficulty", "beginner"))
                dur = format_duration(course.get("estimated_minutes", 0))
                cr = course.get("credits", 0)
                cr_s = f"{cr} CR" if cr > 0 else "—"
                prereq = check_prerequisites(course, completed)
                lock = "🔒" if not prereq["met"] else "🔓"
                table.add_row(str(i), f"{course.get('icon', '📚')} {course['title']}", di, dur if dur != "0 min" else "—", cr_s, lock)
            console.print(table)
            console.print()
            console.print("[dim]🔒 = Locked (complete prerequisites first)  🔓 = Available[/dim]")
            console.print()
            console.print("  [green][S][/green] 🔍 Search courses")
            console.print("  [green][F][/green] Filter by difficulty")
            # Continue where you left off (#12)
            last_course = config.get("last_hierarchical_course", "")
            if last_course:
                console.print(f"  [green][L][/green] Continue: {last_course}")
            console.print("  [green][0][/green] [dim]Back to Main Menu[/dim]")
            console.print()
            try:
                choice = console.input("[bold green]╰─► Select course:[/bold green] ").strip().upper()
                if choice == "0":
                    return None
                elif choice == "S":
                    try:
                        sq = console.input("[bold yellow]Search:[/bold yellow] ").strip()
                    except KeyboardInterrupt:
                        continue
                    return self.show_courses(filter_difficulty=filter_difficulty, search_query=sq if sq else None)
                elif choice == "F":
                    console.print("  [1] Beginner  [2] Intermediate  [3] Advanced  [4] Expert  [R] Reset")
                    try:
                        fc = console.input("[bold yellow]Filter:[/bold yellow] ").strip()
                    except KeyboardInterrupt:
                        continue
                    diff_map = {"1": "beginner", "2": "intermediate", "3": "advanced", "4": "expert"}
                    if fc == "R":
                        return self.show_courses()
                    elif fc in diff_map:
                        return self.show_courses(filter_difficulty=diff_map[fc])
                    continue
                elif choice == "L" and last_course:
                    # Continue where you left off
                    cd = load_hierarchical_course(last_course)
                    if cd:
                        self.show_course_details(cd, breadcrumb=[cd.get("title", last_course)])
                    continue
                elif choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(courses):
                        sel = courses[idx]
                        # Save last visited course (#12)
                        config["last_hierarchical_course"] = sel.get("key", sel.get("id", ""))
                        save_config(config)
                        cd = load_hierarchical_course(sel["key"])
                        if cd:
                            prereq = check_prerequisites(cd, completed)
                            if not prereq["met"]:
                                clear_screen()
                                console.print()
                                show_panel("🔒 Prerequisites Required", prereq["message"], "yellow")
                                console.print()
                                console.print("[dim]Complete required courses first, then return here.[/dim]")
                                console.print()
                                console.input("[bold green]╰─► Press Enter to continue...[/bold green]")
                            else:
                                self.show_course_details(cd, breadcrumb=[sel["title"]])
                    else:
                        show_warning("Invalid selection!")
                        time.sleep(1)
            except (ValueError, KeyboardInterrupt):
                return None

    def show_course_details(self, course, breadcrumb):
        while True:
            clear_screen()
            console.print()
            console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
            console.print()
            diff = course.get("difficulty", "beginner")
            di = difficulty_icon(diff)
            dur = format_duration(self.loader.calculate_total_duration(course))
            credits = course.get("credits", 0)
            version = course.get("version", "1.0")
            stats = get_course_stats(course)
            lines = [f"[bold white]{course.get('description', '')}[/bold white]", ""]
            mi = []
            if diff:
                mi.append(f"{di} {diff.capitalize()}")
            if dur and dur != "0 min":
                mi.append(f"⏱️  {dur}")
            if credits > 0:
                mi.append(f"🎓 {credits} Credits")
            mi.append(f"📦 v{version}")
            if mi:
                lines.append("  ".join(mi))
                lines.append("")
            prereqs = course.get("prerequisites", [])
            if prereqs:
                lines.append("[bold yellow]Prerequisites:[/bold yellow]")
                for p in prereqs:
                    lines.append(f"  [green]✓[/green] {p}")
                lines.append("")
            tags = course.get("tags", [])
            if tags:
                lines.append("  ".join([f"[cyan]#{t}[/cyan]" for t in tags]))
                lines.append("")
            styles = course.get("learning_styles", [])
            if styles:
                si = {"visual": "👁️", "auditory": "👂", "reading": "📖", "hands-on": "🔧", "analytical": "🧮"}
                lines.append(f"[dim]Learning styles: {'  '.join([si.get(s, '📌') + ' ' + s for s in styles])}[/dim]")
                lines.append("")
            inst = course.get("instructor_notes", "")
            if inst:
                lines.append(f"[bold yellow]👨‍🏫 Instructor Notes:[/bold yellow]")
                lines.append(f"[dim]{inst}[/dim]")
                lines.append("")
            lines.append("[dim]─── Course Statistics ───[/dim]")
            lines.append(f"  📦 {stats['total_units']} units  •  🎯 {stats['total_outcomes']} outcomes  •  📄 {stats['total_subtopics']} topics")
            if stats['total_glossary_terms'] > 0:
                lines.append(f"  📖 {stats['total_glossary_terms']} glossary terms")
            if stats['total_case_studies'] > 0:
                lines.append(f"  📋 {stats['total_case_studies']} case studies")
            if stats['total_discussion_prompts'] > 0:
                lines.append(f"  💬 {stats['total_discussion_prompts']} discussion prompts")
            if stats['total_media_items'] > 0:
                lines.append(f"  🎬 {stats['total_media_items']} media items")
            console.print(Panel("\n".join(lines), box=box.ROUNDED, border_style="cyan",
                               title=f"{course.get('icon', '📚')} {course.get('title', 'Course')}", title_align="left"))
            console.print()
            categories = course.get("categories", [])
            if categories:
                tbl = Table(box=box.ROUNDED, border_style="green")
                tbl.add_column("#", style="yellow", width=4)
                tbl.add_column("Category", style="bold white")
                tbl.add_column("Units", style="dim", width=8)
                tbl.add_column("Duration", style="dim", width=10)
                for i, cat in enumerate(categories, 1):
                    uc = len(cat.get("units", []))
                    cm = cat.get("estimated_minutes", 0)
                    cdu = format_duration(cm) if cm > 0 else "—"
                    tbl.add_row(str(i), cat.get("title", "Untitled"), str(uc), cdu)
                console.print(tbl)
                console.print()
            act = Table(box=None, show_header=False, expand=True, padding=(0, 1))
            act.add_column("Key", style="green")
            act.add_column("Action", style="white")
            act.add_row("[G]", "📖 View Glossary")
            act.add_row("[C]", "📋 View Case Studies")
            act.add_row("[M]", "🎬 View Media")
            act.add_row("[R]", "📎 View Resources")
            act.add_row("[D]", "💬 View Discussion Prompts")
            act.add_row("[A]", "🤖 Ask AI about this course")
            act.add_row("[S]", "📊 Course Stats")
            act.add_row("[0]", "Back to Course Catalog")
            console.print(act)
            console.print()
            try:
                choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().upper()
                if choice == "0":
                    return
                elif choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(categories):
                        sel = categories[idx]
                        self.show_units(sel, course, breadcrumb + [sel.get("title", "Category")])
                    else:
                        show_warning("Invalid selection!")
                        time.sleep(1)
                elif choice == "G":
                    self._show_glossary(course, breadcrumb)
                elif choice == "C":
                    self._show_case_studies(course, breadcrumb)
                elif choice == "M":
                    self._show_media(course, breadcrumb)
                elif choice == "R":
                    self._show_resources(course, breadcrumb)
                elif choice == "D":
                    self._show_discussions(course, breadcrumb)
                elif choice == "A":
                    self._ask_ai_about_course(course)
                elif choice == "S":
                    self._show_course_stats_full(course, breadcrumb)
            except (ValueError, KeyboardInterrupt):
                return

    def show_units(self, category, course, breadcrumb):
        units = category.get("units", [])
        if not units:
            show_warning("No units found in this category")
            time.sleep(1.5)
            return
        while True:
            clear_screen()
            console.print()
            console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
            console.print()
            cdu = format_duration(category.get("estimated_minutes", 0))
            cdiff = category.get("difficulty", "")
            ci = difficulty_icon(cdiff) if cdiff else ""
            hdr = [category.get("description", "")]
            if cdiff:
                hdr.append(f"{ci} {cdiff.capitalize()}")
            if cdu and cdu != "0 min":
                hdr.append(f"⏱️  {cdu}")
            show_panel(f"📦 {category.get('title', 'Category')}", " | ".join(hdr) if len(hdr) > 1 else hdr[0], "cyan")
            console.print()
            config = load_config()
            progress = config.get("learning_progress", {})
            tbl = Table(box=box.ROUNDED, border_style="green")
            tbl.add_column("#", style="yellow", width=4)
            tbl.add_column("Unit", style="bold white")
            tbl.add_column("Code", style="dim", width=18)
            tbl.add_column("Outcomes", style="dim", width=8)
            tbl.add_column("Duration", style="dim", width=8)
            tbl.add_column("Lock", style="dim", width=6)
            for i, unit in enumerate(units, 1):
                oc = len(unit.get("learning_outcomes", []))
                udu = format_duration(unit.get("estimated_minutes", 0))
                ud = difficulty_icon(unit.get("difficulty", "beginner"))
                ul = is_unit_unlocked(unit, progress)
                lk = "🔒" if not ul["unlocked"] else "🔓"
                tbl.add_row(str(i), unit.get("title", "Untitled"), unit.get("code", ""), str(oc), udu if udu != "0 min" else "—", lk)
            console.print(tbl)
            console.print()
            console.print("[dim]🔒 = Complete prerequisites/previous units first  🔓 = Available[/dim]")
            console.print()
            act = Table(box=None, show_header=False, expand=True, padding=(0, 1))
            act.add_column("Key", style="green")
            act.add_column("Action", style="white")
            gl = category.get("glossary", [])
            cs = category.get("case_studies", [])
            dp = category.get("discussion_prompts", [])
            if gl:
                act.add_row("[G]", f"📖 Glossary ({len(gl)} terms)")
            if cs:
                act.add_row("[K]", f"📋 Case Studies ({len(cs)})")
            if dp:
                act.add_row("[D]", f"💬 Discussions ({len(dp)})")
            act.add_row("[0]", "Back to Course Details")
            console.print(act)
            console.print()
            try:
                choice = console.input("[bold green]╰─► Select unit:[/bold green] ").strip().upper()
                if choice == "0":
                    return
                elif choice == "G":
                    self._show_glossary(category, breadcrumb)
                elif choice == "K":
                    self._show_case_studies(category, breadcrumb)
                elif choice == "D":
                    self._show_discussions(category, breadcrumb)
                elif choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(units):
                        sel = units[idx]
                        ul = is_unit_unlocked(sel, progress)
                        if not ul["unlocked"]:
                            clear_screen()
                            console.print()
                            show_panel("🔒 Unit Locked", ul["reason"], "yellow")
                            console.print()
                            console.input("[bold green]╰─► Press Enter to continue...[/bold green]")
                        else:
                            self.show_learning_outcomes(sel, course, category, breadcrumb + [sel.get("title", "Unit")])
                    else:
                        show_warning("Invalid selection!")
                        time.sleep(1)
            except (ValueError, KeyboardInterrupt):
                return

    def show_learning_outcomes(self, unit, course, category, breadcrumb):
        outcomes = unit.get("learning_outcomes", [])
        if not outcomes:
            show_warning("No learning outcomes found in this unit")
            time.sleep(1.5)
            return
        while True:
            clear_screen()
            console.print()
            console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
            console.print()
            udu = format_duration(unit.get("estimated_minutes", 0))
            ud = difficulty_icon(unit.get("difficulty", "beginner"))
            hdr = unit.get("description", "")
            if udu != "0 min":
                hdr += f" | {udu}"
            show_panel(f"🎯 {unit.get('title', 'Unit')}", hdr, "cyan")
            console.print()
            tools = unit.get("tools", [])
            equip = unit.get("equipment", [])
            sups = unit.get("supplies", [])
            if tools or equip or sups:
                console.print("[bold yellow]🔧 Required Materials:[/bold yellow]")
                if tools:
                    console.print(f"  [green]Tools:[/green] {', '.join(tools)}")
                if equip:
                    console.print(f"  [green]Equipment:[/green] {', '.join(equip)}")
                if sups:
                    console.print(f"  [green]Supplies:[/green] {', '.join(sups)}")
                console.print()
            perf = unit.get("performance_standards", [])
            if perf:
                console.print("[bold cyan]🎯 Performance Standards:[/bold cyan]")
                for p in perf:
                    console.print(f"  [green]•[/green] [white]{p}[/white]")
                console.print()
            config = load_config()
            progress = config.get("learning_progress", {})
            tbl = Table(box=box.ROUNDED, border_style="green")
            tbl.add_column("#", style="yellow", width=4)
            tbl.add_column("Learning Outcome", style="bold white")
            tbl.add_column("Sub-topics", style="dim", width=8)
            tbl.add_column("Min Score", style="dim", width=10)
            tbl.add_column("Lock", style="dim", width=6)
            for i, outcome in enumerate(outcomes, 1):
                sc = len(outcome.get("subtopics", []))
                ms = outcome.get("min_score", 0)
                ms_s = f"{ms}%" if ms > 0 else "—"
                ul = is_outcome_unlocked(outcome, progress, i - 1, len(outcomes))
                lk = "🔒" if not ul["unlocked"] else "🔓"
                tbl.add_row(str(i), outcome.get("title", "Untitled"), str(sc), ms_s, lk)
            console.print(tbl)
            console.print()
            console.print("[dim]🔒 = Pass previous outcome with min score first  🔓 = Available[/dim]")
            console.print()
            act = Table(box=None, show_header=False, expand=True, padding=(0, 1))
            act.add_column("Key", style="green")
            act.add_column("Action", style="white")
            ug = unit.get("glossary", [])
            uc = unit.get("case_studies", [])
            um = unit.get("media", [])
            udd = unit.get("discussion_prompts", [])
            if ug:
                act.add_row("[G]", f"📖 Glossary ({len(ug)} terms)")
            if uc:
                act.add_row("[K]", f"📋 Case Studies ({len(uc)})")
            if um:
                act.add_row("[M]", f"🎬 Media ({len(um)})")
            if udd:
                act.add_row("[D]", f"💬 Discussions ({len(udd)})")
            act.add_row("[0]", "Back to Units")
            console.print(act)
            console.print()
            try:
                choice = console.input("[bold green]╰─► Select outcome:[/bold green] ").strip().upper()
                if choice == "0":
                    return
                elif choice == "G":
                    self._show_glossary({"glossary": ug}, breadcrumb)
                elif choice == "K":
                    self._show_case_studies({"case_studies": uc}, breadcrumb)
                elif choice == "M":
                    self._show_media({"media": um}, breadcrumb)
                elif choice == "D":
                    self._show_discussions({"discussion_prompts": udd}, breadcrumb)
                elif choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(outcomes):
                        sel = outcomes[idx]
                        ul = is_outcome_unlocked(sel, progress, idx, len(outcomes))
                        if not ul["unlocked"]:
                            clear_screen()
                            console.print()
                            show_panel("🔒 Outcome Locked", ul["reason"], "yellow")
                            console.print()
                            console.input("[bold green]╰─► Press Enter to continue...[/bold green]")
                        else:
                            self.show_subtopics(sel, course, category, unit, breadcrumb + [sel.get("title", "Outcome")])
                    else:
                        show_warning("Invalid selection!")
                        time.sleep(1)
            except (ValueError, KeyboardInterrupt):
                return

    def show_subtopics(self, outcome, course, category, unit, breadcrumb):
        subtopics = outcome.get("subtopics", [])
        if not subtopics:
            show_warning("No sub-topics found")
            time.sleep(1.5)
            return
        while True:
            clear_screen()
            console.print()
            console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
            console.print()
            odu = format_duration(outcome.get("estimated_minutes", 0))
            ms = outcome.get("min_score", 0)
            ma = outcome.get("must_complete_all", False)
            hdr = [outcome.get("description", "")]
            if odu != "0 min":
                hdr.append(f"⏱️  {odu}")
            if ms > 0:
                hdr.append(f"Min score: {ms}%")
            if ma:
                hdr.append("Must complete all")
            show_panel(f"📋 {outcome.get('title', 'Outcome')}", " | ".join(hdr) if len(hdr) > 1 else hdr[0], "cyan")
            console.print()
            oc = outcome.get("case_studies", [])
            od = outcome.get("discussion_prompts", [])
            if oc or od:
                if oc:
                    console.print(f"[dim]📋 {len(oc)} case study(ies) available[/dim]")
                if od:
                    console.print(f"[dim]💬 {len(od)} discussion prompt(s) available[/dim]")
                console.print()
            ti = {"content": "📄", "example": "💡", "activity": "🔧", "assessment": "📝", "reference": "📎"}
            tbl = Table(box=box.ROUNDED, border_style="green")
            tbl.add_column("#", style="yellow", width=4)
            tbl.add_column("Sub-topic", style="bold white")
            tbl.add_column("Type", style="dim", width=10)
            tbl.add_column("Duration", style="dim", width=8)
            tbl.add_column("Difficulty", style="dim", width=6)
            for i, sub in enumerate(subtopics, 1):
                st = sub.get("type", "content")
                ic = ti.get(st, "📄")
                sdu = format_duration(sub.get("estimated_minutes", 0))
                sdi = difficulty_icon(sub.get("difficulty", "beginner"))
                tbl.add_row(str(i), sub.get("title", "Untitled"), f"{ic} {st}", sdu if sdu != "0 min" else "—", sdi)
            console.print(tbl)
            console.print()
            act = Table(box=None, show_header=False, expand=True, padding=(0, 1))
            act.add_column("Key", style="green")
            act.add_column("Action", style="white")
            if oc:
                act.add_row("[K]", "📋 View Case Studies")
            if od:
                act.add_row("[D]", "💬 View Discussion Prompts")
            act.add_row("[0]", "Back to Outcomes")
            console.print(act)
            console.print()
            try:
                choice = console.input("[bold green]╰─► Select sub-topic:[/bold green] ").strip().upper()
                if choice == "0":
                    return
                elif choice == "K":
                    self._show_case_studies({"case_studies": oc}, breadcrumb)
                elif choice == "D":
                    self._show_discussions({"discussion_prompts": od}, breadcrumb)
                elif choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(subtopics):
                        sel = subtopics[idx]
                        self.show_content(sel, course, category, unit, outcome, breadcrumb + [sel.get("title", "Sub-topic")])
                    else:
                        show_warning("Invalid selection!")
                        time.sleep(1)
            except (ValueError, KeyboardInterrupt):
                return

    def show_content(self, subtopic, course, category, unit, outcome, breadcrumb):
        clear_screen()
        console.print()
        console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
        console.print()
        title = subtopic.get("title", "Content")
        stype = subtopic.get("type", "content")
        ti = {"content": "📄", "example": "💡", "activity": "🔧", "assessment": "📝", "reference": "📎"}
        icon = ti.get(stype, "📄")
        sdu = format_duration(subtopic.get("estimated_minutes", 0))
        sdi = difficulty_icon(subtopic.get("difficulty", "beginner"))
        ss = subtopic.get("learning_styles", [])
        meta = []
        if sdu != "0 min":
            meta.append(f"⏱️  {sdu}")
        meta.append(sdi)
        if ss:
            si = {"visual": "👁️", "auditory": "👂", "reading": "📖", "hands-on": "🔧", "analytical": "🧮"}
            meta.append(" ".join([si.get(s, "📌") for s in ss]))
        if meta:
            console.print(f"[dim]{' | '.join(meta)}[/dim]")
            console.print()

        # Check if already completed
        config = load_config()
        progress = config.get("learning_progress", {})
        subtopic_id = subtopic.get("id", subtopic.get("title", ""))
        completion_key = f"hier_{subtopic_id}"
        is_complete = completion_key in progress and progress[completion_key].get("completed", False)

        if is_complete:
            console.print("[bold green]✅ Marked as complete[/bold green]")
            console.print()
        content = subtopic.get("content", "")
        if content:
            console.print(Panel(f"[white]{content}[/white]", box=box.ROUNDED, border_style="cyan",
                               title=f"{icon} {title}", title_align="left"))
        else:
            console.print(Panel("[yellow]No content available[/yellow]", box=box.ROUNDED, border_style="yellow",
                               title=f"{icon} {title}"))
        console.print()
        kp = subtopic.get("key_points", [])
        if kp:
            console.print("[bold cyan]✓ Key Points:[/bold cyan]")
            for p in kp:
                console.print(f"  [green]•[/green] [white]{p}[/white]")
            console.print()
        exs = subtopic.get("examples", [])
        for i, ex in enumerate(exs, 1):
            console.print(f"\n  [yellow]Example {i}: {ex.get('title', '')}[/yellow]")
            console.print(f"  [dim]{ex.get('explanation', '')}[/dim]")
            code = ex.get("code", "")
            if code:
                console.print(Panel(f"[dim]{code}[/dim]", box=box.ASCII, border_style="green", title="Code"))
        console.print()
        sm = subtopic.get("media", [])
        if sm:
            console.print("[bold cyan]🎬 Media Resources:[/bold cyan]")
            for m in sm:
                mt = m.get("type", "link")
                mi = {"video": "🎥", "audio": "🎧", "image": "🖼️", "link": "🔗"}.get(mt, "🔗")
                console.print(f"  {mi} [{mt}] {m.get('title', '')} — [dim]{m.get('url', '')}[/dim]")
                if m.get("description"):
                    console.print(f"     [dim]{m['description']}[/dim]")
            console.print()
        sr = subtopic.get("resources", [])
        if sr:
            console.print("[bold cyan]📎 Downloadable Resources:[/bold cyan]")
            for r in sr:
                console.print(f"  📎 {r.get('name', '')} — [dim]{r.get('url', '')}[/dim]")
            console.print()
        sdp = subtopic.get("discussion_prompts", [])
        if sdp:
            console.print("[bold cyan]💬 Discussion Prompts:[/bold cyan]")
            for d in sdp:
                console.print(f"  💬 {d}")
            console.print()

        # Assessment quiz — make it runnable
        quiz = subtopic.get("quiz", [])
        quiz_completed = False
        if stype == "assessment" and quiz:
            console.print()
            quiz_result = self._run_hierarchical_quiz(quiz, subtopic, outcome, unit, course, category)
            if quiz_result is not None:
                quiz_completed = True

        console.print(Rule("[dim]Navigation[/dim]", style="cyan"))
        console.print()
        nav = Table(box=None, show_header=False, expand=True, padding=(0, 1))
        nav.add_column("Key", style="green")
        nav.add_column("Action", style="white")
        if not is_complete and not quiz_completed:
            nav.add_row("[X]", "✅ Mark as Complete")
        nav.add_row("[B]", "Back to Sub-topics")
        nav.add_row("[0]", "Back to Main Menu")
        console.print(nav)
        console.print()
        while True:
            try:
                ch = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().lower()
                if ch == "b":
                    return
                elif ch == "0":
                    return None
                elif ch == "x" and not is_complete and not quiz_completed:
                    # Mark as complete
                    config = load_config()
                    if "learning_progress" not in config:
                        config["learning_progress"] = {}
                    config["learning_progress"][completion_key] = {
                        "completed": True,
                        "completed_at": time.time(),
                        "subtopic_title": title,
                        "subtopic_id": subtopic_id,
                        "outcome_title": outcome.get("title", ""),
                        "unit_title": unit.get("title", ""),
                        "course_title": course.get("title", ""),
                        "category": category,
                        "type": "hierarchical_subtopic",
                    }
                    save_config(config)
                    console.print(Panel(
                        "[bold green]✅ Marked as complete![/bold green]",
                        box=box.ROUNDED,
                        border_style="green",
                    ))
                    time.sleep(1)
                    # AI suggestions after completing a sub-topic
                    course_tags = course.get("tags", [])
                    self.show_ai_suggestions("subtopic_done", title=subtopic.get("title", ""),
                                            tags=course_tags, category=category)
                    return
            except KeyboardInterrupt:
                return

    def _run_hierarchical_quiz(self, quiz, subtopic, outcome, unit, course, category):
        """Run a quiz embedded in a hierarchical sub-topic. Returns score dict or None."""
        if not quiz:
            return None

        console.clear()
        console.print()
        show_panel("📝 Assessment Quiz", subtopic.get("title", "Quiz"), "cyan")
        console.print()
        console.input("[bold green]╰─► Press Enter to start...[/bold green]")

        score = 0
        total = len(quiz)
        streak = 0
        best_streak = 0

        for i, q in enumerate(quiz, 1):
            console.clear()
            console.print()
            console.print(f"[dim]Question {i}/{total}[/dim]  [yellow]🔥 Streak: {streak}[/yellow]")
            console.print()

            question = q.get("question", q.get("q", "?"))
            options = q.get("options", [])
            answer_idx = q.get("answer", q.get("correct", 0))
            explanation = q.get("explanation", q.get("exp", "No explanation."))

            console.print(Panel(f"[bold white]{question}[/bold white]", box=box.ROUNDED, border_style="cyan"))
            console.print()

            for j, opt in enumerate(options, 1):
                console.print(f"  [green][{j}][/green] [white]{opt}[/white]")
            console.print()

            try:
                ans = console.input("[bold green]╰─► Your answer:[/bold green] ").strip()
                ans_num = int(ans) - 1

                if ans_num == answer_idx:
                    score += 1
                    streak += 1
                    best_streak = max(streak, best_streak)
                    console.print(Panel("[bold green]✓ Correct![/bold green]", box=box.ROUNDED, border_style="green"))
                else:
                    streak = 0
                    correct_text = options[answer_idx] if answer_idx < len(options) else "?"
                    console.print(Panel(
                        f"[bold red]✗ Wrong![/bold red]\n[cyan]Correct: {correct_text}\n💡 {explanation}[/cyan]",
                        box=box.ROUNDED, border_style="red",
                    ))
            except (ValueError, IndexError):
                console.print(Panel("[red]Invalid input![/red]", box=box.ROUNDED, border_style="red"))
            except KeyboardInterrupt:
                break
            time.sleep(1.5)

        percentage = (score / total * 100) if total > 0 else 0
        console.clear()
        console.print()

        # Save quiz result to learning_progress for outcome gating
        config = load_config()
        if "learning_progress" not in config:
            config["learning_progress"] = {}
        outcome_id = outcome.get("id", outcome.get("title", ""))
        quiz_key = f"hier_outcome_{outcome_id}"
        config["learning_progress"][quiz_key] = {
            "completed": True,
            "completed_at": time.time(),
            "last_score": score,
            "last_accuracy": percentage,
            "questions": total,
            "correct": score,
            "best_streak": best_streak,
            "outcome_title": outcome.get("title", ""),
            "unit_title": unit.get("title", ""),
            "course_title": course.get("title", ""),
            "category": category,
            "type": "hierarchical_outcome_quiz",
        }
        save_config(config)

        # Check achievements
        from kslearn.engines.achievements import check_achievements
        check_achievements(config, config.get("learning_progress", {}), content_loader.get_brain_stats().get("total_qa_pairs", 0))

        result_content = f"Questions: {total}\nCorrect: [green]{score}[/green]\nScore: {score}/{total}\nAccuracy: [{'green' if percentage >= 70 else 'yellow' if percentage >= 50 else 'red'}]{percentage:.0f}%[/{'green' if percentage >= 70 else 'yellow' if percentage >= 50 else 'red'}]\nBest Streak: [red]{best_streak} 🔥[/red]"
        if percentage >= 80:
            result_content += "\n\n[bold green]🎉 Excellent![/bold green]"
        elif percentage >= 60:
            result_content += "\n\n[bold yellow]👍 Good job![/bold yellow]"
        else:
            result_content += "\n\n[bold cyan]📚 Review and try again![/bold cyan]"

        console.print(Panel(result_content, box=box.ROUNDED, border_style="cyan", title="📊 Quiz Results"))
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

        # AI suggestions after hierarchical quiz
        course_tags = course.get("tags", [])
        self.show_ai_suggestions("quiz_done", title=course.get("title", ""),
                                tags=course_tags, category=category)
        return {"score": score, "total": total, "percentage": percentage}

    def _show_glossary(self, data, breadcrumb):
        glossary = data.get("glossary", [])
        if not glossary:
            show_info("No glossary terms available")
            time.sleep(1.5)
            return
        clear_screen()
        console.print()
        console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
        console.print()
        show_panel(f"📖 Glossary ({len(glossary)} terms)", "Key terms and definitions", "cyan")
        console.print()
        table = Table(box=box.ROUNDED, border_style="green")
        table.add_column("Term", style="bold white")
        table.add_column("Definition", style="dim")
        for t in glossary:
            table.add_row(t.get("term", ""), t.get("definition", ""))
        console.print(table)
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

    def _show_case_studies(self, data, breadcrumb):
        cases = data.get("case_studies", [])
        if not cases:
            show_info("No case studies available")
            time.sleep(1.5)
            return
        clear_screen()
        console.print()
        console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
        console.print()
        show_panel(f"📋 Case Studies ({len(cases)})", "Real-world scenarios and analysis", "cyan")
        console.print()
        for i, case in enumerate(cases, 1):
            console.print(Panel(f"[bold white]{case.get('title', f'Case Study {i}')}[/bold white]\n\n[dim]{case.get('scenario', case.get('description', ''))}[/dim]", box=box.ROUNDED, border_style="magenta"))
            console.print()
            questions = case.get("questions", [])
            if questions:
                console.print("[bold yellow]Questions to consider:[/bold yellow]")
                for q in questions:
                    console.print(f"  [green]•[/green] {q}")
                console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

    def _show_media(self, data, breadcrumb):
        media = data.get("media", [])
        if not media:
            show_info("No media resources available")
            time.sleep(1.5)
            return
        clear_screen()
        console.print()
        console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
        console.print()
        show_panel(f"🎬 Media Resources ({len(media)})", "Videos, images, and audio", "cyan")
        console.print()
        for m in media:
            mt = m.get("type", "link")
            mi = {"video": "🎥", "audio": "🎧", "image": "🖼️", "link": "🔗"}.get(mt, "🔗")
            console.print(Panel(f"[bold white]{mi} {m.get('title', '')}[/bold white]\n\n[dim]{m.get('description', '')}[/dim]\n\n[blue underline]{m.get('url', '')}[/blue underline]", box=box.ROUNDED, border_style="blue"))
            console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

    def _show_resources(self, data, breadcrumb):
        resources = data.get("resources", [])
        if not resources:
            show_info("No downloadable resources available")
            time.sleep(1.5)
            return
        clear_screen()
        console.print()
        console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
        console.print()
        show_panel(f"📎 Resources ({len(resources)})", "Downloadable files and links", "cyan")
        console.print()
        for r in resources:
            console.print(Panel(f"[bold white]📎 {r.get('name', '')}[/bold white]\n\n[dim]{r.get('description', '')}[/dim]\n\n[blue underline]{r.get('url', '')}[/blue underline]", box=box.ROUNDED, border_style="green"))
            console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

    def _show_discussions(self, data, breadcrumb):
        prompts = data.get("discussion_prompts", [])
        if not prompts:
            show_info("No discussion prompts available")
            time.sleep(1.5)
            return
        clear_screen()
        console.print()
        console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
        console.print()
        show_panel(f"💬 Discussion Prompts ({len(prompts)})", "Questions for reflection and group discussion", "cyan")
        console.print()
        for i, p in enumerate(prompts, 1):
            console.print(f"  [yellow]{i}.[/yellow] [white]{p}[/white]")
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

    def _show_course_stats_full(self, course, breadcrumb):
        clear_screen()
        console.print()
        console.print(f"[dim]📂 {' → '.join(breadcrumb)}[/dim]")
        console.print()
        stats = get_course_stats(course)
        show_panel(f"📊 {course.get('title', 'Course')} — Statistics", "Complete course breakdown", "cyan")
        console.print()
        st = Table(box=box.ROUNDED, border_style="cyan")
        st.add_column("Metric", style="bold white")
        st.add_column("Value", style="dim")
        st.add_row("Difficulty", f"{difficulty_icon(stats['difficulty'])} {stats['difficulty'].capitalize()}")
        st.add_row("Estimated Duration", stats['duration_formatted'])
        st.add_row("Credits", str(stats['credits']))
        st.add_row("Version", stats['version'])
        st.add_row("Units", str(stats['total_units']))
        st.add_row("Learning Outcomes", str(stats['total_outcomes']))
        st.add_row("Sub-topics", str(stats['total_subtopics']))
        st.add_row("Glossary Terms", str(stats['total_glossary_terms']))
        st.add_row("Case Studies", str(stats['total_case_studies']))
        st.add_row("Discussion Prompts", str(stats['total_discussion_prompts']))
        st.add_row("Media Items", str(stats['total_media_items']))
        if stats['tags']:
            st.add_row("Tags", ", ".join(stats['tags']))
        console.print(st)
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

    def _ask_ai_about_course(self, course):
        """Ask AI about this course — choose offline (JSON Brain) or online (AI Chat)."""
        title = course.get("title", "this course")
        desc = course.get("description", "")
        tags = ", ".join(course.get("tags", []))
        console.clear()
        console.print()
        console.print(Panel(
            f"[bold cyan]{title}[/bold cyan]\n[dim]{desc}[/dim]\n" +
            (f"[dim]Tags: {tags}[/dim]\n" if tags else "") +
            "[dim]Select AI mode:[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
            title="🤖 Ask AI about this Course",
        ))
        console.print()
        mode_table = Table(box=None, show_header=False, expand=True, padding=(0, 2))
        mode_table.add_column("Key", style="green")
        mode_table.add_column("Mode", style="white")
        mode_table.add_column("Description", style="dim")
        mode_table.add_row("[1]", "Offline (JSON Brain)", "Search local knowledge base")
        mode_table.add_row("[2]", "Online (AI Chat)", "Use tgpt-powered AI chat")
        mode_table.add_row("[0]", "Back", "Return to previous menu")
        console.print(mode_table)
        console.print()
        try:
            choice = console.input("[bold green]╰─► Select mode:[/bold green] ").strip().lower()
        except KeyboardInterrupt:
            return
        if choice == "1":
            self._ask_ai_offline_about_course(course)
        elif choice == "2":
            self._ask_ai_online_about_course(course)

    def _ask_ai_offline_about_course(self, course):
        """Offline AI about course — search JSON Brain."""
        title = course.get("title", "")
        cat = course.get("category", "")
        console.clear()
        console.print()
        console.print(Panel(
            f"[bold cyan]Course: {title}[/bold cyan]\n[dim]Offline mode — searching knowledge base[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
            title="🤖 Ask AI (Offline)",
        ))
        console.print()
        while True:
            try:
                question = console.input("[bold green]╰─► Q:[/bold green] ").strip()
                if question.lower() in ("quit", "exit", "q"):
                    break
                if not question:
                    continue
                # Search with course context
                full_query = f"{title} {cat} {question}"
                results = content_loader.search_brain(full_query, limit=3)
                if results:
                    console.print()
                    console.print("[bold green]A:[/bold green]")
                    for result in results[:1]:
                        console.print(Panel(f"[white]{result['answer']}[/white]", box=box.ROUNDED, border_style="green"))
                    console.print()
                    content_loader.add_qa_to_brain(question, results[0]["answer"], category=title, tags=["course_ai", "offline"])
                else:
                    console.print(Panel("[yellow]No answer found in knowledge base.[/yellow]", box=box.ROUNDED, border_style="yellow"))
                    answer = console.input("[bold yellow]╰─► Provide answer (or Enter to skip):[/bold yellow] ").strip()
                    if answer and len(answer) >= 10:
                        content_loader.add_qa_to_brain(question, answer, category=title, tags=["user-provided"])
                        console.print(Panel("[green]✓ Added to knowledge brain![/green]", box=box.ROUNDED, border_style="green"))
                console.print()
            except KeyboardInterrupt:
                break

    def _ask_ai_online_about_course(self, course):
        """Online AI chat about course."""
        title = course.get("title", "")
        cat = course.get("category", "")
        try:
            from kslearn.main.ai_chat import AIChat
        except ImportError:
            show_error("AI Chat module not available")
            time.sleep(2)
            return
        chat = AIChat()
        chat.system_prompt = (
            f"You are kslearn AI Tutor. The user is studying the course: '{title}'"
            f"{' in category: ' + cat if cat else ''}. "
            f"Be concise, educational, and encouraging."
        )
        console.clear()
        console.print()
        console.print(Panel(
            f"[bold cyan]Course: {title}[/bold cyan]\n"
            f"[dim]Provider: {chat.provider} | Type 'quit' to exit[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
            title="🤖 Ask AI (Online)",
        ))
        console.print()
        while True:
            try:
                question = console.input("[bold green]╰─► Q:[/bold green] ").strip()
                if question.lower() in ("quit", "exit", "q"):
                    break
                if not question:
                    continue
                response = chat.chat(question)
                if response:
                    console.print()
                    console.print("[bold green]A:[/bold green]")
                    console.print(Panel(f"[white]{response}[/white]", box=box.ROUNDED, border_style="green"))
                    console.print()
                    if chat.auto_save_to_brain:
                        chat._save_to_knowledge_brain(question, response)
                else:
                    console.print(Panel("[yellow]No response from AI. Check connection/provider.[/yellow]", box=box.ROUNDED, border_style="yellow"))
            except KeyboardInterrupt:
                break

    def show_ai_suggestions(self, context, title="", tags=None, category=""):
        """Show AI-powered 'What to Study Next' suggestions to keep learners engaged."""
        config = load_config()
        progress = config.get("learning_progress", {})
        completed_ids = {k for k in progress if k.startswith("hier_") and progress.get(k, {}).get("completed")}

        suggestions = []

        # 1. Based on current course tags/category
        if tags:
            courses = self._get_all_courses()
            for c in courses:
                c_tags = [t.lower() for t in c.get("tags", [])]
                c_cat = c.get("category", "").lower()
                overlap = sum(1 for t in tags if t.lower() in c_tags or t.lower() in c_cat or c_cat in t.lower())
                if overlap >= 1 and c.get("title", "").lower() != title.lower():
                    c_id = c.get("id", "")
                    c_progress = sum(1 for cid in completed_ids if c_id in cid)
                    c_total = c.get("estimated_minutes", 0)
                    progress_pct = (c_progress / max(c_total, 1)) * 100
                    status = "✅ In Progress" if 0 < progress_pct < 100 else ("🔓 New" if progress_pct == 0 else "🔒 Started")
                    matched = [t for t in tags if t.lower() in str(c_tags) + " " + c_cat]
                    suggestions.append({
                        "type": "course",
                        "title": c.get("title", ""),
                        "desc": c.get("description", ""),
                        "reason": f"Shares {overlap} topic(s): {', '.join(matched[:3])}",
                        "icon": c.get("icon", "📚"),
                        "difficulty": c.get("difficulty", "beginner"),
                        "duration": format_minutes(c.get("estimated_minutes", 0)),
                        "status": status,
                    })

        # 2. Based on weak areas from quiz history
        if context == "quiz_done":
            for k, v in progress.items():
                if "quiz" in k or "hier_outcome" in k:
                    score = v.get("score", 100)
                    if score < 80:
                        suggestions.append({
                            "type": "review",
                            "title": f"Review: {v.get('topic_title', k)}",
                            "desc": f"You scored {score}% — try again to reach 80%+",
                            "reason": "💡 Weak area — practice makes perfect!",
                            "icon": "📝",
                            "difficulty": "",
                            "duration": "~10 min",
                            "status": "⚠️ Needs Review",
                        })

        # 3. Based on streak & daily goal momentum
        streak = config.get("study_streak", {}).get("current", 0)
        if streak >= 3:
            suggestions.append({
                "type": "challenge",
                "title": "🔥 Streak Challenge",
                "desc": f"You're on a {streak}-day streak! Try a timed quiz to keep it going.",
                "reason": "⚡ You're on fire — push your limits!",
                "icon": "🏆",
                "difficulty": "",
                "duration": "5 min",
                "status": "🔥 Active Streak",
            })

        # 4. Spaced review recommendations
        try:
            now = datetime.now()
            review_due = []
            for k, v in progress.items():
                if k.startswith("hier_") and v.get("completed") and v.get("completed_at"):
                    try:
                        completed_dt = datetime.fromisoformat(v["completed_at"])
                        days_since = (now - completed_dt).days
                        if 1 <= days_since <= 3:
                            review_due.append(v.get("subtopic_title", k))
                    except (ValueError, TypeError):
                        pass
            if review_due:
                suggestions.append({
                    "type": "spaced_review",
                    "title": "📅 Spaced Review",
                    "desc": f"{len(review_due)} topic(s) are due for review today",
                    "reason": "🧠 Perfect timing — review now to lock it in memory",
                    "icon": "📅",
                    "difficulty": "",
                    "duration": "~15 min",
                    "status": "⏰ Due Today",
                })
        except Exception:
            pass

        # 5. If nothing else, suggest popular/beginner content
        if not suggestions:
            courses = self._get_all_courses()
            for c in courses[:2]:
                if c.get("difficulty") == "beginner" and c.get("title", "").lower() != title.lower():
                    suggestions.append({
                        "type": "course",
                        "title": c.get("title", ""),
                        "desc": c.get("description", ""),
                        "reason": "🌟 Great starting point for beginners",
                        "icon": c.get("icon", "📚"),
                        "difficulty": "beginner",
                        "duration": format_minutes(c.get("estimated_minutes", 0)),
                        "status": "🔓 New",
                    })

        if not suggestions:
            return

        # Display suggestions
        console.print()
        intro = self._get_suggestion_intro(context)
        console.print(Panel(
            f"[bold cyan]🤖 AI Tutor Says:[/bold cyan]\n\n{intro}",
            box=box.ROUNDED,
            border_style="cyan",
            title="✨ What to Study Next",
        ))

        for i, s in enumerate(suggestions[:3], 1):
            diff_icon = difficulty_icon(s["difficulty"]) if s["difficulty"] else ""
            card = Panel(
                f"[bold white]{s['icon']} {s['title']}[/bold white] {diff_icon}\n\n"
                f"[dim]{s['desc']}[/dim]\n\n"
                f"[cyan]{s['reason']}[/cyan]\n\n"
                f"[dim]{s.get('duration', '')} • {s['status']}[/dim]",
                box=box.ROUNDED,
                border_style="green",
            )
            console.print(card)
            console.print()

        # Quick actions
        console.print("[dim]Quick actions:[/dim]")
        quick = Table(box=None, show_header=False, padding=(0, 1))
        quick.add_column("Key", style="green")
        quick.add_column("Action", style="white")

        if any(s["type"] == "course" for s in suggestions):
            quick.add_row("[C]", "Browse suggested courses")
        if any(s["type"] == "review" for s in suggestions):
            quick.add_row("[R]", "Start spaced review")
        if any(s["type"] == "challenge" for s in suggestions):
            quick.add_row("[T]", "Take timed quiz challenge")
        quick.add_row("[0]", "Continue")
        console.print(quick)
        console.print()

        try:
            choice = console.input("[bold green]╰─► Your choice:[/bold green] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return

        if choice == "c":
            course_titles = [s["title"] for s in suggestions if s["type"] == "course"]
            if course_titles:
                console.print(f"\n[dim]Showing {len(course_titles)} suggested course(s)...[/dim]")
                time.sleep(1)
        elif choice == "r":
            run_spaced_review()
        elif choice == "t":
            from kslearn.cli import _run_timed_quiz
            _run_timed_quiz()

    def _get_suggestion_intro(self, context):
        intros = {
            "search": "Based on your search, here's what might interest you:",
            "quiz_done": "Great effort! Here's what to focus on next:",
            "course_viewed": "Since you're exploring this topic, check these out:",
            "subtopic_done": "You're making progress! Keep the momentum going:",
            "login": "Welcome back! Here's your personalized study plan:",
        }
        return intros.get(context, "Here are some personalized suggestions:")

    def _get_all_courses(self):
        """Get all available hierarchical courses."""
        all_courses = []
        for ksl_file in self.loader._discover_ksl_files():
            data = self.loader._load_ksl_data(ksl_file)
            if data and "courses" in data:
                for c in data["courses"]:
                    c["_source"] = str(ksl_file)
                    all_courses.append(c)
        return all_courses

    def search_all_notes(self, query, limit=20):
        """Search across all hierarchical course content for a query string.
        
        Returns list of dicts with category, title, snippet, and breadcrumb.
        """
        results = []
        query_lower = query.lower()
        courses = self._get_all_courses()
        for course in courses:
            cat_list = course.get("categories", [])
            for cat in cat_list:
                cat_title = cat.get("title", "")
                units = cat.get("units", [])
                for unit in units:
                    unit_title = unit.get("title", "")
                    outcomes = unit.get("learning_outcomes", [])
                    for outcome in outcomes:
                        outcome_title = outcome.get("title", "")
                        subtopics = outcome.get("subtopics", [])
                        for sub in subtopics:
                            sub_title = sub.get("title", "")
                            content = sub.get("content", "")
                            key_points = sub.get("key_points", [])
                            examples = sub.get("examples", [])
                            # Search in title + content + key points + examples
                            searchable = f"{sub_title} {content} {' '.join(key_points)}"
                            for ex in examples:
                                searchable += f" {ex.get('title', '')} {ex.get('explanation', '')} {ex.get('code', '')}"
                            if query_lower in searchable.lower():
                                # Extract snippet
                                idx = searchable.lower().find(query_lower)
                                start = max(0, idx - 40)
                                end = min(len(searchable), idx + len(query) + 80)
                                snippet = ("..." if start > 0 else "") + searchable[start:end].strip() + ("..." if end < len(searchable) else "")
                                results.append({
                                    "category": cat_title,
                                    "title": sub_title,
                                    "snippet": snippet,
                                    "breadcrumb": [course.get("title", ""), cat_title, unit_title, outcome_title, sub_title],
                                    "type": sub.get("type", "content"),
                                })
        # Also search flat notes (from combined/notes ksl files)
        for notes_file in self.loader._discover_ksl_files():
            data = self.loader._load_ksl_data(notes_file)
            if not data:
                continue
            ctype = get_ksl_content_type(data)
            if ctype == TYPE_COMBINED:
                combined = extract_combined_content(data)
                topics = combined.get("notes", [])
            else:
                topics = extract_notes(data)
            if not topics:
                continue
            cat_meta = get_ksl_metadata(data)
            cat_name = cat_meta.get("category", cat_meta.get("title", str(notes_file.stem)))
            for topic in topics:
                t_title = topic.get("title", "")
                t_content = topic.get("content", "")
                searchable = f"{t_title} {t_content}"
                if query_lower in searchable.lower():
                    idx = searchable.lower().find(query_lower)
                    start = max(0, idx - 40)
                    end = min(len(searchable), idx + len(query) + 80)
                    snippet = ("..." if start > 0 else "") + searchable[start:end].strip() + ("..." if end < len(searchable) else "")
                    results.append({
                        "category": cat_name,
                        "title": t_title,
                        "snippet": snippet,
                        "breadcrumb": [cat_name, t_title],
                        "type": "note",
                    })
        return results[:limit]


def run_hierarchical_notes():
    """Main entry point for hierarchical notes browsing."""
    viewer = HierarchicalNotesViewer()
    viewer.show_courses()
