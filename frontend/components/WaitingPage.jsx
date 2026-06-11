'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { QUIZ_RESULTS_TIMEOUT_MS, submitQuizResults } from '@/lib/api';
import { useApiBase } from '@/components/ApiProvider';
import { getQuizAnswers, setLastError, setQuizResult } from '@/lib/session';


export default function WaitingPage({ quizId }) {
  const router = useRouter();
  const apiBase = useApiBase();

  useEffect(() => {
    const answers = getQuizAnswers(quizId);
    if (!answers) {
      router.replace('/');
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        const result = await submitQuizResults(apiBase, quizId, answers, {
          timeoutMs: QUIZ_RESULTS_TIMEOUT_MS,
        });
        if (cancelled) return;
        setQuizResult(quizId, result);
        router.replace(`/quiz/${quizId}/results`);
      } catch (err) {
        if (cancelled) return;
        setLastError(err?.message || 'quiz results failed');
        router.replace('/error');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [apiBase, quizId, router]);

  return (
    <div className="container">
      <header>
        <div className="pixel-title">Waiting for results…</div>
        <div className="subtitle">Calculating your class</div>
      </header>
      <div className="intro-card">
        <p>Hang tight while we match your answers to the cast.</p>
      </div>
    </div>
  );
}
