import type { Listing, ListingInput } from '../../api/client';

export type Category = NonNullable<ListingInput['category']>;
type FactField = { key: string; label: string; options?: string[]; min?: number; max?: number };
export const categories: Record<Category, { label: string; fields: FactField[] }> = {
  cars: { label: 'Cars', fields: [] },
  homes: {
    label: 'Homes',
    fields: [
      {
        key: 'property_type',
        label: 'Property type',
        options: ['house', 'apartment', 'land', 'other'],
      },
      { key: 'bedrooms', label: 'Bedrooms', min: 0, max: 100 },
      { key: 'bathrooms', label: 'Bathrooms', min: 0, max: 100 },
      { key: 'floor_area_m2', label: 'Floor area (m²)', min: 1, max: 1000000 },
    ],
  },
  golf: {
    label: 'Golf clubs',
    fields: [
      { key: 'brand', label: 'Brand' },
      {
        key: 'club_type',
        label: 'Club type',
        options: ['other', 'driver', 'irons', 'putter', 'wedge', 'set'],
      },
      { key: 'hand', label: 'Hand', options: ['right', 'left', 'either'] },
      { key: 'condition', label: 'Condition', options: ['good', 'new', 'like_new', 'fair'] },
    ],
  },
  other: {
    label: 'Something else',
    fields: [
      { key: 'brand', label: 'Brand' },
      { key: 'condition', label: 'Condition', options: ['good', 'new', 'like_new', 'fair'] },
    ],
  },
};
export const words = (value: string) => value.replaceAll('_', ' ');
export function categoryLabel(value: string): string {
  return categories[value as Category]?.label || 'Other finds';
}
export function listingSpecs(item: Listing): [string, string][] {
  if (item.category === 'cars' && item.car)
    return [
      ['Year', String(item.car.year)],
      ['Mileage', `${item.car.mileage_km.toLocaleString()} km`],
      ['Fuel type', item.car.fuel],
      ['Gearbox', item.car.transmission],
    ];
  const fields = categories[item.category as Category]?.fields || [];
  return fields.flatMap((field) => {
    const value = item.attributes?.[field.key];
    return (typeof value === 'string' && value !== '') || typeof value === 'number'
      ? [[field.label, words(String(value))] as [string, string]]
      : [];
  });
}
export const listingSummary = (item: Listing) =>
  listingSpecs(item)
    .slice(0, 3)
    .map(([, value]) => value)
    .join(' · ') || categoryLabel(item.category);
