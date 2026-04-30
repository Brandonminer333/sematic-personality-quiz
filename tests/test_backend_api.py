"""Unit + API tests for the FastAPI classifier backend.

Covers:
- Pure math (cosine_similarity, rank_types) on a tiny in-memory reference set.
- CSV loader normalizes lowercase types ("steel" -> "Steel").
- /healthz reports reference size.
- /classify returns the top type plus a sorted ranking.
- /classify validates payload shape and Likert range.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.api import create_app
from api.classifier import (
    QUESTION_COLUMNS,
    ReferenceData,
    classify,
    cosine_similarity,
    fit_pca_model,
    load_reference_data,
    project_vector,
    rank_types,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_CSV = REPO_ROOT / "api" / "data" / "gym_leaders.csv"


def _tiny_reference() -> ReferenceData:
    """Two Fire leaders that lean +1, two Water leaders that lean -1."""
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


def test_cosine_similarity_handles_zero_vector_without_nan():
    v = np.zeros(3)
    vs = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    sims = cosine_similarity(v, vs)
    assert sims.shape == (2,)
    assert np.all(sims == 0.0)


def test_cosine_similarity_basic():
    v = np.array([1.0, 0.0])
    vs = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]])
    sims = cosine_similarity(v, vs)
    assert sims[0] == pytest.approx(1.0)
    assert sims[1] == pytest.approx(0.0)
    assert sims[2] == pytest.approx(-1.0)


def test_rank_types_orders_descending():
    ref = _tiny_reference()
    answer = np.ones(15)
    ranking = rank_types(answer, ref)
    types = [t for t, _ in ranking]
    scores = [s for _, s in ranking]
    assert types == ["Fire", "Water"]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] > scores[1]


def test_classify_returns_consistent_top_with_ranking():
    """The first entry of `ranking` is always the chosen `type`."""
    ref = _tiny_reference()
    top, ranking = classify(np.ones(15), ref)
    assert ranking[0][0] == top
    assert all(ranking[i][1] >= ranking[i + 1][1] for i in range(len(ranking) - 1))


def test_load_reference_data_normalizes_lowercase_types():
    ref = load_reference_data(REFERENCE_CSV)
    assert len(ref.leaders) > 0
    assert ref.vectors.shape == (len(ref.leaders), len(QUESTION_COLUMNS))

    types = set(ref.types.tolist())
    assert "Steel" in types
    assert "Dragon" in types
    assert "Dark" in types
    assert "steel" not in types
    assert "dragon" not in types


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(reference=_tiny_reference()))


def test_healthz_reports_reference_size(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["reference_size"] == 4


def test_classify_endpoint_returns_top_type(client: TestClient):
    r = client.post("/classify", json={"answers": [1.0] * 15})
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "Fire"
    assert [entry["type"] for entry in body["ranking"]] == ["Fire", "Water"]
    assert body["ranking"][0]["score"] >= body["ranking"][1]["score"]


def test_classify_endpoint_includes_pca_projection(client: TestClient):
    """The response carries a 3D projection of the user and every leader,
    so the frontend can render the personality map without a second request."""
    r = client.post("/classify", json={"answers": [1.0] * 15})
    assert r.status_code == 200
    projection = r.json()["projection"]

    assert set(projection["user"]) == {"x", "y", "z"}
    assert all(isinstance(projection["user"][k], float) for k in ("x", "y", "z"))

    leaders = projection["leaders"]
    assert len(leaders) == 4  # matches _tiny_reference()
    leader_names = {entry["name"] for entry in leaders}
    assert leader_names == {"A", "B", "C", "D"}
    for entry in leaders:
        assert entry["type"] in {"Fire", "Water"}
        for k in ("x", "y", "z"):
            assert isinstance(entry[k], float)


def test_pca_model_projects_leaders_consistently():
    ref = _tiny_reference()
    model = fit_pca_model(ref)

    assert model.components.shape == (3, 15)
    assert model.leader_projections.shape == (4, 3)

    # Projecting each leader vector through `project_vector` must reproduce
    # the cached `leader_projections` (up to FP noise).
    for i, vec in enumerate(ref.vectors):
        np.testing.assert_allclose(
            project_vector(model, vec),
            model.leader_projections[i],
            atol=1e-9,
        )


def test_classify_endpoint_rejects_wrong_length(client: TestClient):
    r = client.post("/classify", json={"answers": [1.0] * 14})
    assert r.status_code == 422
    assert "expected 15 answers" in r.text


def test_classify_endpoint_rejects_out_of_range(client: TestClient):
    r = client.post("/classify", json={"answers": [2.0] + [0.0] * 14})
    assert r.status_code == 422
    assert "outside [-1, 1]" in r.text


def test_classify_endpoint_rejects_non_numeric(client: TestClient):
    r = client.post("/classify", json={"answers": ["a"] * 15})
    assert r.status_code == 422


def test_real_reference_classifies_strongly_agree_vector():
    """End-to-end with the bundled reference data: a real answer vector
    classifies to a known canonical (TitleCase) type."""
    app = create_app()
    c = TestClient(app)
    r = c.post("/classify", json={"answers": [1.0] * 15})
    assert r.status_code == 200
    body = r.json()
    assert body["type"][:1].isupper(), f"expected canonical type, got {body['type']!r}"
    assert len(body["ranking"]) >= 5
