import { sha256 } from '@noble/hashes/sha2.js';
import { mutation, request, type SellerListing, type UploadSession } from '../../api/client';

const wait = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    signal?.throwIfAborted();
    const abort = () => {
      clearTimeout(timer);
      reject(signal?.reason);
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', abort);
      resolve();
    }, ms);
    signal?.addEventListener('abort', abort, { once: true });
  });

export async function fingerprint(file: File, signal?: AbortSignal): Promise<string> {
  const hash = sha256.create();
  for (let offset = 0; offset < file.size; offset += 4 * 1024 * 1024) {
    signal?.throwIfAborted();
    hash.update(new Uint8Array(await file.slice(offset, offset + 4 * 1024 * 1024).arrayBuffer()));
    await wait(0, signal);
  }
  return Array.from(hash.digest(), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

export async function uploadVideo(
  listingId: string,
  file: File,
  update: (message: string) => void,
  options: {
    signal?: AbortSignal;
    restart?: boolean;
    waitForProcessing?: boolean;
    queued?: () => void;
    allocated?: () => void;
  } = {},
) {
  const { signal } = options;
  if (!file.size || file.size > 500 * 1024 * 1024) throw new Error('Choose a video up to 500 MB.');
  update('Checking your original video…');
  const digest = await fingerprint(file, signal);
  const owner = await request<SellerListing>(`/listings/${listingId}/owner`, { signal });
  const resume = (asset: string) =>
    request<UploadSession>(`/media/${asset}/resume`, {
      ...mutation({ file_sha256: digest, size: file.size }),
      signal,
    });
  let session: UploadSession;
  if (owner.media && !options.restart) {
    session = await resume(owner.media.id);
  } else {
    const body = {
      name: file.name,
      size: file.size,
      file_sha256: digest,
      restart: !!options.restart,
      content_type:
        file.type === 'video/quicktime' || file.name.toLowerCase().endsWith('.mov')
          ? 'video/quicktime'
          : 'video/mp4',
    };
    // Keep the allocation key stable if its response is lost.
    const key = options.restart ? crypto.randomUUID() : digest;
    const allocate = () =>
      request<UploadSession>(`/media/listings/${listingId}/upload`, {
        ...mutation(body, key),
        signal,
      });
    try {
      session = await allocate();
    } catch (problem) {
      signal?.throwIfAborted();
      await wait(500, signal);
      session = await allocate().catch(() => {
        throw problem;
      });
    }
  }
  const assetId = session.asset_id;
  options.allocated?.();
  let parts = new Map(session.completed_parts?.map((part) => [part.part_number, part.etag]));
  const showProgress = () => {
    const bytes = [...parts.keys()].reduce(
      (sum, number) =>
        sum + Math.min(session.part_size, file.size - (number - 1) * session.part_size),
      0,
    );
    update(
      `Uploading video · ${Math.round((bytes / file.size) * 100)}% · ${parts.size} parts saved`,
    );
  };
  if (session.state === 'uploading') {
    showProgress();
    for (let index = 0; index < session.part_urls.length; index += 1) {
      if (parts.has(index + 1)) continue;
      let saved = false;
      for (let attempt = 0; attempt < 3 && !saved; attempt += 1) {
        signal?.throwIfAborted();
        try {
          const response = await fetch(session.part_urls[index], {
            method: 'PUT',
            body: file.slice(index * session.part_size, (index + 1) * session.part_size),
            signal,
          });
          if (!response.ok) throw new Error('Storage connection interrupted.');
          const etag = response.headers.get('ETag');
          if (!etag) throw new Error('Storage did not return an upload receipt.');
          parts.set(index + 1, etag);
          saved = true;
        } catch {
          signal?.throwIfAborted();
          // Reconcile a lost PUT response and renew expired signed URLs before retrying.
          await wait(500 * (attempt + 1), signal);
          session = await resume(assetId);
          parts = new Map(session.completed_parts?.map((part) => [part.part_number, part.etag]));
          saved = parts.has(index + 1);
        }
      }
      if (!saved)
        throw new Error(
          'Upload interrupted. Your saved parts are safe. Resume here or in My cars with the original file.',
        );
      showProgress();
    }
    await request(`/media/${assetId}/complete`, {
      ...mutation({
        generation: session.generation,
        parts: [...parts]
          .sort(([a], [b]) => a - b)
          .map(([part_number, etag]) => ({ part_number, etag })),
      }),
      signal,
    });
  } else if (session.state === 'failed') {
    throw new Error(
      'Video processing failed. Open My cars to retry processing or replace the video.',
    );
  }
  options.queued?.();
  update('Making your video ready… You can close this window.');
  if (options.waitForProcessing === false) return 'processing';
  for (let attempt = 0; attempt < 150; attempt += 1) {
    signal?.throwIfAborted();
    const status = await request<{ status: string }>(`/media/${assetId}`, { signal });
    if (status.status === 'ready') return 'live';
    if (status.status === 'pending_review') return 'pending_review';
    if (status.status === 'failed')
      throw new Error(
        'Video processing failed. Open My cars to retry or replace it on this advert.',
      );
    await wait(2000, signal);
  }
  return 'processing';
}
