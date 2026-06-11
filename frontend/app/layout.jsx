import './globals.css';
import { ApiProvider } from '@/components/ApiProvider';
import { normalizeBaseUrl } from '@/lib/apiBase';

export const metadata = {
  title: 'Personality Quiz',
  description: 'A personality quiz built from fictional class systems.',
  icons: {
    icon: '/favicon.svg',
  },
};

function getClassifierBaseUrl() {
  return normalizeBaseUrl(
    process.env.CLOUD_RUN_URI ||
      process.env.CLOUD_RUN_URL ||
      process.env.cloud_run_url ||
      process.env.NEXT_PUBLIC_API_URL ||
      null,
  );
}

export default function RootLayout({ children }) {
  const apiBaseUrl = getClassifierBaseUrl();
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Nunito:wght@400;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <ApiProvider apiBaseUrl={apiBaseUrl}>{children}</ApiProvider>
      </body>
    </html>
  );
}
