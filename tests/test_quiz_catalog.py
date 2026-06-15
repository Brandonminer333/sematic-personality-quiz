"""Tests for quiz catalog listing (local disk and GCS)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from api.storage.quiz_store import (
    GcsQuizStore,
    list_local_quiz_summaries,
    list_quiz_catalog,
    quiz_summary_from_meta,
)

pytestmark = pytest.mark.unit


def test_quiz_summary_from_meta():
    meta = {
        "title": "Harry Potter",
        "source_prompt": "Hogwarts houses",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    row = quiz_summary_from_meta(meta, "abc123")
    assert row == {
        "quiz_id": "abc123",
        "title": "Harry Potter",
        "source_prompt": "Hogwarts houses",
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def test_list_local_quiz_summaries(tmp_path):
    quiz_dir = tmp_path / "quiz1"
    quiz_dir.mkdir()
    meta = {
        "quiz_id": "quiz1",
        "title": "Dune",
        "source_prompt": "Great houses",
        "created_at": "2026-02-01T00:00:00+00:00",
    }
    (quiz_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    rows = list_local_quiz_summaries(tmp_path)
    assert len(rows) == 1
    assert rows[0]["quiz_id"] == "quiz1"
    assert rows[0]["title"] == "Dune"


@patch("google.cloud.storage.Client")
def test_gcs_list_quiz_summaries(mock_client_cls):
    meta_blob = MagicMock()
    meta_blob.name = "quizzes/q1/meta.json"
    meta_blob.download_as_text.return_value = json.dumps(
        {
            "title": "Star Wars",
            "source_prompt": "Jedi vs Sith",
            "created_at": "2026-03-01T00:00:00+00:00",
        }
    )

    mock_bucket = MagicMock()
    mock_bucket.list_blobs.return_value = [meta_blob]
    mock_client_cls.return_value.bucket.return_value = mock_bucket

    store = GcsQuizStore(bucket_name="bucket")
    rows = store.list_quiz_summaries()
    assert len(rows) == 1
    assert rows[0]["quiz_id"] == "q1"
    assert rows[0]["title"] == "Star Wars"


def test_list_quiz_catalog_merges_local_and_gcs(tmp_path):
    quiz_dir = tmp_path / "local1"
    quiz_dir.mkdir()
    (quiz_dir / "meta.json").write_text(
        json.dumps(
            {
                "title": "Local Quiz",
                "source_prompt": "local prompt",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    gcs_store = MagicMock(spec=GcsQuizStore)
    gcs_store.list_quiz_summaries.return_value = [
        {
            "quiz_id": "gcs1",
            "title": "GCS Quiz",
            "source_prompt": "gcs prompt",
            "created_at": "2026-03-01T00:00:00+00:00",
        }
    ]

    rows = list_quiz_catalog(gcs_store=gcs_store, out_dir=tmp_path)
    assert len(rows) == 2
    assert rows[0]["quiz_id"] == "gcs1"
    assert rows[1]["quiz_id"] == "local1"
