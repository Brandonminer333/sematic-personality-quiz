'use client';

import PcaPlot from '@/components/PcaPlot';
import { colorForLabel } from '@/lib/colors';

export default function ResultView({ result, title }) {
  const classColor = colorForLabel(result?.type);
  const closest = result?.closest_character;

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

        {result?.projection && (
          <PcaPlot projection={result.projection} userType={result.type} />
        )}
      </div>
    </div>
  );
}
