"""
jtlearn Learning Engines
Centralized engines for quizzes, notes, achievements, and learning tracking
"""

from jtlearn.engines.quiz_engine import QuizEngine, run_quiz_interactive
from jtlearn.engines.notes_viewer import NotesViewer, run_notes_interactive
from jtlearn.engines.achievements import check_achievements, get_achievement_summary, ACHIEVEMENTS
from jtlearn.engines.verse_engine import VerseEngine, run_verse_interactive
from jtlearn.engines.rage_bait import run_rage_bait

__all__ = [
    "QuizEngine",
    "run_quiz_interactive",
    "NotesViewer",
    "run_notes_interactive",
    "check_achievements",
    "get_achievement_summary",
    "ACHIEVEMENTS",
    "VerseEngine",
    "run_verse_interactive",
    "run_rage_bait",
]
