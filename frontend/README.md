# Frontend — Semantic Personality Quiz

A [Next.js](https://nextjs.org/) (App Router) app that hosts the gym-leader personality quiz. Deployed on Vercel.

## Local development

```bash
npm install
cp .env.example .env.local   # points NEXT_PUBLIC_API_URL at http://localhost:8080
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000). You'll also need the FastAPI backend running on `localhost:8080` — see the root README for instructions, or run:

```bash
(cd .. && uvicorn backend.api:app --reload --port 8080)
```

## End-to-end tests

```bash
npx playwright install --with-deps   # one-time
npm run test:e2e
```

## Deploy

This is intended to be its own Vercel project (separate from any other site).

When importing the repo into Vercel:

- **Root Directory:** `frontend`
- **Framework Preset:** Next.js (auto-detected)
- **Build Command:** `next build` (default)
- **Install Command:** `npm install` (default)
- **Environment Variables:** set `NEXT_PUBLIC_API_URL` to the Cloud Run URL of the classifier backend (no trailing slash). This must be set at build time — `NEXT_PUBLIC_*` values are baked into the static bundle.

No `vercel.json` is required.

## Structure

```
frontend/
├── app/                    # App Router routes
│   ├── layout.jsx          # root layout, fonts, metadata
│   ├── page.jsx            # home page (server component shell)
│   └── globals.css         # site-wide styles
├── components/
│   └── Quiz.jsx            # main client component (the quiz)
├── tests/                  # Playwright spec (mocks /classify with route())
└── public/                 # static assets (favicon, icons)
```

The classifier itself lives in `backend/` (FastAPI on Cloud Run). On submit, the quiz POSTs the 15-answer vector to `${NEXT_PUBLIC_API_URL}/classify` and renders the returned type.
