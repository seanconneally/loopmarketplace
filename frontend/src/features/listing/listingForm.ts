import { categories, type Category } from './categories';
import type { ListingInput } from '../../api/client';

export function listingDetails(form: HTMLFormElement, original?: ListingInput): ListingInput {
  const data = new FormData(form);
  const category = String(data.get('category') || original?.category || 'other') as Category;
  const attributes = Object.fromEntries(
    categories[category].fields.flatMap((field) => {
      const raw = String(data.get(`attr_${field.key}`) ?? '').trim();
      return raw ? [[field.key, field.min !== undefined ? Number(raw) : raw]] : [];
    }),
  );
  return {
    title: String(data.get('title')),
    description: String(data.get('description')),
    price_cents: Math.round(Number(data.get('price')) * 100),
    area: String(data.get('area')),
    latitude: original?.latitude ?? 53.3498,
    longitude: original?.longitude ?? -6.2603,
    category,
    attributes,
    region_id: 'ie-dublin',
    rights_confirmed: true,
    car:
      category === 'cars'
        ? {
            make: String(data.get('make')),
            model: String(data.get('model')),
            year: Number(data.get('year')),
            mileage_km: Number(data.get('mileage')),
            fuel: String(data.get('fuel')) as NonNullable<ListingInput['car']>['fuel'],
            transmission: String(data.get('transmission')) as NonNullable<
              ListingInput['car']
            >['transmission'],
          }
        : null,
  };
}
