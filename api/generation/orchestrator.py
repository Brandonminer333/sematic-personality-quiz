"""Stage 5 orchestrator: roleplay a franchise spec and persist a reference quiz."""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path

from api.generation.models import FranchiseSpec, QuizArtifact, ReferenceRow
from api.generation.persist import default_quizzes_dir, write_quiz_artifact
from api.generation.roleplay import roleplay_character
from api.generation.validate import validate_reference_rows
from api.llm.client import LLMClient


def generate_quiz(
    spec: FranchiseSpec,
    *,
    quiz_id: str | None = None,
    out_dir: str | Path | None = None,
    llm: LLMClient | None = None,
    roleplay_retries: int = 1,
    save_raw: bool = True,
) -> tuple["QuizArtifact", list[tuple[str, str]]]:
    """Run stages 3–5 for every character in `spec` and write quiz artifacts.

    Returns the persisted `QuizArtifact` and a list of skipped characters
    with their error messages.
    """
    llm = llm or LLMClient()
    quiz_id = quiz_id or uuid.uuid4().hex

    rows: list[ReferenceRow] = []
    raw_responses: dict[str, str] = {}
    source_urls: dict[str, str | None] = {}
    skipped: list[tuple[str, str]] = []

    for index, character_ref in enumerate(spec.characters, start=1):
        label = f"[{index}/{len(spec.characters)}] {character_ref.name}"
        print(f"Roleplaying {label}...")
        try:
            result = roleplay_character(
                character_ref.name,
                franchise_name=spec.franchise_name,
                wiki_base_url=spec.wiki_base_url,
                llm=llm,
                retries=roleplay_retries,
            )
        except Exception as exc:
            skipped.append((character_ref.name, str(exc)))
            print(f"  skipped: {exc}")
            continue

        rows.append(
            ReferenceRow(
                leader=result.character,
                type=character_ref.character_class,
                answers=result.answers,
            )
        )
        source_urls[result.character] = result.source_url
        if save_raw:
            raw_responses[result.character] = result.raw_response
        print(f"  done ({character_ref.character_class})")

    if not rows:
        if skipped:
            rate_limited = sum(
                1 for _, reason in skipped if "429" in reason or "RESOURCE_EXHAUSTED" in reason
            )
            if rate_limited == len(skipped):
                raise ValueError(
                    "Quiz generation failed: Gemini API rate limit exceeded for all "
                    f"{len(skipped)} characters. Wait a minute and retry, or set "
                    "FAKE_QUIZ_SPEC=1 in .env for local development without Gemini."
                )
            sample = "; ".join(f"{name}: {reason[:80]}" for name, reason in skipped[:2])
            raise ValueError(
                f"No reference rows were produced ({len(skipped)} characters skipped). "
                f"Examples: {sample}"
            )

    validate_reference_rows(rows, spec.classes)

    artifact = write_quiz_artifact(
        quiz_id=quiz_id,
        spec=spec,
        rows=rows,
        out_dir=out_dir,
        raw_responses=raw_responses if save_raw else None,
        source_urls=source_urls,
    )
    return artifact, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a classifier reference quiz from a franchise spec JSON file.",
    )
    parser.add_argument(
        "--spec",
        required=True,
        help="Path to a franchise spec JSON file (franchise_name, classes, characters).",
    )
    parser.add_argument(
        "--out-dir",
        default=str(default_quizzes_dir()),
        help="Directory where api/data/quizzes/{id}/ will be written.",
    )
    parser.add_argument(
        "--quiz-id",
        default=None,
        help="Optional quiz id (defaults to a random UUID).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Number of LLM retries per character when parsing answers fails.",
    )
    parser.add_argument(
        "--no-raw",
        action="store_true",
        help="Do not write raw LLM responses under raw/.",
    )
    args = parser.parse_args(argv)

    spec = FranchiseSpec.from_path(args.spec)
    artifact, skipped = generate_quiz(
        spec,
        quiz_id=args.quiz_id,
        out_dir=args.out_dir,
        roleplay_retries=args.retries,
        save_raw=not args.no_raw,
    )

    print(f"\nWrote quiz {artifact.quiz_id} to {artifact.quiz_dir}")
    print(f"  characters: {len(artifact.rows)}")
    print(f"  reference:  {artifact.reference_csv}")
    if skipped:
        print(f"  skipped:    {len(skipped)}")
        for name, reason in skipped:
            print(f"    - {name}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
