#!/usr/bin/env python3
"""
KSL File Loader — Load .ksl (KSLearn Package) files

.k sl files are simple: a 128-byte binary header followed by plain JSON.
No encryption. Author credentials in the header are verified before loading.
Files not authored by kslearn are rejected.
"""

import json
import struct
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# ─── Constants ──────────────────────────────────────────────────────
KSL_MAGIC = b"KSL\x01"
HEADER_SIZE = 128

# Content types — includes hierarchical type
TYPE_NOTES = "notes"
TYPE_QUIZ = "quiz"
TYPE_FLASHCARD = "flashcard"
TYPE_TUTORIAL = "tutorial"
TYPE_BRAIN = "brain"
TYPE_COMBINED = "combined"
TYPE_HIERARCHICAL = "hierarchical"  # Course → Category → Unit → Learning Outcome → Sub-topic → Content


def _unpack_string(data: bytes) -> str:
    return data.split(b"\x00")[0].decode("utf-8", errors="replace").strip()


def parse_ksl_header(header: bytes) -> Optional[Dict]:
    """Parse the 128-byte header. Returns None if invalid."""
    if len(header) < HEADER_SIZE or header[0:4] != KSL_MAGIC:
        return None
    author_cred = _unpack_string(header[88:124])
    return {
        "version": struct.unpack_from(">I", header, 4)[0],
        "type": _unpack_string(header[8:24]),
        "title": _unpack_string(header[24:56]),
        "author": _unpack_string(header[56:72]),
        "created": datetime.fromtimestamp(
            struct.unpack_from(">Q", header, 72)[0]
        ).strftime("%Y-%m-%d %H:%M:%S"),
        "payload_length": struct.unpack_from(">Q", header, 80)[0],
        "content_count": struct.unpack_from(">I", header, 124)[0],
        "author_cred": author_cred,
    }


def load_ksl_file(ksl_path: Path) -> Optional[Dict]:
    """
    Load a .ksl file. Accepts any valid .ksl package regardless of author.
    Returns None only if the file is structurally invalid.
    """
    ksl_path = Path(ksl_path)
    if not ksl_path.exists():
        return None
    try:
        with open(ksl_path, "rb") as f:
            file_data = f.read()
        header_bytes = file_data[:HEADER_SIZE]
        header_info = parse_ksl_header(header_bytes)
        if not header_info:
            return None

        payload_len = header_info["payload_length"]
        json_payload = file_data[HEADER_SIZE:HEADER_SIZE + payload_len]
        return json.loads(json_payload.decode("utf-8"))
    except Exception:
        return None


def get_ksl_info(ksl_path: Path) -> Optional[Dict]:
    """Get header info from a .ksl file (no JSON parsing needed)."""
    ksl_path = Path(ksl_path)
    if not ksl_path.exists():
        return None
    try:
        with open(ksl_path, "rb") as f:
            header = f.read(HEADER_SIZE)
        info = parse_ksl_header(header)
        if info:
            info["file"] = str(ksl_path)
            info["file_size"] = ksl_path.stat().st_size
            info["author_cred"] = info.get("author_cred", "none")
        return info
    except Exception:
        return None


# ─── Content Extraction Helpers ─────────────────────────────────────

def extract_notes(d): return d.get("content", {}).get("notes", [])
def extract_quiz_topics(d): return d.get("content", {}).get("quiz_topics", [])
def extract_quiz_metadata(d): return d.get("content", {}).get("quiz_metadata", {})
def extract_flashcards(d): return d.get("content", {}).get("flashcards", [])
def extract_tutorials(d): return d.get("content", {}).get("tutorials", [])
def extract_brain_qa(d): return d.get("content", {}).get("brain_qa", [])

def extract_combined_content(ksl_data: Dict) -> Dict:
    c = ksl_data.get("content", {})
    return {
        "notes": c.get("notes", []),
        "quiz_topics": c.get("quiz_topics", []),
        "quiz_metadata": c.get("quiz_metadata", {}),
        "flashcards": c.get("flashcards", []),
        "tutorials": c.get("tutorials", []),
    }

def get_ksl_metadata(d): return d.get("metadata", {})
def get_ksl_content_type(d): return d.get("metadata", {}).get("content_type", "notes")
def has_notes(d): return bool(extract_notes(d))
def has_quiz(d): return bool(extract_quiz_topics(d))
def has_flashcards(d): return bool(extract_flashcards(d))
def has_tutorials(d): return bool(extract_tutorials(d))
def has_brain(d): return bool(extract_brain_qa(d))


# ─── Hierarchical Content Extraction ────────────────────────────────

def extract_hierarchical_courses(d: Dict) -> List[Dict]:
    """Extract top-level courses from hierarchical .ksl data."""
    content = d.get("content", {})
    return content.get("courses", [])


def extract_hierarchical_data(d: Dict) -> Dict:
    """Extract full hierarchical structure from .ksl data."""
    content = d.get("content", {})
    return {
        "courses": content.get("courses", []),
        "metadata": content.get("metadata", d.get("metadata", {})),
    }


def has_hierarchical(d: Dict) -> bool:
    """Check if .ksl data contains hierarchical content."""
    return bool(extract_hierarchical_courses(d))


# ─── Extended Hierarchical Field Extractors ─────────────────────────

def extract_course_metadata(course: Dict) -> Dict:
    """Extract enriched metadata from a course dict."""
    return {
        "prerequisites": course.get("prerequisites", []),
        "estimated_minutes": course.get("estimated_minutes", 0),
        "difficulty": course.get("difficulty", "beginner"),
        "credits": course.get("credits", 0),
        "tags": course.get("tags", []),
        "completion_requirements": course.get("completion_requirements", {}),
        "instructor_notes": course.get("instructor_notes", ""),
        "glossary": course.get("glossary", []),
        "media": course.get("media", []),
        "resources": course.get("resources", []),
        "learning_styles": course.get("learning_styles", []),
        "version": course.get("version", "1.0"),
        "changelog": course.get("changelog", ""),
    }


def extract_unit_metadata(unit: Dict) -> Dict:
    """Extract enriched metadata from a unit dict."""
    return {
        "prerequisites": unit.get("prerequisites", []),
        "estimated_minutes": unit.get("estimated_minutes", 0),
        "difficulty": unit.get("difficulty", "beginner"),
        "tools": unit.get("tools", []),
        "equipment": unit.get("equipment", []),
        "supplies": unit.get("supplies", []),
        "completion_requirements": unit.get("completion_requirements", {}),
        "instructor_notes": unit.get("instructor_notes", ""),
        "glossary": unit.get("glossary", []),
        "case_studies": unit.get("case_studies", []),
        "media": unit.get("media", []),
        "resources": unit.get("resources", []),
        "learning_styles": unit.get("learning_styles", []),
        "discussion_prompts": unit.get("discussion_prompts", []),
    }


def extract_outcome_metadata(outcome: Dict) -> Dict:
    """Extract enriched metadata from a learning outcome dict."""
    return {
        "estimated_minutes": outcome.get("estimated_minutes", 0),
        "difficulty": outcome.get("difficulty", "beginner"),
        "min_score": outcome.get("min_score", 0),
        "must_complete_all": outcome.get("must_complete_all", False),
        "discussion_prompts": outcome.get("discussion_prompts", []),
        "case_studies": outcome.get("case_studies", []),
        "media": outcome.get("media", []),
    }


def extract_subtopic_metadata(subtopic: Dict) -> Dict:
    """Extract enriched metadata from a sub-topic dict."""
    return {
        "estimated_minutes": subtopic.get("estimated_minutes", 0),
        "difficulty": subtopic.get("difficulty", "beginner"),
        "learning_styles": subtopic.get("learning_styles", []),
        "media": subtopic.get("media", []),
        "resources": subtopic.get("resources", []),
        "discussion_prompts": subtopic.get("discussion_prompts", []),
    }


def format_duration(minutes: int) -> str:
    """Format minutes into human-readable duration string."""
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def difficulty_icon(difficulty: str) -> str:
    """Return emoji icon for difficulty level."""
    icons = {
        "beginner": "🟢",
        "intermediate": "🟡",
        "advanced": "🔴",
        "expert": "⚫",
    }
    return icons.get(difficulty.lower(), "🔵")


# ─── Cache ──────────────────────────────────────────────────────────

class KSLLoader:
    def __init__(self, key: str = None):
        self._cache: Dict[str, Dict] = {}
        self._info_cache: Dict[str, Dict] = {}

    def load(self, ksl_path: Path) -> Optional[Dict]:
        cache_key = str(ksl_path)
        if cache_key in self._cache:
            return self._cache[cache_key]
        data = load_ksl_file(ksl_path)
        if data:
            self._cache[cache_key] = data
        return data

    def info(self, ksl_path: Path) -> Optional[Dict]:
        cache_key = str(ksl_path)
        if cache_key in self._info_cache:
            return self._info_cache[cache_key]
        info = get_ksl_info(ksl_path)
        if info:
            self._info_cache[cache_key] = info
        return info

    def discover(self, directory: Path) -> List[Path]:
        """Discover all .ksl files in a directory.

        Uses a single glob pattern — no redundant glob calls.
        """
        directory = Path(directory)
        if not directory.exists():
            return []
        return sorted(f.resolve() for f in directory.glob("*.ksl"))

    def discover_all(self, directories: List[Path]) -> List[Path]:
        files = []
        for d in directories:
            files.extend(self.discover(d))
        return sorted(set(files))

    def load_all(self, directory: Path) -> List[Dict]:
        results = []
        for f in self.discover(directory):
            data = self.load(f)
            if data:
                results.append(data)
        return results

    def clear_cache(self):
        self._cache.clear()
        self._info_cache.clear()
