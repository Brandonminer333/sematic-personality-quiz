import pytest
import requests

from api.generation.resolve_wiki import (
    WikiResolutionError,
    _ascii_fold,
    _franchise_slug,
    build_fandom_wiki_url,
    character_to_wiki_slug,
    is_fandom_wiki_url,
    resolve_wiki_url,
)

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        content: bytes = b"",
        text: str = "",
    ):
        self.status_code = status_code
        self.content = content if content else text.encode("utf-8")
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, handlers: dict):
        self._handlers = handlers
        self.calls: list[tuple[str, str]] = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        handler = self._handlers.get(("GET", url))
        if handler is None:
            handler = self._handlers.get("GET")
        if handler is None:
            raise AssertionError(f"unexpected GET: {url}")
        return handler(url, **kwargs)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url))
        handler = self._handlers.get(("POST", url))
        if handler is None:
            handler = self._handlers.get("POST")
        if handler is None:
            raise AssertionError(f"unexpected POST: {url}")
        return handler(url, **kwargs)


def test_is_fandom_wiki_url_accepts_fandom_article():
    assert is_fandom_wiki_url("https://harrypotter.fandom.com/wiki/Harry_Potter")
    assert is_fandom_wiki_url("https://pokemon.fandom.com/wiki/Erika")


def test_is_fandom_wiki_url_rejects_non_fandom():
    assert not is_fandom_wiki_url("https://bulbapedia.bulbagarden.net/wiki/Erika")
    assert not is_fandom_wiki_url("https://en.wikipedia.org/wiki/Harry_Potter")
    assert not is_fandom_wiki_url("https://harrypotter.fandom.com/")


def test_ascii_fold_strips_accents():
    assert _ascii_fold("Pokémon") == "Pokemon"
    assert _ascii_fold("éèêë") == "eeee"
    assert _ascii_fold("José") == "Jose"


def test_franchise_slug_folds_accents():
    assert _franchise_slug("Pokémon") == "pokemon"
    assert _franchise_slug("Harry Potter") == "harrypotter"


def test_character_to_wiki_slug_replaces_spaces():
    assert character_to_wiki_slug("Harry Potter") == "Harry_Potter"
    assert character_to_wiki_slug("Lt. Surge") == "Lt._Surge"
    assert character_to_wiki_slug("José") == "Jose"


def test_build_fandom_wiki_url_normalizes_base():
    assert (
        build_fandom_wiki_url(
            "https://harrypotter.fandom.com/wiki/",
            "Hermione Granger",
        )
        == "https://harrypotter.fandom.com/wiki/Hermione_Granger"
    )
    assert (
        build_fandom_wiki_url(
            "https://harrypotter.fandom.com",
            "Harry Potter",
        )
        == "https://harrypotter.fandom.com/wiki/Harry_Potter"
    )


def test_resolve_wiki_url_uses_constructed_fandom_url_when_page_exists():
    target = "https://harrypotter.fandom.com/wiki/Harry_Potter"
    html = b"<html><head><title>Harry Potter</title></head><body></body></html>"

    def get_handler(url, **kwargs):
        assert url == target
        return _FakeResponse(content=html)

    session = _FakeSession({("GET", target): get_handler})

    out = resolve_wiki_url(
        "Harry Potter",
        "Harry Potter",
        wiki_base_url="https://harrypotter.fandom.com/wiki/",
        session=session,
    )
    assert out == target
    assert session.calls == [("GET", target)]


def test_resolve_wiki_url_falls_back_to_search_when_constructed_page_missing():
    constructed = "https://harrypotter.fandom.com/wiki/Harry_Potter"
    discovered = "https://harrypotter.fandom.com/wiki/Harry_James_Potter"
    missing_html = b'<html><div class="noarticletext"></div></html>'
    search_html = """
    <html><body>
      <a class="result__a" href="https://en.wikipedia.org/wiki/Harry_Potter">Wrong wiki</a>
      <a class="result__a" href="https://harrypotter.fandom.com/wiki/Harry_James_Potter">Right wiki</a>
    </body></html>
    """

    def get_handler(url, **kwargs):
        if url == constructed:
            return _FakeResponse(content=missing_html)
        raise AssertionError(f"unexpected GET: {url}")

    def post_handler(url, **kwargs):
        assert "Harry Potter" in kwargs["data"]["q"]
        assert "site:fandom.com" in kwargs["data"]["q"]
        return _FakeResponse(text=search_html)

    session = _FakeSession(
        {
            ("GET", constructed): get_handler,
            "POST": post_handler,
        }
    )

    out = resolve_wiki_url(
        "Harry Potter",
        "Harry Potter",
        wiki_base_url="https://harrypotter.fandom.com/wiki/",
        session=session,
    )
    assert out == discovered
    assert ("GET", constructed) in session.calls
    assert ("POST", "https://html.duckduckgo.com/html/") in session.calls


def test_resolve_wiki_url_search_decodes_duckduckgo_redirect():
    search_html = """
    <html><body>
      <a class="result__a"
         href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fharrypotter.fandom.com%2Fwiki%2FHermione_Granger">
        Hermione
      </a>
    </body></html>
    """

    def post_handler(url, **kwargs):
        return _FakeResponse(text=search_html)

    session = _FakeSession({"POST": post_handler})

    out = resolve_wiki_url(
        "Harry Potter",
        "Hermione Granger",
        session=session,
    )
    assert out == "https://harrypotter.fandom.com/wiki/Hermione_Granger"


def test_resolve_wiki_url_rejects_non_fandom_base_url():
    with pytest.raises(WikiResolutionError, match="Fandom wiki"):
        resolve_wiki_url(
            "Pokemon",
            "Erika",
            wiki_base_url="https://bulbapedia.bulbagarden.net/wiki/",
        )


def test_resolve_wiki_url_raises_when_nothing_found():
    search_html = '<html><body><a class="result__a" href="https://en.wikipedia.org/wiki/Harry_Potter">Nope</a></body></html>'

    session = _FakeSession(
        {
            "POST": lambda url, **kwargs: _FakeResponse(text=search_html),
        }
    )

    with pytest.raises(WikiResolutionError, match="Could not resolve"):
        resolve_wiki_url("Harry Potter", "Harry Potter", session=session)
