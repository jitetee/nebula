#!/usr/bin/env python3
"""
Content Loader Module — Load learning materials from .ksl package files

All content is packaged into .ksl (KSLearn Package) files.
These are encrypted, signed packages that only the creator can build.
Users can load and study but cannot edit or forge packages.
"""

import base64
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# ─── Data Directory ──────────────────────────────────────────────────
# ALL .ksl content packages live in one flat folder: data/ksl/
# .ksl files are self-describing (header tells their type).
# Config stays in data/config/ (user prefs, not content).
#
# Platform-specific resolution:
#   - If running from cloned repo (editable install): uses repo/data/ksl/
#   - On Windows user install: uses %APPDATA%/kslearn/data/ksl/
#   - On Linux/macOS user install: uses ~/.local/share/kslearn/data/ksl/

def _get_platform_data_dir():
    """Resolve user-specific data directory per platform."""
    import sys
    if sys.platform == "win32":
        # Windows: %APPDATA%\kslearn\data\ksl
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return appdata / "kslearn" / "data"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/kslearn/data
        return Path.home() / "Library" / "Application Support" / "kslearn" / "data"
    else:
        # Linux/Android/Termux: ~/.local/share/kslearn/data
        xdg = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return xdg / "kslearn" / "data"

def _resolve_data_dir():
    """
    Return the data directory.
    Priority: repo-adjacent data/  >  platform user data dir.
    This lets editable installs (pip install -e .) use the repo's data/
    while standalone installs use proper OS paths.
    """
    repo_data = Path(__file__).parent.parent / "data"
    # If repo has a data/ folder, prefer it (editable install)
    if (repo_data / "ksl").exists() or repo_data.exists():
        return repo_data
    # Otherwise fall back to platform-specific user data dir
    return _get_platform_data_dir()

DATA_DIR = _resolve_data_dir()
KSL_DIR = DATA_DIR / "ksl"
CONFIG_DIR = DATA_DIR / "config"

# Backwards-compat aliases (point to KSL_DIR)
NOTES_DIR = KSL_DIR
QUIZZES_DIR = KSL_DIR
SNIPPETS_DIR = KSL_DIR
BRAIN_DIR = KSL_DIR

# ─── Import KSL loader ──────────────────────────────────────────────
from kslearn.ksl_loader import KSLLoader, load_ksl_file, get_ksl_info
from kslearn.ksl_loader import (
    extract_notes, extract_quiz_topics, extract_quiz_metadata,
    extract_flashcards, extract_tutorials, extract_brain_qa,
    extract_combined_content, get_ksl_metadata, get_ksl_content_type,
    has_notes, has_quiz, has_flashcards, has_tutorials, has_brain,
    extract_hierarchical_courses, extract_hierarchical_data, has_hierarchical,
    extract_course_metadata, extract_unit_metadata, extract_outcome_metadata,
    extract_subtopic_metadata, format_duration, difficulty_icon,
)

# Re-export content type constants for use in loader.py methods
TYPE_NOTES = "notes"
TYPE_QUIZ = "quiz"
TYPE_FLASHCARD = "flashcard"
TYPE_TUTORIAL = "tutorial"
TYPE_BRAIN = "brain"
TYPE_COMBINED = "combined"
TYPE_HIERARCHICAL = "hierarchical"


class ContentLoader:
    """Load and manage learning content from .ksl package files"""

    def __init__(self):
        self._cache = {}
        self._pending_activation = None
        self._ksl_loader = KSLLoader()
        self._dir_mtime = {}
        self._ensure_directories()

    def _ensure_directories(self):
        """Create data directories if they don't exist"""
        KSL_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # ─── Discovery Methods ───────────────────────────────────────

    def _discover_ksl_files(self, directory: Path = None) -> List[Path]:
        """Find all .ksl files in data/ksl/. Auto-detects new files and clears cache."""
        target = directory or KSL_DIR
        # Check if directory contents changed (new/removed .ksl files)
        if target.exists():
            import os
            try:
                stat = os.stat(target)
                current_mtime = stat.st_mtime
                prev_mtime = self._dir_mtime.get(str(target))
                if prev_mtime is not None and current_mtime != prev_mtime:
                    # Directory changed — clear file-level caches
                    self._cache.clear()
                    self._ksl_loader.clear_cache()
                self._dir_mtime[str(target)] = current_mtime
            except OSError:
                pass
        return self._ksl_loader.discover(target)

    def _load_ksl_data(self, ksl_path: Path) -> Optional[Dict]:
        """Load a .ksl file. Returns data or None if invalid."""
        try:
            result = self._ksl_loader.load(ksl_path)
            return result
        except Exception:
            return None

    def _validate_ksl_file(self, ksl_path: Path) -> Dict:
        """Check if a .ksl file is valid. Returns status dict."""
        from kslearn.ksl_loader import get_ksl_info, parse_ksl_header, HEADER_SIZE
        info = get_ksl_info(ksl_path)
        if info:
            # Verify header magic + JSON payload
            try:
                with open(ksl_path, "rb") as f:
                    file_data = f.read()
                hdr = file_data[:HEADER_SIZE]
                h = parse_ksl_header(hdr)
                if h is None:
                    return {"file": str(ksl_path), "valid": False, "error": "Invalid .ksl header"}
                payload_len = h["payload_length"]
                payload = file_data[HEADER_SIZE:HEADER_SIZE + payload_len]
                json.loads(payload.decode("utf-8"))
                return {"file": str(ksl_path), "valid": True, "type": h["type"], "title": h["title"]}
            except Exception as e:
                return {"file": str(ksl_path), "valid": False, "error": f"Invalid file format: {e}"}
        return {"file": str(ksl_path), "valid": False, "error": "Cannot read file"}

    # ─── Notes Methods ───────────────────────────────────────────

    def load_notes(self, category: str) -> Optional[Dict]:
        """
        Load learning notes for a category from .ksl files.

        Searches content.ksl (combined) and individual .ksl in NOTES_DIR.
        """
        cache_key = f"notes:{category}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        all_topics = []
        merged_metadata = {}
        category_lower = category.lower()

        # Load from .ksl files in data/
        for ksl_file in self._discover_ksl_files():
            data = self._load_ksl_data(ksl_file)
            if not data:
                continue
            meta = get_ksl_metadata(data)
            ctype = get_ksl_content_type(data)

            # If combined package, extract notes
            if ctype == TYPE_COMBINED:
                combined = extract_combined_content(data)
                topics = combined.get("notes", [])
            else:
                topics = extract_notes(data)

            pkg_cat = meta.get("category", "").lower()
            pkg_title = meta.get("title", "").lower()
            file_stem = ksl_file.stem.lower()

            if pkg_cat == category_lower or file_stem == category_lower or category_lower in pkg_title:
                if not merged_metadata:
                    merged_metadata = {
                        "category": meta.get("category", category),
                        "title": meta.get("title", category),
                        "description": meta.get("description", ""),
                        "icon": meta.get("icon", "📖"),
                        "difficulty": meta.get("difficulty", "beginner"),
                        "version": meta.get("version", "1.0"),
                        "source_ksl": str(ksl_file),
                    }
                base_id = len(all_topics)
                for i, topic in enumerate(topics):
                    topic_copy = dict(topic)
                    topic_copy["id"] = base_id + i + 1
                    topic_copy["_source"] = str(ksl_file)
                    all_topics.append(topic_copy)

        if not all_topics:
            return None

        result = {"metadata": merged_metadata, "topics": all_topics}
        self._cache[cache_key] = result
        return result

    def save_notes(self, category: str, notes: Dict) -> bool:
        """Saving is not supported for .ksl files — use ksl_tool.py to create packages."""
        return False

    def get_all_notes_categories(self) -> List[Dict[str, str]]:
        """Get all available notes categories from .ksl files in data/."""
        categories = []
        for ksl_file in self._discover_ksl_files():
            data = self._load_ksl_data(ksl_file)
            if not data:
                continue
            meta = get_ksl_metadata(data)
            ctype = get_ksl_content_type(data)
            if ctype == TYPE_COMBINED:
                combined = extract_combined_content(data)
                topics = combined.get("notes", [])
            else:
                topics = extract_notes(data)
            if topics:
                categories.append({
                    "key": ksl_file.stem,
                    "title": meta.get("title", ksl_file.stem.replace("_", " ").title()),
                    "description": meta.get("description", "Study materials"),
                    "icon": meta.get("icon", "📖"),
                    "topic_count": len(topics),
                    "source": str(ksl_file),
                })
        return sorted(categories, key=lambda x: x["title"])

    # ─── Quiz Methods ────────────────────────────────────────────

    def load_quiz(self, category: str) -> Optional[Dict]:
        """Load quiz for a category from .ksl files (combined or separate)."""
        cache_key = f"quiz:{category}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        all_quiz_topics = []
        merged_metadata = {}
        category_lower = category.lower()

        for ksl_file in self._discover_ksl_files():
            data = self._load_ksl_data(ksl_file)
            if not data:
                continue
            meta = get_ksl_metadata(data)
            ctype = get_ksl_content_type(data)

            if ctype == TYPE_COMBINED:
                combined = extract_combined_content(data)
                quiz_topics = combined.get("quiz_topics", [])
                quiz_meta = combined.get("quiz_metadata", {})
            else:
                quiz_topics = extract_quiz_topics(data)
                quiz_meta = extract_quiz_metadata(data)

            pkg_cat = meta.get("category", "").lower()
            pkg_title = meta.get("title", "").lower()
            file_stem = ksl_file.stem.lower()

            if pkg_cat == category_lower or file_stem == category_lower or category_lower in pkg_title:
                if not merged_metadata:
                    merged_metadata = {
                        "category": quiz_meta.get("category", meta.get("category", category)),
                        "title": quiz_meta.get("title", meta.get("title", category)),
                        "description": quiz_meta.get("description", meta.get("description", "")),
                        "icon": quiz_meta.get("icon", meta.get("icon", "📝")),
                        "difficulty": quiz_meta.get("difficulty", meta.get("difficulty", "beginner")),
                        "version": quiz_meta.get("version", meta.get("version", "1.0")),
                        "source_ksl": str(ksl_file),
                    }
                base_id = len(all_quiz_topics)
                for i, qt in enumerate(quiz_topics):
                    qt_copy = dict(qt)
                    qt_copy["id"] = base_id + i + 1
                    qt_copy["_source"] = str(ksl_file)
                    all_quiz_topics.append(qt_copy)

        if not all_quiz_topics:
            return None

        result = {"metadata": merged_metadata, "topics": all_quiz_topics}
        self._cache[cache_key] = result
        return result

    def load_quiz_strict(self, category: str) -> Dict:
        """Load quiz with strict error checking."""
        data = self.load_quiz(category)
        if data is None:
            raise FileNotFoundError(
                f"Quiz data not found for '{category}'. "
                f"Please add a .ksl quiz file to {QUIZZES_DIR}."
            )
        return data

    def save_quiz(self, category: str, quiz: Dict) -> bool:
        """Saving is not supported for .ksl files — use ksl_tool.py to create packages."""
        return False

    def get_all_quiz_categories(self) -> List[Dict[str, str]]:
        """Get all available quiz categories from .ksl files in data/."""
        categories = []
        for ksl_file in self._discover_ksl_files():
            data = self._load_ksl_data(ksl_file)
            if not data:
                continue
            meta = get_ksl_metadata(data)
            ctype = get_ksl_content_type(data)
            if ctype == TYPE_COMBINED:
                combined = extract_combined_content(data)
                quiz_topics = combined.get("quiz_topics", [])
            else:
                quiz_topics = extract_quiz_topics(data)
            if quiz_topics:
                categories.append({
                    "key": ksl_file.stem,
                    "title": meta.get("title", ksl_file.stem.replace("_", " ").title()),
                    "description": meta.get("description", "Quiz materials"),
                    "icon": meta.get("icon", "📝"),
                    "topic_count": len(quiz_topics),
                    "source": str(ksl_file),
                })
        return sorted(categories, key=lambda x: x["title"])

    # ─── Flashcard Methods ───────────────────────────────────────

    def get_all_flashcard_categories(self) -> List[Dict[str, str]]:
        """Get all flashcard categories from .ksl files in data/."""
        categories = []
        for ksl_file in self._discover_ksl_files():
            data = self._load_ksl_data(ksl_file)
            if not data:
                continue
            ctype = get_ksl_content_type(data)
            if ctype == TYPE_COMBINED:
                combined = extract_combined_content(data)
                cards = combined.get("flashcards", [])
            else:
                cards = extract_flashcards(data)
            if cards:
                meta = get_ksl_metadata(data)
                categories.append({
                    "key": ksl_file.stem,
                    "title": meta.get("title", ksl_file.stem.replace("_", " ").title()),
                    "description": meta.get("description", "Flashcards"),
                    "icon": meta.get("icon", "🃏"),
                    "card_count": len(cards),
                    "source": str(ksl_file),
                })
        return sorted(categories, key=lambda x: x["title"])

    # ─── Tutorial Methods ────────────────────────────────────────

    def get_all_tutorial_categories(self) -> List[Dict[str, str]]:
        """Get all tutorial categories from .ksl files in data/."""
        categories = []
        for ksl_file in self._discover_ksl_files():
            data = self._load_ksl_data(ksl_file)
            if not data:
                continue
            ctype = get_ksl_content_type(data)
            if ctype == TYPE_COMBINED:
                combined = extract_combined_content(data)
                tutorials = combined.get("tutorials", [])
            else:
                tutorials = extract_tutorials(data)
            if tutorials:
                meta = get_ksl_metadata(data)
                categories.append({
                    "key": ksl_file.stem,
                    "title": meta.get("title", ksl_file.stem.replace("_", " ").title()),
                    "description": meta.get("description", "Tutorials"),
                    "icon": meta.get("icon", "🎓"),
                    "tutorial_count": len(tutorials),
                    "source": str(ksl_file),
                })
        return sorted(categories, key=lambda x: x["title"])

    def load_tutorials(self, category: str) -> Optional[List[Dict]]:
        """Load tutorials for a category from .ksl files."""
        cache_key = f"tutorials:{category}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        all_tutorials = []
        category_lower = category.lower()

        for ksl_file in self._discover_ksl_files():
            data = self._load_ksl_data(ksl_file)
            if not data:
                continue
            meta = get_ksl_metadata(data)
            ctype = get_ksl_content_type(data)

            if ctype == TYPE_COMBINED:
                combined = extract_combined_content(data)
                tutorials = combined.get("tutorials", [])
            else:
                tutorials = extract_tutorials(data)

            pkg_cat = meta.get("category", "").lower()
            file_stem = ksl_file.stem.lower()
            if pkg_cat == category_lower or file_stem == category_lower or category_lower in meta.get("title", "").lower():
                all_tutorials.extend(tutorials)

        if not all_tutorials:
            return None

        self._cache[cache_key] = all_tutorials
        return all_tutorials

    def load_flashcards(self, category: str) -> Optional[List[Dict]]:
        """Load flashcards for a category from .ksl files."""
        cache_key = f"flashcards:{category}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        all_cards = []
        category_lower = category.lower()

        for ksl_file in self._discover_ksl_files():
            data = self._load_ksl_data(ksl_file)
            if not data:
                continue
            ctype = get_ksl_content_type(data)

            if ctype == TYPE_COMBINED:
                combined = extract_combined_content(data)
                cards = combined.get("flashcards", [])
            else:
                cards = extract_flashcards(data)

            meta = get_ksl_metadata(data)
            pkg_cat = meta.get("category", "").lower()
            file_stem = ksl_file.stem.lower()
            if pkg_cat == category_lower or file_stem == category_lower or category_lower in meta.get("title", "").lower():
                all_cards.extend(cards)

        if not all_cards:
            return None

        self._cache[cache_key] = all_cards
        return all_cards

    # ─── Brain Methods ───────────────────────────────────────────

    def load_brain_qa(self) -> List[Dict]:
        """Load brain Q&A pairs from brain.ksl file(s) in data/."""
        cache_key = "brain:qa"
        if cache_key in self._cache:
            return self._cache[cache_key]

        all_qa = []
        for ksl_file in self._discover_ksl_files():
            data = self._load_ksl_data(ksl_file)
            if not data:
                continue
            ctype = get_ksl_content_type(data)
            if ctype == TYPE_BRAIN:
                all_qa.extend(extract_brain_qa(data))

        self._cache[cache_key] = all_qa
        return all_qa

    def search_brain(self, query: str, limit: int = 10) -> List[Dict]:
        """Search brain Q&A by keyword."""
        qa_pairs = self.load_brain_qa()
        results = []
        query_lower = query.lower()
        for qa in qa_pairs:
            searchable = f"{qa.get('question', '')} {qa.get('answer', '')} {' '.join(qa.get('tags', []))}".lower()
            if query_lower in searchable:
                results.append(qa)
            if len(results) >= limit:
                break
        return results

    def get_brain_stats(self) -> Dict:
        """Get brain statistics."""
        qa_pairs = self.load_brain_qa()
        categories = set(qa.get("category", "general") for qa in qa_pairs)
        return {
            "total_qa_pairs": len(qa_pairs),
            "categories": sorted(categories),
            "total_conversations": 0,
            "last_updated": "N/A"
        }

    def get_all_brain_categories(self) -> List[str]:
        """Get all brain Q&A categories."""
        qa_pairs = self.load_brain_qa()
        return sorted(set(qa.get("category", "general") for qa in qa_pairs))

    def add_qa_to_brain(self, question: str, answer: str, category: str = "general",
                        tags: List[str] = None) -> bool:
        """Add a Q&A pair (for runtime learning — stored in brain.ksl if it exists)."""
        # Since brain.ksl is read-only, we store runtime additions separately
        # and merge them when searching
        qa_entry = {
            "question": question,
            "answer": answer,
            "category": category,
            "tags": tags or [],
            "created": datetime.now().isoformat(),
            "helpful_count": 0,
        }
        cache_key = "brain:qa_runtime"
        if cache_key not in self._cache:
            self._cache[cache_key] = []
        self._cache[cache_key].append(qa_entry)
        return True

    # ─── Config Methods ──────────────────────────────────────────

    def load_config(self, name: str = "settings") -> Optional[Dict]:
        """Load configuration file (JSON — config is not encrypted)."""
        config_path = CONFIG_DIR / f"{name}.json"
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_config(self, name: str, config: Dict) -> bool:
        """Save configuration file."""
        config_path = CONFIG_DIR / f"{name}.json"
        try:
            import json
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False

    # ─── Progress Tracking ───────────────────────────────────────

    def load_progress(self, user_id: str = "default") -> Dict:
        """Load user progress"""
        progress = self.load_config(f"progress_{user_id}")
        return progress or {
            "quizzes_completed": 0,
            "total_score": 0,
            "categories": {},
            "streak": 0,
            "last_study": None
        }

    def save_progress(self, user_id: str, progress: Dict) -> bool:
        """Save user progress"""
        progress["last_updated"] = datetime.now().isoformat()
        return self.save_config(f"progress_{user_id}", progress)

    # ─── KSL Package Management ──────────────────────────────────

    def list_ksl_packages(self) -> List[Dict]:
        """List all .ksl packages in the data directory with validation status."""
        packages = []
        for ksl_file in self._discover_ksl_files():
            status = self._validate_ksl_file(ksl_file)
            if status["valid"]:
                info = get_ksl_info(ksl_file)
                if info:
                    packages.append(info)
            else:
                packages.append({
                    "file": str(ksl_file),
                    "title": ksl_file.stem,
                    "type": "invalid",
                    "error": status.get("error", "Unknown error"),
                    "author": "unknown",
                })
        return packages

    def is_ksl_activated(self) -> bool:
        """All .ksl files are open — no activation required."""
        return True

    def clear_cache(self):
        """Clear all caches."""
        self._cache.clear()
        self._ksl_loader.clear_cache()

    # ─── Hierarchical Content Methods ────────────────────────────

    def load_hierarchical_courses(self) -> List[Dict]:
        """Load all courses from hierarchical .ksl files."""
        cache_key = "hierarchical:courses"
        if cache_key in self._cache:
            return self._cache[cache_key]

        all_courses = []
        for ksl_file in self._discover_ksl_files():
            data = self._load_ksl_data(ksl_file)
            if not data:
                continue
            ctype = get_ksl_content_type(data)
            if ctype == TYPE_HIERARCHICAL:
                courses = extract_hierarchical_courses(data)
                for course in courses:
                    course["_source"] = str(ksl_file)
                    all_courses.append(course)
            elif ctype == TYPE_COMBINED:
                combined = extract_combined_content(data)
                courses = combined.get("courses", [])
                for course in courses:
                    course["_source"] = str(ksl_file)
                    all_courses.append(course)

        self._cache[cache_key] = all_courses
        return all_courses

    def load_hierarchical_course(self, course_id: str) -> Optional[Dict]:
        """Load a specific course by ID."""
        courses = self.load_hierarchical_courses()
        for course in courses:
            if course.get("id") == course_id or course.get("code") == course_id:
                return course
            if course.get("title", "").lower() == course_id.lower():
                return course
        return None

    def get_all_hierarchical_courses(self) -> List[Dict[str, str]]:
        """Flat list of all hierarchical courses."""
        courses = self.load_hierarchical_courses()
        result = []
        for course in courses:
            result.append({
                "key": course.get("id", course.get("code", "")),
                "title": course.get("title", "Untitled Course"),
                "description": course.get("description", ""),
                "icon": course.get("icon", "📚"),
                "category": course.get("category", "general"),
                "unit_count": len(course.get("categories", [])),
                "source": course.get("_source", ""),
                "difficulty": course.get("difficulty", "beginner"),
                "estimated_minutes": course.get("estimated_minutes", 0),
                "credits": course.get("credits", 0),
                "tags": course.get("tags", []),
                "prerequisites": course.get("prerequisites", []),
                "version": course.get("version", "1.0"),
            })
        return sorted(result, key=lambda x: x["title"])

    # ─── Filtering & Prerequisite Methods ────────────────────────

    def filter_courses_by_difficulty(self, difficulty: str) -> List[Dict]:
        courses = self.get_all_hierarchical_courses()
        return [c for c in courses if c.get("difficulty", "beginner").lower() == difficulty.lower()]

    def filter_courses_by_tag(self, tag: str) -> List[Dict]:
        courses = self.get_all_hierarchical_courses()
        tag_lower = tag.lower()
        return [c for c in courses if any(tag_lower in t.lower() for t in c.get("tags", []))]

    def search_hierarchical(self, query: str) -> List[Dict]:
        results = []
        courses = self.load_hierarchical_courses()
        ql = query.lower()
        for course in courses:
            if ql in course.get("title", "").lower() or ql in course.get("description", "").lower():
                results.append({"type": "course", "data": course, "match": "course"})
                continue
            for cat in course.get("categories", []):
                if ql in cat.get("title", "").lower():
                    results.append({"type": "category", "data": cat, "course": course, "match": "category"})
                    continue
                for unit in cat.get("units", []):
                    if ql in unit.get("title", "").lower() or ql in unit.get("description", "").lower():
                        results.append({"type": "unit", "data": unit, "course": course, "category": cat, "match": "unit"})
                        continue
                    for outcome in unit.get("learning_outcomes", []):
                        if ql in outcome.get("title", "").lower():
                            results.append({"type": "outcome", "data": outcome, "course": course, "unit": unit, "match": "outcome"})
                            continue
                        for sub in outcome.get("subtopics", []):
                            searchable = f"{sub.get('title', '')} {sub.get('content', '')}".lower()
                            if ql in searchable:
                                results.append({"type": "subtopic", "data": sub, "course": course, "outcome": outcome, "match": "content"})
        return results

    def check_prerequisites(self, course: Dict, completed: Dict) -> Dict:
        prereqs = course.get("prerequisites", [])
        if not prereqs:
            return {"met": True, "missing": [], "message": "No prerequisites required"}
        missing = [p for p in prereqs if p not in completed]
        if missing:
            return {"met": False, "missing": missing, "message": f"Prerequisites required: {', '.join(missing)}"}
        return {"met": True, "missing": [], "message": "All prerequisites met"}

    def calculate_total_duration(self, course: Dict) -> int:
        mins = course.get("estimated_minutes", 0)
        if mins > 0:
            return mins
        total = 0
        for cat in course.get("categories", []):
            for unit in cat.get("units", []):
                um = unit.get("estimated_minutes", 0)
                if um > 0:
                    total += um
                else:
                    for o in unit.get("learning_outcomes", []):
                        om = o.get("estimated_minutes", 0)
                        if om > 0:
                            total += om
                        else:
                            for s in o.get("subtopics", []):
                                total += s.get("estimated_minutes", 0)
        return total

    def get_course_stats(self, course: Dict) -> Dict:
        total_units = total_outcomes = total_subtopics = total_minutes = 0
        total_glossary = total_case = total_disc = total_media = 0
        for cat in course.get("categories", []):
            total_glossary += len(cat.get("glossary", []))
            total_case += len(cat.get("case_studies", []))
            total_disc += len(cat.get("discussion_prompts", []))
            for unit in cat.get("units", []):
                total_units += 1
                total_glossary += len(unit.get("glossary", []))
                total_case += len(unit.get("case_studies", []))
                total_disc += len(unit.get("discussion_prompts", []))
                total_media += len(unit.get("media", []))
                um = unit.get("estimated_minutes", 0)
                if um > 0:
                    total_minutes += um
                for o in unit.get("learning_outcomes", []):
                    total_outcomes += 1
                    total_disc += len(o.get("discussion_prompts", []))
                    total_case += len(o.get("case_studies", []))
                    for s in o.get("subtopics", []):
                        total_subtopics += 1
                        total_minutes += s.get("estimated_minutes", 0)
        return {
            "total_units": total_units, "total_outcomes": total_outcomes,
            "total_subtopics": total_subtopics, "estimated_minutes": total_minutes,
            "duration_formatted": format_duration(total_minutes),
            "difficulty": course.get("difficulty", "beginner"),
            "credits": course.get("credits", 0),
            "total_glossary_terms": total_glossary, "total_case_studies": total_case,
            "total_discussion_prompts": total_disc, "total_media_items": total_media,
            "tags": course.get("tags", []), "version": course.get("version", "1.0"),
        }

    # ─── Progression Gating — Level Locking ──────────────────────

    def is_unit_unlocked(self, unit: Dict, progress: Dict) -> Dict:
        """Check if a unit is unlocked based on prerequisites and previous unit completion.

        Returns:
            {"unlocked": bool, "reason": str, "locked_by": str}
        """
        # Check explicit prerequisites
        prereqs = unit.get("prerequisites", [])
        for prereq_id in prereqs:
            if prereq_id not in progress:
                return {"unlocked": False, "reason": f"Prerequisite not completed: {prereq_id}", "locked_by": prereq_id}
            p = progress[prereq_id]
            min_score = unit.get("completion_requirements", {}).get("prereq_min_score", 0)
            if min_score > 0 and p.get("last_accuracy", 0) < min_score:
                return {"unlocked": False, "reason": f"Prerequisite {prereq_id} requires {min_score}% (you scored {p.get('last_accuracy', 0):.0f}%)", "locked_by": prereq_id}

        return {"unlocked": True, "reason": "Available", "locked_by": None}

    def is_outcome_unlocked(self, outcome: Dict, unit_progress: Dict, outcome_index: int, total_outcomes: int) -> Dict:
        """Check if a learning outcome is unlocked (sequential locking + score gating).

        Rules:
        1. First outcome is always unlocked
        2. Next outcome requires previous outcome completed with min_score
        3. If must_complete_all is set, ALL previous outcomes must pass min_score
        """
        min_score = outcome.get("min_score", 0)
        must_all = outcome.get("must_complete_all", False)

        # First outcome — always available
        if outcome_index == 0:
            return {"unlocked": True, "reason": "Start here!", "locked_by": None}

        # Check previous outcome(s)
        prev_key = f"outcome_{outcome_index - 1}"
        if prev_key not in unit_progress:
            return {"unlocked": False, "reason": "Complete the previous outcome first", "locked_by": prev_key}

        prev = unit_progress[prev_key]
        prev_score = prev.get("last_accuracy", 0)
        prev_min = unit_progress.get(f"outcome_{outcome_index - 1}_min_score", min_score)

        if prev_score < prev_min:
            return {"unlocked": False, "reason": f"Previous outcome requires {prev_min}% (you scored {prev_score:.0f}%)", "locked_by": prev_key}

        # If must_complete_all, check ALL previous outcomes
        if must_all:
            for i in range(outcome_index):
                pk = f"outcome_{i}"
                if pk not in unit_progress:
                    return {"unlocked": False, "reason": f"Outcome {i+1} not yet completed", "locked_by": pk}
                if unit_progress[pk].get("last_accuracy", 0) < min_score:
                    return {"unlocked": False, "reason": f"Outcome {i+1} needs retake (below {min_score}%)", "locked_by": pk}

        return {"unlocked": True, "reason": "Available", "locked_by": None}

    def save_outcome_progress(self, config: Dict, unit_key: str, outcome_index: int, outcome: Dict, score: int, total: int, accuracy: float):
        """Save learning outcome progress to config."""
        from kslearn.config import save_config
        if "learning_progress" not in config:
            config["learning_progress"] = {}

        pkey = f"outcome_{outcome_index}"
        config["learning_progress"][pkey] = {
            "last_score": score,
            "last_accuracy": accuracy,
            "completed_at": __import__("time").time(),
            "outcome_id": outcome.get("id", ""),
            "outcome_title": outcome.get("title", ""),
            "unit_key": unit_key,
            "questions": total,
            "correct": score,
        }
        config["learning_progress"][f"{pkey}_min_score"] = outcome.get("min_score", 0)
        save_config(config)

    def save_unit_progress(self, config: Dict, unit_key: str, unit: Dict, accuracy: float, score: int):
        """Save unit completion progress."""
        from kslearn.config import save_config
        if "learning_progress" not in config:
            config["learning_progress"] = {}

        config["learning_progress"][unit_key] = {
            "last_score": score,
            "last_accuracy": accuracy,
            "completed_at": __import__("time").time(),
            "unit_id": unit.get("id", ""),
            "unit_title": unit.get("title", ""),
        }
        save_config(config)


# ─── Global instance ────────────────────────────────────────────────
content_loader = ContentLoader()

# ─── Convenience functions ──────────────────────────────────────────

def load_notes(category: str) -> Optional[Dict]:
    return content_loader.load_notes(category)


def load_quiz(category: str) -> Optional[Dict]:
    return content_loader.load_quiz(category)


def load_flashcards(category: str) -> Optional[List[Dict]]:
    return content_loader.load_flashcards(category)


def load_tutorials(category: str) -> Optional[List[Dict]]:
    return content_loader.load_tutorials(category)


def load_brain_qa() -> List[Dict]:
    return content_loader.load_brain_qa()


def search_brain(query: str, limit: int = 10) -> List[Dict]:
    return content_loader.search_brain(query, limit)


def get_brain_stats() -> Dict:
    return content_loader.get_brain_stats()


# ─── Hierarchical Convenience Functions ─────────────────────────

def load_hierarchical_courses() -> List[Dict]:
    return content_loader.load_hierarchical_courses()


def load_hierarchical_course(course_id: str) -> Optional[Dict]:
    return content_loader.load_hierarchical_course(course_id)


def get_all_hierarchical_courses() -> List[Dict[str, str]]:
    return content_loader.get_all_hierarchical_courses()


def filter_courses_by_difficulty(difficulty: str) -> List[Dict]:
    return content_loader.filter_courses_by_difficulty(difficulty)


def filter_courses_by_tag(tag: str) -> List[Dict]:
    return content_loader.filter_courses_by_tag(tag)


def search_hierarchical(query: str) -> List[Dict]:
    return content_loader.search_hierarchical(query)


def check_prerequisites(course: Dict, completed: Dict) -> Dict:
    return content_loader.check_prerequisites(course, completed)


def calculate_course_duration(course: Dict) -> int:
    return content_loader.calculate_total_duration(course)


def get_course_stats(course: Dict) -> Dict:
    return content_loader.get_course_stats(course)


def is_unit_unlocked(unit: Dict, progress: Dict) -> Dict:
    return content_loader.is_unit_unlocked(unit, progress)


def is_outcome_unlocked(outcome: Dict, unit_progress: Dict, outcome_index: int, total_outcomes: int) -> Dict:
    return content_loader.is_outcome_unlocked(outcome, unit_progress, outcome_index, total_outcomes)

