"""FastAPI service that classifies a 15-answer quiz vector into a Pokémon type.

Designed to run on Google Cloud Run: listens on `$PORT` (default 8080), serves
JSON, and computes weighted cosine similarity on-demand against the reference
gym-leader set bundled at build time.

The /classify response also includes a 3D PCA projection of the user's answer
vector alongside every gym leader, so the frontend can render a "where you
land in the gym leader map" visualization without a second round trip.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .classifier import (
    PCAModel,
    QUESTION_COLUMNS,
    ReferenceData,
    classify,
    fit_pca_model,
    load_reference_data,
    project_vector,
)

DEFAULT_REFERENCE_CSV = Path(__file__).parent / "data" / "gym_leaders.csv"


class ClassifyRequest(BaseModel):
    answers: list[float] = Field(
        ...,
        description=(
            "15 Likert answers in [-1, 1] "
            "(strongly disagree=-1, somewhat disagree=-0.5, neutral=0, "
            "somewhat agree=0.5, strongly agree=1)."
        ),
    )

    @field_validator("answers")
    @classmethod
    def _check_shape_and_range(cls, value: list[float]) -> list[float]:
        if len(value) != len(QUESTION_COLUMNS):
            raise ValueError(
                f"expected {len(QUESTION_COLUMNS)} answers, got {len(value)}"
            )
        for i, v in enumerate(value):
            if not (-1.0 <= v <= 1.0):
                raise ValueError(f"answers[{i}]={v} is outside [-1, 1]")
        return value


class RankingEntry(BaseModel):
    type: str
    score: float


class ProjectionPoint(BaseModel):
    x: float
    y: float
    z: float


class LeaderProjection(BaseModel):
    name: str
    type: str
    x: float
    y: float
    z: float


class Projection(BaseModel):
    user: ProjectionPoint
    leaders: list[LeaderProjection]


class ClassifyResponse(BaseModel):
    type: str
    ranking: list[RankingEntry]
    projection: Projection


def _allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if raw == "*" or not raw:
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _build_projection(model: PCAModel, answer_vector: np.ndarray) -> Projection:
    user_xyz = project_vector(model, answer_vector)
    leaders = [
        LeaderProjection(
            name=name,
            type=str(type_name),
            x=float(coords[0]),
            y=float(coords[1]),
            z=float(coords[2]),
        )
        for name, type_name, coords in zip(
            model.leaders, model.types, model.leader_projections
        )
    ]
    return Projection(
        user=ProjectionPoint(
            x=float(user_xyz[0]),
            y=float(user_xyz[1]),
            z=float(user_xyz[2]),
        ),
        leaders=leaders,
    )


def create_app(reference: ReferenceData | None = None) -> FastAPI:
    """Build a FastAPI app, optionally with an injected reference set (for tests)."""
    if reference is None:
        csv_path = Path(os.getenv("REFERENCE_CSV", str(DEFAULT_REFERENCE_CSV)))
        reference = load_reference_data(csv_path)

    pca_model = fit_pca_model(reference)

    app = FastAPI(
        title="Semantic Personality Quiz",
        description=(
            "Classifies a 15-answer Likert vector into a Pokémon gym-leader type "
            "using weighted cosine similarity over reference vectors, and returns "
            "a 3D PCA projection of the user alongside every leader."
        ),
        version="1.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str | int]:
        return {"status": "ok", "reference_size": len(reference.leaders)}

    @app.post("/classify", response_model=ClassifyResponse)
    def classify_endpoint(payload: ClassifyRequest) -> ClassifyResponse:
        answer_vector = np.asarray(payload.answers, dtype=np.float64)
        try:
            top_type, ranking = classify(answer_vector, reference)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"classification failed: {exc}") from exc
        return ClassifyResponse(
            type=top_type,
            ranking=[RankingEntry(type=t, score=s) for t, s in ranking],
            projection=_build_projection(pca_model, answer_vector),
        )

    return app


app = create_app()
