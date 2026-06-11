"""Stage 2: discover characters and assign them to franchise classes."""

from __future__ import annotations

from api.generation.json_utils import parse_json_object
from api.generation.models import CharacterRef, FranchiseContext, FranchiseSpec
from api.generation.parse_spec import parse_franchise_context
from api.llm.client import LLMClient

DEFAULT_PER_CLASS = 4
MAX_CHARACTERS = 16

_STAGE2_PROMPT = """You are a franchise lore expert building a cast list for a personality quiz.

Franchise: {franchise_name}
Classes: {classes}
Wiki: {wiki_base_url}
Original user request: {source_prompt}

Respond with JSON only (no markdown fences):
{{
  "characters": [
    {{"name": "Full Character Name", "class": "ExactClassName"}},
    ...
  ]
}}

Rules:
- Pick canon characters who belong to each class (not fan theories).
- Provide up to {per_class} characters per class.
- Every "class" value must exactly match one of: {classes}
- Use full character names (e.g. "Hermione Granger", not "Hermione").
- No duplicate characters.
- Prefer well-known characters with rich wiki pages.
"""


def _validate_roster(
    data: dict,
    *,
    classes: list[str],
    per_class: int,
    max_characters: int,
) -> list[CharacterRef]:
    raw_characters = data.get("characters")
    if not isinstance(raw_characters, list) or not raw_characters:
        raise ValueError("characters must be a non-empty list")

    class_set = set(classes)
    roster: list[CharacterRef] = []
    seen_names: set[str] = set()

    for item in raw_characters:
        if not isinstance(item, dict):
            raise ValueError("each character entry must be an object")
        name = str(item.get("name", "")).strip()
        character_class = str(item.get("class", "")).strip()
        if not name or not character_class:
            raise ValueError("each character requires name and class")
        if character_class not in class_set:
            raise ValueError(f"unknown class {character_class!r} for {name!r}")
        key = name.lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        roster.append(CharacterRef(name=name, character_class=character_class))
        if len(roster) >= max_characters:
            break

    if not roster:
        raise ValueError("roster is empty after validation")

    present_classes = {character.character_class for character in roster}
    missing = sorted(class_set - present_classes)
    if missing:
        raise ValueError(f"missing characters for classes: {', '.join(missing)}")

    counts: dict[str, int] = {cls: 0 for cls in classes}
    for character in roster:
        counts[character.character_class] += 1
        if counts[character.character_class] > per_class:
            raise ValueError(
                f"too many characters for class {character.character_class!r} "
                f"(max {per_class})"
            )

    return roster


def discover_roster(
    context: FranchiseContext,
    source_prompt: str,
    llm: LLMClient,
    *,
    per_class: int = DEFAULT_PER_CLASS,
    max_characters: int = MAX_CHARACTERS,
    retries: int = 1,
) -> list[CharacterRef]:
    """Stage 2: propose canon characters for each class."""
    attempts = max(retries, 0) + 1
    last_error: Exception | None = None
    prompt = _STAGE2_PROMPT.format(
        franchise_name=context.franchise_name,
        classes=", ".join(context.classes),
        wiki_base_url=context.wiki_base_url or "unknown",
        source_prompt=source_prompt.strip(),
        per_class=per_class,
    )

    for attempt in range(attempts):
        try:
            raw = llm.generate_text(prompt, retry_on_rate_limit=False)
            return _validate_roster(
                parse_json_object(raw),
                classes=context.classes,
                per_class=per_class,
                max_characters=max_characters,
            )
        except Exception as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
    raise ValueError(f"failed to discover roster: {last_error}") from last_error


def build_franchise_spec_from_prompt(
    prompt: str,
    llm: LLMClient,
    *,
    per_class: int = DEFAULT_PER_CLASS,
    max_characters: int = MAX_CHARACTERS,
) -> FranchiseSpec:
    """Run stages 1 and 2, returning a complete FranchiseSpec."""
    context = parse_franchise_context(prompt, llm)
    characters = discover_roster(
        context,
        prompt,
        llm,
        per_class=per_class,
        max_characters=max_characters,
    )
    return FranchiseSpec(
        franchise_name=context.franchise_name,
        classes=context.classes,
        characters=characters,
        wiki_base_url=context.wiki_base_url,
        source_prompt=prompt.strip(),
    )
