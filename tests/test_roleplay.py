"""Unit tests for api/generation/roleplay.py — Stage 4 roleplay pipeline."""

import json

import pytest

from api.generation.questions import EXPECTED_QUESTION_COUNT, load_quiz_questions
from api.generation.roleplay import (
    build_roleplay_prompt,
    format_wiki_context_block,
    roleplay_answers,
    roleplay_character,
)

pytestmark = pytest.mark.unit


def test_load_quiz_questions_returns_fifteen_items():
    questions, options = load_quiz_questions()
    assert len(questions) == EXPECTED_QUESTION_COUNT
    assert len(options) == 5
    assert "strongly agree" in options


def test_build_roleplay_prompt_includes_all_questions():
    prompt = build_roleplay_prompt("Hermione Granger")
    questions, _ = load_quiz_questions()
    assert "Hermione Granger" in prompt
    assert '"answers"' in prompt
    for question in questions:
        assert question in prompt


def test_format_wiki_context_block_success():
    block = format_wiki_context_block(
        character="Erika",
        entity={
            "url": "https://pokemon.fandom.com/wiki/Erika",
            "summary": "Summary text",
            "appearances": ["A1"],
            "histories": ["H1"],
            "quotes": ["Q1"],
        },
    )
    assert "Summary text" in block
    assert "A1" in block
    assert "--- END CONTEXT ---" in block


def test_format_wiki_context_block_fallback():
    block = format_wiki_context_block(
        character="Erika",
        source_url="https://example.com/wiki/Erika",
        error="offline",
    )
    assert "Failed to fetch wiki context" in block
    assert "offline" in block


def test_roleplay_answers_parses_json_response():
    answers = ["strongly agree"] * 15
    captured: dict = {}

    class FakeLLM:
        def generate_text(self, prompt: str) -> str:
            captured["prompt"] = prompt
            return json.dumps({"answers": answers})

    result = roleplay_answers(
        "Hermione Granger",
        "--- CONTEXT ---\nLorem ipsum\n--- END CONTEXT ---",
        llm=FakeLLM(),
    )

    assert result.character == "Hermione Granger"
    assert result.answers == answers
    assert "Hermione Granger" in captured["prompt"]
    assert "Lorem ipsum" in captured["prompt"]


def test_roleplay_answers_retries_on_unparseable_response():
    calls = {"count": 0}

    class FakeLLM:
        def generate_text(self, prompt: str) -> str:
            calls["count"] += 1
            if calls["count"] == 1:
                return "not valid"
            return json.dumps({"answers": ["neutral"] * 15})

    result = roleplay_answers(
        "Harry Potter",
        "--- CONTEXT ---\nctx\n--- END CONTEXT ---",
        llm=FakeLLM(),
        retries=1,
    )
    assert result.answers == ["neutral"] * 15
    assert calls["count"] == 2


def test_roleplay_character_wires_wiki_fetch_and_llm(monkeypatch):
    answers = ["somewhat agree"] * 15

    monkeypatch.setattr(
        "api.generation.roleplay.resolve_wiki_url",
        lambda *a, **k: "https://harrypotter.fandom.com/wiki/Harry_Potter",
    )
    monkeypatch.setattr(
        "api.generation.roleplay.scrape_wiki_entity",
        lambda url, **k: {
            "url": url,
            "summary": "The boy who lived.",
            "appearances": [],
            "histories": [],
            "quotes": [],
        },
    )

    class FakeLLM:
        def generate_text(self, prompt: str) -> str:
            assert "The boy who lived." in prompt
            return json.dumps({"answers": answers})

    result = roleplay_character(
        "Harry Potter",
        franchise_name="Harry Potter",
        wiki_base_url="https://harrypotter.fandom.com/wiki/",
        llm=FakeLLM(),
    )

    assert result.source_url == "https://harrypotter.fandom.com/wiki/Harry_Potter"
    assert result.answers == answers
