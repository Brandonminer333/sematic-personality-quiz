"""Resolve Fandom wiki URLs for franchise characters."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

_FANDOM_HOST_SUFFIX = ".fandom.com"
_WIKI_PATH_MARKER = "/wiki/"
_DISALLOWED_PATH_FRAGMENTS = (
    "/wiki/Special:",
    "/wiki/Category:",
    "/wiki/File:",
    "/wiki/Template:",
    "(disambiguation)",
    "(episode)",
    "(film)",
    "(book)",
)
_DEFAULT_HEADERS = {
    "User-Agent": "SemanticPersonalityQuiz/1.0 (wiki-resolver; contact@example.com)",
}
_DDG_HTML_SEARCH = "https://html.duckduckgo.com/html/"


class WikiResolutionError(Exception):
    """Raised when no suitable Fandom wiki URL can be resolved."""


def is_fandom_wiki_url(url: str) -> bool:
    """Return True when `url` points at a Fandom wiki article."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    return host.endswith(_FANDOM_HOST_SUFFIX) and _WIKI_PATH_MARKER in path


def character_to_wiki_slug(character: str) -> str:
    """Convert a display name to a MediaWiki page slug."""
    slug = _ascii_fold(character.strip()).replace(" ", "_")
    return re.sub(r"_+", "_", slug)


def build_fandom_wiki_url(wiki_base_url: str, character: str) -> str:
    """Join a Fandom wiki base URL with a character page slug."""
    base = wiki_base_url.strip()
    if not base.endswith("/"):
        base += "/"

    if not base.endswith(_WIKI_PATH_MARKER):
        if base.endswith("/wiki"):
            base += "/"
        else:
            base = urljoin(base, "wiki/")

    slug = character_to_wiki_slug(character)
    return urljoin(base, slug)


def _normalize_host(host: str) -> str:
    return host.lower().removeprefix("www.")


def _ascii_fold(text: str) -> str:
    """Strip accents so é → e, ñ → n, etc."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _franchise_slug(franchise_name: str) -> str:
    folded = _ascii_fold(franchise_name.lower())
    return re.sub(r"[^a-z0-9]+", "", folded)


def _extract_target_url(href: str) -> str | None:
    if not href:
        return None

    if href.startswith("//"):
        href = f"https:{href}"

    parsed = urlparse(href)
    if "uddg" in parse_qs(parsed.query):
        return unquote(parse_qs(parsed.query)["uddg"][0])

    if parsed.scheme in {"http", "https"}:
        return href

    return None


def _is_disallowed_wiki_path(path: str) -> bool:
    lowered = path.lower()
    return any(fragment.lower() in lowered for fragment in _DISALLOWED_PATH_FRAGMENTS)


def _score_fandom_candidate(
    url: str,
    *,
    franchise_name: str,
    character: str,
) -> int:
    parsed = urlparse(url)
    path = parsed.path or ""
    host = _normalize_host(parsed.hostname or "")
    slug = character_to_wiki_slug(character).lower()
    franchise_slug = _franchise_slug(franchise_name)

    if not is_fandom_wiki_url(url) or _is_disallowed_wiki_path(path):
        return -1

    score = 0
    article_slug = path.split("/wiki/", 1)[-1].split("?")[0].lower()

    if slug and (article_slug == slug or slug in article_slug):
        score += 20
    elif slug and article_slug.startswith(slug[: max(3, len(slug) // 2)]):
        score += 8

    if franchise_slug and franchise_slug in host:
        score += 10

    return score


def _page_exists(url: str, *, session: requests.Session) -> bool:
    response = session.get(url, headers=_DEFAULT_HEADERS, timeout=20, allow_redirects=True)
    if response.status_code == 404:
        return False
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    if soup.select_one(".noarticletext"):
        return False

    title = (soup.find("title").get_text(strip=True) if soup.find("title") else "").lower()
    if "may refer to" in title or "disambiguation" in title:
        return False

    return True


def _search_fandom_wiki_url(
    franchise_name: str,
    character: str,
    *,
    session: requests.Session,
) -> str | None:
    query = f"{franchise_name} wiki {character} site:fandom.com"
    response = session.post(
        _DDG_HTML_SEARCH,
        data={"q": query},
        headers=_DEFAULT_HEADERS,
        timeout=20,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    candidates: list[tuple[int, str]] = []

    for anchor in soup.select("a.result__a"):
        target = _extract_target_url(anchor.get("href", ""))
        if not target:
            continue

        score = _score_fandom_candidate(
            target,
            franchise_name=franchise_name,
            character=character,
        )
        if score >= 0:
            candidates.append((score, target))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def resolve_wiki_url(
    franchise_name: str,
    character: str,
    *,
    wiki_base_url: str | None = None,
    session: requests.Session | None = None,
) -> str:
    """Resolve a Fandom wiki article URL for `character`.

    Resolution order:
    1. Construct from `wiki_base_url` when it is a Fandom wiki base and the page exists.
    2. DuckDuckGo HTML search, keeping only `*.fandom.com/wiki/` results.
    """
    if not franchise_name.strip():
        raise WikiResolutionError("franchise_name must be non-empty")
    if not character.strip():
        raise WikiResolutionError("character must be non-empty")

    http = session or requests.Session()

    if wiki_base_url:
        parsed_base = urlparse(wiki_base_url)
        host = _normalize_host(parsed_base.hostname or "")
        if not host.endswith(_FANDOM_HOST_SUFFIX):
            raise WikiResolutionError(
                f"wiki_base_url must be a Fandom wiki, got host '{parsed_base.hostname}'"
            )

        constructed = build_fandom_wiki_url(wiki_base_url, character)
        if _page_exists(constructed, session=http):
            return constructed

    discovered = _search_fandom_wiki_url(franchise_name, character, session=http)
    if discovered and is_fandom_wiki_url(discovered):
        return discovered

    raise WikiResolutionError(
        f"Could not resolve a Fandom wiki URL for '{character}' in '{franchise_name}'"
    )
