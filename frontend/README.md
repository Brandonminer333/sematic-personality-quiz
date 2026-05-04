# Frontend — Semantic Personality Quiz

A [Next.js](https://nextjs.org/) (App Router) app that hosts the gym-leader personality quiz. Deployed on Vercel.

## Local development

```bash
npm install
cp .env.example .env.local   # set CLOUD_RUN_URI (see .env.example)
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
- **Environment Variables:** set **`CLOUD_RUN_URI`** to the Cloud Run base URL of the classifier (no trailing slash). The home page reads it on the server and passes it into the client quiz. Optionally set **`NEXT_PUBLIC_API_URL`** to the same value if you want a client-visible fallback; `NEXT_PUBLIC_*` is inlined at build time.

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

The classifier is the FastAPI app in `../api/` (Cloud Run in production). On submit, the quiz POSTs the 15-answer vector to `{apiBaseUrl}/classify` and renders the returned type.
