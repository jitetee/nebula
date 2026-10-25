# 🏗️ Hierarchical Course Structure

> **jtlearn** supports **6-level hierarchical navigation** for course content with **progression gating** — you can't advance to the next level until you meet requirements.

<p align="center">
  <sub>📄 Documentation • Version 1.0 • jtlearn 2.0.0</sub>
</p>

---

## 📋 Table of Contents

- [📊 Overview](#-overview)
- [🏗️ The Hierarchy](#%EF%B8%8F-the-hierarchy)
- [🔒 Progression Gating](#-progression-gating-locking-system)
- [📦 Complete JSON Structure](#-complete-json-structure)
- [📝 Sub-topic Types](#-sub-topic-types)
- [🎯 Assessment Quizzes](#-assessment-quizzes-in-sub-topics)
- [✅ Mark as Complete](#-mark-as-complete)
- [📊 Difficulty Levels](#-difficulty-levels)
- [🔍 Course Catalog Features](#-course-catalog-features)
- [📦 Packaging](#-how-to-package)
- [🚀 Access Your Course](#-how-to-access)
- [🔄 Backward Compatibility](#-backward-compatibility)
- [📊 Progress Tracking Keys](#-progress-tracking-keys)

---

## 📊 Overview

| Feature | Description |
|:---|:---|
| **Navigation Levels** | 6-level deep hierarchy |
| **Progression Gating** | Lock/unlock system based on prerequisites and scores |
| **Content Types** | Notes, quizzes, activities, assessments, references |
| **Tracking** | Automatic progress saving with achievement triggers |

---

## 🏗️ The Hierarchy

```
Level 1: Course 📘
  └── Level 2: Category (Unit Category) 📁
       └── Level 3: Unit 📖
            └── Level 4: Learning Outcome 🎯
                 └── Level 5: Sub-topic (Performance Standard) 📝
                      └── Level 6: Content (actual text, examples, code) 📄
```

> **Example Path:** `Introduction to Python` → `Programming Basics` → `Variables & Data Types` → `Understand Python Variables` → `Variable Declaration` → `Content with examples`

---

## 🔒 Progression Gating (Locking System)

| Gate Type | Level | Rule | Icon |
|:---|:---|:---|:---:|
| **Prerequisites** | Course | Must complete prerequisite courses first | 🔒 |
| **Prerequisites** | Unit | Must complete prerequisite units (with optional `min_score`) | 🔒 |
| **Sequential** | Learning Outcome | Must pass previous outcome with `min_score`% before unlocking next | 🔒 |
| **Must Complete All** | Learning Outcome | If set, **ALL** previous outcomes must pass `min_score` | 🔒 |

### Lock Indicators

| Icon | Meaning |
|:---:|:---|
| 🔒 | **Locked** — Requirements not met |
| 🔓 | **Available** — Ready to access |

---

## 📦 Complete JSON Structure

> 📁 **Reference:** See `data/jif/hierarchical_sample.json` for a working example with all fields.

### Key Fields at Each Level

| Level | Key Fields |
|:---|:---|
| **Course** | `id`, `code`, `title`, `description`, `icon`, `prerequisites[]`, `difficulty`, `estimated_minutes`, `credits`, `tags[]`, `learning_styles[]`, `glossary[]`, `media[]`, `resources[]`, `instructor_notes`, `completion_requirements{min_score, must_complete_all}`, `version`, `changelog` |
| **Category** | `id`, `title`, `description`, `difficulty`, `estimated_minutes`, `glossary[]`, `case_studies[]`, `discussion_prompts[]` |
| **Unit** | `id`, `code`, `title`, `description`, `prerequisites[]`, `difficulty`, `estimated_minutes`, `tools[]`, `equipment[]`, `supplies[]`, `performance_standards[]`, `glossary[]`, `case_studies[]`, `media[]`, `resources[]`, `discussion_prompts[]`, `completion_requirements`, `instructor_notes` |
| **Learning Outcome** | `id`, `title`, `description`, `min_score`, `must_complete_all`, `estimated_minutes`, `difficulty`, `discussion_prompts[]`, `case_studies[]`, `media[]` |
| **Sub-topic** | `id`, `title`, `type`, `content`, `key_points[]`, `examples[]`, `quiz[]`, `difficulty`, `estimated_minutes`, `learning_styles[]`, `media[]`, `resources[]`, `discussion_prompts[]` |

---

## 📝 Sub-topic Types

| Type | Icon | Purpose | Runnable |
|:---|:---:|:---|:---:|
| `content` | 📄 | Main learning content | ❌ |
| `example` | 💡 | Illustrative examples | ❌ |
| `activity` | 🔧 | Hands-on exercises | ❌ |
| `assessment` | 📝 | Quizzes and tests | ✅ **Yes** — runs quiz inline |
| `reference` | 📎 | Additional resources | ❌ |

---

## 🎯 Assessment Quizzes in Sub-topics

Sub-topics of type `"assessment"` can include embedded `quiz[]` arrays. When the user opens the sub-topic:

| Feature | Description |
|:---|:---|
| **Display** | Question-by-question with streak tracking |
| **Scoring** | Score, accuracy, and best streak results |
| **Auto-save** | Saves to `learning_progress` (key: `hier_outcome_{outcome_id}`) |
| **Achievements** | Checks triggered on completion |

### Example Assessment Structure

```json
{
  "id": "sub_quiz_1",
  "title": "Quiz: Variables",
  "type": "assessment",
  "quiz": [
    {
      "question": "What is the output of print(type([]))?",
      "options": ["<class 'tuple'>", "<class 'list'>", "<class 'dict'>", "<class 'set'>"],
      "answer": 1,
      "explanation": "[] creates an empty list in Python."
    }
  ]
}
```

---

## ✅ Mark as Complete

Every sub-topic content view includes an **✅ Mark as Complete** `[X]` option.

| Action | Result |
|:---|:---|
| Press `[X]` | Saves to `learning_progress` with key `hier_{subtopic_id}` |
| Timestamp | Records completion date and time |
| Breadcrumb | Saves full navigation path for analytics |

> ⚠️ **Hidden** if already completed — no duplicate entries.

---

## 📊 Difficulty Levels

| Level | Icon | Color | Description |
|:---|:---:|:---:|:---|
| `beginner` | 🟢 | Green | Starting point — no prerequisites |
| `intermediate` | 🟡 | Yellow | Some foundational knowledge required |
| `advanced` | 🔴 | Red | Significant prior experience needed |
| `expert` | ⚫ | Black | Mastery-level content |

---

## 🔍 Course Catalog Features

| Feature | Key | Description |
|:---|:---:|:---|
| **Search** | `[S]` | Text search across course titles, descriptions, and tags |
| **Filter** | `[F]` | Filter by difficulty (`beginner`/`intermediate`/`advanced`/`expert`) |
| **Continue** | `[L]` | Jump back to your last-visited course |
| **Reset** | `[R]` | Clear all active filters |

### Additional Course Actions

| Key | Action | Description |
|:---:|:---|:---|
| `G` | 📖 **Glossary** | View course terminology |
| `C` | 📋 **Case Studies** | Real-world scenarios |
| `M` | 🎬 **Media** | Videos, images, interactive content |
| `R` | 📎 **Resources** | External links and references |
| `D` | 💬 **Discussions** | Prompt-based group learning |
| `A` | 🤖 **Ask AI** | Get AI explanations about this course |
| `S` | 📊 **Stats** | View your progress and performance |

---

## 📦 How to Package

### Interactive Mode

```bash
python jif_tool.py
```

### CLI Mode

```bash
python jif_tool.py pack my_course.json -t "Course Title"
```

> 📦 Creates a `.jif` file in `data/jif/` ready for distribution.

---

## 🚀 How to Access

1. **Launch:** `jtlearn` or `python -m jtlearn`
2. **Select:** Option 1 — Course Catalog
3. **Browse:** Course → Category → Unit → Outcome → Sub-topic → Content
4. **Extra Actions:** Use `[G]`, `[C]`, `[M]`, `[R]`, `[D]`, `[S]` for enrichment
5. **Search & Filter:** `[S]` to search, `[F]` to filter by difficulty, `[L]` to continue

---

## 🔄 Backward Compatibility

| Format | Status | Notes |
|:---|:---:|:---|
| **Flat `.jif` files** | ✅ Supported | Continue to work as before |
| **Hierarchical format** | ✅ Supported | Additional content type |

> **No breaking changes.** Existing content loads automatically.

---

## 📊 Progress Tracking Keys

| Key Pattern | Type | Stored When |
|:---|:---|:---|
| `hier_{subtopic_id}` | Sub-topic completion | User presses `[X]` Mark as Complete |
| `hier_outcome_{outcome_id}` | Outcome quiz result | Assessment quiz completed |
| `reading_{category}_{topic}` | Reading time | User leaves a notes topic (5s+ spend) |

---

<p align="center">
  <sub>📚 jtlearn Documentation • <a href="https://github.com/jitetee/nebula">GitHub</a> • <a href="https://kash-sight.web.app">Website</a></sub>
</p>
