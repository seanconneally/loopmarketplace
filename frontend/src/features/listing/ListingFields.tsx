import { useState } from 'react';
import { categories, words, type Category } from './categories';
import type { ListingInput } from '../../api/client';

export function ListingFields({
  value,
  disabled = false,
  draft,
}: {
  value?: ListingInput;
  disabled?: boolean;
  draft?: Record<string, string>;
}) {
  const [category, setCategory] = useState<Category>(
    Object.hasOwn(categories, draft?.category || '')
      ? (draft?.category as Category)
      : value?.category || (draft?.make ? 'cars' : 'other'),
  );
  return (
    <fieldset className="listing-fields" disabled={disabled}>
      <div className="form-section-heading">
        <span>01</span>
        <div>
          <strong>The essentials</strong>
          <p>Give buyers the details they need at a glance.</p>
        </div>
      </div>
      <label>
        Category
        <select
          aria-label="Category"
          name="category"
          value={category}
          onChange={(event) => setCategory(event.target.value as Category)}
        >
          {Object.entries(categories).map(([key, info]) => (
            <option key={key} value={key}>
              {info.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Listing title
        <input
          name="title"
          required
          minLength={3}
          maxLength={120}
          defaultValue={draft?.title ?? value?.title}
          placeholder="e.g. The thing someone’s been looking for"
        />
      </label>
      <div className="form-grid">
        {category === 'cars' && (
          <>
            <label>
              Make
              <input
                name="make"
                required
                maxLength={50}
                defaultValue={draft?.make ?? value?.car?.make}
                placeholder="Volkswagen"
              />
            </label>
            <label>
              Model
              <input
                name="model"
                required
                maxLength={60}
                defaultValue={draft?.model ?? value?.car?.model}
                placeholder="Golf"
              />
            </label>
            <label>
              Year
              <input
                name="year"
                type="number"
                min="1900"
                max="2100"
                defaultValue={draft?.year ?? value?.car?.year ?? 2021}
                required
              />
            </label>
            <label>
              Mileage (km)
              <input
                name="mileage"
                type="number"
                min="0"
                max="3000000"
                defaultValue={draft?.mileage ?? value?.car?.mileage_km}
                required
              />
            </label>
          </>
        )}
        <label>
          Asking price (€)
          <input
            name="price"
            type="number"
            min="1"
            max="20000000"
            step="0.01"
            defaultValue={draft?.price ?? (value ? value.price_cents / 100 : undefined)}
            required
          />
        </label>
        <label>
          Area
          <input
            name="area"
            defaultValue={draft?.area ?? value?.area ?? 'Dublin city'}
            required
            minLength={2}
            maxLength={100}
          />
        </label>
        {category === 'cars' && (
          <>
            <label>
              Fuel
              <select name="fuel" defaultValue={draft?.fuel ?? value?.car?.fuel ?? 'petrol'}>
                <option value="petrol">Petrol</option>
                <option value="diesel">Diesel</option>
                <option value="electric">Electric</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </label>
            <label>
              Gearbox
              <select
                name="transmission"
                defaultValue={draft?.transmission ?? value?.car?.transmission ?? 'automatic'}
              >
                <option value="automatic">Automatic</option>
                <option value="manual">Manual</option>
              </select>
            </label>
          </>
        )}
        {categories[category].fields.map((field) => (
          <label key={`${category}:${field.key}`}>
            {field.label}
            {field.options ? (
              <select
                name={`attr_${field.key}`}
                defaultValue={
                  draft?.[`attr_${field.key}`] ??
                  String(value?.attributes?.[field.key] ?? field.options[0])
                }
              >
                {field.options.map((option) => (
                  <option key={option} value={option}>
                    {words(option)}
                  </option>
                ))}
              </select>
            ) : (
              <input
                name={`attr_${field.key}`}
                type={field.min !== undefined ? 'number' : 'text'}
                min={field.min}
                max={field.max}
                maxLength={80}
                step={field.key === 'floor_area_m2' ? 'any' : undefined}
                defaultValue={
                  draft?.[`attr_${field.key}`] ?? String(value?.attributes?.[field.key] ?? '')
                }
              />
            )}
          </label>
        ))}
      </div>
      <div className="form-section-heading">
        <span>02</span>
        <div>
          <strong>A little more detail</strong>
          <p>The history, the highlights and anything worth knowing.</p>
        </div>
      </div>
      <label>
        About this listing
        <textarea
          name="description"
          maxLength={3000}
          defaultValue={draft?.description ?? value?.description}
          placeholder="The history, the highlights, the little things worth knowing."
        />
      </label>
      <label className="checkbox">
        <input
          name="rights"
          type="checkbox"
          required
          defaultChecked={draft ? draft.rights === 'on' : !!value}
        />
        I have the right to use this video and advertise this listing.
      </label>
    </fieldset>
  );
}
