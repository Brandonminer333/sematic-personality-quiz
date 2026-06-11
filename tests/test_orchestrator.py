"""Integration tests for api/generation/orchestrator.py — stages 3–5."""

import json
from pathlib import Path

import numpy as np
import pytest

from api.classifier import classify, load_reference_data
from api.generation.models import FranchiseSpec
from api.generation.orchestrator import generate_quiz

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_generate_quiz_writes_classifiable_reference(tmp_path, monkeypatch):
    spec = FranchiseSpec.from_path(FIXTURES / "hogwarts_spec.json")
    answers = ["strongly agree"] * 15

    monkeypatch.setattr(
        "api.generation.orchestrator.roleplay_character",
        lambda character, **kwargs: type(
            "Result",
            (),
            {
                "character": character,
                "answers": answers,
                "source_url": f"https://harrypotter.fandom.com/wiki/{character.replace(' ', '_')}",
                "raw_response": json.dumps({"answers": answers}),
            },
        )(),
    )

    artifact, skipped = generate_quiz(
        spec,
        quiz_id="test-quiz",
        out_dir=tmp_path,
        llm=object(),
        save_raw=True,
    )

    assert skipped == []
    assert artifact.reference_csv.exists()

    ref = load_reference_data(artifact.reference_csv)
    assert set(ref.types.tolist()) == {"Gryffindor", "Slytherin"}

    top, ranking = classify(np.ones(15), ref)
    assert top in {"Gryffindor", "Slytherin"}
    assert ranking

    meta = json.loads(artifact.meta_json.read_text(encoding="utf-8"))
    assert meta["title"] == "Harry Potter"
    assert meta["row_count"] == 2
