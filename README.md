# Semantic Personality Quiz

An interactive personality quiz that maps the user's answers onto a vector space and finds their nearest **Pokémon gym leader type** (Fire, Water, Grass, etc.) by weighted cosine similarity. Gym leaders are used as a proxy: each leader canonically represents one type, and the LLM is prompted to embody that type's general personality rather than the specific character.

## Architecture

```plaintext
sematic-personality-quiz/
├── frontend/                  # Next.js (App Router) — Vercel-hosted UI shell
├── api/                       # FastAPI service — classifier (Cloud Run)
│   ├── __init__.py            # makes `api` an importable package
│   ├── api.py                 # /classify and /healthz endpoints
│   ├── classifier.py          # weighted-cosine math + reference loader
│   ├── data/gym_leaders.csv   # canonical reference vectors (bundled into image)
│   ├── requirements.txt       # runtime deps for the container
│   └── Dockerfile
├── data_sythesizer/           # offline tooling: regenerate reference data
├── tests/                     # pytest suite (unit + integration)
├── gym_leader_eda.ipynb       # exploratory work that yielded the algorithm
├── .dockerignore              # keeps the Cloud Run build context minimal
└── requirements.txt           # full dev env (incl. api + tests)
```

The frontend no longer ships a precomputed answer→type lookup. It collects 15 Likert answers in `[-1, 1]` and POSTs them to the FastAPI backend, which computes weighted cosine similarity over the reference set on demand.

## Classification

For an incoming answer vector `v` (15-dim, each entry in `{-1, -0.5, 0, 0.5, 1}`):

1. Compute cosine similarity between `v` and every reference gym-leader vector.
2. For each Pokémon type, compute a *weighted average* of its leader vectors using the cosine similarities as weights — leaders that look more like the user contribute more.
3. Score each type by the mean of its weighted-average vector and rank descending.

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
- Optional: `GCP_PROJECT_ID`, `GCP_REGION`, `AR_REPOSITORY`, `IMAGE_NAME`,
  `CLOUD_RUN_SERVICE`, `DEPLOY_ENVIRONMENT` (defaults match this project's GCP setup)

## Roadmap

- **3-D PCA visualization** — render the user's answer-vector embedding next to all gym leader vectors using principal components, displayed on the results screen.
- **Character-set agnostic pipeline** — rerun the agent on any topic (Hogwarts houses, Myers-Briggs archetypes, office roles, etc.) with no changes to the quiz engine.
- **Question shuffling** — randomize question and answer order between attempts so users can double-check results without reverse-engineering the quiz.
- **Soft results** — surface the top 2–3 archetypes with cosine scores rather than a hard single answer (the backend already returns the full ranking).
- **Quiz database** — store generated quizzes so the agent can reuse or extend existing character sets rather than regenerating from scratch.
