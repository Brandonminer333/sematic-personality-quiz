"""Unit tests for api/llm/client.py — the Gemini LLM wrapper.

The Google GenAI client is mocked so no API key or network is required; we
only verify our wrapper forwards the prompt and surfaces the response text.
"""

import pytest

from api.llm import client as client_mod
from api.llm.client import GeminiRateLimitError, GeminiUnavailableError, LLMClient

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
    assert captured["model"] == "gemini-2.5-flash-lite"


class _FlakyModels:
    def __init__(self, exc: Exception):
        self._exc = exc
        self.calls = 0

    def generate_content(self, *, model: str, contents: str):
        self.calls += 1
        raise self._exc


def test_generate_text_raises_unavailable_when_retries_disabled(monkeypatch):
    exc = RuntimeError("503 UNAVAILABLE. high demand")
    monkeypatch.setattr(
        client_mod.genai,
        "Client",
        lambda: type("C", (), {"models": _FlakyModels(exc)})(),
    )
    llm = LLMClient()
    with pytest.raises(GeminiUnavailableError):
        llm.generate_text("hello", retry_on_rate_limit=False)


def test_generate_text_retries_on_503(monkeypatch):
    exc = RuntimeError("503 UNAVAILABLE")
    flaky = _FlakyModels(exc)

    class _Client:
        models = flaky

    monkeypatch.setattr(client_mod, "time", type("T", (), {"sleep": lambda *_: None})())
    monkeypatch.setattr(client_mod.genai, "Client", lambda: _Client())

    call_count = {"n": 0}
    original_generate = flaky.generate_content

    def _eventually_succeed(*, model: str, contents: str):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise exc
        return _FakeResponse("ok after retry")

    flaky.generate_content = _eventually_succeed  # type: ignore[method-assign]

    llm = LLMClient()
    assert llm.generate_text("hello") == "ok after retry"
    assert call_count["n"] == 2
