#!/usr/bin/env python3
"""
Content Integrity & Access Key System

Protects JSON content files (notes, quizzes) from unauthorized tampering
and enforces access key validation for editing/adding content.
"""

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from kslearn.loader import DATA_DIR, KSL_DIR, CONFIG_DIR


# ─── Access Key Storage ────────────────────────────────────────────
_KEYS_DIR = CONFIG_DIR / "keys"
_MASTER_KEY_FILE = _KEYS_DIR / "master.key"
_CONTENT_HASH_FILE = DATA_DIR / ".content_hashes.json"


def _ensure_keys_dir():
    """Create key storage directory."""
    _KEYS_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ─── Master Access Key ─────────────────────────────────────────────

def has_master_key() -> bool:
    """Check if a master access key has been set."""
    return _MASTER_KEY_FILE.exists()


def set_master_key(secret: str) -> bool:
    """
    Set the master access key. This is used to:
    1. Sign content file hashes
    2. Authorize content modifications

    Returns True if key was set, False if already set.
    """
    _ensure_keys_dir()
    if has_master_key():
        return False  # Key already exists, don't overwrite
    _MASTER_KEY_FILE.write_text(secret, encoding="utf-8")
    # Set restrictive permissions on Unix (skip on Windows)
    if os.name != "nt":
        try:
            os.chmod(str(_MASTER_KEY_FILE), 0o600)  # Only owner can read
        except OSError:
            pass  # Windows doesn't support chmod
    return True


def verify_master_key(secret: str) -> bool:
    """Check if the provided secret matches the master key."""
    if not has_master_key():
        return False
    stored = _MASTER_KEY_FILE.read_text(encoding="utf-8").strip()
    return hmac.compare_digest(stored, secret)


def get_master_key() -> Optional[str]:
    """Read the master key from disk. Returns None if not set."""
    if not has_master_key():
        return None
    return _MASTER_KEY_FILE.read_text(encoding="utf-8").strip()


# ─── Content File Hashing ─────────────────────────────────────────

def _compute_file_hash(file_path: Path) -> str:
    """Compute HMAC-SHA256 hash of a file's content using master key."""
    key = get_master_key()
    if not key:
        # No key set — return plain SHA256 (no signing, just checksum)
        return hashlib.sha256(file_path.read_bytes()).hexdigest()
    content = file_path.read_bytes()
    return hmac.new(key.encode(), content, hashlib.sha256).hexdigest()


def generate_content_manifest() -> Dict:
    """
    Scan all content .ksl files and generate a signed manifest.
    This should be run after adding/editing content, with the master key.
    """
    manifest = {
        "version": "1.0",
        "files": {},
        "generated_at": None,
    }

    from datetime import datetime
    manifest["generated_at"] = datetime.now().isoformat()

    # Scan all .ksl files in data/ksl/
    for ksl_file in KSL_DIR.glob("*.ksl"):
        rel_path = str(ksl_file.relative_to(KSL_DIR))
        manifest["files"][rel_path] = _compute_file_hash(ksl_file)

    # Also scan any legacy JSON files that might still exist in data/
    for json_file in DATA_DIR.glob("*.json"):
        if json_file.name.startswith("."):
            continue
        rel_path = str(json_file.relative_to(DATA_DIR))
        manifest["files"][rel_path] = _compute_file_hash(json_file)

    return manifest


def save_content_manifest(manifest: Dict) -> bool:
    """Save the signed content manifest."""
    _ensure_data_dir()
    _ensure_keys_dir()
    manifest_path = _KEYS_DIR / "content_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    # Set restrictive permissions on Unix (skip on Windows)
    if os.name != "nt":
        try:
            os.chmod(str(manifest_path), 0o600)
        except OSError:
            pass
    return True


def load_content_manifest() -> Optional[Dict]:
    """Load the signed content manifest."""
    manifest_path = _KEYS_DIR / "content_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return None


# ─── Integrity Verification ────────────────────────────────────────

def verify_all_content() -> Tuple[bool, list]:
    """
    Verify all content files against the signed manifest.
    
    Returns:
        (all_valid, list_of_issues)
    """
    manifest = load_content_manifest()
    if not manifest:
        return True, ["No content manifest found — run 'kslearn protect' first"]

    issues = []
    verified_count = 0

    for rel_path, expected_hash in manifest.get("files", {}).items():
        file_path = DATA_DIR / rel_path

        if not file_path.exists():
            issues.append(f"MISSING: {rel_path}")
            continue

        actual_hash = _compute_file_hash(file_path)
        if actual_hash != expected_hash:
            issues.append(f"TAMPERED: {rel_path}")
        else:
            verified_count += 1

    all_valid = len(issues) == 0
    return all_valid, issues


def verify_single_file(file_path: Path) -> bool:
    """Verify a single content file hasn't been tampered with."""
    manifest = load_content_manifest()
    if not manifest:
        return True  # No manifest, can't verify — allow by default

    if not file_path.exists():
        return False

    rel_path = str(file_path.relative_to(DATA_DIR))
    expected_hash = manifest.get("files", {}).get(rel_path)
    if expected_hash is None:
        return True  # File not in manifest (new/unknown file)

    actual_hash = _compute_file_hash(file_path)
    return hmac.compare_digest(actual_hash, expected_hash)


# ─── Content Edit Authorization ────────────────────────────────────

def authorize_content_edit(secret: str) -> bool:
    """
    Check if the user is authorized to edit content files.
    Requires the master access key.
    """
    return verify_master_key(secret)


def protect_content_with_key(secret: str) -> bool:
    """
    Set master key AND generate signed content manifest in one step.
    Call this during initial setup or when adding new content.
    """
    if not has_master_key():
        if not set_master_key(secret):
            return False

    # Generate and save manifest
    manifest = generate_content_manifest()
    return save_content_manifest(manifest)
