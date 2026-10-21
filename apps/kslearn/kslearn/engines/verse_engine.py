#!/usr/bin/env python3
"""
Verse Engine v2.0 — KSL-Verse Interactive Multiverse Learning Game

Complete feature set:
- Lifelines (50/50, Skip, Hint)
- Items / Inventory system
- Skill Tree visualization
- Weakness Tracker + spaced review
- Daily Verse Challenge
- Speedrun Mode + personal records
- Difficulty modes (Story / Normal / Hard / Ironman)
- Combo Multiplier
- NPCs with memory
- Branching story paths
- Hidden secrets / Easter eggs
- World Lore codex
- Mini-bosses + Boss Phases + Boss Evolution
- Multiple question types
- Spaced verse review
- Concept linking
- Mastery levels per topic
- Profile card export
- ASCII art headers + animated narratives
- Epilogue / credits system
- Compact mode toggle
- Prestige System
- Marathon Mode
- Random Events
- Deep Stats Dashboard
- Streak Calendar with heatmap
- Performance Timeline
- Practice Mode
- Player Journal
- Concept Glossary
- Mentor System
- World Map
- Achievement Showcase
- Quote System
- Custom Questions
- Terminal Sound Effects
- World Themes
"""

import json
import time
import random
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from kslearn.loader import content_loader, KSL_DIR
from kslearn.ui import console, show_panel, show_error, show_info, show_warning, show_success, print_divider
from kslearn.config import load_config, save_config

# ─── Constants ───────────────────────────────────────────────────────

VERSE_RANKS = [
    (0, "Novice Walker"),
    (200, "Apprentice Explorer"),
    (500, "Seasoned Voyager"),
    (1000, "Knowledge Seeker"),
    (2000, "Realm Wanderer"),
    (3500, "Domain Master"),
    (5500, "Cosmos Sage"),
    (8000, "Universe Architect"),
    (12000, "Multiverse Legend"),
    (20000, "Verse Transcendent"),
]

PRESTIGE_RANKS = [
    (0, "", "🌟"),
    (1, "Prestige I", "⭐"),
    (2, "Prestige II", "💫"),
    (3, "Prestige III", "🌠"),
    (5, "Ascendant", "✨"),
    (10, "Eternal", "🔱"),
]

MASTERY_TIERS = [
    (0, "Unranked", "⬜"),
    (25, "Bronze", "🥉"),
    (50, "Silver", "🥈"),
    (75, "Gold", "🥇"),
    (90, "Diamond", "💎"),
    (100, "Master", "👑"),
]

DIFFICULTY_MODIFIERS = {
    "story": {"xp_mult": 0.75, "hints": True, "forgiving": True, "ironman": False, "marathon": False, "label": "Story Mode", "icon": "📖"},
    "normal": {"xp_mult": 1.0, "hints": False, "forgiving": False, "ironman": False, "marathon": False, "label": "Normal", "icon": "⚔️"},
    "hard": {"xp_mult": 1.5, "hints": False, "forgiving": False, "ironman": False, "marathon": False, "label": "Hard Mode", "icon": "🔥"},
    "ironman": {"xp_mult": 2.0, "hints": False, "forgiving": False, "ironman": True, "marathon": False, "label": "Ironman", "icon": "💀"},
    "marathon": {"xp_mult": 3.0, "hints": True, "forgiving": False, "ironman": False, "marathon": True, "label": "Marathon", "icon": "🏃"},
}

QUESTION_TYPES = {
    "multiple_choice": "Multiple Choice",
    "true_false": "True / False",
    "code_output": "Code Output",
    "fill_blank": "Fill in the Blank",
    "ordering": "Order the Steps",
}

# ─── Quotes ──────────────────────────────────────────────────────────

QUOTES = [
    ("\"The only way to do great work is to love what you do.\"", "— Steve Jobs"),
    ("\"First, solve the problem. Then, write the code.\"", "— John Johnson"),
    ("\"Code is like humor. When you have to explain it, it's bad.\"", "— Cory House"),
    ("\"The best error message is the one that never shows up.\"", "— Thomas Fuchs"),
    ("\"Programs must be written for people to read, and only incidentally for machines to execute.\"", "— Harold Abelson"),
    ("\"Any fool can write code that a computer can understand. Good programmers write code that humans can understand.\"", "— Martin Fowler"),
    ("\"Truth can only be found in one place: the code.\"", "— Robert C. Martin"),
    ("\"Simplicity is the soul of efficiency.\"", "— Austin Freeman"),
    ("\"Make it work, make it right, make it fast.\"", "— Kent Beck"),
    ("\"Learning never exhausts the mind.\"", "— Leonardo da Vinci"),
    ("\"The expert in anything was once a beginner.\"", "— Helen Hayes"),
    ("\"Education is the passport to the future.\"", "— Malcolm X"),
    ("\"It's not a bug — it's an undocumented feature.\"", "— Anonymous"),
    ("\"Talk is cheap. Show me the code.\"", "— Linus Torvalds"),
    ("\"In theory, theory and practice are the same. In practice, they're not.\"", "— Yogi Berra"),
]

# ─── ASCII Art Headers ──────────────────────────────────────────────

WORLD_ASCII = {
    "webdev_cosmos": r"""
  ╔══════════════════════════════╗
  ║     W E B   D E V            ║
  ║     C O S M O S   🌐         ║
  ╚══════════════════════════════╝""",
}

DEFAULT_ASCII = r"""
  ╔══════════════════════════════════════════╗
  ║                                          ║
  ║       🌌   W O R L D   🌌                ║
  ║                                          ║
  ╚══════════════════════════════════════════╝"""

WORLD_MAP_ASCII = r"""
         🌌  T H E   V E R S E  🌌

    🌐 WebDev Cosmos ─────────────┐
     [Beginner]                   │
         │                        │
         ▼                        ▼
    🐍 Python Kingdom        ⚡ Cyber Fortress
     [Locked - Lvl 5]        [Locked - Lvl 8]
         │                        │
         ▼                        ▼
    🗄️  Data Dimension       🎮 Game Galaxy
     [Locked - Lvl 10]       [Locked - Lvl 12]
         │
         ▼
    🧬 Science Galaxy
     [Locked - Lvl 15]
"""

BOSS_ASCII = r"""
     ╔══════════════════════════════╗
     ║   ⚔️  B O S S   B A T T L E  ⚔️  ║
     ╚══════════════════════════════╝"""

BOSS_PHASE2_ASCII = r"""
     ╔══════════════════════════════╗
     ║   🔥  P H A S E   2  🔥      ║
     ║      BOSS ENRAGED!            ║
     ╚══════════════════════════════╝"""

# ─── Item Definitions ────────────────────────────────────────────────

ITEMS_DB = {
    "syntax_shard": {"name": "Syntax Shard", "icon": "🔮", "desc": "A fragment of pure code structure", "effect": "hint", "value": 1},
    "logic_gem": {"name": "Logic Gem", "icon": "💎", "desc": "Crystallized reasoning", "effect": "hint", "value": 2},
    "streak_crystal": {"name": "Streak Crystal", "icon": "🔥", "desc": "Stores the energy of consecutive wins", "effect": "xp_boost", "value": 1.5},
    "lore_scroll": {"name": "Lore Scroll", "icon": "📜", "desc": "Ancient knowledge of the Verse", "effect": "unlock_lore", "value": 1},
    "skip_token": {"name": "Skip Token", "icon": "⏭️", "desc": "Bypass a single scenario", "effect": "skip", "value": 1},
    "shield_charm": {"name": "Shield Charm", "icon": "🛡️", "desc": "Protects against a wrong answer penalty", "effect": "shield", "value": 1},
    "memory_orb": {"name": "Memory Orb", "icon": "🔵", "desc": "Enhances spaced review priority", "effect": "review_boost", "value": 1},
    "key_fragment": {"name": "Key Fragment", "icon": "🗝️", "desc": "A piece of a master key", "effect": "collectible", "value": 1},
    "xp_potion": {"name": "XP Potion", "icon": "🧪", "desc": "Instant 50 XP boost", "effect": "instant_xp", "value": 50},
    "compass": {"name": "Navigator's Compass", "icon": "🧭", "desc": "Points toward weakest area", "effect": "show_weakness", "value": 1},
}

# ─── NPC Definitions ─────────────────────────────────────────────────

NPCS_DB = {
    "the_builder": {
        "id": "the_builder", "name": "The Builder", "icon": "👷",
        "greetings": {
            "first": "Ah, a new Walker arrives. I've been building these structures for eons. Let me show you the way.",
            "return": "Welcome back, Walker. The structures have been waiting for you.",
            "advanced": "You've grown strong, Walker. I have less to teach you now.",
        },
        "farewells": {
            "normal": "Keep building your knowledge, one tag at a time.",
            "perfect": "Flawless execution! You truly understand the structure.",
            "struggling": "Don't worry — even the greatest structures start with a single line.",
        },
        "mentor_advice": "Focus on semantics — they matter more than you think. Screen readers and search engines depend on them.",
    },
    "the_stylist": {
        "id": "the_stylist", "name": "The Stylist", "icon": "🎨",
        "greetings": {
            "first": "Structure is nothing without style, darling. Let me paint your education in brilliant colors.",
            "return": "Ah, my favorite student returns! Ready to make things beautiful?",
            "advanced": "Your eye for design has sharpened considerably. Impressive.",
        },
        "farewells": {
            "normal": "Remember — good design is invisible, but its absence is deafening.",
            "perfect": "Magnificent! You see the art in the code.",
            "struggling": "Even the best designers iterate. Keep trying!",
        },
        "mentor_advice": "Master the box model first. Everything in CSS flows from understanding padding, margin, and border.",
    },
    "the_code_keeper": {
        "id": "the_code_keeper", "name": "The Code Keeper", "icon": "⚡",
        "greetings": {
            "first": "Sparks fly where logic meets creativity. I guard the Junction — prove your worth.",
            "return": "The energy here responds to knowledge. You feel stronger this time.",
            "advanced": "The current bends to your will now. The Junction recognizes you.",
        },
        "farewells": {
            "normal": "May your functions always return and your variables always be defined.",
            "perfect": "The lightning itself applauds. Rare indeed.",
            "struggling": "Even the Keeper was once a student. Push through!",
        },
        "mentor_advice": "Learn to read error messages — they tell you exactly what's wrong. Don't ignore the stack trace.",
    },
    "the_dom_warden": {
        "id": "the_dom_warden", "name": "The DOM Warden", "icon": "🌊",
        "greetings": {
            "first": "The Delta flows with nodes and events. I watch over every ripple. Step carefully.",
            "return": "The waters remember your touch, Walker. Dive back in.",
            "advanced": "You navigate the currents like a native. The Delta trusts you.",
        },
        "farewells": {
            "normal": "Every event bubbles. Every node connects. Remember the flow.",
            "perfect": "You've mastered the currents themselves. Astonishing.",
            "struggling": "The Delta is deep, but patience reveals its patterns.",
        },
        "mentor_advice": "Understand event delegation — attach one listener to a parent instead of many to children.",
    },
    "the_chrono_sage": {
        "id": "the_chrono_sage", "name": "The Chrono Sage", "icon": "🔮",
        "greetings": {
            "first": "Time bends here. Promises yet unfulfilled, callbacks from ages past. I am the Sage of Asynchrony.",
            "return": "The timelines shift as you return, Walker. You carry different temporal weight now.",
            "advanced": "You see through the veil of time itself. Few reach this understanding.",
        },
        "farewells": {
            "normal": "Await with patience. Resolve with purpose.",
            "perfect": "You've bent time to your will. The Sage bows in respect.",
            "struggling": "Async is the hardest concept. Even I struggled once. Persist.",
        },
        "mentor_advice": "Always handle errors in async code. Uncaught promise rejections will bite you later.",
    },
}

# ─── Sound Effects (terminal beeps) ─────────────────────────────────

def play_sound(sound_type: str, enabled: bool = True):
    """Play terminal sound effects using ASCII bell character."""
    if not enabled:
        return
    try:
        if sound_type == "correct":
            # Pleasant double beep
            console.print("\a", end="")
            time.sleep(0.1)
            console.print("\a", end="")
        elif sound_type == "wrong":
            # Single low beep
            console.print("\a", end="")
        elif sound_type == "achievement":
            # Triple celebratory beep
            for _ in range(3):
                console.print("\a", end="")
                time.sleep(0.1)
        elif sound_type == "level_up":
            # Rising beeps
            console.print("\a", end="")
            time.sleep(0.15)
            console.print("\a", end="")
            time.sleep(0.15)
            console.print("\a", end="")
            time.sleep(0.15)
            console.print("\a", end="")
        elif sound_type == "boss":
            # Ominous slow beep
            console.print("\a", end="")
            time.sleep(0.3)
            console.print("\a", end="")
    except Exception:
        pass  # Some terminals don't support bell


# ─── Helper Functions ────────────────────────────────────────────────


def get_rank(xp: int) -> Tuple[str, int, int]:
    """Get (rank_title, current_threshold, next_threshold)."""
    current_t = 0
    next_t = VERSE_RANKS[-1][0]
    rank_title = VERSE_RANKS[-1][1]
    for i, (threshold, title) in enumerate(VERSE_RANKS):
        if xp >= threshold:
            current_t = threshold
            rank_title = title
            if i + 1 < len(VERSE_RANKS):
                next_t = VERSE_RANKS[i + 1][0]
            else:
                next_t = threshold
    return rank_title, current_t, next_t


def get_prestige(prestige_level: int) -> Tuple[str, str]:
    """Get (prestige_title, prestige_icon)."""
    title = ""
    icon = "🌟"
    for threshold, t, ic in PRESTIGE_RANKS:
        if prestige_level >= threshold:
            title, icon = t, ic
    return title, icon


def get_mastery(xp: int) -> Tuple[str, str]:
    """Get (mastery_title, icon) from XP."""
    title, icon = MASTERY_TIERS[0][1], MASTERY_TIERS[0][2]
    for threshold, t, ic in MASTERY_TIERS:
        if xp >= threshold:
            title, icon = t, ic
    return title, icon


def xp_bar(current: int, next_threshold: int, prev_threshold: int = 0, width: int = 25) -> str:
    if next_threshold == prev_threshold:
        pct = 1.0
    else:
        pct = min((current - prev_threshold) / (next_threshold - prev_threshold), 1.0)
    filled = int(pct * width)
    empty = width - filled
    return f"[cyan]{'█' * filled}[/{'cyan'}][dim]{'░' * empty}[/dim] {current}/{next_threshold}"


def encode_challenge(data: str) -> str:
    return hashlib.md5(data.encode()).hexdigest()[:12].upper()


def decode_difficulty_config(diff: str) -> Dict:
    return DIFFICULTY_MODIFIERS.get(diff, DIFFICULTY_MODIFIERS["normal"])


# ─── Verse Engine ────────────────────────────────────────────────────


class VerseEngine:
    """Core engine for the KSL-Verse interactive learning game — v2.0 with all features."""

    def __init__(self, multiplayer=False, session_id=None, firebase=None):
        self.config = load_config()
        self.verse_progress = self.config.get("verse_progress", {})
        self.total_xp = self.verse_progress.get("total_xp", 0)
        self.worlds_data = {}
        self.session_streak = 0
        self.session_xp = 0
        self.sound_enabled = self.verse_progress.get("sound_enabled", True)
        
        # Multiplayer support
        self.multiplayer = multiplayer
        self.session_id = session_id
        self.firebase = firebase
        
        self._sync_state()

    # ─── Content Loading ─────────────────────────────────────────────

    def discover_worlds(self) -> List[Dict]:
        worlds = []
        if not KSL_DIR.exists():
            return worlds
        for json_file in sorted(KSL_DIR.glob("*_verse.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                verse = data.get("verse", data)
                if verse and "id" in verse:
                    worlds.append(verse)
                    self.worlds_data[verse["id"]] = verse
            except (json.JSONDecodeError, IOError):
                pass
        return worlds

    # ─── State Management ────────────────────────────────────────────

    def _save_progress(self):
        self.config = load_config()
        self.config["verse_progress"] = self.verse_progress
        save_config(self.config)

    def _sync_state(self):
        self.total_xp = self.verse_progress.get("total_xp", 0)
        self.combo_multiplier = self.verse_progress.get("combo_multiplier", 1.0)
        self.combo_count = self.verse_progress.get("combo_count", 0)
        self.difficulty = self.verse_progress.get("difficulty", "normal")
        self.compact_mode = self.verse_progress.get("compact_mode", False)
        self.lifelines = self.verse_progress.get("lifelines", {"fifty_fifty": 3, "skip": 2, "hint": 3})
        self.inventory = self.verse_progress.get("inventory", [])
        self.weaknesses = self.verse_progress.get("weaknesses", {})
        self.lore_unlocked = self.verse_progress.get("lore_unlocked", [])
        self.speedrun_records = self.verse_progress.get("speedrun_records", {})
        self.daily_challenge = self.verse_progress.get("daily_challenge", None)
        self.npc_memory = self.verse_progress.get("npc_memory", {})
        self.journal = self.verse_progress.get("journal", {})
        self.session_stats = self.verse_progress.get("session_stats", {"total_sessions": 0, "total_time": 0, "total_correct": 0, "total_wrong": 0, "history": []})
        self.streak_calendar = self.verse_progress.get("streak_calendar", {})
        self.prestige_level = self.verse_progress.get("prestige_level", 0)
        self.prestige_bonus = self.verse_progress.get("prestige_bonus", 0)
        self.custom_questions = self.verse_progress.get("custom_questions", [])
        self.mentor_active = self.verse_progress.get("mentor_active", False)
        self.world_themes = self.verse_progress.get("world_themes", {})
        self.quote_index = self.verse_progress.get("quote_index", 0)
        self.animate_narrative = self.verse_progress.get("animate_narrative", False)
        self.sound_enabled = self.verse_progress.get("sound_enabled", True)

    def _get_world_progress(self, world_id: str) -> Dict:
        wp = self.verse_progress.get("worlds", {}).get(world_id, {})
        return {
            "completed_levels": wp.get("completed_levels", []),
            "best_level_scores": wp.get("best_level_scores", {}),
            "boss_defeated": wp.get("boss_defeated", False),
            "world_completed": wp.get("world_completed", False),
            "mini_bosses": wp.get("mini_bosses", []),
            "mastery": wp.get("mastery", {}),
            "boss_phase_records": wp.get("boss_phase_records", {}),
        }

    def _set_world_progress(self, world_id: str, progress: Dict):
        if "worlds" not in self.verse_progress:
            self.verse_progress["worlds"] = {}
        self.verse_progress["worlds"][world_id] = progress
        self._save_progress()

    # ─── Core Systems ────────────────────────────────────────────────

    def _add_xp(self, amount: int) -> int:
        diff_mod = decode_difficulty_config(self.difficulty)
        mult = diff_mod.get("xp_mult", 1.0) * self.combo_multiplier
        prestige_mult = 1.0 + (self.prestige_bonus * 0.1)
        final_xp = int(amount * mult * prestige_mult)
        self.total_xp += final_xp
        self.session_xp += final_xp
        self.verse_progress["total_xp"] = self.total_xp
        return final_xp

    def _update_combo(self, correct: bool):
        if correct:
            self.combo_count += 1
            self.combo_multiplier = min(1.0 + (self.combo_count // 5) * 0.25, 3.0)
        else:
            self.combo_count = 0
            self.combo_multiplier = 1.0
        self.verse_progress["combo_multiplier"] = self.combo_multiplier
        self.verse_progress["combo_count"] = self.combo_count

    def _track_weakness(self, topic: str, concept: str):
        key = f"{topic}:{concept}"
        if key not in self.weaknesses:
            self.weaknesses[key] = {"count": 0, "last_wrong": None, "review_date": None}
        self.weaknesses[key]["count"] += 1
        self.weaknesses[key]["last_wrong"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.weaknesses[key]["review_date"] = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        self.verse_progress["weaknesses"] = self.weaknesses

    def _track_streak_day(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.streak_calendar[today] = True
        self.verse_progress["streak_calendar"] = self.streak_calendar

    def _record_session(self, correct: int, wrong: int, elapsed: float, level_name: str):
        self.session_stats["total_sessions"] += 1
        self.session_stats["total_time"] += elapsed
        self.session_stats["total_correct"] += correct
        self.session_stats["total_wrong"] += wrong
        self.session_stats["history"].append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "level": level_name,
            "correct": correct,
            "wrong": wrong,
            "time": round(elapsed, 1),
            "accuracy": round((correct / max(correct + wrong, 1)) * 100, 0),
        })
        # Keep last 100 sessions
        if len(self.session_stats["history"]) > 100:
            self.session_stats["history"] = self.session_stats["history"][-100:]
        self.verse_progress["session_stats"] = self.session_stats

    def _award_item(self, item_id: str):
        if item_id in ITEMS_DB:
            self.inventory.append({"id": item_id, "acquired": datetime.now().strftime("%Y-%m-%d %H:%M")})
            self.verse_progress["inventory"] = self.inventory

    def _use_item(self, item_id: str) -> bool:
        for i, inv_item in enumerate(self.inventory):
            if inv_item["id"] == item_id:
                self.inventory.pop(i)
                self.verse_progress["inventory"] = self.inventory
                self._save_progress()
                return True
        return False

    def _unlock_lore(self, lore_id: str, title: str, content: str):
        if lore_id not in self.lore_unlocked:
            self.lore_unlocked.append(lore_id)
            self.verse_progress["lore_unlocked"] = self.lore_unlocked
            self._save_progress()
            return True
        return False

    def _show_quote(self):
        """Show a random inspirational quote."""
        idx = self.quote_index % len(QUOTES)
        quote, author = QUOTES[idx]
        self.quote_index = (idx + 1) % len(QUOTES)
        self.verse_progress["quote_index"] = self.quote_index
        console.print()
        console.print(f"  [dim italic]{quote}[/dim italic]")
        console.print(f"  [dim]{author}[/dim]")
        console.print()

    def _save_journal_entry(self, world_id: str, level_id: str, entry: str):
        key = f"{world_id}:{level_id}"
        if key not in self.journal:
            self.journal[key] = []
        self.journal[key].append({
            "text": entry,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        self.verse_progress["journal"] = self.journal
        self._save_progress()

    def _calc_player_level(self) -> int:
        level = 1
        for i, (threshold, _) in enumerate(VERSE_RANKS):
            if self.total_xp >= threshold:
                level = i + 1
        return level

    # ─── Lifelines ───────────────────────────────────────────────────

    def _use_lifeline(self, lifeline: str, options: List[Dict]) -> Tuple[List[Dict], Optional[str]]:
        if lifeline == "fifty_fifty" and self.lifelines.get("fifty_fifty", 0) > 0:
            self.lifelines["fifty_fifty"] -= 1
            self.verse_progress["lifelines"] = self.lifelines
            wrong = [o for o in options if not o.get("correct", False)]
            to_remove = random.sample(wrong, min(2, len(wrong)))
            remaining = [o for o in options if o not in to_remove]
            return remaining, f"[yellow]50/50 used! {self.lifelines['fifty_fifty']} remaining[/yellow]"
        elif lifeline == "skip" and self.lifelines.get("skip", 0) > 0:
            self.lifelines["skip"] -= 1
            self.verse_progress["lifelines"] = self.lifelines
            return [], "SKIPPED"
        elif lifeline == "hint" and self.lifelines.get("hint", 0) > 0:
            self.lifelines["hint"] -= 1
            self.verse_progress["lifelines"] = self.lifelines
            correct_opt = next((o for o in options if o.get("correct")), None)
            hint_text = f"[yellow]💡 Hint: Eliminate the obviously wrong options... {self.lifelines['hint']} hints left.[/yellow]"
            return options, hint_text
        return options, None

    # ─── Random Events ───────────────────────────────────────────────

    def _check_random_event(self) -> Optional[str]:
        """Randomly trigger an event between levels (15% chance)."""
        if random.random() > 0.15:
            return None

        events = [
            ("🌟 XP Storm!", "You caught an XP storm! +25 bonus XP!", lambda: self._add_xp(25)),
            ("🧙 Wandering Merchant", "A merchant offers a free item!", lambda: self._award_item(random.choice(list(ITEMS_DB.keys())))),
            ("⚡ NPC Challenge", "A rival Walker challenges you!", lambda: self._random_npc_challenge()),
            ("🍀 Lucky Break", "Your next answer gets double XP!", lambda: self.verse_progress.__setitem__("lucky_break", True)),
            ("📖 Wisdom Scroll", "You found a hidden scroll! +10 XP!", lambda: self._add_xp(10)),
        ]
        event = random.choice(events)
        try:
            event[2]()
        except Exception:
            return None
        return f"  [bold magenta]{event[0]}[/bold magagenta]\n  {event[1]}"

    def _random_npc_challenge(self):
        """Quick 2-question NPC challenge for bonus XP."""
        questions = [
            {"q": "What does HTML stand for?", "a": "HyperText Markup Language", "opts": ["HyperText Markup Language", "High Tech Modern Language", "Home Tool Markup Language", "Hyper Transfer Markup Language"]},
            {"q": "CSS stands for?", "a": "Cascading Style Sheets", "opts": ["Cascading Style Sheets", "Creative Style System", "Computer Style Sheets", "Colorful Style Sheets"]},
            {"q": "Which language runs in the browser?", "a": "JavaScript", "opts": ["JavaScript", "Python", "Java", "C++"]},
            {"q": "What does DOM stand for?", "a": "Document Object Model", "opts": ["Document Object Model", "Digital Ordinance Model", "Document Orientation Method", "Data Object Mapping"]},
        ]
        q = random.choice(questions)
        console.print(f"\n  ⚡ [bold]Quick Challenge![/bold] Answer for 15 bonus XP!")
        console.print(f"  [white]{q['q']}[/white]")
        for i, opt in enumerate(q["opts"], 1):
            console.print(f"  [{i}] {opt}")
        try:
            ans = console.input("\n  [bold green]Choose (1-4):[/bold green] ").strip()
            if ans == "1" or q["a"] in q["opts"][int(ans)-1:int(ans)]:
                # Simplified check
                pass
            self._add_xp(15)
        except (ValueError, IndexError):
            pass

    # ─── Main Menu ───────────────────────────────────────────────────

    def show_verse_menu(self):
        worlds = self.discover_worlds()
        self._sync_state()

        while True:
            rank_title, _, next_xp = get_rank(self.total_xp)
            console.clear()
            console.print()
            prestige_title, prestige_icon = get_prestige(self.prestige_level)
            prestige_display = f" {prestige_icon} {prestige_title}" if prestige_title else ""
            show_panel(f"🌌  K S L - V E R S E{prestige_display}", "The Multiverse Learning Adventure", "magenta")
            console.print()

            player_level = self._calc_player_level()
            console.print(f"  [bold white]Level {player_level}[/bold white] — [cyan]{rank_title}[/cyan]  |  [yellow]{self.total_xp} XP[/yellow]  |  [magenta]{self.combo_multiplier:.1f}x combo[/magenta]")
            console.print(f"  {xp_bar(self.total_xp, next_xp)}")
            console.print()

            diff_info = decode_difficulty_config(self.difficulty)
            mode_tags = [f"{diff_info['icon']} {diff_info['label']}"]
            if self.compact_mode:
                mode_tags.append("[dim]📋 Compact[/dim]")
            if self.prestige_level > 0:
                mode_tags.append(f"{prestige_icon}P{self.prestige_level}")
            if self.inventory:
                mode_tags.append(f"🎒{len(self.inventory)}")
            console.print(f"  [dim]{'  '.join(mode_tags)}[/dim]")
            console.print()

            if not worlds:
                show_info("No worlds discovered yet!")
                console.input("\n[bold green]╰─► Press Enter to return...[/bold green]")
                return

            console.print("  [bold]Available Worlds:[/bold]\n")
            for i, world in enumerate(worlds, 1):
                wid = world["id"]
                icon = world.get("icon", "🌍")
                title = world.get("title", "Unknown World")
                diff = world.get("difficulty", "unknown")
                level_req = world.get("player_level_required", 1)
                wp = self._get_world_progress(wid)
                player_level = self._calc_player_level()

                if wp.get("world_completed"):
                    status = "[green]✅ Mastered[/green]"
                elif player_level < level_req:
                    status = f"[dim]🔒 Requires Level {level_req}[/dim]"
                else:
                    completed = len(wp.get("completed_levels", []))
                    total_levels = len(world.get("levels", []))
                    boss = " 🏆" if wp.get("boss_defeated") else ""
                    status = f"[cyan]{completed}/{total_levels}{boss}[/cyan]"

                diff_icon = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(diff, "⚪")
                console.print(f"  [yellow]{i:02d}[/yellow] {icon} [white]{title}[/white] {diff_icon}")
                console.print(f"       {status}")
                console.print()

            # Main menu options
            console.print(f"  [yellow] 1[/yellow]-[yellow]{len(worlds)}[/yellow] [white]Enter World[/white]")
            console.print(f"  [yellow] M[/yellow] [white]🗺️  World Map[/white]")
            console.print(f"  [yellow] D[/yellow] [white]📅 Daily Challenge[/white]")
            console.print(f"  [yellow] R[/yellow] [white]⏱️  Speedrun Mode[/white]")
            console.print(f"  [yellow] W[/yellow] [white]📊 Weakness Review[/white]")
            console.print(f"  [yellow] L[/yellow] [white]📜 Lore Codex[/white]")
            console.print(f"  [yellow] I[/yellow] [white]🎒 Inventory[/white]")
            console.print(f"  [yellow] T[/yellow] [white]🌳 Skill Tree[/white]")
            console.print(f"  [yellow] J[/yellow] [white]📓 Journal[/white]")
            console.print(f"  [yellow] G[/yellow] [white]📖 Glossary[/white]")
            console.print(f"  [yellow] N[/yellow] [white]🧙 Mentor Advice[/white]")
            console.print(f"  [yellow] A[/yellow] [white]🏆 Achievement Showcase[/white]")
            console.print(f"  [yellow] E[/yellow] [white]📈 Deep Stats[/white]")
            console.print(f"  [yellow] C[/yellow] [white]📅 Streak Calendar[/white]")
            console.print()
            console.print(f"  [bold magenta]─── Game Modes ───[/bold magenta]")
            console.print(f"  [yellow] B[/yellow] [white]⚔️  Boss Rush Mode[/white]")
            console.print(f"  [yellow] U[/yellow] [white]♾️  Endless Mode[/white]")
            console.print(f"  [yellow] V[/yellow] [white]💀 Survival Mode[/white]")
            console.print(f"  [yellow] Z[/yellow] [white]🎲 Randomizer Mode[/white]")
            console.print()
            console.print(f"  [bold magenta]─── Tools ───[/bold magenta]")
            console.print(f"  [yellow] P[/yellow] [white]⚙️  Settings[/white]")
            console.print(f"  [yellow] S[/yellow] [white]📊 Player Stats[/white]")
            console.print(f"  [yellow] K[/yellow] [white]🃏 Profile Card[/white]")
            console.print(f"  [yellow] Q[/yellow] [white]✏️  Custom Questions[/white]")
            console.print(f"  [yellow] O[/yellow] [white]📊 Report Card[/white]")
            console.print(f"  [yellow] X[/yellow] [white]🔄 Prestige[/white]")
            console.print(f"  [yellow] F[/yellow] [white]🛠️  World Builder[/white]")
            console.print(f"  [yellow] H[/yellow] [white]✏️  Auto-Generate World[/white]")
            console.print(f"  [yellow] Y[/yellow] [white]📤 Export Progress[/white]")
            console.print(f"  [yellow] IM[/yellow] [white]📥 Import Progress[/white]")
            console.print(f"  [yellow] SH[/yellow] [white]📤 Share Code[/white]")
            console.print(f"  [yellow] AC[/yellow] [white]♿ Accessibility[/white]")
            console.print()
            console.print(f"  [yellow] 0[/yellow] [white]Back to Main Menu[/white]")
            console.print()

            try:
                choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
                if choice == "0": return
                elif choice == "M": self._show_world_map()
                elif choice == "D": self._run_daily_challenge()
                elif choice == "R": self._run_speedrun_menu(worlds)
                elif choice == "W": self._run_weakness_review()
                elif choice == "L": self._show_lore_codex()
                elif choice == "I": self._show_inventory()
                elif choice == "T": self._show_skill_tree(worlds)
                elif choice == "J": self._show_journal()
                elif choice == "G": self._show_glossary()
                elif choice == "N": self._show_mentor_advice()
                elif choice == "A": self._show_achievement_showcase()
                elif choice == "E": self._show_deep_stats()
                elif choice == "C": self._show_streak_calendar()
                elif choice == "B": self._run_boss_rush(worlds)
                elif choice == "U": self._run_endless_mode(worlds)
                elif choice == "V": self._run_survival_mode(worlds)
                elif choice == "Z": self._run_randomizer_mode(worlds)
                elif choice == "P": self._show_settings_menu()
                elif choice == "S": self._show_player_stats()
                elif choice == "K": self._export_profile_card()
                elif choice == "Q": self._manage_custom_questions()
                elif choice == "O": self._generate_report_card(worlds)
                elif choice == "X": self._show_prestige_menu()
                elif choice == "F": self._run_world_builder()
                elif choice == "H": self._auto_generate_world()
                elif choice == "Y": self._export_progress()
                elif choice == "IM": self._import_progress()
                elif choice == "SH": self._generate_share_code()
                elif choice == "AC": self._accessibility_menu()
                else:
                    try:
                        idx = int(choice)
                        if 1 <= idx <= len(worlds):
                            self._enter_world(worlds[idx - 1])
                        else:
                            show_warning("Invalid selection!")
                            time.sleep(1)
                    except ValueError:
                        show_warning("Invalid input!")
                        time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Returning...[/yellow]")
                time.sleep(1)
                return

    # ─── World Navigation ────────────────────────────────────────────

    def _enter_world(self, world: Dict):
        world_id = world["id"]
        world_title = world.get("title", world_id)
        world_desc = world.get("description", "")
        levels = world.get("levels", [])
        wp = self._get_world_progress(world_id)
        completed_levels = wp.get("completed_levels", [])
        boss_defeated = wp.get("boss_defeated", False)

        # Random event check
        event_msg = self._check_random_event()
        if event_msg:
            console.clear()
            console.print()
            console.print(event_msg)
            time.sleep(2)

        while True:
            console.clear()
            console.print()
            ascii_art = WORLD_ASCII.get(world_id, DEFAULT_ASCII)
            console.print(f"[magenta]{ascii_art}[/magenta]")
            console.print()
            console.print(f"  [dim]{world_desc}[/dim]")
            console.print()

            self._show_npc_greeting(world_id, levels, completed_levels)

            console.print("  [bold]Level Map:[/bold]\n")
            for i, level in enumerate(levels):
                lid = level.get("id", f"level_{i + 1}")
                licon = level.get("icon", "📍")
                ltitle = level.get("title", f"Level {i + 1}")
                is_completed = lid in completed_levels
                mastery_info = wp.get("mastery", {}).get(lid, {})
                mastery_title, mastery_icon = get_mastery(mastery_info.get("xp", 0))

                if is_completed:
                    status = f"[green]✅ Cleared[/green] {mastery_icon} {mastery_title}"
                elif i == 0 or levels[i - 1].get("id", f"level_{i}") in completed_levels:
                    status = "[yellow]🔓 Unlocked[/yellow]"
                else:
                    status = "[dim]🔒 Locked[/dim]"

                has_mini = level.get("mini_boss")
                mini_tag = " ⚡" if has_mini and lid not in wp.get("mini_bosses", []) else ""
                console.print(f"  [{i + 1}] {licon} [white]{ltitle}[/white] — {status}{mini_tag}")
                console.print()

            if boss_defeated:
                console.print(f"  [yellow] B[/yellow] 🏆 [green]Boss Defeated — Replay[/green]")
            else:
                all_cleared = len(completed_levels) == len(levels) and levels
                if all_cleared:
                    console.print(f"  [yellow] B[/yellow] 🏆 [bold red]⚔️  Boss Battle![/bold red]")
                else:
                    console.print(f"  [yellow] B[/yellow] 🏆 [dim]Boss Locked[/dim]")
            console.print()

            console.print(f"  [yellow] 1[/yellow]-[yellow]{len(levels)}[/yellow] [white]Enter Level[/white]")
            console.print(f"  [yellow] P[/yellow] [white]🏃 Practice Mode (all levels, no penalty)[/white]")
            if boss_defeated or (len(completed_levels) == len(levels) and levels):
                console.print(f"  [yellow] M[/yellow] [white]🏃 Marathon Mode (full world run)[/white]")
            console.print(f"  [yellow] L[/yellow] [white]📜 Lore[/white]")
            console.print(f"  [yellow] J[/yellow] [white]📓 Write Journal Entry[/white]")
            console.print(f"  [yellow] 0[/yellow] [white]Back[/white]")
            console.print()

            try:
                choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
                if choice == "0": return
                elif choice == "B":
                    all_cleared = len(completed_levels) == len(levels) and levels
                    if all_cleared or boss_defeated:
                        self._run_boss_battle(world, levels[-1])
                    else:
                        show_warning("Clear all levels first!")
                        time.sleep(2)
                elif choice == "P":
                    self._run_practice_mode(world, levels)
                elif choice == "M":
                    if len(completed_levels) == len(levels) and levels:
                        self._run_marathon_mode(world, levels)
                    else:
                        show_warning("Complete all levels first for Marathon Mode!")
                        time.sleep(2)
                elif choice == "L":
                    self._show_world_lore(world)
                elif choice == "J":
                    self._write_journal_entry(world_id, None)
                else:
                    try:
                        idx = int(choice)
                        if 1 <= idx <= len(levels):
                            level = levels[idx - 1]
                            lid = level.get("id", f"level_{idx}")
                            if idx > 1:
                                prev_lid = levels[idx - 2].get("id", f"level_{idx - 1}")
                                if prev_lid not in completed_levels and lid not in completed_levels:
                                    show_warning("Complete previous level first!")
                                    time.sleep(2)
                                    continue
                            self._run_level(world, level, wp)
                        else:
                            show_warning("Invalid selection!")
                            time.sleep(1)
                    except ValueError:
                        show_warning("Invalid input!")
                        time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Returning...[/yellow]")
                time.sleep(1)
                return

    # ─── NPC System ──────────────────────────────────────────────────

    def _show_npc_greeting(self, world_id: str, levels: List, completed: List):
        world_npc_map = {"webdev_cosmos": ["the_builder", "the_stylist", "the_code_keeper", "the_dom_warden", "the_chrono_sage"]}
        npc_list = world_npc_map.get(world_id, [])
        if not npc_list: return

        npc_index = min(len(completed), len(npc_list) - 1)
        npc_key = npc_list[npc_index]
        npc = NPCS_DB.get(npc_key)
        if not npc: return

        mem = self.npc_memory.get(npc_key, {})
        visits = mem.get("visits", 0) + 1
        self.npc_memory[npc_key] = {"visits": visits, "last_visit": datetime.now().strftime("%Y-%m-%d")}
        self.verse_progress["npc_memory"] = self.npc_memory

        if visits == 1: greeting = npc["greetings"]["first"]
        elif len(completed) == len(levels): greeting = npc["greetings"]["advanced"]
        else: greeting = npc["greetings"].get("return", npc["greetings"]["first"])

        console.print(f"  {npc['icon']} [bold cyan]{npc['name']}[/bold cyan]:")
        console.print(f"  [dim italic]\"{greeting}\"[/dim italic]")
        console.print()
        self._save_progress()

    def _show_npc_farewell(self, world_id: str, accuracy: float):
        world_npc_map = {"webdev_cosmos": ["the_builder", "the_stylist", "the_code_keeper", "the_dom_warden", "the_chrono_sage"]}
        npc_list = world_npc_map.get(world_id, [])
        if not npc_list: return

        wp = self._get_world_progress(world_id)
        npc_index = min(len(wp.get("completed_levels", [])), len(npc_list) - 1)
        npc_key = npc_list[npc_index]
        npc = NPCS_DB.get(npc_key)
        if not npc: return

        if accuracy >= 95: farewell = npc["farewells"]["perfect"]
        elif accuracy >= 60: farewell = npc["farewells"]["normal"]
        else: farewell = npc["farewells"]["struggling"]

        console.print(f"\n  {npc['icon']} [bold cyan]{npc['name']}[/bold cyan]:")
        console.print(f"  [dim italic]\"{farewell}\"[/dim italic]")

    # ─── Level Gameplay ──────────────────────────────────────────────

    def _run_level(self, world: Dict, level: Dict, wp: Dict, is_practice: bool = False) -> Dict:
        world_title = world.get("title", "Unknown World")
        level_title = level.get("title", "Unknown Level")
        level_icon = level.get("icon", "📍")
        level_id = level.get("id", "unknown")
        scenarios = level.get("scenarios", [])
        xp_per_scenario = level.get("xp_reward_per_scenario", 25)

        if not scenarios:
            show_info("This level has no scenarios!")
            time.sleep(2)
            return {}

        self.session_streak = 0
        self.session_xp = 0
        correct_count = 0
        total_attempts = 0
        first_try_correct = 0
        wrong_count = 0
        start_time = time.time()

        if not self.compact_mode:
            console.clear()
            console.print()
            show_panel(f"{level_icon}  {level_title}", f"in {world_title}", "cyan")
            console.print()
            story_intro = level.get("story_intro", "")
            if story_intro:
                console.print(f"  [italic]{story_intro}[/italic]")
                console.print()
            diff_mod = decode_difficulty_config(self.difficulty)
            mode_label = "Practice Mode" if is_practice else f"{diff_mod['icon']} {diff_mod['label']}"
            console.print(f"  [dim]{mode_label} | {len(scenarios)} scenarios | {xp_per_scenario} XP each[/dim]")
            console.print()
            if not is_practice:
                console.input("[bold green]╰─► Press Enter to begin...[/bold green]")

        mini_boss = level.get("mini_boss")
        mini_boss_midpoint = len(scenarios) // 2 if mini_boss else 999

        for i, scenario in enumerate(scenarios, 1):
            # Mini-boss
            if i == mini_boss_midpoint + 1 and mini_boss:
                self._run_mini_boss(world, level, mini_boss, wp)

            # Show quote between scenarios occasionally
            if i > 1 and i % 3 == 0 and not is_practice:
                self._show_quote()

            console.clear()
            console.print()
            console.print(f"  [dim]Scenario {i}/{len(scenarios)}[/dim]  [yellow]🔥 {self.session_streak}[/yellow]  [magenta]{self.combo_multiplier:.1f}x[/magenta]")
            print_divider()
            console.print()

            # Secret discovery
            if scenario.get("is_secret") and scenario.get("id") not in self.verse_progress.get("secrets_found", []):
                self._discover_secret(scenario, world_title, level_title)

            # Custom questions injection
            custom_qs = [q for q in self.custom_questions if q.get("level_id") == level_id and q.get("used", False) is False]
            if custom_qs and random.random() < 0.3:
                cq = random.choice(custom_qs)
                self._run_custom_question(cq, level_title, xp_per_scenario)

            narrative = scenario.get("narrative", "")
            if narrative and not self.compact_mode:
                console.print(f"  [italic]{narrative}[/italic]")
                console.print()

            question = scenario.get("question", "")
            q_type = scenario.get("type", "multiple_choice")
            console.print(f"  [bold white][{QUESTION_TYPES.get(q_type, 'Multiple Choice')}] {question}[/bold white]")
            console.print()

            code_block = scenario.get("code", "")
            if code_block:
                console.print(f"  [bold yellow]Code:[/bold yellow]")
                for line in code_block.strip().split("\n"):
                    console.print(f"  [yellow]{line}[/yellow]")
                console.print()

            options = list(scenario.get("options", []))
            if q_type == "true_false" and not options:
                is_true = scenario.get("answer", True)
                options = [{"letter": "A", "text": "True", "correct": is_true}, {"letter": "B", "text": "False", "correct": not is_true}]

            for opt in options:
                letter = opt.get("letter", "").upper()
                text = opt.get("text", "")
                if letter:
                    console.print(f"  [green][{letter}][/green] [white]{text}[/white]")
            console.print()

            if not is_practice:
                lifeline_info = []
                if self.lifelines.get("fifty_fifty", 0) > 0:
                    lifeline_info.append(f"[yellow]50[/yellow] ({self.lifelines['fifty_fifty']})")
                if self.lifelines.get("skip", 0) > 0:
                    lifeline_info.append(f"[yellow]S[/yellow] ({self.lifelines['skip']})")
                if self.lifelines.get("hint", 0) > 0:
                    lifeline_info.append(f"[yellow]H[/yellow] ({self.lifelines['hint']})")
                if lifeline_info:
                    console.print(f"  [dim]Lifelines: {' | '.join(lifeline_info)}[/dim]")
                    console.print()

            correct = False
            attempts_on_this = 0
            while not correct:
                try:
                    if is_practice:
                        answer = console.input("[bold green]╰─► Choose (A-D, Q):[/bold green] ").strip().upper()
                    else:
                        answer = console.input("[bold green]╰─► Choose (A-D, 50, S, H, Q):[/bold green] ").strip().upper()

                    if answer == "Q":
                        console.print("\n[yellow]Level paused.[/yellow]")
                        time.sleep(1)
                        return {"quit": True}

                    # Lifelines (not in practice mode)
                    if not is_practice and answer in ("50", "S", "H"):
                        if answer == "50" and self.lifelines.get("fifty_fifty", 0) > 0:
                            options, msg = self._use_lifeline("fifty_fifty", options)
                            if msg: console.print(f"\n  {msg}")
                            if options:
                                console.print()
                                for opt in options:
                                    console.print(f"  [green][{opt['letter']}][/green] [white]{opt['text']}[/white]")
                                console.print()
                            continue
                        elif answer == "S" and self.lifelines.get("skip", 0) > 0:
                            _, _ = self._use_lifeline("skip", options)
                            console.print("\n  [yellow]Scenario skipped![/yellow]")
                            correct = True
                            continue
                        elif answer == "H" and self.lifelines.get("hint", 0) > 0:
                            _, msg = self._use_lifeline("hint", options)
                            if msg: console.print(f"\n  {msg}")
                            continue
                        else:
                            show_warning("No uses remaining!")
                            continue

                    valid_letters = [o.get("letter", "").upper() for o in options]
                    if answer not in valid_letters:
                        show_warning("Invalid choice!")
                        continue

                    attempts_on_this += 1
                    total_attempts += 1
                    chosen = next((o for o in options if o.get("letter", "").upper() == answer), None)
                    if not chosen: continue

                    is_correct = chosen.get("correct", False)

                    if is_correct:
                        correct = True
                        correct_count += 1
                        self.session_streak += 1
                        if attempts_on_this == 1: first_try_correct += 1

                        play_sound("correct", self.sound_enabled)

                        xp_gain = xp_per_scenario
                        if self.session_streak >= 3:
                            xp_gain += (self.session_streak - 2) * 5
                            xp_msg = f"+{xp_gain} XP (streak! 🔥)"
                        else:
                            xp_msg = f"+{xp_gain} XP"

                        if is_practice:
                            console.print(f"\n[bold green]✅ Correct![/bold green]")
                        else:
                            actual_xp = self._add_xp(xp_gain)
                            self._update_combo(True)
                            console.print(f"\n[bold green]✅ Correct! +{actual_xp} XP[/bold green]")

                        explanation = scenario.get("explanation_correct", "Well done!")
                        if not self.compact_mode:
                            console.print(f"\n  📖 {explanation}")
                        related = scenario.get("related_concepts", [])
                        if related and not self.compact_mode:
                            console.print(f"\n  [dim]🔗 Related: {', '.join(related)}[/dim]")

                        # Item drop (10%)
                        if not is_practice and random.random() < 0.10:
                            drop = random.choice(list(ITEMS_DB.keys()))
                            self._award_item(drop)
                            item_info = ITEMS_DB[drop]
                            console.print(f"\n  🎁 Item: {item_info['icon']} {item_info['name']}!")

                    else:
                        wrong_count += 1
                        self._update_combo(False)
                        play_sound("wrong", self.sound_enabled)

                        if is_practice:
                            explanation = scenario.get("explanation_wrong", "Review and try again!")
                            console.print(f"\n[bold red]❌ Not Quite![/bold red]")
                            console.print(f"\n  📖 {explanation}")
                            # In practice mode, show correct answer and move on
                            correct_opt = next((o for o in options if o.get("correct")), None)
                            if correct_opt:
                                console.print(f"\n  [green]Correct answer: {correct_opt['text']}[/green]")
                            correct = True  # Move on in practice mode
                        else:
                            explanation = scenario.get("explanation_wrong", "Try again!")
                            console.print(f"\n[bold red]❌ Not Quite![/bold red]")
                            if not self.compact_mode:
                                console.print(f"\n  📖 {explanation}")
                            console.print(f"\n  [yellow]🔁 Try again![/yellow]")

                            topic = level_title
                            concept = scenario.get("concept", scenario.get("id", ""))
                            self._track_weakness(topic, concept)

                            # Ironman mode — one wrong = game over
                            diff_cfg = decode_difficulty_config(self.difficulty)
                            if diff_cfg.get("ironman"):
                                console.print(f"\n  [bold red]💀 IRONMAN: One wrong answer ends the run![/bold red]")
                                elapsed = time.time() - start_time
                                self._record_session(correct_count, wrong_count, elapsed, level_title)
                                time.sleep(2)
                                return {"ironman_failed": True}

                            # Shield charm
                            if self.verse_progress.get("shield_active", False):
                                self._use_item("shield_charm")
                                self.verse_progress["shield_active"] = False
                                console.print(f"\n  🛡️ Shield Charm absorbed the penalty!")

                            time.sleep(2)
                            if not self.compact_mode and not is_practice:
                                console.clear()
                                console.print()
                                console.print(f"  [dim]Scenario {i}/{len(scenarios)} — Retrying[/dim]")
                                console.print()
                                if narrative:
                                    console.print(f"  [italic]{narrative}[/italic]")
                                    console.print()
                                console.print(f"  [bold white]{question}[/bold white]")
                                console.print()
                                for opt in options:
                                    console.print(f"  [green][{opt['letter']}][/green] [white]{opt['text']}[/white]")
                                console.print()

                except (ValueError, KeyboardInterrupt):
                    console.print("\n[yellow]Level paused.[/yellow]")
                    time.sleep(1)
                    return {"quit": True}

        elapsed = time.time() - start_time
        accuracy = (correct_count / max(total_attempts, 1)) * 100

        # Bonuses (not in practice mode)
        if not is_practice:
            if accuracy == 100 and total_attempts == len(scenarios):
                bonus = self._add_xp(50)
                show_panel("🏆 Perfect Level!", f"+{bonus} XP bonus", "green")
                play_sound("achievement", self.sound_enabled)

            # Speedrun record
            if elapsed < self.speedrun_records.get(f"{world['id']}_{level_id}", float("inf")):
                self.speedrun_records[f"{world['id']}_{level_id}"] = round(elapsed, 1)
                self.verse_progress["speedrun_records"] = self.speedrun_records
                console.print(f"  [bold yellow]⏱️  New Record: {elapsed:.1f}s![/bold yellow]")

            # Save progress
            if "completed_levels" not in wp:
                wp["completed_levels"] = []
            if level_id not in wp["completed_levels"]:
                wp["completed_levels"].append(level_id)

            if "mastery" not in wp:
                wp["mastery"] = {}
            if level_id not in wp["mastery"]:
                wp["mastery"][level_id] = {"xp": 0, "attempts": 0, "best_accuracy": 0}
            wp["mastery"][level_id]["xp"] += self.session_xp
            wp["mastery"][level_id]["attempts"] += 1
            wp["mastery"][level_id]["best_accuracy"] = max(wp["mastery"][level_id]["best_accuracy"], accuracy)

            self._set_world_progress(world["id"], wp)
            self._record_session(correct_count, wrong_count, elapsed, level_title)
            self._track_streak_day()

            self._show_npc_farewell(world["id"], accuracy)

            console.print(f"\n  [bold]Stats:[/bold] {correct_count}/{len(scenarios)} | {accuracy:.0f}% | {elapsed:.1f}s")
            console.print()
            console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

        return {"completed": True, "xp": self.session_xp, "accuracy": accuracy, "time": elapsed}

    # ─── Mini-Boss ───────────────────────────────────────────────────

    def _run_mini_boss(self, world: Dict, level: Dict, mini_boss: Dict, wp: Dict):
        level_id = level.get("id", "unknown")
        if level_id in wp.get("mini_bosses", []): return

        boss_name = mini_boss.get("name", "Mini-Boss")
        questions = mini_boss.get("questions", [])
        xp_reward = mini_boss.get("xp_reward", 75)

        console.clear()
        console.print()
        show_panel(f"⚡  MINI-BOSS: {boss_name}", "A mid-level challenge!", "yellow")
        console.print()
        console.print(f"  [dim]{len(questions)} questions | {xp_reward} XP[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

        correct = 0
        for i, q in enumerate(questions, 1):
            console.clear()
            console.print()
            console.print(f"  [bold yellow]⚡ {boss_name}[/bold yellow] — Q{i}/{len(questions)}")
            console.print()
            console.print(f"  [bold white]{q.get('question', q.get('q', ''))}[/bold white]")
            console.print()
            options = q.get("options", [])
            for opt in options:
                letter = opt.get("letter", "").upper()
                text = opt.get("text", "")
                if letter:
                    console.print(f"  [green][{letter}][/green] [white]{text}[/white]")
            console.print()

            try:
                answer = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
                chosen = next((o for o in options if o.get("letter", "").upper() == answer), None)
                if chosen and chosen.get("correct", False):
                    correct += 1
                    console.print(f"\n[bold green]✅ Correct![/bold green]")
                else:
                    console.print(f"\n[bold red]❌ Resisted![/bold red]")
                    if chosen:
                        exp = chosen.get("explanation", q.get("explanation", ""))
                        if exp: console.print(f"  📖 {exp}")
                time.sleep(1)
            except KeyboardInterrupt: return

        passed = correct >= len(questions) * 0.6
        if passed:
            xp = self._add_xp(xp_reward)
            if "mini_bosses" not in wp: wp["mini_bosses"] = []
            wp["mini_bosses"].append(level_id)
            self._set_world_progress(world["id"], wp)
            play_sound("achievement", self.sound_enabled)
            show_panel(f"⚡ {boss_name} Defeated!", f"{correct}/{len(questions)} | +{xp} XP", "green")
        else:
            show_panel(f"💪 Mini-Boss Survived", f"{correct}/{len(questions)} — Need 60%")
        console.input("\n[bold green]╰─► Press Enter...[/bold green]")

    # ─── Boss Battles (with Phases + Evolution) ──────────────────────

    def _run_boss_battle(self, world: Dict, last_level: Dict) -> Dict:
        world_id = world["id"]
        wp = self._get_world_progress(world_id)
        boss_defeated = wp.get("boss_defeated", False)

        boss = last_level.get("boss", {})
        if not boss:
            for level in reversed(world.get("levels", [])):
                if level.get("boss"): boss = level["boss"]; break
        if not boss:
            show_info("No boss available!"); time.sleep(2); return {}

        boss_name = boss.get("name", boss.get("id", "Boss"))
        boss_narrative = boss.get("narrative", "")
        questions = list(boss.get("questions", []))
        xp_reward = boss.get("xp_reward", 150)

        if not questions:
            show_info("Boss has no questions!"); time.sleep(2); return {}

        # Boss Evolution — adapt questions based on player weaknesses
        evolved = self._evolve_boss_questions(world_id, questions)

        console.clear()
        console.print()
        console.print(f"[red]{BOSS_ASCII}[/red]")
        console.print()

        play_sound("boss", self.sound_enabled)

        if boss_defeated:
            show_panel(f"🏆  Replay: {boss_name}", f"Re-challenge", "yellow")
        else:
            show_panel(f"⚔️  BOSS: {boss_name}", f"Final challenge of {world.get('title', '')}", "red")
        console.print()
        if boss_narrative and not self.compact_mode:
            console.print(f"  [italic red]{boss_narrative}[/italic red]")
            console.print()
        total_q = len(evolved)
        console.print(f"  [dim]{total_q} questions | {xp_reward} XP | Need 60%+ | 2 Phases[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

        correct = 0
        total = total_q
        phase1_end = total // 2
        phase_triggered = False

        for i, q in enumerate(evolved, 1):
            # Phase 2 trigger at 50%
            if i == phase1_end + 1 and not phase_triggered and not boss_defeated:
                phase_triggered = True
                # Check if player is struggling
                if correct < phase1_end * 0.6:
                    console.clear()
                    console.print()
                    console.print(f"[bold red]{BOSS_PHASE2_ASCII}[/bold red]")
                    console.print()
                    console.print(f"  [bold red]The Boss enters Phase 2 — questions get harder![/bold red]")
                    console.print(f"  [dim]Phase 1: {correct}/{phase1_end} correct[/dim]")
                    console.print()
                    console.input("[bold green]╰─► Press Enter to face Phase 2...[/bold green]")
                else:
                    console.print(f"\n  [bold green]Phase 1 Complete: {correct}/{phase1_end} — Boss weakens![/bold green]")
                    time.sleep(1.5)

            console.clear()
            console.print()
            hp_pct = ((total - correct) / total) * 100
            hp_bar_len = int(hp_pct / 4)
            phase_label = " 🔥P2" if phase_triggered else ""
            hp_bar = f"[{'red' if phase_triggered else 'yellow'}]{'█' * hp_bar_len}[/{'red' if phase_triggered else 'yellow'}][dim]{'░' * (25 - hp_bar_len)}[/dim]"
            console.print(f"  [bold]Boss HP{phase_label}:[/bold] {hp_bar} {hp_pct:.0f}%")
            console.print(f"  [dim]Q{i}/{total}[/dim]")
            console.print()

            q_text = q.get("question", q.get("q", ""))
            code = q.get("code", "")
            if code:
                console.print(f"  [bold yellow]Code:[/bold yellow]")
                for line in code.strip().split("\n"):
                    console.print(f"  [yellow]{line}[/yellow]")
                console.print()
            console.print(f"  [bold white]{q_text}[/bold white]")
            console.print()

            options = q.get("options", [])
            for opt in options:
                letter = opt.get("letter", "").upper()
                text = opt.get("text", "")
                if letter:
                    console.print(f"  [green][{letter}][/green] [white]{text}[/white]")
            console.print()

            try:
                answer = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
                chosen = next((o for o in options if o.get("letter", "").upper() == answer), None)
                if chosen:
                    if chosen.get("correct", False):
                        correct += 1
                        console.print(f"\n[bold green]✅ Boss takes damage![/bold green]")
                    else:
                        console.print(f"\n[bold red]❌ Boss resists![/bold red]")
                        explanation = chosen.get("explanation", q.get("explanation", ""))
                        if explanation: console.print(f"  📖 {explanation}")
                else:
                    console.print("\n[yellow]Invalid — Boss gets free hit![/yellow]")
                time.sleep(1.5)
            except KeyboardInterrupt:
                console.print("\n[yellow]Boss battle fled![/yellow]")
                time.sleep(1)
                return {"quit": True}

        boss_accuracy = (correct / total) * 100 if total > 0 else 0
        passed = boss_accuracy >= 60

        console.clear()
        console.print()
        if passed:
            xp_earned = int((correct / total) * xp_reward)
            actual_xp = self._add_xp(xp_earned)
            show_panel("🏆 BOSS DEFEATED!", f"{correct}/{total} | +{actual_xp} XP", "green")
            wp["boss_defeated"] = True
            wp["world_completed"] = True
            self._set_world_progress(world_id, wp)
            play_sound("achievement", self.sound_enabled)

            worlds_completed = sum(1 for w in self.verse_progress.get("worlds", {}).values() if w.get("world_completed"))
            if worlds_completed == 1:
                bonus = self._add_xp(100)
                console.print(f"\n[bold magenta]🌟 First World Complete! +{bonus} XP![/bold magenta]")

            self._show_epilogue(world, correct, total)
        else:
            show_panel("💀 Boss Victory...", f"{correct}/{total} — Need 60%!")
            console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")
        return {"completed": passed, "correct": correct, "total": total}

    def _evolve_boss_questions(self, world_id: str, questions: List[Dict]) -> List[Dict]:
        """Adapt boss questions based on player weaknesses."""
        if not self.weaknesses:
            return questions

        # Find weakest concepts
        weak_concepts = sorted(self.weaknesses.items(), key=lambda x: x[1]["count"], reverse=True)[:3]
        weak_keys = [k for k, _ in weak_concepts]

        # Add extra questions about weak areas if available
        evolved = list(questions)
        # For now, just shuffle to keep it varied
        random.shuffle(evolved)
        return evolved

    # ─── Epilogue ────────────────────────────────────────────────────

    def _show_epilogue(self, world: Dict, correct: int, total: int):
        world_title = world.get("title", "Unknown World")
        epilogue = world.get("epilogue", "")

        console.clear()
        console.print()
        console.print("  ╔══════════════════════════════════╗")
        console.print("  ║  🎉  WORLD CONQUERED!  🎉       ║")
        console.print("  ╚══════════════════════════════════╝")
        console.print()
        if epilogue and not self.compact_mode:
            console.print(f"  [italic cyan]{epilogue}[/italic cyan]")
            console.print()

        wp = self._get_world_progress(world["id"])
        levels_completed = len(wp.get("completed_levels", []))
        total_levels = len(world.get("levels", []))
        console.print(f"  [bold]{world_title} — Complete![/bold]")
        console.print(f"  Levels: {levels_completed}/{total_levels} | Boss: {correct}/{total}")
        console.print()

        worlds = self.discover_worlds()
        current_idx = next((i for i, w in enumerate(worlds) if w["id"] == world["id"]), -1)
        if current_idx >= 0 and current_idx + 1 < len(worlds):
            next_world = worlds[current_idx + 1]
            console.print(f"  [dim]Next:[/dim] [bold magenta]{next_world.get('icon', '🌍')} {next_world.get('title', 'Unknown')}[/bold magenta]")
        console.print()

    # ─── Practice Mode ───────────────────────────────────────────────

    def _run_practice_mode(self, world: Dict, levels: List):
        """Practice any level with no penalties."""
        console.clear()
        console.print()
        show_panel("🏃  Practice Mode", "No penalties, no XP — just learning!", "green")
        console.print()

        for i, level in enumerate(levels, 1):
            lid = level.get("id", f"level_{i}")
            licon = level.get("icon", "📍")
            ltitle = level.get("title", f"Level {i + 1}")
            console.print(f"  [yellow]{i}[/yellow] {licon} [white]{ltitle}[/white]")
        console.print()
        console.print(f"  [yellow] 0[/yellow] [white]Back[/white]")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip()
            if choice == "0": return
            idx = int(choice)
            if 1 <= idx <= len(levels):
                wp = self._get_world_progress(world["id"])
                self._run_level(world, levels[idx - 1], wp, is_practice=True)
        except (ValueError, IndexError):
            show_warning("Invalid selection!")
            time.sleep(1)

    # ─── Marathon Mode ───────────────────────────────────────────────

    def _run_marathon_mode(self, world: Dict, levels: List):
        """Complete all levels back-to-back with no breaks."""
        console.clear()
        console.print()
        show_panel("🏃  Marathon Mode", f"All {len(levels)} levels in one run — {world.get('title', '')}", "yellow")
        console.print()
        console.print("  [dim]No breaks between levels. All answers count. XP multiplier: x3[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter to start the marathon...[/bold green]")

        total_correct = 0
        total_wrong = 0
        start_time = time.time()

        old_diff = self.difficulty
        self.difficulty = "marathon"
        self.verse_progress["difficulty"] = "marathon"

        for i, level in enumerate(levels, 1):
            console.print(f"\n  [bold]🏃 Marathon — Level {i}/{len(levels)}[/bold]")
            time.sleep(1)
            wp = self._get_world_progress(world["id"])
            result = self._run_level(world, level, wp)
            if result.get("quit"):
                break
            total_correct += 1  # Simplified
            console.print(f"  [dim]Press Enter for next level...[/dim]")
            if i < len(levels):
                console.input()

        elapsed = time.time() - start_time
        self.difficulty = old_diff
        self.verse_progress["difficulty"] = old_diff
        self._save_progress()

        console.clear()
        console.print()
        show_panel("🏁 Marathon Complete!", f"All levels finished in {elapsed:.0f}s!", "green")
        console.input("\n[bold green]╰─► Press Enter...[/bold green]")

    # ─── Daily Challenge ─────────────────────────────────────────────

    def _generate_daily_challenge(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.daily_challenge and self.daily_challenge.get("date") == today:
            return self.daily_challenge

        worlds = self.discover_worlds()
        if not worlds: return None

        all_scenarios = []
        for world in worlds:
            for level in world.get("levels", []):
                for scenario in level.get("scenarios", []):
                    all_scenarios.append({"world_id": world["id"], "world_title": world.get("title", ""), "level_title": level.get("title", ""), "scenario": scenario})

        if not all_scenarios: return None

        seed_val = int(hashlib.md5(today.encode()).hexdigest(), 16)
        random.seed(seed_val)
        selected = random.sample(all_scenarios, min(3, len(all_scenarios)))
        random.seed()

        challenge = {"date": today, "scenarios": selected, "completed": False, "score": 0, "best_score": self.verse_progress.get("daily_challenge_best", 0)}
        self.daily_challenge = challenge
        self.verse_progress["daily_challenge"] = challenge
        self._save_progress()
        return challenge

    def _run_daily_challenge(self):
        challenge = self._generate_daily_challenge()
        if not challenge:
            show_info("No daily challenge available!"); time.sleep(2); return

        console.clear()
        console.print()
        show_panel("📅  Daily Challenge", f"Date: {challenge['date']}", "magenta")
        console.print()

        if challenge.get("completed"):
            console.print(f"  [green]✅ Completed today![/green]  [dim]Best: {challenge.get('best_score', 0)}/{len(challenge['scenarios'])}[/dim]")
            console.print()
            console.input("[bold green]╰─► Press Enter...[/bold green]")
            return

        console.print(f"  [dim]3 scenarios — prove your versatility![/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter to begin...[/bold green]")

        correct = 0
        for i, item in enumerate(challenge["scenarios"], 1):
            scenario = item["scenario"]
            console.clear()
            console.print()
            console.print(f"  [dim]Daily Challenge {i}/3[/dim]  —  [cyan]{item['world_title']}[/cyan]")
            console.print()

            narrative = scenario.get("narrative", "")
            if narrative:
                console.print(f"  [italic]{narrative}[/italic]")
                console.print()

            question = scenario.get("question", "")
            console.print(f"  [bold white]{question}[/bold white]")
            console.print()

            options = scenario.get("options", [])
            answer_map = {}
            for opt in options:
                letter = opt.get("letter", "").upper()
                text = opt.get("text", "")
                if letter:
                    answer_map[letter] = opt
                    console.print(f"  [green][{letter}][/green] [white]{text}[/white]")
            console.print()

            try:
                answer = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
                chosen = answer_map.get(answer)
                if chosen and chosen.get("correct", False):
                    correct += 1
                    console.print(f"\n[bold green]✅ Correct! +30 XP[/bold green]")
                    self._add_xp(30)
                    play_sound("correct", self.sound_enabled)
                else:
                    console.print(f"\n[bold red]❌ Incorrect![/bold red]")
                    play_sound("wrong", self.sound_enabled)
                    if chosen:
                        exp = chosen.get("explanation", scenario.get("explanation_wrong", ""))
                        if exp: console.print(f"  📖 {exp}")
                time.sleep(1.5)
            except KeyboardInterrupt: return

        challenge["completed"] = True
        challenge["score"] = correct
        if correct > challenge.get("best_score", 0):
            challenge["best_score"] = correct
            self.verse_progress["daily_challenge_best"] = correct
        self.verse_progress["daily_challenge"] = challenge
        self._save_progress()

        console.clear()
        console.print()
        if correct == 3:
            show_panel("🌟 Perfect Daily!", f"3/3 | +90 XP", "green")
            play_sound("achievement", self.sound_enabled)
        elif correct >= 2:
            show_panel("✅ Daily Passed", f"{correct}/3 | +{correct * 30} XP")
        else:
            show_panel("📅 Daily Failed", f"{correct}/3. Try again tomorrow!")
        console.input("\n[bold green]╰─► Press Enter...[/bold green]")

    # ─── Speedrun ────────────────────────────────────────────────────

    def _run_speedrun_menu(self, worlds: List[Dict]):
        console.clear()
        console.print()
        show_panel("⏱️  Speedrun Records", "Your best times", "yellow")
        console.print()

        if not self.speedrun_records:
            show_info("No records yet!"); console.print()
            console.input("[bold green]╰─► Press Enter...[/bold green]")
            return

        sorted_recs = sorted(self.speedrun_records.items(), key=lambda x: x[1])
        for record_key, time_val in sorted_recs:
            level_title = record_key.replace("_", " ").title()
            for w in worlds:
                for lvl in w.get("levels", []):
                    if lvl.get("id") == record_key:
                        level_title = lvl.get("title", record_key)
                        break
            console.print(f"  ⏱️  [white]{level_title}[/white] — [yellow]{time_val}s[/yellow]")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── Weakness Review ─────────────────────────────────────────────

    def _run_weakness_review(self):
        if not self.weaknesses:
            show_info("No weaknesses tracked!"); time.sleep(2); return

        due_today = self._check_spaced_review_due()
        console.clear()
        console.print()
        show_panel("📊  Weakness Review", f"{len(self.weaknesses)} tracked topics", "cyan")
        console.print()

        if due_today:
            console.print(f"  [bold yellow]📅 Due today ({len(due_today)}):[/bold yellow]\n")
            for key in due_today:
                data = self.weaknesses[key]
                console.print(f"  ⚠️  [white]{key}[/white] [dim](wrong {data['count']}x)[/dim]")
            console.print()

        console.print("  [bold]All Weaknesses:[/bold]\n")
        sorted_weak = sorted(self.weaknesses.items(), key=lambda x: x[1]["count"], reverse=True)
        for key, data in sorted_weak[:10]:
            review_status = "📅 DUE" if key in due_today else "⏳"
            console.print(f"  {review_status} [white]{key}[/white] [dim]({data['count']}x | {data.get('last_wrong', 'N/A')})[/dim]")
        console.print()
        console.print("  [dim]💡 Revisit relevant levels to strengthen your understanding.[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    def _check_spaced_review_due(self) -> List[str]:
        today = datetime.now().strftime("%Y-%m-%d")
        return [k for k, v in self.weaknesses.items() if v.get("review_date") == today]

    # ─── Lore Codex ──────────────────────────────────────────────────

    def _show_lore_codex(self):
        if not self.lore_unlocked:
            show_info("No lore discovered yet!"); time.sleep(2); return

        console.clear()
        console.print()
        show_panel("📜  Lore Codex", f"{len(self.lore_unlocked)} entries", "magenta")
        console.print()

        for lore_id in self.lore_unlocked:
            found = False
            for world in self.worlds_data.values():
                lore_data = world.get("lore", {}).get(lore_id, {})
                if lore_data:
                    console.print(f"  [bold]{lore_data.get('icon', '📜')} {lore_data.get('title', lore_id)}[/bold]")
                    console.print(f"  [dim]{lore_data.get('content', '')}[/dim]")
                    console.print()
                    found = True; break
            if not found:
                console.print(f"  [dim]{lore_id}[/dim]\n")

        console.input("[bold green]╰─► Press Enter...[/bold green]")

    def _show_world_lore(self, world: Dict):
        lore = world.get("lore", {})
        if not lore:
            show_info("No lore for this world!"); time.sleep(2); return

        console.clear()
        console.print()
        show_panel(f"📜  {world.get('title', '')} Lore", f"{len(lore)} entries", "magenta")
        console.print()

        for lore_id, entry in lore.items():
            if lore_id in self.lore_unlocked:
                console.print(f"  [bold]{entry.get('icon', '📜')} {entry.get('title', lore_id)}[/bold]")
                console.print(f"  [dim]{entry.get('content', '')}[/dim]")
            else:
                console.print(f"  [dim]🔒 ??? (Undiscovered)[/dim]")
            console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    def _discover_secret(self, scenario: Dict, world_title: str, level_title: str):
        secret_id = scenario.get("id", "unknown")
        if "secrets_found" not in self.verse_progress:
            self.verse_progress["secrets_found"] = []
        self.verse_progress["secrets_found"].append(secret_id)
        self._save_progress()

        bonus = self._add_xp(50)
        lore_id = scenario.get("secret_lore_id", f"secret_{secret_id}")
        lore_title = scenario.get("secret_lore_title", f"Secret of {level_title}")
        lore_content = scenario.get("secret_lore_content", "A hidden truth discovered.")
        self._unlock_lore(lore_id, lore_title, lore_content)

        console.print()
        console.print(f"  [bold magenta]🌟 SECRET DISCOVERED![/bold magenta]")
        console.print(f"  +{bonus} XP | 📜 Lore unlocked!")
        play_sound("achievement", self.sound_enabled)
        console.print()
        time.sleep(3)

    # ─── Inventory ───────────────────────────────────────────────────

    def _show_inventory(self):
        if not self.inventory:
            show_info("Inventory empty!"); time.sleep(2); return

        console.clear()
        console.print()
        show_panel("🎒  Inventory", f"{len(self.inventory)} items", "cyan")
        console.print()

        item_counts = defaultdict(int)
        for inv_item in self.inventory:
            item_counts[inv_item["id"]] += 1

        for item_id, count in item_counts.items():
            item_info = ITEMS_DB.get(item_id, {})
            icon = item_info.get("icon", "📦")
            name = item_info.get("name", item_id)
            desc = item_info.get("desc", "")
            console.print(f"  {icon} [white]{name}[/white] x{count}")
            console.print(f"     [dim]{desc}[/dim]")
            console.print()

        console.print("  [yellow]U[/yellow] Use item  [yellow]0[/yellow] Back")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
            if choice == "U": self._use_item_menu()
        except (ValueError, KeyboardInterrupt): pass

    def _use_item_menu(self):
        if not self.inventory:
            show_info("No items!"); time.sleep(1); return

        console.clear()
        console.print()
        show_panel("🎒  Use Item", "Select item", "cyan")
        console.print()

        for i, inv_item in enumerate(self.inventory, 1):
            item_id = inv_item["id"]
            item_info = ITEMS_DB.get(item_id, {})
            icon = item_info.get("icon", "📦")
            name = item_info.get("name", item_id)
            effect = item_info.get("effect", "")
            console.print(f"  [yellow]{i}[/yellow] {icon} [white]{name}[/white] [dim]({effect})[/dim]")
        console.print()
        console.print("  [yellow]0[/yellow] Back")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip()
            if choice == "0": return
            idx = int(choice)
            if 1 <= idx <= len(self.inventory):
                inv_item = self.inventory[idx - 1]
                item_id = inv_item["id"]
                item_info = ITEMS_DB.get(item_id, {})
                effect = item_info.get("effect", "")

                if effect == "instant_xp":
                    xp = item_info.get("value", 50)
                    self._add_xp(xp)
                    self._use_item(item_id)
                    show_success(f"🧪 XP Potion used! +{xp} XP")
                elif effect == "show_weakness":
                    self._use_item(item_id)
                    self._run_weakness_review()
                    return
                elif effect == "xp_boost":
                    self.verse_progress["xp_boost_active"] = True
                    self._use_item(item_id)
                    show_success("🔥 Streak Crystal activated!")
                elif effect == "shield":
                    self.verse_progress["shield_active"] = True
                    self._use_item(item_id)
                    show_success("🛡️ Shield Charm activated!")
                elif effect == "hint":
                    self.lifelines["hint"] = self.lifelines.get("hint", 0) + item_info.get("value", 1)
                    self._use_item(item_id)
                    self.verse_progress["lifelines"] = self.lifelines
                    show_success(f"💡 +{item_info.get('value', 1)} hints!")
                else:
                    show_info(f"{item_info.get('name', 'Item')} — no use action.")
                time.sleep(2)
        except (ValueError, IndexError):
            show_warning("Invalid!")
            time.sleep(1)

    # ─── Skill Tree ──────────────────────────────────────────────────

    def _show_skill_tree(self, worlds: List[Dict]):
        console.clear()
        console.print()
        show_panel("🌳  Skill Tree", "Your mastery across all worlds", "green")
        console.print()

        for world in worlds:
            wid = world["id"]
            wicon = world.get("icon", "🌍")
            wtitle = world.get("title", "Unknown")
            wp = self._get_world_progress(wid)
            levels = world.get("levels", [])

            console.print(f"  {wicon} [bold]{wtitle}[/bold]")
            console.print()

            if not levels:
                console.print(f"    [dim]No levels[/dim]\n"); continue

            for i, level in enumerate(levels):
                lid = level.get("id", f"level_{i + 1}")
                licon = level.get("icon", "📍")
                ltitle = level.get("title", f"Level {i + 1}")
                is_completed = lid in wp.get("completed_levels", [])
                mastery = wp.get("mastery", {}).get(lid, {})
                mastery_title, mastery_icon = get_mastery(mastery.get("xp", 0))

                prefix = "    ├── " if i < len(levels) - 1 else "    └── "
                continuation = "    │   " if i < len(levels) - 1 else "        "
                status = f"[green]{mastery_icon} {mastery_title}[/green]" if is_completed else "[dim]🔒 Locked[/dim]"
                console.print(f"{prefix}{licon} [white]{ltitle}[/white] — {status}")

                concepts = level.get("concepts", [])
                if concepts and is_completed:
                    for j, concept in enumerate(concepts):
                        sub_prefix = continuation + ("    ├── " if j < len(concepts) - 1 else "    └── ")
                        console.print(f"{sub_prefix}[dim]• {concept}[/dim]")
                elif not is_completed and i == 0:
                    console.print(f"{continuation}    [dim]— Complete to reveal skills —[/dim]")
                console.print()

        console.print("  [dim]💡 Complete levels to unlock skills.[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── Journal ─────────────────────────────────────────────────────

    def _show_journal(self):
        if not self.journal:
            show_info("No journal entries yet!"); time.sleep(2); return

        console.clear()
        console.print()
        show_panel("📓  Journal", f"{sum(len(v) for v in self.journal.values())} entries", "cyan")
        console.print()

        for key, entries in self.journal.items():
            console.print(f"  [bold]{key}[/bold]")
            for entry in entries:
                console.print(f"    [dim]{entry['date']}[/dim]")
                console.print(f"    {entry['text']}")
            console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    def _write_journal_entry(self, world_id: str, level_id: Optional[str]):
        console.clear()
        console.print()
        show_panel("📓  Write Journal Entry", "Record your thoughts", "cyan")
        console.print()

        try:
            entry = console.input("  [bold green]Your entry:[/bold green] ").strip()
            if entry:
                lid = level_id or "general"
                self._save_journal_entry(world_id, lid, entry)
                show_success("Journal entry saved!")
            else:
                show_info("Empty entry — not saved.")
            time.sleep(1.5)
        except KeyboardInterrupt: pass

    # ─── Glossary ────────────────────────────────────────────────────

    def _show_glossary(self):
        """Auto-built glossary from all encountered concepts."""
        glossary = {}
        for world in self.worlds_data.values():
            for level in world.get("levels", []):
                concepts = level.get("concepts", [])
                for scenario in level.get("scenarios", []):
                    concept = scenario.get("concept", "")
                    related = scenario.get("related_concepts", [])
                    for c in [concept] + related:
                        if c and c not in glossary:
                            glossary[c] = {"world": world.get("title", ""), "level": level.get("title", "")}

        if not glossary:
            show_info("No glossary entries yet! Explore worlds to build the glossary."); time.sleep(2); return

        console.clear()
        console.print()
        show_panel("📖  Concept Glossary", f"{len(glossary)} concepts", "green")
        console.print()

        for concept, info in sorted(glossary.items()):
            console.print(f"  [bold]{concept}[/bold]")
            console.print(f"    [dim]From: {info['world']} → {info['level']}[/dim]")
            console.print()

        console.print("  [dim]💡 Glossary is auto-built as you explore concepts in worlds.[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── Mentor System ───────────────────────────────────────────────

    def _get_course_mentor_advice(self):
        """Get advice from hierarchical course content based on current world."""
        if not self.current_world:
            return None

        world_id = self.current_world.get("id", "")
        source_course = self.current_world.get("source_course", "")

        # Map verse world IDs to course concepts for advice
        # Pull key_points from hierarchical course content
        from kslearn.loader import content_loader
        courses = content_loader.load_hierarchical_courses()

        # Find advice based on concepts in the current world
        world_concepts = self.current_world.get("concepts", [])
        all_key_points = []

        # courses is a list, iterate directly
        for course in courses:
            for cat in course.get("categories", []):
                for unit in cat.get("units", []):
                    for lo in unit.get("learning_outcomes", []):
                        for sub in lo.get("subtopics", []):
                            kp = sub.get("key_points", [])
                            if kp:
                                for point in kp:
                                    # Match course concepts to world concepts
                                    for wc in world_concepts:
                                        if any(word.lower() in point.lower() for word in wc.lower().split()):
                                            all_key_points.append(point)

        if all_key_points:
            import random
            return random.choice(all_key_points)

        return None

    def _show_mentor_advice(self):
        """Personalized advice based on player's weaknesses and current world context."""
        console.clear()
        console.print()
        show_panel("🧙  Mentor Advice", "Personalized guidance", "magenta")
        console.print()

        # Find most appropriate NPC based on weaknesses
        if self.weaknesses:
            weakest = max(self.weaknesses.items(), key=lambda x: x[1]["count"])
            console.print(f"  [bold red]⚠️  Your weakest area: {weakest[0]}[/bold red]")
            console.print(f"  [dim]Got it wrong {weakest[1]['count']} time(s)[/dim]")
            console.print()

        # Course-based advice from hierarchical content
        course_advice = self._get_course_mentor_advice()
        if course_advice:
            console.print("  [bold cyan]📚 Course Mentor advises:[/bold cyan]")
            console.print(f"  [dim italic]\"{course_advice}\"[/dim italic]")
            console.print()

        # NPC mentor advice (fallback for verse worlds with NPCs)
        world_id = self.current_world.get("id", "") if self.current_world else ""
        world_npcs = WORLD_NPCS.get(world_id, [])
        if world_npcs:
            for npc_key in world_npcs:
                npc = NPCS_DB.get(npc_key)
                if npc and npc.get("mentor_advice"):
                    console.print(f"  {npc['icon']} [bold cyan]{npc['name']}[/bold cyan] advises:")
                    console.print(f"  [dim italic]\"{npc['mentor_advice']}\"[/dim italic]")
                    console.print()

        # General advice based on stats
        if self.session_stats.get("total_sessions", 0) > 0:
            accuracy = (self.session_stats["total_correct"] / max(self.session_stats["total_correct"] + self.session_stats["total_wrong"], 1)) * 100
            if accuracy < 50:
                console.print("  [bold]📊 Mentor's Note:[/bold] Your overall accuracy is below 50%.")
                console.print("  [dim italic]\"Try Practice Mode to review concepts without pressure before attempting levels again.\"[/dim italic]")
            elif accuracy >= 80:
                console.print("  [bold]📊 Mentor's Note:[/bold] Excellent overall accuracy!")
                console.print("  [dim italic]\"You're ready for Hard Mode or even Ironman. Challenge yourself!\"[/dim italic]")
            console.print()

        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── World Map ───────────────────────────────────────────────────

    def _show_world_map(self):
        console.clear()
        console.print()
        show_panel("🗺️  World Map", "The Verse Galaxy", "magenta")
        console.print()
        console.print(f"[cyan]{WORLD_MAP_ASCII}[/cyan]")
        console.print()

        worlds = self.discover_worlds()
        console.print("  [bold]Worlds:[/bold]\n")
        for world in worlds:
            wid = world["id"]
            wp = self._get_world_progress(wid)
            icon = world.get("icon", "🌍")
            title = world.get("title", "Unknown")
            status = "[green]✅[/green]" if wp.get("world_completed") else "[yellow]🔓[/yellow]"
            console.print(f"  {icon} [white]{title}[/white] {status}")
        console.print()
        console.print("  [dim]💡 More worlds will appear here as content is added![/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── Achievement Showcase ────────────────────────────────────────

    def _show_achievement_showcase(self):
        from kslearn.engines.achievements import ACHIEVEMENTS

        earned_ids = set(a.get("id", "") for a in self.verse_progress.get("achievements", []))
        console.clear()
        console.print()
        show_panel("🏆  Achievement Showcase", "All achievements", "magenta")
        console.print()

        total = len(ACHIEVEMENTS)
        earned = len(earned_ids)
        console.print(f"  [bold]Progress: {earned}/{total} unlocked[/bold]\n")

        for ach_id, ach in ACHIEVEMENTS.items():
            is_earned = ach_id in earned_ids
            icon = ach.get("icon", "🏅")
            name = ach.get("name", "Unknown")
            desc = ach.get("description", "")
            rarity = ach.get("rarity", "common")
            rarity_color = {"common": "white", "uncommon": "green", "rare": "cyan", "legendary": "magenta"}.get(rarity, "white")

            if is_earned:
                console.print(f"  {icon} [bold {rarity_color}]{name}[/bold {rarity_color}] [dim]({rarity})[/dim]")
                console.print(f"     {desc}")
                console.print(f"     [green]✅ Unlocked[/green]")
            else:
                console.print(f"  [dim]{icon} [dim]{name}[/dim] [dim]({rarity})[/dim]")
                console.print(f"     [dim]{desc}[/dim]")
                console.print(f"     [dim]🔒 Not yet earned[/dim]")
            console.print()

        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── Deep Stats ──────────────────────────────────────────────────

    def _show_deep_stats(self):
        from rich.table import Table
        from rich import box

        console.clear()
        console.print()
        show_panel("📈  Deep Statistics", "Comprehensive analytics", "cyan")
        console.print()

        stats = self.session_stats
        total_sessions = stats.get("total_sessions", 0)
        total_time = stats.get("total_time", 0)
        total_correct = stats.get("total_correct", 0)
        total_wrong = stats.get("total_wrong", 0)
        total_answers = total_correct + total_wrong
        overall_accuracy = (total_correct / max(total_answers, 1)) * 100

        stats_table = Table(box=box.ROUNDED, border_style="cyan")
        stats_table.add_column("Metric", style="bold white", ratio=2)
        stats_table.add_column("Value", style="cyan", ratio=1, justify="right")

        stats_table.add_row("Total Sessions", str(total_sessions))
        stats_table.add_row("Total Time Playing", f"{total_time/60:.1f} min")
        stats_table.add_row("Total Questions Answered", str(total_answers))
        stats_table.add_row("Correct Answers", f"[green]{total_correct}[/green]")
        stats_table.add_row("Wrong Answers", f"[red]{total_wrong}[/red]")
        stats_table.add_row("Overall Accuracy", f"[{'green' if overall_accuracy >= 70 else 'yellow' if overall_accuracy >= 50 else 'red'}]{overall_accuracy:.1f}%[/]")
        stats_table.add_row("Avg Time per Session", f"{(total_time/max(total_sessions,1))/60:.1f} min")
        stats_table.add_row("Items Collected", str(len(self.inventory)))
        stats_table.add_row("Secrets Found", str(len(self.verse_progress.get("secrets_found", []))))
        stats_table.add_row("Lore Entries", str(len(self.lore_unlocked)))

        console.print(stats_table)
        console.print()

        # Accuracy trend (last 10 sessions)
        history = stats.get("history", [])[-10:]
        if history:
            console.print("  [bold]Recent Accuracy Trend:[/bold]\n")
            max_acc = max((h.get("accuracy", 0) for h in history), default=100)
            for h in history:
                acc = h.get("accuracy", 0)
                bar_len = int(acc / 3)
                color = "green" if acc >= 70 else "yellow" if acc >= 50 else "red"
                bar = f"[{color}]{'█' * bar_len}[/{color}][dim]{'░' * (33 - bar_len)}[/dim]"
                label = (h.get("level", "")[:20]).ljust(20)
                console.print(f"  {label} [{color}]{acc:5.0f}%[/color] {bar}")
            console.print()

        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── Streak Calendar ─────────────────────────────────────────────

    def _show_streak_calendar(self):
        console.clear()
        console.print()
        show_panel("📅  Streak Calendar", "Your study activity", "green")
        console.print()

        # Generate last 30 days
        today = datetime.now()
        console.print("  [bold]Last 30 Days:[/bold]\n")

        # Week headers
        week_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        console.print("       " + " ".join(f"[dim]{d}[/dim]" for d in week_labels))

        # Find start day (Monday of first week)
        start_date = today - timedelta(days=29)
        # Align to Monday
        days_since_monday = start_date.weekday()
        start_date -= timedelta(days=days_since_monday)

        for week in range(5):
            week_row = ""
            for day in range(7):
                current_date = start_date + timedelta(weeks=week, days=day)
                date_str = current_date.strftime("%Y-%m-%d")
                is_active = self.streak_calendar.get(date_str, False)
                is_future = current_date > today

                if is_future:
                    cell = "[dim]  [/dim]"
                elif is_active:
                    cell = "[bright_green]🟩[/bright_green] "
                else:
                    cell = "[dim]⬛[/dim] "
                week_row += cell

            console.print(f"  W{week+1} {week_row}")

        console.print("       🟩 Active  ⬛ Rest")
        console.print()

        # Streak count
        current_streak = 0
        for i in range(30, -1, -1):
            date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if self.streak_calendar.get(date_str, False):
                current_streak += 1
            else:
                if i < 30:
                    break

        console.print(f"  [bold]Current Streak:[/bold] [yellow]{current_streak} days[/yellow]")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── Settings Menu ───────────────────────────────────────────────

    def _show_settings_menu(self):
        while True:
            console.clear()
            console.print()
            show_panel("⚙️  Verse Settings", "Customize your experience", "cyan")
            console.print()

            diff_info = decode_difficulty_config(self.difficulty)
            console.print(f"  [1] Difficulty:  {diff_info['icon']} [bold]{diff_info['label']}[/bold] (XP x{diff_info['xp_mult']})")
            console.print(f"  [2] Compact Mode:  {'[green]ON[/green]' if self.compact_mode else '[dim]OFF[/dim]'}")
            console.print(f"  [3] Narrative Animation:  {'[green]ON[/green]' if self.verse_progress.get('animate_narrative', False) else '[dim]OFF[/dim]'}")
            console.print(f"  [4] Sound Effects:  {'[green]ON[/green]' if self.sound_enabled else '[dim]OFF[/dim]'}")
            console.print(f"  [5] Reset Lifelines  (50/50: {self.lifelines.get('fifty_fifty', 0)} | S: {self.lifelines.get('skip', 0)} | H: {self.lifelines.get('hint', 0)})")
            console.print(f"  [6] World Theme Colors")
            console.print(f"  [0] Back")
            console.print()

            try:
                choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip()
                if choice == "0": return
                elif choice == "1":
                    order = ["story", "normal", "hard", "ironman", "marathon"]
                    idx = order.index(self.difficulty) if self.difficulty in order else 1
                    self.difficulty = order[(idx + 1) % len(order)]
                    self.verse_progress["difficulty"] = self.difficulty
                    self._save_progress()
                elif choice == "2":
                    self.compact_mode = not self.compact_mode
                    self.verse_progress["compact_mode"] = self.compact_mode
                    self._save_progress()
                elif choice == "3":
                    self.verse_progress["animate_narrative"] = not self.verse_progress.get("animate_narrative", False)
                    self._save_progress()
                elif choice == "4":
                    self.sound_enabled = not self.sound_enabled
                    self.verse_progress["sound_enabled"] = self.sound_enabled
                    self._save_progress()
                    if self.sound_enabled: play_sound("correct", True)
                elif choice == "5":
                    self.lifelines = {"fifty_fifty": 3, "skip": 2, "hint": 3}
                    self.verse_progress["lifelines"] = self.lifelines
                    self._save_progress()
                    show_success("Lifelines reset!")
                    time.sleep(1)
                elif choice == "6":
                    self._manage_world_themes()
            except KeyboardInterrupt: return

    def _manage_world_themes(self):
        """Change color themes per world."""
        console.clear()
        console.print()
        show_panel("🎨  World Themes", "Choose colors per world", "magenta")
        console.print()

        themes = ["cyan", "green", "magenta", "yellow", "red", "blue", "white"]
        worlds = self.discover_worlds()

        for world in worlds:
            wid = world["id"]
            wicon = world.get("icon", "🌍")
            wtitle = world.get("title", "Unknown")
            current_theme = self.world_themes.get(wid, "cyan")
            console.print(f"  {wicon} [white]{wtitle}[/white] — [{current_theme}]{current_theme}[/{current_theme}]")
        console.print()
        console.print("  [dim]Themes: cyan, green, magenta, yellow, red, blue, white[/dim]")
        console.print("  [dim]Settings auto-save per session.[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter to go back...[/bold green]")

    # ─── Player Stats ────────────────────────────────────────────────

    def _show_player_stats(self):
        from rich.table import Table
        from rich import box

        rank_title, curr_t, next_xp = get_rank(self.total_xp)
        player_level = self._calc_player_level()
        prestige_title, prestige_icon = get_prestige(self.prestige_level)
        worlds = self.discover_worlds()
        total_levels = sum(len(w.get("levels", [])) for w in worlds)
        completed = sum(len(self._get_world_progress(w["id"]).get("completed_levels", [])) for w in worlds)
        bosses = sum(1 for w in worlds if self._get_world_progress(w["id"]).get("boss_defeated"))

        console.clear()
        console.print()
        prestige_display = f" {prestige_icon} {prestige_title}" if prestige_title else ""
        show_panel(f"📊  Player Statistics{prestige_display}", "Your Journey", "magenta")
        console.print()

        stats_table = Table(box=box.ROUNDED, border_style="magenta")
        stats_table.add_column("Stat", style="bold white", ratio=2)
        stats_table.add_column("Value", style="cyan", ratio=1, justify="right")

        stats_table.add_row("Player Level", str(player_level))
        stats_table.add_row("Rank Title", rank_title)
        if prestige_title:
            stats_table.add_row("Prestige", f"{prestige_icon} {prestige_title} (+{self.prestige_bonus * 10}% XP)")
        stats_table.add_row("Total XP", str(self.total_xp))
        stats_table.add_row("XP to Next", str(next_xp - self.total_xp))
        stats_table.add_row("Combo Multiplier", f"{self.combo_multiplier:.1f}x")
        stats_table.add_row("Difficulty", decode_difficulty_config(self.difficulty)["label"])
        stats_table.add_row("Worlds", f"{completed}/{total_levels} levels, {bosses} bosses")
        stats_table.add_row("Items", str(len(self.inventory)))
        stats_table.add_row("Lore", str(len(self.lore_unlocked)))
        stats_table.add_row("Secrets", str(len(self.verse_progress.get("secrets_found", []))))
        stats_table.add_row("Lifelines", f"50/50:{self.lifelines.get('fifty_fifty', 0)} S:{self.lifelines.get('skip', 0)} H:{self.lifelines.get('hint', 0)}")
        stats_table.add_row("Weaknesses", str(len(self.weaknesses)))
        stats_table.add_row("Custom Qs Added", str(len(self.custom_questions)))

        console.print(stats_table)
        console.print()
        console.print(f"  {xp_bar(self.total_xp, next_xp, curr_t)}")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── Profile Card ────────────────────────────────────────────────

    def _export_profile_card(self):
        rank_title, _, _ = get_rank(self.total_xp)
        player_level = self._calc_player_level()
        prestige_title, prestige_icon = get_prestige(self.prestige_level)
        worlds = self.discover_worlds()
        total_levels = sum(len(w.get("levels", [])) for w in worlds)
        completed = sum(len(self._get_world_progress(w["id"]).get("completed_levels", [])) for w in worlds)
        bosses = sum(1 for w in worlds if self._get_world_progress(w["id"]).get("boss_defeated"))

        prestige_line = ""
        if prestige_title:
            prestige_line = f"  Prestige: {prestige_title.ljust(15)}{prestige_icon}"

        card_lines = [
            "╔══════════════════════════════════════════════╗",
            "║          🌌 KSL-VERSE Profile Card           ║",
            "╠══════════════════════════════════════════════╣",
            f"║  Level: {str(player_level).ljust(6)} Rank: {rank_title.ljust(20)}║",
        ]
        if prestige_line:
            card_lines.append(f"║  {prestige_line.ljust(44)}║")
        card_lines.extend([
            f"║  XP: {str(self.total_xp).ljust(8)} Combo: {f'{self.combo_multiplier:.1f}x'.ljust(12)}      ║",
            "║                                              ║",
            f"║  Worlds: {str(len(worlds)).ljust(3)} Levels: {f'{completed}/{total_levels}'.ljust(8)} Bosses: {str(bosses).ljust(6)}       ║",
            f"║  Items: {str(len(self.inventory)).ljust(6)} Lore: {str(len(self.lore_unlocked)).ljust(6)} Secrets: {str(len(self.verse_progress.get('secrets_found', []))).ljust(6)}       ║",
            "╠══════════════════════════════════════════════╣",
            f"║  Generated: {datetime.now().strftime('%Y-%m-%d').ljust(28)}║",
            "╚══════════════════════════════════════════════╝",
        ])
        card = "\n".join(card_lines)

        console.clear()
        console.print()
        console.print(f"[bold cyan]{card}[/bold cyan]")
        console.print()
        console.print("  [dim]📋 Copy to share your progress![/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── Custom Questions ────────────────────────────────────────────

    def _manage_custom_questions(self):
        """Add and manage custom questions."""
        while True:
            console.clear()
            console.print()
            show_panel("✏️  Custom Questions", f"{len(self.custom_questions)} added", "cyan")
            console.print()

            if self.custom_questions:
                for i, q in enumerate(self.custom_questions, 1):
                    q_text = q.get("question", "")[:40]
                    level = q.get("level_id", "any")
                    used = "✅" if q.get("used", False) else "⏳"
                    console.print(f"  [yellow]{i}[/yellow] [{level}] {q_text}... {used}")
                console.print()

            console.print("  [yellow]1[/yellow] Add Question")
            console.print("  [yellow]2[/yellow] Toggle Used/Unused")
            console.print("  [yellow]3[/yellow] Delete Question")
            console.print("  [yellow]0[/yellow] Back")
            console.print()

            try:
                choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip()
                if choice == "0": return
                elif choice == "1":
                    self._add_custom_question()
                elif choice == "2" and self.custom_questions:
                    try:
                        idx = int(console.input("  Question #: ").strip())
                        if 1 <= idx <= len(self.custom_questions):
                            self.custom_questions[idx - 1]["used"] = not self.custom_questions[idx - 1].get("used", False)
                            self.verse_progress["custom_questions"] = self.custom_questions
                            self._save_progress()
                    except ValueError: pass
                elif choice == "3" and self.custom_questions:
                    try:
                        idx = int(console.input("  Delete #: ").strip())
                        if 1 <= idx <= len(self.custom_questions):
                            self.custom_questions.pop(idx - 1)
                            self.verse_progress["custom_questions"] = self.custom_questions
                            self._save_progress()
                    except ValueError: pass
            except KeyboardInterrupt: return

    def _add_custom_question(self):
        console.print()
        try:
            level_id = console.input("  Level ID (e.g., level_1): ").strip()
            question = console.input("  Question: ").strip()
            console.print("  Options (one per line, mark correct with *):")
            options = []
            letters = ["A", "B", "C", "D"]
            for i in range(4):
                opt_text = console.input(f"    {letters[i]}: ").strip()
                is_correct = opt_text.startswith("*")
                opt_text = opt_text.lstrip("*").strip()
                options.append({"letter": letters[i], "text": opt_text, "correct": is_correct})

            explanation = console.input("  Explanation: ").strip()

            self.custom_questions.append({
                "level_id": level_id,
                "question": question,
                "options": options,
                "explanation": explanation,
                "used": True,
                "added": datetime.now().strftime("%Y-%m-%d"),
            })
            self.verse_progress["custom_questions"] = self.custom_questions
            self._save_progress()
            show_success("Question added!")
            time.sleep(1)
        except KeyboardInterrupt: pass

    def _run_custom_question(self, cq: Dict, level_title: str, xp_base: int):
        """Run a custom question inline during a level."""
        console.print()
        console.print(f"  [bold magenta]✏️  Custom Question![/bold magenta]")
        console.print(f"  [bold white]{cq['question']}[/bold white]")
        console.print()
        for opt in cq.get("options", []):
            letter = opt.get("letter", "")
            text = opt.get("text", "")
            console.print(f"  [green][{letter}][/green] [white]{text}[/white]")
        console.print()

        try:
            answer = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
            chosen = next((o for o in cq.get("options", []) if o.get("letter", "").upper() == answer), None)
            if chosen and chosen.get("correct", False):
                xp = self._add_xp(xp_base)
                console.print(f"\n[bold green]✅ Correct! +{xp} XP[/bold green]")
                play_sound("correct", self.sound_enabled)
            else:
                console.print(f"\n[bold red]❌ Not quite![/bold red]")
                play_sound("wrong", self.sound_enabled)
                if chosen:
                    exp = cq.get("explanation", "")
                    if exp: console.print(f"  📖 {exp}")
            time.sleep(1.5)
        except (ValueError, KeyboardInterrupt): pass

    # ─── Prestige System ─────────────────────────────────────────────

    def _show_prestige_menu(self):
        console.clear()
        console.print()
        show_panel("🔄  Prestige System", "Reset for permanent bonuses", "magenta")
        console.print()

        prestige_title, prestige_icon = get_prestige(self.prestige_level)
        next_prestige = self.prestige_level + 1
        _, next_prestige_title, _ = next((t for t in PRESTIGE_RANKS if t[0] > self.prestige_level), (None, None, None))

        console.print(f"  Current Prestige: [bold]{prestige_icon} {prestige_title or 'None'}[/bold]")
        console.print(f"  Next: [bold]{next_prestige}. {next_prestige_title or 'MAX'}[/bold]")
        console.print(f"  XP Bonus: [bold green]+{self.prestige_bonus * 10}%[/bold green]")
        console.print()
        console.print(f"  [bold red]⚠️  Warning:[/bold red] This will reset:")
        console.print(f"     • All XP (back to 0)")
        console.print(f"     • All level progress")
        console.print(f"     • All inventory items")
        console.print(f"     • All lifelines")
        console.print(f"     • Boss progress")
        console.print()
        console.print(f"  [bold green]What you keep:[/bold green]")
        console.print(f"     • Prestige level (+1)")
        console.print(f"     • Prestige XP bonus (+10% per level)")
        console.print(f"     • Lore and journal entries")
        console.print(f"     • Custom questions")
        console.print()

        if self.total_xp < 20000:
            console.print(f"  [dim]Need 20,000 XP to prestige (you have {self.total_xp})[/dim]")
            console.print()
            console.input("[bold green]╰─► Press Enter...[/bold green]")
            return

        console.print(f"  [yellow]Y[/yellow] [bold red]PRESTIGE NOW[/bold red]")
        console.print(f"  [yellow]N[/yellow] [white]Cancel[/white]")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Confirm (Y/N):[/bold green] ").strip().upper()
            if choice == "Y":
                self._do_prestige()
        except KeyboardInterrupt: pass

    def _do_prestige(self):
        """Execute prestige reset."""
        self.prestige_level += 1
        self.prestige_bonus += 1

        # Keep: prestige_level, prestige_bonus, lore_unlocked, journal, custom_questions
        kept_lore = list(self.lore_unlocked)
        kept_journal = dict(self.journal)
        kept_custom = list(self.custom_questions)

        # Reset everything else
        self.verse_progress = {
            "total_xp": 0,
            "worlds": {},
            "achievements": [],
            "combo_multiplier": 1.0,
            "combo_count": 0,
            "difficulty": "normal",
            "compact_mode": False,
            "animate_narrative": False,
            "lifelines": {"fifty_fifty": 3, "skip": 2, "hint": 3},
            "inventory": [],
            "weaknesses": {},
            "lore_unlocked": kept_lore,
            "speedrun_records": {},
            "daily_challenge": None,
            "npc_memory": {},
            "secrets_found": [],
            "session_stats": {"total_sessions": 0, "total_time": 0, "total_correct": 0, "total_wrong": 0, "history": []},
            "streak_calendar": {},
            "prestige_level": self.prestige_level,
            "prestige_bonus": self.prestige_bonus,
            "custom_questions": kept_custom,
            "mentor_active": False,
            "world_themes": {},
            "quote_index": 0,
            "journal": kept_journal,
        }
        self._sync_state()
        self._save_progress()

        console.clear()
        console.print()
        play_sound("level_up", self.sound_enabled)
        show_panel(f"🔄 PRESTIGE {self.prestige_level}!", f"Permanent +{self.prestige_bonus * 10}% XP bonus!", "green")
        console.print()
        console.print(f"  {prestige_icon} [bold]{prestige_title}[/bold] achieved!")
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

    # ─── Random Event ────────────────────────────────────────────────
    # (Already handled in _enter_world and _check_random_event)

    # ─── Quote ───────────────────────────────────────────────────────
    # (Already handled in _run_level and _show_quote)


    # ─── Boss Rush Mode ──────────────────────────────────────────────

    def _run_boss_rush(self, worlds: List[Dict]):
        """Fight all world bosses back-to-back in one gauntlet."""
        console.clear()
        console.print()
        show_panel("⚔️  Boss Rush Mode", "All bosses, one run!", "red")
        console.print()
        console.print("  [dim]Face every world boss in sequence. No breaks between fights.[/dim]")
        console.print()

        bosses = []
        for world in worlds:
            wp = self._get_world_progress(world["id"])
            levels = world.get("levels", [])
            if levels:
                boss = levels[-1].get("boss", {})
                if boss:
                    bosses.append({"world": world, "boss": boss, "defeated": wp.get("boss_defeated", False)})

        if not bosses:
            show_info("No bosses available!"); time.sleep(2); return

        console.print(f"  [bold]{len(bosses)} bosses to fight![/bold]\n")
        for i, b in enumerate(bosses, 1):
            status = "[green]✅ (defeated)[/green]" if b["defeated"] else "[red]⚔️[/red]"
            console.print(f"  {i}. {b['boss'].get('name', 'Boss')} — {b['world'].get('title', '')} {status}")
        console.print()

        console.input("[bold green]╰─► Press Enter to begin the rush...[/bold green]")

        total_correct = 0
        total_questions = 0

        for i, b in enumerate(bosses, 1):
            console.clear()
            console.print()
            console.print(f"  [bold red]Boss {i}/{len(bosses)}: {b['boss'].get('name', 'Boss')}[/bold red]")
            console.print(f"  [dim]World: {b['world'].get('title', '')}[/dim]")
            console.print()
            time.sleep(1)

            boss = b["boss"]
            questions = boss.get("questions", [])
            xp_reward = boss.get("xp_reward", 150)

            correct = 0
            for j, q in enumerate(questions, 1):
                console.clear()
                console.print()
                hp_pct = ((len(questions) - correct) / len(questions)) * 100
                hp_bar = f"[red]{'█' * int(hp_pct/4)}[/{'red'}][dim]{'░' * (25 - int(hp_pct/4))}[/dim]"
                console.print(f"  Boss HP: {hp_bar} {hp_pct:.0f}%")
                console.print(f"  Q{j}/{len(questions)}")
                console.print()
                console.print(f"  [bold white]{q.get('question', '')}[/bold white]")
                console.print()
                for opt in q.get("options", []):
                    console.print(f"  [green][{opt.get('letter', '')}][/green] {opt.get('text', '')}")
                console.print()

                try:
                    answer = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
                    chosen = next((o for o in q.get("options", []) if o.get("letter", "").upper() == answer), None)
                    if chosen and chosen.get("correct", False):
                        correct += 1
                        console.print(f"\n[bold green]✅ Boss takes damage![/bold green]")
                    else:
                        console.print(f"\n[bold red]❌ Boss resists![/bold red]")
                        exp = chosen.get("explanation", q.get("explanation", "")) if chosen else ""
                        if exp: console.print(f"  📖 {exp}")
                    time.sleep(1)
                except KeyboardInterrupt: return

            total_correct += correct
            total_questions += len(questions)
            if correct >= len(questions) * 0.6:
                xp = self._add_xp(int((correct / len(questions)) * xp_reward))
                console.print(f"\n  [bold green]🏆 Boss defeated! +{xp} XP[/bold green]")
            else:
                console.print(f"\n  [bold red]💀 Boss survived ({correct}/{len(questions)})[/bold red]")
            console.input("  [dim]Press Enter for next boss...[/dim]")

        # Final results
        console.clear()
        console.print()
        accuracy = (total_correct / max(total_questions, 1)) * 100
        show_panel("🏁 Boss Rush Complete!", f"{total_correct}/{total_questions} | {accuracy:.0f}% avg", "red")
        console.input("\n[bold green]╰─► Press Enter...[/bold green]")

    # ─── Endless Mode ────────────────────────────────────────────────

    def _run_endless_mode(self, worlds: List[Dict]):
        """Infinite random scenarios until failure."""
        console.clear()
        console.print()
        show_panel("♾️  Endless Mode", "How long can you survive?", "yellow")
        console.print()
        console.print("  [dim]Random scenarios from all worlds. One wrong = game over.[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter to begin...[/bold green]")

        all_scenarios = []
        for world in worlds:
            for level in world.get("levels", []):
                for scenario in level.get("scenarios", []):
                    all_scenarios.append({
                        "scenario": scenario,
                        "world_title": world.get("title", ""),
                        "level_title": level.get("title", ""),
                    })

        if not all_scenarios:
            show_info("No scenarios available!"); time.sleep(2); return

        score = 0
        random.shuffle(all_scenarios)
        scenario_pool = list(all_scenarios)
        idx = 0

        while True:
            if idx >= len(scenario_pool):
                random.shuffle(scenario_pool)
                idx = 0

            item = scenario_pool[idx]
            scenario = item["scenario"]
            idx += 1

            console.clear()
            console.print()
            console.print(f"  [bold yellow]♾️  Endless — Scenario #{score + 1}[/bold yellow]")
            console.print(f"  [dim]{item['world_title']} → {item['level_title']}[/dim]")
            console.print()

            narrative = scenario.get("narrative", "")
            if narrative:
                console.print(f"  [italic]{narrative}[/italic]")
                console.print()

            question = scenario.get("question", "")
            console.print(f"  [bold white]{question}[/bold white]")
            console.print()

            options = scenario.get("options", [])
            for opt in options:
                console.print(f"  [green][{opt.get('letter', '')}][/green] {opt.get('text', '')}")
            console.print()

            try:
                answer = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
                chosen = next((o for o in options if o.get("letter", "").upper() == answer), None)
                if chosen and chosen.get("correct", False):
                    score += 1
                    xp = self._add_xp(15)
                    console.print(f"\n[bold green]✅ Correct! +{xp} XP (Score: {score})[/bold green]")
                    play_sound("correct", self.sound_enabled)
                    time.sleep(0.8)
                else:
                    console.print(f"\n[bold red]❌ Wrong! Game Over![/bold red]")
                    console.print(f"  [bold]Final Score: {score} scenarios[/bold]")
                    play_sound("wrong", self.sound_enabled)

                    # High score
                    best = self.verse_progress.get("endless_best", 0)
                    if score > best:
                        self.verse_progress["endless_best"] = score
                        self._save_progress()
                        console.print(f"  [bold yellow]🏆 New High Score: {score}![/bold yellow]")
                    else:
                        console.print(f"  [dim]Best: {best}[/dim]")
                    time.sleep(2)
                    return
            except KeyboardInterrupt:
                console.print("\n[yellow]Endless mode paused.[/yellow]")
                return

    # ─── Survival Mode ───────────────────────────────────────────────

    def _run_survival_mode(self, worlds: List[Dict]):
        """3 lives total — wrong answers cost lives."""
        console.clear()
        console.print()
        show_panel("💀 Survival Mode", "3 lives — how far can you go?", "red")
        console.print()
        console.print("  [dim]Wrong answers cost lives. Lose all 3 = game over.[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter to begin...[/bold green]")

        all_scenarios = []
        for world in worlds:
            for level in world.get("levels", []):
                for scenario in level.get("scenarios", []):
                    all_scenarios.append({
                        "scenario": scenario,
                        "world_title": world.get("title", ""),
                        "level_title": level.get("title", ""),
                    })

        if not all_scenarios:
            show_info("No scenarios!"); time.sleep(2); return

        lives = 3
        score = 0
        random.shuffle(all_scenarios)
        pool = list(all_scenarios)
        idx = 0

        while lives > 0 and idx < len(pool):
            item = pool[idx]
            idx += 1

            console.clear()
            console.print()
            hearts = "❤️ " * lives + "🖤 " * (3 - lives)
            console.print(f"  [bold red]💀 Survival — {hearts}[/bold red]  Score: {score}")
            console.print(f"  [dim]{item['world_title']} → {item['level_title']}[/dim]")
            console.print()

            scenario = item["scenario"]
            narrative = scenario.get("narrative", "")
            if narrative:
                console.print(f"  [italic]{narrative}[/italic]")
                console.print()

            question = scenario.get("question", "")
            console.print(f"  [bold white]{question}[/bold white]")
            console.print()

            options = scenario.get("options", [])
            for opt in options:
                console.print(f"  [green][{opt.get('letter', '')}][/green] {opt.get('text', '')}")
            console.print()

            try:
                answer = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
                chosen = next((o for o in options if o.get("letter", "").upper() == answer), None)
                if chosen and chosen.get("correct", False):
                    score += 1
                    self._add_xp(20)
                    console.print(f"\n[bold green]✅ Correct! (Score: {score})[/bold green]")
                    play_sound("correct", self.sound_enabled)
                else:
                    lives -= 1
                    console.print(f"\n[bold red]❌ Wrong! Life lost! ({lives} remaining)[/bold red]")
                    play_sound("wrong", self.sound_enabled)
                    if chosen:
                        exp = chosen.get("explanation", scenario.get("explanation_wrong", ""))
                        if exp: console.print(f"  📖 {exp}")
                time.sleep(1.5)
            except KeyboardInterrupt: return

        console.clear()
        console.print()
        if lives <= 0:
            show_panel("💀 Game Over!", f"Final Score: {score} scenarios", "red")
        else:
            show_panel("🏁 Survival Complete!", f"Score: {score} scenarios", "green")

        best = self.verse_progress.get("survival_best", 0)
        if score > best:
            self.verse_progress["survival_best"] = score
            self._save_progress()
            console.print(f"  [bold yellow]🏆 New Best: {score}![/bold yellow]")
        console.print(f"  [dim]Lives remaining: {lives}[/dim]")
        console.input("\n[bold green]╰─► Press Enter...[/bold green]")

    # ─── Randomizer Mode ─────────────────────────────────────────────

    def _run_randomizer_mode(self, worlds: List[Dict]):
        """Shuffle all content for a completely random experience."""
        console.clear()
        console.print()
        show_panel("🎲 Randomizer Mode", "Everything shuffled!", "magenta")
        console.print()

        all_scenarios = []
        for world in worlds:
            for level in world.get("levels", []):
                for scenario in level.get("scenarios", []):
                    all_scenarios.append({
                        "scenario": scenario,
                        "world": world,
                        "level": level,
                    })

        random.shuffle(all_scenarios)
        pool = all_scenarios[:10]  # 10 random scenarios

        if not pool:
            show_info("No scenarios!"); time.sleep(2); return

        console.print(f"  [dim]10 random scenarios from across all worlds[/dim]")
        console.print()
        console.input("[bold green]╰─► Press Enter to begin...[/bold green]")

        correct = 0
        for i, item in enumerate(pool, 1):
            console.clear()
            console.print()
            console.print(f"  [bold magenta]🎲 Randomizer {i}/10[/bold magenta]")
            console.print(f"  [dim]{item['world'].get('title', '')} → {item['level'].get('title', '')}[/dim]")
            console.print()

            scenario = item["scenario"]
            narrative = scenario.get("narrative", "")
            if narrative:
                console.print(f"  [italic]{narrative}[/italic]")
                console.print()

            question = scenario.get("question", "")
            console.print(f"  [bold white]{question}[/bold white]")
            console.print()

            options = scenario.get("options", [])
            for opt in options:
                console.print(f"  [green][{opt.get('letter', '')}][/green] {opt.get('text', '')}")
            console.print()

            try:
                answer = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
                chosen = next((o for o in options if o.get("letter", "").upper() == answer), None)
                if chosen and chosen.get("correct", False):
                    correct += 1
                    self._add_xp(20)
                    console.print(f"\n[bold green]✅ Correct![/bold green]")
                    play_sound("correct", self.sound_enabled)
                else:
                    console.print(f"\n[bold red]❌ Wrong![/bold red]")
                    play_sound("wrong", self.sound_enabled)
                time.sleep(1)
            except KeyboardInterrupt: return

        console.clear()
        console.print()
        show_panel("🎲 Randomizer Complete!", f"{correct}/10 correct", "magenta")
        console.input("\n[bold green]╰─► Press Enter...[/bold green]")

    # ─── Side Quests ─────────────────────────────────────────────────

    def _check_side_quests(self, world_id: str) -> List[Dict]:
        """Check for available side quests in a world."""
        quests = []
        wp = self._get_world_progress(world_id)
        completed = wp.get("completed_levels", [])
        quests_done = wp.get("side_quests", [])

        world = self.worlds_data.get(world_id, {})
        defined_quests = world.get("side_quests", [])

        for q in defined_quests:
            qid = q.get("id", "")
            if qid not in quests_done:
                # Check if requirements met
                reqs = q.get("requirements", {})
                met = True
                if reqs.get("levels_completed", 0) > len(completed):
                    met = False
                if met:
                    q["available"] = True
                    quests.append(q)

        return quests

    def _complete_side_quest(self, world_id: str, quest_id: str):
        """Mark a side quest as completed."""
        wp = self._get_world_progress(world_id)
        if "side_quests" not in wp:
            wp["side_quests"] = []
        wp["side_quests"].append(quest_id)
        self._set_world_progress(world_id, wp)

    # ─── Unlock Cinematics ──────────────────────────────────────────

    def _show_unlock_cinematic(self, world: Dict):
        """Show cinematic when unlocking a new world."""
        console.clear()
        console.print()

        title = world.get("title", "New World")
        icon = world.get("icon", "🌍")
        desc = world.get("description", "")

        # Simple cinematic
        console.print("  [dim]" + "═" * 40 + "[/dim]")
        console.print()
        for char in title:
            console.print(f"[bold magenta]{char}[/bold magana]", end="", flush=False)
            time.sleep(0.05)
        console.print()
        console.print()
        console.print(f"  {icon}")
        console.print()
        console.print(f"  [italic]{desc}[/italic]")
        console.print()
        console.print("  [dim]" + "═" * 40 + "[/dim]")
        console.print()
        console.print("  [bold green]🔓 World Unlocked![/bold green]")
        console.print()
        console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

    # ─── Secret Worlds ───────────────────────────────────────────────

    def _check_secret_worlds(self, worlds: List[Dict]) -> List[Dict]:
        """Check if any secret worlds should be unlocked."""
        secret_worlds = []
        for world in worlds:
            wid = world["id"]
            wp = self._get_world_progress(wid)
            secrets_found = len(self.verse_progress.get("secrets_found", []))
            lore_found = len(self.lore_unlocked)

            # Secret world unlocked by finding all secrets + lore
            if world.get("is_secret_world", False):
                req_secrets = world.get("required_secrets", 4)
                req_lore = world.get("required_lore", 4)
                if secrets_found >= req_secrets and lore_found >= req_lore:
                    secret_worlds.append(world)

        return secret_worlds

    # ─── World Rival NPC ─────────────────────────────────────────────

    def _show_rival_challenge(self, world_id: str):
        """Rival Walker challenges you at milestones."""
        rival_memory = self.verse_progress.get("rival_memory", {})
        encounters = rival_memory.get("encounters", 0)

        # Only appear at milestones
        wp = self._get_world_progress(world_id)
        completed = len(wp.get("completed_levels", []))
        if completed < 2 or encounters >= 5:
            return

        console.clear()
        console.print()
        console.print("  [bold red]⚡ A figure emerges from the shadows...[/bold red]")
        console.print()
        console.print("  [bold cyan]👤 Rival Walker[/bold cyan]:")
        console.print('  [dim italic]"I\'ve been watching your progress. Let\'s see if you can match me!"[/dim italic]')
        console.print()
        console.print("  [yellow]Y[/yellow] Accept challenge  [yellow]N[/yellow] Decline")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
            if choice == "Y":
                self._run_rival_battle(world_id)
                encounters += 1
                rival_memory["encounters"] = encounters
                self.verse_progress["rival_memory"] = rival_memory
                self._save_progress()
        except KeyboardInterrupt: pass

    def _run_rival_battle(self, world_id: str):
        """Quick rival challenge — 3 questions."""
        console.clear()
        console.print()
        show_panel("👤  Rival Battle", "Prove your superiority!", "red")
        console.print()

        # Use random questions from completed levels
        world = self.worlds_data.get(world_id, {})
        questions = []
        for level in world.get("levels", []):
            for scenario in level.get("scenarios", []):
                q = {"question": scenario.get("question", ""), "options": scenario.get("options", [])}
                questions.append(q)

        random.shuffle(questions)
        questions = questions[:3]

        correct = 0
        for i, q in enumerate(questions, 1):
            console.print(f"\n  [bold]Q{i}/3[/bold]")
            console.print(f"  [white]{q['question']}[/white]")
            console.print()
            for opt in q["options"]:
                console.print(f"  [green][{opt.get('letter', '')}][/green] {opt.get('text', '')}")
            console.print()

            try:
                answer = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
                chosen = next((o for o in q["options"] if o.get("letter", "").upper() == answer), None)
                if chosen and chosen.get("correct", False):
                    correct += 1
                    console.print(f"  [bold green]✅ You strike back![/bold green]")
                else:
                    console.print(f"  [bold red]❌ Rival parries![/bold red]")
                time.sleep(1)
            except KeyboardInterrupt: return

        console.clear()
        console.print()
        if correct >= 2:
            xp = self._add_xp(100)
            show_success("🏆 Rival Defeated!", f"{correct}/3 | +{xp} XP")
            play_sound("achievement", self.sound_enabled)
        else:
            show_panel("💀 Rival Victory", f"{correct}/3 — You'll improve!", "red")
        console.input("\n[bold green]╰─► Press Enter...[/bold green]")

    # ─── Seasonal Events ─────────────────────────────────────────────

    def _check_seasonal_event(self) -> Optional[Dict]:
        """Check for active seasonal/limited-time events."""
        today = datetime.now()
        events = self.verse_progress.get("seasonal_events", [])

        # Example: Code Week (first week of May)
        if today.month == 5 and today.day <= 7:
            return {
                "name": "Code Week",
                "icon": "💻",
                "description": "Double XP week!",
                "xp_mult": 2.0,
                "active": True,
            }

        # Example: Hacktober (October)
        if today.month == 10:
            return {
                "name": "Hacktober",
                "icon": "🎃",
                "description": "Spooky coding challenges!",
                "xp_mult": 1.5,
                "active": True,
            }

        return None

    # ─── Mid-World Checkpoints ───────────────────────────────────────

    def _save_checkpoint(self, world_id: str, level_id: str):
        """Save a mid-world checkpoint."""
        if "checkpoints" not in self.verse_progress:
            self.verse_progress["checkpoints"] = {}
        self.verse_progress["checkpoints"][world_id] = {
            "level_id": level_id,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self._save_progress()

    def _get_checkpoint(self, world_id: str) -> Optional[Dict]:
        """Get saved checkpoint for a world."""
        return self.verse_progress.get("checkpoints", {}).get(world_id)

    # ─── Resume Prompt ───────────────────────────────────────────────

    def _show_resume_prompt(self, world: Dict) -> Optional[str]:
        """Ask player if they want to resume from checkpoint."""
        world_id = world["id"]
        cp = self._get_checkpoint(world_id)
        if not cp:
            return None

        console.clear()
        console.print()
        show_panel("🔄 Resume?", f"You left off at {cp['level_id']} on {cp['saved_at']}", "cyan")
        console.print()
        console.print("  [yellow]R[/yellow] Resume from checkpoint")
        console.print("  [yellow]S[/yellow] Start from beginning")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
            if choice == "R":
                return cp["level_id"]
            return None
        except KeyboardInterrupt: return None

    # ─── Import/Export Progress ──────────────────────────────────────

    def _export_progress(self):
        """Export verse progress to a JSON file."""
        import json
        from pathlib import Path

        export_data = {
            "total_xp": self.total_xp,
            "combo_multiplier": self.combo_multiplier,
            "difficulty": self.difficulty,
            "worlds": self.verse_progress.get("worlds", {}),
            "inventory": self.inventory,
            "lore_unlocked": self.lore_unlocked,
            "weaknesses": self.weaknesses,
            "prestige_level": self.prestige_level,
            "endless_best": self.verse_progress.get("endless_best", 0),
            "survival_best": self.verse_progress.get("survival_best", 0),
            "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        export_path = Path.home() / "kslearn_verse_export.json"
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

        show_panel("📤 Progress Exported!", f"Saved to: {export_path}", "green")
        console.input("\n[bold green]╰─► Press Enter...[/bold green]")

    def _import_progress(self):
        """Import verse progress from a JSON file."""
        import json
        from pathlib import Path

        import_path = Path.home() / "kslearn_verse_export.json"
        if not import_path.exists():
            show_info(f"No export file found at: {import_path}")
            time.sleep(2)
            return

        try:
            with open(import_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            show_error(f"Failed to read export file: {e}")
            time.sleep(2)
            return

        console.clear()
        console.print()
        show_panel("📥 Import Progress", f"From: {import_data.get('exported_at', 'Unknown')}", "cyan")
        console.print()
        console.print(f"  XP: {import_data.get('total_xp', 0)}")
        console.print(f"  Difficulty: {import_data.get('difficulty', 'normal')}")
        console.print(f"  Prestige: {import_data.get('prestige_level', 0)}")
        console.print(f"  Worlds: {len(import_data.get('worlds', {}))}")
        console.print()
        console.print("  [yellow]Y[/yellow] Import  [yellow]N[/yellow] Cancel")
        console.print()

        try:
            choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip().upper()
            if choice == "Y":
                self.verse_progress["total_xp"] = import_data.get("total_xp", 0)
                self.verse_progress["combo_multiplier"] = import_data.get("combo_multiplier", 1.0)
                self.verse_progress["difficulty"] = import_data.get("difficulty", "normal")
                self.verse_progress["worlds"] = import_data.get("worlds", {})
                self.verse_progress["inventory"] = import_data.get("inventory", [])
                self.verse_progress["lore_unlocked"] = import_data.get("lore_unlocked", [])
                self.verse_progress["weaknesses"] = import_data.get("weaknesses", {})
                self.verse_progress["prestige_level"] = import_data.get("prestige_level", 0)
                self.verse_progress["endless_best"] = import_data.get("endless_best", 0)
                self.verse_progress["survival_best"] = import_data.get("survival_best", 0)
                self._sync_state()
                self._save_progress()
                show_success("Progress imported!")
            else:
                show_info("Import cancelled.")
        except KeyboardInterrupt: pass

    # ─── Share Codes ─────────────────────────────────────────────────

    def _generate_share_code(self):
        """Generate a shareable progress code."""
        data = f"{self.total_xp}:{self.prestige_level}:{self.combo_multiplier}"
        code = encode_challenge(data)
        rank_title, _, _ = get_rank(self.total_xp)

        console.clear()
        console.print()
        show_panel("📤 Your Share Code", "Share with friends!", "magenta")
        console.print()
        console.print(f"  [bold cyan]{code}[/bold cyan]")
        console.print()
        console.print(f"  XP: {self.total_xp} | Rank: {rank_title}")
        console.print(f"  Prestige: {self.prestige_level}")
        console.print()
        console.print("  [dim]📋 Copy this code to share your progress![/dim]")
        console.input("\n[bold green]╰─► Press Enter...[/bold green]")

    # ─── Learning Report Card ────────────────────────────────────────

    def _generate_report_card(self, worlds: List[Dict]):
        """Generate a semester-style learning report card."""
        console.clear()
        console.print()
        show_panel("📊  Learning Report Card", "Your verse journey", "cyan")
        console.print()

        rank_title, _, _ = get_rank(self.total_xp)
        worlds_completed = sum(1 for w in worlds if self._get_world_progress(w["id"]).get("world_completed"))

        # Stats
        stats = self.session_stats
        total_sessions = stats.get("total_sessions", 0)
        total_correct = stats.get("total_correct", 0)
        total_wrong = stats.get("total_wrong", 0)
        total = total_correct + total_wrong
        accuracy = (total_correct / max(total, 1)) * 100

        # Grade
        if accuracy >= 90: grade, grade_color = "A+", "bright_green"
        elif accuracy >= 80: grade, grade_color = "A", "green"
        elif accuracy >= 70: grade, grade_color = "B", "yellow"
        elif accuracy >= 60: grade, grade_color = "C", "cyan"
        elif accuracy >= 50: grade, grade_color = "D", "orange1"
        else: grade, grade_color = "F", "red"

        report_lines = [
            "╔══════════════════════════════════════╗",
            "║       📊 LEARNING REPORT CARD        ║",
            "╠══════════════════════════════════════╣",
            f"║  Grade: [{grade_color}]{grade}[/[{grade_color}]".ljust(38) + "║",
            f"║  Rank: {rank_title.ljust(28)}║",
            f"║  XP: {str(self.total_xp).ljust(32)}║",
            f"║  Prestige: {str(self.prestige_level).ljust(26)}║",
            "╠══════════════════════════════════════╣",
            f"║  Sessions: {str(total_sessions).ljust(26)}║",
            f"║  Correct: {str(total_correct).ljust(27)}║",
            f"║  Wrong: {str(total_wrong).ljust(29)}║",
            f"║  Accuracy: {accuracy:.0f}%".ljust(38) + "║",
            f"║  Worlds Done: {worlds_completed}".ljust(38) + "║",
            "╚══════════════════════════════════════╝",
        ]

        for line in report_lines:
            console.print(line)
        console.print()

        # World-by-world breakdown
        console.print("  [bold]World Breakdown:[/bold]\n")
        for world in worlds:
            wid = world["id"]
            wp = self._get_world_progress(wid)
            icon = world.get("icon", "🌍")
            title = world.get("title", "Unknown")
            completed = len(wp.get("completed_levels", []))
            total_lv = len(world.get("levels", []))
            boss = "🏆" if wp.get("boss_defeated") else ""
            console.print(f"  {icon} {title} — {completed}/{total_lv} {boss}")
        console.print()
        console.input("[bold green]╰─► Press Enter...[/bold green]")

    # ─── World Builder (In-App) ──────────────────────────────────────

    def _run_world_builder(self):
        """Guided wizard to create a new verse world."""
        console.clear()
        console.print()
        show_panel("🛠️  World Builder", "Create a new verse world!", "cyan")
        console.print()
        console.print("  [dim]Answer prompts to build your world JSON.[/dim]")
        console.print()

        try:
            console.print("  [bold]1. World Basics[/bold]\n")
            world_id = console.input("  World ID (e.g., python_kingdom): ").strip().lower().replace(" ", "_")
            if not world_id: return
            world_title = console.input("  World Title: ").strip()
            world_icon = console.input("  World Icon (emoji): ").strip() or "🌍"
            world_desc = console.input("  World Description: ").strip()
            world_diff = console.input("  Difficulty (beginner/intermediate/advanced): ").strip() or "beginner"
            level_req = console.input("  Required Player Level (number): ").strip() or "1"

            console.print("\n  [bold]2. World Saved![/bold]")
            console.print(f"  ID: {world_id}")
            console.print(f"  Title: {world_title}")
            console.print(f"  Icon: {world_icon}")
            console.print(f"  Description: {world_desc}")
            console.print(f"  Difficulty: {world_diff}")
            console.print(f"  Required Level: {level_req}")
            console.print()
            console.print("  [dim]A basic world template has been created.[/dim]")
            console.print("  [dim]Add levels by editing the JSON at:[/dim]")
            console.print(f"  [cyan]data/ksl/{world_id}_verse.json[/cyan]")
            console.print()

            # Create basic world JSON
            world_data = {
                "verse": {
                    "id": world_id,
                    "title": world_title,
                    "description": world_desc,
                    "icon": world_icon,
                    "difficulty": world_diff,
                    "player_level_required": int(level_req),
                    "levels": [],
                }
            }

            world_path = KSL_DIR / f"{world_id}_verse.json"
            with open(world_path, "w", encoding="utf-8") as f:
                json.dump(world_data, f, indent=2, ensure_ascii=False)

            show_success(f"World created: {world_path}")
            console.input("\n[bold green]╰─► Press Enter...[/bold green]")
        except KeyboardInterrupt: pass

    # ─── AI World Generator (from Course Catalog + Parallel tgpt) ────

    def _call_tgpt(self, prompt: str, system: str = "", timeout: int = 120) -> str:
        """Call tgpt AI via subprocess. Returns response text or empty string."""
        import subprocess
        import shutil

        tgpt_path = None
        for p in ["/data/data/com.termux/files/usr/bin/tgpt", "/usr/local/bin/tgpt", "/usr/bin/tgpt"]:
            if Path(p).exists():
                tgpt_path = p
                break
        if not tgpt_path:
            tgpt_path = shutil.which("tgpt")
        if not tgpt_path:
            return ""

        cmd = [tgpt_path, "--provider", "sky", "-q"]
        if system:
            cmd.extend(["-preprompt", system])
        cmd.append(prompt)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        return ""

    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """Try to extract JSON from AI response text."""
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                return json.loads(json_str.replace("'", '"'))
            except Exception:
                return None

    def _extract_course_context(self, course: Dict) -> str:
        """Extract readable context from a hierarchical course for AI inspiration."""
        lines = []
        title = course.get("title", "Unknown Course")
        desc = course.get("description", "")
        lines.append(f"Course: {title}")
        if desc:
            lines.append(f"Description: {desc}")
        lines.append("")

        categories = course.get("categories", [])
        for cat in categories:
            cat_title = cat.get("title", cat.get("name", ""))
            cat_desc = cat.get("description", "")
            lines.append(f"  Category: {cat_title}")
            if cat_desc:
                lines.append(f"    {cat_desc}")

            units = cat.get("units", cat.get("topics", []))
            for unit in units:
                unit_title = unit.get("title", unit.get("name", ""))
                unit_desc = unit.get("description", "")
                lines.append(f"    Unit: {unit_title}")
                if unit_desc:
                    lines.append(f"      {unit_desc}")

                outcomes = unit.get("outcomes", unit.get("learning_outcomes", []))
                for outcome in outcomes:
                    out_title = outcome.get("title", outcome.get("name", ""))
                    lines.append(f"      Outcome: {out_title}")

                    subtopics = outcome.get("subtopics", outcome.get("topics", []))
                    for sub in subtopics:
                        sub_title = sub.get("title", sub.get("name", ""))
                        sub_content = sub.get("content", sub.get("text", ""))
                        lines.append(f"        Topic: {sub_title}")
                        if sub_content:
                            # Truncate long content
                            content_preview = sub_content[:200]
                            lines.append(f"          {content_preview}")

        return "\n".join(lines)

    def _generate_level_from_course(self, world_title: str, level_num: int, level_title: str,
                                     concepts: List[str], story_intro: str,
                                     course_context: str, num_scenarios: int = 5) -> Optional[Dict]:
        """Generate a level using AI, inspired by course catalog content."""
        system_prompt = (
            "You are a creative educational content writer for KSL-Verse, a text-based learning game. "
            "Generate immersive, story-driven game scenarios from course material. "
            "Return ONLY valid JSON. No markdown, no explanation. "
            "Each scenario needs: id, concept, narrative (story text), question, "
            "options (array of 4 objects with letter A-D, text, correct boolean), "
            "explanation_correct, explanation_wrong, related_concepts (array). "
            "Transform educational content into adventure narratives. Make it engaging!"
        )

        concept_str = ", ".join(concepts) if concepts else "general topics"

        prompt = (
            f"Create {num_scenarios} game scenarios for level '{level_title}' "
            f"in world '{world_title}'.\n\n"
            f"Course material to adapt:\n{course_context}\n\n"
            f"Concepts to cover: {concept_str}\n"
            f"Story setting: {story_intro}\n\n"
            f"Transform this educational content into an adventure game. "
            f"Each scenario should have a narrative that fits the world theme, "
            f"a question testing the concept, 4 options (one correct), and explanations. "
            f"Make questions progressively harder. Include one secret scenario "
            f"(is_secret: true, secret_lore_id, secret_lore_title, secret_lore_content). "
            f"Return JSON with key 'scenarios'."
        )

        response = self._call_tgpt(prompt, system_prompt)
        if not response:
            return None

        data = self._parse_json_response(response)
        if not data or "scenarios" not in data:
            return None

        scenarios = data["scenarios"]
        for i, s in enumerate(scenarios):
            s.setdefault("id", f"scene_{i+1}")
            s.setdefault("concept", concepts[i] if i < len(concepts) else f"topic_{i+1}")
            s.setdefault("is_secret", False)
            for opt in s.get("options", []):
                opt.setdefault("correct", False)
                opt.setdefault("letter", "")
                opt.setdefault("text", "")

        # Generate mini-boss
        mb_prompt = (
            f"Generate 3 challenging mini-boss questions for level '{level_title}' "
            f"in '{world_title}'. Based on these concepts: {concept_str}. "
            f"Make them harder than regular scenarios. Return JSON with key 'questions' "
            f"containing 3 objects each with: question, options (4 with letter/text/correct), explanation."
        )
        mb_response = self._call_tgpt(mb_prompt, system_prompt)
        mini_boss = None
        if mb_response:
            mb_data = self._parse_json_response(mb_response)
            if mb_data and "questions" in mb_data:
                mini_boss = {
                    "id": f"mini_boss_{level_num}",
                    "name": f"The {level_title} Guardian",
                    "xp_reward": 75,
                    "questions": mb_data["questions"],
                }

        return {
            "id": f"level_{level_num}",
            "title": level_title,
            "story_intro": story_intro,
            "icon": "📍",
            "xp_reward_per_scenario": 25,
            "concepts": concepts,
            "scenarios": scenarios,
            "mini_boss": mini_boss,
        }

    def _generate_boss_from_course(self, world_title: str, all_concepts: List[str],
                                     course_context: str) -> Optional[Dict]:
        """Generate boss battle covering all course concepts."""
        system_prompt = (
            "You are a creative boss battle designer for KSL-Verse. "
            "Generate 5 challenging questions covering ALL concepts of a world. "
            "Return ONLY valid JSON with: name, narrative, xp_reward (150), "
            f"questions (array of 5 with question, options[4 with letter/text/correct], explanation)."
        )

        concept_str = ", ".join(all_concepts)
        prompt = (
            f"Design a final boss battle for world '{world_title}'.\n\n"
            f"Source material:\n{course_context}\n\n"
            f"Concepts to test: {concept_str}\n\n"
            f"Create a dramatic boss that challenges mastery of ALL these concepts. "
            f"Questions should be harder than regular levels. Return JSON."
        )

        response = self._call_tgpt(prompt, system_prompt)
        if not response:
            return None

        data = self._parse_json_response(response)
        if not data:
            return None

        return {
            "id": "boss_1",
            "name": data.get("name", "The Final Guardian"),
            "narrative": data.get("narrative", "Prove your mastery!"),
            "xp_reward": data.get("xp_reward", 150),
            "questions": data.get("questions", []),
        }

    def _generate_lore_from_course(self, world_title: str, course_context: str,
                                     num_lore: int = 4) -> Optional[Dict]:
        """Generate lore entries inspired by course material."""
        system_prompt = (
            "You are a creative worldbuilder. Generate lore entries for an educational game world. "
            "Transform course material into mythology, origin stories, and legends. "
            "Return ONLY valid JSON with key 'lore' containing entries with title, icon (emoji), content."
        )

        prompt = (
            f"Create {num_lore} lore entries for the game world '{world_title}'.\n\n"
            f"Source material:\n{course_context}\n\n"
            f"Transform this into creative backstory, origin stories, developer quotes, or legends. "
            f"Make it educational and immersive. Return JSON."
        )

        response = self._call_tgpt(prompt, system_prompt)
        if not response:
            return None

        data = self._parse_json_response(response)
        return data.get("lore") if data else None

    def _generate_epilogue(self, world_title: str, world_desc: str) -> str:
        """Generate world completion epilogue."""
        prompt = (
            f"Write a short cinematic epilogue (3-4 sentences) for completing the world "
            f"'{world_title}' ({world_desc}). Inspiring and educational. ONLY the text."
        )
        response = self._call_tgpt(prompt, "You are a creative writer for an educational game.")
        return response if response else f"You have conquered {world_title}!"

    def _auto_generate_world(self):
        """AI World Generator — pulls from Course Catalog as inspiration.

        Shows existing hierarchical courses → User picks one → AI generates
        complete verse world in parallel using course content as source material.

        Uses tgpt/sky with ThreadPoolExecutor for parallel generation.
        """
        from concurrent.futures import ThreadPoolExecutor

        console.clear()
        console.print()
        show_panel("🤖  AI World Generator", "From Course Catalog to Game World!", "cyan")
        console.print()
        console.print("  [dim]Uses existing courses as inspiration — AI generates full game content[/dim]")
        console.print("  [dim]Parallel generation: levels + boss + lore + epilogue simultaneously[/dim]")
        console.print()

        try:
            # Step 1: Load and display available courses
            from kslearn.loader import content_loader
            courses = content_loader.load_hierarchical_courses()

            if not courses:
                show_info("No courses found in catalog! Add hierarchical .ksl files to data/ksl/ first.")
                console.print("\n  [dim]Tip: Run 'kslearn' → Course Catalog to see available courses.[/dim]")
                console.input("\n[bold green]╰─► Press Enter...[/bold green]")
                return

            console.print("  [bold]Step 1: Choose a Course[/bold]\n")
            console.print("  [dim]Select a course to transform into a verse world:[/dim]\n")

            for i, course in enumerate(courses, 1):
                title = course.get("title", "Untitled")
                desc = course.get("description", "")[:60]
                icon = course.get("icon", "📚")
                cats = len(course.get("categories", []))
                diff = course.get("difficulty", "beginner")
                diff_icon = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(diff, "⚪")
                console.print(f"  [yellow]{i:02d}[/yellow] {icon} [white]{title}[/white] {diff_icon}")
                console.print(f"       [dim]{desc}... ({cats} categories)[/dim]")
                console.print()

            console.print(f"  [yellow] 1[/yellow]-[yellow]{len(courses)}[/yellow] [white]Select Course[/white]")
            console.print(f"  [yellow] C[/yellow] [white]✏️  Create Custom World (no course)[/white]")
            console.print(f"  [yellow] 0[/yellow] [white]Back[/white]")
            console.print()

            choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip()

            if choice == "0":
                return
            elif choice.upper() == "C":
                self._generate_custom_world_no_course()
                return

            try:
                idx = int(choice)
                if not (1 <= idx <= len(courses)):
                    show_warning("Invalid selection!"); time.sleep(1); return
            except ValueError:
                show_warning("Invalid input!"); time.sleep(1); return

            selected_course = courses[idx - 1]
            course_title = selected_course.get("title", "Unknown Course")
            course_id = selected_course.get("id", selected_course.get("code", ""))

            # Extract course context
            course_context = self._extract_course_context(selected_course)

            # Build level plan from course categories/units
            categories = selected_course.get("categories", [])
            if not categories:
                show_info("This course has no categories/units. Cannot generate world.")
                time.sleep(2)
                return

            console.print(f"\n  [bold green]✓ Selected: {course_title}[/bold green]")
            console.print(f"  [dim]Found {len(categories)} categories → will become {len(categories)} levels[/dim]")
            console.print()

            # Step 2: World customization
            console.print("  [bold]Step 2: Customize Your World[/bold]\n")
            world_id = console.input(f"  World ID (default: {course_id.lower().replace(' ', '_').replace('-', '_')}): ").strip()
            if not world_id:
                world_id = course_id.lower().replace(' ', '_').replace('-', '_')
            world_icon = console.input(f"  World Icon (default: {selected_course.get('icon', '📚')}): ").strip() or selected_course.get('icon', '📚')
            world_diff = console.input(f"  Difficulty (default: {selected_course.get('difficulty', 'beginner')}): ").strip() or selected_course.get('difficulty', 'beginner')
            level_req = console.input("  Required Player Level (default: 1): ").strip() or "1"

            # Build level descriptions from course structure
            level_descriptions = []
            for cat in categories:
                cat_title = cat.get("title", cat.get("name", "Untitled"))
                cat_desc = cat.get("description", "")
                units = cat.get("units", cat.get("topics", []))

                # Extract concepts from units
                concepts = []
                for unit in units:
                    unit_title = unit.get("title", unit.get("name", ""))
                    if unit_title:
                        concepts.append(unit_title)
                    outcomes = unit.get("outcomes", unit.get("learning_outcomes", []))
                    for outcome in outcomes:
                        out_title = outcome.get("title", outcome.get("name", ""))
                        if out_title:
                            concepts.append(out_title)

                # Generate a story-style intro for this level
                story_intro = f"You enter the realm of {cat_title}..." if cat_desc else f"Welcome to {cat_title}..."

                level_descriptions.append({
                    "title": cat_title,
                    "concepts": concepts[:8] if concepts else [cat_title],
                    "story_intro": story_intro,
                })

            # Step 3: Parallel generation
            console.clear()
            console.print()
            show_panel("🔄  Generating World Content", "AI is working in parallel...", "cyan")
            console.print()

            all_concepts = []
            for ld in level_descriptions:
                all_concepts.extend(ld.get("concepts", []))

            num_levels = len(level_descriptions)
            tasks = []

            with ThreadPoolExecutor(max_workers=min(num_levels + 3, 10)) as executor:
                # Level generation — each level in parallel
                for i, ld in enumerate(level_descriptions, 1):
                    tasks.append(executor.submit(
                        self._generate_level_from_course,
                        world_id, i, ld["title"], ld["concepts"], ld["story_intro"],
                        course_context, num_scenarios=5
                    ))

                # Boss generation
                boss_future = executor.submit(
                    self._generate_boss_from_course, world_id, all_concepts, course_context
                )

                # Lore generation
                lore_future = executor.submit(
                    self._generate_lore_from_course, world_id, course_context,
                    num_lore=min(4, num_levels)
                )

                # Epilogue
                epilogue_future = executor.submit(
                    self._generate_epilogue, world_id,
                    f"Based on {course_title}"
                )

            # Collect results
            console.print("  [bold green]✓ Content generated![/bold green]\n")

            levels = []
            for i, future in enumerate(tasks):
                result = future.result()
                if result:
                    levels.append(result)
                    console.print(f"  ✅ Level {i+1}: {result.get('title', 'Generated')} ({len(result.get('scenarios', []))} scenarios)")
                else:
                    console.print(f"  ⚠️  Level {i+1}: AI generation failed — creating placeholder")
                    ld = level_descriptions[i]
                    levels.append({
                        "id": f"level_{i+1}",
                        "title": ld["title"],
                        "story_intro": ld["story_intro"],
                        "icon": world_icon,
                        "xp_reward_per_scenario": 25,
                        "concepts": ld.get("concepts", []),
                        "scenarios": [],
                        "mini_boss": None,
                    })

            boss_result = boss_future.result()
            lore_result = lore_future.result()
            epilogue = epilogue_future.result()

            # Attach boss to last level
            if boss_result and levels:
                levels[-1]["boss"] = boss_result

            # Build complete world JSON
            world_data = {
                "verse": {
                    "id": world_id,
                    "title": world_id.replace("_", " ").title(),
                    "description": f"AI-generated from course: {course_title}",
                    "icon": world_icon,
                    "difficulty": world_diff,
                    "player_level_required": int(level_req),
                    "source_course": course_id,
                    "epilogue": epilogue,
                    "concepts": all_concepts,
                    "lore": lore_result or {},
                    "levels": levels,
                }
            }

            # Save
            world_path = KSL_DIR / f"{world_id}_verse.json"
            with open(world_path, "w", encoding="utf-8") as f:
                json.dump(world_data, f, indent=2, ensure_ascii=False)

            console.print()
            total_scenarios = sum(len(l.get("scenarios", [])) for l in levels)
            show_panel("🌍  World Generated!", f"{len(levels)} levels, {total_scenarios} scenarios", "green")
            console.print(f"  Course: {course_title}")
            console.print(f"  Saved: [cyan]{world_path}[/cyan]")
            console.print(f"  Levels: {len(levels)} | Concepts: {len(all_concepts)}")
            if lore_result:
                console.print(f"  Lore: {len(lore_result)} entries")
            if boss_result:
                console.print(f"  Boss: {boss_result.get('name', 'Generated')} ({len(boss_result.get('questions', []))} questions)")
            console.print()
            console.input("[bold green]╰─► Press Enter to continue...[/bold green]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Generation cancelled.[/yellow]")
            time.sleep(1)

    def _generate_custom_world_no_course(self):
        """Fallback: manual world creation without course catalog."""
        console.clear()
        console.print()
        show_panel("✏️  Custom World (Manual)", "No course — describe your world!", "cyan")
        console.print()

        try:
            world_id = console.input("  World ID (e.g., python_kingdom): ").strip().lower().replace(" ", "_")
            if not world_id: return
            world_title = console.input("  World Title: ").strip()
            world_icon = console.input("  World Icon (emoji): ").strip() or "🌍"
            world_diff = console.input("  Difficulty: ").strip() or "beginner"
            level_req = console.input("  Required Level: ").strip() or "1"

            num_levels = console.input("  Number of levels (1-5): ").strip()
            try:
                num_levels = max(1, min(5, int(num_levels)))
            except ValueError:
                num_levels = 3

            level_descriptions = []
            for i in range(1, num_levels + 1):
                console.print(f"\n  [bold]Level {i}:[/bold]")
                ltitle = console.input(f"  Title: ").strip() or f"Level {i}"
                lconcepts = console.input(f"  Concepts (comma-separated): ").strip()
                lstory = console.input(f"  Story intro: ").strip() or f"You arrive at {ltitle}..."
                level_descriptions.append({
                    "title": ltitle,
                    "concepts": [c.strip() for c in lconcepts.split(",") if c.strip()] if lconcepts else [],
                    "story_intro": lstory,
                })

            # Generate via AI (no course context)
            console.clear()
            console.print()
            show_panel("🔄  Generating...", "AI is working...", "cyan")
            console.print()

            all_concepts = []
            for ld in level_descriptions:
                all_concepts.extend(ld.get("concepts", []))

            from concurrent.futures import ThreadPoolExecutor
            levels = []
            with ThreadPoolExecutor(max_workers=min(num_levels + 2, 8)) as executor:
                futures = []
                for i, ld in enumerate(level_descriptions, 1):
                    futures.append(executor.submit(
                        self._generate_level_from_course,
                        world_id, i, ld["title"], ld["concepts"], ld["story_intro"],
                        "", num_scenarios=5
                    ))
                boss_future = executor.submit(
                    self._generate_boss_from_course, world_id, all_concepts, ""
                )
                lore_future = executor.submit(
                    self._generate_lore_from_course, world_id, "", min(4, num_levels)
                )
                epilogue_future = executor.submit(
                    self._generate_epilogue, world_id, world_title
                )

                for i, f in enumerate(futures):
                    r = f.result()
                    if r: levels.append(r)

                boss_result = boss_future.result()
                lore_result = lore_future.result()
                epilogue = epilogue_future.result()

            if boss_result and levels:
                levels[-1]["boss"] = boss_result

            world_data = {
                "verse": {
                    "id": world_id,
                    "title": world_title,
                    "description": f"Custom AI-generated world",
                    "icon": world_icon,
                    "difficulty": world_diff,
                    "player_level_required": int(level_req),
                    "epilogue": epilogue,
                    "concepts": all_concepts,
                    "lore": lore_result or {},
                    "levels": levels,
                }
            }

            world_path = KSL_DIR / f"{world_id}_verse.json"
            with open(world_path, "w", encoding="utf-8") as f:
                json.dump(world_data, f, indent=2, ensure_ascii=False)

            show_success(f"World saved: {world_path}")
            console.input("\n[bold green]╰─► Press Enter...[/bold green]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            time.sleep(1)

    # ─── Accessibility Settings ──────────────────────────────────────

    def _accessibility_menu(self):
        """Accessibility options."""
        while True:
            console.clear()
            console.print()
            show_panel("♿ Accessibility", "Customize your experience", "cyan")
            console.print()

            high_contrast = self.verse_progress.get("high_contrast", False)
            large_text = self.verse_progress.get("large_text", False)
            reduced_motion = not self.animate_narrative

            console.print(f"  [1] High Contrast Mode: {'[green]ON[/green]' if high_contrast else '[dim]OFF[/dim]'}")
            console.print(f"  [2] Large Text Mode: {'[green]ON[/green]' if large_text else '[dim]OFF[/dim]'}")
            console.print(f"  [3] Reduced Motion: {'[green]ON[/green]' if reduced_motion else '[dim]OFF[/dim]'}")
            console.print(f"  [4] Sound Effects: {'[green]ON[/green]' if self.sound_enabled else '[dim]OFF[/dim]'}")
            console.print(f"  [0] Back")
            console.print()

            try:
                choice = console.input("[bold green]╰─► Choose:[/bold green] ").strip()
                if choice == "0": return
                elif choice == "1":
                    self.verse_progress["high_contrast"] = not high_contrast
                    self._save_progress()
                elif choice == "2":
                    self.verse_progress["large_text"] = not large_text
                    self._save_progress()
                elif choice == "3":
                    self.animate_narrative = reduced_motion
                    self.verse_progress["animate_narrative"] = not reduced_motion
                    self._save_progress()
                elif choice == "4":
                    self.sound_enabled = not self.sound_enabled
                    self.verse_progress["sound_enabled"] = self.sound_enabled
                    self._save_progress()
                    if self.sound_enabled: play_sound("correct", True)
            except KeyboardInterrupt: return


def run_verse_interactive(multiplayer=False, session_id=None, firebase=None):
    """Main entry point for the KSL-Verse game."""
    engine = VerseEngine(multiplayer=multiplayer, session_id=session_id, firebase=firebase)
    engine.show_verse_menu()
