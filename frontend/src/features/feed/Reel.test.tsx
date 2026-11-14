import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import type { Listing } from '../../api/client';
import { Reel } from './Reel';

vi.mock('../../shared/Auth', () => ({ useAuth: () => ({ user: null }) }));
vi.mock('hls.js', () => ({ default: { isSupported: () => false } }));

const listing: Listing = {
  id: 'listing',
  title: 'Local reading chair',
  description: 'Oak frame',
  price_cents: 8500,
  currency: 'EUR',
  status: 'live',
  area: 'Dundrum',
  category: 'other',
  region_id: 'ie-dublin',
  attributes: {},
  saved: false,
  has_audio: true,
  playback_url: '/video.mp4',
  seller: { id: 'seller', name: 'Local seller', dealer_verified: false },
};

beforeEach(() => {
  vi.stubGlobal(
    'IntersectionObserver',
    class {
      constructor(private callback: IntersectionObserverCallback) {}
      observe() {
        this.callback(
          [{ isIntersecting: true }] as IntersectionObserverEntry[],
          this as unknown as IntersectionObserver,
        );
      }
      disconnect() {}
    },
  );
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined);
  vi.spyOn(HTMLMediaElement.prototype, 'load').mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function open(item = listing) {
  return render(
    <MemoryRouter>
      <Reel
        listing={item}
        nearby
        onActive={() => undefined}
        onSave={() => undefined}
        onMessage={() => undefined}
      />
    </MemoryRouter>,
  );
}

test('video buffering clears on readiness and a failed video can be retried', () => {
  open();
  const video = screen.getByLabelText('Video tour of Local reading chair');
  expect(screen.getByRole('status')).toHaveTextContent('Loading video');
  fireEvent.canPlay(video);
  expect(screen.queryByRole('status')).toBeNull();
  fireEvent.waiting(video);
  expect(screen.getByRole('status')).toHaveTextContent('Loading video');
  fireEvent.error(video);
  expect(screen.getByRole('status')).toHaveTextContent('Video unavailable');
  fireEvent.click(screen.getByRole('button', { name: 'Retry video' }));
  expect(screen.getByRole('status')).toHaveTextContent('Loading video');
  fireEvent.playing(video);
  expect(screen.queryByRole('status')).toBeNull();
  expect(screen.getByRole('button', { name: 'Message seller' })).toBeEnabled();
});

test('an advert without a video remains usable and never shows an indefinite spinner', () => {
  open({ ...listing, playback_url: null });
  expect(screen.getByRole('status')).toHaveTextContent('Video unavailable');
  expect(screen.queryByText('Loading video…')).toBeNull();
  expect(screen.queryByRole('button', { name: 'Retry video' })).toBeNull();
  expect(screen.getByRole('button', { name: 'Save listing' })).toBeEnabled();
});
