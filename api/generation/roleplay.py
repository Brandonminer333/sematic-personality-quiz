"""Stage 4: roleplay a character through the personality quiz via Gemini."""

from __future__ import annotations

from dataclasses import dataclass

from api.generation.parse_answers import parse_likert_answers
from api.generation.questions import EXPECTED_QUESTION_COUNT, load_quiz_questions
from api.generation.resolve_wiki import resolve_wiki_url
from api.generation.scrape_wiki import format_list, scrape_wiki_entity
from api.llm.client import LLMClient


@dataclass(frozen=True)
class RoleplayResult:
    """One character's quiz answers plus trace metadata for debugging."""

    character: str
    answers: list[str]
    source_url: str | None
    raw_response: str


def format_wiki_context_block(
    *,
    character: str,
    entity: dict | None = None,
    source_url: str | None = None,
    source_label: str = "Wiki",
    error: str | None = None,
) -> str:
    """Render wiki scrape output (or a fallback) into a prompt context block."""
    if error is not None or entity is None:
        return f"""--- CONTEXT ---
Character: {character}
Source URL (unfetched): {source_url or "unknown"}
Note: Failed to fetch wiki context ({error or "no entity"})
--- END CONTEXT ---"""

    url = entity.get("url", source_url or "unknown")
    return f"""--- CONTEXT ({source_label}) ---
URL: {url}

Summary:
{entity.get("summary", "Summary not found.")}

Appearance:
{format_list(entity.get("appearances", []))}

History:
{format_list(entity.get("histories", []))}

Notable Quotes:
{format_list(entity.get("quotes", []))}
--- END CONTEXT ---"""


def build_roleplay_prompt(character: str) -> str:
    """Build the system/user prompt for a single character roleplay."""
    questions, likert_options = load_quiz_questions()
    options_text = ", ".join(f'"{option}"' for option in likert_options)

    numbered_questions = "\n".join(
        f"{index + 1}. {question}" for index, question in enumerate(questions)
    )

    return f"""You are {character}. Answer the following personality quiz questions as this character would, based on their personality, history, and demeanor — not on meta knowledge of franchise "types" or "houses".

Respond with JSON only (no markdown fences):
{{"answers": ["{likert_options[0]}", "..."]}}

Rules:
- Provide exactly {EXPECTED_QUESTION_COUNT} answers in order, one per question.
- Each answer must be exactly one of: {options_text}
- Stay in character throughout.

Questions:
{numbered_questions}
"""


def attach_context_to_prompt(base_prompt: str, context_block: str) -> str:
    return base_prompt.rstrip() + "\n\n" + context_block.rstrip() + "\n"


def fetch_wiki_context(
    character: str,
    *,
    franchise_name: str,
    wiki_base_url: str | None = None,
    session=None,
) -> tuple[str | None, str]:
    """Resolve a Fandom wiki URL, scrape it, and return (url, context_block)."""
    try:
        url = resolve_wiki_url(
            franchise_name,
            character,
            wiki_base_url=wiki_base_url,
            session=session,
        )
        entity = scrape_wiki_entity(url, session=session)
        block = format_wiki_context_block(
            character=character,
            entity=entity,
            source_url=url,
        )
        return url, block
    except Exception as exc:
        block = format_wiki_context_block(
            character=character,
            source_url=wiki_base_url,
            error=str(exc),
        )
        return None, block


def roleplay_answers(
    character: str,
    context_block: str,
    *,
    llm: LLMClient | None = None,
    retries: int = 1,
) -> RoleplayResult:
    """Call Gemini to answer the quiz as `character`, parsing validated Likert labels."""
    if retries < 0:
        retries = 0

    llm = llm or LLMClient()
    prompt = attach_context_to_prompt(build_roleplay_prompt(character), context_block)

    attempts = retries + 1
    last_raw = ""
    for _ in range(attempts):
        last_raw = llm.generate_text(prompt)
        answers = parse_likert_answers(last_raw)
        if answers is not None:
            return RoleplayResult(
                character=character,
                answers=answers,
                source_url=None,
                raw_response=last_raw,
            )

    raise ValueError(
        f"Could not parse {EXPECTED_QUESTION_COUNT} Likert answers for {character!r} "
        f"after {attempts} attempt(s). Last response: {last_raw[:500]!r}"
    )


def roleplay_character(
    character: str,
    *,
    franchise_name: str,
    wiki_base_url: str | None = None,
    llm: LLMClient | None = None,
    retries: int = 1,
    session=None,
) -> RoleplayResult:
    """Stage 3 + 4: fetch wiki context, then roleplay the quiz for one character."""
    source_url, context_block = fetch_wiki_context(
        character,
        franchise_name=franchise_name,
        wiki_base_url=wiki_base_url,
        session=session,
    )
    result = roleplay_answers(
        character,
        context_block,
        llm=llm,
        retries=retries,
    )
    return RoleplayResult(
        character=result.character,
        answers=result.answers,
        source_url=source_url,
        raw_response=result.raw_response,
    )
