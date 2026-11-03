import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import {
  CarFront,
  Check,
  Film,
  Pause,
  Pencil,
  Play,
  Plus,
  RotateCcw,
  UploadCloud,
  Volume2,
} from 'lucide-react';
import {
  euros,
  mutation,
  request,
  type SellerListing,
  type SellerListingPage,
} from '../../api/client';
import { useAuth } from '../../shared/Auth';
import { Modal } from '../../shared/Modal';
import { ListingFields } from './ListingFields';
import { listingDetails } from './listingForm';
import { uploadVideo } from './uploads';

const statuses = [
  'all',
  'draft',
  'processing',
  'pending_review',
  'live',
  'paused',
  'failed',
  'sold',
  'removed',
];
const labels: Record<string, string> = {
  all: 'All adverts',
  draft: 'Draft',
  processing: 'Processing video',
  pending_review: 'Safety review',
  live: 'Live',
  paused: 'Paused',
  failed: 'Needs attention',
  sold: 'Sold',
  removed: 'Removed',
};
const errors: Record<string, string> = {
  duration_limit: 'Use a video between 15 and 60 seconds.',
  invalid_video: 'We could not read this video. Try exporting it as an MP4.',
  file_mismatch: 'The uploaded video did not match the original. Replace it with the correct file.',
  processing_failed:
    'Processing could not finish. Retry using your saved original or replace the video.',
  missing_video: 'This file does not contain a video track.',
  invalid_container: 'Choose an MP4 or MOV video.',
};

export function SellerDashboard({ create }: { create: () => void }) {
  const { user } = useAuth();
  const client = useQueryClient();
  const [filter, setFilter] = useState('all');
  const [editing, setEditing] = useState<SellerListing | null>(null);
  const [video, setVideo] = useState<{ listing: SellerListing; restart: boolean } | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const retryKeys = useRef(new Map<string, string>());
  const query = useInfiniteQuery({
    queryKey: ['seller-listings', user?.id, filter],
    initialPageParam: '',
    queryFn: ({ pageParam }) =>
      request<SellerListingPage>(
        `/listings/mine?${new URLSearchParams({ ...(filter === 'all' ? {} : { status: filter }), ...(pageParam ? { cursor: pageParam } : {}) })}`,
      ),
    getNextPageParam: (page) => page.next_cursor || undefined,
    refetchInterval: (state) =>
      state.state.data?.pages.some((page) =>
        page.items.some((item) => item.status === 'processing'),
      )
        ? 3000
        : false,
  });
  const items = query.data?.pages.flatMap((page) => page.items) || [];
  async function refresh() {
    await Promise.all([
      client.invalidateQueries({ queryKey: ['seller-listings'] }),
      client.invalidateQueries({ queryKey: ['feed'] }),
      client.invalidateQueries({ queryKey: ['saved'] }),
    ]);
  }
  async function action(item: SellerListing, kind: 'pause' | 'resume' | 'sold' | 'retry' | 'edit') {
    setError('');
    setBusy(item.id);
    try {
      if (kind === 'edit') {
        setEditing(await request<SellerListing>(`/listings/${item.id}/owner`));
        return;
      }
      if (kind === 'retry' && item.media) {
        let key = retryKeys.current.get(item.media.id);
        if (!key) {
          key = crypto.randomUUID();
          retryKeys.current.set(item.media.id, key);
        }
        await request(`/media/${item.media.id}/retry`, mutation({}, key));
        retryKeys.current.delete(item.media.id);
      } else await request(`/listings/${item.id}/${kind}`, mutation({ revision: item.revision }));
      await refresh();
    } catch (problem) {
      setError((problem as Error).message);
      await refresh();
    } finally {
      setBusy('');
    }
  }
  return (
    <>
      <div className="page-heading seller-heading">
        <div>
          <div className="eyebrow">YOUR SELLER DASHBOARD</div>
          <h1>Your cars. Your next chapter.</h1>
          <p>Keep every advert moving, from first draft to keys handed over.</p>
        </div>
        <button className="button dark" onClick={create}>
          <Plus size={16} />
          Add a car
        </button>
      </div>
      <div className="seller-toolbar">
        <label>
          Show
          <select
            aria-label="Filter adverts"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          >
            {statuses.map((status) => (
              <option key={status} value={status}>
                {labels[status]}
              </option>
            ))}
          </select>
        </label>
        <button className="text-button" onClick={() => void refresh()}>
          <RotateCcw size={14} /> Refresh
        </button>
      </div>
      {(error || query.error) && (
        <p className="error notice" role="alert">
          {error || query.error?.message}
        </p>
      )}
      {query.isPending && <p role="status">Loading your cars…</p>}
      <div className="seller-grid">
        {items.map((item) => {
          const closed = ['sold', 'removed'].includes(item.status);
          const unfinished = ['draft', 'failed'].includes(item.status);
          return (
            <article className="seller-advert" key={item.id} aria-label={item.title}>
              <div className="seller-cover">
                {item.poster_url || item.media?.poster_url ? (
                  <img src={item.poster_url || item.media?.poster_url || ''} alt="" />
                ) : (
                  <CarFront size={46} />
                )}
                <span className={`seller-status status-${item.status}`}>
                  {labels[item.status] || item.status}
                </span>
                {item.media?.has_audio && (
                  <span className="seller-audio">
                    <Volume2 size={13} />
                    Audio included
                  </span>
                )}
              </div>
              <div className="seller-advert-body">
                <p className="eyebrow">
                  {item.area} · {item.car.year}
                </p>
                <h2>{item.title}</h2>
                <p className="muted">
                  {item.car.make} {item.car.model} · {item.car.mileage_km.toLocaleString()} km
                </p>
                <strong className="seller-price">{euros(item.price_cents)}</strong>
                <p className="seller-hint">
                  {item.status === 'draft'
                    ? item.media
                      ? 'Your upload is saved. Select the original file to continue.'
                      : 'Your details are saved. Add a walkaround to publish.'
                    : item.status === 'paused'
                      ? 'Hidden from discovery. Resume when you are ready.'
                      : item.status === 'processing'
                        ? 'Your video is processing. This page updates automatically.'
                        : item.status === 'pending_review'
                          ? 'Awaiting a safety review. Your advert will appear after approval.'
                          : item.status === 'failed'
                            ? errors[item.media?.error_code || ''] ||
                              'The video needs attention. Retry processing or choose a new file.'
                            : item.status === 'live'
                              ? 'Visible to buyers in the loop.'
                              : item.status === 'sold'
                                ? 'A new chapter, complete.'
                                : 'This advert has been removed.'}
                </p>
                <div className="seller-actions">
                  {!closed && (
                    <button
                      className="button seller-secondary"
                      disabled={busy === item.id}
                      onClick={() => void action(item, 'edit')}
                    >
                      <Pencil size={14} />
                      Edit details
                    </button>
                  )}
                  {item.status === 'live' && (
                    <button
                      className="button seller-secondary"
                      disabled={busy === item.id}
                      onClick={() => void action(item, 'pause')}
                    >
                      <Pause size={14} />
                      Pause advert
                    </button>
                  )}
                  {item.status === 'paused' && (
                    <button
                      className="button primary"
                      disabled={busy === item.id}
                      onClick={() => void action(item, 'resume')}
                    >
                      <Play size={14} />
                      Resume advert
                    </button>
                  )}
                  {['live', 'paused'].includes(item.status) && (
                    <button
                      className="text-button"
                      disabled={busy === item.id}
                      onClick={() => void action(item, 'sold')}
                    >
                      <Check size={14} />
                      Mark as sold
                    </button>
                  )}
                  {unfinished && item.media?.status === 'failed' && (
                    <button
                      className="button primary"
                      disabled={busy === item.id || item.media.retry_count >= 3}
                      onClick={() => void action(item, 'retry')}
                    >
                      <RotateCcw size={14} />
                      Retry processing
                    </button>
                  )}
                  {unfinished && (!item.media || item.media.status === 'uploading') && (
                    <button
                      className="button primary"
                      onClick={() => setVideo({ listing: item, restart: false })}
                    >
                      <UploadCloud size={14} />
                      {item.media ? 'Resume upload' : 'Add video'}
                    </button>
                  )}
                  {unfinished && item.media && (
                    <button
                      className="text-button"
                      onClick={() => setVideo({ listing: item, restart: true })}
                    >
                      Replace video
                    </button>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>
      {!query.isPending && !query.error && !items.length && (
        <div className="empty-card">
          <Film size={36} />
          <h2>
            {filter === 'all' ? 'Every journey starts with a draft.' : 'No adverts here yet.'}
          </h2>
          <p>
            {filter === 'all'
              ? 'Add your car and bring its story to the loop.'
              : 'Choose another status to see your cars.'}
          </p>
          {filter === 'all' && (
            <button className="button dark" onClick={create}>
              Add your first car
            </button>
          )}
        </div>
      )}
      {query.hasNextPage && (
        <button
          className="button dark seller-more"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          Load more adverts
        </button>
      )}
      {editing && (
        <EditAdvert
          listing={editing}
          close={() => setEditing(null)}
          saved={() => {
            setEditing(null);
            void refresh();
          }}
        />
      )}
      {video && (
        <VideoDialog
          listing={video.listing}
          restart={video.restart}
          close={() => {
            setVideo(null);
            void refresh();
          }}
          changed={() => void refresh()}
        />
      )}
    </>
  );
}

function EditAdvert({
  listing,
  close,
  saved,
}: {
  listing: SellerListing;
  close: () => void;
  saved: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const details = listingDetails(event.currentTarget, {
      ...listing,
      rights_confirmed: true,
      category: 'cars',
      region_id: 'ie-dublin',
    });
    try {
      await request(`/listings/${listing.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ ...details, revision: listing.revision }),
      });
      saved();
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="A fresh look for your advert." close={close}>
      <form className="form-stack" onSubmit={(event) => void submit(event)}>
        <p className="muted">
          Update the price, details or description. Changes are checked before publication.
        </p>
        <ListingFields
          value={{ ...listing, rights_confirmed: true, category: 'cars', region_id: 'ie-dublin' }}
          disabled={busy}
        />
        {error && (
          <p className="error" role="alert">
            {error} Close this window and reopen Edit details to load the latest version.
          </p>
        )}
        <button className="button primary" disabled={busy}>
          {busy ? 'Saving…' : 'Save changes'}
        </button>
      </form>
    </Modal>
  );
}

function VideoDialog({
  listing,
  restart,
  close,
  changed,
}: {
  listing: SellerListing;
  restart: boolean;
  close: () => void;
  changed: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [replace, setReplace] = useState(restart);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError('');
    controller.current = new AbortController();
    try {
      await uploadVideo(listing.id, file, setStatus, {
        restart: replace,
        signal: controller.current.signal,
        waitForProcessing: false,
        allocated: () => {
          setReplace(false);
          changed();
        },
        queued: () => {
          const key = `motorloop.pending-advert.${listing.seller.id}`;
          try {
            if (JSON.parse(localStorage.getItem(key) || 'null')?.listingId === listing.id)
              localStorage.removeItem(key);
          } catch {
            /* malformed local hint */
          }
        },
      });
      changed();
      close();
    } catch (problem) {
      setError(
        controller.current.signal.aborted
          ? 'Upload paused. Your saved parts are safe.'
          : (problem as Error).message,
      );
      changed();
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={restart ? 'A new video. The same advert.' : 'Continue your walkaround.'}
      close={close}
    >
      <p className="muted">
        {restart
          ? 'Replace the unfinished video on this advert. Previously uploaded parts will be discarded.'
          : `Choose ${listing.media?.original_filename || 'your MP4 or MOV'}. Saved parts will be skipped.`}{' '}
        Audio is preserved.
      </p>
      <form className="form-stack" onSubmit={(event) => void submit(event)}>
        <label className="upload-drop">
          <UploadCloud size={30} />
          <strong>{file?.name || 'Choose your video'}</strong>
          <span>15–60 seconds · MP4 or MOV · up to 500 MB</span>
          <input
            aria-label="Car video"
            type="file"
            accept="video/mp4,video/quicktime,.mov"
            required
            disabled={busy}
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </label>
        {status && (
          <p className="notice" role="status">
            {status}
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="button primary" disabled={busy}>
          {busy ? 'Uploading…' : replace ? 'Replace & upload' : 'Resume upload'}
        </button>
        {busy && (
          <button type="button" className="button dark" onClick={() => controller.current?.abort()}>
            Pause upload
          </button>
        )}
      </form>
    </Modal>
  );
}
