import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { UploadCloud, CheckCircle2 } from 'lucide-react';
import { mutation, request, type Listing, type ListingInput } from '../../api/client';
import { Modal } from '../../shared/Modal';
import { useAuth } from '../../shared/Auth';
import { ListingFields } from './ListingFields';
import { listingDetails } from './listingForm';
import { uploadVideo } from './uploads';

type PendingDraft = {
  version: 1;
  key: string;
  data: ListingInput;
  listingId?: string;
  fileName: string;
};
function readPending(key: string): PendingDraft | null {
  try {
    const value = JSON.parse(localStorage.getItem(key) || 'null') as PendingDraft | null;
    return value?.version === 1 && value.key && value.data ? value : null;
  } catch {
    return null;
  }
}

export function Upload({ close, complete }: { close: () => void; complete: () => void }) {
  const { user } = useAuth();
  const storageKey = `motorloop.pending-advert.${user?.id}`;
  const [pending, setPending] = useState<PendingDraft | null>(() => readPending(storageKey));
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState('');
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy) return;
    setError('');
    let saved = pending;
    try {
      if (!saved) {
        saved = {
          version: 1,
          key: crypto.randomUUID(),
          data: listingDetails(event.currentTarget),
          fileName: file.name,
        };
        // Persist the exact body and key BEFORE creation, including when its response is lost.
        localStorage.setItem(storageKey, JSON.stringify(saved));
        setPending(saved);
      }
      setBusy(true);
      const abort = new AbortController();
      controller.current = abort;
      if (!saved.listingId) {
        setStatus('Saving your draft…');
        const listing = await request<Listing>('/listings', {
          ...mutation(saved.data, saved.key),
          signal: abort.signal,
        });
        saved = { ...saved, listingId: listing.id };
        localStorage.setItem(storageKey, JSON.stringify(saved));
        setPending(saved);
        complete();
      }
      const state = await uploadVideo(saved.listingId!, file, setStatus, {
        signal: abort.signal,
        queued: () => localStorage.removeItem(storageKey),
      });
      setResult(
        state === 'live'
          ? 'You’re in the loop. Your car is live!'
          : state === 'pending_review'
            ? 'Your video is ready and awaiting a safety review.'
            : 'Your upload is saved. Processing is continuing in the background.',
      );
      complete();
    } catch (problem) {
      setError(
        controller.current?.signal.aborted
          ? 'Upload paused. Resume with this file here or in My cars.'
          : (problem as Error).message,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title={pending ? 'Continue your saved advert.' : 'Give your car its moment.'}
      close={close}
    >
      {result ? (
        <div className="success-state">
          <CheckCircle2 size={42} />
          <h3>{result}</h3>
          <Link className="button primary" to="/my-cars" onClick={close}>
            Manage in My cars
          </Link>
          <button className="button dark" onClick={close}>
            Back to the loop
          </button>
        </div>
      ) : (
        <>
          <p className="muted">
            A quick walkaround says more than a hundred photos. Your video’s audio is preserved.
          </p>
          {pending && (
            <div className="notice">
              Your draft is saved. Choose {pending.fileName} to continue on the same advert. You can
              edit its details in My cars.
            </div>
          )}
          <form className="form-stack" onSubmit={(event) => void submit(event)}>
            <label className="upload-drop">
              <UploadCloud size={30} />
              <strong>{file?.name || 'Choose your walkaround video'}</strong>
              <span>15–60 seconds · MP4 or MOV · up to 500 MB</span>
              <input
                aria-label="Car video"
                type="file"
                accept="video/mp4,video/quicktime,.mov"
                required
                disabled={busy}
                onChange={(event) => {
                  setFile(event.target.files?.[0] || null);
                  setError('');
                }}
              />
            </label>
            <ListingFields value={pending?.data} disabled={busy || !!pending} />
            <p className="tiny muted">
              You can close this window and resume later in My cars. After a refresh, select the
              original video again.
            </p>
            {status && (
              <p role="status" className="notice">
                {status}
              </p>
            )}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button className="button primary" disabled={busy}>
              {busy ? 'Working on your video…' : pending ? 'Resume upload' : 'Upload & publish'}
            </button>
            {busy && (
              <button
                type="button"
                className="button dark"
                onClick={() => controller.current?.abort()}
              >
                Pause upload
              </button>
            )}
            {pending && !busy && (
              <button
                type="button"
                className="text-button"
                onClick={() => {
                  localStorage.removeItem(storageKey);
                  setPending(null);
                  setFile(null);
                  setStatus('');
                  setError('');
                }}
              >
                Start another advert
              </button>
            )}
            <Link to="/my-cars" onClick={close}>
              Go to My cars
            </Link>
          </form>
        </>
      )}
    </Modal>
  );
}
