'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import PcaPlot from '@/components/PcaPlot';
import { colorForLabel } from '@/lib/colors';

async function copyTextToClipboard(text) {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // fall through to execCommand
    }
  }

  if (typeof document === 'undefined') return false;

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'absolute';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  try {
    return document.execCommand('copy');
  } catch {
    return false;
  } finally {
    document.body.removeChild(textarea);
  }
}

export default function ResultView({ result, title, quizId }) {
  const classColor = colorForLabel(result?.type);
  const closest = result?.closest_character;
  const [shareLabel, setShareLabel] = useState('Share');
  const resetTimerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
    };
  }, []);

  const handleShare = useCallback(async () => {
    if (!quizId) return;

    const url = `${window.location.origin}/quiz/${quizId}`;
    const copied = await copyTextToClipboard(url);

    if (resetTimerRef.current) clearTimeout(resetTimerRef.current);

    if (copied) {
      setShareLabel('Copied!');
      resetTimerRef.current = setTimeout(() => setShareLabel('Share'), 2000);
    } else {
      setShareLabel('Copy failed');
      resetTimerRef.current = setTimeout(() => setShareLabel('Share'), 2000);
    }
  }, [quizId]);

  const shareCopied = shareLabel === 'Copied!';

  return (
    <div className="container">
      <header>
        <div className="pixel-title">Your result</div>
        {title && <div className="subtitle">{title}</div>}
      </header>

      <div className="card result-card" style={{ borderTop: `5px solid ${classColor}` }}>
        <h2 className="result-type" style={{ color: classColor }}>
          You are a {result.type}
        </h2>

        {closest?.name && (
          <p className="result-desc">
            Most similar character: <strong>{closest.name}</strong>
          </p>
        )}

        {Array.isArray(result.ranking) && result.ranking.length > 0 && (
          <div className="ranking-list">
            <div className="famous-label">Class ranking (avg. similarity)</div>
            <ul className="ranking-items">
              {result.ranking.map((entry) => (
                <li key={entry.type} className="ranking-item">
                  <span style={{ color: colorForLabel(entry.type) }}>{entry.type}</span>
                  <span className="ranking-score">{entry.score.toFixed(3)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {quizId && (
          <button
            type="button"
            className={`share-btn${shareCopied ? ' share-btn--copied' : ''}`}
            aria-label="Copy quiz link"
            onClick={handleShare}
          >
            {shareLabel}
          </button>
        )}

        {result?.projection && (
          <PcaPlot projection={result.projection} userType={result.type} />
        )}
      </div>
    </div>
  );
}
