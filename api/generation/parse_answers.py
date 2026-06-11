"""Parse LLM roleplay output into validated Likert answer labels."""

from __future__ import annotations

import json
import re

from api.classifier import LIKERT_MAPPING

_VALID_LIKERT = frozenset(LIKERT_MAPPING.keys())


def _normalize_label(raw: str) -> str | None:
    label = raw.strip().strip('"').strip("'").lower()
    # I delibrately do not fix typos because there shouldn't be any in the first place
    return label if label in _VALID_LIKERT else None


def _strip_code_fence(text: str) -> str:
    """Remove code fences from the text."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json|csv|plaintext)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _try_parse_json(text: str) -> list[str] | None:
    """Try to parse the text as JSON."""
    try:
        payload = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict):
        answers = payload.get("answers")
    elif isinstance(payload, list):
        answers = payload
    else:
        return None

    if not isinstance(answers, list):
        return None

    normalized = [_normalize_label(str(item)) for item in answers]
    if len(normalized) == 15 and all(normalized):
        return normalized
    return None


def _try_parse_delimited(text: str) -> list[str] | None:
    """Fallback for CSV-ish or quoted-list outputs."""
    body = _strip_code_fence(text)
    if not body:
        return None

    # Quoted tokens: "strongly agree", "neutral", ...
    quoted = re.findall(r'"([^"]+)"', body)
    if quoted:
        normalized = [_normalize_label(item) for item in quoted]
        if len(normalized) >= 15:
            chunk = normalized[:15]
            if all(chunk):
                return chunk

    # Comma-separated without quotes
    parts = [part.strip() for part in re.split(r"[,\n]+", body) if part.strip()]
    normalized = [_normalize_label(part) for part in parts]
    if len(normalized) >= 15:
        chunk = normalized[:15]
        if all(chunk):
            return chunk

    return None


def parse_likert_answers(raw: str, *, expected_count: int = 15) -> list[str] | None:
    """Extract exactly `expected_count` valid Likert labels from LLM output.
    Returns None if the output is not valid.
    """
    answers = _try_parse_json(raw)
    if answers is not None and len(answers) == expected_count:
        return answers
    answers = _try_parse_delimited(raw)
    if answers is not None and len(answers) == expected_count:
        return answers
    return None
