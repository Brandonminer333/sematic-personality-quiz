import pytest
from bs4 import BeautifulSoup

from data_sythesizer.call_available_llm import LLMCandidate, call_prompt_with_first_available_model
from data_sythesizer.mini_rag import scrape_wiki_entity


class _FakeOpenAIResponse:
    class _Choice:
        class _Message:
            def __init__(self, content: str):
                self.content = content

        def __init__(self, content: str):
            self.message = self._Message(content)

    def __init__(self, content: str):
        self.choices = [self._Choice(content)]


def test_call_prompt_with_first_available_model_openai_compatible(monkeypatch):
    from data_sythesizer import call_available_llm as mod

    class FakeOpenAI:
        def __init__(self, *, base_url: str, api_key: str):
            self.base_url = base_url
            self.api_key = api_key

            class _Completions:
                @staticmethod
                def create(**kwargs):
                    return _FakeOpenAIResponse(" hello ")

            class _Chat:
                completions = _Completions()

            self.chat = _Chat()

    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI)

    out = call_prompt_with_first_available_model(
        "Prompt",
        candidates=[LLMCandidate(
            api_key="k", base_url="https://x", model="m", model_label="lbl")],
    )
    assert out["content"] == "hello"
    assert out["provider_kind"] == "openai_compatible"
    assert out["model_label"] == "lbl"


def test_call_prompt_with_first_available_model_falls_through_on_quota_error(monkeypatch):
    from data_sythesizer import call_available_llm as mod

    class FakeOpenAI:
        def __init__(self, *, base_url: str, api_key: str):
            self.base_url = base_url

            class _Completions:
                def create(_self, **kwargs):
                    if base_url == "https://bad":
                        raise RuntimeError("Error code: 429")
                    return _FakeOpenAIResponse("ok")

            class _Chat:
                completions = _Completions()

            self.chat = _Chat()

    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI)

    out = call_prompt_with_first_available_model(
        "Prompt",
        candidates=[
            LLMCandidate(api_key="k1", base_url="https://bad", model="m1"),
            LLMCandidate(api_key="k2", base_url="https://good", model="m2"),
        ],
    )
    assert out["content"] == "ok"
    assert out["base_url"] == "https://good"


def test_call_prompt_with_first_available_model_cloudflare_workers_ai(monkeypatch):
    from data_sythesizer import call_available_llm as mod

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"result": {"response": "cf ok"}}

    def fake_post(url, headers, json, timeout):
        assert "Authorization" in headers
        return FakeResp()

    monkeypatch.setattr(mod.requests, "post", fake_post)

    out = call_prompt_with_first_available_model(
        "Prompt",
        candidates=[
            LLMCandidate(
                api_key="k",
                base_url="https://api.cloudflare.com/ai/run",
                model="m",
                provider_kind="cloudflare_workers_ai",
                model_label="cloudflare",
            )
        ],
    )
    assert out["content"] == "cf ok"
    assert out["provider_kind"] == "cloudflare_workers_ai"


def test_scrape_wiki_entity_parses_html_without_network(monkeypatch):
    from data_sythesizer import mini_rag as mod

    html = """
    <div class="mw-parser-output">
      <p>Lead paragraph with citation.[1]</p>
      <h2><span>Appearance</span></h2>
      <p>Appearance paragraph 1.</p>
      <p>Appearance paragraph 2.</p>
      <h2><span>History</span></h2>
      <p>History paragraph 1.</p>
      <h2><span>Quotes</span></h2>
      <ul><li>Quote bullet that is long enough to include.</li></ul>
    </div>
    """

    class FakeResp:
        content = html.encode("utf-8")

        def raise_for_status(self):
            return None

    def fake_get(url, headers):
        return FakeResp()

    monkeypatch.setattr(mod.requests, "get", fake_get)

    out = scrape_wiki_entity("https://example.com/wiki/Erika")
    assert out["url"] == "https://example.com/wiki/Erika"
    assert out["summary"] == "Lead paragraph with citation."
    assert out["appearances"]
    assert out["histories"]
    assert out["quotes"]
