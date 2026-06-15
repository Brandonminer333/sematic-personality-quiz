'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { listQuizzes } from '@/lib/api';
import { useApiBase } from '@/components/ApiProvider';

export default function QuizzesPage() {
  const apiBase = useApiBase();
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const data = await listQuizzes(apiBase);
        if (!cancelled) setQuizzes(data.quizzes ?? []);
      } catch (err) {
        if (!cancelled) {
          setError(err?.message || 'Failed to load quizzes');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  return (
    <div className="container">
      <header>
        <div className="pixel-title">Quiz library</div>
        <div className="subtitle">Quizzes created by the community</div>
      </header>

      <div className="intro-card quiz-catalog-card">
        {loading && <p className="quiz-catalog-status">Loading quizzes…</p>}

        {!loading && error && (
          <p className="quiz-catalog-status quiz-catalog-status--error">{error}</p>
        )}

        {!loading && !error && quizzes.length === 0 && (
          <p className="quiz-catalog-status">No quizzes yet. Be the first to create one!</p>
        )}

        {!loading && !error && quizzes.length > 0 && (
          <ul className="quiz-catalog-list">
            {quizzes.map((quiz) => (
              <li key={quiz.quiz_id} className="quiz-catalog-item">
                <Link href={`/quiz/${quiz.quiz_id}`} className="quiz-catalog-link">
                  <div className="quiz-catalog-title">{quiz.title}</div>
                  {quiz.source_prompt && (
                    <p className="quiz-catalog-prompt">{quiz.source_prompt}</p>
                  )}
                  <div className="quiz-catalog-meta">Take quiz →</div>
                </Link>
              </li>
            ))}
          </ul>
        )}

        <Link href="/" className="browse-quizzes-btn browse-quizzes-btn--back">
          ← CREATE YOUR OWN
        </Link>
      </div>
    </div>
  );
}
