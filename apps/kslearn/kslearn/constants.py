"""
Centralized Constants for kslearn

All content type constants, menu definitions, and shared constants.
Import from here instead of duplicating across files.
"""

# ─── Content Type Constants ───────────────────────────────────────
TYPE_NOTES = "notes"
TYPE_QUIZ = "quiz"
TYPE_FLASHCARD = "flashcard"
TYPE_TUTORIAL = "tutorial"
TYPE_BRAIN = "brain"
TYPE_HIERARCHICAL = "hierarchical"
TYPE_COMBINED = "combined"

# Human-readable labels for content types
CONTENT_TYPE_LABELS = {
    TYPE_NOTES: "Study Notes",
    TYPE_QUIZ: "Quiz",
    TYPE_FLASHCARD: "Flashcards",
    TYPE_TUTORIAL: "Tutorial",
    TYPE_BRAIN: "Knowledge Brain",
    TYPE_HIERARCHICAL: "Hierarchical Course",
    TYPE_COMBINED: "Combined Content",
}

# ─── Menu Structure Definitions ──────────────────────────────────

MAIN_MENU = [
    ("1", "📂 Course Catalog", "Hierarchical courses with progression & AI tutor"),
    ("2", "📚 Study Notes", "Browse comprehensive learning materials"),
    ("3", "📝 Take Quiz", "Test your knowledge"),
    ("4", "🌌 KSL-Verse", "Interactive multiverse learning game"),
    ("5", "🤖 AI Chat", "Chat with AI tutor (online & offline)"),
    ("6", "📊 My Progress", "Analytics, achievements, quiz scores & export"),
    ("7", "🔖 Study Tools", "Bookmarks, global search & spaced review"),
    ("8", "🧠 Knowledge Brain", "Offline AI Q&A database"),
    ("9", "🏪 Data Store", "Download new content (Free & Premium)"),
    ("F", "🎮 Study Modes", "Flashcards, timed quiz & tutorials"),
    ("L", "🏆 LearnQuest", "Answer quiz → JSON → submit & win rewards"),
    ("P", "👤 Profile & Account", "Manage profile, online login, friends"),
    ("O", "🌐 Online Hub", "Friends, leaderboards, share worlds"),
    ("S", "⚙️  Settings", "Configure your experience"),
    ("H", "❤️  Support", "Credits, social links & help"),
    ("0", "❌ Exit", "Leave kslearn"),
]

# Sub-menu for Profile (P)
PROFILE_MENU = [
    ("1", "👤 View Profile", "See your stats and progress"),
    ("2", "✏️  Edit Profile", "Update username and settings"),
    ("3", "🔑 Online Login", "Sign in to Firebase account"),
    ("4", "📝 Online Signup", "Create a new cloud account"),
    ("5", "🔄 Sync Data", "Sync progress to/from cloud"),
    ("6", "👥 Manage Friends", "Add/remove friends online"),
    ("7", "🏆 View Leaderboard", "See global rankings"),
    ("B", "⬅️  Back", "Return to main menu"),
]

# Sub-menu for Study Modes (F)
STUDY_MODES_MENU = [
    ("1", "🃏 Flashcards", "Quick review with flashcard mode"),
    ("2", "⏱️  Timed Quiz", "Race against the clock"),
    ("3", "🎓 Tutorials", "Step-by-step guided lessons"),
    ("B", "⬅️  Back", "Return to main menu"),
]

# Sub-menu for Study Tools (6)
STUDY_TOOLS_MENU = [
    ("1", "🔖 Bookmarks", "Manage your bookmarked topics"),
    ("2", "🔍 Global Search", "Search across all content"),
    ("3", "📅 Spaced Review", "Review topics at optimal intervals"),
    ("B", "⬅️  Back", "Return to main menu"),
]

# ─── Version ──────────────────────────────────────────────────────
VERSION = "2.0.0"
APP_NAME = "kslearn"
AUTHOR = "KashSight Platform"
LICENSE = "MIT"

# ─── Navigation Breadcrumb Separator ─────────────────────────────
BREADCRUMB_SEP = " > "
