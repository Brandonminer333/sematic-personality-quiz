const PREFIX = 'quiz:';

function key(quizId, suffix) {
  return `${PREFIX}${quizId}:${suffix}`;
}

export function clearAllQuizSessions() {
  if (typeof window === 'undefined') return;
  const toRemove = [];
  for (let i = 0; i < sessionStorage.length; i += 1) {
    const k = sessionStorage.key(i);
    if (k?.startsWith(PREFIX)) toRemove.push(k);
  }
  toRemove.forEach((k) => sessionStorage.removeItem(k));
}

export function setQuizMeta(quizId, meta) {
  sessionStorage.setItem(key(quizId, 'meta'), JSON.stringify(meta));
}

export function getQuizMeta(quizId) {
  const raw = sessionStorage.getItem(key(quizId, 'meta'));
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setQuizAnswers(quizId, answers) {
  sessionStorage.setItem(key(quizId, 'answers'), JSON.stringify(answers));
}

export function getQuizAnswers(quizId) {
  const raw = sessionStorage.getItem(key(quizId, 'answers'));
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setQuizResult(quizId, result) {
  sessionStorage.setItem(key(quizId, 'result'), JSON.stringify(result));
}

const LAST_ERROR_KEY = `${PREFIX}last-error`;

export function setLastError(message) {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(LAST_ERROR_KEY, message);
}

export function getLastError() {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(LAST_ERROR_KEY);
}

export function clearLastError() {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(LAST_ERROR_KEY);
}

export function getQuizResult(quizId) {
  const raw = sessionStorage.getItem(key(quizId, 'result'));
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
