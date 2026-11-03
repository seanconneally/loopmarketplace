import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { onlineManager, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Chat } from './Chat';

vi.mock('../../shared/Auth', () => ({ useAuth: () => ({ user: { id: 'buyer' } }) }));
const clients: QueryClient[] = [];
afterEach(() => {
  cleanup();
  sessionStorage.clear();
  clients.forEach((client) => client.clear());
  clients.length = 0;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  onlineManager.setOnline(true);
});
const conversation = (id: string) => ({
  id,
  buyer_id: 'buyer',
  seller_id: 'seller',
  other_name: `Seller ${id}`,
  listing_title: `Car ${id}`,
});
const message = (id: string, body: string) => ({
  id,
  body,
  sender_id: 'buyer',
  conversation_id: 'a',
  warnings: [],
  created_at: '2026-11-03T10:00:00Z',
  read_at: null,
  message_type: 'text',
});
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  clients.push(client);
  render(
    <QueryClientProvider client={client}>
      <Chat />
    </QueryClientProvider>,
  );
}

test('older inbox pages and messages remain reachable and drafts stay with their conversation', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.endsWith('/conversations'))
        return Response.json({ items: [conversation('a')], next_cursor: 'next-conversations' });
      if (url.includes('next-conversations'))
        return Response.json({ items: [conversation('b')], next_cursor: null });
      if (url.includes('/messages?cursor='))
        return Response.json({ items: [message('old', 'Older message')], next_cursor: null });
      if (url.includes('/messages'))
        return Response.json({ items: [message('new', 'Latest message')], next_cursor: 'older' });
      if (url.includes('/viewings')) return Response.json({ items: [], next_cursor: null });
      throw new Error(`Unexpected request ${url}`);
    }),
  );
  mount();
  fireEvent.click(await screen.findByRole('button', { name: /Seller a/ }));
  expect(await screen.findByText('Latest message')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Load older messages' }));
  expect(await screen.findByText('Older message')).toBeInTheDocument();
  expect(screen.getByText('Latest message')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Your message'), { target: { value: 'Draft for car a' } });
  fireEvent.click(screen.getByRole('button', { name: 'More conversations' }));
  fireEvent.click(await screen.findByRole('button', { name: /Seller b/ }));
  expect(screen.getByLabelText('Your message')).toHaveValue('');
  fireEvent.change(screen.getByLabelText('Your message'), { target: { value: 'Draft for car b' } });
  fireEvent.click(screen.getByRole('button', { name: /Seller a/ }));
  expect(screen.getByLabelText('Your message')).toHaveValue('Draft for car a');
});

test('retrying a message after a lost response reuses its operation key', async () => {
  const keys: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, options: RequestInit) => {
      if (options.method === 'POST') {
        keys.push(new Headers(options.headers).get('Idempotency-Key')!);
        if (keys.length === 1) throw new TypeError('Connection lost after server accepted message');
        return Response.json(message('saved-once', 'Can I view it?'));
      }
      return Response.json({
        items: url.endsWith('/conversations') ? [conversation('a')] : [],
        next_cursor: null,
      });
    }),
  );
  mount();
  fireEvent.click(await screen.findByRole('button', { name: /Seller a/ }));
  fireEvent.change(screen.getByLabelText('Your message'), { target: { value: 'Can I view it?' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
  await screen.findByText('Couldn’t reach Motorloop. Check your connection and try again.');
  expect(screen.getByLabelText('Your message')).toHaveValue('Can I view it?');
  cleanup();
  mount();
  fireEvent.click(await screen.findByRole('button', { name: /Seller a/ }));
  expect(screen.getByLabelText('Your message')).toHaveValue('Can I view it?');
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send message' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
  await waitFor(() => expect(screen.getByLabelText('Your message')).toHaveValue(''));
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
});

test('retrying a viewing proposal after a lost response keeps the same operation key', async () => {
  const keys: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, options: RequestInit) => {
      if (options.method === 'POST') {
        keys.push(new Headers(options.headers).get('Idempotency-Key')!);
        if (keys.length === 1) throw new TypeError('Viewing response lost');
        return Response.json({ id: 'viewing' });
      }
      return Response.json({
        items: url.endsWith('/conversations') ? [conversation('a')] : [],
        next_cursor: null,
      });
    }),
  );
  mount();
  fireEvent.click(await screen.findByRole('button', { name: /Seller a/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Propose a viewing' }));
  fireEvent.change(screen.getByLabelText('Date & time (your local timezone)'), {
    target: { value: '2027-01-03T10:00' },
  });
  fireEvent.change(screen.getByLabelText('Public meeting place'), {
    target: { value: 'Dundrum main entrance' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Send proposal' }));
  await screen.findByText('Couldn’t reach Motorloop. Check your connection and try again.');
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send proposal' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Send proposal' }));
  await waitFor(() =>
    expect(screen.queryByRole('button', { name: 'Send proposal' })).not.toBeInTheDocument(),
  );
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
});

test('offline drafts survive reopening the inbox and are never sent automatically', async () => {
  let online = true;
  vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online);
  const fetcher = vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method) throw new Error('No automatic writes expected');
    return Response.json({
      items: url.endsWith('/conversations') ? [conversation('a')] : [],
      next_cursor: null,
    });
  });
  vi.stubGlobal('fetch', fetcher);
  mount();
  fireEvent.click(await screen.findByRole('button', { name: /Seller a/ }));
  online = false;
  fireEvent(window, new Event('offline'));
  fireEvent.change(screen.getByLabelText('Your message'), {
    target: { value: 'Keep this unfinished message' },
  });
  expect(screen.getByRole('button', { name: 'Send message' })).toBeDisabled();
  cleanup();
  online = true;
  mount();
  fireEvent(window, new Event('online'));
  fireEvent.click(await screen.findByRole('button', { name: /Seller a/ }));
  expect(screen.getByLabelText('Your message')).toHaveValue('Keep this unfinished message');
  online = true;
  fireEvent(window, new Event('online'));
  expect(screen.getByRole('button', { name: 'Send message' })).toBeEnabled();
  expect(
    fetcher.mock.calls.every((call) => call.length === 1 || !('method' in (call[1] || {}))),
  ).toBe(true);
});
