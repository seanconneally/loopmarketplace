import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, SearchX } from 'lucide-react';
import { request, type Listing } from '../../api/client';
import { useAuth } from '../../shared/Auth';
import { Reel } from '../feed/Reel';
import { ListingDetails } from './ListingDetails';

export function ListingPage({
  requireAuth,
  message,
}: {
  requireAuth: () => void;
  message: (listing: Listing) => void;
}) {
  const { id } = useParams(),
    auth = useAuth(),
    location = useLocation(),
    navigate = useNavigate(),
    client = useQueryClient();
  const [saving, setSaving] = useState(false),
    [error, setError] = useState('');
  const query = useQuery({
    queryKey: ['listing', id, auth.user?.id],
    queryFn: () => request<Listing>(`/listings/${id}`),
    retry: false,
    refetchInterval: (state) => (state.state.data?.status === 'live' ? 15000 : false),
  });
  const listing = query.data;
  const state = location.state as { from?: string } | null;
  const from = state?.from?.startsWith('/') && !state.from.startsWith('//') ? state.from : '/';
  useEffect(() => {
    if (!listing) return;
    const previous = document.title;
    document.title = `${listing.title} · Motorloop`;
    return () => {
      document.title = previous;
    };
  }, [listing]);
  async function save() {
    if (!listing || saving) return;
    if (!auth.user) {
      requireAuth();
      return;
    }
    setSaving(true);
    setError('');
    try {
      await request(`/listings/${listing.id}/save`, { method: listing.saved ? 'DELETE' : 'PUT' });
      await Promise.all(
        ['listing', 'feed', 'saved'].map((key) => client.invalidateQueries({ queryKey: [key] })),
      );
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setSaving(false);
    }
  }
  function chat() {
    if (!listing) return;
    if (listing.seller.id === auth.user?.id) navigate('/my-cars');
    else message(listing);
  }
  return (
    <section className="advert-page">
      <Link className="advert-back" to={from}>
        <ArrowLeft size={16} />
        {from.startsWith('/saved') ? 'Back to saved cars' : 'Back to discovery'}
      </Link>
      {query.isPending && (
        <div className="empty-card" role="status">
          <div className="spinner" />
          <h1>Opening your next drive…</h1>
        </div>
      )}
      {query.error && (
        <div className="empty-card">
          <SearchX size={36} />
          <h1>This advert isn’t available.</h1>
          <p>It may have been paused or removed, or you may not have access.</p>
          <p className="tiny">{query.error.message}</p>
          <Link className="button dark" to="/">
            Discover more cars
          </Link>
        </div>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {listing && !query.error && (
        <div className="advert-layout">
          <div className="advert-video">
            <Reel
              key={listing.id}
              listing={listing}
              nearby
              onActive={() => undefined}
              onSave={() => void save()}
              saving={saving}
              onMessage={chat}
            />
          </div>
          <ListingDetails
            key={listing.id}
            listing={listing}
            onSave={() => void save()}
            saving={saving}
            onMessage={chat}
            requireAuth={requireAuth}
            standalone
          />
        </div>
      )}
    </section>
  );
}
