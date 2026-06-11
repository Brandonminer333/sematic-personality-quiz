"""Unit tests for api/llm/client.py — the Gemini LLM wrapper.

The Google GenAI client is mocked so no API key or network is required; we
only verify our wrapper forwards the prompt and surfaces the response text.
"""

import pytest

from api.llm import client as client_mod
from api.llm.client import LLMClient

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeModels:
    def __init__(self, captured: dict):
        self._captured = captured

    def generate_content(self, *, model: str, contents: str):
        self._captured["model"] = model
        self._captured["contents"] = contents
        return _FakeResponse("fake gemini reply")


class _FakeGenAIClient:
    def __init__(self, captured: dict):
        self.models = _FakeModels(captured)


def test_generate_text_forwards_prompt_and_returns_text(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(
        client_mod.genai, "Client", lambda: _FakeGenAIClient(captured)
    )

    llm = LLMClient()
    out = llm.generate_text("hello world")

    assert out == "fake gemini reply"
    assert captured["contents"] == "hello world"
    assert captured["model"] == "gemini-2.5-flash"
