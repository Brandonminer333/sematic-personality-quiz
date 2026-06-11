"""Load the canonical 15-question personality quiz from shared/questions.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
QUESTIONS_PATH = _REPO_ROOT / "shared" / "questions.json"
EXPECTED_QUESTION_COUNT = 15


@lru_cache(maxsize=1)
def load_quiz_questions() -> tuple[list[str], list[str]]:
    """Return (questions, likert_options) from the shared JSON file."""
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    questions = data.get("questions")
    likert_options = data.get("likert_options")
    if not isinstance(questions, list) or not questions:
        raise ValueError(f"{QUESTIONS_PATH} must contain a non-empty 'questions' list")
    if not isinstance(likert_options, list) or not likert_options:
        raise ValueError(f"{QUESTIONS_PATH} must contain a non-empty 'likert_options' list")
    if len(questions) != EXPECTED_QUESTION_COUNT:
        raise ValueError(
            f"{QUESTIONS_PATH} must contain exactly {EXPECTED_QUESTION_COUNT} questions, "
            f"got {len(questions)}"
        )

    return [str(q) for q in questions], [str(o) for o in likert_options]
