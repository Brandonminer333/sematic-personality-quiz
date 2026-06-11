"""Test-only hooks for E2E runs without a live LLM (FAKE_QUIZ_SPEC=1)."""

from __future__ import annotations

from api.generation.models import CharacterRef, FranchiseSpec, ReferenceRow
from api.generation.persist import write_quiz_artifact


def fake_spec_builder(prompt: str, _llm) -> FranchiseSpec:
    return FranchiseSpec(
        franchise_name="Harry Potter",
        classes=["Gryffindor", "Slytherin"],
        characters=[
            CharacterRef("Harry Potter", "Gryffindor"),
            CharacterRef("Draco Malfoy", "Slytherin"),
        ],
        wiki_base_url="https://harrypotter.fandom.com/wiki/",
        source_prompt=prompt,
    )


def instant_generation_runner(quiz_id, spec, *, store, out_dir=None, llm=None, gcs_store=None):
    rows = [
        ReferenceRow("Harry Potter", "Gryffindor", ["strongly agree"] * 15),
        ReferenceRow("Draco Malfoy", "Slytherin", ["somewhat disagree"] * 15),
    ]
    artifact = write_quiz_artifact(
        quiz_id=quiz_id,
        spec=spec,
        rows=rows,
        out_dir=out_dir,
    )
    store.mark_ready(quiz_id, reference_csv=artifact.reference_csv)
