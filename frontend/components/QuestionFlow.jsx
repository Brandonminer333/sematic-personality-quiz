'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { answerOptions, quizQuestions } from '@/lib/questions';
import { setQuizAnswers } from '@/lib/session';

const letters = ['A', 'B', 'C', 'D', 'E'];

export default function QuestionFlow({ quizId, title, classes }) {
  const router = useRouter();
  const [currentQ, setCurrentQ] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [answers, setAnswers] = useState([]);

  const nextQuestion = () => {
    if (selectedOption === null) return;
    const newAnswers = [...answers, selectedOption];
    setAnswers(newAnswers);

    if (currentQ < quizQuestions.length - 1) {
      setCurrentQ(currentQ + 1);
      setSelectedOption(null);
      return;
    }

    setQuizAnswers(quizId, newAnswers);
    router.push(`/quiz/${quizId}/waiting`);
  };

  const progress = ((currentQ + 1) / quizQuestions.length) * 100;
  const classList = Array.isArray(classes) ? classes.join(' · ') : '';

  return (
    <div className="container">
      <header>
        <div className="pixel-title">Which {title} class are you?</div>
        {classList && <div className="subtitle">{classList}</div>}
      </header>

      <div className="progress-label">
        QUESTION {currentQ + 1} OF {quizQuestions.length}
      </div>
      <div className="progress-wrap">
        <div className="progress-bar" style={{ width: `${progress}%` }} />
      </div>

      <div className="card">
        <div className="question-number">
          Q.{String(currentQ + 1).padStart(2, '0')}
        </div>
        <div className="question-text">{quizQuestions[currentQ].text}</div>
        <div className="options">
          {answerOptions.map((opt, i) => (
            <button
              key={opt.text}
              type="button"
              className={`option-btn ${selectedOption === opt.value ? 'selected' : ''}`}
              onClick={() => setSelectedOption(opt.value)}
            >
              <span className="option-letter">{letters[i]}</span>
              {opt.text}
            </button>
          ))}
        </div>
        <button
          type="button"
          className={`next-btn ${selectedOption !== null ? 'visible' : ''}`}
          onClick={nextQuestion}
        >
          {currentQ === quizQuestions.length - 1
            ? 'SEE MY RESULT ▶'
            : 'NEXT QUESTION ▶'}
        </button>
      </div>
    </div>
  );
}
