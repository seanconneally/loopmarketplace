import { expect, test } from '@playwright/test';

// Keep intentionally intercepted feed responses outside the service-worker path.
test.use({ serviceWorkers: 'block' });

test('end of feed preserves old listings, checks beyond repeats and appends new adverts', async ({
  page,
}) => {
  const response = await page.request.get('/api/v1/feed');
  expect(response.status()).toBe(200);
  const original = (await response.json()).items[0];
  const fresh = {
    ...original,
    id: '00000000-0000-4000-8000-000000000123',
    title: 'Demo · Newly published advert',
  };
  let freshAvailable = false;
  let repeatedPageChecks = 0;
  await page.route(
    (url) => url.pathname === '/api/v1/feed',
    async (route) => {
      const continuation = new URL(route.request().url()).searchParams.get('cursor');
      if (freshAvailable && continuation === 'fresh-cursor') {
        repeatedPageChecks += 1;
        return route.fulfill({ json: { items: [fresh], next_cursor: null } });
      }
      return route.fulfill({
        json: { items: [original], next_cursor: freshAvailable ? 'fresh-cursor' : null },
      });
    },
  );
  await page.goto('/');
  const end = page.getByRole('region', { name: 'End of listings' });
  await expect(end).toBeVisible();
  const originalTitle = await page.locator('.listing-panel h2').innerText();
  await end.getByRole('button', { name: 'Check for new listings' }).click();
  await expect(
    page.getByText('No new matches in the latest set. Your current listings are still here.'),
  ).toBeVisible();
  await expect(page.locator('.listing-panel h2')).toHaveText(originalTitle);
  freshAvailable = true;
  await end.getByRole('button', { name: 'Check for new listings' }).click();
  await expect(page.locator('.listing-panel h2')).toHaveText(fresh.title);
  expect(repeatedPageChecks).toBe(1);
  await expect(page.getByRole('button', { name: 'Previous listing' })).toBeEnabled();
  await page.getByRole('button', { name: 'Previous listing' }).click();
  await expect(page.locator('.listing-panel h2')).toHaveText(originalTitle);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
