"""Functional tests for api/api.py — the FastAPI classifier service.

Exercises the app in-process via TestClient: /healthz, /classify happy path,
the PCA projection payload, and request validation. No external network.
"""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.api import create_app
from api.classifier import ReferenceData

pytestmark = pytest.mark.functional


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
    assert body["closest_character"]["name"] in {"A", "B"}
    assert body["closest_character"]["class"] == "Fire"
    assert body["closest_character"]["score"] > 0


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
