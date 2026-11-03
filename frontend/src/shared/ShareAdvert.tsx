import { useState } from 'react';
import { Check, Share2 } from 'lucide-react';

export function ShareAdvert({ id, title }: { id: string; title: string }) {
  const [copied, setCopied] = useState(false),
    [manual, setManual] = useState(false),
    [busy, setBusy] = useState(false);
  const url = `${location.origin}/listings/${id}`;
  async function share() {
    setBusy(true);
    setCopied(false);
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === 'AbortError')) setManual(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="advert-share">
      <button
        className="text-button"
        onClick={() => void share()}
        disabled={busy}
        aria-label="Share advert"
        title={`Copy a link to ${title}`}
      >
        {copied ? <Check size={15} /> : <Share2 size={15} />}
        {copied ? 'Link copied' : 'Share advert'}
      </button>
      {copied && (
        <span className="sr-only" role="status">
          Advert link copied to clipboard.
        </span>
      )}
      {manual && (
        <label className="share-manual">
          Copy this advert link
          <input
            aria-label="Advert link"
            readOnly
            value={url}
            onFocus={(event) => event.target.select()}
          />
        </label>
      )}
    </div>
  );
}
