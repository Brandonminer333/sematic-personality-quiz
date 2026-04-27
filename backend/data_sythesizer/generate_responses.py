import os
import csv
from pathlib import Path

from dotenv import load_dotenv

from mini_rag import format_list, scrape_wiki_entity
# TODO: clean up folder structure to avoid this weird stuff, can all live in root
from call_available_llm import LLMCandidate, call_prompt_with_first_available_model

load_dotenv()  # If this fails, I don't care to catch the exception—The code will always just fail to run


def add_context_to_prompt(base_prompt, character):
    # hardcoded because just sticking to Pokemon
    base_url = "https://bulbapedia.bulbagarden.net/wiki/"
    url = base_url + character.replace(" ", "_")
    try:
        entity = scrape_wiki_entity(url)

    except Exception as e:
        # If the wiki fetch fails (offline, blocked, etc.), fall back gracefully.
        fallback_block = f"""--- CONTEXT ---
Character: {character}
Source URL (unfetched): {url}
Note: Failed to fetch Bulbapedia context ({e})
--- END CONTEXT ---"""
        return base_prompt.rstrip() + "\n\n" + fallback_block + "\n"

    context_block = f"""--- CONTEXT (Bulbapedia) ---
URL: {entity.get("url", url)}

Summary:
{entity.get("summary", "Summary not found.")}

Appearance:
{format_list(entity.get("appearances"))}

History:
{format_list(entity.get("histories"))}

Notable Quotes:
{format_list(entity.get("quotes"))}
--- END CONTEXT ---"""

    return base_prompt.rstrip() + "\n\n" + context_block + "\n"


def _build_llm_candidates_from_env() -> list[LLMCandidate]:
    """
    Ordered fallbacks. Set *_API_KEY in `.env` and optionally override *_MODEL env vars.

    Notes:
    - OpenRouter models often require a `:free` suffix for free-tier variants.
    - If a key is missing or set to "not-set-up", that candidate is skipped.
    """

    def ok(key: str | None) -> bool:
        return bool(key) and key != "not-set-up"

    candidates: list[LLMCandidate] = []

    openrouter_key = os.getenv("OPEN_ROUTER_API_KEY")
    if ok(openrouter_key):
        candidates.append(
            LLMCandidate(
                api_key=openrouter_key,  # type: ignore[arg-type]
                base_url="https://openrouter.ai/api/v1",
                # Use OpenRouter's free router by default; it picks an available free model.
                # Override with OPENROUTER_MODEL to pin a specific model.
                model=os.getenv("OPENROUTER_MODEL", "openrouter/free"),
                model_label="openrouter",
                provider_kind="openai_compatible",
            )
        )

    groq_key = os.getenv("GROQ_API_KEY")
    if ok(groq_key):
        candidates.append(
            LLMCandidate(
                api_key=groq_key,  # type: ignore[arg-type]
                base_url="https://api.groq.com/openai/v1",
                model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                model_label="groq",
                provider_kind="openai_compatible",
            )
        )

    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    if ok(hf_key):
        candidates.append(
            LLMCandidate(
                api_key=hf_key,  # type: ignore[arg-type]
                base_url="https://api-inference.huggingface.co/v1/",
                model=os.getenv("HUGGINGFACE_MODEL",
                                "mistralai/Mistral-7B-Instruct-v0.3"),
                model_label="huggingface",
                provider_kind="openai_compatible",
            )
        )

    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if ok(nvidia_key):
        candidates.append(
            LLMCandidate(
                api_key=nvidia_key,  # type: ignore[arg-type]
                base_url="https://integrate.api.nvidia.com/v1",
                model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct"),
                model_label="nvidia",
                provider_kind="openai_compatible",
            )
        )

    cloudflare_key = os.getenv("CLOUDFLARE_API_KEY")
    cloudflare_base = os.getenv("CLOUDFLARE_BASE_URL", "").strip()
    cloudflare_model = os.getenv("CLOUDFLARE_MODEL", "").strip()
    if ok(cloudflare_key) and cloudflare_base and cloudflare_model:
        candidates.append(
            LLMCandidate(
                api_key=cloudflare_key,  # type: ignore[arg-type]
                base_url=cloudflare_base,
                model=cloudflare_model,
                model_label="cloudflare",
                provider_kind="cloudflare_workers_ai",
            )
        )

    return candidates


def roleplay_responses(character, prompt, retries=0):

    prompt = add_context_to_prompt(prompt, character)
    candidates = _build_llm_candidates_from_env()
    if not candidates:
        raise RuntimeError(
            "No LLM candidates configured. Set at least one of: "
            "OPEN_ROUTER_API_KEY, GROQ_API_KEY, HUGGINGFACE_API_KEY, NVIDIA_API_KEY "
            "(and for Cloudflare: CLOUDFLARE_API_KEY + CLOUDFLARE_BASE_URL + CLOUDFLARE_MODEL)."
        )

    if retries < 0:
        print("Retries cannot be negative. Setting retries to 0.")
        retries = 0

    if retries == 0:
        responses = [call_prompt_with_first_available_model(
            prompt, candidates=candidates)]

    else:
        responses = []
        for _ in range(retries+1):
            responses.append(call_prompt_with_first_available_model(
                prompt, candidates=candidates))

    return responses


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    # Avoid pandas dependency: read a single-column CSV with header "Leader".
    with open(here / "gym_leaders.csv", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "Leader" not in reader.fieldnames:
            raise RuntimeError(
                "gym_leaders.csv must have a header column named 'Leader'")
        characters = [row["Leader"] for row in reader if row.get("Leader")]

    with open(here / "roleplay_quiz_prompt.md", "r") as f:
        base_prompt = f.read()

    with open(here / "responses.csv", "w", newline="") as f:
        writer = csv.writer(f)
        for character in characters:
            print(f"Generating response for {character}...")
            response = roleplay_responses(character, base_prompt, retries=0)
            writer.writerow([character, response])
            f.flush()  # ensure it's written to disk immediately
