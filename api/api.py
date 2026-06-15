"""FastAPI service: quiz generation, classification, and health."""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from api.generation.discover_roster import build_franchise_spec_from_prompt
from api.generation.models import FranchiseSpec
from api.generation.quiz_jobs import QuizJobStore, get_default_job_store, start_generation_in_background
from api.llm.client import GeminiRateLimitError, GeminiUnavailableError, LLMClient
from api.llm.errors import (
    AI_PROVIDER_OVERLOAD_MESSAGE,
    http_status_for_error,
    is_ai_provider_overload,
    user_facing_error,
)
from api.logging_config import setup_logging
from api.storage.quiz_resolver import resolve_quiz_job
from api.storage.quiz_store import GcsQuizStore, default_cache_dir, list_quiz_catalog

from .classifier import (
    PCAModel,
    QUESTION_COLUMNS,
    ReferenceData,
    classify,
    closest_character,
    fit_pca_model,
    load_reference_data,
    project_vector,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
setup_logging()

logger = logging.getLogger(__name__)

DEFAULT_REFERENCE_CSV = Path(__file__).parent / "data" / "gym_leaders.csv"
PRESET_QUIZ_ID = "preset"

_GCS_STORE_UNSET = object()

MAX_PROMPT_LENGTH = 120
def _gemini_api_key_configured() -> bool:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return bool(key) and key != "api_key"


def _missing_api_key_detail() -> str:
    return (
        "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key, "
        "or set FAKE_QUIZ_SPEC=1 in .env for local development without Gemini."
    )


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


class CreateQuizRequest(BaseModel):
    prompt: str = Field(..., min_length=1)


class CreateQuizResponse(BaseModel):
    quiz_id: str
    status: str
    title: str
    classes: list[str]


class QuizCatalogItem(BaseModel):
    quiz_id: str
    title: str
    source_prompt: str | None = None
    created_at: str | None = None


class QuizCatalogResponse(BaseModel):
    quizzes: list[QuizCatalogItem]


class QuizStatusResponse(BaseModel):
    quiz_id: str
    status: str
    title: str
    classes: list[str]
    progress: dict[str, int]
    error: str | None = None


class QuizResultsRequest(BaseModel):
    answers: list[float]
    quiz_id: str | None = Field(
        default=None,
        description="Custom quiz id from POST /quizzes. Omit for the bundled preset.",
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


class ClosestCharacter(BaseModel):
    name: str
    class_: str = Field(serialization_alias="class")
    score: float


class ClassifyResponse(BaseModel):
    type: str
    ranking: list[RankingEntry]
    projection: Projection
    closest_character: ClosestCharacter
    quiz_id: str | None = None


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


def _build_classify_response(
    *,
    answer_vector: np.ndarray,
    ref: ReferenceData,
    model: PCAModel,
    quiz_id: str | None,
) -> ClassifyResponse:
    top_type, ranking = classify(answer_vector, ref)
    character_name, character_class, score = closest_character(answer_vector, ref)
    return ClassifyResponse(
        type=top_type,
        ranking=[RankingEntry(type=t, score=s) for t, s in ranking],
        projection=_build_projection(model, answer_vector),
        closest_character=ClosestCharacter(
            name=character_name,
            class_=character_class,
            score=score,
        ),
        quiz_id=quiz_id,
    )


def _job_status_payload(job) -> QuizStatusResponse:
    return QuizStatusResponse(
        quiz_id=job.quiz_id,
        status=job.status,
        title=job.title,
        classes=job.classes,
        progress={
            "completed": job.progress_completed,
            "total": job.progress_total,
        },
        error=user_facing_error(job.error) if job.error else None,
    )


def _raise_for_failed_job(job) -> None:
    detail = user_facing_error(job.error)
    raise HTTPException(status_code=http_status_for_error(job.error), detail=detail)


def _wait_for_ready_job(
    store: QuizJobStore,
    quiz_id: str,
    *,
    out_dir: str | Path | None,
    gcs_store: GcsQuizStore | None,
    cache_dir: Path,
):
    """Return the ready job or a 202 response without blocking the worker."""
    job = resolve_quiz_job(
        store,
        quiz_id,
        out_dir=out_dir,
        gcs_store=gcs_store,
        cache_dir=cache_dir,
    )
    if job is None:
        raise HTTPException(status_code=404, detail=f"quiz {quiz_id!r} not found")
    if job.status == "ready":
        return job
    if job.status == "failed":
        _raise_for_failed_job(job)
    return JSONResponse(
        status_code=202,
        content=_job_status_payload(job).model_dump(),
    )


def create_app(
    reference: ReferenceData | None = None,
    *,
    job_store: QuizJobStore | None = None,
    spec_builder: Callable[[str, LLMClient | None], FranchiseSpec] | None = None,
    generation_runner: Callable[..., None] | None = None,
    quizzes_out_dir: str | Path | None = None,
    gcs_store: GcsQuizStore | None | object = _GCS_STORE_UNSET,
    cache_dir: str | Path | None = None,
) -> FastAPI:
    """Build a FastAPI app, optionally with injected dependencies (for tests)."""
    if reference is None:
        csv_path = Path(os.getenv("REFERENCE_CSV", str(DEFAULT_REFERENCE_CSV)))
        reference = load_reference_data(csv_path)

    preset_pca = fit_pca_model(reference)
    store = job_store if job_store is not None else get_default_job_store()
    if gcs_store is _GCS_STORE_UNSET:
        quiz_gcs_store = GcsQuizStore.from_env()
    else:
        quiz_gcs_store = gcs_store  # type: ignore[assignment]
    quiz_cache_dir = Path(cache_dir) if cache_dir is not None else default_cache_dir()

    app = FastAPI(
        title="Semantic Personality Quiz",
        description=(
            "Creates custom franchise quizzes from natural language, classifies "
            "15-answer Likert vectors via cosine similarity, and returns "
            "a 3D PCA projection."
        ),
        version="1.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log_fn = logger.warning if response.status_code >= 400 else logger.info
        log_fn(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": duration_ms,
                "event": "http_request",
            },
        )
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str | int]:
        return {"status": "ok", "reference_size": len(reference.leaders)}

    @app.post("/quizzes", response_model=CreateQuizResponse, status_code=202)
    def create_quiz(payload: CreateQuizRequest) -> CreateQuizResponse:
        """Stages 1–2 synchronously, then start async generation (stages 3–5)."""
        prompt = payload.prompt.strip()
        try:
            if len(prompt) > MAX_PROMPT_LENGTH:
                raise HTTPException(
                    status_code=422,
                    detail=f"prompt is too long, must be less than {MAX_PROMPT_LENGTH} characters",
                ) # TODO: Double check error handling
            if spec_builder is not None:
                spec = spec_builder(prompt, None)
            else:
                if not _gemini_api_key_configured():
                    raise HTTPException(
                        status_code=422,
                        detail=_missing_api_key_detail(),
                    )
                spec = build_franchise_spec_from_prompt(prompt, LLMClient())
        except HTTPException:
            raise
        except (GeminiRateLimitError, GeminiUnavailableError):
            logger.warning(
                "Gemini unavailable while creating quiz",
                extra={"stage": "parse_spec", "event": "gemini_overload"},
            )
            raise HTTPException(
                status_code=503,
                detail=AI_PROVIDER_OVERLOAD_MESSAGE,
            )
        except ValueError as exc:
            if is_ai_provider_overload(str(exc)):
                logger.warning(
                    "Gemini unavailable while creating quiz: %s",
                    exc,
                    extra={"stage": "parse_spec", "event": "gemini_overload"},
                )
                raise HTTPException(
                    status_code=503,
                    detail=AI_PROVIDER_OVERLOAD_MESSAGE,
                ) from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"failed to parse quiz prompt: {exc}",
            ) from exc

        quiz_id = uuid.uuid4().hex
        store.create(quiz_id=quiz_id, spec=spec)
        logger.info(
            "Quiz created",
            extra={"quiz_id": quiz_id, "stage": "create", "event": "quiz_created"},
        )
        start_generation_in_background(
            quiz_id,
            spec,
            store=store,
            out_dir=quizzes_out_dir,
            gcs_store=quiz_gcs_store,
            runner=generation_runner,
        )
        return CreateQuizResponse(
            quiz_id=quiz_id,
            status="generating",
            title=spec.franchise_name,
            classes=list(spec.classes),
        )

    @app.get("/quizzes", response_model=QuizCatalogResponse)
    def list_quizzes() -> QuizCatalogResponse:
        """List persisted quizzes from GCS and/or local storage."""
        try:
            rows = list_quiz_catalog(gcs_store=quiz_gcs_store, out_dir=quizzes_out_dir)
        except Exception as exc:
            logger.exception("Failed to list quizzes", extra={"event": "quiz_list_failed"})
            raise HTTPException(
                status_code=500,
                detail=f"failed to list quizzes: {exc}",
            ) from exc
        return QuizCatalogResponse(
            quizzes=[QuizCatalogItem(**row) for row in rows],
        )

    @app.get("/quizzes/{quiz_id}", response_model=QuizStatusResponse)
    def get_quiz_status(quiz_id: str) -> QuizStatusResponse:
        job = resolve_quiz_job(
            store,
            quiz_id,
            out_dir=quizzes_out_dir,
            gcs_store=quiz_gcs_store,
            cache_dir=quiz_cache_dir,
        )
        if job is None:
            raise HTTPException(status_code=404, detail=f"quiz {quiz_id!r} not found")
        return _job_status_payload(job)

    @app.post("/quiz_results", response_model=ClassifyResponse)
    def quiz_results(payload: QuizResultsRequest):
        answer_vector = np.asarray(payload.answers, dtype=np.float64)
        quiz_id = payload.quiz_id

        if quiz_id is None or quiz_id == PRESET_QUIZ_ID:
            try:
                return _build_classify_response(
                    answer_vector=answer_vector,
                    ref=reference,
                    model=preset_pca,
                    quiz_id=PRESET_QUIZ_ID,
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=f"classification failed: {exc}",
                ) from exc

        ready = _wait_for_ready_job(
            store,
            quiz_id,
            out_dir=quizzes_out_dir,
            gcs_store=quiz_gcs_store,
            cache_dir=quiz_cache_dir,
        )
        if isinstance(ready, JSONResponse):
            return ready

        if ready.reference_csv is None:
            raise HTTPException(
                status_code=500,
                detail="quiz is ready but reference CSV is missing",
            )

        try:
            custom_ref = load_reference_data(ready.reference_csv)
            custom_pca = fit_pca_model(custom_ref)
            return _build_classify_response(
                answer_vector=answer_vector,
                ref=custom_ref,
                model=custom_pca,
                quiz_id=quiz_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"classification failed: {exc}",
            ) from exc

    @app.post("/classify", response_model=ClassifyResponse)
    def classify_endpoint(payload: ClassifyRequest) -> ClassifyResponse:
        """Backward-compatible alias for the bundled preset quiz."""
        return quiz_results(
            QuizResultsRequest(answers=payload.answers, quiz_id=PRESET_QUIZ_ID)
        )

    return app


def _build_default_app() -> FastAPI:
    kwargs: dict = {}
    if os.getenv("FAKE_QUIZ_SPEC") == "1":
        from api.test_mode import fake_spec_builder, instant_generation_runner

        kwargs["spec_builder"] = fake_spec_builder
        kwargs["generation_runner"] = instant_generation_runner
        out_dir = os.getenv("QUIZZES_OUT_DIR")
        if out_dir:
            kwargs["quizzes_out_dir"] = out_dir
    return create_app(**kwargs)


app = _build_default_app()
