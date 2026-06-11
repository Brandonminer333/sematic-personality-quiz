"""Unit tests for api/storage/quiz_store.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from api.storage.quiz_store import GcsQuizStore, local_exists, local_quiz_dir, load_meta_from_path

pytestmark = pytest.mark.unit


def test_local_quiz_dir_and_exists(tmp_path):
    quiz_id = "abc123"
    quiz_dir = local_quiz_dir(quiz_id, tmp_path)
    assert quiz_dir == tmp_path / quiz_id
    assert not local_exists(quiz_id, tmp_path)

    quiz_dir.mkdir(parents=True)
    (quiz_dir / "meta.json").write_text("{}", encoding="utf-8")
    assert local_exists(quiz_id, tmp_path)


def test_load_meta_from_path(tmp_path):
    meta = {"quiz_id": "x", "title": "Test", "classes": ["A", "B"]}
    path = tmp_path / "meta.json"
    path.write_text(json.dumps(meta), encoding="utf-8")
    assert load_meta_from_path(path) == meta


def test_gcs_quiz_store_from_env(monkeypatch):
    monkeypatch.delenv("GCS_QUIZZES_BUCKET", raising=False)
    assert GcsQuizStore.from_env() is None

    monkeypatch.setenv("GCS_QUIZZES_BUCKET", "my-bucket")
    monkeypatch.setenv("GCS_QUIZZES_PREFIX", "custom")
    store = GcsQuizStore.from_env()
    assert store is not None
    assert store.bucket_name == "my-bucket"
    assert store.prefix == "custom"


@patch("google.cloud.storage.Client")
def test_gcs_upload_quiz_dir(mock_client_cls, tmp_path):
    mock_bucket = MagicMock()
    mock_client_cls.return_value.bucket.return_value = mock_bucket

    quiz_dir = tmp_path / "quiz1"
    quiz_dir.mkdir()
    (quiz_dir / "meta.json").write_text("{}", encoding="utf-8")
    raw_dir = quiz_dir / "raw"
    raw_dir.mkdir()
    (raw_dir / "Harry.txt").write_text("trace", encoding="utf-8")
    (quiz_dir / "reference.csv").write_text("Leader,Type\n", encoding="utf-8")

    store = GcsQuizStore(bucket_name="bucket", prefix="quizzes")
    store.upload_quiz_dir(quiz_dir)

    assert mock_bucket.blob.call_count == 3
    uploaded_names = {call.args[0] for call in mock_bucket.blob.call_args_list}
    assert uploaded_names == {
        "quizzes/quiz1/meta.json",
        "quizzes/quiz1/raw/Harry.txt",
        "quizzes/quiz1/reference.csv",
    }


@patch("google.cloud.storage.Client")
def test_gcs_exists_and_load_meta(mock_client_cls):
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    mock_blob.download_as_text.return_value = json.dumps({"quiz_id": "q1"})
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client_cls.return_value.bucket.return_value = mock_bucket

    store = GcsQuizStore(bucket_name="bucket")
    assert store.exists("q1") is True
    assert store.load_meta("q1") == {"quiz_id": "q1"}
    mock_bucket.blob.assert_called_with("quizzes/q1/meta.json")


@patch("google.cloud.storage.Client")
def test_gcs_download_quiz(mock_client_cls, tmp_path):
    meta_blob = MagicMock()
    meta_blob.name = "quizzes/q1/meta.json"
    meta_blob.download_to_filename = lambda path: Path(path).write_text(
        json.dumps({"quiz_id": "q1", "reference_csv": "reference.csv"}),
        encoding="utf-8",
    )

    csv_blob = MagicMock()
    csv_blob.name = "quizzes/q1/reference.csv"
    csv_blob.download_to_filename = lambda path: Path(path).write_text(
        "Leader,Type\n", encoding="utf-8"
    )

    mock_bucket = MagicMock()
    mock_bucket.list_blobs.return_value = [meta_blob, csv_blob]
    mock_client_cls.return_value.bucket.return_value = mock_bucket

    store = GcsQuizStore(bucket_name="bucket")
    quiz_dir = store.download_quiz("q1", tmp_path)

    assert quiz_dir == tmp_path / "q1"
    assert (quiz_dir / "meta.json").is_file()
    assert (quiz_dir / "reference.csv").is_file()
