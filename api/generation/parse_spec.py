"""Stage 1: parse natural language into franchise context."""

from __future__ import annotations

from api.generation.json_utils import parse_json_object
from api.generation.models import FranchiseContext
from api.generation.resolve_wiki import is_fandom_wiki_url
from api.llm.client import LLMClient

_STAGE1_PROMPT = """You are a franchise quiz designer. The user wants a personality quiz based on a fictional class system.

User request:
{prompt}

Respond with JSON only (no markdown fences):
{{
  "franchise_name": "string — the franchise or universe name",
  "classes": ["class A", "class B", "..."],
  "wiki_base_url": "https://subdomain.fandom.com/wiki/"
}}

Rules:
- Identify a real fictional franchise with a recognizable class/faction/house/type system.
- Include every major class from that system (e.g. all 4 Hogwarts houses, all Divergent factions).
- There must be at least 2 classes.
- wiki_base_url MUST be a Fandom wiki base URL ending in /wiki/ (e.g. https://harrypotter.fandom.com/wiki/).
- If the request is not a fictional class-system quiz, set "error" to a short explanation instead of inventing classes.
"""


def _validate_stage1_payload(data: dict) -> FranchiseContext:
    if data.get("error"):
        raise ValueError(str(data["error"]))

    franchise_name = str(data.get("franchise_name", "")).strip()
    if not franchise_name:
        raise ValueError("franchise_name is required")

    classes = data.get("classes")
    if not isinstance(classes, list) or len(classes) < 2:
        raise ValueError("classes must be a list with at least 2 entries")

    normalized_classes = [str(item).strip() for item in classes if str(item).strip()]
    if len(normalized_classes) < 2:
        raise ValueError("classes must contain at least 2 non-empty names")

    wiki_base_url = data.get("wiki_base_url")
    if wiki_base_url is not None:
        wiki_base_url = str(wiki_base_url).strip() or None
    if wiki_base_url:
        wiki_base_url = wiki_base_url.rstrip("/") + "/"
        if not wiki_base_url.endswith("wiki/"):
            raise ValueError("wiki_base_url must end with /wiki/")
        if not is_fandom_wiki_url(wiki_base_url + "Example"):
            raise ValueError("wiki_base_url must be a Fandom wiki base URL")

    return FranchiseContext(
        franchise_name=franchise_name,
        classes=normalized_classes,
        wiki_base_url=wiki_base_url,
    )


def parse_franchise_context(
    prompt: str,
    llm: LLMClient,
    *,
    retries: int = 1,
) -> FranchiseContext:
    """Stage 1: extract franchise name, classes, and Fandom wiki base from a prompt."""
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("prompt must be non-empty")

    attempts = max(retries, 0) + 1
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            raw = llm.generate_text(
                _STAGE1_PROMPT.format(prompt=prompt),
                retry_on_rate_limit=False,
            )
            return _validate_stage1_payload(parse_json_object(raw))
        except Exception as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
    raise ValueError(f"failed to parse franchise context: {last_error}") from last_error
