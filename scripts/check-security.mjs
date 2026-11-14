// Bounded, read-only gateway checks. Run with the local Compose app available.
import assert from 'node:assert/strict';
import { loadEnvFile } from 'node:process';

try {
  loadEnvFile();
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
const base = process.env.BASE_URL || process.env.PUBLIC_ORIGIN || `http://localhost:${process.env.WEB_PORT || 8080}`;
const get = (path, options = {}) => fetch(new URL(path, base), {
  redirect: 'manual', signal: AbortSignal.timeout(10000), ...options,
});
function headers(response, path) {
  assert.equal(response.headers.get('x-frame-options'), 'DENY', `${path}: framing`);
  assert.equal(response.headers.get('x-content-type-options'), 'nosniff', `${path}: MIME sniffing`);
  assert.match(response.headers.get('content-security-policy') || '', /frame-ancestors 'none'/);
  assert.match(response.headers.get('content-security-policy') || '', /base-uri 'none'/);
  assert.match(response.headers.get('content-security-policy') || '', /form-action 'self'/);
  assert.doesNotMatch(response.headers.get('server') || '', /\//, `${path}: server version`);
}

const home = await get('/');
assert.equal(home.status, 200);
headers(home, '/');
const html = await home.text();
const assets = [...html.matchAll(/(?:src|href)="(\/assets\/[^"?]+)"/g)].map(match => match[1]);
assert.ok(assets.length, 'Built application assets must exist');
for (const path of ['/sw.js', ...assets]) {
  const response = await get(path);
  assert.equal(response.status, 200, path);
  headers(response, path);
}
for (const path of ['/.git/config', '/.env', '/assets/.git/HEAD', '/assets/app.js.map', '/backup.sql', '/media/', '/media/?list-type=2']) {
  const response = await get(path);
  assert.equal(response.status, 404, path);
  headers(response, path);
}
const feed = await get('/api/v1/feed');
assert.equal(feed.status, 200);
headers(feed, '/api/v1/feed');
assert.equal(feed.headers.get('cache-control'), 'no-store');
const { items } = await feed.json();
const media = items.find(item => item.playback_url)?.playback_url;
assert.ok(media, 'A published video is needed to check playback');
const mediaPath = new URL(media).pathname;
const playlist = await get(mediaPath);
assert.equal(playlist.status, 200);
headers(playlist, mediaPath);
const rendition = (await playlist.text()).split('\n').find(line => line && !line.startsWith('#'));
assert.ok(rendition);
const renditionPath = new URL(rendition, new URL(mediaPath, base)).pathname;
const renditionResponse = await get(renditionPath);
assert.equal(renditionResponse.status, 200);
const segment = (await renditionResponse.text()).split('\n').find(line => line && !line.startsWith('#'));
assert.ok(segment);
const segmentPath = new URL(segment, new URL(renditionPath, base)).pathname;
const segmentResponse = await get(segmentPath);
assert.equal(segmentResponse.status, 200);
headers(segmentResponse, segmentPath);
assert.equal((await get(`${mediaPath}?acl`)).status, 404);
assert.equal((await get(mediaPath, { method: 'PUT', body: 'not a video' })).status, 403);
// This request must be rejected before it creates an OTP challenge.
const crossOrigin = await get('/api/v1/auth/otp/request', {
  method: 'POST',
  headers: { Origin: 'https://attacker.example', 'Content-Type': 'application/json' },
  body: JSON.stringify({ phone: '+353871234567' }),
});
assert.equal(crossOrigin.status, 403);
headers(crossOrigin, '/api/v1/auth/otp/request');
console.log(`Security checks passed: ${assets.length} assets, private paths, API, video playback and cross-origin OTP.`);
