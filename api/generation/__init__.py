"""Quiz generation pipeline: wiki resolution, scraping, and reference synthesis."""

from .discover_roster import (
    DEFAULT_PER_CLASS,
    MAX_CHARACTERS,
    build_franchise_spec_from_prompt,
    discover_roster,
)
from .models import (
    CharacterRef,
    FranchiseContext,
    FranchiseSpec,
    QuizArtifact,
    ReferenceRow,
)
from .orchestrator import generate_quiz
from .parse_answers import parse_likert_answers
from .parse_spec import parse_franchise_context
from .persist import default_quizzes_dir, write_quiz_artifact
from .questions import load_quiz_questions
from .quiz_jobs import QuizJob, QuizJobStore, get_default_job_store, start_generation_in_background
from .resolve_wiki import (
    WikiResolutionError,
    build_fandom_wiki_url,
    is_fandom_wiki_url,
    resolve_wiki_url,
)
from .roleplay import (
    RoleplayResult,
    attach_context_to_prompt,
    build_roleplay_prompt,
    fetch_wiki_context,
    format_wiki_context_block,
    roleplay_answers,
    roleplay_character,
)
from .scrape_wiki import format_list, scrape_wiki_entity
from .validate import validate_reference_rows

__all__ = [
    "CharacterRef",
    "DEFAULT_PER_CLASS",
    "FranchiseContext",
    "FranchiseSpec",
    "MAX_CHARACTERS",
    "QuizArtifact",
    "QuizJob",
    "QuizJobStore",
    "ReferenceRow",
    "RoleplayResult",
    "WikiResolutionError",
    "attach_context_to_prompt",
    "build_fandom_wiki_url",
    "build_franchise_spec_from_prompt",
    "build_roleplay_prompt",
    "default_quizzes_dir",
    "discover_roster",
    "fetch_wiki_context",
    "format_list",
    "format_wiki_context_block",
    "generate_quiz",
    "get_default_job_store",
    "is_fandom_wiki_url",
    "load_quiz_questions",
    "parse_franchise_context",
    "parse_likert_answers",
    "resolve_wiki_url",
    "roleplay_answers",
    "roleplay_character",
    "scrape_wiki_entity",
    "start_generation_in_background",
    "validate_reference_rows",
    "write_quiz_artifact",
]
