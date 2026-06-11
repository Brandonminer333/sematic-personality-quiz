"""Unit tests for api/generation/persist.py."""

import csv
import json

import pytest

from api.generation.models import FranchiseSpec, ReferenceRow
from api.generation.persist import write_quiz_artifact

pytestmark = pytest.mark.unit


def _spec() -> FranchiseSpec:
    return FranchiseSpec.from_dict(
        {
            "franchise_name": "Harry Potter",
            "classes": ["Gryffindor", "Slytherin"],
            "characters": [
                {"name": "Harry Potter", "class": "Gryffindor"},
                {"name": "Draco Malfoy", "class": "Slytherin"},
            ],
        }
    )


def test_write_quiz_artifact_writes_csv_and_meta(tmp_path):
    rows = [
        ReferenceRow("Harry Potter", "Gryffindor", ["strongly agree"] * 15),
        ReferenceRow("Draco Malfoy", "Slytherin", ["somewhat disagree"] * 15),
    ]

    artifact = write_quiz_artifact(
        quiz_id="abc123",
        spec=_spec(),
        rows=rows,
        out_dir=tmp_path,
        raw_responses={"Harry Potter": "raw one"},
        source_urls={"Harry Potter": "https://harrypotter.fandom.com/wiki/Harry_Potter"},
    )

    assert artifact.reference_csv.exists()
    assert artifact.meta_json.exists()
    assert (artifact.quiz_dir / "raw" / "Harry Potter.txt").exists()

    with artifact.reference_csv.open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == 2
    assert csv_rows[0]["Leader"] == "Harry Potter"
    assert csv_rows[0]["Q1"] == "strongly agree"

    meta = json.loads(artifact.meta_json.read_text(encoding="utf-8"))
    assert meta["quiz_id"] == "abc123"
    assert meta["row_count"] == 2
    assert meta["characters"][0]["source_url"].endswith("Harry_Potter")
