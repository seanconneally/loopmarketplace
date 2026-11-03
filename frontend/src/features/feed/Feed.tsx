import { flushSignals } from './signals';
import { categories } from '../listing/categories';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { ArrowDown, ArrowUp, RotateCw, Search, SlidersHorizontal, X } from 'lucide-react';
import { euros, fetchFeed, request, type Listing } from '../../api/client';
import { useAuth } from '../../shared/Auth';
import { Reel } from './Reel';
import { TuneFeed } from './TuneFeed';
import { ListingDetails } from '../listing/ListingDetails';
import { PageHeading } from '../../shared/PageHeading';
import {
  defaultFilters,
  feedQuery,
  readFilters,
  searchParams,
  sortLabels,
  type DiscoveryFilters,
} from './search';

type Props = { requireAuth: () => void; message: (listing: Listing) => void };
export function Feed(props: Props) {
  const [params, setParams] = useSearchParams();
  const filters = readFilters(params);
  const [advanced, setAdvanced] = useState(false);
  const [error, setError] = useState('');
  const options = useQuery({
    queryKey: ['feed-options'],
    queryFn: () => request<{ makes: string[] }>('/feed/options'),
    staleTime: 30000,
  });
  const makes = [
    ...new Set([...(options.data?.makes || []), ...(filters.make ? [filters.make] : [])]),
  ].sort();
  function update(patch: Partial<DiscoveryFilters>) {
    const next = { ...filters, ...patch };
    if (next.min_price > next.max_price) {
      setError('The minimum price must be below the maximum price.');
      return;
    }
    if (next.min_year > next.max_year) {
      setError('The earliest year must be before the latest year.');
      return;
    }
    setError('');
    setParams(searchParams(readFilters(searchParams(next))));
  }
  function advancedSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    update({
      min_price: Math.round(Number(data.get('min_price')) * 100),
      max_price: Math.round(Number(data.get('max_price')) * 100),
      min_year: Number(data.get('min_year') ?? 1900),
      max_year: Number(data.get('max_year') ?? 2100),
      max_mileage: Number(data.get('max_mileage') ?? 3000000),
      fuel: String(data.get('fuel') ?? '') as DiscoveryFilters['fuel'],
      transmission: String(data.get('transmission') ?? '') as DiscoveryFilters['transmission'],
    });
  }
  const chips: { key: keyof DiscoveryFilters; text: string }[] = [];
  if (filters.category) chips.push({ key: 'category', text: categories[filters.category].label });
  if (filters.q) chips.push({ key: 'q', text: `“${filters.q}”` });
  if (filters.make) chips.push({ key: 'make', text: filters.make });
  if (filters.min_price) chips.push({ key: 'min_price', text: `From ${euros(filters.min_price)}` });
  if (filters.max_price !== defaultFilters.max_price)
    chips.push({ key: 'max_price', text: `Up to ${euros(filters.max_price)}` });
  if (filters.fuel) chips.push({ key: 'fuel', text: filters.fuel });
  if (filters.transmission) chips.push({ key: 'transmission', text: filters.transmission });
  if (filters.min_year !== 1900) chips.push({ key: 'min_year', text: `From ${filters.min_year}` });
  if (filters.max_year !== 2100) chips.push({ key: 'max_year', text: `To ${filters.max_year}` });
  if (filters.max_mileage !== 3000000)
    chips.push({ key: 'max_mileage', text: `Under ${filters.max_mileage.toLocaleString()} km` });
  if (filters.radius_km !== 50)
    chips.push({ key: 'radius_km', text: `Within ${filters.radius_km} km` });
  const budgetValues =
    filters.category === 'homes'
      ? [30000000, 50000000, 100000000]
      : filters.category === 'cars'
        ? [2000000, 3000000, 5000000]
        : [10000, 50000, 100000];
  return (
    <>
      <PageHeading
        className="discovery-heading"
        eyebrow="A BETTER WAY TO BUY LOCAL"
        title={
          <>
            Your next find, <span>in motion.</span>
          </>
        }
        description="Real videos. Local sellers. A proper look before you meet."
        action={
          <div className="heading-stamp">
            <span className="live-dot" />
            Exploring Dublin
          </div>
        }
      />
      <div className="discovery-search-row">
        <KeywordSearch key={filters.q} value={filters.q} submit={(q) => update({ q })} />
        <label className="discovery-sort">
          Sort by
          <select
            aria-label="Sort adverts"
            value={filters.sort}
            onChange={(event) => update({ sort: event.target.value as DiscoveryFilters['sort'] })}
          >
            {Object.entries(sortLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <nav className="category-tabs" aria-label="Listing categories">
        <button
          className={!filters.category ? 'selected' : ''}
          aria-pressed={!filters.category}
          onClick={() => update({ ...defaultFilters, q: filters.q })}
        >
          For you
        </button>
        {Object.entries(categories)
          .filter(([key]) => key !== 'other')
          .map(([key, info]) => (
            <button
              key={key}
              className={filters.category === key ? 'selected' : ''}
              aria-pressed={filters.category === key}
              onClick={() =>
                update({
                  ...defaultFilters,
                  q: filters.q,
                  category: key as DiscoveryFilters['category'],
                })
              }
            >
              {info.label}
            </button>
          ))}
      </nav>
      <div className="filter-bar">
        {filters.category === 'cars' && (
          <>
            <label className="filter-select">
              <span>Make</span>
              <select
                aria-label="Filter by make"
                value={filters.make}
                onChange={(event) => update({ make: event.target.value })}
              >
                <option value="">All makes</option>
                {makes.map((make) => (
                  <option key={make}>{make}</option>
                ))}
              </select>
            </label>
          </>
        )}
        <label className="filter-select">
          <span>Budget</span>
          <select
            aria-label="Maximum price"
            value={filters.max_price}
            onChange={(event) => update({ max_price: Number(event.target.value), min_price: 0 })}
          >
            <option value="2000000000">Any price</option>
            {budgetValues.map((value) => (
              <option key={value} value={value}>
                Up to {euros(value)}
              </option>
            ))}
            {filters.max_price !== 2000000000 && !budgetValues.includes(filters.max_price) && (
              <option value={filters.max_price}>Up to {euros(filters.max_price)}</option>
            )}
          </select>
        </label>
        <label className="filter-select">
          <span>Distance</span>
          <select
            aria-label="Search radius"
            value={filters.radius_km}
            onChange={(event) => update({ radius_km: Number(event.target.value) })}
          >
            {[10, 25, 50, 100].map((value) => (
              <option key={value} value={value}>
                Within {value} km
              </option>
            ))}
            {![10, 25, 50, 100].includes(filters.radius_km) && (
              <option value={filters.radius_km}>Within {filters.radius_km} km</option>
            )}
          </select>
        </label>
        <button
          className={`filter-button ${advanced ? 'selected' : ''}`}
          aria-expanded={advanced}
          aria-controls="discovery-filters"
          onClick={() => setAdvanced(!advanced)}
        >
          <SlidersHorizontal size={16} />
          Filters{chips.length > 0 && <span className="filter-count">{chips.length}</span>}
        </button>
      </div>
      {advanced && (
        <form
          id="discovery-filters"
          key={searchParams(filters).toString()}
          className="discovery-advanced form-stack"
          onSubmit={advancedSubmit}
        >
          <div className="form-grid">
            <label>
              Minimum price (€)
              <input
                name="min_price"
                type="number"
                min="0"
                max="20000000"
                step="1"
                required
                defaultValue={filters.min_price / 100}
              />
            </label>
            <label>
              Maximum price (€)
              <input
                name="max_price"
                type="number"
                min="0"
                max="20000000"
                step="1"
                required
                defaultValue={filters.max_price / 100}
              />
            </label>
            {filters.category === 'cars' && (
              <>
                <label>
                  Minimum year
                  <input
                    aria-label="Minimum year"
                    name="min_year"
                    type="number"
                    min="1900"
                    max="2100"
                    required
                    defaultValue={filters.min_year}
                  />
                </label>
                <label>
                  Maximum year
                  <input
                    name="max_year"
                    type="number"
                    min="1900"
                    max="2100"
                    required
                    defaultValue={filters.max_year}
                  />
                </label>
                <label>
                  Fuel type
                  <select name="fuel" aria-label="Fuel type" defaultValue={filters.fuel}>
                    <option value="">Any fuel</option>
                    {['petrol', 'diesel', 'electric', 'hybrid'].map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Transmission
                  <select
                    name="transmission"
                    aria-label="Transmission"
                    defaultValue={filters.transmission}
                  >
                    <option value="">Any gearbox</option>
                    <option value="automatic">Automatic</option>
                    <option value="manual">Manual</option>
                  </select>
                </label>
                <label>
                  Maximum mileage (km)
                  <input
                    name="max_mileage"
                    type="number"
                    min="0"
                    max="3000000"
                    required
                    defaultValue={filters.max_mileage}
                  />
                </label>
              </>
            )}
          </div>
          <div className="discovery-filter-actions">
            <p className="muted">
              Distances use Dublin city centre. Seller locations stay approximate.
            </p>
            <button className="button dark">Apply filters</button>
          </div>
        </form>
      )}
      {chips.length > 0 && (
        <div className="discovery-chips" aria-label="Active filters">
          {chips.map((chip) => (
            <button
              key={chip.key}
              aria-label={`Clear ${chip.text} filter`}
              onClick={() => update({ [chip.key]: defaultFilters[chip.key] })}
            >
              {chip.text}
              <X size={12} />
            </button>
          ))}
          <button
            className="clear-filters"
            onClick={() => {
              setError('');
              setParams({});
            }}
          >
            Clear all
          </button>
        </div>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="loop-toolbar">
        <TuneFeed requireAuth={props.requireAuth} />
        <span>Fresh finds. A little more you.</span>
      </div>
      <FeedResults
        key={searchParams(filters).toString()}
        {...props}
        filters={filters}
        reset={() => {
          setError('');
          setParams({});
        }}
      />
    </>
  );
}

function KeywordSearch({ value, submit }: { value: string; submit: (value: string) => void }) {
  const [text, setText] = useState(value);
  return (
    <form
      className="discovery-search"
      role="search"
      onSubmit={(event) => {
        event.preventDefault();
        submit(text.trim());
      }}
    >
      <Search size={19} />
      <input
        aria-label="Search listings"
        value={text}
        onChange={(event) => setText(event.target.value)}
        maxLength={100}
        placeholder="Search listings…"
        type="search"
      />
      <button className="button dark">Search</button>
    </form>
  );
}

function FeedResults({
  filters,
  reset,
  requireAuth,
  message,
}: Props & { filters: DiscoveryFilters; reset: () => void }) {
  const auth = useAuth(),
    navigate = useNavigate(),
    client = useQueryClient();
  const [active, setActive] = useState(0),
    [notice, setNotice] = useState(''),
    [saving, setSaving] = useState('');
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [lastHidden, setLastHidden] = useState<Listing | null>(null);
  const scroll = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(650);
  const queryKey = [
    'feed',
    searchParams(filters).toString(),
    auth.user?.id,
    auth.user?.analytics_consent,
  ];
  const query = useInfiniteQuery({
    queryKey,
    initialPageParam: '',
    queryFn: async ({ pageParam }) => {
      if (pageParam) await flushSignals();
      return fetchFeed({ ...feedQuery(filters), cursor: pageParam || undefined });
    },
    getNextPageParam: (page) => page.next_cursor || undefined,
  });
  const listings = [
    ...new Map(
      (query.data?.pages.flatMap((page) => page.items) || [])
        .filter((item) => !hidden.has(item.id))
        .map((item) => [item.id, item]),
    ).values(),
  ];
  const virtualizer = useVirtualizer({
    count: listings.length,
    getScrollElement: () => scroll.current,
    estimateSize: () => height,
    overscan: 2,
  });
  const current = listings[Math.min(active, listings.length - 1)] || listings[0];
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
    if (
      active >= listings.length - 2 &&
      query.hasNextPage &&
      !query.isFetchingNextPage &&
      !query.isFetchNextPageError
    )
      void query.fetchNextPage();
  }, [active, listings.length, query]);
  async function save(listing: Listing) {
    if (!auth.user) {
      requireAuth();
      return;
    }
    if (saving) return;
    setSaving(listing.id);
    setNotice('');
    try {
      await request(`/listings/${listing.id}/save`, { method: listing.saved ? 'DELETE' : 'PUT' });
      await Promise.all([
        client.invalidateQueries({ queryKey: ['feed'] }),
        client.invalidateQueries({ queryKey: ['saved'] }),
        client.invalidateQueries({ queryKey: ['listing', listing.id] }),
      ]);
    } catch (problem) {
      setNotice((problem as Error).message);
    } finally {
      setSaving('');
    }
  }
  function chat(listing: Listing) {
    if (listing.seller.id === auth.user?.id) navigate('/my-listings');
    else message(listing);
  }
  async function dismiss(listing: Listing) {
    if (!auth.user) {
      requireAuth();
      return;
    }
    try {
      await request('/feed/feedback', {
        method: 'PUT',
        body: JSON.stringify({ listing_id: listing.id }),
      });
      setHidden((current) => new Set([...current, listing.id]));
      setLastHidden(listing);
      setActive((index) => Math.max(0, Math.min(index, listings.length - 2)));
    } catch (problem) {
      setNotice((problem as Error).message);
    }
  }
  return (
    <>
      {notice && (
        <p className="error" role="alert">
          {notice}
        </p>
      )}
      {lastHidden && (
        <div className="notice feed-feedback" role="status">
          <span>Advert hidden from your loop.</span>
          <button
            className="text-button"
            onClick={() => {
              const listing = lastHidden;
              void request(`/feed/feedback/${listing.id}`, { method: 'DELETE' })
                .then(async () => {
                  setHidden((current) => {
                    const next = new Set(current);
                    next.delete(listing.id);
                    return next;
                  });
                  setLastHidden(null);
                  setActive(0);
                  await client.resetQueries({ queryKey, exact: true });
                })
                .catch((problem: Error) => setNotice(problem.message));
            }}
          >
            Undo
          </button>
        </div>
      )}
      <div className="feed-layout">
        <div className="feed-column">
          <div className="feed-label">
            <span>
              <i />
              THE LOCAL LOOP
            </span>
            <span>
              {listings.length
                ? `${Math.min(active + 1, listings.length)} of ${listings.length} loaded`
                : 'Scroll to discover'}
              <ArrowDown size={12} />
            </span>
          </div>
          <div
            className="feed-scroll"
            ref={scroll}
            aria-label="Video feed"
            tabIndex={0}
            onKeyDown={(event) => {
              if (
                event.target !== event.currentTarget ||
                !['ArrowDown', 'ArrowUp'].includes(event.key)
              )
                return;
              event.preventDefault();
              virtualizer.scrollToIndex(
                Math.max(
                  0,
                  Math.min(listings.length - 1, active + (event.key === 'ArrowDown' ? 1 : -1)),
                ),
                { align: 'start' },
              );
            }}
          >
            {query.isPending && (
              <div className="feed-empty" role="status">
                <div className="spinner" />
                <h2>Finding your next find…</h2>
              </div>
            )}
            {query.isError && !listings.length && (
              <div className="feed-empty">
                <h2>Let’s try that again.</h2>
                <p>{query.error.message}</p>
                <button
                  className="button primary"
                  onClick={() => void client.resetQueries({ queryKey, exact: true })}
                >
                  <RotateCw size={16} />
                  Retry
                </button>
              </div>
            )}
            {!query.isPending && !query.isError && !listings.length && (
              <div className="feed-empty">
                <Search size={32} />
                <h2>No listings match just yet.</h2>
                <p>Try a different search, budget or distance.</p>
                <button className="button primary" onClick={reset}>
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
                    saving={saving === listings[item.index].id}
                    onMessage={() => chat(listings[item.index])}
                  />
                </div>
              ))}
            </div>
          </div>
          <div className="feed-footer">
            <span>
              {query.isFetchingNextPage
                ? 'Finding more listings…'
                : 'See something you like? Start a conversation.'}
            </span>
            <div>
              <button
                className="icon-button"
                aria-label="Previous listing"
                disabled={active === 0 || !listings.length}
                onClick={() => virtualizer.scrollToIndex(active - 1, { align: 'start' })}
              >
                <ArrowUp size={17} />
              </button>
              <button
                className="icon-button"
                aria-label="Next listing"
                disabled={active >= listings.length - 1}
                onClick={() => virtualizer.scrollToIndex(active + 1, { align: 'start' })}
              >
                <ArrowDown size={17} />
              </button>
            </div>
          </div>
          <div className="feed-context-actions">
            {current && current.seller.id !== auth.user?.id && (
              <button
                className="text-button"
                aria-label="Not interested in this listing"
                onClick={() => void dismiss(current)}
              >
                Not interested
              </button>
            )}
            <button
              className="text-button"
              onClick={() => {
                setActive(0);
                scroll.current?.scrollTo({ top: 0 });
                void client.resetQueries({ queryKey, exact: true });
              }}
            >
              Refresh your loop
            </button>
          </div>
          {query.isFetchNextPageError && (
            <div className="notice feed-recovery" role="alert">
              <p>{query.error?.message || 'Could not load more listings.'}</p>
              <button
                className="button dark"
                onClick={() => {
                  setActive(0);
                  scroll.current?.scrollTo({ top: 0 });
                  void client.resetQueries({ queryKey, exact: true });
                }}
              >
                Refresh results
              </button>
            </div>
          )}
        </div>
        {current && (
          <ListingDetails
            key={current.id}
            listing={current}
            onSave={() => void save(current)}
            saving={saving === current.id}
            onMessage={() => chat(current)}
            requireAuth={requireAuth}
          />
        )}
      </div>
    </>
  );
}
