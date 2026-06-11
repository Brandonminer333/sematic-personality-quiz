'use client';

import { useEffect, useState } from 'react';
import { clearLastError, getLastError } from '@/lib/session';

export default function ErrorPage() {
  const [message, setMessage] = useState(null);

  useEffect(() => {
    setMessage(getLastError());
    clearLastError();
  }, []);

  return (
    <div className="container">
      <header>
        <div className="pixel-title">Something went wrong</div>
      </header>
      <div className="intro-card">
        <p>{message || 'Sorry, there was an error processing your quiz.'}</p>
      </div>
    </div>
  );
}
