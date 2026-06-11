"""Unit tests for api/generation/parse_spec.py — Stage 1."""

import json

import pytest

from api.generation.parse_spec import parse_franchise_context

pytestmark = pytest.mark.unit

_STAGE1_JSON = {
    "franchise_name": "Harry Potter",
    "classes": ["Gryffindor", "Slytherin"],
    "wiki_base_url": "https://harrypotter.fandom.com/wiki/",
}


class FakeLLM:
    def __init__(self, payload: dict):
        self.payload = payload
        self.prompts: list[str] = []

    def generate_text(self, prompt: str, **kwargs) -> str:
        self.prompts.append(prompt)
        return json.dumps(self.payload)


def test_parse_franchise_context_returns_context():
    llm = FakeLLM(_STAGE1_JSON)
    context = parse_franchise_context("Hogwarts houses", llm)

    assert context.franchise_name == "Harry Potter"
    assert context.classes == ["Gryffindor", "Slytherin"]
    assert context.wiki_base_url == "https://harrypotter.fandom.com/wiki/"
    assert "Hogwarts houses" in llm.prompts[0]


def test_parse_franchise_context_rejects_model_error():
    llm = FakeLLM({"error": "not a fictional class quiz"})
    with pytest.raises(ValueError, match="not a fictional class quiz"):
        parse_franchise_context("tell me a joke", llm)


def test_parse_franchise_context_rejects_invalid_wiki_base():
    payload = dict(_STAGE1_JSON)
    payload["wiki_base_url"] = "https://en.wikipedia.org/wiki/"
    llm = FakeLLM(payload)
    with pytest.raises(ValueError, match="Fandom"):
        parse_franchise_context("Hogwarts houses", llm)
