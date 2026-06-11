"""Allow `python -m api` when the repo root is on PYTHONPATH or cwd."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from serve_api import main

if __name__ == "__main__":
    main()
