'use client';

import { createContext, useContext } from 'react';
import { resolveApiBaseUrl } from '@/lib/apiBase';

const ApiContext = createContext('http://localhost:8080');

export function ApiProvider({ apiBaseUrl, children }) {
  const base = resolveApiBaseUrl(apiBaseUrl);
  return <ApiContext.Provider value={base}>{children}</ApiContext.Provider>;
}

export function useApiBase() {
  return useContext(ApiContext);
}
