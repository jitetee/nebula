"""
kslearn Learning Engines
Centralized engines for quizzes, notes, achievements, and learning tracking
"""

from kslearn.engines.quiz_engine import QuizEngine, run_quiz_interactive
from kslearn.engines.notes_viewer import NotesViewer, run_notes_interactive
from kslearn.engines.achievements import check_achievements, get_achievement_summary, ACHIEVEMENTS
from kslearn.engines.verse_engine import VerseEngine, run_verse_interactive

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
]
