# 🤖 AI-Powered "What to Study Next"

> **jtlearn's proactive suggestion engine — making learning addictive by always showing the logical next step.**

<p align="center">
  <sub>🧠 AI Engine • Version 1.0 • jtlearn 2.0.0</sub>
</p>

---

## 📋 Table of Contents

- [📊 Overview](#-overview)
- [⚙️ How It Works](#%EF%B8%8F-how-it-works)
- [📍 Where Suggestions Appear](#-where-suggestions-appear)
- [🎯 Topic Detection Matrix](#-topic-detection-matrix)
- [📦 Suggestion Types](#-suggestion-types)
- [⚡ Quick Actions](#-quick-actions)
- [📁 Files Involved](#-files-involved)
- [🔧 Customization](#-customization)

---

## 📊 Overview

| Attribute | Detail |
|:---|:---|
| **Purpose** | Proactively recommend what to learn next after every interaction |
| **Goal** | Make learning **addictive** — never run out of momentum |
| **Trigger** | After every user action (chat, quiz, course, search, etc.) |
| **Personalization** | Based on quiz performance, study patterns, streaks, and spaced review timing |

---

## ⚙️ How It Works

The suggestion engine analyzes your current context and generates personalized recommendations:

| Factor | Description |
|:---|:---|
| **1. Topic Detection** | Keyword matching across 10 topic areas |
| **2. Quiz Performance** | Weak areas scoring below 80% |
| **3. Study Streak** | Momentum-based challenges |
| **4. Spaced Review Timing** | Topics due for review (1-3 days since completion) |
| **5. Course Relationships** | Shared tags and categories |
| **6. Beginner Defaults** | If no data, suggest popular starter courses |

---

## 📍 Where Suggestions Appear

### 1. 💬 After AI Chat

| Property | Value |
|:---|:---|
| **Trigger** | You ask the AI tutor a question |
| **Detection** | Keyword matching across 10 topic areas |
| **Output** | 3-4 cards with specific next steps |

**Example:**
```
You: "What are Python variables?"
AI: [Explains variables with examples]

✨ Keep Learning
─────────────────────────────────────
🎓 AI Tutor Suggests:

Based on your question, here's a great next step:

📚 Learn about Functions & Scope
   Master reusable code blocks

📝 Try a Python Quiz
   Test your knowledge with 5 questions

🔧 Build a Mini Project
   Apply what you've learned in practice
```

---

### 2. 📝 After Quiz Completion

| Property | Value |
|:---|:---|
| **Trigger** | You finish any quiz |
| **Detection** | Score analysis — identifies weak areas (<80%) |
| **Output** | Review recommendations + related topics |

**Example:**
```
📊 Quiz Results
Score: 7/10 (70%)

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

---

### 3. 📂 After Course Viewing

| Property | Value |
|:---|:---|
| **Trigger** | You browse a hierarchical course |
| **Detection** | Course tags and category matching |
| **Output** | Related courses with shared topics |

---

### 4. ✅ After Sub-topic Complete

| Property | Value |
|:---|:---|
| **Trigger** | You press "Mark as Complete" `[X]` |
| **Detection** | Course tags + progress momentum |
| **Output** | Next logical step in learning path |

---

### 5. 🔍 After Global Search

| Property | Value |
|:---|:---|
| **Trigger** | You search all notes |
| **Detection** | Search term + result categories |
| **Output** | Related content based on search results |

---

### 6. 🔥 Streak Challenge

| Property | Value |
|:---|:---|
| **Trigger** | Study streak ≥ 3 days |
| **Detection** | `study_streak.current` in config |
| **Output** | Timed quiz challenge |

---

### 7. 📅 Spaced Review Reminder

| Property | Value |
|:---|:---|
| **Trigger** | 1-3 days since last completion |
| **Detection** | `completed_at` timestamps in `learning_progress` |
| **Output** | Review specific topics to lock in memory |

---

## 🎯 Topic Detection Matrix

| Topic | Keywords Detected |
|:---|:---|
| 🐍 **Python** | `python`, `variable`, `function`, `loop`, `class`, `object`, `list`, `dict`, `code` |
| 🔢 **Math** | `math`, `algebra`, `calculus`, `equation`, `derivative`, `integral`, `geometry` |
| 🔬 **Science** | `physics`, `chemistry`, `biology`, `atom`, `molecule`, `cell`, `energy` |
| 🌐 **Web Dev** | `html`, `css`, `javascript`, `react`, `node`, `web`, `browser`, `frontend` |
| 📊 **Data Science** | `data`, `analysis`, `statistics`, `probability`, `pandas`, `numpy`, `ml` |
| 📜 **History** | `history`, `war`, `empire`, `civilization`, `ancient`, `medieval`, `revolution` |
| 🧠 **Psychology** | `psychology`, `mind`, `behavior`, `cognitive`, `therapy`, `mental`, `emotion` |
| 🎵 **Music** | `music`, `chord`, `scale`, `rhythm`, `melody`, `harmony`, `instrument` |
| 💼 **Business** | `business`, `marketing`, `sales`, `revenue`, `profit`, `startup`, `strategy` |
| 🗣️ **Language** | `grammar`, `vocabulary`, `language`, `learn english`, `speak`, `pronounce` |

---

## 📦 Suggestion Types

| Type | Icon | When Shown |
|:---|:---:|:---|
| Related Course | 📚 | Tag/category overlap detected |
| Weak Area Review | 📝 | Quiz score < 80% |
| Practice/Project | 🔧 | After learning new concept |
| Explore Next | 📖 | Natural progression path |
| Style/Best Practice | 💡 | Code or writing topics |
| Streak Challenge | 🔥 | Streak ≥ 3 days |
| Spaced Review | 📅 | 1-3 days since completion |
| Beginner Default | 🌟 | No data available |

---

## ⚡ Quick Actions

After suggestions are displayed:

| Key | Action |
|:---:|:---|
| `C` | Browse suggested courses |
| `R` | Start spaced review immediately |
| `T` | Take timed quiz challenge |
| `S` | Show suggestions again |
| `0` | Continue to main menu |

---

## 📁 Files Involved

| File | Purpose |
|:---|:---|
| `jtlearn/engines/notes_viewer.py` | `show_ai_suggestions()` — main engine for courses |
| `jtlearn/engines/notes_viewer.py` | `search_all_notes()` — global search across all content |
| `jtlearn/main/ai_chat.py` | `_generate_learning_suggestions()` — AI chat suggestions |
| `jtlearn/cli.py` | `_run_global_search()` — search with AI suggestions |
| `jtlearn/cli.py` | `_run_quiz_interactive()` — quiz with post-quiz suggestions |

---

## 🔧 Customization

Suggestions are driven by:

| Factor | How to Improve |
|:---|:---|
| **Course tags** | Add more tags to your `.jif` courses for better matching |
| **Quiz performance** | The more you quiz, the better the weak-area detection |
| **Study patterns** | Streaks and spaced review timing are personalized |

### Extending Topic Detection

Add new entries to the `topic_keywords` dict in:
- `jtlearn/engines/notes_viewer.py` (`show_ai_suggestions`)
- `jtlearn/main/ai_chat.py` (`_generate_learning_suggestions`)

---

<p align="center">
  <sub>📚 jtlearn Documentation • <a href="https://github.com/jitetee/nebula">GitHub</a> • <a href="https://kash-sight.web.app">Website</a></sub>
</p>
