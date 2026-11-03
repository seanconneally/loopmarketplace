import { afterEach, expect, test, vi } from 'vitest';
import { request } from '../../api/client';
import { clearSignals, flushSignals, setSignalOwner, signal } from './signals';

vi.mock('../../api/client', () => ({
  request: vi.fn(),
  mutation: (body: unknown) => ({ body: JSON.stringify(body) }),
}));
afterEach(() => {
  setSignalOwner(null);
  vi.clearAllMocks();
});

test('failed receipts retain IDs for a retry, and reset drops queued history', async () => {
  setSignalOwner('alice');
  vi.mocked(request).mockRejectedValueOnce(new Error('offline')).mockResolvedValue(undefined);
  signal('alice', 'golf', 'completion', 1);
  await flushSignals();
  const first = vi.mocked(request).mock.calls[0][1]?.body;
  await flushSignals();
  expect(vi.mocked(request).mock.calls[1][1]?.body).toBe(first);
  signal('alice', 'car', 'completion', 1);
  clearSignals();
  await flushSignals();
  expect(request).toHaveBeenCalledTimes(2);
});

test('switching accounts drops queued receipts and rejects the old account sampler', async () => {
  setSignalOwner('alice');
  signal('alice', 'car', 'completion', 1);
  setSignalOwner('bob');
  signal('alice', 'car', 'replay', 1);
  await flushSignals();
  expect(request).not.toHaveBeenCalled();
  signal('bob', 'home', 'completion', 0.8);
  vi.mocked(request).mockResolvedValue(undefined);
  await flushSignals();
  expect(request).toHaveBeenCalledOnce();
  expect(vi.mocked(request).mock.calls[0][2]).toBe(false);
  expect(JSON.parse(String(vi.mocked(request).mock.calls[0][1]?.body)).events[0].listing_id).toBe(
    'home',
  );
});
