"""Unit tests for api/generation/validate.py."""

import pytest

from api.generation.models import ReferenceRow
from api.generation.validate import validate_reference_rows

pytestmark = pytest.mark.unit


def _row(name: str, cls: str) -> ReferenceRow:
    return ReferenceRow(
        leader=name,
        type=cls,
        answers=["neutral"] * 15,
    )


def test_validate_reference_rows_accepts_complete_set():
    rows = [_row("Harry Potter", "Gryffindor"), _row("Draco Malfoy", "Slytherin")]
    validate_reference_rows(rows, ["Gryffindor", "Slytherin"])


def test_validate_reference_rows_rejects_missing_class():
    rows = [_row("Harry Potter", "Gryffindor")]
    with pytest.raises(ValueError, match="Missing reference rows"):
        validate_reference_rows(rows, ["Gryffindor", "Slytherin"])


def test_validate_reference_rows_rejects_invalid_label():
    rows = [
        ReferenceRow("Harry Potter", "Gryffindor", ["very agree"] + ["neutral"] * 14),
        _row("Draco Malfoy", "Slytherin"),
    ]
    with pytest.raises(ValueError, match="invalid Likert labels"):
        validate_reference_rows(rows, ["Gryffindor", "Slytherin"])
