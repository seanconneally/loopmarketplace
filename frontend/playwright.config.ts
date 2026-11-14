import { defineConfig, devices } from '@playwright/test';
import { baseURL } from './playwright-base';

export default defineConfig({
  testDir: './tests',
  testIgnore: '**/mobile-readiness.spec.ts',
  fullyParallel: false,
  workers: 1,
  timeout: 180000,
  expect: { timeout: 15000 },
  reporter: 'list',
  use: { baseURL, trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
