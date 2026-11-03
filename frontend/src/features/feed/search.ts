import type { FeedQuery } from '../../api/client';

export type DiscoveryFilters = {
  q: string;
  make: string;
  min_price: number;
  max_price: number;
  radius_km: number;
  min_year: number;
  max_year: number;
  max_mileage: number;
  fuel: NonNullable<FeedQuery['fuel']> | '';
  transmission: NonNullable<FeedQuery['transmission']> | '';
  sort: NonNullable<FeedQuery['sort']>;
};
export const defaultFilters: DiscoveryFilters = {
  q: '',
  make: '',
  min_price: 0,
  max_price: 100000000,
  radius_km: 50,
  min_year: 1900,
  max_year: 2100,
  max_mileage: 3000000,
  fuel: '',
  transmission: '',
  sort: 'recommended',
};
export const sortLabels: Record<DiscoveryFilters['sort'], string> = {
  recommended: 'Recommended',
  newest: 'Newest first',
  price_asc: 'Lowest price',
  price_desc: 'Highest price',
};

export function readFilters(params: URLSearchParams): DiscoveryFilters {
  const number = (key: keyof DiscoveryFilters, min: number, max: number) => {
    const raw = params.get(key),
      value = Number(raw);
    return raw && Number.isInteger(value) && value >= min && value <= max
      ? value
      : Number(defaultFilters[key]);
  };
  const fuel = params.get('fuel'),
    transmission = params.get('transmission'),
    sort = params.get('sort');
  const result: DiscoveryFilters = {
    q: (params.get('q') || '').trim().split(/\s+/).slice(0, 8).join(' ').slice(0, 100),
    make: (params.get('make') || '').trim().slice(0, 50),
    min_price: number('min_price', 0, 100000000),
    max_price: number('max_price', 0, 100000000),
    radius_km: number('radius_km', 1, 100),
    min_year: number('min_year', 1900, 2100),
    max_year: number('max_year', 1900, 2100),
    max_mileage: number('max_mileage', 0, 3000000),
    fuel: ['petrol', 'diesel', 'electric', 'hybrid'].includes(fuel || '')
      ? (fuel as DiscoveryFilters['fuel'])
      : '',
    transmission: ['manual', 'automatic'].includes(transmission || '')
      ? (transmission as DiscoveryFilters['transmission'])
      : '',
    sort:
      sort && Object.hasOwn(sortLabels, sort) ? (sort as DiscoveryFilters['sort']) : 'recommended',
  };
  if (result.min_price > result.max_price) result.min_price = 0;
  if (result.min_year > result.max_year) result.max_year = 2100;
  return result;
}

export function searchParams(filters: DiscoveryFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const key of Object.keys(defaultFilters) as (keyof DiscoveryFilters)[])
    if (filters[key] !== defaultFilters[key]) params.set(key, String(filters[key]));
  return params;
}

export function feedQuery(filters: DiscoveryFilters): FeedQuery {
  return {
    ...filters,
    q: filters.q || undefined,
    make: filters.make || undefined,
    fuel: filters.fuel || undefined,
    transmission: filters.transmission || undefined,
  };
}
