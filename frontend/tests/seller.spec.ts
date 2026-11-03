import { expect, test, type Page } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';

const video = path.resolve('tests/fixtures/resumable.mp4');
test.beforeAll(() => {
  fs.mkdirSync('tests/fixtures', { recursive: true });
  fs.mkdirSync('../docs/screenshots', { recursive: true });
  execFileSync('docker', ['compose', 'exec', '-T', 'api', 'python', 'scripts/make_test_video.py', '/tmp/resumable.mp4', '--padding-mib', '17'], { cwd: path.resolve('..'), timeout: 60000 });
  execFileSync('docker', ['compose', 'cp', 'api:/tmp/resumable.mp4', 'frontend/tests/fixtures/resumable.mp4'], { cwd: path.resolve('..'), timeout: 30000 });
});

async function seller(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('Phone number').fill(`+35383${String(Date.now()).slice(-7)}`);
  await page.getByRole('button', { name: /Continue with phone/ }).click();
  await page.getByLabel('Verification code').fill('123456');
  await page.getByLabel('Your name').fill('Dashboard seller');
  await page.getByLabel(/I am 18/).check();
  await page.getByRole('button', { name: /Verify & continue/ }).click();
}
async function details(page: Page, title: string, file: string | { name: string; mimeType: string; buffer: Buffer }) {
  await page.getByRole('button', { name: 'Sell a car', exact: true }).click();
  await page.getByLabel('Car video').setInputFiles(file);
  await page.getByLabel('Listing title').fill(title);
  await page.getByLabel('Make', { exact: true }).fill('Toyota');
  await page.getByLabel('Model', { exact: true }).fill('Yaris');
  await page.getByLabel('Mileage (km)').fill('33000');
  await page.getByLabel('Asking price (€)').fill('18000');
  await page.getByLabel(/I own this video/).check();
}

test('lost draft response → interrupted parts → refresh → resume → edit → pause → resume', async ({ page }) => {
  await seller(page);
  const title = `Resumable car ${Date.now()}`;
  let loseDraftResponse = true;
  const creationKeys: string[] = [];
  await page.route('**/api/v1/listings', async route => {
    if (route.request().method() !== 'POST') return route.continue();
    creationKeys.push(route.request().headers()['idempotency-key']);
    if (loseDraftResponse) {
      loseDraftResponse = false;
      await route.fetch(); // The database commits, but the browser never receives the result.
      return route.abort('connectionreset');
    }
    return route.continue();
  });
  await details(page, title, video);
  await page.getByRole('button', { name: 'Upload & publish' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await page.reload();
  await expect(page.locator('.account-button')).toContainText('Dashboard seller');
  await page.getByRole('button', { name: 'Sell a car', exact: true }).click();
  await expect(page.getByLabel('Listing title')).toHaveValue(title);
  await page.getByLabel('Car video').setInputFiles(video);
  let interrupted = true;
  let firstPartRequests = 0;
  await page.route('http://localhost:9000/**', async route => {
    if (route.request().method() === 'PUT') {
      const number = new URL(route.request().url()).searchParams.get('partNumber');
      if (number === '1') firstPartRequests += 1;
      if (number !== '1' && interrupted) return route.abort('connectionreset');
    }
    return route.continue();
  });
  await page.getByRole('button', { name: 'Resume upload', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Your saved parts are safe', { timeout: 60000 });
  expect(creationKeys).toHaveLength(2);
  expect(creationKeys[0]).toBe(creationKeys[1]);
  expect(firstPartRequests).toBe(1);
  interrupted = false;
  await page.goto('/my-cars');
  const card = page.getByRole('article', { name: title, exact: true });
  await expect(card).toHaveCount(1);
  await card.getByRole('button', { name: 'Resume upload', exact: true }).click();
  const wrong = Buffer.from(fs.readFileSync(video)); wrong[wrong.length - 1] = 1;
  await page.getByLabel('Car video').setInputFiles({ name: 'resumable.mp4', mimeType: 'video/mp4', buffer: wrong });
  await page.getByRole('dialog').getByRole('button', { name: 'Resume upload', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Choose the original video');
  await page.getByLabel('Car video').setInputFiles(video);
  await page.getByRole('dialog').getByRole('button', { name: 'Resume upload', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 60000 });
  await expect(card.locator('.seller-status')).toHaveText('Live', { timeout: 150000 });
  await expect(card.getByText('Audio included')).toBeVisible();
  expect(firstPartRequests).toBe(1);
  await card.getByRole('button', { name: 'Edit details' }).click();
  await page.getByLabel('Asking price (€)').fill('16500');
  await page.getByLabel('A little about the car').fill('Price reduced. Full service history.');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(card.locator('.seller-price')).toHaveText('€16,500');
  await page.getByRole('link', { name: 'Discover', exact: true }).first().click();
  await expect(page.locator('.listing-panel h2')).toHaveText(title);
  await expect(page.locator('.asking-price')).toContainText('16,500');
  await expect(page.getByRole('button', { name: 'Unmute video' }).first()).toBeEnabled();
  await page.getByRole('button', { name: 'Unmute video' }).first().click();
  await expect(page.locator('video').first()).toHaveJSProperty('muted', false);
  await page.getByRole('link', { name: 'My cars', exact: true }).click();
  await card.getByRole('button', { name: 'Pause advert' }).click();
  await expect(card.locator('.seller-status')).toHaveText('Paused');
  await page.getByRole('link', { name: 'Discover', exact: true }).first().click();
  await expect(page.locator('.listing-panel h2')).not.toHaveText(title);
  await page.getByRole('link', { name: 'My cars', exact: true }).click();
  await card.getByRole('button', { name: 'Resume advert' }).click();
  await expect(card.locator('.seller-status')).toHaveText('Live');
  await page.screenshot({ path: '../docs/screenshots/seller-dashboard.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '../docs/screenshots/seller-mobile.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await card.getByRole('button', { name: 'Mark as sold' }).click();
  await expect(card.locator('.seller-status')).toHaveText('Sold');
});

test('failed processing can be retried from the retained source', async ({ page }) => {
  await seller(page);
  const title = `Failed video ${Date.now()}`;
  await details(page, title, { name: 'invalid.mp4', mimeType: 'video/mp4', buffer: Buffer.from('invalid video bytes') });
  await page.getByRole('button', { name: 'Upload & publish' }).click();
  await expect(page.getByRole('alert')).toContainText('Video processing failed', { timeout: 60000 });
  await page.getByRole('link', { name: 'Go to My cars' }).click();
  const card = page.getByRole('article', { name: title, exact: true });
  await expect(card.locator('.seller-status')).toHaveText('Needs attention');
  const retried = page.waitForResponse(response => response.url().endsWith('/retry'));
  await card.getByRole('button', { name: 'Retry processing' }).click();
  expect((await retried).status()).toBe(200);
  await expect(card.locator('.seller-status')).toHaveText('Needs attention', { timeout: 60000 });
  await expect(card.getByText(/could not read this video/)).toBeVisible();
  await expect(card).toHaveCount(1);
});
