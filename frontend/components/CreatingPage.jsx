'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

const MIN_WAIT_MS = Number(process.env.NEXT_PUBLIC_CREATE_MIN_WAIT_MS || 3000);

export default function CreatingPage({ quizId }) {
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => {
      router.push(`/quiz/${quizId}`);
    }, MIN_WAIT_MS);
    return () => clearTimeout(timer);
  }, [quizId, router]);

  return (
    <div className="container">
      <header>
        <div className="pixel-title">Creating your quiz…</div>
        <div className="subtitle">This will only take a moment</div>
      </header>
      <div className="intro-card">
        <p>We&apos;re preparing your characters and questions.</p>
      </div>
    </div>
  );
}
