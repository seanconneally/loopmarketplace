import { expect, test } from '@playwright/test';
import fs from 'node:fs';

test('private pages distinguish checking, unavailable and signed-out sessions', async ({ page }) => {
  let finish!: () => void;
  let requests = 0;
  await page.route('**/api/v1/auth/refresh', async route => {
    if (requests++ === 0) {
      await new Promise<void>(resolve => { finish = resolve; });
      return route.fulfill({status:503, contentType:'application/json', body:'{}'});
    }
    return route.fulfill({status:401, contentType:'application/json', body:'{}'});
  });
  await page.goto('/saved');
  await expect(page.getByRole('heading', {name:'Checking your session…'})).toBeVisible();
  await expect(page.getByRole('heading', {name:'Make yourself at home.'})).toHaveCount(0);
  finish();
  await expect(page.getByRole('heading', {name:'Your session is temporarily unavailable.'})).toBeVisible();
  await page.locator('.session-state').getByRole('button', {name:'Retry session'}).click();
  await expect(page.getByRole('heading', {name:'Make yourself at home.'})).toBeVisible();
});

test('a render failure keeps navigation and offers a working retry', async ({ page }) => {
  let broken = true;
  await page.route(url => url.pathname === '/api/v1/feed', route => broken ? route.fulfill({
    contentType:'application/json', body:JSON.stringify({items:[{id:'broken'}], next_cursor:null}),
  }) : route.continue());
  await page.goto('/');
  await expect(page.getByRole('heading', {name:'Something went wrong on this page.'})).toBeVisible();
  await expect(page.getByRole('navigation').last()).toBeVisible();
  broken = false;
  await page.getByRole('button', {name:'Try again'}).click();
  await expect(page.locator('.listing-panel h2')).toBeVisible();
});

test('mobile video controls, offline form recovery and constrained dialog viewport', async ({ page, context }, info) => {
  await page.goto('/');
  await expect(page.locator('.listing-panel h2')).toBeVisible();
  const video = page.locator('video').first();
  await expect(video).toHaveAttribute('playsinline', '');
  if (info.project.name === 'android-chromium') {
    await expect.poll(() => video.evaluate(element => (element as HTMLVideoElement).currentTime)).toBeGreaterThan(0);
    await page.getByRole('button', {name:'Pause video'}).first().click();
    await expect.poll(() => video.evaluate(element => (element as HTMLVideoElement).paused)).toBe(true);
    await page.getByRole('button', {name:'Play video'}).first().click();
    await expect.poll(() => video.evaluate(element => (element as HTMLVideoElement).paused)).toBe(false);
  } else {
    info.annotations.push({type:'hardware-needed', description:'WebKit on Windows does not certify HLS codec/autoplay/audio behaviour on an actual iPhone.'});
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.getByRole('button', {name:'Sign in', exact:true}).click();
  await page.getByLabel('Phone number').fill(`+35389${String(Date.now()).slice(-7)}`);
  await page.getByRole('button', {name:'Continue with phone'}).click();
  await page.getByLabel('Verification code').fill('123456');
  await page.getByLabel('Your name').fill('Mobile review member');
  await page.getByLabel(/I am 18/).check();
  await page.getByRole('button', {name:'Verify & continue'}).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('button', {name:'Account', exact:true}).click();
  await page.getByRole('dialog').getByRole('button', {name:'Close dialog'}).click();
  await page.locator('.mobile-nav').getByRole('button', {name:'Sell', exact:true}).click();
  await page.getByLabel('Listing video', { exact: true }).setInputFiles({name:'owned-walkaround.mov', mimeType:'video/quicktime', buffer:Buffer.from('selection only, not submitted')});
  await expect(page.getByRole('dialog')).toContainText('owned-walkaround.mov');
  await context.setOffline(true);
  await expect(page.getByText('You’re offline. Keep editing; reconnect before sending or uploading.')).toBeVisible();
  await page.getByLabel('Listing title').fill('Unfinished mobile advert');
  await page.getByLabel('Asking price (€)').fill('19950');
  await expect(page.getByRole('button', {name:'Upload & publish'})).toBeDisabled();
  await page.getByRole('button', {name:'Close dialog'}).click();
  await page.locator('.mobile-nav').getByRole('button', {name:'Sell', exact:true}).click();
  await expect(page.getByLabel('Listing title')).toHaveValue('Unfinished mobile advert');
  await expect(page.getByLabel('Asking price (€)')).toHaveValue('19950');
  await context.setOffline(false);
  await expect(page.getByRole('button', {name:'Upload & publish'})).toBeEnabled();
  // Synthetic viewport shrink exercises the keyboard accommodation code, not hardware.
  await page.evaluate(() => {
    if (visualViewport) {
      Object.defineProperty(visualViewport, 'height', {value:350, configurable:true});
      visualViewport.dispatchEvent(new Event('resize'));
    }
  });
  await expect.poll(async () => (await page.getByRole('dialog').boundingBox())?.height || 9999).toBeLessThanOrEqual(330);
  await expect(page.getByRole('button', {name:'Close dialog'})).toBeInViewport();
  fs.mkdirSync('../docs/screenshots', {recursive:true});
  await page.screenshot({path:`../docs/screenshots/recovery-${info.project.name}.png`});
  await page.getByRole('button', {name:'Close dialog'}).click();
});
