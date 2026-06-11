"""Functional tests for quiz creation and async results API."""

from __future__ import annotations

import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.api import create_app
from api.classifier import ReferenceData, load_reference_data
from api.generation.models import CharacterRef, FranchiseSpec, ReferenceRow
from api.generation.persist import write_quiz_artifact
from api.generation.quiz_jobs import QuizJobStore

pytestmark = pytest.mark.functional


def _tiny_reference() -> ReferenceData:
    return ReferenceData(
        leaders=["A", "B", "C", "D"],
        types=np.array(["Fire", "Fire", "Water", "Water"]),
        vectors=np.array(
            [
                [1.0] + [0.5] * 14,
                [0.8] + [0.4] * 14,
                [-1.0] + [-0.5] * 14,
                [-0.8] + [-0.4] * 14,
            ]
        ),
    )


def _fake_spec(prompt: str, _llm) -> FranchiseSpec:
    return FranchiseSpec(
        franchise_name="Harry Potter",
        classes=["Gryffindor", "Slytherin"],
        characters=[
            CharacterRef("Harry Potter", "Gryffindor"),
            CharacterRef("Draco Malfoy", "Slytherin"),
        ],
        wiki_base_url="https://harrypotter.fandom.com/wiki/",
        source_prompt=prompt,
    )


@pytest.fixture
def quiz_client(tmp_path) -> TestClient:
    store = QuizJobStore()

    def _instant_generation(quiz_id, spec, *, store, out_dir=None, llm=None, gcs_store=None):
        rows = [
            ReferenceRow("Harry Potter", "Gryffindor", ["strongly agree"] * 15),
            ReferenceRow("Draco Malfoy", "Slytherin", ["somewhat disagree"] * 15),
        ]
        artifact = write_quiz_artifact(
            quiz_id=quiz_id,
            spec=spec,
            rows=rows,
            out_dir=out_dir or tmp_path,
        )
        store.mark_ready(quiz_id, reference_csv=artifact.reference_csv)

    app = create_app(
        reference=_tiny_reference(),
        job_store=store,
        spec_builder=_fake_spec,
        generation_runner=_instant_generation,
        quizzes_out_dir=tmp_path,
        gcs_store=None,
    )
    app.state.job_store = store
    return TestClient(app)


def test_create_quiz_returns_generating_status(quiz_client: TestClient):
    r = quiz_client.post("/quizzes", json={"prompt": "Hogwarts houses"})
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "generating"
    assert body["title"] == "Harry Potter"
    assert "Gryffindor" in body["classes"]
    assert body["quiz_id"]


def _wait_for_ready(client: TestClient, quiz_id: str, *, timeout_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        body = client.get(f"/quizzes/{quiz_id}").json()
        if body["status"] == "ready":
            return
        time.sleep(0.05)
    raise AssertionError(f"quiz {quiz_id} did not become ready in time")


def test_get_quiz_status_becomes_ready(quiz_client: TestClient):
    created = quiz_client.post("/quizzes", json={"prompt": "Hogwarts houses"}).json()
    quiz_id = created["quiz_id"]
    _wait_for_ready(quiz_client, quiz_id)

    status = quiz_client.get(f"/quizzes/{quiz_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "ready"
    assert body["progress"]["completed"] == body["progress"]["total"]


def test_quiz_results_classifies_custom_quiz(quiz_client: TestClient):
    created = quiz_client.post("/quizzes", json={"prompt": "Hogwarts houses"}).json()
    quiz_id = created["quiz_id"]
    _wait_for_ready(quiz_client, quiz_id)

    r = quiz_client.post(
        "/quiz_results",
        json={"quiz_id": quiz_id, "answers": [1.0] * 15},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["quiz_id"] == quiz_id
    assert body["type"] in {"Gryffindor", "Slytherin"}
    assert body["closest_character"]["name"] in {"Harry Potter", "Draco Malfoy"}
    assert "class" in body["closest_character"]
    assert "score" in body["closest_character"]


def test_get_quiz_status_hydrates_from_disk_after_store_clear(quiz_client: TestClient, tmp_path):
    created = quiz_client.post("/quizzes", json={"prompt": "Hogwarts houses"}).json()
    quiz_id = created["quiz_id"]
    _wait_for_ready(quiz_client, quiz_id)

    # Simulate API restart: in-memory store empty, artifacts still on disk.
    quiz_client.app.state.job_store.clear()

    status = quiz_client.get(f"/quizzes/{quiz_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "ready"
    assert body["title"] == "Harry Potter"


def test_quiz_results_hydrates_from_disk_after_store_clear(quiz_client: TestClient):
    created = quiz_client.post("/quizzes", json={"prompt": "Hogwarts houses"}).json()
    quiz_id = created["quiz_id"]
    _wait_for_ready(quiz_client, quiz_id)

    quiz_client.app.state.job_store.clear()

    r = quiz_client.post(
        "/quiz_results",
        json={"quiz_id": quiz_id, "answers": [1.0] * 15},
    )
    assert r.status_code == 200
    assert r.json()["quiz_id"] == quiz_id


def test_quiz_results_returns_202_while_generating(tmp_path):
    store = QuizJobStore()

    app = create_app(
        reference=_tiny_reference(),
        job_store=store,
        spec_builder=_fake_spec,
        generation_runner=lambda **kwargs: None,
        quizzes_out_dir=tmp_path,
    )
    client = TestClient(app)

    created = client.post("/quizzes", json={"prompt": "Hogwarts houses"}).json()
    quiz_id = created["quiz_id"]

    r = client.post(
        "/quiz_results",
        json={"quiz_id": quiz_id, "answers": [1.0] * 15},
    )
    assert r.status_code == 202
    assert r.json()["status"] == "generating"
