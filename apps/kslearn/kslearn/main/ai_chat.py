#!/usr/bin/env python3
"""AI Chat & Tutor for kslearn - Powered by tgpt (termux-ai)"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box

from kslearn.ui import (
    console,
    show_panel,
    show_success,
    show_error,
    show_warning,
    show_info,
    print_divider,
    prompt_confirm,
)

# Paths — use centralized loader paths
from kslearn.loader import DATA_DIR, CONFIG_DIR
TGPT_CONFIG_DIR = CONFIG_DIR / "tgpt"
TGPT_API_KEYS_FILE = TGPT_CONFIG_DIR / "api_keys"
CHAT_HISTORY_FILE = DATA_DIR / "chat_history.json"

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
TGPT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class AIChat:
    """AI Chat interface using tgpt CLI (termux-ai backend)"""

    def __init__(self):
        self.provider: str = "sky"
        self.api_key: Optional[str] = None
        self.chat_history: List[Dict] = []
        self.system_prompt = (
            "You are kslearn AI Tutor — a friendly, knowledgeable assistant for learning "
            "absolutely anything: math, science, languages, history, psychology, religion, "
            "music, art, business, technology, and more. kslearn is a platform built for "
            "lifelong learners of all ages and backgrounds.\n\n"
            "If someone asks who you are or who made you, say: "
            "'I'm kslearn AI, your learning companion. kslearn was created by kslearn, "
            "with credit also to their partner who helped bring this platform to life.' "
            "Always give credit to both.\n\n"
            "Be concise, educational, and encouraging. Adapt your tone to the subject — "
            "be it a child learning arithmetic or an adult studying philosophy."
        )
        self.tgpt_path = self._find_tgpt()
        self.auto_save_to_brain: bool = True  # Default: enabled
        self.load_api_keys()
        self.load_chat_history()
        self.load_settings()

    def _find_tgpt(self) -> str:
        """Find tgpt binary"""
        paths_to_check = [
            "/data/data/com.termux/files/usr/bin/tgpt",
            "/usr/local/bin/tgpt",
            "/usr/bin/tgpt",
        ]
        
        for path in paths_to_check:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        import shutil
        tgpt_in_path = shutil.which("tgpt")
        if tgpt_in_path:
            return tgpt_in_path
        
        return "tgpt"

    def load_api_keys(self):
        """Load API keys from tgpt config"""
        if TGPT_API_KEYS_FILE.exists():
            try:
                with open(TGPT_API_KEYS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line:
                            key, value = line.split("=", 1)
                            if key == self.provider:
                                self.api_key = value
                                break
            except IOError:
                pass

    def save_api_key(self, provider: str, key: str):
        """Save API key for a provider"""
        keys = {}
        
        if TGPT_API_KEYS_FILE.exists():
            try:
                with open(TGPT_API_KEYS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line:
                            k, v = line.split("=", 1)
                            keys[k] = v
            except IOError:
                pass
        
        keys[provider] = key
        
        with open(TGPT_API_KEYS_FILE, "w", encoding="utf-8") as f:
            for k, v in keys.items():
                f.write(f"{k}={v}\n")
        # Set restrictive permissions on Unix (skip on Windows)
        if os.name != "nt":
            try:
                os.chmod(TGPT_API_KEYS_FILE, 0o600)
            except OSError:
                pass

    def get_providers(self) -> Dict[str, Dict]:
        """Get tgpt-supported providers"""
        return {
            "sky": {
                "name": "Sky (Free, Default)",
                "requires_key": False,
                "description": "Free provider using gpt-4.1-mini",
            },
            "phind": {
                "name": "Phind (Developers)",
                "requires_key": False,
                "description": "Great for coding questions",
            },
            "deepseek": {
                "name": "DeepSeek",
                "requires_key": True,
                "description": "Requires API key",
                "key_url": "https://platform.deepseek.com/api-keys",
            },
            "gemini": {
                "name": "Google Gemini",
                "requires_key": True,
                "description": "Requires API key",
                "key_url": "https://aistudio.google.com/apikey",
            },
            "groq": {
                "name": "Groq (Fast & Free)",
                "requires_key": True,
                "description": "Fast inference, free tier available",
                "key_url": "https://console.groq.com/keys",
            },
            "openai": {
                "name": "OpenAI",
                "requires_key": True,
                "description": "Requires API key",
                "key_url": "https://platform.openai.com/api-keys",
            },
            "ollama": {
                "name": "Ollama (Local)",
                "requires_key": False,
                "description": "Local models, no API key needed",
            },
            "kimi": {
                "name": "Kimi",
                "requires_key": False,
                "description": "Moonshot AI assistant",
            },
            "isou": {
                "name": "ISou",
                "requires_key": False,
                "description": "Search-powered AI",
            },
            "pollinations": {
                "name": "Pollinations",
                "requires_key": False,
                "description": "Free image and text generation",
            },
        }

    def chat(self, message: str) -> Optional[str]:
        """Send message via tgpt CLI"""
        if not self.tgpt_path:
            show_error("tgpt not found. Install termux-ai or tgpt.")
            show_info("Run: pkg install termux-ai")
            return None

        try:
            cmd = [self.tgpt_path, "--provider", self.provider, "-q"]

            # Add API key if provider requires it
            provider_info = self.get_providers().get(self.provider, {})
            if provider_info.get("requires_key", False) and self.api_key:
                cmd.extend(["--key", self.api_key])

            # Add system prompt using -preprompt (tgpt flag)
            if self.system_prompt:
                cmd.extend(["-preprompt", self.system_prompt])

            cmd.append(message)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                response = result.stdout.strip()
                
                # Save to chat history
                self.chat_history.append({"role": "user", "content": message})
                self.chat_history.append({"role": "assistant", "content": response})
                self.save_chat_history()
                
                # Auto-save useful Q&A to knowledge brain (if enabled)
                if self.auto_save_to_brain:
                    self._save_to_knowledge_brain(message, response)
                
                return response
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                show_error(f"tgpt error ({result.returncode}): {error_msg}")
                return None

        except subprocess.TimeoutExpired:
            show_error("tgpt request timed out (60s). Try again or switch provider.")
            show_info("Free providers like Sky can be slow during peak times.")
            return None
        except FileNotFoundError:
            show_error("tgpt command not found")
            show_info("Install termux-ai: pkg install termux-ai")
            return None
        except Exception as e:
            show_error(f"tgpt error: {e}")
            return None

    def _save_to_knowledge_brain(self, question: str, answer: str):
        """Automatically save useful Q&A pairs to knowledge brain"""
        try:
            # Reject slash commands, empty, or junk inputs
            if not question or not answer:
                return
            q = question.strip()
            a = answer.strip()
            if not q or not a:
                return
            if q.startswith("/"):
                return
            if q.lower() in ("quit", "exit", "q", "back", "b", "clear", "save", "config", "provider"):
                return
            if a.lower() in ("quit", "exit", "q", "back", "b", "none", "n/a", ""):
                return
            if len(a) < 10:  # Too short to be a useful answer
                return

            # Auto-detect category from question keywords
            category = self._detect_category(question)

            # Generate relevant tags
            tags = self._generate_tags(question, category)

            # Add to brain
            json_brain.add_qa_pair(
                question=question,
                answer=answer,
                category=category,
                tags=tags,
                context="Learned from AI chat conversation"
            )
        except Exception:
            # Silently fail - don't interrupt chat if brain save fails
            pass

    def _detect_category(self, question: str) -> str:
        """Auto-detect category from question keywords"""
        question_lower = question.lower()
        
        # Category keywords mapping
        category_keywords = {
            # Technology
            "python": ["python", "pip", "venv", "def ", "lambda", "django", "flask", "__init__"],
            "ai_ml": ["machine learning", "ai", "neural", "deep learning", "model", "training", "nlp", "transformer"],
            "webdev": ["html", "css", "javascript", "react", "node", "api", "http", "json", "dom", "frontend", "backend"],
            "cybersecurity": ["security", "hack", "attack", "encryption", "malware", "phishing", "firewall", "vulnerability"],
            "linux": ["linux", "terminal", "bash", "shell", "chmod", "sudo", "ssh", "ubuntu", "command"],
            "git": ["git", "commit", "push", "pull", "branch", "merge", "github", "repository"],
            "datascience": ["pandas", "numpy", "data science", "visualization", "jupyter", "scikit"],
            # General Education
            "math": ["math", "algebra", "calculus", "geometry", "trigonometry", "arithmetic", "equation", "fraction", "number", "multiply", "divide", "add", "subtract"],
            "science": ["physics", "chemistry", "biology", "atom", "molecule", "element", "gravity", "force", "cell", "organism", "evolution"],
            "psychology": ["psychology", "mental", "cognitive", "behavior", "emotion", "therapy", "depression", "anxiety", "mind", "brain", "neuroscience"],
            "history": ["history", "ancient", "medieval", "war", "empire", "civilization", "revolution", "century", "historical"],
            "religion": ["religion", "christianity", "bible", "jesus", "god", "church", "prayer", "faith", "islam", "buddhism", "hinduism", "theology", "spiritual"],
            "language": ["grammar", "vocabulary", "writing", "essay", "reading", "literature", "poetry", "novel", "english", "spanish", "french", "language"],
            "music": ["music", "instrument", "guitar", "piano", "melody", "harmony", "chord", "scale", "rhythm", "song"],
            "art": ["art", "painting", "drawing", "color", "design", "sculpture", "creative", "canvas"],
            "business": ["business", "marketing", "finance", "accounting", "management", "entrepreneur", "startup", "invest", "money", "economy"],
            "health": ["health", "nutrition", "exercise", "diet", "medical", "disease", "wellness", "fitness"],
            # Fallback
            "general": ["programming", "code", "software", "algorithm", "database", "sql", "technology", "computer"],
        }
        
        # Find best matching category
        best_category = "general"
        best_score = 0
        
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            if score > best_score:
                best_score = score
                best_category = category
        
        return best_category

    def _generate_tags(self, question: str, category: str) -> List[str]:
        """Generate relevant tags from question"""
        tags = [category, "ai-chat"]
        
        # Add topic-specific tags
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["what", "define", "explain"]):
            tags.append("definition")
        if any(word in question_lower for word in ["how", "way", "method"]):
            tags.append("howto")
        if any(word in question_lower for word in ["difference", "vs", "compare"]):
            tags.append("comparison")
        if any(word in question_lower for word in ["example", "sample", "code"]):
            tags.append("example")
        if any(word in question_lower for word in ["error", "problem", "issue", "fix"]):
            tags.append("troubleshooting")
        if any(word in question_lower for word in ["best", "good", "recommend"]):
            tags.append("best-practices")
            
        return list(set(tags))  # Remove duplicates

    def load_chat_history(self):
        """Load chat history from file"""
        if CHAT_HISTORY_FILE.exists():
            try:
                with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.chat_history = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.chat_history = []
        else:
            self.chat_history = []

    def save_chat_history(self):
        """Save chat history to file"""
        try:
            if len(self.chat_history) > 50:
                self.chat_history = self.chat_history[-50:]
            with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.chat_history, f, indent=2)
        except IOError:
            pass

    def clear_chat_history(self):
        """Clear chat history"""
        self.chat_history = []
        if CHAT_HISTORY_FILE.exists():
            try:
                CHAT_HISTORY_FILE.unlink()
                show_success("Chat history cleared")
            except IOError:
                pass

    def load_settings(self):
        """Load chat settings from config file"""
        settings_file = DATA_DIR / "chat_settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    self.auto_save_to_brain = settings.get("auto_save_to_brain", True)
            except (json.JSONDecodeError, IOError):
                self.auto_save_to_brain = True
        else:
            self.auto_save_to_brain = True

    def save_settings(self):
        """Save chat settings to config file"""
        settings_file = DATA_DIR / "chat_settings.json"
        settings = {
            "auto_save_to_brain": self.auto_save_to_brain,
            "last_provider": self.provider,
        }
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except IOError:
            pass

    def toggle_auto_save(self) -> bool:
        """Toggle auto-save to brain setting"""
        self.auto_save_to_brain = not self.auto_save_to_brain
        self.save_settings()
        return self.auto_save_to_brain

    def _generate_learning_suggestions(self, question, response):
        """Generate proactive 'what to learn next' suggestions by analyzing
        the ACTUAL conversation text — not hardcoded keywords."""
        import re

        # Combine question + response for topic extraction
        combined = (question + " " + response).lower()

        # Extract key technical terms (2-3 word phrases, code terms, etc.)
        # Look for: function names, technical concepts, named entities
        patterns = [
            r'([a-z]+(?:\s+[a-z]+){0,2})\s+(?:function|method|class|type|variable|loop|array|object|module|package|library|framework)',
            r'(?:learn|study|understand|explore|know|about|what\s+is|how\s+to|explain)\s+([a-z][a-z\s]{2,30}?)(?:\.|,|in|with|and|or|is|are|was|were)',
            r'(python|javascript|html|css|react|node|django|flask|express|sql|nosql|mongo|postgres|git|docker|linux|windows|macos|android|ios|api|rest|graphql|ml|ai|data\s+science|web\s+dev|cyber\s*security|networking|database|programming|algorithm|data\s+structure)',
        ]

        detected_topics = []
        for pattern in patterns:
            matches = re.findall(pattern, combined)
            for m in matches:
                if isinstance(m, tuple):
                    m = m[-1] if m[-1] else m[0]
                term = m.strip()
                if len(term) >= 3 and term not in ('the', 'and', 'for', 'this', 'that', 'what', 'how', 'can', 'you', 'your'):
                    detected_topics.append(term.title())

        # Deduplicate
        detected_topics = list(dict.fromkeys(detected_topics))[:5]

        if not detected_topics:
            # Fallback: suggest general next steps
            detected_topics = ['Related Concepts']

        # Build dynamic suggestions from extracted topics
        suggestions = []
        for topic in detected_topics[:3]:
            suggestions.append({
                'emoji': '📚',
                'text': f'Dive deeper into {topic}',
                'hint': f'Explore more advanced aspects of {topic.lower()}',
            })

        # Add a quiz suggestion based on what was discussed
        suggestions.append({
            'emoji': '📝',
            'text': f'Take a quiz on what you just learned',
            'hint': 'Test your understanding with interactive questions',
        })

        # Add a practice suggestion
        suggestions.append({
            'emoji': '🔧',
            'text': 'Practice with a hands-on project',
            'hint': 'Apply what you learned in a real scenario',
        })

        return {
            'intro': 'Based on our conversation, here\'s what to explore next:',
            'items': suggestions[:4],
        }


def ai_config_menu():
    """Interactive AI configuration menu"""
    chat = AIChat()

    while True:
        console.clear()
        console.print(f"\n[bold cyan]══ AI Configuration ══[/bold cyan]\n")

        show_panel("AI Configuration", "Set up your AI provider (powered by tgpt)", "cyan")

        providers = chat.get_providers()

        console.print()
        console.print(f"  [cyan]Current Provider:[/cyan] ", end="")
        if chat.provider:
            console.print(f"[bold green]{providers.get(chat.provider, {}).get('name', chat.provider)}[/bold green]")
        else:
            console.print("[yellow]Not configured[/yellow]")

        # Show auto-save status
        save_status = "[green]Enabled[/green]" if chat.auto_save_to_brain else "[yellow]Disabled[/yellow]"
        console.print(f"  [cyan]Auto-save to Brain:[/cyan] {save_status}")

        console.print()
        print_divider("Options", "dim")
        console.print()
        console.print("  [yellow]1[/yellow]  Select Provider")
        console.print("  [yellow]2[/yellow]  Set API Key (for paid providers)")
        console.print("  [yellow]3[/yellow]  Toggle Auto-save to Brain")
        console.print("  [yellow]4[/yellow]  Clear Chat History")
        console.print("  [yellow]5[/yellow]  View Provider Info")
        console.print("  [yellow]0[/yellow]  Back")
        console.print()

        try:
            choice = console.input("  [bold green]Select option:[/bold green] ").strip()

            if choice == "0":
                return
            elif choice == "1":
                select_provider_interactive(chat)
            elif choice == "2":
                set_api_key_interactive(chat)
            elif choice == "3":
                # Toggle auto-save
                enabled = chat.toggle_auto_save()
                status = "[green]enabled[/green]" if enabled else "[yellow]disabled[/yellow]"
                console.print(Panel(
                    f"Auto-save to brain {status}",
                    box=box.ROUNDED,
                    border_style="green" if enabled else "yellow",
                ))
                time.sleep(1.5)
            elif choice == "4":
                if prompt_confirm("Clear chat history?", default=False):
                    chat.clear_chat_history()
            elif choice == "5":
                view_providers(chat)

        except KeyboardInterrupt:
            return


def view_providers(chat: AIChat):
    """View all available providers"""
    console.clear()
    show_panel("Available AI Providers", "Powered by tgpt (termux-ai)", "cyan")
    console.print()
    
    providers = chat.get_providers()
    
    for key, info in providers.items():
        name = info.get("name", key)
        desc = info.get("description", "")
        requires_key = info.get("requires_key", False)
        
        key_status = "[red]🔑 Key Required[/red]" if requires_key else "[green]✓ Free[/green]"
        
        console.print(f"[bold cyan]{name}[/bold cyan]")
        console.print(f"  [dim]{desc}[/dim]")
        console.print(f"  {key_status}")
        console.print()
    
    console.input("  [dim]Press Enter to continue...[/dim]")


def select_provider_interactive(chat: AIChat):
    """Interactive provider selection"""
    console.clear()
    show_panel("Select AI Provider", "Choose your preferred provider", "cyan")
    console.print()
    
    providers = chat.get_providers()
    options = list(providers.keys())
    
    for i, key in enumerate(options, 1):
        info = providers[key]
        name = info.get("name", key)
        requires_key = info.get("requires_key", False)
        key_status = "[yellow]🔑[/yellow]" if requires_key else "[green]✓[/green]"
        console.print(f"  [bold cyan]{i}[/bold cyan] {key_status} [white]{name}[/white]")
    
    console.print()
    console.print("  [bold cyan]0[/bold cyan] Back")
    console.print()
    
    try:
        choice = console.input("  [bold green]Select provider:[/bold green] ").strip()
        
        if choice == "0":
            return
        
        choice_num = int(choice)
        if 1 <= choice_num <= len(options):
            selected = options[choice_num - 1]
            chat.provider = selected
            chat.api_key = None
            chat.load_api_keys()
            
            provider_info = providers[selected]
            if provider_info.get("requires_key", False):
                show_warning(f"{selected} requires an API key")
                if prompt_confirm("Set API key now?", default=True):
                    set_api_key_interactive(chat)
            else:
                show_success(f"Provider set to: {selected}")
            
            # Save provider preference
            chat.save_api_key(selected, chat.api_key or "")
            
    except ValueError:
        show_warning("Please enter a number")
    except KeyboardInterrupt:
        pass


def set_api_key_interactive(chat: AIChat):
    """Interactive API key setup"""
    console.print()
    show_panel("Set API Key", "Enter your API key securely", "cyan")
    console.print()
    
    providers = chat.get_providers()
    current = providers.get(chat.provider, {})
    
    console.print(f"  [cyan]Provider:[/cyan] {current.get('name', chat.provider)}")
    console.print(f"  [dim]Get key: {current.get('key_url', 'N/A')}[/dim]")
    console.print()
    
    api_key = console.input("  [bold green]Enter API key:[/bold green] ").strip()
    
    if api_key:
        chat.save_api_key(chat.provider, api_key)
        show_success("API key saved!")
    else:
        show_warning("No API key entered")
    
    console.print()
    console.input("  [dim]Press Enter to continue...[/dim]")


def ai_chat_interface():
    """Interactive AI chat interface"""
    chat = AIChat()

    console.clear()
    
    # Header banner
    providers = chat.get_providers()
    provider_name = providers.get(chat.provider, {}).get("name", chat.provider)
    
    console.print()
    console.print(Panel(
        f"[bold cyan]AI Chat[/bold cyan]  •  Powered by tgpt\n[dim]Provider: {provider_name}[/dim]\n[green]✓ Conversations auto-saved to Knowledge Brain[/green]",
        box=box.ROUNDED,
        border_style="cyan",
        title="🤖",
        title_align="left",
    ))
    console.print()

    # Commands help
    commands_table = Table(
        box=None,
        show_header=False,
        expand=True,
        padding=(0, 2),
    )
    commands_table.add_column("Command", style="yellow")
    commands_table.add_column("Description", style="dim")
    
    commands_table.add_row("/provider", "Change AI provider")
    commands_table.add_row("/clear", "Clear chat history")
    commands_table.add_row("/save", "Save last Q&A to brain")
    commands_table.add_row("/config", "AI settings")
    commands_table.add_row("/back", "Return to menu")
    commands_table.add_row("/quit", "Exit chat")
    
    console.print(commands_table)
    console.print()
    console.print(Rule("[dim]Start chatting[/dim]", style="cyan"))
    console.print()

    # Chat loop
    while True:
        try:
            # Input with styled prompt
            console.print()
            message = console.input(
                "[bold green]╭─[/bold green] [bold white]You[/bold white]\n"
                "[bold green]╰─►[/bold green] "
            ).strip()

            if not message:
                continue

            if message.lower() in ("/quit", "/exit", "/q"):
                console.print()
                console.print(Panel(
                    "[cyan]Goodbye! Keep learning![/cyan]",
                    box=box.ROUNDED,
                    border_style="green",
                ))
                time.sleep(1)
                break

            if message.lower() in ("/back", "/b"):
                console.print()
                console.print(Panel(
                    "[cyan]Returning to menu...[/cyan]",
                    box=box.ROUNDED,
                    border_style="green",
                ))
                time.sleep(1)
                break

            if message.lower() == "/clear":
                chat.clear_chat_history()
                console.print(Panel(
                    "[green]✓ Chat history cleared[/green]",
                    box=box.ROUNDED,
                    border_style="green",
                ))
                continue

            if message.lower() == "/save":
                if len(chat.chat_history) >= 2:
                    # Save last Q&A pair to brain
                    last_user = None
                    last_assistant = None
                    for msg in reversed(chat.chat_history[-10:]):
                        if msg["role"] == "assistant" and last_assistant is None:
                            last_assistant = msg["content"]
                        elif msg["role"] == "user" and last_user is None:
                            last_user = msg["content"]
                            break
                    
                    if last_user and last_assistant:
                        chat._save_to_knowledge_brain(last_user, last_assistant)
                        console.print(Panel(
                            "[green]✓ Last Q&A saved to Knowledge Brain![/green]\n[dim]Category auto-detected, tags generated[/dim]",
                            box=box.ROUNDED,
                            border_style="green",
                        ))
                    else:
                        console.print(Panel(
                            "[yellow]No conversation to save[/yellow]",
                            box=box.ROUNDED,
                            border_style="yellow",
                        ))
                else:
                    console.print(Panel(
                        "[yellow]No conversation history yet[/yellow]",
                        box=box.ROUNDED,
                        border_style="yellow",
                    ))
                continue

            if message.lower() == "/provider":
                select_provider_interactive(chat)
                providers = chat.get_providers()
                provider_name = providers.get(chat.provider, {}).get("name", chat.provider)
                console.print(Panel(
                    f"[green]✓ Now using:[/green] [bold]{provider_name}[/bold]",
                    box=box.ROUNDED,
                    border_style="green",
                ))
                # Update header
                console.clear()
                console.print()
                console.print(Panel(
                    f"[bold cyan]AI Chat[/bold cyan]  •  Powered by tgpt\n[dim]Provider: {provider_name}[/dim]\n[green]✓ Conversations auto-saved to Knowledge Brain[/green]",
                    box=box.ROUNDED,
                    border_style="cyan",
                    title="🤖",
                    title_align="left",
                ))
                console.print()
                console.print(commands_table)
                console.print()
                console.print(Rule("[dim]Start chatting[/dim]", style="cyan"))
                continue

            if message.lower() == "/config":
                ai_config_menu()
                console.clear()
                console.print()
                console.print(Panel(
                    f"[bold cyan]AI Chat[/bold cyan]  •  Powered by tgpt\n[dim]Provider: {provider_name}[/dim]\n[green]✓ Conversations auto-saved to Knowledge Brain[/green]",
                    box=box.ROUNDED,
                    border_style="cyan",
                    title="🤖",
                    title_align="left",
                ))
                console.print()
                console.print(commands_table)
                console.print()
                console.print(Rule("[dim]Start chatting[/dim]", style="cyan"))
                continue

            # Show AI thinking indicator
            console.print()
            console.print(Panel(
                "[dim]AI is thinking...[/dim]\n[dim]Response will be saved to Knowledge Brain[/dim]",
                box=box.ROUNDED,
                border_style="yellow",
                title="🤖",
                title_align="left",
            ))

            response = chat.chat(message)

            if response:
                console.clear()
                console.print()
                console.print(Panel(
                    f"[bold cyan]AI Chat[/bold cyan]  •  Powered by tgpt\n[dim]Provider: {provider_name}[/dim]\n[green]✓ Auto-saved to Knowledge Brain[/green]",
                    box=box.ROUNDED,
                    border_style="cyan",
                    title="🤖",
                    title_align="left",
                ))
                console.print()

                # Display AI response in a nice panel
                console.print(Panel(
                    f"[white]{response}[/white]",
                    box=box.ROUNDED,
                    border_style="green",
                    title="💬 AI Response",
                    title_align="left",
                ))
                console.print()

                # ─── Proactive AI Tutor Suggestions ──────────────────────────
                # After each response, suggest what to explore next
                suggestions = chat._generate_learning_suggestions(message, response)
                if suggestions:
                    console.print(Panel(
                        "[bold cyan]🎓 AI Tutor Suggests:[/bold cyan]\n\n"
                        f"[dim]{suggestions['intro']}[/dim]",
                        box=box.ROUNDED,
                        border_style="cyan",
                        title="✨ Keep Learning",
                    ))
                    console.print()
                    for i, s in enumerate(suggestions["items"][:3], 1):
                        console.print(Panel(
                            f"[bold white]{s['emoji']} {s['text']}[/bold white]\n"
                            f"[dim]{s.get('hint', '')}[/dim]",
                            box=box.ROUNDED,
                            border_style="green",
                        ))
                        console.print()
            else:
                console.print(Panel(
                    "[red]✗ No response from AI. Try again or switch provider.[/red]",
                    box=box.ROUNDED,
                    border_style="red",
                ))

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Chat interrupted. Returning to menu...[/yellow]")
            time.sleep(1)
            break


def main():
    """Main entry point for AI chat"""
    ai_chat_interface()


if __name__ == "__main__":
    main()
