"""Unit tests for api/classifier.py — pure classification math.

Covers cosine similarity, weighted-cosine ranking, the CSV loader's type
normalization, and PCA projection — all on tiny in-memory references or the
bundled reference CSV, with no network or app boot.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from api.classifier import (
    QUESTION_COLUMNS,
    ReferenceData,
    classify,
    closest_character,
    cosine_similarity,
    fit_pca_model,
    load_reference_data,
    project_vector,
    rank_types,
)

pytestmark = pytest.mark.unit

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


def test_closest_character_returns_highest_cosine_match():
    ref = _tiny_reference()
    answer = ref.vectors[0].copy()
    name, character_class, score = closest_character(answer, ref)
    assert name == "A"
    assert character_class == "Fire"
    assert score == pytest.approx(1.0, abs=1e-6)


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
