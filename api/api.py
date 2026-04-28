"""FastAPI service that classifies a 15-answer quiz vector into a Pokémon type.

Designed to run on Google Cloud Run: listens on `$PORT` (default 8080), serves
JSON, and computes weighted cosine similarity on-demand against the reference
gym-leader set bundled at build time.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .classifier import (
    QUESTION_COLUMNS,
    ReferenceData,
    classify,
    load_reference_data,
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


class ClassifyResponse(BaseModel):
    type: str
    ranking: list[RankingEntry]


def _allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if raw == "*" or not raw:
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(reference: ReferenceData | None = None) -> FastAPI:
    """Build a FastAPI app, optionally with an injected reference set (for tests)."""
    if reference is None:
        csv_path = Path(os.getenv("REFERENCE_CSV", str(DEFAULT_REFERENCE_CSV)))
        reference = load_reference_data(csv_path)

    app = FastAPI(
        title="Semantic Personality Quiz",
        description=(
            "Classifies a 15-answer Likert vector into a Pokémon gym-leader type "
            "using weighted cosine similarity over reference vectors."
        ),
        version="1.0.0",
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
        try:
            top_type, ranking = classify(np.asarray(payload.answers, dtype=np.float64), reference)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"classification failed: {exc}") from exc
        return ClassifyResponse(
            type=top_type,
            ranking=[RankingEntry(type=t, score=s) for t, s in ranking],
        )

    return app


app = create_app()
