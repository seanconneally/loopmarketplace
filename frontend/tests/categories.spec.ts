import { expect, test } from '@playwright/test';

test('mixed FYP includes uncategorised stock with only three category filters', async ({ page }) => {
  const result = await page.request.get('/api/v1/feed?sort=newest&q=Sample');
  expect(result.ok()).toBeTruthy();
  const items = (await result.json()).items;
  expect(items.some((item: { category: string }) => item.category === 'other')).toBeTruthy();
  expect((await page.request.get('/api/v1/feed?category=other')).status()).toBe(422);
  await page.goto('/');
  const tabs = page.getByRole('navigation', { name: 'Listing categories' });
  await expect(tabs.getByRole('button')).toHaveCount(4);
  await tabs.getByRole('button', { name: 'Homes', exact: true }).click();
  await expect(page).toHaveURL(/category=homes/);
  await expect(page.locator('.listing-panel')).toContainText('Bedrooms');
  await tabs.getByRole('button', { name: 'Golf clubs', exact: true }).click();
  await expect(page).toHaveURL(/category=golf/);
  await expect(page.locator('.listing-panel')).toContainText('Club type');
  await tabs.getByRole('button', { name: 'For you', exact: true }).click();
  expect(new URL(page.url()).searchParams.has('category')).toBe(false);
  const generic = items.find((item: { category: string }) => item.category === 'other');
  await page.goto(`/listings/${generic.id}`);
  await expect(page.locator('.listing-panel h2')).toHaveText(generic.title);
  await page.goto(`/cars/${generic.id}`); // Existing shared links keep working.
  await expect(page.locator('.listing-panel h2')).toHaveText(generic.title);
  await expect(page).toHaveTitle(/Loop Marketplace/);
});
