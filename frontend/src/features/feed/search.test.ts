import { expect, test } from 'vitest';
import { defaultFilters, feedQuery, readFilters, searchParams } from './search';

test('search links round-trip filters, including custom budgets', () => {
  const filters = {
    ...defaultFilters,
    q: 'Toyota Yaris',
    max_price: 1745000,
    min_year: 2020,
    fuel: 'hybrid' as const,
    sort: 'price_asc' as const,
  };
  expect(readFilters(searchParams(filters))).toEqual(filters);
  expect(searchParams(filters).get('q')).toBe('Toyota Yaris');
  expect(feedQuery(filters).max_price).toBe(1745000);
});
test('invalid URL values fall back to usable bounds', () => {
  const filters = readFilters(
    new URLSearchParams(
      'min_price=999999999&max_price=-1&min_year=2050&max_year=2000&radius_km=oops&fuel=water&sort=__proto__',
    ),
  );
  expect(filters.min_price).toBe(0);
  expect(filters.max_price).toBe(100000000);
  expect(filters.max_year).toBe(2100);
  expect(filters.radius_km).toBe(50);
  expect(filters.fuel).toBe('');
  expect(filters.sort).toBe('recommended');
});
test('default filters produce a clean URL and omit empty API strings', () => {
  expect(searchParams(defaultFilters).toString()).toBe('');
  expect(feedQuery(defaultFilters)).toMatchObject({
    q: undefined,
    make: undefined,
    fuel: undefined,
    transmission: undefined,
  });
});
