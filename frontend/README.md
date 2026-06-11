# Frontend — Personality Quiz

A [Next.js](https://nextjs.org/) (App Router) app for the customizable personality quiz. Deployed on Vercel.

If you are new to Next.js or React, read **Project layout for beginners** below first — it maps URLs to files and explains what to edit.

## Routes

| Route | Purpose |
|-------|---------|
| `/` | Landing — describe a fictional class system |
| `/creating/[quizId]` | Brief “creating” screen before questions |
| `/quiz/[quizId]` | 15 Likert questions |
| `/quiz/[quizId]/waiting` | Classify via `POST /quiz_results` |
| `/quiz/[quizId]/results` | Class label, closest character, ranking, PCA |
| `/error` | Generic error page |

## Project layout for beginners

### How Next.js routing works here

This app uses the **App Router**. The folder structure under `app/` defines URLs:

- `app/page.jsx` → `/`
- `app/quiz/[quizId]/page.jsx` → `/quiz/abc123` (the `[quizId]` folder is a **dynamic segment** — any id in the URL is passed into the page as `params.quizId`)

You do not configure routes in a separate router file. If you add `app/about/page.jsx`, you automatically get `/about`.

### Two layers: thin routes + fat components

Most `app/**/page.jsx` files are **thin wrappers**. They only:

1. Read route params (like `quizId`)
2. Render a component from `components/`

Example — the quiz URL file:

```jsx
// app/quiz/[quizId]/page.jsx
import QuizPage from '@/components/QuizPage';

export default async function QuizRoute({ params }) {
  const { quizId } = await params;
  return <QuizPage quizId={quizId} />;
}
```

**To change what users see on a screen, edit the component in `components/`, not usually the `page.jsx` wrapper.**

### Where to edit what

| You want to change… | Start here |
|---------------------|------------|
| Landing copy, prompt textarea, “CREATE QUIZ” button | `components/LandingPage.jsx` |
| Short “Creating your quiz…” screen | `components/CreatingPage.jsx` |
| Question UI, answer buttons, progress bar | `components/QuestionFlow.jsx` (used by `QuizPage.jsx`) |
| Loading quiz metadata before questions | `components/QuizPage.jsx` |
| “Waiting for results…” + API submit | `components/WaitingPage.jsx` |
| Results layout (class, character, ranking) | `components/ResultsPage.jsx`, `components/ResultView.jsx` |
| PCA scatter plot | `components/PcaPlot.jsx` |
| Error message display | `components/ErrorPage.jsx` |
| Site title, fonts, API base URL wiring for whole app | `app/layout.jsx` |
| Global styles (colors, buttons, cards) | `app/globals.css` |
| API calls (`POST /quizzes`, etc.) | `lib/api.js` |
| `sessionStorage` keys for quiz state | `lib/session.js` |
| The 15 quiz questions shown in the UI | `lib/questions.data.json` (keep in sync with `../shared/questions.json`) |
| Favicon / static images | `public/` |

### Folder reference

```plaintext
frontend/
├── app/                    # Routes (URLs) — mostly thin page.jsx files
│   ├── layout.jsx          # Wraps every page: <html>, fonts, ApiProvider
│   ├── page.jsx            # /
│   ├── globals.css         # Global CSS
│   ├── creating/[quizId]/page.jsx
│   ├── quiz/[quizId]/page.jsx
│   │   ├── waiting/page.jsx
│   │   └── results/page.jsx
│   └── error/page.jsx
├── components/             # React UI — where most editing happens
├── lib/                    # Shared JS (API client, session, questions loader)
├── public/                 # Static files served as-is (favicon, icons)
├── tests/                  # Playwright E2E tests
├── next.config.mjs         # Next.js config (aliases, etc.)
└── package.json            # npm scripts and dependencies
```

### React basics used in this project

- **Components** are functions that return JSX (HTML-like syntax). Files in `components/` export one main component each.
- **`'use client'`** at the top of a file means that component runs in the **browser** (for `useState`, `useEffect`, `onClick`, `sessionStorage`). Files in `app/` without it are **server components** by default; interactive pieces live in `components/` with `'use client'`.
- **Props** pass data into components, e.g. `<QuizPage quizId={quizId} />`.
- **`@/` imports** — `@/components/LandingPage` means `frontend/components/LandingPage.jsx` (see `jsconfig.json`).

### User flow (which file runs when)

1. `/` → `LandingPage` → `lib/api.js` `createQuiz()` → navigate to `/creating/{id}`
2. `/creating/{id}` → `CreatingPage` (short delay) → `/quiz/{id}`
3. `/quiz/{id}` → `QuizPage` → `QuestionFlow` → answers saved via `lib/session.js`
4. `/quiz/{id}/waiting` → `WaitingPage` → `submitQuizResults()` → `/quiz/{id}/results`
5. `/quiz/{id}/results` → `ResultsPage` reads cached result from `sessionStorage`

### Environment variables

| Variable | Purpose |
|----------|---------|
| `CLOUD_RUN_URI` | Backend API base URL (server-side, used in `layout.jsx`) |
| `NEXT_PUBLIC_API_URL` | Optional client fallback if `CLOUD_RUN_URI` is unset |

Copy `frontend/.env.example` to `frontend/.env.local` for local dev.

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
