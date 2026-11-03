import { afterEach, expect, test, vi } from 'vitest';
import { request, restoreSession, setToken } from './client';

afterEach(() => {
  setToken(null);
  vi.unstubAllGlobals();
});

test('a delayed refresh cannot replace a newer sign-in or resurrect a signed-out token', async () => {
  for (const replacement of ['new-login', null]) {
    let finish!: (response: Response) => void;
    const fetcher = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            finish = resolve;
          }),
      )
      .mockResolvedValueOnce(Response.json({ ok: true }));
    vi.stubGlobal('fetch', fetcher);
    setToken('old');
    const restoring = restoreSession();
    setToken(replacement);
    finish(Response.json({ access_token: 'stale-refresh', user: {} }));
    expect(await restoring).toBeNull();
    await request('/users/me');
    expect(new Headers(fetcher.mock.calls[1][1].headers).get('Authorization')).toBe(
      replacement ? `Bearer ${replacement}` : null,
    );
  }
});

test('parallel expired requests share one refresh and preserve mutation idempotency keys', async () => {
  let refreshes = 0;
  const keys: string[] = [];
  const fetcher = vi.fn(async (url: string, options: RequestInit) => {
    if (url.endsWith('/refresh')) {
      refreshes++;
      await Promise.resolve();
      return Response.json({ access_token: 'renewed', user: {} });
    }
    keys.push(new Headers(options.headers).get('Idempotency-Key')!);
    if (new Headers(options.headers).get('Authorization') === 'Bearer expired')
      return new Response('{}', { status: 401 });
    return Response.json({ ok: true });
  });
  vi.stubGlobal('fetch', fetcher);
  setToken('expired');
  const options = { method: 'POST', body: '{}', headers: { 'Idempotency-Key': 'one-operation' } };
  await Promise.all([request('/one', options), request('/two', options)]);
  expect(refreshes).toBe(1);
  expect(keys).toEqual(Array(4).fill('one-operation'));
});

test('late 401 responses reuse an already renewed token without rotating the cookie again', async () => {
  let late!: (response: Response) => void;
  let refreshes = 0;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, options: RequestInit) => {
      if (url.endsWith('/refresh')) {
        refreshes++;
        return Response.json({ access_token: 'new', user: {} });
      }
      if (new Headers(options.headers).get('Authorization') === 'Bearer old') {
        if (url.endsWith('/late'))
          return new Promise<Response>((resolve) => {
            late = resolve;
          });
        return new Response('{}', { status: 401 });
      }
      return Response.json({ ok: true });
    }),
  );
  setToken('old');
  const pending = request('/late');
  await request('/first');
  late(new Response('{}', { status: 401 }));
  expect(await pending).toEqual({ ok: true });
  expect(refreshes).toBe(1);
});
