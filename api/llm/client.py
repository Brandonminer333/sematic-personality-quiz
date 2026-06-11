import re
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

_MAX_RETRIES = 3
_DEFAULT_RETRY_SECONDS = 35.0


class GeminiRateLimitError(Exception):
    """Raised when Gemini returns 429 and caller opted out of blocking retries."""


def _retry_delay_seconds(exc: Exception) -> float:
    match = re.search(r"retry in ([0-9.]+)s", str(exc), re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0
    return _DEFAULT_RETRY_SECONDS


def _is_rate_limited(exc: Exception) -> bool:
    message = str(exc)
    return "429" in message or "RESOURCE_EXHAUSTED" in message


class LLMClient:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = genai.Client()
        return self._client

    def generate_text(self, prompt: str, *, retry_on_rate_limit: bool = True) -> str:
        last_exc: Exception | None = None
        max_retries = _MAX_RETRIES if retry_on_rate_limit else 0
        for attempt in range(max_retries + 1):
            try:
                return self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                ).text
            except Exception as exc:
                last_exc = exc
                if _is_rate_limited(exc):
                    if not retry_on_rate_limit:
                        raise GeminiRateLimitError(str(exc)) from exc
                    if attempt < max_retries:
                        time.sleep(_retry_delay_seconds(exc))
                        continue
                raise
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("generate_text failed without an exception")
