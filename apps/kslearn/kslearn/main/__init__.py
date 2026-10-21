"""kslearn - Legacy Module (Deprecated)

⚠️  The main/ directory contains legacy modules from v1.
    Most functionality has been migrated to engines/ and cli/.

    Remaining modules:
    - support: Social links and credits
    - ai_chat: AI chat interface via tgpt
"""

from . import support
from . import ai_chat

__all__ = [
    "support",
    "ai_chat",
]
