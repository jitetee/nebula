#!/usr/bin/env python3
"""Allow running as: python -m kslearn

Routes to the primary CLI entry point (kslearn.cli:main).
"""

from .cli import main

if __name__ == "__main__":
    main()
