import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, test } from 'vitest';
import { ListingFields } from './ListingFields';
import { listingDetails } from './listingForm';
afterEach(cleanup);

test('non-car adverts serialize category facts without hidden car requirements', () => {
  const { container } = render(
    <form>
      <ListingFields />
    </form>,
  );
  expect(screen.getByLabelText('Category')).toHaveValue('other');
  expect(screen.queryByLabelText('Make')).toBeNull();
  fireEvent.change(screen.getByLabelText('Listing title'), { target: { value: 'A set of irons' } });
  fireEvent.change(screen.getByLabelText('Asking price (€)'), { target: { value: '320' } });
  fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'golf' } });
  fireEvent.change(screen.getByLabelText('Brand'), { target: { value: 'Mizuno' } });
  fireEvent.change(screen.getByLabelText('Club type'), { target: { value: 'irons' } });
  const data = listingDetails(container.querySelector('form')!);
  expect(data).toMatchObject({
    category: 'golf',
    car: null,
    price_cents: 32000,
    attributes: { brand: 'Mizuno', club_type: 'irons' },
  });
  fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'homes' } });
  fireEvent.change(screen.getByLabelText('Bedrooms'), { target: { value: '3' } });
  expect(listingDetails(container.querySelector('form')!)).toMatchObject({
    category: 'homes',
    car: null,
    attributes: { bedrooms: 3 },
  });
  expect(listingDetails(container.querySelector('form')!).attributes).not.toHaveProperty('brand');
});

test('older car drafts retain their category when reopened', () => {
  render(<ListingFields draft={{ title: 'My car', make: 'Toyota', model: 'Yaris' }} />);
  expect(screen.getByLabelText('Category')).toHaveValue('cars');
  expect(screen.getByLabelText('Make')).toHaveValue('Toyota');
});
