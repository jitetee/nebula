#!/usr/bin/env python3
"""
Quiz Engine - Centralized quiz system for all topics
Loads quiz data dynamically from JSON files with progress tracking
"""

import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from kslearn.loader import content_loader, KSL_DIR, CONFIG_DIR
from kslearn.ui import console, show_panel, show_success, show_error, show_info, show_warning, print_divider
from kslearn.config import load_config, save_config


class QuizEngine:
    """Professional quiz engine with progress tracking"""

    def __init__(self):
        self.loader = content_loader
        self.current_category: Optional[str] = None
        self.current_topic: Optional[str] = None
        self.score: int = 0
        self.correct: int = 0
        self.total_answered: int = 0
        self.total_questions: int = 0
        self.streak: int = 0
        self.best_streak: int = 0
        self.session_questions: List[Dict] = []

    @staticmethod
    def normalize_question(q_data: Dict) -> Dict:
        """Normalize question data to handle different JSON formats."""
        return {
            "q": q_data.get("q", q_data.get("question", "Unknown question")),
            "options": q_data.get("options", []),
            "answer": q_data.get("answer", q_data.get("correct", 0)),
            "exp": q_data.get("exp", q_data.get("explanation", "No explanation available.")),
        }

    def reset(self):
        """Reset quiz engine state for a new quiz session."""
        self.score = 0
        self.correct = 0
        self.total_answered = 0
        self.streak = 0
        self.best_streak = 0
        self.session_questions = []

    def get_available_quizzes(self) -> List[Dict[str, str]]:
        """Get list of all available quiz categories from .ksl files"""
        return self.loader.get_all_quiz_categories()
    
    def load_quiz(self, category: str) -> Optional[Dict]:
        """Load quiz data from JSON file"""
        try:
            data = self.loader.load_quiz_strict(category)
            return data
        except (FileNotFoundError, ValueError) as e:
            show_error(str(e))
            return None
    
    def select_topic(self, quiz_data: Dict) -> Optional[str]:
        """Let user select a topic within the quiz category"""
        topics = quiz_data.get("topics", [])

        if not topics:
            show_error("No topics available in this quiz")
            return None

        console.print()
        show_panel("Select Topic", f"Choose a topic from {quiz_data.get('metadata', {}).get('title', 'this quiz')}", "cyan")
        console.print()

        for i, topic in enumerate(topics, 1):
            question_count = len(topic.get("questions", []))
            console.print(f"  [yellow]{i:02d}[/yellow] [white]{topic.get('title', f'Topic {i}')}[/white] [dim]({question_count} questions)[/dim]")

        console.print()
        console.print(f"  [yellow] R[/yellow] [white]🎲 Random Topic[/white]")
        console.print(f"  [yellow] 0[/yellow] [white]Back[/white]")
        console.print()

        while True:
            try:
                choice = console.input("[bold green]╰─► Select topic:[/bold green] ").strip().upper()

                if choice == "0":
                    return None
                elif choice == "R":
                    return random.choice(topics)
                else:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(topics):
                        return topics[choice_num - 1]
                    else:
                        show_warning("Invalid selection!")
            except (ValueError, KeyboardInterrupt):
                show_warning("Please enter a valid number")
                return None
    
    def run_quiz(self, category: str, topic: str, questions: List[Dict], max_questions: int = 6) -> Dict[str, Any]:
        """Run a quiz session for a specific topic"""
        self.current_category = category
        self.current_topic = topic
        self.score = 0
        self.correct = 0
        self.total_answered = 0
        self.streak = 0
        self.best_streak = 0
        
        # Shuffle and limit questions
        shuffled = questions[:]
        random.shuffle(shuffled)
        quiz_questions = shuffled[:max_questions]
        
        console.print()
        show_panel(
            f"📝 {topic}",
            f"Answer {len(quiz_questions)} questions. Type 'q' to quit anytime.",
            "cyan"
        )
        console.print()
        time.sleep(1)
        
        for i, q_data in enumerate(quiz_questions, 1):
            console.clear()
            self._display_question(i, q_data, len(quiz_questions))
            
            if not self._ask_question(q_data):
                console.print("\n[yellow]Quiz ended early.[/yellow]")
                break
        
        results = self._show_results()
        self._save_progress()

        # Check for new achievements
        from kslearn.config import load_config
        from kslearn.engines.achievements import check_achievements

        config = load_config()
        new_achs = check_achievements(config, config.get("learning_progress", {}), content_loader.get_brain_stats().get("total_qa_pairs", 0))

        return results
    
    def _display_question(self, num: int, q_data: Dict, total: int):
        """Display a question with progress info"""
        # Normalize question data
        q_data = self.normalize_question(q_data)

        # Progress bar
        progress = f"[{num}/{total}]"
        console.print(f"\n[dim]{progress}[/dim]  [yellow]🔥 Streak: {self.streak}[/yellow]")
        print_divider()

        # Question
        console.print(f"\n[bold white]{q_data['q']}[/bold white]\n")

        # Options
        for i, option in enumerate(q_data.get("options", []), 1):
            console.print(f"  [green][{i}][/green] [white]{option}[/white]")

        console.print()
        console.print(f"[dim]  [Q] Quit[/dim]")
        console.print()
    
    def _ask_question(self, q_data: Dict) -> bool:
        """Get user answer and provide feedback"""
        # Normalize question data
        q_data = self.normalize_question(q_data)
        
        try:
            answer = console.input("[bold green]╰─► Your answer:[/bold green] ").strip().lower()
            
            if answer == 'q':
                return False
            
            answer_num = int(answer) - 1
            self.total_answered += 1
            
            correct_answer = q_data.get("answer", 0)
            options = q_data.get("options", [])
            explanation = q_data.get("exp", "No explanation available.")
            
            if answer_num == correct_answer:
                # Correct!
                points = 10 + (self.streak * 2)
                self.score += points
                self.correct += 1
                self.streak += 1
                self.best_streak = max(self.streak, self.best_streak)
                
                console.print(f"\n[bold green]✓ Correct! +{points} points[/bold green]")
                console.print(f"[cyan]💡 {explanation}[/cyan]")
            else:
                # Wrong
                self.streak = 0
                correct_text = options[correct_answer] if correct_answer < len(options) else "Unknown"
                
                console.print(f"\n[bold red]✗ Incorrect[/bold red]")
                console.print(f"[green]Correct: {correct_text}[/green]")
                console.print(f"[cyan]💡 {explanation}[/cyan]")
            
            time.sleep(2)
            return True
            
        except (ValueError, IndexError):
            console.print("\n[red]Invalid input! Please enter a number.[/red]")
            time.sleep(1)
            return True
        except KeyboardInterrupt:
            return False

    def _ask_question_timed(self, q_data: Dict) -> bool:
        """Get user answer with minimal feedback (for timed quiz)"""
        # Normalize question data
        q_data = self.normalize_question(q_data)
        
        try:
            answer = console.input("[bold green]╰─► Answer:[/bold green] ").strip()

            if answer.lower() == 'q':
                return False

            answer_num = int(answer) - 1
            self.total_answered += 1

            correct_answer = q_data.get("answer", 0)
            options = q_data.get("options", [])
            explanation = q_data.get("exp", "")

            if answer_num == correct_answer:
                points = 10 + (self.streak * 2)
                self.score += points
                self.correct += 1
                self.streak += 1
                self.best_streak = max(self.streak, self.best_streak)
                console.print(f"[bold green]✓ +{points}[/bold green]")
            else:
                self.streak = 0
                correct_text = options[correct_answer] if correct_answer < len(options) else "?"
                console.print(f"[bold red]✗ {correct_text}[/bold red]")

            time.sleep(0.5)
            return True

        except (ValueError, IndexError):
            console.print("[red]Invalid![/red]")
            time.sleep(0.3)
            return True
        except KeyboardInterrupt:
            return False
    
    def _show_results(self) -> Dict[str, Any]:
        """Display quiz results and return stats"""
        console.clear()
        
        percentage = (self.correct / self.total_answered * 100) if self.total_answered > 0 else 0
        
        show_panel(
            "📊 Quiz Results",
            f"Topic: {self.current_topic}",
            "cyan"
        )
        
        console.print()
        
        results_table = [
            ("Questions", str(self.total_answered)),
            ("Correct", f"[green]{self.correct}[/green]"),
            ("Score", f"[yellow]{self.score}[/yellow]"),
            ("Accuracy", f"[cyan]{percentage:.1f}%[/cyan]"),
            ("Best Streak", f"[red]{self.best_streak} 🔥[/red]"),
        ]
        
        for label, value in results_table:
            console.print(f"  [bold]{label}:[/bold] {value}")
        
        console.print()
        
        # Performance feedback
        if percentage >= 80:
            console.print("  [bold green]🏆 Excellent! You've mastered this topic![/bold green]")
        elif percentage >= 60:
            console.print("  [bold yellow]👍 Good job! Keep practicing![/bold yellow]")
        elif percentage >= 40:
            console.print("  [bold blue]📚 Review the material and try again![/bold blue]")
        else:
            console.print("  [bold cyan]💪 Keep learning! Practice makes perfect![/bold cyan]")
        
        console.print()
        
        return {
            "category": self.current_category,
            "topic": self.current_topic,
            "questions": self.total_answered,
            "correct": self.correct,
            "score": self.score,
            "accuracy": percentage,
            "best_streak": self.best_streak,
            "timestamp": time.time()
        }
    
    def _save_progress(self):
        """Save quiz progress to config (single read-modify-write)"""
        progress_key = f"quiz_{self.current_category}_{self.current_topic}"
        accuracy = (self.correct / self.total_answered * 100) if self.total_answered > 0 else 0

        # Single read-modify-write
        config = load_config()
        if "learning_progress" not in config:
            config["learning_progress"] = {}
        config["learning_progress"][progress_key] = {
            "last_score": self.score,
            "last_accuracy": accuracy,
            "completed_at": time.time(),
            "topic": self.current_topic,
            "category": self.current_category,
            "questions": self.total_answered,
            "correct": self.correct,
            "best_streak": self.best_streak,
        }
        save_config(config)


def run_quiz_interactive():
    """Main entry point for interactive quiz selection"""
    engine = QuizEngine()
    
    while True:
        console.clear()
        show_panel("📝 Quiz Center", "Select a quiz category", "cyan")
        console.print()
        
        quizzes = engine.get_available_quizzes()
        
        if not quizzes:
            show_error("No quiz files found in data/ksl/")
            show_info("Pack your JSON files into .ksl using ksl_tool.py!")
            console.input("\nPress Enter to continue...")
            return
        
        # Display quiz categories
        for i, quiz in enumerate(quizzes, 1):
            console.print(f"  [yellow]{i:02d}[/yellow] [white]{quiz['title']}[/white]")
            console.print(f"       [dim]{quiz['description']}[/dim]")
        
        console.print()
        console.print(f"  [yellow] 0[/yellow] [white]Back[/white]")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Select quiz:[/bold green] ").strip()
            
            if choice == "0":
                return
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(quizzes):
                selected = quizzes[choice_num - 1]
                
                # Load quiz data
                quiz_data = engine.load_quiz(selected["key"])
                if not quiz_data:
                    continue
                
                # Select topic
                topic = engine.select_topic(quiz_data)
                if not topic:
                    continue

                # Get questions for topic (topic is now a dict from the topics list)
                topic_title = topic.get("title", f"Topic {topic.get('id', '?')}")
                questions = topic.get("questions", [])
                if not questions:
                    show_error(f"No questions found for topic: {topic_title}")
                    time.sleep(2)
                    continue

                # Run quiz
                engine.run_quiz(selected["key"], topic_title, questions)
                
                console.input("\n[bold green]Press Enter to continue...[/bold green]")
            else:
                show_warning("Invalid selection!")
                time.sleep(1)
                
        except (ValueError, KeyboardInterrupt):
            console.print("\n[yellow]Returning to menu...[/yellow]")
            time.sleep(1)


if __name__ == "__main__":
    run_quiz_interactive()


# --- Timed Quiz (60-Second Speed Mode) ---

def run_timed_quiz(engine, category: str, questions: List[Dict], duration: int = 60):
    """Run a timed quiz — answer as many as possible in the time limit."""
    import time

    console.clear()
    console.print()
    show_panel("⚡ Speed Quiz", f"Answer as many as you can in {duration} seconds!\n[dim]Type 'q' at any question to exit early[/dim]", "yellow")
    console.print()
    console.input("[bold green]╰─► Press Enter to start the timer...[/bold green]")

    engine.reset()
    engine.total_questions = len(questions)

    start_time = time.time()
    q_index = 0

    while True:
        elapsed = time.time() - start_time
        remaining = duration - int(elapsed)

        if remaining <= 0 or q_index >= len(questions):
            break

        console.clear()
        console.print()

        # Timer display
        timer_color = "red" if remaining <= 10 else "yellow" if remaining <= 20 else "green"
        console.print(f"[bold {timer_color}]⏱️  {remaining}s remaining[/bold {timer_color}]")
        console.print(f"[dim]Questions answered: {engine.total_answered} | Score: {engine.score}[/dim]")
        console.print()

        q_data = questions[q_index]
        engine._display_question(engine.total_answered + 1, q_data, len(questions))

        try:
            result = engine._ask_question_timed(q_data)
            if result:
                q_index += 1
        except Exception:
            break

    # Show results
    console.clear()
    console.print()
    show_panel("⚡ Speed Quiz Results", "Time's up!", "yellow")
    console.print()

    results_table = [
        ("Time", f"{duration}s"),
        ("Questions Answered", str(engine.total_answered)),
        ("Correct", f"[green]{engine.correct}[/green]"),
        ("Score", f"[yellow]{engine.score}[/yellow]"),
        ("Best Streak", f"[red]{engine.best_streak} 🔥[/red]"),
    ]

    for label, value in results_table:
        console.print(f"  [bold]{label}:[/bold] {value}")

    console.print()

    # Save best and progress (profile-scoped)
    config = load_config()
    profile_name = config.get("active_profile", "default")
    timed_best_key = f"profile_{profile_name}_timed_quiz_best"
    best = config.get(timed_best_key, config.get("timed_quiz_best", 0))
    is_new_best = engine.total_answered > best
    if is_new_best:
        config[timed_best_key] = engine.total_answered

    # Save to learning_progress
    if "learning_progress" not in config:
        config["learning_progress"] = {}
    accuracy = (engine.correct / engine.total_answered * 100) if engine.total_answered > 0 else 0
    config["learning_progress"][f"timed_{category}"] = {
        "last_score": engine.score,
        "last_accuracy": accuracy,
        "completed_at": time.time(),
        "topic": "Timed Quiz",
        "category": category,
        "questions": engine.total_answered,
        "correct": engine.correct,
        "best_streak": engine.best_streak,
    }

    save_config(config)

    if is_new_best:
        console.print(f"[bold green]🎉 New Personal Best: {engine.total_answered} questions![/bold green]")

    console.print()
    return {"answered": engine.total_answered, "correct": engine.correct, "score": engine.score}


# --- Quiz Review Mode (Retake Wrong Answers Only) ---

def run_quiz_review(engine, category: str, wrong_questions: List[Dict]):
    """Retake only the questions the user got wrong."""
    if not wrong_questions:
        show_panel("🎉 Perfect Review", "You got everything right! Nothing to review.", "green")
        time.sleep(2)
        return

    console.clear()
    console.print()
    show_panel("📝 Quiz Review", f"Retaking {len(wrong_questions)} question(s) you missed", "cyan")
    console.print()
    console.input("[bold green]╰─► Press Enter to start review...[/bold green]")

    engine.reset()
    engine.total_questions = len(wrong_questions)

    for i, q_data in enumerate(wrong_questions, 1):
        console.clear()
        console.print()
        console.print(f"[dim]Review Question {i}/{len(wrong_questions)}[/dim]")
        console.print()

        engine._display_question(i, q_data, len(wrong_questions))

        try:
            result = engine._ask_question(q_data)
            if not result:
                console.print("\n[yellow]Review ended early.[/yellow]")
                break
        except KeyboardInterrupt:
            break

    engine._show_results()
