import { loadEnvFile } from 'node:process';

try {
  loadEnvFile(new URL('../.env', import.meta.url));
} catch (error) {
  if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
}

export const baseURL =
  process.env.BASE_URL ||
  process.env.PUBLIC_ORIGIN ||
  `http://localhost:${process.env.WEB_PORT || 8080}`;
