# 🌌 KSL-Verse — Complete Game Design Document

> **An Interactive Multiverse Learning Experience for KSLearn**

<p align="center">
  <sub>🎮 Game Design • Version 2.0 • April 2026</sub>
</p>

---

## 📋 Table of Contents

- [📖 Overview](#-overview)
- [🎮 Core Concept](#-core-concept)
- [🗺️ World Structure](#%EF%B8%8F-world-structure)
- [🌐 WebDev Cosmos — Starter World](#-webdev-cosmos--starter-world)
- [🏆 XP & Player Level System](#-xp--player-level-system)
- [🎮 Game Modes](#-game-modes)
- [🧩 Additional Features](#-additional-features)
- [📊 Analytics & Export](#-analytics--export)
- [🏅 Achievements](#-achievements-32-total)
- [🎭 Accessibility Options](#-accessibility-options)
- [📝 JSON Schema Reference](#-json-schema-reference)
- [🔧 Technical Implementation](#-technical-implementation)
- [🚀 Future Expansion](#-future-expansion)
- [📝 Version History](#-version-history)

---

## 📖 Overview

| Attribute | Detail |
|:---|:---|
| **Type** | Story-driven, choice-based educational game |
| **Platform** | KSLearn CLI (terminal) |
| **Content** | Self-contained in `*_verse.json` files |
| **Dependencies** | None — no quiz files or other engines required |
| **Player Role** | **Verse Walker** — a learner who traverses knowledge universes |

---

## 🎮 Core Concept

### The Premise

> You are a **Verse Walker** — a learner who can traverse between knowledge universes. Each universe contains multiple worlds, and each world is divided into levels you must conquer by answering questions, making choices, and proving your mastery.

### Gameplay Loop

```
Select World → View Level Map → Enter Level → Read Scenario Narrative
  → Make Choices (A/B/C/D) → Earn XP → Unlock Next Scenario
    → Complete All Scenarios → Face Boss Battle → Conquer World!
```

### Key Mechanics

| Mechanic | Description |
|:---|:---|
| **XP (Experience Points)** | Earned per correct answer. Streaks multiply rewards. |
| **Player Level** | Total XP determines your Verse Walker rank. Higher levels unlock prestige. |
| **Worlds** | Themed knowledge domains (e.g., WebDev Cosmos). Content in `*_verse.json`. |
| **Levels** | Progressive stages within a world. Each has a story arc. |
| **Scenarios** | Narrative-driven nodes with a story beat + multiple-choice question. |
| **Branching Outcomes** | Correct answers advance the story; wrong answers trigger explanations and retries. |
| **Boss Battles** | Final challenge of each world — harder, multi-part questions with bonus XP. |
| **Achievements** | Special badges for milestones (first world, speed runs, perfect scores, etc.). |

---

## 🗺️ World Structure

Each world is defined in a `*_verse.json` file:

```json
{
  "verse": {
    "id": "webdev_cosmos",
    "title": "WebDev Cosmos",
    "description": "From markup to mastery...",
    "icon": "🌐",
    "difficulty": "beginner",
    "player_level_required": 1,
    "lore": { "origin_of_cosmos": { "title": "...", "icon": "🌌", "content": "..." } },
    "side_quests": [
      { "id": "sq_1", "name": "Speed Demon", "description": "Complete a level in under 60s",
        "requirements": { "levels_completed": 1 }, "xp_reward": 100 }
    ],
    "levels": [
      {
        "id": "level_1",
        "title": "The HTML Highlands",
        "story_intro": "You materialize on a plateau...",
        "icon": "🏔️",
        "xp_reward_per_scenario": 25,
        "concepts": ["DOCTYPE", "Semantic HTML", "Forms"],
        "scenarios": [
          {
            "id": "scene_1",
            "concept": "DOCTYPE",
            "narrative": "The Builder approaches...",
            "question": "Which line declares the document type?",
            "options": [
              {"letter": "A", "text": "<!DOCTYPE html>", "correct": true},
              {"letter": "B", "text": "<html>", "correct": false}
            ],
            "explanation_correct": "<!DOCTYPE html> tells the browser...",
            "explanation_wrong": "HTML5 uses <!DOCTYPE html>...",
            "is_secret": true,
            "secret_lore_id": "origin_of_cosmos"
          }
        ],
        "mini_boss": { "name": "The Tag Gatekeeper", "xp_reward": 75, "questions": [...] },
        "boss": { "name": "The Markup Sentinel", "xp_reward": 150, "questions": [...] }
      }
    ],
    "epilogue": "The WebDev Cosmos trembles..."
  }
}
```

---

## 🌐 WebDev Cosmos — Starter World

> *"From markup to mastery — forge your path through the fabric of the web."*

| Level | Name | Theme | Icon |
|:---:|:---|:---|:---:|
| 1 | The HTML Highlands | HTML fundamentals — structure, semantic tags, forms | 🏔️ |
| 2 | The CSS Canyons | CSS — selectors, box model, flexbox, colors | 🎨 |
| 3 | The JavaScript Junction | JS basics — variables, functions, conditionals | ⚡ |
| 4 | The DOM Delta | DOM manipulation, events, event bubbling | 🌊 |
| 5 | The Async Abyss | Callbacks, Promises, async/await, fetch API | 🔮 |

> Each level has **5 scenarios** + **1 mini-boss** (mid-level) + **1 boss battle** (end of world).

---

## 🏆 XP & Player Level System

### XP Rewards

| Action | XP |
|:---|:---:|
| Correct scenario answer | 25 XP |
| Correct boss question | 30 XP |
| Scenario streak (3+ correct) | +5 bonus per streak |
| Perfect level (no wrong answers) | +50 bonus |
| Perfect world (all levels perfect) | +200 bonus |
| First world completion | +100 bonus |

### Player Levels (Verse Walker Ranks)

| Level | Rank Title | Total XP Required | Badge |
|:---:|:---|:---:|:---:|
| 1 | Novice Walker | 0 | 🌱 |
| 2 | Apprentice Explorer | 200 | 🔍 |
| 3 | Seasoned Voyager | 500 | 🧭 |
| 4 | Knowledge Seeker | 1,000 | 📖 |
| 5 | Realm Wanderer | 2,000 | 🗺️ |
| 6 | Domain Master | 3,500 | 🎯 |
| 7 | Cosmos Sage | 5,500 | 🌟 |
| 8 | Universe Architect | 8,000 | 🏗️ |
| 9 | Multiverse Legend | 12,000 | 🏆 |
| 10 | Verse Transcendent | 20,000 | 👑 |

---

## 🎮 Game Modes

| Mode | XP Multiplier | Description |
|:---|:---:|:---|
| ⚔️ **Story Mode** | 1× | Relaxed pace, hints available, forgiving wrong answers |
| ⚔️ **Normal** | 1× | Standard experience |
| 🔥 **Hard Mode** | 1.5× | No hints, no forgiveness |
| 💀 **Ironman** | 2× | One wrong answer = run ends |
| 🏃 **Marathon** | 3× | Complete entire world back-to-back |
| ⚔️ **Boss Rush** | 2× | Fight all world bosses in sequence |
| ♾️ **Endless** | 1× | Infinite random scenarios — one wrong = game over |
| 💀 **Survival** | 1× | 3 lives — wrong answers cost lives |
| 🎲 **Randomizer** | 1× | 10 random scenarios from all worlds |
| 🏃 **Practice** | 0× | No penalties, no XP — just learning |

---

## 🧩 Additional Features

### 🎯 Side Quests

Optional challenges per world defined in verse JSON:

| Quest | Requirement | Reward |
|:---|:---|:---|
| Speed Demon | Complete a level in under 60s | 100 XP |
| No Lifelines | Complete without using lifelines | Bonus XP |
| Perfect Boss | Get 100% on the boss battle | Bonus XP |

### 💎 Lifelines (3 Types)

| Lifeline | Uses | Effect |
|:---|:---:|:---|
| **50/50** | 3 | Remove 2 wrong options |
| **Skip** | 2 | Bypass a scenario |
| **Hint** | 3 | Get a clue about the answer |

### 🎒 Items & Inventory

Random drops (10% chance per correct answer):

| Item | Icon | Effect |
|:---|:---:|:---|
| Syntax Shard | 🔮 | +1 hint use |
| Logic Gem | 💎 | +2 hint uses |
| Streak Crystal | 🔥 | 1.5x XP for next level |
| Lore Scroll | 📜 | Unlock a lore entry |
| Skip Token | ⏭️ | Skip next scenario |
| Shield Charm | 🛡️ | Absorb one wrong answer penalty |
| Memory Orb | 🔵 | Boost spaced review priority |
| XP Potion | 🧪 | Instant 50 XP |
| Compass | 🧭 | Show weakest area |

### 👤 NPC System

| Feature | Description |
|:---|:---|
| **Dynamic Greetings** | Change based on visit count and progress |
| **Farewell Messages** | Personalized based on performance |
| **Mentor Advice** | Guidance about your weakest areas |
| **Rival Challenges** | Rival Walker at milestones (3 questions, 100 XP) |

### 📖 World Lore Codex

| Feature | Description |
|:---|:---|
| **Hidden Secrets** | 5% chance per scenario to unlock lore |
| **Lore Entries** | Backstory, developer quotes, Easter eggs |
| **Collection** | Tracked per world |

### ⚔️ Boss Phases

| Phase | Description |
|:---|:---|
| **Phase 1** | First half of boss battle |
| **Phase 2** | Second half — harder if struggling in Phase 1 |
| **Visual** | "BOSS ENRAGED" notification when difficulty increases |

### 📅 Seasonal Events

| Event | When | Bonus |
|:---|:---|:---|
| **Code Week** | May 1-7 | Double XP |
| **Hacktober** | October | 1.5x XP, spooky-themed challenges |

### 🔄 Prestige System

After reaching max level (20,000 XP):

| Feature | Description |
|:---|:---|
| **XP Bonus** | Permanent +10% XP per prestige level |
| **Titles** | Prestige I–X, Ascendant, Eternal |
| **Kept** | Lore, journal entries, custom questions |
| **Reset** | Progress restarts for replay value |

### 📍 Mid-World Checkpoints

| Feature | Description |
|:---|:---|
| **Auto-Save** | Save progress mid-level on quit |
| **Resume** | Prompt appears when re-entering a world |
| **Data** | Current scenario, XP, items, streak |

### 🌍 World Builder (In-App)

> Guided CLI wizard to create new verse worlds — no JSON editing required.

| Step | Description |
|:---|:---|
| 1 | Enter world info (title, description, icon, difficulty) |
| 2 | Create levels with story arcs |
| 3 | Write scenarios and boss questions |
| 4 | Generates `*_verse.json` automatically |

### 🤖 AI World Generator

The primary world creation method. Uses **tgpt/sky** AI with `ThreadPoolExecutor`:

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  Course Catalog │ ──► │  AI Generation      │ ──► │  Playable World │
│  (data/ksl/)    │     │  (up to 10 workers) │     │  (*_verse.json) │
└─────────────────┘     └─────────────────────┘     └─────────────────┘
```

**Process:**
1. **Browse Course Catalog** — Shows all existing hierarchical courses
2. **Pick a Course** — Select any course as source material
3. **AI generates in parallel** — Each course category → a game level
4. **Content created** — 5 scenarios per level + mini-boss + boss battle
5. **Lore + epilogue** — Inspired by course content
6. **Fallback** — If no courses exist, create custom world manually

---

## 📊 Analytics & Export

| Feature | Description |
|:---|:---|
| 📈 **Deep Stats** | Total sessions, time, accuracy trends, improvement graphs |
| 🔥 **Streak Calendar** | 30-day heatmap of verse study days |
| 📊 **Performance Timeline** | Score trends over time with 📈/📉 icons |
| 🎯 **Weakness Tracker** | Spaced review scheduling for wrong answers |
| 📤 **Import/Export** | Backup and restore progress via JSON file |
| 🔗 **Share Codes** | Generate a hash code from your stats to share |
| 📋 **Report Card** | Semester-style grade (A+ to F) with world breakdown |
| 🃏 **Profile Card** | Copyable ASCII card with your stats |

---

## 🏅 Achievements (32 Total)

### Original (15)

| Achievement | Description |
|:---|:---|
| First Steps | Complete your first quiz |
| Quiz Master | Score 100% on any quiz |
| Perfectionist | Complete a quiz with no wrong answers |
| Hot Streak | Answer 5 questions correctly in a row |
| Month Warrior | Complete 30 days of studying |
| Knowledge Seeker | Study 10 different topics |
| Walking Encyclopedia | Complete all topics in a category |
| Explorer | Try every main menu feature |
| Speed Demon | Complete a timed quiz in under 30s |
| Bookworm | Read 50 topics |
| Flash of Genius | Answer 10 questions correctly in a row |
| Consistent Learner | Study 7 days in a row |
| Renaissance Mind | Study 3 different subject areas in one day |
| Tutorial Graduate | Complete a tutorial |
| Profile Creator | Create a user profile |

### KSL-Verse (17)

| Achievement | Description |
|:---|:---|
| First Steps in the Verse | Play your first KSL-Verse session |
| Level Cleared | Complete any level |
| World Conqueror | Complete an entire world |
| Perfect Run | No wrong answers in a level |
| Streak Walker | Maintain a 10+ streak |
| Boss Slayer | Defeat a boss battle |
| Multiverse Explorer | Play 5 different worlds |
| Verse Transcendent | Reach max player level |
| Secret Hunter | Unlock 5 lore entries |
| Daily Champion | Complete a daily challenge |
| Speed Runner | Complete a level in under 60s |
| Combo Master | 3x combo multiplier |
| Masochist (Hard Mode) | Complete a world on Hard |
| Collector | Collect 20 items |
| Lore Master | Unlock all lore in a world |
| Reborn (Prestige) | Prestige for the first time |
| Journaler | Write 10 journal entries |

---

## 🎭 Accessibility Options

| Option | Description |
|:---|:---|
| 🎨 **High Contrast Mode** | Bolder colors, clearer separators |
| 🔤 **Large Text Mode** | Bigger fonts throughout |
| 🚫 **Reduced Motion** | No typing animations |
| 🔇 **Sound Effects Toggle** | Terminal bell on/off |
| 📦 **Compact Mode** | Questions only, minimal narrative |

---

## 📝 JSON Schema Reference

### Verse File

| Key | Type | Required |
|:---|:---|:---:|
| `verse.id` | string | ✅ |
| `verse.title` | string | ✅ |
| `verse.description` | string | ✅ |
| `verse.icon` | emoji | ✅ |
| `verse.difficulty` | string | ✅ |
| `verse.player_level_required` | number | ✅ |
| `verse.lore` | object | ❌ |
| `verse.side_quests` | array | ❌ |
| `verse.epilogue` | string | ❌ |
| `verse.levels` | array | ✅ |

### Level

| Key | Type | Required |
|:---|:---|:---:|
| `level.id` | string | ✅ |
| `level.title` | string | ✅ |
| `level.story_intro` | string | ✅ |
| `level.icon` | emoji | ✅ |
| `level.xp_reward_per_scenario` | number | ✅ |
| `level.concepts` | array | ❌ |
| `level.scenarios` | array | ✅ |
| `level.mini_boss` | object | ❌ |
| `level.boss` | object | ❌ |

### Scenario

| Key | Type | Required |
|:---|:---|:---:|
| `scenario.id` | string | ✅ |
| `scenario.concept` | string | ❌ |
| `scenario.narrative` | string | ✅ |
| `scenario.question` | string | ✅ |
| `scenario.options` | array | ✅ |
| `scenario.explanation_correct` | string | ✅ |
| `scenario.explanation_wrong` | string | ✅ |
| `scenario.related_concepts` | array | ❌ |
| `scenario.is_secret` | boolean | ❌ |
| `scenario.code` | string | ❌ (for code output questions) |

---

## 🔧 Technical Implementation

### Files

| File | Purpose |
|:---|:---|
| `jtlearn/engines/verse_engine.py` | Core game engine (~3,400 lines) |
| `data/ksl/webdev_verse.json` | WebDev Cosmos world content |
| `data/ksl/*_verse.json` | Custom/generated worlds |
| `docs/KSL_VERSE_GAME_DESIGN.md` | This document |

### Modified Files

| File | Changes |
|:---|:---|
| `jtlearn/config.py` | Added `verse_progress` profile key + defaults |
| `jtlearn/engines/achievements.py` | Added 17 verse achievements |
| `jtlearn/cli.py` | Added option 9/V/VERSE to main menu + `jtlearn verse` command |

### Content Loading

| Feature | Description |
|:---|:---|
| **Discovery** | Scans all `*_verse.json` files in `data/ksl/` |
| **Independence** | No dependency on quiz engine or `.ksl` files |
| **Auto-Load** | Worlds auto-discovered on menu load |
| **Custom** | Worlds added via World Builder or manual JSON |

### State Persistence

All progress stored in `settings.json` under `verse_progress`:

```json
{
  "verse_progress": {
    "total_xp": 0,
    "worlds": {},
    "combo_multiplier": 1.0,
    "difficulty": "normal",
    "lifelines": {"fifty_fifty": 3, "skip": 2, "hint": 3},
    "inventory": [],
    "weaknesses": {},
    "lore_unlocked": [],
    "speedrun_records": {},
    "session_stats": {},
    "streak_calendar": {},
    "prestige_level": 0,
    "journal": {},
    "sound_enabled": true
  }
}
```

---

## 🚀 Future Expansion

### New Worlds (Planned)

| World | Icon | Theme |
|:---|:---:|:---|
| Python Kingdom | 🐍 | Python fundamentals |
| Data Dimension | 🗄️ | SQL, databases |
| Science Galaxy | 🧬 | Physics, chemistry, biology |
| History Timeline | 📜 | Historical events |
| Math Universe | 🔢 | Algebra, statistics |

### Planned Features

| Feature | Description |
|:---|:---|
| 🎵 **Background Chiptune Music** | Retro game-style audio |
| 🏅 **Online Leaderboards** | Competitive rankings |
| 📖 **World Lore Encyclopedia** | Searchable lore database |
| 🔄 **Daily Verse Challenges** | Rotating scenario sets |
| 🎨 **Custom Player Avatars** | Personalized characters |
| 📱 **Mobile App Companion** | Cross-platform progress sync |

---

## 📝 Version History

| Version | Date | Notes |
|:---:|:---|:---|
| **1.0** | April 2026 | Initial release — WebDev Cosmos, XP system, achievements |
| **2.0** | April 2026 | Added: Boss Rush, Endless, Survival, Randomizer, Side Quests, Difficulty Scaling, Unlock Cinematics, Secret Worlds, Rival NPC, Seasonal Events, Checkpoints, Resume Prompt, Import/Export, Share Codes, Report Card, World Builder, AI World Generator, Accessibility, Deep Stats, Streak Calendar, Performance Timeline, Mastery Levels, Custom Questions, Terminal Sound Effects |

---

<p align="center">
  <sub>📚 jtlearn Documentation • <a href="https://github.com/kashsight/kslearn">GitHub</a> • <a href="https://kash-sight.web.app">Website</a></sub>
</p>
