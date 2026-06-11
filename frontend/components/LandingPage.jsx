'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createQuiz } from '@/lib/api';
import { useApiBase } from '@/components/ApiProvider';
import { clearAllQuizSessions, setLastError, setQuizMeta } from '@/lib/session';

const MAX_PROMPT_LENGTH = 255;

export default function LandingPage() {
  const router = useRouter();
  const apiBase = useApiBase();
  const [promptLength, setPromptLength] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    clearAllQuizSessions();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;

    const formData = new FormData(e.currentTarget);
    const trimmed = String(formData.get('prompt') ?? '').trim();
    if (!trimmed) return;

    setSubmitting(true);
    try {
      const created = await createQuiz(apiBase, trimmed);
      setQuizMeta(created.quiz_id, {
        title: created.title,
        classes: created.classes,
      });
      router.push(`/creating/${created.quiz_id}`);
    } catch (err) {
      setLastError(err?.message || 'create quiz failed');
      router.push('/error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container">
      <header>
        <div className="pixel-title">Personality Quiz</div>
        <div className="subtitle">Describe a fictional class system to begin</div>
      </header>

      <form className="intro-card" onSubmit={handleSubmit}>
        <p>
          Tell us about a franchise with distinct classes, houses, types, or factions.
          We&apos;ll build a quiz from canon characters.
        </p>
        <label className="prompt-label" htmlFor="quiz-prompt">
          Your prompt
        </label>
        <textarea
          id="quiz-prompt"
          name="prompt"
          className="prompt-input"
          maxLength={MAX_PROMPT_LENGTH}
          rows={4}
          defaultValue=""
          onInput={(e) => setPromptLength(e.currentTarget.value.length)}
          placeholder="e.g. Hogwarts houses from Harry Potter"
          disabled={submitting}
        />
        <div className="prompt-meta">
          {promptLength}/{MAX_PROMPT_LENGTH}
        </div>
        <button className="start-btn" type="submit" disabled={submitting}>
          {submitting ? 'CREATING…' : 'CREATE QUIZ ▶'}
        </button>
      </form>
    </div>
  );
}
