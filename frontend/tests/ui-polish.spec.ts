import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';

async function settled(page: Page) {
  await page.evaluate(() => document.fonts.ready);
  await expect.poll(() => page.locator('.page-content').evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
}
async function capture(page: Page, name: string) {
  await settled(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `../docs/screenshots/ui-${name}.png`, fullPage: true });
}
async function signIn(page: Page, phone: string) {
  await page.getByRole('button', { name: 'Sign in', exact: true }).first().click();
  await page.getByLabel('Phone number').fill(phone);
  await page.getByRole('button', { name: 'Continue with phone' }).click();
  await page.getByLabel('Verification code').fill('123456');
  await page.getByRole('button', { name: 'Verify & continue' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
}

test('visual system covers public, member, dealer and moderator pages', async ({ page, browser }) => {
  fs.mkdirSync('../docs/screenshots', { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1080 });
  await page.goto('/');
  await expect(page.locator('.listing-panel h2')).toBeVisible();
  await capture(page, 'discover-desktop');
  expect(await page.evaluate(() => document.fonts.check('700 14px Manrope'))).toBe(true);
  await page.getByRole('button', { name: 'Filters', exact: true }).click();
  await expect(page.locator('#discovery-filters')).toBeVisible();
  await capture(page, 'filters');
  await page.getByRole('button', { name: 'Filters', exact: true }).click();
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await capture(page, 'sign-in');
  await page.getByRole('button', { name: 'Close dialog' }).click();
  await page.goto('/saved');
  await expect(page.getByRole('heading', { name: 'Make yourself at home.' })).toBeVisible();
  await capture(page, 'signed-out');
  await page.goto('/safety');
  await capture(page, 'safety-desktop');
  await page.goto('/not-a-page');
  await expect(page.getByRole('heading', { name: 'Let’s get you back on track.' })).toBeVisible();
  await capture(page, 'not-found');
  await page.goto('/');
  await signIn(page, '+353860000001');
  await page.getByRole('link', { name: 'My cars', exact: true }).click();
  await expect(page.locator('.seller-overview')).toBeVisible();
  await capture(page, 'seller-desktop');
  await page.getByRole('button', { name: 'Add a car', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await capture(page, 'upload');
  await page.getByRole('button', { name: 'Close dialog' }).click();
  await page.getByRole('link', { name: 'Dealer studio', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Download template' })).toBeVisible();
  expect((await page.request.get('/dealer-template.csv')).status()).toBe(200);
  await capture(page, 'dealer-desktop');
  await page.getByRole('link', { name: 'Messages', exact: true }).first().click();
  await expect(page.locator('.chat-layout')).toBeVisible();
  await capture(page, 'inbox-desktop');
  await page.locator('.account-button').click();
  await expect(page.getByRole('dialog').getByRole('button', { name: 'Sign out', exact: true })).toBeVisible();
  await capture(page, 'profile');
  await page.getByRole('button', { name: 'Close dialog' }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('link', { name: 'Discover', exact: true }).last().click();
  await expect(page.locator('.listing-panel h2')).toBeVisible();
  await capture(page, 'discover-mobile');
  await page.getByRole('button', { name: 'Account', exact: true }).click();
  await page.getByRole('link', { name: 'Manage your adverts' }).click();
  await expect(page.locator('.seller-overview')).toBeVisible();
  await capture(page, 'seller-mobile');
  await page.goto('/dealer');
  await capture(page, 'dealer-mobile');
  await page.goto('/safety');
  await capture(page, 'safety-mobile');
  await page.goto('/messages');
  await capture(page, 'inbox-mobile');
  const adminContext = await browser.newContext({ viewport: { width: 1440, height: 1080 } });
  const admin = await adminContext.newPage();
  await admin.goto('/');
  await signIn(admin, '+353860000099');
  await admin.getByRole('link', { name: 'Review queue', exact: true }).click();
  await expect(admin.locator('.page-heading')).toContainText('A fair review.');
  await capture(admin, 'moderation-desktop');
  await admin.setViewportSize({ width: 390, height: 844 });
  await capture(admin, 'moderation-mobile');
  await adminContext.close();
  expect(errors).toEqual([]);
});
