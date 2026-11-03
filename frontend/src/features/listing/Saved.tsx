import { useQuery } from '@tanstack/react-query';
import { Bookmark, MessageCircle } from 'lucide-react';
import { euros, request, type Listing } from '../../api/client';

export function Saved({ message }: { message: (listing: Listing) => void }) {
  const query = useQuery({
    queryKey: ['saved'],
    queryFn: () => request<{ items: Listing[] }>('/listings/saved'),
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">THE ONES THAT CAUGHT YOUR EYE</div>
          <h1>Your shortlist.</h1>
          <p>Good cars are worth a second look.</p>
        </div>
      </div>
      {query.error && <p className="error">{query.error.message}</p>}
      <div className="saved-grid">
        {query.data?.items.map((item) => (
          <article className="saved-card" key={item.id}>
            <img src={item.poster_url || ''} alt={item.title} />
            <div>
              <span className="eyebrow">
                {item.area} · {item.status}
              </span>
              <h2>{item.title}</h2>
              <p>
                {item.car.year} · {item.car.mileage_km.toLocaleString()} km
              </p>
              <strong>{euros(item.price_cents)}</strong>
              <button
                className="button dark"
                onClick={() => message(item)}
                disabled={item.status !== 'live'}
              >
                <MessageCircle size={16} />
                Message seller
              </button>
            </div>
          </article>
        ))}
      </div>
      {query.data?.items.length === 0 && (
        <div className="empty-card">
          <Bookmark size={36} />
          <h2>Make room for a few favourites.</h2>
          <p>Tap the bookmark on any car to save it here.</p>
        </div>
      )}
    </>
  );
}
