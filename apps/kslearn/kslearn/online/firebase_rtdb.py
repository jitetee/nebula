"""
kslearn Firebase RTDB Integration - Online Mode

Handles:
- User authentication (anonymous + email/password)
- Real-time multiplayer sync via RTDB
- Content sharing (JSON as text)
- Global leaderboards
- Friend system

Firebase API keys are public project identifiers. Security is enforced by
Firebase Security Rules (auth != null), not by hiding the key.
See: https://firebase.google.com/docs/projects/api-keys
"""

import json
import os
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from kslearn.ui import console, show_panel, show_error, show_info, show_success, show_warning
from kslearn.config import load_config, save_config

# ─── Firebase Configuration ──────────────────────────────────────────
# API keys are public project identifiers. Real security comes from
# Firebase Security Rules (auth != null), not from hiding these values.
# Users can override via .env or env vars to use their own project.

FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY", "AIzaSyAta1rlqXCP5_rYAUsUtKRL606taZXzQ2g"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", "kashsight-4cbb8.firebaseapp.com"),
    "databaseURL": os.getenv(
        "FIREBASE_DATABASE_URL",
        "https://kashsight-4cbb8-default-rtdb.firebaseio.com",
    ),
    "projectId": os.getenv("FIREBASE_PROJECT_ID", "kashsight-4cbb8"),
    "storageBucket": os.getenv(
        "FIREBASE_STORAGE_BUCKET", "kashsight-4cbb8.appspot.com"
    ),
    "messagingSenderId": os.getenv(
        "FIREBASE_MESSAGING_SENDER_ID", "394824465014"
    ),
    "appId": os.getenv(
        "FIREBASE_APP_ID", "1:394824465014:web:3c29bfc8676dfc84397d57"
    ),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", "G-BN16V4S3JY"),
}

FIREBASE_RTDB_URL = FIREBASE_CONFIG["databaseURL"]
FIREBASE_API_KEY = FIREBASE_CONFIG["apiKey"]
FIREBASE_PROJECT = FIREBASE_CONFIG["projectId"]


def read_password_masked(prompt_text: str = "Password") -> str:
    """Read password showing asterisks instead of blank"""
    import sys
    import termios
    import tty

    # Flush stdin to clear any leftover input
    try:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass
    
    console.print(f"[dim]{prompt_text}:[/dim] ", end="")
    console.file.flush()
    
    password = []
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        tty.setraw(fd)
        while True:
            char = sys.stdin.read(1)
            
            # Enter key
            if char in ('\r', '\n'):
                console.print()
                break
            # Ctrl+C
            elif char == '\x03':
                console.print()
                raise KeyboardInterrupt
            # Backspace
            elif char in ('\x7f', '\x08'):
                if password:
                    password.pop()
                    # Move cursor back, print space, move back again
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            # Regular character
            elif ord(char) >= 32:
                password.append(char)
                sys.stdout.write('*')
                sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    return ''.join(password)


class FirebaseRTDB:
    """Firebase Realtime Database client for terminal-based kslearn"""

    def __init__(self, api_key: str = None, db_url: str = None):
        self.api_key = api_key or FIREBASE_API_KEY
        self.db_url = db_url or FIREBASE_RTDB_URL
        self.project_id = FIREBASE_CONFIG["projectId"]
        self.auth_token = None
        self.user_id = None
        self.user_data = {}
        self._listeners = []

    def _url(self, path: str) -> str:
        """Build Firebase RTDB URL"""
        return f"{self.db_url}/{path}.json"

    def _auth_url(self, path: str) -> str:
        """Build Firebase RTDB URL with auth"""
        if self.auth_token:
            from urllib.parse import quote
            encoded_token = quote(self.auth_token, safe='')
            return f"{self.db_url}/{path}.json?auth={encoded_token}"
        return self._url(path)
    
    # ─── HTTP Helpers ─────────────────────────────────────────────

    def _masked_error(self, operation: str) -> str:
        """Return a user-friendly error without exposing Firebase details"""
        return f"{operation} failed. Check your connection and try again."

    def _get(self, path: str) -> Optional[Dict]:
        """GET from RTDB"""
        try:
            resp = requests.get(self._auth_url(path), timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                show_warning("Authentication expired. Please re-login.")
            else:
                show_warning(self._masked_error("Fetch"))
            return None
        except Exception:
            show_warning(self._masked_error("Fetch"))
            return None

    def _put(self, path: str, data: Dict) -> bool:
        """PUT to RTDB (overwrite)"""
        try:
            resp = requests.put(self._auth_url(path), json=data, timeout=10)
            resp.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                show_warning("Authentication expired. Please re-login.")
            else:
                show_warning(self._masked_error("Save"))
            return False
        except Exception:
            show_warning(self._masked_error("Save"))
            return False

    def _patch(self, path: str, data: Dict) -> bool:
        """PATCH RTDB (update)"""
        try:
            resp = requests.patch(self._auth_url(path), json=data, timeout=10)
            resp.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                show_warning("Authentication expired. Please re-login.")
            else:
                show_warning(self._masked_error("Update"))
            return False
        except Exception:
            show_warning(self._masked_error("Update"))
            return False

    def _post(self, path: str, data: Dict) -> Optional[str]:
        """POST to RTDB (push with auto-generated key)"""
        try:
            resp = requests.post(self._auth_url(path), json=data, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            return result.get("name")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                show_warning("Authentication expired. Please re-login.")
            else:
                show_warning(self._masked_error("Create"))
            return None
        except Exception:
            show_warning(self._masked_error("Create"))
            return None

    def _delete(self, path: str) -> bool:
        """DELETE from RTDB"""
        try:
            resp = requests.delete(self._auth_url(path), timeout=10)
            resp.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                show_warning("Authentication expired. Please re-login.")
            else:
                show_warning(self._masked_error("Delete"))
            return False
        except Exception:
            show_warning(self._masked_error("Delete"))
            return False
    
    # ─── Authentication ──────────────────────────────────────────
    
    def signup(self, email: str, password: str, username: str) -> bool:
        """Create new user account via Firebase Auth REST API"""
        if not HAS_REQUESTS:
            show_error("requests library required. Install: pip install requests")
            return False

        signup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        try:
            resp = requests.post(signup_url, json=payload, timeout=10)
            data = resp.json()

            if "error" in data:
                error_msg = data['error']['message']
                
                # Provide user-friendly error messages
                if "API_KEY_NOT_VALID" in error_msg or "API key not valid" in error_msg:
                    show_error(f"Firebase API key is invalid!")
                    console.print()
                    console.print("[yellow]To fix this:[/yellow]")
                    console.print("[dim]1. Go to https://console.firebase.google.com[/dim]")
                    console.print("[dim]2. Select your project → Project Settings[/dim]")
                    console.print("[dim]3. Copy the 'Web API Key'[/dim]")
                    console.print("[dim]4. Update FIREBASE_CONFIG in firebase_rtdb.py[/dim]")
                    console.print()
                    return False
                elif "EMAIL_EXISTS" in error_msg:
                    show_error("Email already registered. Please login instead.")
                    return False
                elif "WEAK_PASSWORD" in error_msg:
                    show_error("Password too weak. Use at least 6 characters.")
                    return False
                else:
                    show_error(f"Signup failed: {error_msg}")
                    return False

            self.auth_token = data["idToken"]
            self.user_id = data["localId"]

            # Create user profile in RTDB
            profile = {
                "username": username,
                "email": email,
                "created_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "status": "online",
                "xp": 0,
                "level": 1,
                "friends": {},
                "settings": {
                    "theme": "sky_blue",
                    "daily_goal": 15
                }
            }

            self._put(f"users/{self.user_id}", profile)
            self.user_data = profile

            # Save auth locally
            self._save_session()

            show_success(f"Account created! Welcome, {username}!")
            return True

        except requests.exceptions.RequestException as e:
            show_error(f"Network error: {e}")
            return False
        except Exception as e:
            show_error(f"Signup error: {e}")
            return False
    
    def login(self, email: str, password: str) -> bool:
        """Login with email/password"""
        if not HAS_REQUESTS:
            show_error("requests library required. Install: pip install requests")
            return False

        login_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        try:
            resp = requests.post(login_url, json=payload, timeout=10)
            data = resp.json()

            if "error" in data:
                error_msg = data['error']['message']
                
                # Provide user-friendly error messages
                if "API_KEY_NOT_VALID" in error_msg or "API key not valid" in error_msg:
                    show_error(f"Firebase API key is invalid!")
                    console.print()
                    console.print("[yellow]To fix this:[/yellow]")
                    console.print("[dim]1. Go to https://console.firebase.google.com[/dim]")
                    console.print("[dim]2. Select project → Settings → General[/dim]")
                    console.print("[dim]3. Copy 'Web API Key'[/dim]")
                    console.print("[dim]4. Edit kslearn/online/firebase_rtdb.py[/dim]")
                    console.print("[dim]5. Update FIREBASE_CONFIG['apiKey'][/dim]")
                    console.print()
                    return False
                elif "INVALID_PASSWORD" in error_msg:
                    show_error("Incorrect password. Please try again.")
                    return False
                elif "EMAIL_NOT_FOUND" in error_msg:
                    show_error("No account found with this email. Please signup first.")
                    return False
                elif "INVALID_LOGIN_CREDENTIALS" in error_msg:
                    show_error("Invalid email or password.")
                    return False
                else:
                    show_error(f"Login failed: {error_msg}")
                    return False

            self.auth_token = data["idToken"]
            self.user_id = data["localId"]

            # Load user profile from RTDB
            profile = self._get(f"users/{self.user_id}")
            if profile:
                self.user_data = profile
                # Update status to online
                self._patch(f"users/{self.user_id}", {
                    "status": "online",
                    "last_seen": datetime.now().isoformat()
                })
                self._save_session()
                show_success(f"Welcome back, {profile.get('username', 'User')}!")
                return True
            else:
                show_error("User profile not found in database")
                return False

        except requests.exceptions.RequestException as e:
            show_error(f"Network error: {e}")
            return False
        except Exception as e:
            show_error(f"Login error: {e}")
            return False
    
    def login_anonymous(self) -> bool:
        """Login anonymously for limited access"""
        self.user_id = f"anon_{int(time.time())}_{hash(str(time.time()))}"
        self.auth_token = None
        self.user_data = {
            "username": f"Guest_{self.user_id[-6:]}",
            "email": None,
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "status": "online",
            "xp": 0,
            "level": 1,
            "friends": {},
            "is_anonymous": True
        }
        
        # Save anonymous profile to RTDB
        self._put(f"users/{self.user_id}", self.user_data)
        self._save_session()
        
        show_info(f"Logged in as {self.user_data['username']} (limited features)")
        return True
    
    def logout(self):
        """Logout and set status offline"""
        if self.user_id and not self.user_data.get("is_anonymous"):
            self._patch(f"users/{self.user_id}", {
                "status": "offline",
                "last_seen": datetime.now().isoformat()
            })
        
        self.auth_token = None
        self.user_id = None
        self.user_data = {}
        
        # Clear session
        session_file = Path.home() / ".kslearn" / "online_session.json"
        if session_file.exists():
            session_file.unlink()
        
        show_info("Logged out successfully")
    
    def _save_session(self):
        """Save auth session locally for persistence"""
        session_dir = Path.home() / ".kslearn"
        session_dir.mkdir(exist_ok=True)
        
        session_file = session_dir / "online_session.json"
        session_data = {
            "user_id": self.user_id,
            "auth_token": self.auth_token,
            "user_data": self.user_data,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)
    
    def load_session(self) -> bool:
        """Load saved session"""
        session_file = Path.home() / ".kslearn" / "online_session.json"
        if not session_file.exists():
            return False
        
        try:
            with open(session_file) as f:
                session_data = json.load(f)
            
            # Check if session is less than 24 hours old
            saved_at = datetime.fromisoformat(session_data["saved_at"])
            if (datetime.now() - saved_at).total_seconds() > 86400:
                session_file.unlink()
                return False
            
            self.user_id = session_data["user_id"]
            self.auth_token = session_data["auth_token"]
            self.user_data = session_data["user_data"]
            
            # Update status to online
            if self.user_id and not self.user_data.get("is_anonymous"):
                self._patch(f"users/{self.user_id}", {
                    "status": "online",
                    "last_seen": datetime.now().isoformat()
                })
            
            show_success(f"Session restored. Welcome back, {self.user_data.get('username', 'User')}!")
            return True
            
        except Exception as e:
            show_warning(f"Failed to load session: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        return self.user_id is not None
    
    # ─── User Profile ────────────────────────────────────────────
    
    def update_profile(self, updates: Dict) -> bool:
        """Update user profile"""
        if not self.user_id:
            return False
        
        updates["last_seen"] = datetime.now().isoformat()
        success = self._patch(f"users/{self.user_id}", updates)
        if success:
            self.user_data.update(updates)
        return success
    
    def get_profile(self, user_id: str = None) -> Optional[Dict]:
        """Get user profile"""
        uid = user_id or self.user_id
        if not uid:
            return None
        return self._get(f"users/{uid}")

    def sync_offline_stats(self) -> bool:
        """Sync offline stats/analytics to Firebase RTDB on login.
        
        Collects verse_progress, session_stats, learning_progress, etc.
        from local config and writes them to the user's RTDB profile.
        """
        if not self.user_id:
            return False

        try:
            from kslearn.config import load_config, get_session_stats
            
            config = load_config()
            
            # Gather all offline stats
            verse_progress = config.get("verse_progress", {})
            session_stats = get_session_stats()
            learning_progress = config.get("learning_progress", {})
            achievements = config.get("achievements", [])
            streak_data = config.get("streak_data", {})
            daily_study = config.get("daily_study", {})
            
            # Build stats payload for RTDB
            stats_payload = {
                "verse_progress": {
                    "total_xp": verse_progress.get("total_xp", 0),
                    "worlds": verse_progress.get("worlds", {}),
                    "combo_count": verse_progress.get("combo_count", 0),
                    "combo_multiplier": verse_progress.get("combo_multiplier", 1.0),
                    "achievements": verse_progress.get("achievements", []),
                    "weaknesses": verse_progress.get("weaknesses", {}),
                    "secrets_found": verse_progress.get("secrets_found", []),
                    "session_stats": verse_progress.get("session_stats", {}),
                    "streak_calendar": verse_progress.get("streak_calendar", {}),
                    "prestige_level": verse_progress.get("prestige_level", 0),
                },
                "session_stats": session_stats,
                "learning_progress": learning_progress,
                "achievements": achievements if isinstance(achievements, list) else [],
                "streak_data": streak_data,
                "daily_study": daily_study,
                "last_synced": datetime.now().isoformat(),
            }
            
            # Calculate derived stats
            total_xp = verse_progress.get("total_xp", 0)
            level = 1
            if total_xp >= 200: level = 2
            if total_xp >= 500: level = 3
            if total_xp >= 1000: level = 5
            if total_xp >= 2500: level = 7
            if total_xp >= 5000: level = 10
            
            stats_payload["total_xp"] = total_xp
            stats_payload["level"] = level
            
            # Update user profile in RTDB with stats
            success = self._patch(f"users/{self.user_id}/stats", stats_payload)
            
            if success:
                # Also update local user_data
                self.user_data["stats"] = stats_payload
                self.user_data["total_xp"] = total_xp
                self.user_data["level"] = level
            
            return success

        except Exception:
            # Silently fail - sync can retry later
            return False

    def pull_online_stats(self) -> Optional[Dict]:
        """Pull online stats from Firebase RTDB to merge with local data."""
        if not self.user_id:
            return None
        return self._get(f"users/{self.user_id}/stats")

    # ─── Sync Settings ──────────────────────────────────────────

    def get_sync_settings(self) -> Dict:
        """Get user's sync preferences from RTDB"""
        if not self.user_id:
            return {"auto_sync_stats": True, "auto_sync_notes": True, "auto_sync_courses": True}
        
        settings = self._get(f"users/{self.user_id}/sync_settings")
        if settings is None:
            return {"auto_sync_stats": True, "auto_sync_notes": True, "auto_sync_courses": True}
        return settings

    def update_sync_setting(self, key: str, value: bool) -> bool:
        """Update a sync preference"""
        if not self.user_id:
            return False
        return self._patch(f"users/{self.user_id}/sync_settings", {key: value})

    # ─── Notes Sync ──────────────────────────────────────────────

    def get_local_notes_categories(self, content_mgr=None) -> List[Dict]:
        """Get list of all local note categories with metadata."""
        if content_mgr is None:
            from kslearn.loader import content_loader
            content_mgr = content_loader
        categories = []
        for cat_info in content_mgr.get_all_notes_categories():
            cat_id = cat_info.get("id", cat_info.get("category", ""))
            categories.append({
                "id": cat_id,
                "title": cat_info.get("title", cat_id),
            })
        return categories

    def sync_single_note_to_cloud(self, cat_id: str, content_mgr=None) -> bool:
        """Upload a single note category to Firebase RTDB."""
        if not self.user_id:
            return False
        try:
            if content_mgr is None:
                from kslearn.loader import content_loader
                content_mgr = content_loader
            notes = content_mgr.load_notes(cat_id)
            if not notes:
                return False
            note_data = {
                "title": cat_id,
                "content": json.dumps(notes, ensure_ascii=False),
                "last_updated": datetime.now().isoformat(),
            }
            return self._put(f"users/{self.user_id}/notes/{cat_id}", note_data)
        except Exception:
            return False

    def sync_single_note_from_cloud(self, cat_id: str, content_mgr=None) -> bool:
        """Download a single note category from Firebase RTDB."""
        if not self.user_id:
            return False
        try:
            if content_mgr is None:
                from kslearn.loader import content_loader
                content_mgr = content_loader
            cloud_note = self._get(f"users/{self.user_id}/notes/{cat_id}")
            if not cloud_note:
                return False
            content = json.loads(cloud_note.get("content", "{}"))
            content_mgr.save_notes(cat_id, content)
            return True
        except Exception:
            return False

    def list_cloud_notes(self) -> Dict:
        """List all note categories in cloud (metadata only)."""
        cloud_notes = self._get(f"users/{self.user_id}/notes")
        if not cloud_notes:
            return {}
        result = {}
        for cat_id, cat_data in cloud_notes.items():
            if isinstance(cat_data, dict):
                result[cat_id] = {
                    "title": cat_data.get("title", cat_id),
                    "last_updated": cat_data.get("last_updated", "Unknown"),
                }
            else:
                # Legacy format: raw JSON string
                result[cat_id] = {
                    "title": cat_id,
                    "last_updated": "Unknown",
                }
        return result

    def sync_notes_to_cloud(self, content_mgr=None) -> bool:
        """Sync all local notes to Firebase RTDB"""
        if not self.user_id:
            return False
        
        try:
            if content_mgr is None:
                from kslearn.loader import content_loader
                content_mgr = content_loader

            categories = content_mgr.get_all_notes_categories()
            notes_data = {}
            
            for cat_info in categories:
                cat_id = cat_info.get("id", cat_info.get("category", ""))
                notes = content_mgr.load_notes(cat_id)
                if notes:
                    notes_data[cat_id] = {
                        "title": cat_info.get("title", cat_id),
                        "content": json.dumps(notes, ensure_ascii=False),
                        "last_updated": datetime.now().isoformat(),
                    }
            
            if notes_data:
                success = self._put(f"users/{self.user_id}/notes", notes_data)
                return success
            return True

        except Exception:
            return False

    def sync_notes_from_cloud(self, content_mgr=None) -> Dict:
        """Pull notes from Firebase RTDB to local storage"""
        if not self.user_id:
            return {}
        
        try:
            if content_mgr is None:
                from kslearn.loader import content_loader
                content_mgr = content_loader

            cloud_notes = self._get(f"users/{self.user_id}/notes")
            if not cloud_notes:
                return {}

            synced = {}
            for cat_id, cat_data in cloud_notes.items():
                content = json.loads(cat_data.get("content", "{}"))
                content_mgr.save_notes(cat_id, content)
                synced[cat_id] = cat_data.get("title", cat_id)

            return synced

        except Exception:
            return {}

    # ─── Courses Sync ────────────────────────────────────────────

    def get_local_courses(self, content_mgr=None) -> List[Dict]:
        """Get list of all local hierarchical courses with metadata."""
        if content_mgr is None:
            from kslearn.loader import content_loader
            content_mgr = content_loader
        courses = []
        for course_info in content_mgr.get_all_hierarchical_courses():
            courses.append({
                "id": course_info.get("key", course_info.get("id", "")),
                "title": course_info.get("title", "Untitled"),
                "description": course_info.get("description", ""),
                "icon": course_info.get("icon", "📚"),
            })
        return courses

    def sync_single_course_to_cloud(self, course_id: str, content_mgr=None) -> bool:
        """Upload a single course to Firebase RTDB."""
        if not self.user_id:
            return False
        try:
            if content_mgr is None:
                from kslearn.loader import content_loader
                content_mgr = content_loader
            full_course = content_mgr.load_hierarchical_course(course_id)
            if not full_course:
                return False
            course_data = {
                "title": full_course.get("title", course_id),
                "content": json.dumps(full_course, ensure_ascii=False),
                "last_updated": datetime.now().isoformat(),
            }
            return self._put(f"users/{self.user_id}/courses/{course_id}", course_data)
        except Exception:
            return False

    def sync_single_course_from_cloud(self, course_id: str, content_mgr=None) -> bool:
        """Download a single course from Firebase RTDB."""
        if not self.user_id:
            return False
        try:
            if content_mgr is None:
                from kslearn.loader import content_loader
                content_mgr = content_loader
            cloud_course = self._get(f"users/{self.user_id}/courses/{course_id}")
            if not cloud_course:
                return False
            content = json.loads(cloud_course.get("content", "{}"))
            # Save as a .ksl file would — store in KSL_DIR as JSON for now
            from kslearn.loader import KSL_DIR
            KSL_DIR.mkdir(parents=True, exist_ok=True)
            out_path = KSL_DIR / f"{course_id}_cloud.json"
            out_path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception:
            return False

    def list_cloud_courses(self) -> Dict:
        """List all courses in cloud (metadata only)."""
        cloud_courses = self._get(f"users/{self.user_id}/courses")
        if not cloud_courses:
            return {}
        result = {}
        for course_id, course_data in cloud_courses.items():
            if isinstance(course_data, dict):
                result[course_id] = {
                    "title": course_data.get("title", course_id),
                    "last_updated": course_data.get("last_updated", "Unknown"),
                }
            else:
                result[course_id] = {
                    "title": course_id,
                    "last_updated": "Unknown",
                }
        return result

    def sync_courses_to_cloud(self, content_mgr=None) -> bool:
        """Sync all local hierarchical courses to Firebase RTDB"""
        if not self.user_id:
            return False

        try:
            if content_mgr is None:
                from kslearn.loader import content_loader
                content_mgr = content_loader

            courses = content_mgr.get_all_hierarchical_courses()
            courses_data = {}

            for course in courses:
                course_id = course.get("id", "")
                full_course = content_mgr.load_hierarchical_course(course_id)
                if full_course:
                    courses_data[course_id] = {
                        "title": full_course.get("title", course_id),
                        "content": json.dumps(full_course, ensure_ascii=False),
                        "last_updated": datetime.now().isoformat(),
                    }

            if courses_data:
                success = self._put(f"users/{self.user_id}/courses", courses_data)
                return success
            return True

        except Exception:
            return False

    def sync_courses_from_cloud(self, content_mgr=None) -> Dict:
        """Pull courses from Firebase RTDB to local storage"""
        if not self.user_id:
            return {}

        try:
            if content_mgr is None:
                from kslearn.loader import content_loader
                content_mgr = content_loader
            
            cloud_courses = self._get(f"users/{self.user_id}/courses")
            if not cloud_courses:
                return {}
            
            synced = {}
            for course_id, course_data in cloud_courses.items():
                content = json.loads(course_data.get("content", "{}"))
                if content:
                    synced[course_id] = course_data.get("title", course_id)
            
            return synced

        except Exception:
            return {}

    # ─── Online Worlds ───────────────────────────────────────────

    def search_world_by_id(self, world_id: str) -> Optional[Dict]:
        """Search for a specific world by ID"""
        world = self._get(f"worlds/{world_id}")
        if world and world.get("world_data"):
            try:
                world["parsed_data"] = json.loads(world["world_data"])
            except Exception:
                pass
        return world

    def get_open_game_sessions(self) -> Dict:
        """Get all open game sessions waiting for players"""
        sessions = self._get("game_sessions")
        if not sessions:
            return {}
        
        open_sessions = {}
        for session_id, session_data in sessions.items():
            if session_data.get("status") == "waiting":
                open_sessions[session_id] = {
                    "name": session_data.get("session_name", session_id),
                    "creator": session_data.get("creator_uid", "Unknown"),
                    "players": len(session_data.get("players", {})),
                    "description": session_data.get("description", "No description"),
                    "created_at": session_data.get("created_at", ""),
                }
        
        return open_sessions
    
    # ─── Friends System ──────────────────────────────────────────
    
    def add_friend(self, friend_id: str) -> bool:
        """Send friend request or accept friend"""
        if not self.user_id:
            return False
        
        # Check if user exists
        friend_profile = self.get_profile(friend_id)
        if not friend_profile:
            show_error("User not found")
            return False
        
        # Add to friends list
        friend_data = {
            "username": friend_profile.get("username", "Unknown"),
            "added_at": datetime.now().isoformat(),
            "status": friend_profile.get("status", "offline")
        }
        
        # Add friend to my list
        self._patch(f"users/{self.user_id}/friends/{friend_id}", friend_data)
        
        # Add me to their list (auto-accept for simplicity)
        my_data = {
            "username": self.user_data.get("username", "Unknown"),
            "added_at": datetime.now().isoformat(),
            "status": "online"
        }
        self._patch(f"users/{friend_id}/friends/{self.user_id}", my_data)
        
        show_success(f"Added {friend_data['username']} as friend!")
        return True
    
    def remove_friend(self, friend_id: str) -> bool:
        """Remove friend"""
        if not self.user_id:
            return False
        
        self._delete(f"users/{self.user_id}/friends/{friend_id}")
        show_info("Friend removed")
        return True
    
    def get_friends(self) -> Dict:
        """Get friends list"""
        if not self.user_id:
            return {}
        
        friends = self._get(f"users/{self.user_id}/friends")
        return friends or {}
    
    def get_online_friends(self) -> List[Dict]:
        """Get list of online friends"""
        friends = self.get_friends()
        online = []
        
        for friend_id, friend_data in friends.items():
            if friend_data.get("status") == "online":
                online.append({
                    "id": friend_id,
                    **friend_data
                })
        
        return online
    
    # ─── Leaderboards ────────────────────────────────────────────
    
    def submit_score(self, game_mode: str, score: int, xp_earned: int, metadata: Dict = None) -> bool:
        """Submit score to global leaderboard"""
        if not self.user_id:
            return False
        
        score_entry = {
            "user_id": self.user_id,
            "username": self.user_data.get("username", "Unknown"),
            "game_mode": game_mode,
            "score": score,
            "xp_earned": xp_earned,
            "total_xp": self.user_data.get("xp", 0),
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Push to leaderboard
        self._post("leaderboard", score_entry)
        
        # Update user's total XP
        current_xp = self.user_data.get("xp", 0)
        new_xp = current_xp + xp_earned
        self.update_profile({"xp": new_xp})
        
        return True
    
    def get_leaderboard(self, game_mode: str = "all", limit: int = 20) -> List[Dict]:
        """Get global leaderboard"""
        scores = self._get("leaderboard")
        if not scores:
            return []
        
        # Convert to list and sort
        score_list = []
        for key, entry in scores.items():
            if game_mode == "all" or entry.get("game_mode") == game_mode:
                score_list.append(entry)
        
        # Sort by score (descending)
        score_list.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return score_list[:limit]
    
    def get_xp_leaderboard(self, limit: int = 20) -> List[Dict]:
        """Get XP-based leaderboard (all-time)"""
        users = self._get("users")
        if not users:
            return []
        
        user_list = []
        for uid, data in users.items():
            if not data.get("is_anonymous"):
                user_list.append({
                    "user_id": uid,
                    "username": data.get("username", "Unknown"),
                    "xp": data.get("xp", 0),
                    "level": data.get("level", 1)
                })
        
        # Sort by XP
        user_list.sort(key=lambda x: x.get("xp", 0), reverse=True)
        return user_list[:limit]
    
    # ─── Content Sharing (JSON as Text) ──────────────────────────
    
    def upload_world(self, world_id: str, world_data: Dict, title: str, description: str) -> bool:
        """Upload KSL-Verse world to RTDB (stored as JSON text)"""
        if not self.user_id:
            show_error("Must be logged in to upload content")
            return False
        
        # Convert world JSON to text string
        world_text = json.dumps(world_data, indent=2)
        
        world_entry = {
            "world_id": world_id,
            "title": title,
            "description": description,
            "author_id": self.user_id,
            "author_name": self.user_data.get("username", "Unknown"),
            "content": world_text,  # Store as text
            "uploaded_at": datetime.now().isoformat(),
            "downloads": 0,
            "likes": 0,
            "category": "community"
        }
        
        success = self._put(f"worlds/{world_id}", world_entry)
        if success:
            show_success(f"World '{title}' uploaded to ksverse!")
        return success
    
    def download_world(self, world_id: str) -> Optional[Dict]:
        """Download KSL-Verse world from RTDB (text back to JSON)"""
        world_data = self._get(f"worlds/{world_id}")
        if not world_data:
            show_error("World not found")
            return None
        
        # Parse content text back to JSON
        try:
            content_text = world_data.get("content", "{}")
            world_json = json.loads(content_text)
            
            # Increment download counter
            current_downloads = world_data.get("downloads", 0)
            self._patch(f"worlds/{world_id}", {"downloads": current_downloads + 1})
            
            return world_json
            
        except json.JSONDecodeError as e:
            show_error(f"Failed to parse world data: {e}")
            return None
    
    def list_worlds(self, category: str = "all") -> List[Dict]:
        """List available worlds from RTDB"""
        worlds = self._get("worlds")
        if not worlds:
            return []
        
        world_list = []
        for wid, data in worlds.items():
            if category == "all" or data.get("category") == category:
                world_list.append({
                    "world_id": wid,
                    "title": data.get("title", "Unknown"),
                    "description": data.get("description", ""),
                    "author": data.get("author_name", "Unknown"),
                    "downloads": data.get("downloads", 0),
                    "likes": data.get("likes", 0),
                    "uploaded_at": data.get("uploaded_at", "")
                })
        
        # Sort by downloads (popular first)
        world_list.sort(key=lambda x: x.get("downloads", 0), reverse=True)
        return world_list
    
    def like_world(self, world_id: str) -> bool:
        """Like a world"""
        world = self._get(f"worlds/{world_id}")
        if not world:
            return False
        
        current_likes = world.get("likes", 0)
        return self._patch(f"worlds/{world_id}", {"likes": current_likes + 1})
    
    # ─── Multiplayer Game State ──────────────────────────────────
    
    def create_game_session(self, session_id: str, host_id: str, game_data: Dict) -> bool:
        """Create multiplayer game session"""
        if not self.user_id:
            return False
        
        session = {
            "session_id": session_id,
            "host_id": host_id,
            "players": {
                host_id: {
                    "username": self.user_data.get("username", "Unknown"),
                    "joined_at": datetime.now().isoformat(),
                    "status": "playing"
                }
            },
            "game_data": game_data,
            "created_at": datetime.now().isoformat(),
            "status": "waiting"
        }
        
        return self._put(f"game_sessions/{session_id}", session)
    
    def join_game_session(self, session_id: str) -> bool:
        """Join existing game session"""
        if not self.user_id:
            return False
        
        session = self._get(f"game_sessions/{session_id}")
        if not session:
            show_error("Game session not found")
            return False
        
        if session.get("status") == "finished":
            show_error("Game session has ended")
            return False
        
        # Add player
        player_data = {
            "username": self.user_data.get("username", "Unknown"),
            "joined_at": datetime.now().isoformat(),
            "status": "playing"
        }
        
        self._patch(f"game_sessions/{session_id}/players/{self.user_id}", player_data)
        
        # Update status to active if 2+ players
        if len(session.get("players", {})) >= 2:
            self._patch(f"game_sessions/{session_id}", {"status": "active"})
        
        show_success("Joined game session!")
        return True
    
    def update_game_state(self, session_id: str, state: Dict) -> bool:
        """Update game state in real-time"""
        if not self.user_id:
            return False
        
        return self._patch(f"game_sessions/{session_id}/game_data", state)
    
    def get_game_state(self, session_id: str) -> Optional[Dict]:
        """Get current game state"""
        session = self._get(f"game_sessions/{session_id}")
        if not session:
            return None
        return session.get("game_data")
    
    def leave_game_session(self, session_id: str) -> bool:
        """Leave game session"""
        if not self.user_id:
            return False
        
        self._delete(f"game_sessions/{session_id}/players/{self.user_id}")
        return True
    
    def finish_game_session(self, session_id: str) -> bool:
        """Mark game session as finished"""
        return self._patch(f"game_sessions/{session_id}", {"status": "finished"})
    
    # ─── Real-time Listeners ─────────────────────────────────────
    
    def listen_to_path(self, path: str, callback: Callable, interval: float = 2.0):
        """Poll RTDB path for changes (simulates real-time listener)"""
        def _poll():
            last_value = None
            while True:
                try:
                    data = self._get(path)
                    if data != last_value:
                        last_value = data
                        callback(data)
                    time.sleep(interval)
                except Exception as e:
                    show_warning(f"Listener error: {e}")
                    time.sleep(interval)
        
        thread = threading.Thread(target=_poll, daemon=True)
        thread.start()
        self._listeners.append(thread)
        return thread
    
    def stop_listeners(self):
        """Stop all real-time listeners"""
        # Note: Can't actually stop daemon threads, but we clear the list
        self._listeners.clear()


# ─── Global Firebase Instance ─────────────────────────────────────────

_firebase = None


def get_firebase() -> FirebaseRTDB:
    """Get or create Firebase instance"""
    global _firebase
    
    if _firebase is None:
        # Use hardcoded API key from Firebase config
        _firebase = FirebaseRTDB(api_key=FIREBASE_API_KEY)
    
    return _firebase


def reset_firebase():
    """Reset Firebase instance (for testing)"""
    global _firebase
    _firebase = None
