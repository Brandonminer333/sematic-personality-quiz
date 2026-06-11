"""Resolve a quiz job from memory, local disk, or GCS."""

from __future__ import annotations

from pathlib import Path

from api.generation.models import CharacterRef, FranchiseSpec
from api.generation.quiz_jobs import QuizJob, QuizJobStore
from api.storage.quiz_store import GcsQuizStore, local_exists, local_quiz_dir, load_meta_from_path


def _spec_from_meta(meta: dict) -> FranchiseSpec:
    characters = meta.get("characters") or []
    refs: list[CharacterRef] = []
    for item in characters:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        character_class = str(item.get("class", "")).strip()
        if name and character_class:
            refs.append(CharacterRef(name=name, character_class=character_class))

    return FranchiseSpec(
        franchise_name=str(meta.get("franchise_name") or meta.get("title") or ""),
        classes=[str(c) for c in meta.get("classes") or []],
        characters=refs,
        wiki_base_url=meta.get("wiki_base_url"),
        source_prompt=meta.get("source_prompt"),
    )


def _job_from_meta(quiz_id: str, quiz_dir: Path, meta: dict) -> QuizJob:
    reference_name = str(meta.get("reference_csv") or "reference.csv")
    reference_csv = quiz_dir / reference_name
    row_count = int(meta.get("row_count") or len(meta.get("characters") or []))
    return QuizJob(
        quiz_id=quiz_id,
        status="ready",
        title=str(meta.get("title") or meta.get("franchise_name") or ""),
        classes=[str(c) for c in meta.get("classes") or []],
        spec=_spec_from_meta(meta),
        reference_csv=reference_csv,
        progress_completed=row_count,
        progress_total=row_count,
        created_at=str(meta.get("created_at") or ""),
    )


def resolve_quiz_job(
    store: QuizJobStore,
    quiz_id: str,
    *,
    out_dir: str | Path | None,
    gcs_store: GcsQuizStore | None,
    cache_dir: Path,
) -> QuizJob | None:
    """Return in-memory, local, or GCS-hydrated job; None if not found."""
    job = store.get(quiz_id)
    if job is not None:
        return job

    if local_exists(quiz_id, out_dir):
        quiz_dir = local_quiz_dir(quiz_id, out_dir)
        meta = load_meta_from_path(quiz_dir / "meta.json")
        return _job_from_meta(quiz_id, quiz_dir, meta)

    if gcs_store is not None and gcs_store.exists(quiz_id):
        quiz_dir = gcs_store.download_quiz(quiz_id, cache_dir)
        meta = load_meta_from_path(quiz_dir / "meta.json")
        return _job_from_meta(quiz_id, quiz_dir, meta)

    return None
