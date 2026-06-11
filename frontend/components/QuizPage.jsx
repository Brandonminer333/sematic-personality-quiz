'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import QuestionFlow from '@/components/QuestionFlow';
import { getQuizStatus } from '@/lib/api';
import { useApiBase } from '@/components/ApiProvider';
import { getQuizMeta, setQuizMeta } from '@/lib/session';

export default function QuizPage({ quizId }) {
  const router = useRouter();
  const apiBase = useApiBase();
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const status = await getQuizStatus(apiBase, quizId);
        if (cancelled) return;

        if (status.status === 'failed') {
          router.replace('/error');
          return;
        }

        const nextMeta = {
          title: status.title,
          classes: status.classes,
        };
        setQuizMeta(quizId, nextMeta);
        setMeta(nextMeta);
        setLoading(false);
      } catch {
        if (!cancelled) router.replace('/error');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [apiBase, quizId, router]);

  if (loading) {
    const cached = getQuizMeta(quizId);
    if (cached) {
      return (
        <QuestionFlow
          quizId={quizId}
          title={cached.title}
          classes={cached.classes}
        />
      );
    }
    return (
      <div className="container">
        <div className="intro-card">
          <p>Loading quiz…</p>
        </div>
      </div>
    );
  }

  if (!meta) return null;

  return (
    <QuestionFlow quizId={quizId} title={meta.title} classes={meta.classes} />
  );
}
