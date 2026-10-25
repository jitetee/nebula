# 📖 jtlearn User Guide

> **Your complete reference for navigating and mastering jtlearn.**

<p align="center">
  <sub>📘 User Guide • Version 2.0 • jtlearn 2.0.0</sub>
</p>

---

## 📋 Table of Contents

- [🚀 Launch](#-launch)
- [📋 Main Menu](#-main-menu)
- [📊 My Progress](#-my-progress-option-5--p)
- [🔖 Study Tools](#-study-tools-option-6--t)
- [🎮 Study Modes](#-study-modes-option-f--m)
- [📂 Course Catalog Features](#-course-catalog-features)
- [🔥 AI-Powered Suggestions](#-ai-powered-suggestions)
- [🎨 Themes](#-themes)
- [⌨️ Shortcut Key Reference](#%EF%B8%8F-shortcut-key-reference)
- [🏪 Data Store](#-data-store)
- [📊 Progress Tracking Keys](#-progress-tracking-keys)

---

## 🚀 Launch

```bash
jtlearn
```

> 💡 **Tip:** Run `jtlearn verse` to launch JT-Verse directly.

---

## 📋 Main Menu

| # | Option | Shortcut | Description |
|:---:|:---|:---:|:---|
| 1 | 📂 Course Catalog | `1` / `CC` | 6-level hierarchical courses with progression gating, AI tutor, mark-as-complete |
| 2 | 📚 Study Notes | `2` / `N` | Browse comprehensive learning materials with reading time tracking |
| 3 | 📝 Take Quiz | `3` / `Q` | Test your knowledge with interactive quizzes |
| 4 | 🤖 AI Chat | `4` | Chat with AI tutor — 11 providers, offline & online modes |
| 5 | 📊 My Progress | `5` / `P` | **Merged:** Analytics dashboard, quiz scores, achievements, export report |
| 6 | 🔖 Study Tools | `6` / `T` | **Merged:** Bookmarks, global search, spaced review |
| 7 | 🧠 Knowledge Brain | `7` / `B` | Offline AI Q&A database with auto-save |
| 8 | 🏪 Data Store | `8` | Download free & premium courses |
| S | ❤️ Support | `S` | Credits, email, website & GitHub |
| F | 🎮 Study Modes | `F` / `M` | **Merged:** Flashcards, timed quiz, tutorials |
| D | 👤 Profiles | `D` | Switch or manage user profiles |
| C | ⚙️ Settings | `C` | Configure theme, daily goal, API provider, spaced review limit |
| H | ❓ Help | `H` | Show commands and usage info |
| 0 | ❌ Exit | `0` | Leave jtlearn (with confirmation) |

---

## 📊 My Progress (Option 5 / P)

> **Your learning analytics dashboard.**

| # | Option | Description |
|:---:|:---|:---|
| 1 | 📈 **Analytics Dashboard** | Visual charts, heatmaps, weak areas, insights |
| 2 | 📋 **Quiz Scores** | Detailed quiz history & accuracy |
| 3 | 🏆 **Achievements** | Badges, milestones, rarity breakdown |
| 4 | 📄 **Export Report** | Generate Markdown progress summary |
| 0 | **Back** | Return to main menu |

### Analytics Dashboard Features

| Feature | Description |
|:---|:---|
| 📊 **Visual Charts** | Progress graphs and trend lines |
| 🔥 **Heatmaps** | 30-day study calendar |
| 🎯 **Weak Areas** | Topics scoring below 80% |
| 💡 **Insights** | Personalized recommendations |

---

## 🔖 Study Tools (Option 6 / T)

> **Your productivity toolkit.**

| # | Option | Description |
|:---:|:---|:---|
| 1 | 🔖 **Bookmarks** | Saved topics for quick review |
| 2 | 🔍 **Global Search** | Search all notes at once |
| 3 | 📅 **Spaced Review** | Revisit topics you struggled with |
| 0 | **Back** | Return to main menu |

### Spaced Review System

| Timing | Purpose |
|:---|:---|
| **1 day** | Initial retention check |
| **3 days** | Short-term memory reinforcement |
| **7 days** | Long-term consolidation |

---

## 🎮 Study Modes (Option F / M)

> **Alternative ways to learn.**

| # | Option | Description |
|:---:|:---|:---|
| 1 | 🃏 **Flashcards** | Card-based review with flip reveal |
| 2 | ⚡ **Timed Quiz** | 60-second speed challenge |
| 3 | 🎓 **Tutorials** | Interactive step-by-step lessons |
| 0 | **Back** | Return to main menu |

---

## 📂 Course Catalog Features

When viewing a course, you have additional options:

### Course View Options

| Key | Action | Description |
|:---:|:---|:---|
| `1-9` | **Select Category** | Navigate into a sub-category |
| `G` | 📖 **View Glossary** | Course terminology and definitions |
| `C` | 📋 **View Case Studies** | Real-world scenarios and applications |
| `M` | 🎬 **View Media** | Videos, images, interactive content |
| `R` | 📎 **View Resources** | External links and references |
| `D` | 💬 **View Discussion Prompts** | Group learning questions |
| `A` | 🤖 **Ask AI** | Get AI explanations about this course (offline/online) |
| `S` | 📊 **Course Stats** | Your progress and performance metrics |
| `0` | **Back** | Return to Course Catalog |

### Course Catalog Main Menu

| Key | Action | Description |
|:---:|:---|:---|
| `S` | **Search** | Search courses by keyword |
| `F` | **Filter** | Filter by difficulty (`beginner`/`intermediate`/`advanced`/`expert`) |
| `L` | **Continue** | Jump to last-visited course |
| `R` | **Reset Filters** | Clear all active filters |

### Sub-topic Actions

| Key | Action | Description |
|:---:|:---|:---|
| `X` | ✅ **Mark as Complete** | Hidden if already completed |
| `B` | **Back** | Return to Sub-topics list |
| `0` | **Main Menu** | Return to Main Menu |

---

## 🔥 AI-Powered Suggestions

> **Personalized "What to Study Next" recommendations after every interaction.**

### Where Suggestions Appear

| Trigger | Icon | Detection | Suggestions |
|:---|:---:|:---|:---|
| **After AI Chat** | 💬 | Keyword matching across 10 topic areas | 3-4 cards with specific next steps |
| **After Quiz** | 📝 | Score analysis — weak areas (<80%) | Review recommendations + related topics |
| **After Course View** | 📂 | Course tags and category matching | Related courses with shared topics |
| **After Sub-topic Complete** | ✅ | Course tags + progress momentum | Next logical step in learning path |
| **After Global Search** | 🔍 | Search term + result categories | Related content based on search results |
| **Streak ≥ 3 days** | 🔥 | `study_streak.current` in config | Timed quiz challenge |
| **Spaced Review Due** | 📅 | 1-3 days since last completion | Review specific topics to lock memory |

### Example Suggestion Display

```
✨ What to Study Next
─────────────────────────────────────
🤖 AI Tutor Says:

Great effort! Here's what to focus on next:

⚠️ Review: Variables and Data Types
   You scored 65% — try again to reach 80%+
   💡 Weak area — practice makes perfect!

📚 Introduction to JavaScript
   Shares 2 topic(s): programming, beginner
   🔓 New • 180 min

🔥 Streak Challenge
   You're on a 3-day streak! Try a timed quiz
   ⚡ You're on fire — push your limits!
```

### Suggestion Quick Actions

| Key | Action |
|:---:|:---|
| `C` | Browse suggested courses |
| `R` | Start spaced review immediately |
| `T` | Take timed quiz challenge |
| `S` | Show suggestions again |
| `0` | Continue to main menu |

> 📖 **Deep dive:** See [AI_SUGGESTIONS.md](AI_SUGGESTIONS.md) for full technical details.

---

## 🎨 Themes

> **Customize your terminal experience.**

| Theme | Icon | Description | Preview |
|:---|:---:|:---|:---|
| `sky_blue` | 🔵 | Clean, bright blue tones **(Default)** | Calm and professional |
| `green` | 🟢 | Forest green, nature-inspired | Natural and refreshing |
| `grey` | ⚪ | Minimalist monochrome | Focused and distraction-free |

### How to Change Theme

1. Press `C` → Settings
2. Edit `theme` value
3. Save — **changes apply immediately**

> 💡 **Tip:** No restart required — theme updates are instant.

---

## ⌨️ Shortcut Key Reference

> **All shortcut keys are unique — no collisions.**

| Key | Routes To | Category |
|:---:|:---|:---|
| `1` / `CC` | 📂 Course Catalog | Learning |
| `2` / `N` | 📚 Study Notes | Learning |
| `3` / `Q` | 📝 Take Quiz | Assessment |
| `4` | 🤖 AI Chat | AI |
| `5` / `P` | 📊 My Progress | Analytics |
| `6` / `T` | 🔖 Study Tools | Productivity |
| `7` / `B` | 🧠 Knowledge Brain | AI |
| `8` | 🏪 Data Store | Content |
| `S` | ❤️ Support | Help |
| `F` / `M` | 🎮 Study Modes | Learning |
| `D` | 👤 Profiles | Account |
| `C` | ⚙️ Settings | Configuration |
| `H` / `?` | ❓ Help | Help |
| `0` | ❌ Exit | System |

---

## 🏪 Data Store

> **Download new courses and content.**

| Source | URL |
|:---|:---|
| **Website** | https://jitetee-ke.web.app/jtlearn |
| **In-App** | Option 8 → Data Store |

### Available Content

| Type | Icon | Description |
|:---|:---:|:---|
| **Free Courses** | 🆓 | Community-contributed content |
| **Premium Content** | 💎 | Professional-grade courses |
| **Updates** | 🔄 | Patches and improvements |

---

## 📊 Progress Tracking Keys

| Key Pattern | Type | Stored When |
|:---|:---|:---|
| `hier_{subtopic_id}` | Sub-topic completion | User presses `[X]` Mark as Complete |
| `hier_outcome_{outcome_id}` | Outcome quiz result | Assessment quiz completed |
| `reading_{category}_{topic}` | Reading time | User leaves a notes topic (5s+ spend) |
| `notes_quiz_{category}_{timestamp}` | Notes quiz result | Notes quiz completed |
| `profile_{name}_{key}` | Profile-scoped data | When using user profiles |

---

<p align="center">
  <sub>📚 jtlearn Documentation • <a href="https://github.com/jitetee/nebula">GitHub</a> • <a href="https://kash-sight.web.app">Website</a></sub>
</p>
