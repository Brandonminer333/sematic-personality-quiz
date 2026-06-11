"""Parse MediaWiki / Fandom pages into structured character context."""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

_DEFAULT_HEADERS = {
    "User-Agent": "SemanticPersonalityQuiz/1.0 (wiki-scraper; contact@example.com)",
}


def _clean_text(text: str) -> str:
    """Remove wiki citations and strip whitespace."""
    text = re.sub(r"\[.*?\]", "", text)
    return text.strip()


def _get_all_section_contents(
    soup: BeautifulSoup,
    section_name: str,
    *,
    max_paragraphs: int = 2,
) -> list[str]:
    """Find sections matching `section_name`, truncating episodic plot bloat."""
    headlines = [
        h
        for h in soup.find_all(["h2", "h3", "h4"])
        if section_name.lower() in h.get_text().lower()
    ]

    all_sections: list[str] = []

    for header_tag in headlines:
        content: list[str] = []
        p_count = 0

        for sibling in header_tag.find_next_siblings():
            if sibling.name in ["h2", "h3", "h4"]:
                break

            if sibling.name in ["p", "ul", "ol"]:
                text = _clean_text(sibling.get_text(separator=" "))

                if not text or len(text) < 15:
                    continue

                content.append(text)
                p_count += 1

                if p_count >= max_paragraphs:
                    break

        if content:
            all_sections.append("\n".join(content).strip())

    return all_sections


def scrape_wiki_entity(url: str, *, session: requests.Session | None = None) -> dict:
    """Fetch a wiki page and extract summary plus key sections."""
    http = session or requests
    response = http.get(url, headers=_DEFAULT_HEADERS, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    first_p = None
    for p in soup.select(".mw-parser-output > p"):
        if p.get_text(strip=True):
            first_p = _clean_text(p.get_text(separator=" "))
            break

    appearances = _get_all_section_contents(soup, "Appearance", max_paragraphs=2)
    histories = _get_all_section_contents(soup, "History", max_paragraphs=2)
    quotes = _get_all_section_contents(soup, "Quotes", max_paragraphs=3)

    return {
        "url": url,
        "summary": first_p or "Summary not found.",
        "appearances": appearances,
        "histories": histories,
        "quotes": quotes,
    }


def format_list(lst: list[str]) -> str:
    return "\n\n".join(lst) if lst else "None"
