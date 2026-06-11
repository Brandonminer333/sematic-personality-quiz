"""Shared JSON extraction helpers for LLM responses."""

from __future__ import annotations

import json
import re


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def parse_json_object(text: str) -> dict:
    """Parse a JSON object from raw LLM text."""
    payload = json.loads(strip_code_fences(text))
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object")
    return payload
