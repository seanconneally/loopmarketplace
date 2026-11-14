import { fetchFeed, type FeedPage, type FeedQuery } from '../../api/client';

// A ranked snapshot contains at most 150 candidates, with four per opted-in page.
export async function findUnseenPage(
  filters: FeedQuery,
  known: ReadonlySet<string>,
  fetchPage: (query: FeedQuery, signal?: AbortSignal) => Promise<FeedPage> = (query, signal) =>
    fetchFeed(query, true, signal),
  signal: AbortSignal = AbortSignal.timeout(15000),
): Promise<FeedPage> {
  let cursor: string | undefined;
  let inspected = 0;
  const visited = new Set<string>();
  for (let pageNumber = 0; pageNumber < 40 && inspected < 150; pageNumber += 1) {
    signal.throwIfAborted();
    const page = await fetchPage({ ...filters, cursor }, signal);
    inspected += page.items.length;
    const items = page.items.filter((item) => !known.has(item.id));
    if (items.length || !page.next_cursor) return { ...page, items };
    if (visited.has(page.next_cursor))
      throw new Error('Could not refresh listings. Please try again.');
    visited.add(page.next_cursor);
    cursor = page.next_cursor;
  }
  return { items: [], next_cursor: null, ranking: 'refresh-limit' };
}
