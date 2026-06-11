"""Unit tests for api/generation/scrape_wiki.py — wiki page parsing.

Covers citation cleaning, section extraction/truncation, list formatting, and
the full parse against fixture HTML (network mocked).
"""

import pytest
from bs4 import BeautifulSoup

from api.generation import scrape_wiki as mod
from api.generation.scrape_wiki import (
    _clean_text,
    _get_all_section_contents,
    format_list,
    scrape_wiki_entity,
)

pytestmark = pytest.mark.unit


def test_clean_text_removes_citations_and_strips():
    assert _clean_text("  Erika[1] is a Gym Leader.  ") == "Erika is a Gym Leader."
    assert _clean_text("[12][13]Hello[2]") == "Hello"


def test_get_all_section_contents_extracts_multiple_sections_and_truncates():
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

    appearances = _get_all_section_contents(soup, "Appearance", max_paragraphs=2)
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


def test_scrape_wiki_entity_parses_html_without_network(monkeypatch):
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

    def fake_get(url, headers, timeout):
        return FakeResp()

    monkeypatch.setattr(mod.requests, "get", fake_get)

    out = scrape_wiki_entity("https://harrypotter.fandom.com/wiki/Hermione_Granger")
    assert out["url"] == "https://harrypotter.fandom.com/wiki/Hermione_Granger"
    assert out["summary"] == "Lead paragraph with citation."
    assert out["appearances"]
    assert out["histories"]
    assert out["quotes"]
