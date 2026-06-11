"""Unit tests for api/storage/quiz_resolver.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from api.generation.quiz_jobs import QuizJobStore
from api.storage.quiz_resolver import resolve_quiz_job
from api.storage.quiz_store import GcsQuizStore

pytestmark = pytest.mark.unit


def _write_local_quiz(tmp_path: Path, quiz_id: str) -> Path:
    quiz_dir = tmp_path / quiz_id
    quiz_dir.mkdir(parents=True)
    meta = {
        "quiz_id": quiz_id,
        "title": "Harry Potter",
        "franchise_name": "Harry Potter",
        "classes": ["Gryffindor", "Slytherin"],
        "characters": [
            {"name": "Harry Potter", "class": "Gryffindor"},
            {"name": "Draco Malfoy", "class": "Slytherin"},
        ],
        "reference_csv": "reference.csv",
        "row_count": 2,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    (quiz_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (quiz_dir / "reference.csv").write_text("Leader,Type\n", encoding="utf-8")
    return quiz_dir


def test_resolve_returns_in_memory_job_first():
    from api.generation.models import CharacterRef, FranchiseSpec

    store = QuizJobStore()
    spec = FranchiseSpec(
        franchise_name="Test",
        classes=["A", "B"],
        characters=[CharacterRef("X", "A")],
    )
    store.create(quiz_id="mem1", spec=spec)
    job = store.get("mem1")
    assert job is not None
    job.status = "generating"

    resolved = resolve_quiz_job(
        store,
        "mem1",
        out_dir="/tmp/unused",
        gcs_store=None,
        cache_dir=Path("/tmp/cache"),
    )
    assert resolved is job
    assert resolved.status == "generating"


def test_resolve_hydrates_from_local_disk(tmp_path):
    store = QuizJobStore()
    quiz_id = "disk1"
    _write_local_quiz(tmp_path, quiz_id)

    resolved = resolve_quiz_job(
        store,
        quiz_id,
        out_dir=tmp_path,
        gcs_store=None,
        cache_dir=tmp_path / "cache",
    )
    assert resolved is not None
    assert resolved.status == "ready"
    assert resolved.title == "Harry Potter"
    assert resolved.classes == ["Gryffindor", "Slytherin"]
    assert resolved.reference_csv == tmp_path / quiz_id / "reference.csv"
    assert resolved.progress_completed == 2


@patch.object(GcsQuizStore, "download_quiz")
@patch.object(GcsQuizStore, "exists")
def test_resolve_hydrates_from_gcs(mock_exists, mock_download, tmp_path):
    store = QuizJobStore()
    quiz_id = "gcs1"
    quiz_dir = _write_local_quiz(tmp_path, quiz_id)
    mock_exists.return_value = True
    mock_download.return_value = quiz_dir

    gcs_store = GcsQuizStore(bucket_name="bucket")
    resolved = resolve_quiz_job(
        store,
        quiz_id,
        out_dir=tmp_path / "empty",
        gcs_store=gcs_store,
        cache_dir=tmp_path / "cache",
    )
    assert resolved is not None
    assert resolved.status == "ready"
    mock_download.assert_called_once_with(quiz_id, tmp_path / "cache")


def test_resolve_returns_none_when_not_found(tmp_path):
    store = QuizJobStore()
    gcs_store = MagicMock(spec=GcsQuizStore)
    gcs_store.exists.return_value = False

    assert (
        resolve_quiz_job(
            store,
            "missing",
            out_dir=tmp_path,
            gcs_store=gcs_store,
            cache_dir=tmp_path / "cache",
        )
        is None
    )
