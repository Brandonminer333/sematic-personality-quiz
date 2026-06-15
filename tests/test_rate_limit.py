"""Unit tests for daily quiz creation rate limits."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.api import create_app
from api.classifier import ReferenceData
from api.generation.models import CharacterRef, FranchiseSpec
from api.generation.quiz_jobs import QuizJobStore
from api.rate_limit import DailyQuizRateLimiter, client_key_from_request, daily_quiz_limit_message


def _tiny_reference() -> ReferenceData:
    return ReferenceData(
        leaders=["A", "B"],
        types=__import__("numpy").array(["Fire", "Water"]),
        vectors=__import__("numpy").array([[1.0] * 15, [-1.0] * 15]),
    )


def _fake_spec(prompt: str, _llm) -> FranchiseSpec:
    return FranchiseSpec(
        franchise_name="Test",
        classes=["A", "B"],
        characters=[
            CharacterRef("One", "A"),
            CharacterRef("Two", "B"),
        ],
        wiki_base_url="https://example.com/wiki/",
        source_prompt=prompt,
    )


def test_daily_quiz_rate_limiter_resets_after_limit():
    limiter = DailyQuizRateLimiter(daily_limit=2)

    assert limiter.try_consume("client-a") == (True, 1)
    assert limiter.try_consume("client-a") == (True, 0)
    assert limiter.try_consume("client-a") == (False, 0)
    assert limiter.try_consume("client-b") == (True, 1)


def test_daily_quiz_limit_message_uses_limit():
    message = daily_quiz_limit_message(3)
    assert "3" in message
    assert "tomorrow" in message.lower()
    assert "github.com/Brandonminer333/sematic-personality-quiz" in message


def test_client_key_from_request_uses_forwarded_for():
    from unittest.mock import MagicMock

    forwarded = MagicMock()
    forwarded.headers.get.return_value = "203.0.113.9, 10.0.0.1"
    forwarded.client.host = "127.0.0.1"

    direct = MagicMock()
    direct.headers.get.return_value = None
    direct.client.host = "127.0.0.1"

    assert client_key_from_request(forwarded) != client_key_from_request(direct)


def test_create_quiz_returns_429_after_daily_limit(tmp_path):
    limiter = DailyQuizRateLimiter(daily_limit=2)
    app = create_app(
        reference=_tiny_reference(),
        job_store=QuizJobStore(),
        spec_builder=_fake_spec,
        generation_runner=lambda **kwargs: None,
        quizzes_out_dir=tmp_path,
        gcs_store=None,
        quiz_rate_limiter=limiter,
    )
    client = TestClient(app)

    for _ in range(2):
        r = client.post("/quizzes", json={"prompt": "houses"})
        assert r.status_code == 202

    r = client.post("/quizzes", json={"prompt": "houses again"})
    assert r.status_code == 429
    assert "today" in r.json()["detail"].lower()
    assert "2" in r.json()["detail"]
    assert "github.com/Brandonminer333/sematic-personality-quiz" in r.json()["detail"]


def test_daily_quiz_rate_limiter_rejects_invalid_limit():
    with pytest.raises(ValueError, match="daily_limit"):
        DailyQuizRateLimiter(daily_limit=0)
