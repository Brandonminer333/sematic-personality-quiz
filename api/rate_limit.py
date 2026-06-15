"""Per-client daily limits for quiz creation."""

from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime, timezone

from fastapi import Request

DEFAULT_DAILY_QUIZ_LIMIT = 5

DAILY_QUIZ_LIMIT_MESSAGE = (
    "You've used all 5 quiz creations for today. Please come back tomorrow."
)


def daily_quiz_limit_message(limit: int) -> str:
    return (
        f"You've used all {limit} quiz creations for today. "
        "Please come back tomorrow."
    )


def client_key_from_request(request: Request) -> str:
    """Hash the client IP for in-memory counters (Cloud Run: X-Forwarded-For)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client is not None:
        ip = request.client.host
    else:
        ip = "unknown"
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:32]


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class DailyQuizRateLimiter:
    """In-memory per-IP daily quiz creation limit (resets at UTC midnight)."""

    def __init__(self, *, daily_limit: int = DEFAULT_DAILY_QUIZ_LIMIT) -> None:
        if daily_limit < 1:
            raise ValueError("daily_limit must be at least 1")
        self.daily_limit = daily_limit
        self._lock = threading.Lock()
        self._counts: dict[str, tuple[str, int]] = {}

    @classmethod
    def from_env(cls) -> DailyQuizRateLimiter | NoOpQuizRateLimiter:
        if os.getenv("QUIZ_RATE_LIMIT_DISABLED", "").strip() in {"1", "true", "True"}:
            return NoOpQuizRateLimiter()
        raw = os.getenv("QUIZ_CREATE_DAILY_LIMIT", "").strip()
        limit = int(raw) if raw else DEFAULT_DAILY_QUIZ_LIMIT
        return cls(daily_limit=limit)

    def try_consume(self, client_key: str) -> tuple[bool, int]:
        """Record one quiz creation if allowed. Returns (allowed, remaining_today)."""
        today = _utc_date()
        with self._lock:
            stored_date, count = self._counts.get(client_key, (today, 0))
            if stored_date != today:
                count = 0
            if count >= self.daily_limit:
                return False, 0
            count += 1
            self._counts[client_key] = (today, count)
            return True, self.daily_limit - count

    def clear(self) -> None:
        with self._lock:
            self._counts.clear()


class NoOpQuizRateLimiter:
    """Disable rate limits (tests or local dev)."""

    daily_limit = DEFAULT_DAILY_QUIZ_LIMIT

    def try_consume(self, client_key: str) -> tuple[bool, int]:
        return True, self.daily_limit

    def clear(self) -> None:
        return None
