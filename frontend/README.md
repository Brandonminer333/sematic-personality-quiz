# Frontend — Semantic Personality Quiz

A [Next.js](https://nextjs.org/) (App Router) app that hosts the gym-leader personality quiz. Deployed on Vercel.

## Local development

```bash
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

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
├── data/
│   └── quiz_results.json   # precomputed answer→type lookup (temporary)
└── public/                 # static assets (favicon, icons)
```

> The `quiz_results.json` lookup is a temporary holdover from the gh-pages
> deployment. It will be removed in a follow-up step in favor of an on-demand
> weighted-cosine-similarity call to a FastAPI backend.
