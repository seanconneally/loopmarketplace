import { expect, test, vi } from 'vitest';
import type { FeedPage, Listing } from '../../api/client';
import { findUnseenPage } from './refresh';

const page = (ids: string[], next_cursor: string | null = null): FeedPage => ({
  items: ids.map((id) => ({ id }) as Listing),
  next_cursor,
  ranking: 'interest-v2',
});

test('refresh skips previously loaded adverts and keeps the cursor after the first unseen page', async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(page(['a', 'b'], 'next'))
    .mockResolvedValueOnce(page(['b', 'c'], 'continue'));
  const result = await findUnseenPage({ category: 'cars' }, new Set(['a', 'b']), fetcher);
  expect(result.items.map((item) => item.id)).toEqual(['c']);
  expect(result.next_cursor).toBe('continue');
  expect(fetcher.mock.calls[1][0]).toEqual({ category: 'cars', cursor: 'next' });
});

test('a refresh with no new adverts ends without replaying the old set', async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(page(['a'], 'last'))
    .mockResolvedValueOnce(page(['b']));
  expect((await findUnseenPage({}, new Set(['a', 'b']), fetcher)).items).toEqual([]);
  expect(fetcher).toHaveBeenCalledTimes(2);
});

test('refresh has a bounded request budget and rejects repeated cursors', async () => {
  let counter = 0;
  const emptyPages = vi.fn(async () => page([], String(++counter)));
  await findUnseenPage({}, new Set(), emptyPages);
  expect(emptyPages).toHaveBeenCalledTimes(40);
  const cycle = vi.fn(async () => page(['known'], 'same'));
  await expect(findUnseenPage({}, new Set(['known']), cycle)).rejects.toThrow('Please try again');
  expect(cycle).toHaveBeenCalledTimes(2);
});

test('network failures remain actionable instead of claiming there are no new adverts', async () => {
  const fetcher = vi.fn().mockRejectedValue(new Error('Connection interrupted'));
  await expect(findUnseenPage({}, new Set(), fetcher)).rejects.toThrow('Connection interrupted');
});

test('an aborted refresh stops before requesting another page', async () => {
  const controller = new AbortController();
  controller.abort();
  const fetcher = vi.fn();
  await expect(findUnseenPage({}, new Set(), fetcher, controller.signal)).rejects.toThrow();
  expect(fetcher).not.toHaveBeenCalled();
});
