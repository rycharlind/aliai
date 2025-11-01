#!/usr/bin/env python3
"""
AliAI - Migration CLI Tool
Command-line utility for managing database migrations
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from aliai.migrations import main

if __name__ == "__main__":
    main()

