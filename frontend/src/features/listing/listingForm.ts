import type { ListingInput } from '../../api/client';

export function listingDetails(form: HTMLFormElement, original?: ListingInput): ListingInput {
  const data = new FormData(form);
  return {
    title: String(data.get('title')),
    description: String(data.get('description')),
    price_cents: Math.round(Number(data.get('price')) * 100),
    area: String(data.get('area')),
    latitude: original?.latitude ?? 53.3498,
    longitude: original?.longitude ?? -6.2603,
    category: 'cars',
    region_id: 'ie-dublin',
    rights_confirmed: true,
    car: {
      make: String(data.get('make')),
      model: String(data.get('model')),
      year: Number(data.get('year')),
      mileage_km: Number(data.get('mileage')),
      fuel: String(data.get('fuel')) as ListingInput['car']['fuel'],
      transmission: String(data.get('transmission')) as ListingInput['car']['transmission'],
    },
  };
}
