# Frontend — Personality Quiz

A [Next.js](https://nextjs.org/) (App Router) app for the customizable personality quiz. Deployed on Vercel.

## Routes

| Route | Purpose |
|-------|---------|
| `/` | Landing — describe a fictional class system |
| `/creating/[quizId]` | Brief “creating” screen before questions |
| `/quiz/[quizId]` | 15 Likert questions |
| `/quiz/[quizId]/waiting` | Classify via `POST /quiz_results` |
| `/quiz/[quizId]/results` | Class label, closest character, ranking, PCA |
| `/error` | Generic error page |

## Local development

```bash
npm install
cp .env.example .env.local   # set CLOUD_RUN_URI (see .env.example)
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Run the FastAPI backend on port 8080 — see the root README.

## End-to-end tests

```bash
npx playwright install --with-deps   # one-time
npm run test:e2e
```

Full stack E2E (backend + frontend) is opt-in:

```bash
pytest -m application
```

Plain `pytest` excludes application tests.

## Deploy

Vercel project settings:

- **Root Directory:** `frontend`
- **Environment Variables:** `CLOUD_RUN_URI` (Cloud Run API base URL, no trailing slash). Optionally `NEXT_PUBLIC_API_URL` for client fallback.

The app calls `POST /quizzes`, `GET /quizzes/{id}`, and `POST /quiz_results` on the API.
