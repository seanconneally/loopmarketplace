import { useEffect, useRef, useState } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { ArrowDown, ArrowUp, RotateCw, SlidersHorizontal } from 'lucide-react';
import { fetchFeed, request, type Listing } from '../../api/client';
import { useAuth } from '../../shared/Auth';
import { Reel } from './Reel';
import { ListingDetails } from '../listing/ListingDetails';

export function Feed({
  requireAuth,
  message,
}: {
  requireAuth: () => void;
  message: (listing: Listing) => void;
}) {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [make, setMake] = useState('');
  const [price, setPrice] = useState('');
  const [radius, setRadius] = useState('50');
  const [year, setYear] = useState('1900');
  const [advanced, setAdvanced] = useState(false);
  const [active, setActive] = useState(0);
  const [notice, setNotice] = useState('');
  const scroll = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(650);
  const query = useInfiniteQuery({
    queryKey: ['feed', make, price, radius, year, auth.user?.id],
    initialPageParam: '',
    queryFn: ({ pageParam }) =>
      fetchFeed({
        radius_km: Number(radius),
        min_year: Number(year),
        make: make || undefined,
        max_price: price ? Number(price) * 100 : undefined,
        cursor: pageParam || undefined,
      }),
    getNextPageParam: (page) => page.next_cursor || undefined,
  });
  const listings = query.data?.pages.flatMap((page) => page.items) || [];
  const virtualizer = useVirtualizer({
    count: listings.length,
    getScrollElement: () => scroll.current,
    estimateSize: () => height,
    overscan: 2,
  });
  const current = listings[active] || listings[0];
  useEffect(() => {
    const element = scroll.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setHeight(element.clientHeight));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    virtualizer.measure();
  }, [height, virtualizer]);
  useEffect(() => {
    if (active >= listings.length - 3 && query.hasNextPage && !query.isFetchingNextPage)
      void query.fetchNextPage();
  }, [active, listings.length, query]);

  async function save(listing: Listing) {
    if (!auth.user) {
      requireAuth();
      return;
    }
    try {
      await request(`/listings/${listing.id}/save`, { method: listing.saved ? 'DELETE' : 'PUT' });
      await queryClient.invalidateQueries({ queryKey: ['feed'] });
      await queryClient.invalidateQueries({ queryKey: ['saved'] });
    } catch (problem) {
      setNotice((problem as Error).message);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">A NEW WAY TO FIND YOUR NEXT CAR</div>
          <h1>
            Less searching. <span>More seeing.</span>
          </h1>
          <p>Real cars. Short videos. Right around the corner.</p>
        </div>
        <div className="heading-stamp">
          <span className="live-dot" />
          DUBLIN, IRELAND
        </div>
      </div>
      <div className="filter-bar">
        <label className="filter-select">
          <span>Make</span>
          <select
            aria-label="Filter by make"
            value={make}
            onChange={(event) => {
              setMake(event.target.value);
              setActive(0);
            }}
          >
            <option value="">All makes</option>
            {['Volkswagen', 'BMW', 'Toyota'].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label className="filter-select">
          <span>Budget</span>
          <select
            aria-label="Maximum price"
            value={price}
            onChange={(event) => {
              setPrice(event.target.value);
              setActive(0);
            }}
          >
            <option value="">Any price</option>
            <option value="20000">Under €20,000</option>
            <option value="30000">Under €30,000</option>
            <option value="50000">Under €50,000</option>
          </select>
        </label>
        <label className="filter-select">
          <span>Distance</span>
          <select
            aria-label="Search radius"
            value={radius}
            onChange={(event) => {
              setRadius(event.target.value);
              setActive(0);
            }}
          >
            <option value="10">Within 10 km</option>
            <option value="25">Within 25 km</option>
            <option value="50">Within 50 km</option>
            <option value="100">Within 100 km</option>
          </select>
        </label>
        <button
          className={`filter-button ${advanced ? 'selected' : ''}`}
          onClick={() => setAdvanced(!advanced)}
        >
          <SlidersHorizontal size={16} />
          Filters
        </button>
      </div>
      {advanced && (
        <div className="advanced-filters">
          <label>
            From year
            <select
              aria-label="Minimum year"
              value={year}
              onChange={(event) => setYear(event.target.value)}
            >
              {['1900', '2015', '2018', '2020', '2023'].map((value) => (
                <option key={value} value={value}>
                  {value === '1900' ? 'Any year' : value}
                </option>
              ))}
            </select>
          </label>
          <p className="muted">
            Distances are measured from Dublin city centre. Exact seller locations stay private.
          </p>
        </div>
      )}
      {notice && (
        <p className="error" role="alert">
          {notice}
        </p>
      )}
      <div className="feed-layout">
        <div className="feed-column">
          <div className="feed-label">
            <span>
              <i /> THE LOCAL LOOP
            </span>
            <span>
              Scroll to discover <ArrowDown size={12} />
            </span>
          </div>
          <div className="feed-scroll" ref={scroll} aria-label="Video feed" tabIndex={0}>
            {query.isPending && (
              <div className="feed-empty">
                <div className="spinner" />
                <h2>Finding your next drive…</h2>
              </div>
            )}
            {query.isError && (
              <div className="feed-empty">
                <h2>Let’s try that again.</h2>
                <p>{query.error.message}</p>
                <button className="button primary" onClick={() => void query.refetch()}>
                  <RotateCw size={16} />
                  Retry
                </button>
              </div>
            )}
            {!query.isPending && !query.isError && !listings.length && (
              <div className="feed-empty">
                <h2>A little quiet around here.</h2>
                <p>Try a different make, budget or search distance.</p>
                <button
                  className="button primary"
                  onClick={() => {
                    setMake('');
                    setPrice('');
                    setYear('1900');
                    setRadius('50');
                  }}
                >
                  Reset filters
                </button>
              </div>
            )}
            <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
              {virtualizer.getVirtualItems().map((item) => (
                <div
                  key={listings[item.index].id}
                  className="reel-slot"
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height,
                    transform: `translateY(${item.start}px)`,
                  }}
                >
                  <Reel
                    listing={listings[item.index]}
                    nearby={item.index >= active && item.index <= active + 2}
                    onActive={() => setActive(item.index)}
                    onSave={() => void save(listings[item.index])}
                    onMessage={() => message(listings[item.index])}
                  />
                </div>
              ))}
            </div>
          </div>
          <div className="feed-footer">
            <span>See something you like? Start a conversation.</span>
            <div>
              <button
                className="icon-button"
                aria-label="Previous car"
                disabled={active === 0}
                onClick={() => virtualizer.scrollToIndex(active - 1, { align: 'start' })}
              >
                <ArrowUp size={17} />
              </button>
              <button
                className="icon-button"
                aria-label="Next car"
                disabled={active >= listings.length - 1}
                onClick={() => virtualizer.scrollToIndex(active + 1, { align: 'start' })}
              >
                <ArrowDown size={17} />
              </button>
            </div>
          </div>
        </div>
        {current && (
          <ListingDetails
            listing={current}
            onSave={() => void save(current)}
            onMessage={() => message(current)}
            requireAuth={requireAuth}
          />
        )}
      </div>
    </>
  );
}
