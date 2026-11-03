// Bounded, read-only local concurrency smoke check. Node 22+; no packages required.
const base = new URL(process.env.BASE_URL || 'http://localhost:8080');
const count = Number(process.env.REQUESTS || 200);
const concurrency = Number(process.env.CONCURRENCY || 10);
const targetRps = Number(process.env.TARGET_RPS || 10);
if (!Number.isInteger(count) || count < 1 || count > 10000 ||
    !Number.isInteger(concurrency) || concurrency < 1 || concurrency > 100 ||
    !Number.isFinite(targetRps) || targetRps < 1 || targetRps > 10000) {
  throw new Error('REQUESTS must be 1–10000; CONCURRENCY 1–100; TARGET_RPS 1–10000.');
}
const seed = await fetch(new URL('/api/v1/feed', base), { signal: AbortSignal.timeout(10000) });
if (!seed.ok) throw new Error(`Feed preparation failed: ${seed.status}`);
const first = (await seed.json()).items?.[0]?.id;
const paths = ['/api/v1/feed', '/api/v1/feed/options', '/api/v1/feed?sort=newest',
  ...(first ? [`/api/v1/listings/${encodeURIComponent(first)}`] : [])];
let next = 0;
const results = [];
const start = performance.now();
await Promise.all(Array.from({ length: Math.min(count, concurrency) }, async () => {
  while (next < count) {
    const index = next++;
    const path = paths[index % paths.length];
    // Pace below the development gateway's 20 requests/second per-IP limit.
    await new Promise(resolve => setTimeout(resolve, Math.max(0, start + index * 1000 / targetRps - performance.now())));
    const begun = performance.now();
    try {
      const response = await fetch(new URL(path, base), { signal: AbortSignal.timeout(10000) });
      const body = await response.json();
      results.push({ path, ms: performance.now() - begun, ok: response.ok && !body.error, status: response.status });
    } catch (error) {
      results.push({ path, ms: performance.now() - begun, ok: false, status: error.name });
    }
  }
}));
const elapsed = performance.now() - start;
const durations = results.map(result => result.ms).sort((a, b) => a - b);
const percentile = value => Math.round(durations[Math.max(0, Math.ceil(durations.length * value) - 1)]);
const failures = results.filter(result => !result.ok);
console.log(JSON.stringify({ base: base.origin, requests: results.length, concurrency,
  target_requests_per_second: targetRps,
  failures: failures.length, elapsed_ms: Math.round(elapsed),
  requests_per_second: Math.round(count / elapsed * 1000),
  latency_ms: { p50: percentile(0.5), p95: percentile(0.95), max: percentile(1) },
  ...(failures.length ? { errors: failures.slice(0, 10) } : {}),
  scope: 'Local read smoke check with sample inventory; not a production capacity certification.' }, null, 2));
if (failures.length) process.exitCode = 1;
