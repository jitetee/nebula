# 🌐 kslearn Online Mode — Complete Documentation

> **Version 2.2.0** — Selective Sync, New Menu Structure, Cloud Browsing

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup & Installation](#setup--installation)
4. [Firebase Configuration](#firebase-configuration)
5. [Authentication](#authentication)
6. [Features](#features)
   - [Profile & Account](#profile--account)
   - [Auto-Sync on Login](#auto-sync-on-login)
   - [Notes Sync](#notes-sync)
   - [Courses Sync](#courses-sync)
   - [Worlds (Online & Local)](#worlds-online--local)
   - [Search World by ID](#search-world-by-id)
   - [Multiplayer Verse](#multiplayer-verse)
   - [Open Game Sessions](#open-game-sessions)
   - [Leaderboards](#leaderboards)
   - [Friends System](#friends-system)
7. [Online vs Offline Rules](#online-vs-offline-rules)
8. [Firebase RTDB Structure](#firebase-rtdb-structure)
9. [Security Rules](#security-rules)
10. [Settings & Configuration](#settings--configuration)
11. [API Reference](#api-reference)
12. [Troubleshooting](#troubleshooting)

---

## Overview

kslearn Online Mode connects your local learning experience to the cloud via Firebase Realtime Database. It enables:

- **Cloud sync** — Stats, notes, courses auto-sync on login
- **Multiplayer** — Play KSL-Verse with friends in real-time
- **Content sharing** — Upload worlds for others to play
- **Social features** — Friends, leaderboards, game sessions

### Key Design Principles

| Principle | Description |
|-----------|-------------|
| **Online = Virtual Play** | Online worlds are played virtually, never downloaded |
| **Offline = Download + Play** | Local worlds can be opened and saved to disk |
| **Auto-Sync** | All local data syncs to cloud automatically on login |
| **Toggle-able** | Each sync type can be enabled/disabled independently |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    kslearn CLI                          │
│                                                         │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ Local Data   │  │ Online Mode   │  │ Verse Engine │ │
│  │ ~/.kslearn/  │  │ (firebase)    │  │ (multiplayer)│ │
│  └──────┬───────┘  └───────┬───────┘  └──────┬───────┘ │
│         │                  │                  │         │
│         └──────────────────┼──────────────────┘         │
│                            │                            │
│              ┌─────────────▼─────────────┐              │
│              │  Firebase RTDB Client     │              │
│              │  (REST API + Auth)        │              │
│              └─────────────┬─────────────┘              │
└────────────────────────────┼────────────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │   Firebase RTDB Cloud       │
              │                             │
              │  /users/{uid}/              │
              │    ├── stats                │
              │    ├── notes                │
              │    ├── courses              │
              │    ├── friends              │
              │    └── sync_settings        │
              │  /worlds/{world_id}         │
              │  /game_sessions/{session}   │
              │  /leaderboard               │
              │  /invites                   │
              └─────────────────────────────┘
```

---

## Setup & Installation

### Install from PyPI (future)
```bash
pip install kslearn[online]
```

### Install from source
```bash
cd kslearn
pip install -e ".[online]"
```

### Dependencies
```
requests     # Firebase REST API
rich         # Terminal UI
click        # CLI framework
```

---

## Firebase Configuration

### Default: Works Out of the Box

kslearn ships with a pre-configured Firebase project (`kashsight-4cbb8`). After `git clone` and `pip install -e .`, the app connects immediately — no setup required.

The API key is hardcoded in `firebase_rtdb.py` as a **default** because:
- Firebase API keys are **public project identifiers** (visible in every web app's source)
- Real security comes from **Firebase Security Rules** (`auth != null`), not hiding the key
- This allows instant `git clone → run` without manual configuration

### Using Your Own Firebase Project (Optional)

If you want to use your own Firebase project instead:

1. **Create a `.env` file** in the kslearn root:
   ```bash
   cp .env.example .env
   ```

2. **Fill in your Firebase credentials**:
   ```env
   FIREBASE_API_KEY=your_api_key_here
   FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   FIREBASE_MESSAGING_SENDER_ID=your_sender_id
   FIREBASE_APP_ID=your_app_id
   FIREBASE_MEASUREMENT_ID=your_measurement_id
   ```

3. **Install python-dotenv** (optional, auto-loaded if available):
   ```bash
   pip install python-dotenv
   ```

Environment variables override the defaults automatically.

### Deploy Security Rules
1. Go to Firebase Console → Database → Rules
2. Paste contents of `firebase-rtdb-rules.json`
3. Click **Publish**

---

## Authentication

### Login/Signup Flow

```bash
kslearn              # Main menu → D. Profiles → 1. Login
# OR
kslearn online       # Direct online mode
```

**Login Options:**
1. **Email/Password** — Full access, cloud sync
2. **Create Account** — New user registration
3. **Guest Mode** — Limited features, no sync

### Password Masking
Passwords display as `*****` for security (termios-based raw input).

### Session Persistence
- Auth token cached in `~/.kslearn/online_session.json`
- 24-hour expiry
- Auto-restored on next launch

---

## Features

### Profile & Account

**Access:** Main Menu → `10. Profile & Account`

Shows:
- Online login status
- Current XP and Level
- Local profiles list
- Quick login/signup options
- Online account management (sync, friends, leaderboard)

### Auto-Sync on Login

When you login, three sync operations run automatically:

| Sync Type | What it syncs | RTDB Path |
|-----------|--------------|-----------|
| **Stats** | Verse XP, levels, combos, achievements, session stats, streaks | `/users/{uid}/stats` |
| **Notes** | All note categories with content | `/users/{uid}/notes` |
| **Courses** | All hierarchical courses | `/users/{uid}/courses` |

**Control:** Settings → Toggle individual sync types ON/OFF

### Notes Sync

```bash
kslearn online → 7. Sync Notes
```

**How it works:**
1. A table shows ALL your local note categories AND cloud notes side-by-side
2. Each row shows: name, local status (✅/❌), cloud status (☁️/—), and suggested action
3. Select items by number:
   - **Single**: Type `1` or `3`
   - **Multiple**: Type `1,3,5` (comma-separated)
   - **All**: Type `A`
4. Items marked "Both" exist locally and in cloud — they are skipped unless you choose "A"
5. Items marked "Upload" exist locally only — they get pushed to cloud
6. Items marked "Download" exist in cloud only — they get pulled to local

**Options:**
1. **Select by number(s)** — Upload local items, download cloud-only items
2. **A** — Sync ALL (upload everything local, download everything cloud-only)
3. **B** — Back to online menu

### Courses Sync

```bash
kslearn online → 8. Sync Courses
```

Same selective table as notes. Shows all local and cloud courses with icons and actions. Select by number(s) or `A` for all.

### Worlds (Online & Local)

```bash
kslearn online → 4. Browse Worlds
```

**Shows both:**
- **Local worlds** (yellow "Local" tag) — Opens normally, saved to disk
- **Online worlds** (cyan "Online" tag) — Played virtually, changes not saved

| Action | Local World | Online World |
|--------|-------------|--------------|
| **Play** | Opens verse engine with full save | Plays virtually, changes discarded |
| **Like** | N/A | Increments download counter |
| **Download** | Already local | Not supported (virtual only) |

### Search World by ID

```bash
kslearn online → 5. Search World by ID
```

Enter exact world ID → View details → Play virtually.

### Multiplayer Verse

```bash
kslearn online → 9. Multiplayer Verse
```

**Options:**
1. **Create Session** — Generate unique session code
2. **Join Session** — Enter session code from friend
3. **Close Session** — End your active sessions

**Session codes:** `ksverse_XXXXXXXX` (8 random chars)

### Open Game Sessions

```bash
kslearn online → 10. Open Sessions
```

Shows all sessions with `status: "waiting"`:
- Session name
- Player count
- Description
- Creation time

Join directly or view details first.

### Leaderboards

```bash
kslearn online → 3. Leaderboards
```

Global rankings by:
- Total XP
- Level
- Worlds completed

### Friends System

```bash
kslearn online → 2. Friends
```

- Add/remove friends by user ID
- See who's online
- Invite to game sessions

---

## Online vs Offline Rules

| Feature | Online Mode | Offline Mode |
|---------|-------------|--------------|
| **Worlds** | Play virtually only | Open, edit, save |
| **Notes** | Sync to/from cloud | Local only |
| **Courses** | Sync to/from cloud | Local only |
| **Progress** | Saved to cloud + local | Saved locally only |
| **Multiplayer** | Yes (RTDB sync) | No |
| **Leaderboards** | Global rankings | Local only |

---

## Firebase RTDB Structure

```
/users/{uid}/
├── username: string
├── email: string
├── xp: number
├── level: number
├── status: "online" | "offline" | "in-game"
├── created_at: ISO timestamp
├── last_seen: ISO timestamp
├── friends: { [friendUid]: { username, status, added_at } }
├── settings: { theme, daily_goal }
├── stats:
│   ├── verse_progress: { total_xp, worlds, combo_count, ... }
│   ├── session_stats: { total_sessions, total_duration, ... }
│   ├── learning_progress: { ... }
│   ├── achievements: [ ... ]
│   ├── streak_data: { ... }
│   ├── daily_study: { ... }
│   ├── total_xp: number
│   ├── level: number
│   └── last_synced: ISO timestamp
├── notes:
│   └── {category_id}: { title, content (JSON string), last_updated }
├── courses:
│   └── {course_id}: { title, content (JSON string), last_updated }
└── sync_settings:
    ├── auto_sync_stats: boolean
    ├── auto_sync_notes: boolean
    └── auto_sync_courses: boolean

/worlds/{world_id}
├── title: string
├── description: string
├── author: string
├── creator_uid: string
├── world_data: JSON string
├── downloads: number
├── likes: number
├── created_at: ISO timestamp
├── version: number
└── tags: string

/game_sessions/{session_id}
├── session_name: string
├── creator_uid: string
├── status: "waiting" | "in-progress" | "finished"
├── description: string
├── created_at: ISO timestamp
├── expires_at: ISO timestamp
├── players: { [uid]: { username, joined_at, role } }
├── world_data: JSON string
└── game_data: JSON string

/leaderboard/{uid}
├── username: string
├── xp: number
├── level: number
└── last_updated: ISO timestamp

/invites/{invite_id}
├── from_uid: string
├── to_uid: string
├── type: "friend_request" | "game_invite" | "world_share"
├── data: string
├── status: "pending" | "accepted" | "declined" | "expired"
└── created_at: ISO timestamp
```

---

## Security Rules

Deploy `firebase-rtdb-rules.json` to Firebase Console.

**Key protections:**
- Users can only write to their own data (`$uid === auth.uid`)
- Worlds are public read, authenticated write
- Game sessions require authentication
- All fields validated for type and length
- No unknown paths allowed (`$other: { ".validate": false }`)

---

## Settings & Configuration

### Online Settings Menu
```bash
kslearn online → S. Settings
```

| Option | Description |
|--------|-------------|
| **1. Auto-sync stats** | Toggle XP/level/achievement sync on login |
| **2. Auto-sync notes** | Toggle notes sync on login |
| **3. Auto-sync courses** | Toggle courses sync on login |
| **4. Clear session** | Remove cached auth token |
| **5. Reset settings** | Clear all online config |

### Sync Settings Storage
Stored in `/users/{uid}/sync_settings` in RTDB — persists across devices.

---

## API Reference

### FirebaseRTDB Class

```python
from kslearn.online.firebase_rtdb import get_firebase, FirebaseRTDB

firebase = get_firebase()

# Auth
firebase.signup(email, password, username) -> bool
firebase.login(email, password) -> bool
firebase.login_anonymous() -> bool
firebase.logout()
firebase.load_session() -> bool
firebase.is_logged_in() -> bool

# Sync
firebase.sync_offline_stats() -> bool
firebase.sync_notes_to_cloud() -> bool          # Sync ALL notes (legacy)
firebase.sync_notes_from_cloud() -> Dict        # Download ALL notes (legacy)
firebase.sync_courses_to_cloud() -> bool        # Sync ALL courses (legacy)
firebase.sync_courses_from_cloud() -> Dict      # Download ALL courses (legacy)

# Selective Sync (NEW — v2.2.0)
firebase.get_local_notes_categories() -> List[Dict]     # List local note categories
firebase.get_local_courses() -> List[Dict]              # List local courses
firebase.list_cloud_notes() -> Dict                     # List cloud note metadata
firebase.list_cloud_courses() -> Dict                   # List cloud course metadata
firebase.sync_single_note_to_cloud(cat_id) -> bool      # Upload one category
firebase.sync_single_note_from_cloud(cat_id) -> bool    # Download one category
firebase.sync_single_course_to_cloud(course_id) -> bool # Upload one course
firebase.sync_single_course_from_cloud(course_id) -> bool

# Settings
firebase.get_sync_settings() -> Dict
firebase.update_sync_setting(key, value) -> bool

# Worlds
firebase.list_worlds(filter_type) -> List[Dict]
firebase.search_world_by_id(world_id) -> Optional[Dict]
firebase.download_world(world_id) -> Optional[Dict]
firebase.upload_world(world_id, title, description, world_data) -> bool
firebase.like_world(world_id) -> bool

# Sessions
firebase.create_game_session(session_id, uid, data) -> bool
firebase.join_game_session(session_id) -> bool
firebase.get_open_game_sessions() -> Dict

# Friends
firebase.add_friend(friend_id) -> bool
firebase.get_friends() -> Dict
firebase.get_online_friends() -> Dict
firebase.remove_friend(friend_id) -> bool

# Leaderboard
firebase.update_leaderboard() -> bool
firebase.get_leaderboard(metric, limit) -> List[Dict]
```

### Verse Engine Multiplayer

```python
from kslearn.engines.verse_engine import run_verse_interactive, VerseEngine

# With multiplayer
run_verse_interactive(
    multiplayer=True,
    session_id="ksverse_abc123",
    firebase=firebase_instance
)

# VerseEngine with multiplayer
engine = VerseEngine(
    multiplayer=True,
    session_id="ksverse_abc123",
    firebase=firebase_instance
)
```

---

## Troubleshooting

### "API key not valid"
1. Verify API key in `firebase_rtdb.py` (or check your `.env`)
2. Check Firebase Console → Project Settings → Web API Key
3. Ensure Authentication is enabled

### "401 Unauthorized"
- Token expired — logout and login again
- Rules not deployed — check Firebase Console → Rules
- User not authenticated — verify `firebase.is_logged_in()`

### "No worlds found"
- Create a world in KSL-Verse first
- Check `~/.kslearn/data/ksl/*_verse.json` exists

### Sync fails silently
- Check internet connection
- Verify Firebase RTDB is enabled
- Check security rules deployed

### Password not masking
- Only works on Unix/Termux (uses `termios`)
- Windows fallback uses standard input

### Selective sync shows wrong data
- Cloud data might be in legacy format (raw JSON strings) — handled automatically
- If a category/course appears as "Both" but you know it's only local, check Firebase Console

---

## File Reference

| File | Purpose |
|------|---------|
| `kslearn/online/firebase_rtdb.py` | Firebase RTDB client, auth, sync, selective sync CRUD |
| `kslearn/online/online_mode.py` | Terminal UI menus, handlers |
| `kslearn/engines/verse_engine.py` | Verse engine with multiplayer support |
| `kslearn/cli.py` | CLI integration, profile menu (option 10) |
| `kslearn/firebase_config.py` | Centralized Firebase config with env var override |
| `kslearn/constants.py` | Content type constants, menu definitions |
| `kslearn/navigation.py` | Breadcrumb system, consistent menu rendering |
| `firebase-rtdb-rules.json` | Firebase security rules |
| `.env.example` | Firebase credentials template |
| `docs/ONLINE_MODE.md` | This documentation |

---

*Last updated: April 11, 2026*
