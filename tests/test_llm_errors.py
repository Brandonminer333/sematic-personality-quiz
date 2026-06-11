"""Unit tests for api/llm/errors.py and transient Gemini handling."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.api import create_app
from api.classifier import ReferenceData
from api.generation.models import CharacterRef, FranchiseSpec
from api.generation.quiz_jobs import QuizJobStore
from api.llm.errors import (
    AI_PROVIDER_OVERLOAD_MESSAGE,
    http_status_for_error,
    is_ai_provider_overload,
    user_facing_error,
)
import numpy as np

pytestmark = pytest.mark.unit


def test_is_ai_provider_overload_detects_503_and_429():
    assert is_ai_provider_overload("503 UNAVAILABLE high demand")
    assert is_ai_provider_overload("429 RESOURCE_EXHAUSTED")
    assert not is_ai_provider_overload("Missing reference rows for required classes")


def test_user_facing_error_maps_overload():
    raw = "failed to parse franchise context: 503 UNAVAILABLE"
    assert user_facing_error(raw) == AI_PROVIDER_OVERLOAD_MESSAGE
    assert user_facing_error("some other error") == "some other error"


def test_http_status_for_error():
    assert http_status_for_error("503 UNAVAILABLE") == 503
    assert http_status_for_error("validation failed") == 422


def _tiny_reference() -> ReferenceData:
    return ReferenceData(
        leaders=["A", "B"],
        types=np.array(["Fire", "Water"]),
        vectors=np.array([[1.0] * 15, [-1.0] * 15]),
    )


def test_create_quiz_returns_503_on_gemini_unavailable():
    def _raise_unavailable(prompt, _llm):
        raise ValueError(
            "failed to parse franchise context: 503 UNAVAILABLE. high demand"
        )

    app = create_app(reference=_tiny_reference(), spec_builder=_raise_unavailable)
    client = TestClient(app)
    r = client.post("/quizzes", json={"prompt": "Hogwarts houses"})
    assert r.status_code == 503
    assert r.json()["detail"] == AI_PROVIDER_OVERLOAD_MESSAGE


def test_quiz_results_returns_503_when_job_failed_with_overload(tmp_path):
    store = QuizJobStore()
    spec = FranchiseSpec(
        franchise_name="Harry Potter",
        classes=["Gryffindor", "Slytherin"],
        characters=[CharacterRef("Harry Potter", "Gryffindor")],
    )
    job = store.create(quiz_id="overload1", spec=spec)
    store.mark_failed(job.quiz_id, "503 UNAVAILABLE high demand")

    app = create_app(
        reference=_tiny_reference(),
        job_store=store,
        gcs_store=None,
        quizzes_out_dir=tmp_path,
    )
    client = TestClient(app)

    r = client.post(
        "/quiz_results",
        json={"quiz_id": "overload1", "answers": [1.0] * 15},
    )
    assert r.status_code == 503
    assert r.json()["detail"] == AI_PROVIDER_OVERLOAD_MESSAGE


def test_get_quiz_status_sanitizes_failed_overload_error(tmp_path):
    store = QuizJobStore()
    spec = FranchiseSpec(
        franchise_name="Harry Potter",
        classes=["Gryffindor"],
        characters=[CharacterRef("Harry Potter", "Gryffindor")],
    )
    job = store.create(quiz_id="overload2", spec=spec)
    store.mark_failed(job.quiz_id, "503 UNAVAILABLE")

    app = create_app(
        reference=_tiny_reference(),
        job_store=store,
        gcs_store=None,
        quizzes_out_dir=tmp_path,
    )
    client = TestClient(app)

    r = client.get("/quizzes/overload2")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed"
    assert body["error"] == AI_PROVIDER_OVERLOAD_MESSAGE
