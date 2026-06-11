'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ResultView from '@/components/ResultView';
import { getQuizMeta, getQuizResult } from '@/lib/session';

export default function ResultsPage({ quizId }) {
  const router = useRouter();
  const [result, setResult] = useState(null);
  const [title, setTitle] = useState('');

  useEffect(() => {
    const stored = getQuizResult(quizId);
    if (!stored) {
      router.replace('/');
      return;
    }
    const meta = getQuizMeta(quizId);
    setResult(stored);
    setTitle(meta?.title ?? '');
  }, [quizId, router]);

  if (!result) return null;

  return <ResultView result={result} title={title} />;
}
