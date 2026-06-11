"""Unit tests for api/generation/parse_answers.py."""

import json

import pytest

from api.generation.parse_answers import parse_likert_answers

pytestmark = pytest.mark.unit

_VALID = [
    "strongly agree",
    "somewhat agree",
    "neutral",
    "somewhat disagree",
    "strongly disagree",
] * 3


def test_parse_likert_answers_accepts_json_object():
    raw = '{"answers": ' + str(_VALID).replace("'", '"') + "}"
    assert parse_likert_answers(raw) == _VALID


def test_parse_likert_answers_accepts_fenced_json():
    raw = "```json\n" + json.dumps({"answers": ["strongly agree"] * 15}) + "\n```"
    assert parse_likert_answers(raw) == ["strongly agree"] * 15


def test_parse_likert_answers_accepts_quoted_csv():
    raw = ', '.join(f'"{answer}"' for answer in _VALID)
    assert parse_likert_answers(raw) == _VALID


def test_parse_likert_answers_rejects_invalid_labels():
    bad = _VALID.copy()
    bad[0] = "very agree"
    raw = '{"answers": ' + str(bad).replace("'", '"') + "}"
    assert parse_likert_answers(raw) is None
