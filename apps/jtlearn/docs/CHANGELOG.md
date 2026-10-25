# 📋 jtlearn Changelog

> **All changes documented by version and release date.**

<p align="center">
  <sub>📝 Changelog • jtlearn 2.2.0</sub>
</p>

---

## [2.2.0] — 2026-04-11

### 🌐 Online Mode — Selective Sync

| # | Change | File(s) | Impact |
|:---|:---|:---|:---|
| 1 | **Selective notes sync** — browse & pick individual categories to upload/download | `online_mode.py`, `firebase_rtdb.py` | No more upload-all; choose specific notes |
| 2 | **Selective courses sync** — browse & pick individual courses to upload/download | `online_mode.py`, `firebase_rtdb.py` | Same selective table for courses |
| 3 | **Cloud browsing table** — shows local ✅/❌ vs cloud ☁️ with suggested action | `online_mode.py` | Clear visual of what will sync |
| 4 | **Multi-select by comma** — type `1,3,5` or `A` for all | `online_mode.py` | Flexible selection |
| 5 | **Legacy cloud data handling** — `isinstance()` check for dict vs string cloud data | `firebase_rtdb.py` | No crashes on old-format data |

### 🗂️ Menu Restructure (No Duplicates)

| # | Change | Before | After |
|:---|:---|:---|:---|
| 6 | JT-Verse moved from 9 to 4 | "9. JT-Verse" | "4. JT-Verse" |
| 7 | Profile merged into option 10 | "D. Profiles" separate | "10. Profile & Account" |
| 8 | Settings moved from C to S | "C. Settings" | "S. Settings" |
| 9 | Help + Support merged into H | Separate S + H | "H. Support & Help" |
| 10 | Duplicate choice "9" removed | Two `elif choice == "9"` blocks | One clean block |
| 11 | Prompt updated | "1-9, O, S, F, L, D, C, H, 0" | "1-10, F, L, O, S, H, 0" |

### 🔧 Bug Fixes

| # | Change | File(s) | Impact |
|:---|:---|:---|:---|
| 12 | **Hardcoded Firebase key** → env var with default fallback | `firebase_rtdb.py` | Works out-of-box; override via `.env` |
| 13 | **`json_brain` import error** in tutorials | `engines/tutorials.py` | Replaced with `content_loader.load_brain_qa()` |
| 14 | **`courses.get()` on list** in verse engine | `engines/verse_engine.py` | Fixed to iterate list directly |
| 15 | **`ContentManager` references** (4×) → `content_loader` | `firebase_rtdb.py` | Replaced with correct singleton |
| 16 | **Version consistency** — all references v2.0.0 | `ui.py`, `update_checker.py`, `support.py` | No more v1.0.0 banners |

### 🗑️ Cleanup

| # | Change | File(s) | Impact |
|:---|:---|:---|:---|
| 17 | **Deleted deprecated `main.py`** | `main.py` (removed) | No more deprecated entry point |
| 18 | **Deleted `main/learning_notes.py`** | `main/learning_notes.py` (removed) | Redirect stub removed |
| 19 | **Updated `main/__init__.py`** | `main/__init__.py` | Removed deleted imports |
| 20 | **License fixed** — Proprietary → MIT | `pyproject.toml` | Matches actual LICENSE file |
| 21 | **Removed `firebase-admin` dep** | `pyproject.toml` | Never used; REST API only |
| 22 | **Added `python-dotenv` optional dep** | `pyproject.toml` | For `.env` file support |
| 23 | **Package list updated** | `pyproject.toml` | Added `jtlearn.config`, `jtlearn.online` |
| 24 | **Protector scans `.jif` files** | `protector.py` | Was scanning `.json` (no content there) |

### 📁 New Files

| # | File | Purpose |
|:---|:---|:---|
| 25 | `jtlearn/constants.py` | Centralized content type constants + menu definitions |
| 26 | `jtlearn/navigation.py` | Breadcrumb system + consistent menu rendering |
| 27 | `.env.example` | Firebase credentials template for custom projects |

### 📄 Documentation

| # | Change | Details |
|:---|:---|:---|
| 28 | **ONLINE_MODE.md updated** | Selective sync, new menu numbers, Firebase config docs |
| 29 | **`.gitignore` updated** | Added `.env`, `.env.local`, `.env.*.local` |
| 30 | **CHANGELOG.md** | This entry |

---

## [2.0.0] — 2026-04-10

### 🛡️ Data Integrity & Safety

| # | Change | File(s) | Impact |
|:---|:---|:---|:---|
| 1 | **Atomic config writes** using `tempfile.mkstemp()` + `os.replace()` | `config.py` | Prevents `settings.json` corruption on crash or power loss |
| 2 | **File locking** via `fcntl.flock()` for concurrent write protection | `config.py` | Eliminates race conditions when multiple processes write config simultaneously |
| 3 | **Removed SSL certificate bypass** (`ssl.CERT_NONE`) | `main/datastore.py` | Restores proper HTTPS certificate verification for downloads |

### 🔧 Performance & Code Quality

| # | Change | File(s) | Impact |
|:---|:---|:---|:---|
| 4 | **Removed redundant glob** — replaced 3× glob calls with single `directory.glob("*.jif")` | `jif_loader.py` | Faster `.jif` file discovery, less memory usage |
| 5 | **Added `total_questions` to `QuizEngine.__init__()`** | `engines/quiz_engine.py` | Fixes uninitialized attribute error in timed/review quiz modes |
| 6 | **`subprocess.run` timeout** already present on `tgpt` calls (60s) | `main/ai_chat.py` | No change needed — already protected against hangs |

### 🏗️ Architecture

| # | Change | File(s) | Impact |
|:---|:---|:---|:---|
| 7 | **Deprecated `main.py`** — added deprecation warning + docstring directing users to CLI | `main.py` | Eliminates dual-entry-point confusion; legacy `python -m jtlearn` now routes to `cli.py` |
| 8 | **`__main__.py` now routes to `cli.py`** instead of `main.py` | `__main__.py` | Consistent behavior regardless of entry point |
| 9 | **`setup.py` reads version from `__init__.py`** (`from jtlearn import __version__`) | `setup.py` | Single source of truth — no more version drift |

### 🔢 Version Sync

| # | Change | Before | After |
|:---|:---|:---|:---|
| 10 | `jtlearn/__init__.py` version | `1.0.0` | `2.0.0` (matches README badge) |

### 📄 Documentation

| # | Change | Details |
|:---|:---|:---|
| 11 | **This changelog** | New file — all changes tracked going forward |
| 12 | README already references v2.0.0 | Now consistent with code version |

---

### Technical Details: Atomic Config Writes

**Before (vulnerable to corruption):**
```python
with open(path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2)  # Crash mid-write = corrupted file
```

**After (atomic, crash-safe):**
```python
fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".settings_tmp_", suffix=".json")
with os.fdopen(fd, "w", encoding="utf-8") as tmp_f:
    json.dump(config, tmp_f, indent=2, ensure_ascii=False)
    tmp_f.flush()
    os.fsync(tmp_f.fileno())
os.replace(tmp_path, str(path))  # Atomic rename — always complete or not
```

### Technical Details: File Locking

```python
@contextmanager
def _file_lock(filepath: Path):
    lock_path = filepath.with_suffix(".lock")
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield lock_file
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass
```

### Technical Details: Redundant Glob Fix

**Before (3× glob, redundant):**
```python
for f in glob_mod.glob(str(directory / "*.jif")):   # glob module
    all_files.add(Path(f).resolve())
for f in directory.glob("*.jif"):                    # pathlib glob
    all_files.add(f.resolve())
for f in directory.glob("*.jif.jif"):                # typo pattern
    all_files.add(f.resolve())
```

**After (single glob, correct):**
```python
return sorted(f.resolve() for f in directory.glob("*.jif"))
```

---

## Version History Summary

| Version | Date | Highlights |
|:---|:---|:---|
| **2.0.0** | 2026-04-10 | Atomic config writes, file locking, deprecated `main.py`, version sync, SSL fix |
| **1.0.0** | — | Initial release with quiz engine, notes, AI chat, JT-Verse, `.jif` packages |

---

<p align="center">
  <sub>📚 jtlearn Documentation • <a href="https://github.com/jitetee/nebula">GitHub</a> • <a href="https://kash-sight.web.app">Website</a></sub>
</p>
