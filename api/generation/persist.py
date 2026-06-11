"""Write generated quiz artifacts to disk."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from api.classifier import QUESTION_COLUMNS
from api.generation.models import FranchiseSpec, QuizArtifact, ReferenceRow


def default_quizzes_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "quizzes"


def write_quiz_artifact(
    *,
    quiz_id: str,
    spec: FranchiseSpec,
    rows: list[ReferenceRow],
    out_dir: str | Path | None = None,
    raw_responses: dict[str, str] | None = None,
    source_urls: dict[str, str | None] | None = None,
) -> QuizArtifact:
    """Persist reference.csv, meta.json, and optional raw LLM traces."""
    base_dir = Path(out_dir) if out_dir is not None else default_quizzes_dir()
    quiz_dir = base_dir / quiz_id
    quiz_dir.mkdir(parents=True, exist_ok=True)

    reference_csv = quiz_dir / "reference.csv"
    fieldnames = ["Leader", "Type", *QUESTION_COLUMNS]
    with reference_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_dict())

    urls = source_urls or {}
    meta = {
        "quiz_id": quiz_id,
        "title": spec.franchise_name,
        "franchise_name": spec.franchise_name,
        "wiki_base_url": spec.wiki_base_url,
        "classes": list(spec.classes),
        "characters": [
            {
                "name": row.leader,
                "class": row.type,
                "source_url": urls.get(row.leader),
            }
            for row in rows
        ],
        "reference_csv": "reference.csv",
        "row_count": len(rows),
        "source_prompt": spec.source_prompt,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_json = quiz_dir / "meta.json"
    meta_json.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    if raw_responses:
        raw_dir = quiz_dir / "raw"
        raw_dir.mkdir(exist_ok=True)
        for character, response in raw_responses.items():
            safe_name = character.replace("/", "_")
            (raw_dir / f"{safe_name}.txt").write_text(response, encoding="utf-8")

    return QuizArtifact(
        quiz_id=quiz_id,
        spec=spec,
        rows=list(rows),
        quiz_dir=quiz_dir,
    )
