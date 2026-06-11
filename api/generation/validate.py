"""Validate generated reference rows before persistence."""

from __future__ import annotations

from api.classifier import LIKERT_MAPPING, QUESTION_COLUMNS
from api.generation.models import ReferenceRow


def validate_reference_rows(
    rows: list[ReferenceRow],
    required_classes: list[str],
) -> None:
    """Ensure rows are classifier-ready and every class is represented."""
    if not rows:
        raise ValueError("No reference rows were produced")

    expected_answer_count = len(QUESTION_COLUMNS)
    for row in rows:
        if not row.leader.strip():
            raise ValueError("Reference row has an empty Leader name")
        if not row.type.strip():
            raise ValueError(f"Reference row for {row.leader!r} has an empty Type")
        if len(row.answers) != expected_answer_count:
            raise ValueError(
                f"Reference row for {row.leader!r} has "
                f"{len(row.answers)} answers, expected {expected_answer_count}"
            )
        invalid = [answer for answer in row.answers if answer not in LIKERT_MAPPING]
        if invalid:
            raise ValueError(
                f"Reference row for {row.leader!r} has invalid Likert labels: {invalid}"
            )

    present_classes = {row.type for row in rows}
    missing_classes = sorted(set(required_classes) - present_classes)
    if missing_classes:
        raise ValueError(
            "Missing reference rows for required classes: "
            + ", ".join(missing_classes)
        )
