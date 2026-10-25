#!/usr/bin/env python3
"""Allow running as: python -m jtlearn

Routes to the primary CLI entry point (jtlearn.cli:main).
"""

from .cli import main

if __name__ == "__main__":
    main()
