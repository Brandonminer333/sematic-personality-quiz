"""Logging setup for local dev and Cloud Run (stdout → Cloud Logging)."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone

_EXTRA_FIELDS = (
    "quiz_id",
    "stage",
    "character",
    "class_name",
    "event",
    "http_method",
    "http_path",
    "http_status",
    "duration_ms",
)


class CloudRunJsonFormatter(logging.Formatter):
    """Emit one JSON object per line for Cloud Logging queries."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
        }
        for key in _EXTRA_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """Configure root logger once (idempotent)."""
    root = logging.getLogger()
    if getattr(root, "_quiz_logging_configured", False):
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    use_json = os.getenv("LOG_FORMAT", "").lower() == "json" or bool(
        os.getenv("K_SERVICE")
    )
    if use_json:
        handler.setFormatter(CloudRunJsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(levelname)s %(name)s: %(message)s")
        )

    root.handlers.clear()
    root.addHandler(handler)
    root._quiz_logging_configured = True  # type: ignore[attr-defined]
