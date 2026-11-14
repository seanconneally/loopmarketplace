import { defineConfig, devices } from '@playwright/test';
import { baseURL } from './playwright-base';

export default defineConfig({
  outputDir: './test-results-mobile',
  testDir: './tests',
  testMatch: ['mobile-readiness.spec.ts', 'feed-continuation.spec.ts'],
  workers: 1,
  timeout: 60000,
  expect: { timeout: 15000 },
  reporter: 'list',
  use: { baseURL, trace: 'retain-on-failure' },
  projects: [
    { name: 'android-chromium', use: { ...devices['Pixel 7'], browserName: 'chromium' } },
    { name: 'iphone-webkit', use: { ...devices['iPhone 13'], browserName: 'webkit' } },
  ],
});
