"""Pure classification math, importable from the API and from tests.

The algorithm mirrors `gym_leader_eda.ipynb`:

1. Compute cosine similarity between the user's answer vector and every reference
   gym-leader vector.
2. For each Pokémon type, compute a *weighted average* of its leader vectors,
   using cosine similarities as weights — so leaders that look more like the
   user contribute more to that type's representative vector.
3. Score each type by the mean of its representative vector and rank.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

LIKERT_MAPPING: dict[str, float] = {
    "strongly disagree": -1.0,
    "somewhat disagree": -0.5,
    "neutral": 0.0,
    "somewhat agree": 0.5,
    "strongly agree": 1.0,
}

QUESTION_COLUMNS: list[str] = [f"Q{i + 1}" for i in range(15)]

# The CSV has lowercase variants ("steel", "dragon", "dark"); the frontend
# expects canonical TitleCase. Normalize once at load time so callers never
# have to worry about it.
_TYPE_DISPLAY_OVERRIDES: dict[str, str] = {
    "steel": "Steel",
    "dragon": "Dragon",
    "dark": "Dark",
}


def _canonical_type(raw: str) -> str:
    key = raw.strip()
    return _TYPE_DISPLAY_OVERRIDES.get(key.lower(), key[:1].upper() + key[1:])


@dataclass(frozen=True)
class ReferenceData:
    """In-memory reference set: leader vectors + their canonical types."""

    leaders: list[str]
    types: np.ndarray  # shape (n,)
    vectors: np.ndarray  # shape (n, 15), dtype float64


def load_reference_data(csv_path: str | Path) -> ReferenceData:
    """Load and normalize the gym-leader reference CSV."""
    df = pd.read_csv(csv_path)

    missing = {"Leader", "Type", *QUESTION_COLUMNS} - set(df.columns)
    if missing:
        raise ValueError(f"Reference CSV missing columns: {sorted(missing)}")

    df = df.dropna(subset=QUESTION_COLUMNS).copy()
    df[QUESTION_COLUMNS] = df[QUESTION_COLUMNS].replace(LIKERT_MAPPING)
    df[QUESTION_COLUMNS] = df[QUESTION_COLUMNS].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=QUESTION_COLUMNS)

    if df.empty:
        raise ValueError(f"Reference CSV at {csv_path} has no usable rows")

    return ReferenceData(
        leaders=df["Leader"].tolist(),
        types=np.array([_canonical_type(t) for t in df["Type"]]),
        vectors=df[QUESTION_COLUMNS].to_numpy(dtype=np.float64),
    )


def cosine_similarity(vector: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """Cosine similarity of `vector` against each row in `vectors`.

    Returns zeros where a norm is zero rather than NaN, so downstream weighting
    handles the all-neutral input gracefully.
    """
    dot_products = vectors @ vector
    norms = np.linalg.norm(vectors, axis=1) * np.linalg.norm(vector)
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        dot_products = vectors @ vector
        norms = np.linalg.norm(vectors, axis=1) * np.linalg.norm(vector)
        sims = dot_products / norms
    return np.nan_to_num(sims, nan=0.0, posinf=0.0, neginf=0.0)


def rank_types(answer_vector: np.ndarray, ref: ReferenceData) -> list[tuple[str, float]]:
    """Rank Pokémon types by weighted-cosine score, descending."""
    sims = cosine_similarity(answer_vector, ref.vectors)

    scores: dict[str, float] = {}
    for pokemon_type in pd.unique(ref.types):
        mask = ref.types == pokemon_type
        weights = sims[mask]
        type_vectors = ref.vectors[mask]

        if np.sum(weights) == 0:
            type_centroid = np.mean(type_vectors, axis=0)
        else:
            type_centroid = np.average(type_vectors, axis=0, weights=weights)

        scores[str(pokemon_type)] = float(type_centroid.mean())

    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def classify(answer_vector: np.ndarray, ref: ReferenceData) -> tuple[str, list[tuple[str, float]]]:
    """Return (top_type, full_ranking)."""
    ranking = rank_types(answer_vector, ref)
    return ranking[0][0], ranking


def closest_character(
    answer_vector: np.ndarray, ref: ReferenceData
) -> tuple[str, str, float]:
    """Return (character_name, class_name, cosine_score) for the nearest reference row."""
    sims = cosine_similarity(answer_vector, ref.vectors)
    idx = int(np.argmax(sims))
    return (
        ref.leaders[idx],
        str(ref.types[idx]),
        float(sims[idx]),
    )


@dataclass(frozen=True)
class PCAModel:
    """3-component PCA fit on the reference leader vectors.

    We fit once at startup and project users on each request, instead of
    re-fitting for every quiz submission. That keeps the projection axes
    stable across users (the "type space" is the same map for everyone)
    and saves ~O(n*d) work per request.
    """

    mean: np.ndarray  # shape (d,)
    components: np.ndarray  # shape (3, d)
    leader_projections: np.ndarray  # shape (n, 3)
    leaders: list[str]
    types: np.ndarray  # shape (n,)


def fit_pca_model(ref: ReferenceData, n_components: int = 3) -> PCAModel:
    """Fit a PCA on `ref.vectors` via mean-centering + thin SVD.

    Equivalent to `sklearn.decomposition.PCA(n_components).fit_transform`,
    but with no extra dependency. Falls back gracefully when there are
    fewer rows than requested components by zero-padding the missing axes.
    """
    if ref.vectors.size == 0:
        raise ValueError("Cannot fit PCA on an empty reference set")

    mean = ref.vectors.mean(axis=0)
    centered = ref.vectors - mean

    # Thin SVD: rows of Vt are the principal axes ordered by descending
    # singular value, matching sklearn's convention.
    _, _, vt = np.linalg.svd(centered, full_matrices=False)

    available = vt.shape[0]
    if available >= n_components:
        components = vt[:n_components]
    else:
        padding = np.zeros((n_components - available, vt.shape[1]))
        components = np.vstack([vt, padding])

    leader_projections = centered @ components.T
    return PCAModel(
        mean=mean,
        components=components,
        leader_projections=leader_projections,
        leaders=list(ref.leaders),
        types=ref.types.copy(),
    )


def project_vector(model: PCAModel, vector: np.ndarray) -> np.ndarray:
    """Project a single answer vector into the model's PCA basis."""
    return (vector - model.mean) @ model.components.T
