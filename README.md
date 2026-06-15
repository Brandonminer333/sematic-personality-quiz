# WIP — Needs to be updated!!!

# Semantic Personality Quiz

An interactive personality quiz that maps the user's answers onto a vector space and classifies them against fictional **classes** (Pokémon types, Hogwarts houses, etc.) by average cosine similarity to reference characters.

## Architecture

```plaintext
sematic-personality-quiz/
├── frontend/                  # Next.js (App Router) — Vercel-hosted UI shell
├── api/                       # FastAPI service — classifier (Cloud Run)
│   ├── __init__.py            # makes `api` an importable package
│   ├── api.py                 # /classify and /healthz endpoints
│   ├── classifier.py          # cosine-similarity math + reference loader
│   ├── data/gym_leaders.csv   # canonical reference vectors (bundled into image)
│   ├── requirements.txt       # runtime deps for the container
│   └── Dockerfile
├── data_sythesizer/           # offline tooling: regenerate reference data
├── tests/                     # pytest suite (unit + integration)
├── gym_leader_eda.ipynb       # exploratory work that yielded the algorithm
├── .dockerignore              # keeps the Cloud Run build context minimal
└── requirements.txt           # full dev env (incl. api + tests)
```

The frontend no longer ships a precomputed answer→type lookup. It collects 15 Likert answers in `[-1, 1]` and POSTs them to the FastAPI backend, which scores each class by mean cosine similarity to its reference characters on demand.

## Classification

For an incoming answer vector `v` (15-dim, each entry in `{-1, -0.5, 0, 0.5, 1}`):

1. Compute cosine similarity between `v` and every reference character vector.
2. For each class, average those similarities across its characters.
3. Rank classes by that average score, descending.

The top-ranked type is returned along with the full ranking (so the UI can later show top-N or confidence scores).

## Backend (FastAPI on Cloud Run)

The service lives in [`api/`](./api). Endpoints:

- `GET /healthz` → `{"status": "ok", "reference_size": <int>}`
- `POST /classify` → `{"type": "<TitleCase>", "ranking": [{"type": ..., "score": ...}, ...]}`
  - Body: `{"answers": [<15 floats in [-1, 1]>]}`

### Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r api/requirements.txt
uvicorn api.api:app --reload --port 8080
# sanity check:
curl localhost:8080/healthz
```

### Build + run the container locally

The Dockerfile expects the **repo root** as the build context (so it can copy
the `api/` package and the bundled reference CSV in one go):

```bash
docker build -f api/Dockerfile -t personality-quiz-api .
docker run --rm -p 8080:8080 -e PORT=8080 personality-quiz-api
```

### Deploy to Cloud Run

The simplest path is `--source .` — Cloud Build will pick up `api/Dockerfile`
(via `gcloud`'s buildpacks fallback) or you can pass it explicitly:

```bash
gcloud run deploy personality-quiz-api \
  --source . \
  --region <region> \
  --allow-unauthenticated \
  --port 8080
```

Or build the image yourself and deploy:

```bash
# Build with repo root as context so `COPY api …` resolves.
gcloud builds submit \
  --tag gcr.io/<project>/personality-quiz-api \
  --config /dev/stdin <<'YAML'
steps:
  - name: gcr.io/cloud-builders/docker
    args: ['build', '-f', 'api/Dockerfile', '-t', 'gcr.io/$PROJECT_ID/personality-quiz-api', '.']
images: ['gcr.io/$PROJECT_ID/personality-quiz-api']
YAML

gcloud run deploy personality-quiz-api \
  --image gcr.io/<project>/personality-quiz-api \
  --region <region> \
  --allow-unauthenticated
```

Cloud Run injects `$PORT`; the container listens on `0.0.0.0:$PORT` (default
`8080`). Set `CORS_ALLOW_ORIGINS` to your Vercel domain (comma-separated) to
lock down CORS in prod; it defaults to `*` for easy local dev.

### Quiz storage (GCS)

Generated quizzes are written under `quizzes/{quiz_id}/` in a GCS bucket so
shareable `quiz_id` URLs survive Cloud Run restarts. Object layout:

```text
gs://{bucket}/quizzes/{quiz_id}/meta.json
gs://{bucket}/quizzes/{quiz_id}/reference.csv
gs://{bucket}/quizzes/{quiz_id}/raw/*.txt   # optional LLM traces
```

**Credentials:** GCS does not use a Gemini-style API key. It uses
[Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials):

| Environment | Setup |
|-------------|-------|
| **Cloud Run** | Grant the runtime service account `roles/storage.objectAdmin` on the bucket. No JSON key on the server. |
| **Local dev** | Service account JSON via `GOOGLE_APPLICATION_CREDENTIALS`, or `gcloud auth application-default login`. |

**One-time bucket setup** (replace `YOUR_BUCKET_NAME`):

```bash
# 1. Cloud Run runtime SA — object access on the bucket
RUNTIME_SA=$(gcloud run services describe personality-quiz-api \
  --region us-west1 \
  --format='value(spec.template.spec.serviceAccountName)')
gcloud storage buckets add-iam-policy-binding gs://YOUR_BUCKET_NAME \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/storage.objectAdmin"

# 2. Local dev — create a JSON key (Console: IAM → Service Accounts → Keys → Add key)
# Grant the same role to your dev SA, then in .env:
#   GCS_QUIZZES_BUCKET=YOUR_BUCKET_NAME
#   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/dev-sa-key.json
```

Set `GCS_QUIZZES_BUCKET` on Cloud Run (or add a `GCS_QUIZZES_BUCKET` GitHub Actions
secret so deploy passes `--set-env-vars`). See [`.env.example`](./.env.example).

Without `GCS_QUIZZES_BUCKET`, quizzes are stored only on local disk under
`api/data/quizzes/` (fine for dev; ephemeral on Cloud Run).

## Frontend (Next.js, Vercel)

The web UI lives in [`frontend/`](./frontend). See [`frontend/README.md`](./frontend/README.md) for run/test instructions.

Set `CLOUD_RUN_URI` to the Cloud Run base URL on Vercel (and in `frontend/.env.local` for local dev). See [`frontend/.env.example`](./frontend/.env.example).

Deploy by importing the repo into Vercel and setting **Root Directory** to `frontend`.

## Python tooling

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Pre-commit

Hooks run on staged changes: basic file hygiene plus `pytest -m "not application"` when
`api/`, `tests/`, or related config changes (no Playwright / full-stack E2E).

One-time setup:

```bash
pip install -r requirements.txt
pre-commit install
```

Run hooks manually:

```bash
pre-commit run --all-files
```

Full application E2E (backend + Next.js + Playwright):

```bash
pip install playwright pytest-playwright
playwright install chromium
(cd frontend && npm install && npm run build)
pytest -m application
```

## CI / API deploy

Pushes to `main` that touch the API or tests run [`.github/workflows/deploy-api.yml`](.github/workflows/deploy-api.yml):

1. `pre-commit run --all-files`
2. `pytest -m "not application"`
3. Build → push to Artifact Registry → deploy Cloud Run

Add **repository secrets** under Settings → Secrets and variables → Actions:

- **`GCP_SA_KEY`** (required) — full service account JSON with Artifact Registry Writer,
  Cloud Run Admin, and Service Account User
- **`GEMINI_API_KEY`** (required) — injected into Cloud Run on each deploy via
  `--update-env-vars` (survives redeploys without manual console edits)
- Optional: `GCP_PROJECT_ID`, `GCP_REGION`, `AR_REPOSITORY`, `IMAGE_NAME`,
  `CLOUD_RUN_SERVICE`, `GCS_QUIZZES_BUCKET` (defaults match this project's GCP setup)

## Roadmap

- **3-D PCA visualization** — render the user's answer-vector embedding next to all gym leader vectors using principal components, displayed on the results screen.
- **Character-set agnostic pipeline** — rerun the agent on any topic (Hogwarts houses, Myers-Briggs archetypes, office roles, etc.) with no changes to the quiz engine.
- **Question shuffling** — randomize question and answer order between attempts so users can double-check results without reverse-engineering the quiz.
- **Soft results** — surface the top 2–3 archetypes with cosine scores rather than a hard single answer (the backend already returns the full ranking).
- **Quiz database** — store generated quizzes so the agent can reuse or extend existing character sets rather than regenerating from scratch.
