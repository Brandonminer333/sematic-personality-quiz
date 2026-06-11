"""Unit tests for api/generation/models.py."""

import pytest

from api.generation.models import FranchiseSpec, ReferenceRow

pytestmark = pytest.mark.unit


def test_franchise_spec_from_dict():
    spec = FranchiseSpec.from_dict(
        {
            "franchise_name": "Harry Potter",
            "wiki_base_url": "https://harrypotter.fandom.com/wiki/",
            "classes": ["Gryffindor", "Slytherin"],
            "characters": [
                {"name": "Harry Potter", "class": "Gryffindor"},
                {"name": "Draco Malfoy", "class": "Slytherin"},
            ],
        }
    )
    assert spec.franchise_name == "Harry Potter"
    assert len(spec.characters) == 2
    assert spec.characters[0].character_class == "Gryffindor"


def test_franchise_spec_requires_two_classes():
    with pytest.raises(ValueError, match="classes"):
        FranchiseSpec.from_dict(
            {
                "franchise_name": "Test",
                "classes": ["OnlyOne"],
                "characters": [{"name": "A", "class": "OnlyOne"}],
            }
        )


def test_reference_row_to_csv_dict():
    row = ReferenceRow(
        leader="Harry Potter",
        type="Gryffindor",
        answers=["strongly agree"] * 15,
    )
    data = row.to_csv_dict()
    assert data["Leader"] == "Harry Potter"
    assert data["Type"] == "Gryffindor"
    assert data["Q15"] == "strongly agree"
