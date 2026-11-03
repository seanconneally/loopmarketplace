import { expect, test } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';

test.beforeAll(() => {
  const cwd = path.resolve('..');
  fs.mkdirSync('tests/fixtures', { recursive: true });
  fs.mkdirSync('../docs/screenshots', { recursive: true });
  execFileSync(
    'docker',
    ['compose', 'exec', '-T', 'api', 'python', 'scripts/make_test_video.py', '/tmp/walkaround.mp4'],
    { cwd, timeout: 60000 },
  );
  execFileSync(
    'docker',
    ['compose', 'cp', 'api:/tmp/walkaround.mp4', 'frontend/tests/fixtures/walkaround.mp4'],
    { cwd, timeout: 30000 },
  );
});

test('upload → feed → message → viewing', async ({ page, browser }) => {
  const sellerPhone = `+35385${String(Date.now()).slice(-7)}`;
  const title = `Playwright golf clubs ${Date.now()}`;
  await page.goto('/');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('Phone number').fill(sellerPhone);
  await page.getByRole('button', { name: /Continue with phone/ }).click();
  await page.getByLabel('Verification code').fill('123456');
  await page.getByLabel('Your name').fill('Playwright seller');
  await page.getByLabel(/I am 18/).check();
  await page.getByRole('button', { name: /Verify & continue/ }).click();
  await page.getByRole('button', { name: 'Sell something', exact: true }).click();
  await page.getByLabel('Listing video', { exact: true }).setInputFiles(path.resolve('tests/fixtures/walkaround.mp4'));
  await page.getByLabel('Listing title').fill(title);
  await page.getByRole('combobox', { name: 'Category', exact: true }).selectOption('golf');
  await page.getByLabel('Brand', { exact: true }).fill('Mizuno');
  await page.getByLabel('Club type').selectOption('irons');
  await page.getByLabel('Asking price (€)').fill('320');
  await page.getByLabel(/I have the right to use this video/).check();
  await page.getByRole('button', { name: 'Upload & publish' }).click();
  await expect(page.getByText('Your upload is saved. Processing is continuing in the background.')).toBeVisible({
    timeout: 150000,
  });
  await page.getByRole('button', { name: 'Back to the loop' }).click();
  await expect(page.locator('.listing-panel h2')).toHaveText(title);

  // A separate browser context has a separate cookie jar and becomes the buyer.
  const buyerContext = await browser.newContext();
  const buyer = await buyerContext.newPage();
  await buyer.goto('/');
  await buyer.getByRole('button', { name: 'Sign in', exact: true }).click();
  await buyer.getByLabel('Phone number').fill(`+35386${String(Date.now()).slice(-7)}`);
  await buyer.getByRole('button', { name: /Continue with phone/ }).click();
  await buyer.getByLabel('Verification code').fill('123456');
  await buyer.getByLabel('Your name').fill('Playwright buyer');
  await buyer.getByRole('button', { name: /Verify & continue/ }).click();
  await expect(buyer.locator('.listing-panel h2')).toHaveText(title);
  await buyer.locator('.message-cta').click();
  await buyer.getByLabel('Your message').fill('Can I see the clubs tomorrow?');
  await buyer.getByRole('button', { name: 'Send message' }).click();
  await expect(buyer.getByText('Can I see the clubs tomorrow?')).toBeVisible();
  await buyer.getByRole('button', { name: 'Propose a viewing' }).click();
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 16);
  await buyer.getByLabel('Date & time (your local timezone)').fill(tomorrow);
  await buyer.getByLabel('Public meeting place').fill('Dundrum shopping centre main entrance');
  await buyer.getByRole('button', { name: 'Send proposal' }).click();
  await expect(buyer.getByText('VIEWING · PROPOSED')).toBeVisible();

  await page.getByRole('link', { name: 'Messages', exact: true }).first().click();
  await page.getByRole('button', { name: /Playwright buyer/ }).click();
  await expect(page.getByText('Can I see the clubs tomorrow?')).toBeVisible();
  await page.getByRole('button', { name: 'Accept', exact: true }).click();
  await expect(page.getByText('VIEWING · ACCEPTED')).toBeVisible();
  await expect(buyer.getByText('VIEWING · ACCEPTED')).toBeVisible();
  await page.screenshot({ path: '../docs/screenshots/viewing-accepted.png', fullPage: true });
  await page.goto('/');
  await page.getByRole('button', { name: 'Mark as sold', exact: true }).click();
  await expect(page.locator('.listing-panel h2')).not.toHaveText(title);
  await buyerContext.close();
  const preview = await browser.newContext({ viewport: { width: 1440, height: 1080 } });
  const previewPage = await preview.newPage();
  await previewPage.goto('/');
  await expect(previewPage.locator('.listing-panel h2')).toBeVisible();
  await expect
    .poll(() =>
      previewPage
        .locator('video')
        .first()
        .evaluate((element) => (element as HTMLVideoElement).readyState),
    )
    .toBeGreaterThanOrEqual(2);
  await expect
    .poll(() =>
      previewPage
        .locator('video')
        .first()
        .evaluate((element) => (element as HTMLVideoElement).currentTime),
    )
    .toBeGreaterThan(0);
  await previewPage.screenshot({ path: '../docs/screenshots/desktop.png', fullPage: true });
  await previewPage.setViewportSize({ width: 390, height: 844 });
  // Responsive video sizing updates after the browser's ResizeObserver callback.
  await expect.poll(async () => {
    const priceBox = await previewPage.locator('.reel-price').first().boundingBox();
    const navigationBox = await previewPage.locator('.mobile-nav').boundingBox();
    return priceBox && navigationBox ? priceBox.y + priceBox.height - navigationBox.y : Infinity;
  }).toBeLessThanOrEqual(0);
  await previewPage.screenshot({ path: '../docs/screenshots/mobile.png', fullPage: true });
  await preview.close();
});
