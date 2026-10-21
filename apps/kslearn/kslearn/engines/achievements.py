#!/usr/bin/env python3
"""Achievements & Badges System for kslearn"""

from typing import Dict, List, Optional
from datetime import datetime


# All possible achievements
ACHIEVEMENTS = {
    "first_quiz": {
        "name": "First Steps",
        "description": "Complete your first quiz",
        "icon": "🌟",
        "rarity": "common",
        "condition": "quizzes_completed >= 1",
    },
    "quiz_master": {
        "name": "Quiz Master",
        "description": "Complete 25 quizzes",
        "icon": "🏆",
        "rarity": "rare",
        "condition": "quizzes_completed >= 25",
    },
    "perfect_score": {
        "name": "Perfectionist",
        "description": "Score 100% on any quiz",
        "icon": "💎",
        "rarity": "uncommon",
        "condition": "any_score_100",
    },
    "streak_5": {
        "name": "Hot Streak",
        "description": "Study 5 days in a row",
        "icon": "🔥",
        "rarity": "uncommon",
        "condition": "streak >= 5",
    },
    "streak_30": {
        "name": "Month Warrior",
        "description": "Study 30 days in a row",
        "icon": "🔥",
        "rarity": "legendary",
        "condition": "streak >= 30",
    },
    "brain_50": {
        "name": "Knowledge Seeker",
        "description": "Save 50 Q&A pairs to the Brain",
        "icon": "🧠",
        "rarity": "uncommon",
        "condition": "brain_entries >= 50",
    },
    "brain_200": {
        "name": "Walking Encyclopedia",
        "description": "Save 200 Q&A pairs to the Brain",
        "icon": "🧠",
        "rarity": "legendary",
        "condition": "brain_entries >= 200",
    },
    "all_topics": {
        "name": "Explorer",
        "description": "Read at least one topic from 5 different categories",
        "icon": "🗺️",
        "rarity": "rare",
        "condition": "categories_read >= 5",
    },
    "speed_demon": {
        "name": "Speed Demon",
        "description": "Answer 15+ questions in a 60-second timed quiz",
        "icon": "⚡",
        "rarity": "rare",
        "condition": "timed_quiz >= 15",
    },
    "bookworm": {
        "name": "Bookworm",
        "description": "Read 20 topics across all notes",
        "icon": "📚",
        "rarity": "rare",
        "condition": "topics_read >= 20",
    },
    "first_flashcard": {
        "name": "Flash of Genius",
        "description": "Complete your first flashcard session",
        "icon": "🃏",
        "rarity": "common",
        "condition": "flashcard_sessions >= 1",
    },
    "spaced_review": {
        "name": "Consistent Learner",
        "description": "Complete 10 spaced repetition reviews",
        "icon": "📅",
        "rarity": "uncommon",
        "condition": "spaced_reviews >= 10",
    },
    "multi_subject": {
        "name": "Renaissance Mind",
        "description": "Score 80%+ in 3 different categories",
        "icon": "🎨",
        "rarity": "legendary",
        "condition": "multi_subject_80 >= 3",
    },
    "tutorial_graduate": {
        "name": "Tutorial Graduate",
        "description": "Complete your first interactive tutorial",
        "icon": "🎓",
        "rarity": "common",
        "condition": "tutorials_completed >= 1",
    },
    "profile_creator": {
        "name": "Profile Creator",
        "description": "Create a second user profile",
        "icon": "👥",
        "rarity": "common",
        "condition": "profiles >= 2",
    },
    # KSL-Verse achievements
    "verse_first_scenario": {
        "name": "First Steps in the Verse",
        "description": "Complete your first scenario in the KSL-Verse",
        "icon": "🌟",
        "rarity": "common",
        "condition": "verse_scenarios >= 1",
    },
    "verse_first_level": {
        "name": "Level Cleared",
        "description": "Complete any level in the KSL-Verse",
        "icon": "✅",
        "rarity": "common",
        "condition": "verse_levels >= 1",
    },
    "verse_world_conqueror": {
        "name": "World Conqueror",
        "description": "Complete all levels and defeat the boss of a world",
        "icon": "🏆",
        "rarity": "uncommon",
        "condition": "verse_worlds_completed >= 1",
    },
    "verse_perfect_level": {
        "name": "Perfect Run",
        "description": "Complete a level with 100% accuracy on first try",
        "icon": "💎",
        "rarity": "uncommon",
        "condition": "verse_perfect_run",
    },
    "verse_streak_5": {
        "name": "Streak Walker",
        "description": "Get a 5-answer streak in the verse",
        "icon": "🔥",
        "rarity": "rare",
        "condition": "verse_streak >= 5",
    },
    "verse_boss_slayer": {
        "name": "Boss Slayer",
        "description": "Defeat 3 boss battles",
        "icon": "⚔️",
        "rarity": "legendary",
        "condition": "verse_bosses >= 3",
    },
    "verse_multiverse": {
        "name": "Multiverse Explorer",
        "description": "Complete worlds from 2 different subjects",
        "icon": "🌌",
        "rarity": "rare",
        "condition": "verse_worlds_completed >= 2",
    },
    "verse_transcendent": {
        "name": "Verse Transcendent",
        "description": "Reach player level 10 in the KSL-Verse",
        "icon": "👑",
        "rarity": "legendary",
        "condition": "verse_level >= 10",
    },
    "verse_secret_hunter": {
        "name": "Secret Hunter",
        "description": "Discover 3 hidden secrets in the KSL-Verse",
        "icon": "🕵️",
        "rarity": "rare",
        "condition": "verse_secrets >= 3",
    },
    "verse_daily_champion": {
        "name": "Daily Champion",
        "description": "Score 3/3 on a daily challenge",
        "icon": "📅",
        "rarity": "uncommon",
        "condition": "verse_daily_perfect",
    },
    "verse_speedster": {
        "name": "Speed Runner",
        "description": "Complete a level in under 60 seconds",
        "icon": "⚡",
        "rarity": "rare",
        "condition": "verse_speedrun_under_60",
    },
    "verse_combo_master": {
        "name": "Combo Master",
        "description": "Reach a 2.0x combo multiplier",
        "icon": "🔥",
        "rarity": "uncommon",
        "condition": "verse_combo_2x",
    },
    "verse_hard_mode": {
        "name": "Masochist",
        "description": "Complete a level on Hard Mode",
        "icon": "💀",
        "rarity": "rare",
        "condition": "verse_hard_mode_clear",
    },
    "verse_collector": {
        "name": "Collector",
        "description": "Collect 10 items in your inventory",
        "icon": "🎒",
        "rarity": "uncommon",
        "condition": "verse_items >= 10",
    },
    "verse_lore_master": {
        "name": "Lore Master",
        "description": "Unlock all lore entries in a world",
        "icon": "📚",
        "rarity": "legendary",
        "condition": "verse_all_lore",
    },
    "verse_prestige": {
        "name": "Reborn",
        "description": "Prestige for the first time",
        "icon": "🔄",
        "rarity": "legendary",
        "condition": "verse_prestige_1",
    },
    "verse_journaler": {
        "name": "Journaler",
        "description": "Write 5 journal entries",
        "icon": "📓",
        "rarity": "common",
        "condition": "verse_journal_5",
    },
    "verse_ironman": {
        "name": "Iron Will",
        "description": "Complete a level on Ironman mode",
        "icon": "🦾",
        "rarity": "legendary",
        "condition": "verse_ironman_clear",
    },
    "verse_marathon": {
        "name": "Marathon Runner",
        "description": "Complete a full world in Marathon Mode",
        "icon": "🏅",
        "rarity": "legendary",
        "condition": "verse_marathon_clear",
    },
    "verse_question_author": {
        "name": "Question Author",
        "description": "Add 5 custom questions",
        "icon": "✏️",
        "rarity": "uncommon",
        "condition": "verse_custom_q_5",
    },
}

RARITY_COLORS = {
    "common": "white",
    "uncommon": "green",
    "rare": "cyan",
    "legendary": "magenta",
}


def check_achievements(config: Dict, progress: Dict, brain_count: int) -> List[Dict]:
    """Check which achievements are earned. Returns newly earned ones."""
    from kslearn.config import save_config

    earned = config.get("achievements", [])
    earned_ids = set(a.get("id", "") for a in earned)
    new_achievements = []

    quizzes_completed = len(progress)
    best_streak = config.get("study_streak", {}).get("best", 0)
    current_streak = config.get("study_streak", {}).get("current", 0)
    topics_read = sum(1 for p in progress.values() if p.get("topic"))
    flashcard_sessions = sum(1 for p in progress.values() if "flashcard" in p.get("topic", "").lower())
    spaced_reviews = sum(1 for p in progress.values() if p.get("spaced_review"))
    profiles = len(config.get("profiles", {}))
    tutorials = sum(1 for v in config.get("tutorial_progress", {}).values() if v.get("completed"))
    timed_quiz_best = config.get("timed_quiz_best", 0)  # Fixed: check config root, not progress

    # Count categories with 80%+ score
    multi_80 = 0
    for p in progress.values():
        if p.get("last_accuracy", 0) >= 80:
            multi_80 += 1

    # Count unique categories read
    categories_read = len(set(p.get("category", "") for p in progress.values() if p.get("category")))

    # Check any 100% score
    any_100 = any(p.get("last_accuracy", 0) >= 100 for p in progress.values())

    checks = {
        "first_quiz": quizzes_completed >= 1,
        "quiz_master": quizzes_completed >= 25,
        "perfect_score": any_100,
        "streak_5": best_streak >= 5,
        "streak_30": best_streak >= 30,
        "brain_50": brain_count >= 50,
        "brain_200": brain_count >= 200,
        "all_topics": categories_read >= 5,
        "speed_demon": timed_quiz_best >= 15,
        "bookworm": topics_read >= 20,
        "first_flashcard": flashcard_sessions >= 1,
        "spaced_review": spaced_reviews >= 10,
        "multi_subject": multi_80 >= 3,
        "tutorial_graduate": tutorials >= 1,
        "profile_creator": profiles >= 2,
    }

    for ach_id, condition_met in checks.items():
        if condition_met and ach_id not in earned_ids:
            ach = ACHIEVEMENTS[ach_id].copy()
            ach["id"] = ach_id
            ach["earned_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_achievements.append(ach)
            earned.append(ach)
            earned_ids.add(ach_id)

    # Save if new achievements were earned
    if new_achievements:
        save_config(config)

    return new_achievements


def get_achievement_summary(config: Dict) -> Dict:
    """Get achievement stats for display."""
    earned = config.get("achievements", [])
    total = len(ACHIEVEMENTS)
    earned_count = len(earned)
    by_rarity = {}
    for r in RARITY_COLORS:
        by_rarity[r] = sum(1 for a in earned if a.get("rarity") == r)

    return {
        "total": total,
        "earned": earned_count,
        "percentage": (earned_count / total * 100) if total > 0 else 0,
        "by_rarity": by_rarity,
        "recent": earned[-3:] if earned else [],
    }
