const DEFAULT_POLL_MS = 500;
export const QUIZ_RESULTS_TIMEOUT_MS = 5 * 60 * 1000;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function parseErrorDetail(res) {
  try {
    const data = await res.json();
    if (typeof data?.detail === 'string') return data.detail;
    if (data?.detail) return JSON.stringify(data.detail);
  } catch {
    // ignore
  }
  return '';
}

export async function createQuiz(apiBase, prompt) {
  const res = await fetch(`${apiBase}/quizzes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    const detail = await parseErrorDetail(res);
    throw new ApiError(detail || `create quiz failed: ${res.status}`, res.status);
  }
  return res.json();
}

export async function listQuizzes(apiBase) {
  const res = await fetch(`${apiBase}/quizzes`);
  if (!res.ok) {
    const detail = await parseErrorDetail(res);
    throw new Error(detail || `list quizzes failed: ${res.status}`);
  }
  return res.json();
}

export async function getQuizStatus(apiBase, quizId) {
  const res = await fetch(`${apiBase}/quizzes/${quizId}`);
  if (!res.ok) {
    const detail = await parseErrorDetail(res);
    throw new Error(detail || `quiz status failed: ${res.status}`);
  }
  return res.json();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function submitQuizResults(
  apiBase,
  quizId,
  answers,
  { timeoutMs = QUIZ_RESULTS_TIMEOUT_MS, pollMs = DEFAULT_POLL_MS } = {},
) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const res = await fetch(`${apiBase}/quiz_results`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quiz_id: quizId, answers }),
    });

    if (res.status === 200) {
      return res.json();
    }

    if (res.status === 202) {
      const status = await getQuizStatus(apiBase, quizId);
      if (status.status === 'failed') {
        throw new Error(status.error || 'quiz generation failed');
      }
      if (status.status === 'ready') {
        continue;
      }
      await sleep(pollMs);
      continue;
    }

    const detail = await parseErrorDetail(res);
    throw new Error(detail || `quiz results failed: ${res.status}`);
  }

  throw new Error('timed out waiting for quiz results');
}
