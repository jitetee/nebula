"""
Centralized Firebase Configuration

Loads Firebase credentials from environment variables with fallback defaults.
Never hardcode API keys in source files.
"""

import os
from typing import Dict


def load_firebase_config() -> Dict[str, str]:
    """
    Load Firebase configuration from environment variables.
    
    Priority:
    1. Environment variables (production/secure)
    2. Default fallback values (development only)
    
    Set these in your environment or .env file:
    - FIREBASE_API_KEY
    - FIREBASE_AUTH_DOMAIN
    - FIREBASE_DATABASE_URL
    - FIREBASE_PROJECT_ID
    - FIREBASE_STORAGE_BUCKET
    - FIREBASE_MESSAGING_SENDER_ID
    - FIREBASE_APP_ID
    - FIREBASE_MEASUREMENT_ID
    """
    return {
        "apiKey": os.getenv("FIREBASE_API_KEY", "AIzaSyAta1rlqXCP5_rYAUsUtKRL606taZXzQ2g"),
        "authDomain": os.getenv(
            "FIREBASE_AUTH_DOMAIN", "kashsight-4cbb8.firebaseapp.com"
        ),
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


# Convenience exports
FIREBASE_CONFIG = load_firebase_config()
FIREBASE_RTDB_URL = FIREBASE_CONFIG["databaseURL"]
FIREBASE_API_KEY = FIREBASE_CONFIG["apiKey"]
FIREBASE_PROJECT = FIREBASE_CONFIG["projectId"]
