"""Read and write quiz artifacts on local disk or Google Cloud Storage."""

from __future__ import annotations

import json
import os
from pathlib import Path

from api.generation.persist import default_quizzes_dir

DEFAULT_GCS_PREFIX = "quizzes"
DEFAULT_CACHE_DIR = Path("/tmp/quiz-cache")


def local_quiz_dir(quiz_id: str, out_dir: str | Path | None = None) -> Path:
    base = Path(out_dir) if out_dir is not None else default_quizzes_dir()
    return base / quiz_id


def local_exists(quiz_id: str, out_dir: str | Path | None = None) -> bool:
    return (local_quiz_dir(quiz_id, out_dir) / "meta.json").is_file()


def load_meta_from_path(meta_path: Path) -> dict:
    return json.loads(meta_path.read_text(encoding="utf-8"))


def quiz_summary_from_meta(meta: dict, quiz_id: str) -> dict:
    """Extract list-catalog fields from a persisted meta.json object."""
    return {
        "quiz_id": quiz_id,
        "title": str(meta.get("title") or meta.get("franchise_name") or quiz_id),
        "source_prompt": meta.get("source_prompt"),
        "created_at": meta.get("created_at"),
    }


def list_local_quiz_summaries(out_dir: str | Path | None = None) -> list[dict]:
    """List quizzes with meta.json under the local quizzes directory."""
    base = Path(out_dir) if out_dir is not None else default_quizzes_dir()
    if not base.is_dir():
        return []

    items: list[dict] = []
    for quiz_dir in sorted(base.iterdir()):
        if not quiz_dir.is_dir():
            continue
        meta_path = quiz_dir / "meta.json"
        if not meta_path.is_file():
            continue
        meta = load_meta_from_path(meta_path)
        items.append(quiz_summary_from_meta(meta, quiz_dir.name))
    return items


def list_quiz_catalog(
    *,
    gcs_store: GcsQuizStore | None,
    out_dir: str | Path | None = None,
) -> list[dict]:
    """Merge local and GCS quiz metadata; GCS wins on duplicate quiz_id."""
    by_id: dict[str, dict] = {}
    for item in list_local_quiz_summaries(out_dir):
        by_id[item["quiz_id"]] = item
    if gcs_store is not None:
        for item in gcs_store.list_quiz_summaries():
            by_id[item["quiz_id"]] = item

    results = list(by_id.values())
    results.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return results


def default_cache_dir() -> Path:
    raw = os.getenv("QUIZZES_CACHE_DIR", "").strip()
    return Path(raw) if raw else DEFAULT_CACHE_DIR


class GcsQuizStore:
    """Upload and download quiz artifacts under gs://{bucket}/{prefix}/{quiz_id}/."""

    def __init__(self, *, bucket_name: str, prefix: str = DEFAULT_GCS_PREFIX) -> None:
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")

    @classmethod
    def from_env(cls) -> GcsQuizStore | None:
        bucket = os.getenv("GCS_QUIZZES_BUCKET", "").strip()
        if not bucket:
            return None
        prefix = os.getenv("GCS_QUIZZES_PREFIX", DEFAULT_GCS_PREFIX).strip() or DEFAULT_GCS_PREFIX
        return cls(bucket_name=bucket, prefix=prefix)

    def _object_prefix(self, quiz_id: str) -> str:
        return f"{self.prefix}/{quiz_id}"

    def _meta_blob_name(self, quiz_id: str) -> str:
        return f"{self._object_prefix(quiz_id)}/meta.json"

    def _client(self):
        from google.cloud import storage

        return storage.Client()

    def _bucket(self):
        return self._client().bucket(self.bucket_name)

    def exists(self, quiz_id: str) -> bool:
        return self._bucket().blob(self._meta_blob_name(quiz_id)).exists()

    def load_meta(self, quiz_id: str) -> dict | None:
        blob = self._bucket().blob(self._meta_blob_name(quiz_id))
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text(encoding="utf-8"))

    def list_quiz_summaries(self) -> list[dict]:
        """List quiz_id, title, and source_prompt for every meta.json in the bucket."""
        prefix = f"{self.prefix}/"
        items: list[dict] = []
        for blob in self._bucket().list_blobs(prefix=prefix):
            if not blob.name.endswith("/meta.json"):
                continue
            relative = blob.name[len(prefix) :]
            quiz_id = relative[: -len("/meta.json")]
            if not quiz_id or "/" in quiz_id:
                continue
            meta = json.loads(blob.download_as_text(encoding="utf-8"))
            items.append(quiz_summary_from_meta(meta, quiz_id))
        return items

    def upload_quiz_dir(self, quiz_dir: Path) -> None:
        quiz_id = quiz_dir.name
        object_prefix = self._object_prefix(quiz_id)
        bucket = self._bucket()
        for path in quiz_dir.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(quiz_dir).as_posix()
            blob_name = f"{object_prefix}/{relative}"
            bucket.blob(blob_name).upload_from_filename(str(path))

    def download_quiz(self, quiz_id: str, dest_dir: Path) -> Path:
        """Download all objects for quiz_id into dest_dir; return quiz directory."""
        quiz_dir = dest_dir / quiz_id
        quiz_dir.mkdir(parents=True, exist_ok=True)
        object_prefix = f"{self._object_prefix(quiz_id)}/"
        bucket = self._bucket()
        blobs = list(bucket.list_blobs(prefix=object_prefix))
        if not blobs:
            raise FileNotFoundError(f"quiz {quiz_id!r} not found in GCS bucket {self.bucket_name!r}")

        for blob in blobs:
            if blob.name.endswith("/"):
                continue
            relative = blob.name[len(object_prefix) :]
            if not relative:
                continue
            local_path = quiz_dir / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_path))

        if not (quiz_dir / "meta.json").is_file():
            raise FileNotFoundError(
                f"quiz {quiz_id!r} in GCS is missing meta.json under {object_prefix}"
            )
        return quiz_dir
