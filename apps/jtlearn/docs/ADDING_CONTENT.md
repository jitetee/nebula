# 📝 Adding Content to jtlearn

> **Complete guide to extending jtlearn with new learning content.**

<p align="center">
  <sub>📚 Content Guide • Version 2.0 • jtlearn 2.0.0</sub>
</p>

---

## 📋 Table of Contents

- [📊 Overview](#-overview)
- [📁 File Structure](#-file-structure)
- [📚 Adding Learning Notes](#-adding-learning-notes)
- [📝 Adding Quizzes](#-adding-quizzes)
- [💻 Adding Code Snippets](#-adding-code-snippets)
- [🏫 Adding Hierarchical Courses](#-adding-hierarchical-courses)
- [✅ Testing Your Content](#-testing-your-content)
- [💡 Tips & Best Practices](#-tips--best-practices)
- [🔧 Troubleshooting](#-troubleshooting)
- [📚 Quick Reference](#-quick-reference)

---

## 📊 Overview

jtlearn uses **JSON files** to store all learning content, making it easy to add new topics without coding.

| Content Type | File Location | Description |
|:---|:---|:---|
| 📚 **Learning Notes** | `data/notes/` | Study materials with explanations |
| 📝 **Quizzes** | `data/quizzes/` | Multiple-choice questions with answers |
| 💻 **Code Snippets** | `data/snippets/` | Reusable code examples |
| 🏫 **Hierarchical Courses** | `data/ksl/` | 6-level course structures with progression gating |

---

## 📁 File Structure

```
jtlearn/
├── data/
│   ├── notes/
│   │   ├── python.json
│   │   ├── ai_ml.json
│   │   └── your_topic.json        ← Add new here
│   │
│   ├── quizzes/
│   │   ├── python.json
│   │   ├── ai_ml.json
│   │   └── your_topic.json        ← Add new here
│   │
│   └── snippets/
│       ├── python.json
│       ├── ai_ml.json
│       └── your_topic.json        ← Add new here
│
└── jtlearn/
    └── engines/
        ├── notes_viewer.py         # Notes display logic
        └── quiz_engine.py          # Quiz logic
```

---

## 📚 Adding Learning Notes

### Step 1: Create JSON File

Create `data/notes/your_topic.json`:

```json
{
  "metadata": {
    "category": "your_topic",
    "title": "📖 Your Topic Name",
    "description": "Brief description of what this topic covers",
    "icon": "📚",
    "difficulty": "beginner",
    "version": "1.0.0"
  },
  "topics": [
    {
      "id": 1,
      "title": "First Topic Title",
      "icon": "📄",
      "content": "Your learning content here.\n\nYou can use multiple paragraphs.\n\n• Bullet points work too\n• Like this",
      "key_points": [
        "Important point 1",
        "Important point 2"
      ],
      "examples": [
        {
          "title": "Example Title",
          "explanation": "What this example demonstrates",
          "code": "print('Hello, World!')",
          "output": "Hello, World!"
        }
      ]
    }
  ],
  "quizzes": [],
  "code_snippets": []
}
```

### Step 2: Topic Fields

| Field | Type | Required | Description |
|:---|:---|:---:|:---|
| `id` | number | ✅ | Unique identifier |
| `title` | string | ✅ | Topic title |
| `icon` | string | ❌ | Emoji icon (default: 📄) |
| `content` | string | ✅ | Learning material (use `\n` for line breaks) |
| `key_points` | array | ❌ | Important takeaways |
| `examples` | array | ❌ | Code examples with explanations |

### Content Formatting Tips

| Pattern | Usage |
|:---|:---|
| Paragraph breaks | Use `\n\n` |
| Line breaks | Use `\n` |
| Bullet points | Use `•` |
| Code blocks | Include in `examples` array |

---

## 📝 Adding Quizzes

### Step 1: Create Quiz JSON

Create `data/quizzes/your_topic.json`:

```json
{
  "metadata": {
    "category": "your_topic",
    "title": "📝 Your Topic Quiz",
    "description": "Test your knowledge",
    "version": "1.0.0",
    "passing_score": 70
  },
  "questions": {
    "Topic Name 1": [
      {
        "q": "Question text here?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": 0,
        "exp": "Explanation of why this is correct"
      }
    ]
  }
}
```

### Question Fields

| Field | Type | Required | Description |
|:---|:---|:---:|:---|
| `q` | string | ✅ | Question text |
| `options` | array | ✅ | 4 answer choices (index 0-3) |
| `answer` | number | ✅ | Correct option index (0-3) |
| `exp` | string | ✅ | Explanation of the answer |

---

## 💻 Adding Code Snippets

Create `data/snippets/your_topic.json`:

```json
{
  "metadata": {
    "category": "your_topic",
    "title": "💻 Code Snippets",
    "version": "1.0.0"
  },
  "snippets": [
    {
      "title": "Function Example",
      "description": "How to define a function",
      "code": "def greet(name):\n    return f'Hello, {name}!'",
      "tags": ["functions", "basics"],
      "language": "python"
    }
  ]
}
```

### Snippet Fields

| Field | Type | Required | Description |
|:---|:---|:---:|:---|
| `title` | string | ✅ | Snippet title |
| `description` | string | ❌ | What it does |
| `code` | string | ✅ | The code itself |
| `tags` | array | ❌ | For searching/filtering |
| `language` | string | ❌ | Programming language |

---

## 🏫 Adding Hierarchical Courses

Hierarchical courses provide a **6-level deep** learning path with **progression gating**.

### Structure

```
Course → Category → Unit → Learning Outcome → Sub-topic → Content
```

### Create Course JSON

Save as `data/ksl/my_course.json`:

```json
{
  "metadata": {
    "title": "My Course Title",
    "author": "Your Name",
    "version": "1.0"
  },
  "courses": [
    {
      "id": "my_course_id",
      "code": "MC/101",
      "title": "My Course Title",
      "description": "What students will learn",
      "icon": "📘",
      "category": "my_category",
      "difficulty": "beginner",
      "estimated_minutes": 120,
      "credits": 2,
      "prerequisites": [],
      "tags": ["tag1", "tag2"],
      "learning_styles": ["visual", "hands-on", "reading"],
      "completion_requirements": {
        "min_score": 60,
        "must_complete_all": false
      },
      "categories": [
        {
          "id": "cat_basics",
          "title": "Category Title",
          "units": [
            {
              "id": "unit_1",
              "title": "Unit 1 Title",
              "learning_outcomes": [
                {
                  "id": "lo_1",
                  "title": "Learning Outcome 1",
                  "min_score": 70,
                  "subtopics": [
                    {
                      "id": "sub_1",
                      "title": "Sub-topic Title",
                      "type": "content",
                      "content": "Main content text here.",
                      "key_points": ["Point 1", "Point 2"]
                    },
                    {
                      "id": "sub_quiz_1",
                      "title": "Quiz: Topic",
                      "type": "assessment",
                      "quiz": [
                        {
                          "question": "What is the answer?",
                          "options": ["A", "B", "C", "D"],
                          "answer": 1,
                          "explanation": "Why B is correct."
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### Sub-topic Types

| Type | Icon | Purpose | Runnable |
|:---|:---:|:---|:---:|
| `content` | 📄 | Main learning content | ❌ |
| `example` | 💡 | Illustrative examples | ❌ |
| `activity` | 🔧 | Hands-on exercises | ❌ |
| `assessment` | 📝 | Quizzes (runs automatically) | ✅ |
| `reference` | 📎 | Additional resources | ❌ |

### Pack Into .ksl File

```bash
python ksl_tool.py pack data/ksl/my_course.json -t "My Course Title"
```

> 📦 Creates `data/ksl/my_course.ksl` — the packaged format jtlearn loads.

---

## ✅ Testing Your Content

### Step 1: Validate JSON

```bash
python -m json.tool data/notes/your_topic.json > /dev/null && echo "Valid JSON"
```

### Step 2: Test in jtlearn

| Step | Action |
|:---:|:---|
| 1 | Launch: `jtlearn` |
| 2 | Select **Option 2: Study Notes** → Find your topic |
| 3 | Select **Option 3: Take Quiz** → Test your quiz |
| 4 | Go to **Option 5: My Progress** → Verify tracking |

---

## 💡 Tips & Best Practices

### ✅ DO

- Write clear, concise explanations
- Use examples for every concept
- Include real-world use cases
- Add multiple choice questions with good distractors
- Use 2-space JSON indentation
- Test all code examples
- Use relevant emojis for visual organization

### ❌ DON'T

- Write walls of text (break into paragraphs)
- Use ambiguous quiz questions
- Make all quiz answers obviously wrong except one
- Include code that doesn't run
- Forget to proofread
- Use single quotes in JSON (requires double quotes)

### Icon Reference

| Category | Suggested Icons |
|:---|:---|
| Python | 🐍 |
| JavaScript | 🟨 |
| AI/ML | 🤖 |
| Web Dev | 🌐 |
| Security | 🔒 |
| Linux | 🐧 |
| Database | 🗄️ |
| Git | 📦 |

---

## 🔧 Troubleshooting

### Content Not Showing Up

| Problem | Solution |
|:---|:---|
| New topic doesn't appear | Check JSON syntax, verify file location, restart jtlearn |
| Quiz shows "No questions found" | Ensure `questions` key exists, check answer is number (0-3) |
| Formatting issues | Use `\n` for line breaks, escape quotes with `\"` |

### Validation Commands

```bash
# Check JSON syntax
python -m json.tool data/notes/your_topic.json

# Quick test
python -c "import json; json.load(open('data/notes/your_topic.json'))"
```

---

## 📚 Quick Reference

### Minimal Notes File
```json
{
  "metadata": { "category": "topic", "title": "📖 Topic" },
  "topics": [{ "id": 1, "title": "First Topic", "content": "Content here" }]
}
```

### Minimal Quiz File
```json
{
  "metadata": { "category": "topic", "title": "Quiz" },
  "questions": {
    "Topic": [{ "q": "Question?", "options": ["A", "B", "C", "D"], "answer": 0, "exp": "Why" }]
  }
}
```

---

<p align="center">
  <sub>📚 jtlearn Documentation • <a href="https://github.com/kashsight/kslearn">GitHub</a> • <a href="https://kash-sight.web.app">Website</a></sub>
</p>
