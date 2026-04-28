"""Generic classifier for OpenAI-compatible free-tier providers.

Handles OpenRouter, Groq, GitHub Models, and HuggingFace Inference API.
All config is passed via env vars so the same script runs for all four
providers — only the workflow changes the values.

Reads env vars:
  PROVIDER_API_KEY    — API key for the provider
  PROVIDER_BASE_URL   — OpenAI-compatible base URL
  MODEL               — model name to use in API call
  MODEL_LABEL         — value stored in classifying_model column
  DATE_FROM           — classify opinions filed on/after this date (YYYY-MM-DD)
  DATE_TO             — classify opinions filed on/before this date (YYYY-MM-DD)
  CLASSIFY_LIMIT      — max opinions to classify (default: 500)
  CLASSIFY_SUMMARY_FILE — path to write summary for email notification

Provider config reference:
  OpenRouter:     base_url=https://openrouter.ai/api/v1
  Groq:           base_url=https://api.groq.com/openai/v1
  GitHub Models:  base_url=https://models.inference.ai.azure.com
  HuggingFace:    base_url=https://api-inference.huggingface.co/v1/
"""

from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import sys
import os

from openai import OpenAI
import requests


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


MAX_TEXT_CHARS = 6000


@dataclass(frozen=True)
class LLMCandidate:
    """One model endpoint to try, in priority order.

    `provider_kind` supports:
      - "openai_compatible": uses OpenAI(base_url=..., api_key=...).chat.completions.create(...)
      - "cloudflare_workers_ai": uses Cloudflare Workers AI REST endpoint (/ai/run)
    """

    api_key: str
    base_url: str
    model: str
    model_label: str | None = None
    provider_kind: str = "openai_compatible"


def _is_quota_or_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc)
    # Keep this intentionally broad: different providers format these differently.
    return any(
        token in msg
        for token in (
            "Error code: 402",
            "Error code: 429",
            # Treat "model not available / misconfigured" as a fallthrough too.
            # This keeps long batch jobs moving even if one model ID goes stale.
            "Error code: 404",
            "404 Client Error",
            "402 Client Error",
            "429 Client Error",
            # Connectivity issues should also fall through (e.g. proxy/VPN issues).
            "APIConnectionError",
            "ProxyError",
            "Tunnel connection failed",
            "Connection error",
            "connect timeout",
            "Read timed out",
            "insufficient_quota",
            "quota",
            "rate limit",
            "rate_limit",
            "credits",
            "Payment Required",
            "Too Many Requests",
            "No endpoints found",
            "model not found",
        )
    )


def call_prompt_with_first_available_model(
    prompt: str,
    *,
    candidates: list[LLMCandidate],
    temperature: float = 0,
    max_tokens: int = 2048,
    timeout_s: int = 120,
) -> dict[str, Any]:
    """Try candidates in order until one succeeds.

    Returns a dict containing:
      - content: str (assistant content)
      - model: str (model name used)
      - base_url: str (endpoint used)
      - model_label: str | None (if provided)
      - provider_kind: str

    Quota/rate-limit-like failures (402/429) are treated as "no credits" and we
    fall through to the next candidate.
    """

    if not candidates:
        raise ValueError("candidates must be a non-empty list[LLMCandidate]")

    failures: list[str] = []
    last_exc: Exception | None = None

    for idx, c in enumerate(candidates, start=1):
        try:
            if c.provider_kind == "cloudflare_workers_ai":
                resp = requests.post(
                    f"{c.base_url.rstrip('/')}/{c.model}",
                    headers={"Authorization": f"Bearer {c.api_key}"},
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=timeout_s,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["result"]["response"]
            elif c.provider_kind == "openai_compatible":
                client = OpenAI(base_url=c.base_url, api_key=c.api_key)
                r = client.chat.completions.create(
                    model=c.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = (r.choices[0].message.content or "").strip()
            else:
                raise ValueError(f"Unknown provider_kind={c.provider_kind!r}")

            return {
                "content": content,
                "model": c.model,
                "base_url": c.base_url,
                "model_label": c.model_label,
                "provider_kind": c.provider_kind,
            }

        except Exception as e:
            last_exc = e
            if _is_quota_or_rate_limit_error(e):
                failures.append(
                    f"[{idx}/{len(candidates)}] {c.provider_kind} {c.model_label or c.model} @ {c.base_url}: {e}"
                )
                continue
            raise

    detail = "\n".join(
        failures) if failures else "(no failure details captured)"
    raise RuntimeError(
        "All candidates appear to be out of credits / rate-limited.\n" + detail
    ) from last_exc
