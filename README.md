# Semantic Personality Quiz

An interactive personality quiz that maps the user's answers onto a vector space and classifies them against fictional **classes** (Pokémon types, Hogwarts houses, etc.) by average cosine similarity to reference characters.

Users describe a franchise in natural language; the backend uses Gemini to build a character roster, roleplays each character through 15 Likert questions, and classifies new answers on demand.

## Quickstart: local development

No Docker or GCP required. You need **Python 3.13**, **npm**, a **Gemini API key**, and internet access (Gemini + Fandom wiki scraping).

### Prerequisites

| Required | Notes |
|----------|-------|
| Git | Clone this repo |
| Python 3.13 | e.g. 3.13.13 |
| npm | Current LTS Node is a safe choice (not pinned in `package.json`) |
| Gemini API key | [Google AI Studio](https://aistudio.google.com/apikey) |
| Internet | Quiz generation calls Gemini and scrapes Fandom wikis |

**Not required for local dev:** Docker, `gcloud`, service account JSON, `GOOGLE_APPLICATION_CREDENTIALS`, or any `GCS_*` variables.

### 1. Install dependencies

From the repo root:

```bash
git clone <repo-url>
cd sematic-personality-quiz

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r api/requirements.txt

cd frontend && npm install && cd ..
```

Use root [`requirements.txt`](./requirements.txt) instead if you also want pytest, pre-commit, and Playwright.

### 2. Configure environment

**Backend** — copy [`.env.example`](./.env.example) to `.env` at the repo root:

```env
GEMINI_API_KEY=your_key_here
QUIZ_RATE_LIMIT_DISABLED=1
```

- `QUIZ_RATE_LIMIT_DISABLED=1` avoids the production 5-quizzes-per-day limit while you iterate locally.
- **Do not set** `GCS_QUIZZES_BUCKET`, `GOOGLE_APPLICATION_CREDENTIALS`, or `GCP_*` for local dev. Without GCS, quizzes are stored on disk under `api/data/quizzes/`.

**Frontend** — copy [`frontend/.env.example`](./frontend/.env.example) to `frontend/.env.local`:

```env
CLOUD_RUN_URI=http://localhost:8080
```

The app defaults to `http://localhost:8080` if this is unset, but setting it explicitly avoids confusion.

### 3. Run (two terminals)

**Terminal 1 — API** (repo root, venv active):

```bash
uvicorn api.api:app --reload --port 8080
```

Sanity check:

```bash
curl http://localhost:8080/healthz
# {"status":"ok","reference_size":...}
```

**Terminal 2 — frontend:**

```bash
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 4. Smoke test

1. Enter a short prompt (e.g. `Hogwarts houses from Harry Potter`, ≤120 characters).
2. Click **CREATE QUIZ** — the API parses the prompt via Gemini (may take several seconds).
3. Wait on the creating screen while background generation roleplays each character (minutes; depends on roster size and wiki availability).
4. Answer 15 Likert questions, then view your class, closest character, ranking, and PCA plot.
5. Browse created quizzes at `/quizzes` (loaded from `api/data/quizzes/` on disk).

### Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| 422 about `GEMINI_API_KEY` | Missing or placeholder key | Set key in root `.env`, restart uvicorn |
| 429 daily limit | Rate limiter active | `QUIZ_RATE_LIMIT_DISABLED=1` in `.env` |
| 503 AI overload | Gemini capacity | Retry later; not a setup issue |
| Quiz stuck on “generating” | Wiki or LLM failure | Check uvicorn logs; try a well-known franchise |
| Frontend can't reach API | Wrong URL or API down | Confirm `CLOUD_RUN_URI` and `curl localhost:8080/healthz` |
| GCS / credentials errors | Bucket set in `.env` | Remove `GCS_*` and `GOOGLE_APPLICATION_CREDENTIALS` |
| `ModuleNotFoundError: api` | Wrong working directory | Run uvicorn from **repo root**, not `api/` |

**Classifier only (no quiz generation):** `POST /classify` with 15 answers uses the bundled [`api/data/gym_leaders.csv`](./api/data/gym_leaders.csv) preset.

---

## Optional: local dev without Gemini

For offline work or CI-style runs, skip the API key and use a fixed Harry Potter fixture with instant generation:

```env
FAKE_QUIZ_SPEC=1
QUIZ_RATE_LIMIT_DISABLED=1
```

See [`api/test_mode.py`](./api/test_mode.py). Full-stack E2E tests use this mode automatically.

---

## Optional: GCS persistence (production / advanced)

By default, quizzes are written to `api/data/quizzes/` on the API host. That is fine for local dev but ephemeral on Cloud Run.

To persist quizzes in Google Cloud Storage, set `GCS_QUIZZES_BUCKET` and configure [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials). GCS does not use a Gemini-style API key.

Object layout:

```text
gs://{bucket}/quizzes/{quiz_id}/meta.json
gs://{bucket}/quizzes/{quiz_id}/reference.csv
gs://{bucket}/quizzes/{quiz_id}/raw/*.txt   # optional LLM traces
```

| Environment | Setup |
|-------------|-------|
| **Cloud Run** | Grant the runtime service account `roles/storage.objectAdmin` on the bucket. No JSON key on the server. |
| **Local + GCS** | `gcloud auth application-default login`, or a service account JSON via `GOOGLE_APPLICATION_CREDENTIALS`. |

**One-time bucket setup** (replace `YOUR_BUCKET_NAME`):

```bash
RUNTIME_SA=$(gcloud run services describe personality-quiz-api \
  --region us-west1 \
  --format='value(spec.template.spec.serviceAccountName)')
gcloud storage buckets add-iam-policy-binding gs://YOUR_BUCKET_NAME \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/storage.objectAdmin"
```

Set `GCS_QUIZZES_BUCKET` on Cloud Run (or as a GitHub Actions secret for deploy). See [`.env.example`](./.env.example).

---

## Architecture

```plaintext
sematic-personality-quiz/
├── frontend/                  # Next.js (App Router) — Vercel-hosted UI
├── api/                       # FastAPI service — Cloud Run
│   ├── api.py                 # HTTP endpoints
│   ├── classifier.py          # cosine-similarity math + reference loader
│   ├── generation/            # prompt → roster → roleplay pipeline
│   ├── storage/               # local disk + optional GCS
│   └── data/gym_leaders.csv   # bundled preset reference vectors
├── shared/questions.json      # 15 quiz questions (synced to frontend)
├── tests/                     # pytest suite
└── requirements.txt           # full dev env (api + tests)
```

The frontend collects 15 Likert answers in `[-1, 1]` and POSTs them to the API, which scores each class by mean cosine similarity to its reference characters.

## Classification

For an incoming answer vector `v` (15-dim, each entry in `{-1, -0.5, 0, 0.5, 1}`):

1. Compute cosine similarity between `v` and every reference character vector.
2. For each class, average those similarities across its characters.
3. Rank classes by that average score, descending.

The top-ranked type is returned along with the full ranking and a 3D PCA projection.

## API

The service lives in [`api/`](./api). Main endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/healthz` | Liveness + preset reference size |
| `POST` | `/quizzes` | Create a custom quiz from a prompt |
| `GET` | `/quizzes` | List persisted quizzes |
| `GET` | `/quizzes/{id}` | Quiz generation status |
| `POST` | `/quiz_results` | Classify 15 answers for a quiz |
| `POST` | `/classify` | Preset gym-leaders quiz (backward compatible) |

## Frontend

The web UI lives in [`frontend/`](./frontend). See [`frontend/README.md`](./frontend/README.md) for routes, component map, and frontend-only tests.

Deploy on Vercel with **Root Directory** `frontend` and `CLOUD_RUN_URI` set to your API base URL (no trailing slash).

## Python tooling

```bash
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

Plain `pytest` excludes full-stack application tests (`pytest -m application`).

### Pre-commit

```bash
pip install -r requirements.txt
pre-commit install
pre-commit run --all-files
```

Hooks run file hygiene plus `pytest -m "not application"` when API or test files change.

### Full application E2E

```bash
pip install playwright pytest-playwright
playwright install chromium
(cd frontend && npm install && npm run build)
pytest -m application
```

## Production deploy

### Cloud Run (API)

Pushes to `main` that touch the API run [`.github/workflows/deploy-api.yml`](./.github/workflows/deploy-api.yml): pre-commit, pytest, build, deploy.

Repository secrets: `GCP_SA_KEY`, `GEMINI_API_KEY`, and optionally `GCS_QUIZZES_BUCKET`, `GCP_PROJECT_ID`, `GCP_REGION`, etc.

Manual deploy:

```bash
gcloud run deploy personality-quiz-api \
  --source . \
  --region <region> \
  --allow-unauthenticated \
  --port 8080
```

Set `CORS_ALLOW_ORIGINS` to your Vercel domain in production; defaults to `*` for local dev.

### Docker (optional)

```bash
docker build -f api/Dockerfile -t personality-quiz-api .
docker run --rm -p 8080:8080 -e PORT=8080 personality-quiz-api
```

Build context is the **repo root**.
