import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link, useLocation } from 'react-router-dom';
import {
  BadgeCheck,
  Bookmark,
  CalendarDays,
  ChevronRight,
  Flag,
  Fuel,
  Gauge,
  MapPin,
  MessageCircle,
  Settings2,
  ShieldCheck,
} from 'lucide-react';
import { euros, mutation, request, type Listing } from '../../api/client';
import { useAuth } from '../../shared/Auth';
import { Modal } from '../../shared/Modal';
import { ShareAdvert } from '../../shared/ShareAdvert';

export function ListingDetails({
  listing,
  onSave,
  onMessage,
  requireAuth,
  standalone = false,
  saving = false,
}: {
  listing: Listing;
  onSave: () => void;
  onMessage: () => void;
  requireAuth: () => void;
  standalone?: boolean;
  saving?: boolean;
}) {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const location = useLocation();
  const isOwner = auth.user?.id === listing.seller.id;
  const [report, setReport] = useState(false);
  const [reason, setReason] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  return (
    <aside className="listing-panel">
      <div className="panel-kicker">
        THE DETAILS <span>↗</span>
      </div>
      <div className="listing-title">
        <div>
          <h2>{listing.title}</h2>
          <p>
            {listing.car.year} · {listing.car.make} {listing.car.model}
          </p>
        </div>
        <button
          className={`icon-button ${listing.saved ? 'saved-icon' : ''}`}
          aria-label={listing.saved ? 'Unsave this car' : 'Save this car'}
          disabled={saving}
          onClick={onSave}
        >
          <Bookmark size={21} fill={listing.saved ? 'currentColor' : 'none'} />
        </button>
      </div>
      <div className="asking-price">
        {euros(listing.price_cents)}
        <span>Asking price</span>
      </div>
      {listing.status !== 'live' && (
        <p className="listing-availability" role="status">
          {listing.status === 'sold'
            ? 'This car has been sold.'
            : 'This advert is not currently live.'}
        </p>
      )}
      <div className="spec-grid">
        <div>
          <CalendarDays />
          <span>Year</span>
          <strong>{listing.car.year}</strong>
        </div>
        <div>
          <Gauge />
          <span>Mileage</span>
          <strong>{listing.car.mileage_km.toLocaleString()} km</strong>
        </div>
        <div>
          <Fuel />
          <span>Fuel type</span>
          <strong>{listing.car.fuel}</strong>
        </div>
        <div>
          <Settings2 />
          <span>Gearbox</span>
          <strong>{listing.car.transmission}</strong>
        </div>
      </div>
      <div className="seller-card">
        <div className="seller-avatar">{listing.seller.name.slice(0, 2).toUpperCase()}</div>
        <div>
          <strong>
            {listing.seller.name}
            {listing.seller.dealer_verified && <BadgeCheck size={16} />}
          </strong>
          <span>
            {listing.seller.dealer_verified ? 'Verified business seller' : 'Phone-verified member'}
          </span>
        </div>
      </div>
      <p className="listing-description">
        {listing.description ||
          'Get a proper look at your next car. Message the seller to ask a question or arrange a viewing.'}
      </p>
      <div className="location-line">
        <MapPin size={16} />
        <div>
          <strong>{listing.area}, Dublin</strong>
          <span>Approximate location</span>
        </div>
      </div>
      <button
        className="button dark message-cta"
        disabled={
          busy ||
          (!isOwner && listing.status !== 'live') ||
          (isOwner && !['live', 'paused'].includes(listing.status))
        }
        onClick={() => {
          if (!isOwner) {
            onMessage();
            return;
          }
          setBusy(true);
          void request(`/listings/${listing.id}/sold`, mutation({}))
            .then(() =>
              Promise.all(
                ['feed', 'saved', 'listing', 'seller-listings'].map((key) =>
                  queryClient.invalidateQueries({ queryKey: [key] }),
                ),
              ),
            )
            .catch((error: Error) => setFeedback(error.message))
            .finally(() => setBusy(false));
        }}
      >
        <MessageCircle size={19} />
        {busy
          ? 'Updating…'
          : listing.status === 'sold'
            ? 'Sold'
            : isOwner
              ? 'Mark as sold'
              : 'Message seller'}
        <ChevronRight size={18} />
      </button>
      <div className="listing-link-actions">
        <ShareAdvert id={listing.id} title={listing.title} />
        {!standalone && (
          <Link to={`/cars/${listing.id}`} state={{ from: location.pathname + location.search }}>
            Full advert <ChevronRight size={14} />
          </Link>
        )}
        {isOwner && (
          <Link to="/my-cars">
            Manage advert <ChevronRight size={14} />
          </Link>
        )}
      </div>
      <div className="safety-card">
        <div className="safety-icon">
          <ShieldCheck size={21} />
        </div>
        <div>
          <strong>A good deal starts with a safe viewing.</strong>
          <p>Meet in a busy public place. Inspect the car before paying. Never send a deposit.</p>
        </div>
      </div>
      <button
        className="text-button report-button"
        onClick={() => {
          if (!auth.user) requireAuth();
          else setReport(true);
        }}
      >
        <Flag size={13} />
        Report this listing
      </button>
      <div className="detail-footnote">
        A little more real.
        <br />
        <span>A lot more local.</span>
        <span className="mini-brand">m↗</span>
      </div>
      {report && (
        <Modal title="Report this listing" close={() => setReport(false)}>
          <form
            className="form-stack"
            onSubmit={(event) => {
              event.preventDefault();
              void request(
                '/moderation/reports',
                mutation({ target_type: 'listing', target_id: listing.id, reason }),
              )
                .then(() => {
                  setFeedback('Report submitted for review.');
                  setReport(false);
                })
                .catch((error: Error) => setFeedback(error.message));
            }}
          >
            <label>
              What’s wrong?
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                minLength={5}
                maxLength={1000}
                required
              />
            </label>
            <button className="button dark">Submit report</button>
          </form>
        </Modal>
      )}
      {feedback && (
        <p className="tiny" role="status">
          {feedback}
        </p>
      )}
    </aside>
  );
}
