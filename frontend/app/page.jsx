import Quiz from '@/components/Quiz';

/** Prefer runtime env on Vercel so `CLOUD_RUN_URI` is not baked in at build time. */
export const dynamic = 'force-dynamic';

function normalizeBaseUrl(raw) {
  if (!raw) return null;
  return String(raw).replace(/\/+$/, '');
}

/** Classifier base URL (no trailing slash). Server-only vars work here; no `NEXT_PUBLIC_` required. */
function getClassifierBaseUrl() {
  return normalizeBaseUrl(
    process.env.CLOUD_RUN_URI ||
      process.env.CLOUD_RUN_URL ||
      process.env.cloud_run_url ||
      process.env.NEXT_PUBLIC_API_URL ||
      null,
  );
}

export default function Page() {
  const apiBaseUrl = getClassifierBaseUrl();
  return <Quiz apiBaseUrl={apiBaseUrl} />;
}
