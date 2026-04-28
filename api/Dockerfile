# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install runtime deps first so they cache independently of source changes.
# Build context is expected to be the repo root (so `api/` is visible here).
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

# Copy the api package (code + bundled reference CSV under api/data/).
COPY api /app/api

# Run as a non-root user. Cloud Run doesn't require this, but it's good hygiene
# and prevents accidental writes inside the read-only container filesystem.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

# Cloud Run injects $PORT (default 8080). EXPOSE is informational only.
EXPOSE 8080

# Use a single uvicorn worker: Cloud Run already scales by spawning instances,
# and multi-worker setups duplicate the in-memory reference data per worker.
CMD ["sh", "-c", "exec uvicorn api.api:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
