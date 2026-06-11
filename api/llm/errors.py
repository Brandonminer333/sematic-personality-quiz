"""User-facing messages and detection for transient Gemini / AI provider errors."""

from __future__ import annotations

AI_PROVIDER_OVERLOAD_MESSAGE = (
    "The AI provider is overloaded. Please try again in a few moments."
)

_TRANSIENT_MARKERS = (
    "429",
    "503",
    "UNAVAILABLE",
    "RESOURCE_EXHAUSTED",
    "high demand",
)


def is_ai_provider_overload(message: str) -> bool:
    """True when an error string looks like Gemini rate limit or capacity pressure."""
    if not message:
        return False
    upper = message.upper()
    return any(marker in message or marker in upper for marker in _TRANSIENT_MARKERS)


def user_facing_error(message: str | None, *, default: str = "Quiz generation failed.") -> str:
    """Map internal error text to a safe client message."""
    if message and is_ai_provider_overload(message):
        return AI_PROVIDER_OVERLOAD_MESSAGE
    return message or default


def http_status_for_error(message: str | None) -> int:
    """HTTP status for a failed quiz or LLM call."""
    if message and is_ai_provider_overload(message):
        return 503
    return 422
