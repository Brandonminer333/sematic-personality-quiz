"""Unit tests for api/generation/discover_roster.py — Stage 2."""

import json

import pytest

from api.generation.discover_roster import build_franchise_spec_from_prompt, discover_roster
from api.generation.models import FranchiseContext

pytestmark = pytest.mark.unit

_CONTEXT = FranchiseContext(
    franchise_name="Harry Potter",
    classes=["Gryffindor", "Slytherin"],
    wiki_base_url="https://harrypotter.fandom.com/wiki/",
)

_ROSTER_JSON = {
    "characters": [
        {"name": "Harry Potter", "class": "Gryffindor"},
        {"name": "Hermione Granger", "class": "Gryffindor"},
        {"name": "Draco Malfoy", "class": "Slytherin"},
        {"name": "Severus Snape", "class": "Slytherin"},
    ]
}


class StageLLM:
    def __init__(self, stage1: dict, stage2: dict):
        self.stage1 = stage1
        self.stage2 = stage2
        self.calls = 0

    def generate_text(self, prompt: str, **kwargs) -> str:
        self.calls += 1
        if self.calls == 1:
            return json.dumps(self.stage1)
        return json.dumps(self.stage2)


def test_discover_roster_returns_character_refs():
    llm = StageLLM({}, _ROSTER_JSON)
    # Skip stage 1 call by invoking stage 2 directly with second response only.
    llm.calls = 1

    roster = discover_roster(_CONTEXT, "Hogwarts houses", llm)
    assert len(roster) == 4
    assert roster[0].name == "Harry Potter"
    assert roster[0].character_class == "Gryffindor"


def test_discover_roster_requires_every_class():
    llm = StageLLM(
        {},
        {
            "characters": [
                {"name": "Harry Potter", "class": "Gryffindor"},
            ]
        },
    )
    llm.calls = 1
    with pytest.raises(ValueError, match="missing characters for classes"):
        discover_roster(_CONTEXT, "Hogwarts houses", llm)


def test_build_franchise_spec_from_prompt_combines_stages():
    stage1 = {
        "franchise_name": "Harry Potter",
        "classes": ["Gryffindor", "Slytherin"],
        "wiki_base_url": "https://harrypotter.fandom.com/wiki/",
    }
    llm = StageLLM(stage1, _ROSTER_JSON)

    spec = build_franchise_spec_from_prompt("Hogwarts houses", llm)
    assert spec.franchise_name == "Harry Potter"
    assert len(spec.characters) == 4
    assert spec.source_prompt == "Hogwarts houses"
