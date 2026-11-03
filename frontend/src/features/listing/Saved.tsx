import { categoryLabel, listingSummary } from './categories';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowUpRight, Bookmark, Package, MessageCircle, X } from 'lucide-react';
import { euros, request, type Listing } from '../../api/client';
import { useAuth } from '../../shared/Auth';
import { PageHeading } from '../../shared/PageHeading';

type SavedPage = { items: Listing[]; next_cursor?: string | null };
export function Saved({ message }: { message: (listing: Listing) => void }) {
  const { user } = useAuth(),
    client = useQueryClient();
  const [busy, setBusy] = useState(''),
    [error, setError] = useState('');
  const query = useInfiniteQuery({
    queryKey: ['saved', user?.id],
    initialPageParam: '',
    queryFn: ({ pageParam }) =>
      request<SavedPage>(
        `/listings/saved${pageParam ? `?cursor=${encodeURIComponent(pageParam)}` : ''}`,
      ),
    getNextPageParam: (page) => page.next_cursor || undefined,
  });
  const items = [
    ...new Map(
      (query.data?.pages.flatMap((page) => page.items) || []).map((item) => [item.id, item]),
    ).values(),
  ];
  async function remove(item: Listing) {
    if (busy) return;
    setBusy(item.id);
    setError('');
    try {
      await request(`/listings/${item.id}/save`, { method: 'DELETE' });
      await Promise.all(
        ['saved', 'feed', 'listing'].map((key) => client.invalidateQueries({ queryKey: [key] })),
      );
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy('');
    }
  }
  return (
    <>
      <PageHeading
        eyebrow="SAVED FOR ANOTHER LOOK"
        title={
          <>
            Keep the <span>good ones close.</span>
          </>
        }
        description="Your favourite finds, ready when you are. Watch again or start a conversation."
        action={
          <span className="section-pill">
            <Bookmark size={16} />
            Your shortlist
          </span>
        }
      />
      {(error || query.error) && (
        <div className="notice error" role="alert">
          <p>{error || query.error?.message}</p>
          <button
            className="text-button"
            onClick={() => void client.resetQueries({ queryKey: ['saved'] })}
          >
            Refresh saved listings
          </button>
        </div>
      )}
      {query.isPending && <p role="status">Loading your saved listings…</p>}
      <div className="saved-grid">
        {items.map((item) => (
          <article className="saved-card shortlist-card" key={item.id} aria-label={item.title}>
            <div className="shortlist-cover">
              <Link
                to={`/listings/${item.id}`}
                state={{ from: '/saved' }}
                aria-label={`View ${item.title}`}
              >
                {item.poster_url ? <img src={item.poster_url} alt="" /> : <Package size={36} />}
              </Link>
              <span className={`shortlist-status ${item.status === 'sold' ? 'is-sold' : ''}`}>
                {item.status === 'sold' ? 'Sold' : item.status === 'live' ? 'Live' : 'Unavailable'}
              </span>
              <button
                className="icon-button"
                aria-label={`Remove ${item.title} from saved listings`}
                disabled={!!busy}
                onClick={() => void remove(item)}
              >
                <X size={15} />
              </button>
            </div>
            <div>
              <span className="eyebrow">
                {item.area} · {categoryLabel(item.category)}
              </span>
              <h2>
                <Link to={`/listings/${item.id}`} state={{ from: '/saved' }}>
                  {item.title}
                </Link>
              </h2>
              <p>{listingSummary(item)}</p>
              <strong>{euros(item.price_cents)}</strong>
              <Link
                className="button shortlist-view"
                to={`/listings/${item.id}`}
                state={{ from: '/saved' }}
              >
                View advert <ArrowUpRight size={15} />
              </Link>
              {item.seller.id === user?.id ? (
                <Link className="button dark" to="/my-listings">
                  Manage advert
                </Link>
              ) : (
                <button
                  className="button dark"
                  onClick={() => message(item)}
                  disabled={item.status !== 'live'}
                >
                  <MessageCircle size={15} />
                  {item.status === 'sold' ? 'This listing has sold' : 'Message seller'}
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
      {query.hasNextPage && (
        <button
          className="button dark seller-more"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          {query.isFetchingNextPage ? 'Loading…' : 'Load more saved listings'}
        </button>
      )}
      {!query.isPending && !query.error && !items.length && (
        <div className="empty-card">
          <Bookmark size={36} />
          <h2>Your shortlist is waiting.</h2>
          <p>Save a listing from Discover to find it here. Unavailable adverts stay hidden.</p>
          <Link className="button dark" to="/">
            Discover listings
          </Link>
        </div>
      )}
    </>
  );
}
