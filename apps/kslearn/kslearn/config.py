#!/usr/bin/env python3
"""Configuration management for kslearn CLI"""

import os
import json
import tempfile
import fcntl
from pathlib import Path
from typing import Optional, Dict
from contextlib import contextmanager

# Config locations — use centralized loader paths
from kslearn.loader import CONFIG_DIR
CONFIG_LOCATIONS = [
    CONFIG_DIR / "settings.json",
    Path.home() / ".kslearnrc",
    Path.home() / ".kslearn" / "config.json",
    Path.cwd() / ".kslearnrc",
    Path.cwd() / "kslearn.json",
]

DEFAULT_CONFIG = {
    "theme": "sky_blue",
    "sound": False,
    "auto_timer": True,
    "timer_minutes": 3,
    "show_explanations": True,
    "difficulty": "mixed",
    "language": "en",
    "username": "",
    "api_key": "",
    # Learning-focused settings
    "daily_goal_minutes": 30,
    "focus_track": "general",
    "notification_enabled": True,
    # API provider settings
    "api_provider": "anthropic",
    # UI preferences
    "use_rich_ui": True,
    "color_scheme": "cyan",
    # Progress tracking
    "bookmarks": [],
    "learning_progress": {},
    # Study streak tracking
    "study_streak": {
        "current": 0,
        "best": 0,
        "last_study_date": None,
    },
    # Achievements
    "achievements": [],
    # Spaced repetition
    "review_queue": {},
    # Daily goal tracking
    "daily_goal": {
        "today_date": None,
        "minutes_studied": 0,
    },
    # Multi-user profiles
    "active_profile": "default",
    "profiles": {
        "default": {
            "name": "Default User",
            "created": None,
        }
    },
    # User preferences
    "flashcard_mode": False,
    "timed_quiz_best": 0,
    "tutorial_progress": {},
}


def find_config() -> Optional[Path]:
    """Find existing config file"""
    for loc in CONFIG_LOCATIONS:
        if loc.exists():
            return loc
    return None


def load_config() -> dict:
    """Load configuration from file, merging profile-scoped data for the active profile."""
    config_path = find_config()
    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                config = {**DEFAULT_CONFIG, **user_config}

                # Merge profile-scoped data into root keys
                profile_name = config.get("active_profile", "default")
                for key in _PROFILE_KEYS:
                    data_key = _get_profile_data_key(profile_name, key)
                    if data_key in config:
                        config[key] = config[data_key]

                # Strip stale root-level profile keys so they don't leak back
                # on next save. Profile data is authoritative.
                for key in _PROFILE_KEYS:
                    if key in user_config:
                        del config[key]
                        # Also delete from original user_config to prevent re-write
                        # (we only delete from merged config; file stays as-is)

                return config
        except (json.JSONDecodeError, IOError):
            pass

    # Auto-migrate on first load
    return DEFAULT_CONFIG.copy()


def save_config(config: dict, path: Optional[Path] = None) -> Path:
    """Save configuration to file atomically with file locking.

    Uses atomic write (tempfile + os.replace()) to prevent corruption
    on crash, and file locking to prevent concurrent write corruption.
    """
    if path is None:
        path = CONFIG_DIR / "settings.json"

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write profile-scoped data back to profile keys before saving
    profile_name = config.get("active_profile", "default")
    for key in _PROFILE_KEYS:
        data_key = _get_profile_data_key(profile_name, key)
        if key in config:
            config[data_key] = config[key]

    # Use file lock + atomic write
    with _file_lock(path):
        _save_config_atomic(config, path)

    return path


def init_config() -> dict:
    """Initialize config with defaults if not exists"""
    config_path = find_config()
    if config_path:
        config = load_config()

        # Migrate existing root data to default profile
        profile_name = config.get("active_profile", "default")
        migration_key = f"profile_{profile_name}_migrated"
        if not config.get(migration_key):
            for key in _PROFILE_KEYS:
                if key in config:
                    data_key = _get_profile_data_key(profile_name, key)
                    if data_key not in config:
                        config[data_key] = config[key]
            config[migration_key] = True
            save_config(config)

        return config

    # Create default config in home directory
    config = DEFAULT_CONFIG.copy()
    save_config(config)
    return config


def get_config_value(key: str, default=None):
    """Get a specific config value"""
    config = load_config()
    return config.get(key, default)


def set_config_value(key: str, value):
    """Set a specific config value and save"""
    config = load_config()
    config[key] = value
    save_config(config)
    return config


def reset_config() -> dict:
    """Reset config to defaults"""
    config_path = find_config()
    if config_path:
        config_path.unlink()
    return DEFAULT_CONFIG.copy()


# --- Study Streak Tracking ---

def update_study_streak():
    """Update the study streak counter. Call this whenever user studies."""
    from datetime import datetime, timedelta

    config = load_config()
    profile_name = config.get("active_profile", "default")

    # Use profile-scoped key
    streak_key = _get_profile_data_key(profile_name, "study_streak")
    streak = config.get(streak_key, {"current": 0, "best": 0, "last_study_date": None})
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    last_date = streak.get("last_study_date")

    if last_date == today:
        return streak  # Already studied today

    if last_date == yesterday or last_date is None:
        streak["current"] = streak.get("current", 0) + 1
    else:
        streak["current"] = 1  # Streak broken, reset

    streak["best"] = max(streak.get("best", 0), streak["current"])
    streak["last_study_date"] = today

    config[streak_key] = streak
    save_config(config)
    return streak


# --- Daily Goal Tracking ---

def update_daily_goal(minutes: int = 5):
    """Add minutes to today's study goal."""
    from datetime import datetime

    config = load_config()
    profile_name = config.get("active_profile", "default")
    today = datetime.now().strftime("%Y-%m-%d")

    goal_key = _get_profile_data_key(profile_name, "daily_goal")
    goal = config.get(goal_key, {"today_date": None, "minutes_studied": 0})

    if goal.get("today_date") != today:
        goal = {"today_date": today, "minutes_studied": 0}

    goal["minutes_studied"] = goal.get("minutes_studied", 0) + minutes
    config[goal_key] = goal
    save_config(config)
    return goal


def get_daily_goal_progress():
    """Get today's goal progress."""
    from datetime import datetime

    config = load_config()
    profile_name = config.get("active_profile", "default")
    today = datetime.now().strftime("%Y-%m-%d")
    goal_minutes = config.get("daily_goal_minutes", 30)

    goal_key = _get_profile_data_key(profile_name, "daily_goal")
    daily = config.get(goal_key, {})

    if daily.get("today_date") != today:
        return {"minutes": 0, "goal": goal_minutes, "percentage": 0}

    minutes = daily.get("minutes_studied", 0)
    return {
        "minutes": minutes,
        "goal": goal_minutes,
        "percentage": min((minutes / goal_minutes) * 100, 100) if goal_minutes > 0 else 0,
    }


# --- Multi-User Profiles ---
# Profile-scoped data keys: learning_progress, bookmarks, achievements,
# study_streak, daily_goal, review_queue, tutorial_progress, timed_quiz_best

_PROFILE_KEYS = [
    "learning_progress", "bookmarks", "achievements",
    "study_streak", "daily_goal", "review_queue",
    "tutorial_progress", "timed_quiz_best", "verse_progress",
    "sessions",
]


# --- Session Tracking & Resume ---

def start_session():
    """Start a new learning session. Returns session ID."""
    from datetime import datetime
    import uuid

    config = load_config()
    profile_name = config.get("active_profile", "default")
    session_key = _get_profile_data_key(profile_name, "sessions")
    sessions = config.get(session_key, [])

    session_id = str(uuid.uuid4())
    session = {
        "id": session_id,
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": None,
        "duration_minutes": 0,
        "activities": [],
        "quizzes_taken": 0,
        "notes_viewed": 0,
        "ai_chats": 0,
        "verse_sessions": 0,
        "tutorials_completed": 0,
    }

    sessions.append(session)
    # Keep only last 50 sessions to prevent bloat
    if len(sessions) > 50:
        sessions = sessions[-50:]

    config[session_key] = sessions
    save_config(config)
    return session_id


def end_session(session_id: str):
    """End an active session and calculate final duration."""
    from datetime import datetime

    config = load_config()
    profile_name = config.get("active_profile", "default")
    session_key = _get_profile_data_key(profile_name, "sessions")
    sessions = config.get(session_key, [])

    for session in sessions:
        if session.get("id") == session_id:
            session["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Calculate duration
            start = datetime.strptime(session["start_time"], "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(session["end_time"], "%Y-%m-%d %H:%M:%S")
            duration = (end - start).total_seconds() / 60
            session["duration_minutes"] = round(duration, 2)
            break

    config[session_key] = sessions
    save_config(config)


def log_activity(session_id: str, activity_type: str, details: dict = None):
    """Log an activity to the current session."""
    from datetime import datetime

    config = load_config()
    profile_name = config.get("active_profile", "default")
    session_key = _get_profile_data_key(profile_name, "sessions")
    sessions = config.get(session_key, [])

    for session in sessions:
        if session.get("id") == session_id:
            activity = {
                "type": activity_type,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "details": details or {},
            }
            session["activities"].append(activity)

            # Update counters
            if activity_type == "quiz":
                session["quizzes_taken"] = session.get("quizzes_taken", 0) + 1
            elif activity_type == "notes":
                session["notes_viewed"] = session.get("notes_viewed", 0) + 1
            elif activity_type == "ai_chat":
                session["ai_chats"] = session.get("ai_chats", 0) + 1
            elif activity_type == "verse":
                session["verse_sessions"] = session.get("verse_sessions", 0) + 1
            elif activity_type == "tutorial":
                session["tutorials_completed"] = session.get("tutorials_completed", 0) + 1

            break

    config[session_key] = sessions
    save_config(config)


def get_session(session_id: str):
    """Get a specific session by ID."""
    config = load_config()
    profile_name = config.get("active_profile", "default")
    session_key = _get_profile_data_key(profile_name, "sessions")
    sessions = config.get(session_key, [])

    for session in sessions:
        if session.get("id") == session_id:
            return session
    return None


def get_sessions(limit: int = 10):
    """Get recent sessions, most recent first."""
    config = load_config()
    profile_name = config.get("active_profile", "default")
    session_key = _get_profile_data_key(profile_name, "sessions")
    sessions = config.get(session_key, [])

    # Return most recent first
    return list(reversed(sessions))[:limit]


def get_session_stats():
    """Get overall session statistics."""
    config = load_config()
    profile_name = config.get("active_profile", "default")
    session_key = _get_profile_data_key(profile_name, "sessions")
    sessions = config.get(session_key, [])

    if not sessions:
        return {
            "total_sessions": 0,
            "total_duration_minutes": 0,
            "total_quizzes": 0,
            "total_notes": 0,
            "total_ai_chats": 0,
            "total_verse_sessions": 0,
            "avg_duration_minutes": 0,
        }

    total_duration = sum(s.get("duration_minutes", 0) for s in sessions)
    total_quizzes = sum(s.get("quizzes_taken", 0) for s in sessions)
    total_notes = sum(s.get("notes_viewed", 0) for s in sessions)
    total_ai_chats = sum(s.get("ai_chats", 0) for s in sessions)
    total_verse = sum(s.get("verse_sessions", 0) for s in sessions)

    return {
        "total_sessions": len(sessions),
        "total_duration_minutes": round(total_duration, 2),
        "total_quizzes": total_quizzes,
        "total_notes": total_notes,
        "total_ai_chats": total_ai_chats,
        "total_verse_sessions": total_verse,
        "avg_duration_minutes": round(total_duration / len(sessions), 2) if sessions else 0,
    }


def resume_session(session_id: str):
    """Resume a session that was ended (returns new session ID if successful)."""
    session = get_session(session_id)
    if not session:
        return None

    # Create a new session based on the resumed one
    new_session_id = start_session()

    # Copy activities from previous session
    config = load_config()
    profile_name = config.get("active_profile", "default")
    session_key = _get_profile_data_key(profile_name, "sessions")
    sessions = config.get(session_key, [])

    for session in sessions:
        if session.get("id") == new_session_id:
            session["resumed_from"] = session_id
            break

    config[session_key] = sessions
    save_config(config)

    return new_session_id


def generate_session_summary(session_id: str):
    """Generate a summary dict for a session."""
    session = get_session(session_id)
    if not session:
        return None

    return {
        "session_id": session.get("id", "N/A"),
        "start_time": session.get("start_time", "N/A"),
        "end_time": session.get("end_time", "N/A"),
        "duration_minutes": session.get("duration_minutes", 0),
        "quizzes_taken": session.get("quizzes_taken", 0),
        "notes_viewed": session.get("notes_viewed", 0),
        "ai_chats": session.get("ai_chats", 0),
        "verse_sessions": session.get("verse_sessions", 0),
        "tutorials_completed": session.get("tutorials_completed", 0),
        "total_activities": len(session.get("activities", [])),
        "resumed_from": session.get("resumed_from", None),
    }


def _get_profile_data_key(profile_name: str, key: str) -> str:
    """Get the config key for profile-specific data."""
    return f"profile_{profile_name}_{key}"


@contextmanager
def _file_lock(filepath: Path):
    """Acquire an exclusive lock on a file. Cross-platform compatible."""
    lock_path = filepath.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield lock_file
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def _save_config_atomic(config: dict, path: Path) -> None:
    """Save config atomically using temp file + os.replace().

    This prevents corruption if the process crashes during write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to temp file in same directory (same filesystem for atomic rename)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=".settings_tmp_",
        suffix=".json",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_f:
            json.dump(config, tmp_f, indent=2, ensure_ascii=False)
            tmp_f.flush()
            os.fsync(tmp_f.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def get_active_profile():
    """Get the active user profile."""
    config = load_config()
    profile_name = config.get("active_profile", "default")
    profiles = config.get("profiles", {})
    return profiles.get(profile_name, {"name": "Default User"})


def get_active_profile_name():
    """Get the active profile name string."""
    config = load_config()
    return config.get("active_profile", "default")


def list_profiles():
    """List all user profiles."""
    config = load_config()
    return config.get("profiles", {})


def create_profile(name: str, display_name: str) -> Dict:
    """Create a new user profile."""
    from datetime import datetime

    config = load_config()
    profiles = config.get("profiles", {})

    if name in profiles:
        return None  # Already exists

    profiles[name] = {
        "name": display_name,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    config["profiles"] = profiles
    save_config(config)
    return profiles[name]


def switch_profile(name: str) -> bool:
    """Switch to a different user profile."""
    config = load_config()
    profiles = config.get("profiles", {})

    if name not in profiles:
        return False

    config["active_profile"] = name
    save_config(config)
    return True


def get_profile_value(profile_name: str, key: str, default=None):
    """Get a profile-scoped value from config."""
    config = load_config()
    data_key = _get_profile_data_key(profile_name, key)
    return config.get(data_key, config.get(key, default))


def set_profile_value(profile_name: str, key: str, value):
    """Set a profile-scoped value in config."""
    config = load_config()
    data_key = _get_profile_data_key(profile_name, key)
    config[data_key] = value
    save_config(config)


def migrate_to_profiles():
    """Migrate root-level data to the default profile if not already done."""
    config = load_config()
    profile_name = "default"

    # Check if migration already done
    migration_key = f"profile_{profile_name}_migrated"
    if config.get(migration_key):
        return

    # Migrate each profile-scoped key
    for key in _PROFILE_KEYS:
        if key in config:
            data_key = _get_profile_data_key(profile_name, key)
            config[data_key] = config[key]

    config[migration_key] = True
    save_config(config)


def get_profiled_config():
    """Get config with profile-scoped data resolved.
    Returns a merged config where profile keys override root keys."""
    config = load_config()
    profile_name = config.get("active_profile", "default")

    merged = config.copy()
    for key in _PROFILE_KEYS:
        data_key = _get_profile_data_key(profile_name, key)
        if data_key in config:
            merged[key] = config[data_key]
        elif key not in merged:
            # Apply defaults
            if key == "study_streak":
                merged[key] = {"current": 0, "best": 0, "last_study_date": None}
            elif key == "daily_goal":
                merged[key] = {"today_date": None, "minutes_studied": 0}
            elif key == "review_queue":
                merged[key] = {}
            elif key in ("learning_progress", "bookmarks", "achievements", "tutorial_progress"):
                merged[key] = {} if key != "bookmarks" else []
            elif key == "timed_quiz_best":
                merged[key] = 0
            elif key == "verse_progress":
                merged[key] = {
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
                    "lore_unlocked": [],
                    "speedrun_records": {},
                    "daily_challenge": None,
                    "npc_memory": {},
                    "secrets_found": [],
                    "session_stats": {"total_sessions": 0, "total_time": 0, "total_correct": 0, "total_wrong": 0, "history": []},
                    "streak_calendar": {},
                    "prestige_level": 0,
                    "prestige_bonus": 0,
                    "custom_questions": [],
                    "mentor_active": False,
                    "world_themes": {},
                    "quote_index": 0,
                    "journal": {},
                    "sound_enabled": True,
                    "daily_challenge_best": 0,
                }

    return merged
