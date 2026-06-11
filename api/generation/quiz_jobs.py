"""In-memory quiz generation jobs for async API flows."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Literal

from api.generation.models import FranchiseSpec
from api.generation.orchestrator import generate_quiz
from api.llm.client import LLMClient

if TYPE_CHECKING:
    from api.storage.quiz_store import GcsQuizStore

QuizStatus = Literal["generating", "ready", "failed"]


@dataclass
class QuizJob:
    quiz_id: str
    status: QuizStatus
    title: str
    classes: list[str]
    spec: FranchiseSpec
    error: str | None = None
    progress_completed: int = 0
    progress_total: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    reference_csv: Path | None = None


class QuizJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, QuizJob] = {}
        self._lock = threading.Lock()

    def create(self, *, quiz_id: str, spec: FranchiseSpec) -> QuizJob:
        job = QuizJob(
            quiz_id=quiz_id,
            status="generating",
            title=spec.franchise_name,
            classes=list(spec.classes),
            spec=spec,
            progress_total=len(spec.characters),
        )
        with self._lock:
            self._jobs[quiz_id] = job
        return job

    def get(self, quiz_id: str) -> QuizJob | None:
        with self._lock:
            return self._jobs.get(quiz_id)

    def mark_ready(self, quiz_id: str, *, reference_csv: Path) -> None:
        with self._lock:
            job = self._jobs.get(quiz_id)
            if job is None:
                return
            job.status = "ready"
            job.reference_csv = reference_csv
            job.progress_completed = job.progress_total
            job.error = None

    def mark_failed(self, quiz_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(quiz_id)
            if job is None:
                return
            job.status = "failed"
            job.error = error

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()


def run_generation_job(
    quiz_id: str,
    spec: FranchiseSpec,
    *,
    store: QuizJobStore,
    out_dir: str | Path | None = None,
    llm: LLMClient | None = None,
    gcs_store: GcsQuizStore | None = None,
) -> None:
    """Background worker: stages 3–5 for a parsed franchise spec."""
    try:
        artifact, _skipped = generate_quiz(
            spec,
            quiz_id=quiz_id,
            out_dir=out_dir,
            llm=llm,
            save_raw=True,
        )
        store.mark_ready(quiz_id, reference_csv=artifact.reference_csv)
        if gcs_store is not None:
            try:
                gcs_store.upload_quiz_dir(artifact.quiz_dir)
            except Exception as exc:
                store.mark_failed(quiz_id, f"failed to upload quiz to GCS: {exc}")
    except Exception as exc:
        store.mark_failed(quiz_id, str(exc))


def start_generation_in_background(
    quiz_id: str,
    spec: FranchiseSpec,
    *,
    store: QuizJobStore,
    out_dir: str | Path | None = None,
    llm: LLMClient | None = None,
    gcs_store: GcsQuizStore | None = None,
    runner: Callable[..., None] | None = None,
) -> None:
    """Spawn generation on a daemon thread (MVP async)."""
    target = runner or run_generation_job
    thread = threading.Thread(
        target=target,
        kwargs={
            "quiz_id": quiz_id,
            "spec": spec,
            "store": store,
            "out_dir": out_dir,
            "llm": llm,
            "gcs_store": gcs_store,
        },
        daemon=True,
    )
    thread.start()


_DEFAULT_STORE = QuizJobStore()


def get_default_job_store() -> QuizJobStore:
    return _DEFAULT_STORE
