# Dockerfile for the API
# Build from repository root: docker build -f api/Dockerfile -t personality-quiz-api .
FROM python:3.12-slim

WORKDIR /app

# Slim, pinned API deps (avoid repo-root requirements.txt).
COPY api/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Keep the `api` package so relative imports (`from .classifier`) work.
COPY api/ ./api/

# Roleplay prompts load quiz text from shared/questions.json at runtime.
COPY shared/ ./shared/

# Cloud Run sets PORT; local runs default to 8080.
ENV PORT=8080

CMD ["sh", "-c", "exec uvicorn api.api:app --host 0.0.0.0 --port ${PORT}"]
