"""
Auto-update checker for kslearn.

Checks PyPI and GitHub for newer versions and displays update notifications.
Uses urllib.request (no additional dependencies required).
"""

import json
import ssl
import threading
import urllib.request
from pathlib import Path

import kslearn

GITHUB_REPO = "kashsight/kslearn"
PYPI_URL = f"https://pypi.org/pypi/kslearn/json"
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_TAGS_URL = f"https://api.github.com/repos/{GITHUB_REPO}/tags"
UPDATE_URL = "https://github.com/kashsight/kslearn"


def _get_latest_pypi_version():
    """Fetch latest version from PyPI."""
    try:
        req = urllib.request.Request(
            PYPI_URL,
            headers={"Accept": "application/json", "User-Agent": "kslearn-update-checker"}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("info", {}).get("version")
    except Exception:
        return None


def _get_latest_github_version():
    """Fetch latest version from GitHub releases/tags."""
    try:
        # Try releases first
        req = urllib.request.Request(
            GITHUB_RELEASES_URL,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "kslearn-update-checker"}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tag = data.get("tag_name", "")
            if tag:
                return tag.lstrip("v")
    except Exception:
        pass

    # Fallback to tags
    try:
        req = urllib.request.Request(
            GITHUB_TAGS_URL,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "kslearn-update-checker"}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                return data[0].get("name", "").lstrip("v")
    except Exception:
        pass

    return None


def _version_tuple(version_str):
    """Convert version string to comparable tuple."""
    try:
        return tuple(int(x) for x in version_str.split("."))
    except (ValueError, AttributeError):
        return (0,)


def check_for_updates():
    """
    Check for updates from PyPI and GitHub.

    Returns a dict with:
        - current_version: str
        - latest_version: str or None
        - update_available: bool
        - source: 'pypi' | 'github' | None
        - update_url: str
        - error: str or None
    """
    current = getattr(kslearn, "__version__", "2.0.0")

    # Check both sources
    pypi_version = _get_latest_pypi_version()
    github_version = _get_latest_github_version()

    # Use whichever is newer
    latest = None
    source = None

    if pypi_version and github_version:
        if _version_tuple(github_version) >= _version_tuple(pypi_version):
            latest = github_version
            source = "github"
        else:
            latest = pypi_version
            source = "pypi"
    elif github_version:
        latest = github_version
        source = "github"
    elif pypi_version:
        latest = pypi_version
        source = "pypi"

    if latest is None:
        return {
            "current_version": current,
            "latest_version": None,
            "update_available": False,
            "source": None,
            "update_url": UPDATE_URL,
            "error": "Could not reach update servers"
        }

    update_available = _version_tuple(latest) > _version_tuple(current)

    return {
        "current_version": current,
        "latest_version": latest,
        "update_available": update_available,
        "source": source,
        "update_url": UPDATE_URL,
        "error": None
    }


def check_updates_async(callback):
    """
    Run update check in a background thread and call callback(result) when done.

    callback receives the same dict as check_for_updates().
    """
    def _worker():
        result = check_for_updates()
        callback(result)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread
