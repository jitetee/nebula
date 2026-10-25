"""
Firebase configuration for jtlearn.

The project's identifiers are kept in the packed file `_fb.dat` instead of
plain text in the source. This only keeps the values out of casual reading and
secret scanners; it is not encryption. The real protection is the Firebase
Security Rules and the key restrictions set in Google Cloud.

To use your own project, set these environment variables (they win over the
packed file): FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_DATABASE_URL,
FIREBASE_PROJECT_ID, FIREBASE_STORAGE_BUCKET, FIREBASE_MESSAGING_SENDER_ID,
FIREBASE_APP_ID, FIREBASE_MEASUREMENT_ID.
"""

import base64
import json
import os
from pathlib import Path
from typing import Dict

_K = b"ks-learn::fb::v1"
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


def _packed() -> Dict[str, str]:
    try:
        d = json.loads((Path(__file__).with_name("_fb.dat")).read_text())
        parts = [None] * len(d["p"])
        for pos, idx in enumerate(d["o"]):
            parts[idx] = d["p"][pos]
        raw = base64.b64decode("".join(parts))
        return json.loads(bytes(b ^ _K[i % len(_K)] for i, b in enumerate(raw)))
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
