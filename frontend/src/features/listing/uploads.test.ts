import { File as NativeFile } from 'node:buffer';
import { afterEach, expect, test, vi } from 'vitest';
import { request } from '../../api/client';
import { fingerprint, uploadVideo } from './uploads';

vi.mock('../../api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api/client')>()),
  request: vi.fn(),
}));
afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});
const file = () =>
  new NativeFile(['abcdefghijkl'], 'car.mp4', { type: 'video/mp4' }) as unknown as File;

test('resume sends only missing parts and completes the same generation', async () => {
  const api = vi.mocked(request);
  api
    .mockResolvedValueOnce({ media: { id: 'asset' } })
    .mockResolvedValueOnce({
      asset_id: 'asset',
      state: 'uploading',
      generation: 3,
      part_size: 4,
      part_urls: ['https://storage/1', 'https://storage/2', 'https://storage/3'],
      completed_parts: [{ part_number: 1, etag: 'saved' }],
    })
    .mockResolvedValueOnce({ status: 'processing' });
  const put = vi.fn().mockResolvedValue(new Response(null, { headers: { ETag: 'new' } }));
  vi.stubGlobal('fetch', put);
  await uploadVideo('listing', file(), vi.fn(), { waitForProcessing: false });
  expect(put.mock.calls.map((call) => call[0])).toEqual(['https://storage/2', 'https://storage/3']);
  expect(JSON.parse(api.mock.calls[2][1]?.body as string)).toEqual({
    generation: 3,
    parts: [
      { part_number: 1, etag: 'saved' },
      { part_number: 2, etag: 'new' },
      { part_number: 3, etag: 'new' },
    ],
  });
  expect(api.mock.calls.some(([url]) => url === '/listings')).toBe(false);
});

test('a different file rejected by resume never sends bytes to storage', async () => {
  vi.mocked(request)
    .mockResolvedValueOnce({ media: { id: 'asset' } })
    .mockRejectedValueOnce(new Error('Choose the original video'));
  const put = vi.fn();
  vi.stubGlobal('fetch', put);
  await expect(uploadVideo('listing', file(), vi.fn())).rejects.toThrow('original video');
  expect(put).not.toHaveBeenCalled();
});

test('fingerprints cover the full file and upload can be paused before allocating', async () => {
  expect(await fingerprint(file())).toBe(
    'd682ed4ca4d989c134ec94f1551e1ec580dd6d5a6ecde9f3d35e6e4a717fbde4',
  );
  const controller = new AbortController();
  controller.abort();
  await expect(
    uploadVideo('listing', file(), vi.fn(), { signal: controller.signal }),
  ).rejects.toBeDefined();
  expect(request).not.toHaveBeenCalled();
});
