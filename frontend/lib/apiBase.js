export function normalizeBaseUrl(raw) {
  if (!raw) return null;
  return String(raw).replace(/\/+$/, '');
}

export function resolveApiBaseUrl(explicit) {
  return (
    normalizeBaseUrl(explicit) ||
    normalizeBaseUrl(process.env.NEXT_PUBLIC_API_URL) ||
    'http://localhost:8080'
  );
}
