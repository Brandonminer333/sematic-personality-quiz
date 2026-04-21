import numpy as np
import pandas as pd
import pytest
from bs4 import BeautifulSoup

from data_sythesizer.call_available_llm import _is_quota_or_rate_limit_error
from data_sythesizer.compile_options import cosine_similarity, rank_types_by_similarity
from data_sythesizer.generate_responses import (
    _build_llm_candidates_from_env,
    add_context_to_prompt,
    roleplay_responses,
)
from data_sythesizer.mini_rag import _clean_text, _get_all_section_contents, format_list


def test__is_quota_or_rate_limit_error_matches_known_tokens():
    assert _is_quota_or_rate_limit_error(Exception("Error code: 429"))
    assert _is_quota_or_rate_limit_error(Exception("Too Many Requests"))
    assert _is_quota_or_rate_limit_error(Exception("insufficient_quota"))
    assert not _is_quota_or_rate_limit_error(Exception("some unrelated error"))


def test_cosine_similarity_basic():
    v = np.array([1.0, 0.0])
    vs = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]])
    sims = cosine_similarity(v, vs)
    assert sims.shape == (3,)
    assert sims[0] == pytest.approx(1.0)
    assert sims[1] == pytest.approx(0.0)
    assert sims[2] == pytest.approx(-1.0)


def test_rank_types_by_similarity_returns_sorted_series():
    # Two types with different means; "Fire" should rank above "Water".
    df = pd.DataFrame(
        {
            "Leader": ["A", "B", "C", "D"],
            "Type": ["Fire", "Fire", "Water", "Water"],
        }
    )
    vectors = np.array(
        [
            [1.0, 1.0],  # Fire
            [1.0, 0.0],  # Fire
            [-1.0, -1.0],  # Water
            [-1.0, 0.0],  # Water
        ]
    )
    new_vector = np.array([1.0, 0.5])
    ranking = rank_types_by_similarity(new_vector, vectors, df)
    assert list(ranking.index) == ["Fire", "Water"]
    assert ranking["Fire"] > ranking["Water"]


def test__clean_text_removes_citations_and_strips():
    assert _clean_text(
        "  Erika[1] is a Gym Leader.  ") == "Erika is a Gym Leader."
    assert _clean_text("[12][13]Hello[2]") == "Hello"


def test__get_all_section_contents_extracts_multiple_sections_and_truncates():
    html = """
    <div class="mw-parser-output">
      <h2><span>Appearance</span></h2>
      <p>Erika wears a kimono and has a calm demeanor.[1]</p>
      <p>Second paragraph that should be included too.</p>
      <p>Third paragraph that should be truncated.</p>
      <h2><span>History</span></h2>
      <p>Erika runs the Celadon Gym.</p>
      <h2><span>Appearance</span></h2>
      <p>Another appearance section entry.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")

    appearances = _get_all_section_contents(
        soup, "Appearance", max_paragraphs=2)
    assert len(appearances) == 2
    assert "Erika wears a kimono" in appearances[0]
    assert "Third paragraph" not in appearances[0]
    assert "Another appearance section entry" in appearances[1]

    histories = _get_all_section_contents(soup, "History", max_paragraphs=2)
    assert len(histories) == 1
    assert "Celadon Gym" in histories[0]


def test_format_list():
    assert format_list([]) == "None"
    assert format_list(["a"]) == "a"
    assert format_list(["a", "b"]) == "a\n\nb"


def test_add_context_to_prompt_success(monkeypatch):
    from data_sythesizer import generate_responses as gr

    def fake_scrape(url: str) -> dict:
        return {
            "url": url,
            "summary": "Summary text",
            "appearances": ["A1", "A2"],
            "histories": ["H1"],
            "quotes": ["Q1"],
        }

    monkeypatch.setattr(gr, "scrape_wiki_entity", fake_scrape)

    out = add_context_to_prompt("Base prompt", "Erika")
    assert out.startswith("Base prompt")
    assert "--- CONTEXT (Bulbapedia) ---" in out
    assert "Summary text" in out
    assert "A1\n\nA2" in out
    assert out.endswith("\n")


def test_add_context_to_prompt_fallback_on_exception(monkeypatch):
    from data_sythesizer import generate_responses as gr

    def boom(url: str) -> dict:
        raise RuntimeError("offline")

    monkeypatch.setattr(gr, "scrape_wiki_entity", boom)

    out = add_context_to_prompt("Base prompt", "Erika")
    assert "--- CONTEXT ---" in out
    assert "Failed to fetch Bulbapedia context" in out
    assert "offline" in out


def test__build_llm_candidates_from_env_builds_and_skips(monkeypatch):
    # Ensure deterministic env and that "not-set-up" is skipped.
    monkeypatch.delenv("OPEN_ROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_BASE_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_MODEL", raising=False)

    monkeypatch.setenv("GROQ_API_KEY", "not-set-up")
    monkeypatch.setenv("OPEN_ROUTER_API_KEY", "ok")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/free")

    candidates = _build_llm_candidates_from_env()
    assert len(candidates) == 1
    c = candidates[0]
    assert c.model_label == "openrouter"
    assert c.provider_kind == "openai_compatible"
    assert "openrouter.ai" in c.base_url


def test_roleplay_responses_calls_llm_correct_number_of_times(monkeypatch):
    from data_sythesizer import generate_responses as gr
    from data_sythesizer.call_available_llm import LLMCandidate

    monkeypatch.setattr(gr, "add_context_to_prompt", lambda p, c: p + " + ctx")
    monkeypatch.setattr(
        gr,
        "_build_llm_candidates_from_env",
        lambda: [LLMCandidate(api_key="k", base_url="u", model="m")],
    )

    calls: list[str] = []

    def fake_call(prompt: str, *, candidates, **kwargs):
        calls.append(prompt)
        return {"content": "ok", "model": "m", "base_url": "u", "model_label": None, "provider_kind": "openai_compatible"}

    monkeypatch.setattr(
        gr, "call_prompt_with_first_available_model", fake_call)

    # retries=0 -> exactly 1
    r0 = roleplay_responses("Erika", "Prompt", retries=0)
    assert len(r0) == 1
    assert len(calls) == 1

    # retries=2 -> 3 total
    calls.clear()
    r2 = roleplay_responses("Erika", "Prompt", retries=2)
    assert len(r2) == 3
    assert len(calls) == 3

    # retries<0 -> coerced to 0
    calls.clear()
    rn = roleplay_responses("Erika", "Prompt", retries=-5)
    assert len(rn) == 1
