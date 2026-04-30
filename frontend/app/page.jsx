import Quiz from '@/components/Quiz';

export default function Page() {
  // `cloud_run_url` is a private Vercel env var (not NEXT_PUBLIC_*).
  // Read it on the server and pass it to the client component.
  const apiBaseUrl = process.env.cloud_run_url || process.env.CLOUD_RUN_URL || null;
  return <Quiz apiBaseUrl={apiBaseUrl} />;
}
