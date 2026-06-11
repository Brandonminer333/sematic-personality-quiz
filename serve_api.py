#!/usr/bin/env python3
"""Start the FastAPI API from any working directory.

Usage (from anywhere):
    python /path/to/sematic-personality-quiz/serve_api.py

Or from the repo root:
    python serve_api.py
    python -m api
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def bootstrap_import_path() -> Path:
    """Ensure repo root is on sys.path and cwd for relative data files."""
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    os.chdir(REPO_ROOT)
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    return REPO_ROOT


def main() -> None:
    bootstrap_import_path()

    import uvicorn

    uvicorn.run(
        "api.api:app",
        host="127.0.0.1",
        port=int(os.getenv("PORT", "8080")),
        reload=os.getenv("API_RELOAD", "1") not in {"0", "false", "False"},
    )


if __name__ == "__main__":
    main()
