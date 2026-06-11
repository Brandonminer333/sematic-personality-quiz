import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    externalDir: true,
  },
  turbopack: {
    resolveAlias: {
      '@shared': path.join(__dirname, '../shared'),
    },
  },
  webpack: (config) => {
    config.resolve.alias['@shared'] = path.join(__dirname, '../shared');
    return config;
  },
};

export default nextConfig;
