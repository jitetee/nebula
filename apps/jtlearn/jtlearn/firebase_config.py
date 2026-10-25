"""
Firebase configuration for jtlearn.

jtlearn shares ONE Firebase project with the rest of Nebula and the J.I.T.E.T.E.E.
website. The project's settings are read from Nebula's own packed config
(assets/cloud/*.dat, see tools/pack-cloud.py), so they are not written in plain text
in the source. This only keeps the values from casual reading and secret scanners; it
is not encryption. The real protection is the Firebase Security Rules
(database.rules.json) and the key restrictions set in Google Cloud.

To use another project, set these environment variables (they win over the pack):
FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_DATABASE_URL, FIREBASE_PROJECT_ID.
"""

import base64
import os
import re
from pathlib import Path
from typing import Dict

_ENV = {
    "apiKey": "FIREBASE_API_KEY",
    "authDomain": "FIREBASE_AUTH_DOMAIN",
    "databaseURL": "FIREBASE_DATABASE_URL",
    "projectId": "FIREBASE_PROJECT_ID",
    "storageBucket": "FIREBASE_STORAGE_BUCKET",
    "messagingSenderId": "FIREBASE_MESSAGING_SENDER_ID",
    "appId": "FIREBASE_APP_ID",
    "measurementId": "FIREBASE_MEASUREMENT_ID",
}


def _nebula_home() -> Path:
    env = os.getenv("NEBULA_HOME")
    return Path(env) if env else Path(__file__).resolve().parents[3]


def _packed() -> Dict[str, str]:
    """Rebuild the settings from Nebula's scrambled chunks (same recipe as lib/cloud.sh)."""
    try:
        home = _nebula_home()
        sh = (home / "lib" / "cloud.sh").read_text()
        arr = lambda n: re.search(n + r"=\(([^)]*)\)", sh).group(1).split()
        seq, kf, ko = arr("CLOUD_SEQ"), arr("CLOUD_KF"), [int(x) for x in arr("CLOUD_KO")]
        blob = "".join((home / "assets" / "cloud" / (f + ".dat")).read_text().strip() for f in seq)
        key = bytes.fromhex("".join(kf[i] for i in ko))
        raw = base64.b64decode(blob)
        lines = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw)).decode().split("\n")
        if lines[0] != "NCFG1":
            return {}
        db, api, proj = lines[1].rstrip("/"), lines[2], (lines[3] if len(lines) > 3 else "")
        return {"apiKey": api, "databaseURL": db, "projectId": proj,
                "authDomain": f"{proj}.firebaseapp.com" if proj else ""}
    except Exception:
        return {}


def load_firebase_config() -> Dict[str, str]:
    """Environment variables first, then the packed defaults."""
    base = _packed()
    return {k: os.getenv(env) or base.get(k, "") for k, env in _ENV.items()}


FIREBASE_CONFIG = load_firebase_config()
FIREBASE_RTDB_URL = FIREBASE_CONFIG["databaseURL"]
FIREBASE_API_KEY = FIREBASE_CONFIG["apiKey"]
FIREBASE_PROJECT = FIREBASE_CONFIG["projectId"]
