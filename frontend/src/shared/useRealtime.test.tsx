import { afterEach, expect, test, vi } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useRealtime } from './useRealtime';

vi.mock('../api/client', () => ({
  mutation: () => ({}),
  request: async () => ({ ticket: 'ticket' }),
}));

const sockets: TestSocket[] = [];
class TestSocket {
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  send = vi.fn();
  close = vi.fn(() => this.onclose?.());
  constructor() {
    sockets.push(this);
  }
}
afterEach(() => {
  cleanup();
  sockets.length = 0;
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

test('reconnect reloads durable state, detects a silent socket and cleans up pending retries', async () => {
  vi.useFakeTimers();
  vi.stubGlobal('WebSocket', TestSocket);
  const client = new QueryClient();
  const invalidate = vi.spyOn(client, 'invalidateQueries');
  const { unmount } = renderHook(() => useRealtime('member'), {
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  });
  await act(async () => {
    await Promise.resolve();
  });
  expect(sockets).toHaveLength(1);
  act(() => sockets[0].onopen?.());
  expect(sockets[0].send).toHaveBeenCalledWith(JSON.stringify({ ticket: 'ticket' }));
  for (const key of ['messages', 'viewings', 'conversations', 'feed', 'seller-listings', 'saved'])
    expect(invalidate).toHaveBeenCalledWith({ queryKey: [key] });
  invalidate.mockClear();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(45000);
  });
  expect(sockets[0].close).toHaveBeenCalledOnce();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1200);
  });
  expect(sockets).toHaveLength(2);
  act(() => sockets[1].onopen?.());
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['messages'] });
  invalidate.mockClear();
  act(() => sockets[1].onmessage?.({ data: JSON.stringify({ type: 'block.changed', data: {} }) }));
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['conversations'] });
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['saved'] });
  act(() => sockets[1].onclose?.());
  unmount();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60000);
  });
  expect(sockets).toHaveLength(2);
  client.clear();
});
