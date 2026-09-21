# conftest.py
# Adds the project root to sys.path so pytest can resolve module imports
# regardless of which directory the test runner is invoked from.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))