"""Data models for the quiz generation pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from api.classifier import QUESTION_COLUMNS


@dataclass(frozen=True)
class FranchiseContext:
    """Stage 1 output: franchise metadata without a character roster."""

    franchise_name: str
    classes: list[str]
    wiki_base_url: str | None = None


@dataclass(frozen=True)
class CharacterRef:
    """A franchise character assigned to a class."""

    name: str
    character_class: str


@dataclass(frozen=True)
class FranchiseSpec:
    """Input describing a franchise quiz to generate."""

    franchise_name: str
    classes: list[str]
    characters: list[CharacterRef]
    wiki_base_url: str | None = None
    source_prompt: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> FranchiseSpec:
        franchise_name = str(data.get("franchise_name", "")).strip()
        if not franchise_name:
            raise ValueError("franchise_name is required")

        classes = data.get("classes")
        if not isinstance(classes, list) or len(classes) < 2:
            raise ValueError("classes must be a list with at least 2 entries")

        raw_characters = data.get("characters")
        if not isinstance(raw_characters, list) or not raw_characters:
            raise ValueError("characters must be a non-empty list")

        characters: list[CharacterRef] = []
        for item in raw_characters:
            if not isinstance(item, dict):
                raise ValueError("each character entry must be an object")
            name = str(item.get("name", "")).strip()
            character_class = str(
                item.get("class") or item.get("character_class") or ""
            ).strip()
            if not name or not character_class:
                raise ValueError("each character requires name and class")
            characters.append(CharacterRef(name=name, character_class=character_class))

        wiki_base_url = data.get("wiki_base_url")
        if wiki_base_url is not None:
            wiki_base_url = str(wiki_base_url).strip() or None

        source_prompt = data.get("source_prompt")
        if source_prompt is not None:
            source_prompt = str(source_prompt).strip() or None

        return cls(
            franchise_name=franchise_name,
            classes=[str(c).strip() for c in classes if str(c).strip()],
            characters=characters,
            wiki_base_url=wiki_base_url,
            source_prompt=source_prompt,
        )

    @classmethod
    def from_json(cls, text: str) -> FranchiseSpec:
        return cls.from_dict(json.loads(text))

    @classmethod
    def from_path(cls, path: str | Path) -> FranchiseSpec:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ReferenceRow:
    """One character row in the classifier reference CSV."""

    leader: str
    type: str
    answers: list[str]

    def to_csv_dict(self) -> dict[str, str]:
        if len(self.answers) != len(QUESTION_COLUMNS):
            raise ValueError(
                f"expected {len(QUESTION_COLUMNS)} answers, got {len(self.answers)}"
            )
        return {
            "Leader": self.leader,
            "Type": self.type,
            **dict(zip(QUESTION_COLUMNS, self.answers)),
        }


@dataclass(frozen=True)
class QuizArtifact:
    """Generated quiz written to api/data/quizzes/{quiz_id}/."""

    quiz_id: str
    spec: FranchiseSpec
    rows: list[ReferenceRow]
    quiz_dir: Path

    @property
    def reference_csv(self) -> Path:
        return self.quiz_dir / "reference.csv"

    @property
    def meta_json(self) -> Path:
        return self.quiz_dir / "meta.json"
