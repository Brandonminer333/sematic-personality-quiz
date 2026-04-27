# Semantic Personality Quiz

An interactive personality quiz that maps the user's answers onto a vector space and finds their nearest **Pokémon gym leader type** (Fire, Water, Grass, etc.) by weighted cosine similarity. Gym leaders are used as a proxy: each leader canonically represents one type, and the LLM is prompted to embody that type's general personality rather than the specific character.

## Architecture

```
sematic-personality-quiz/
├── frontend/          # Next.js (App Router) — Vercel-hosted web UI
├── data_sythesizer/   # Python — synthetic-data + reference-vector generation
├── tests/             # pytest suite for the synthesizer
├── gym_leader_eda.ipynb
└── requirements.txt
```

> A FastAPI backend (`backend/`, deployed to Google Cloud Run) is on the roadmap and will replace the precomputed answer-lookup table currently bundled with the frontend. See [Roadmap](#roadmap).

## Classification

- Each answer maps to a weight vector over all archetypes.
- User answers are summed and normalized to a unit vector.
- Result is the archetype with the highest cosine similarity to the user's unit vector.
- A decision tree trained on per-question answer sequences serves as a secondary validator during development; disagreement between the two flags miscalibrated questions or reference vectors.

## Frontend (Next.js, Vercel)

The web UI lives in [`frontend/`](./frontend). See [`frontend/README.md`](./frontend/README.md) for run/test instructions.

Deploy by importing the repo into Vercel and setting **Root Directory** to `frontend`. No `vercel.json` is required.

## Python tooling

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Pre-commit hook

Runs an end-to-end smoke test (boots the Next.js dev server, walks the full
quiz flow with Playwright, asserts a result card renders) before every commit.
The hook is skipped automatically when no `frontend/`, `backend/`, `tests/`,
`requirements.txt`, or `conftest.py` changes are staged.

One-time setup:

```bash
pip install -r requirements.txt
playwright install chromium
(cd frontend && npm install)
./scripts/install-git-hooks.sh
```

Run the integration test directly any time:

```bash
pytest tests/test_integration.py
```

## Roadmap

- **Backend (FastAPI on Google Cloud Run)** — replace the precomputed lookup table with on-demand weighted cosine similarity over reference vectors.
- **3-D PCA visualization** — render the user's answer-vector embedding next to all gym leader vectors using principal components, displayed on the results screen.
- **Character-set agnostic pipeline** — rerun the agent on any topic (Hogwarts houses, Myers-Briggs archetypes, office roles, etc.) with no changes to the quiz engine.
- **Question shuffling** — randomize question and answer order between attempts so users can double-check results without reverse-engineering the quiz.
- **Soft results** — optionally surface the top 2–3 archetypes with cosine scores rather than a hard single answer, for users who want nuance.
- **Quiz database** — store generated quizzes so the agent can reuse or extend existing character sets rather than regenerating from scratch.
