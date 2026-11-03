import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TuneFeed } from './TuneFeed';

const { updateUser } = vi.hoisted(() => ({ updateUser: vi.fn() }));
vi.mock('../../shared/Auth', () => ({
  useAuth: () => ({
    user: { id: 'member', name: 'Member', adult_declared: false, analytics_consent: false },
    updateUser,
  }),
}));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  updateUser.mockClear();
});

test('personalisation requires an explicit choice and saves the actual consent setting', async () => {
  const fetcher = vi.fn(async (url: string, options?: RequestInit) => {
    expect(url).toBe('/api/v1/users/me');
    expect(options?.method).toBe('PATCH');
    return Response.json({
      id: 'member',
      name: 'Member',
      adult_declared: false,
      analytics_consent: true,
    });
  });
  vi.stubGlobal('fetch', fetcher);
  const client = new QueryClient();
  render(
    <QueryClientProvider client={client}>
      <TuneFeed requireAuth={vi.fn()} />
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Tune your loop' }));
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Save feed preferences' }));
  await waitFor(() =>
    expect(updateUser).toHaveBeenCalledWith(expect.objectContaining({ analytics_consent: true })),
  );
  expect(fetcher.mock.calls[0][0]).toBe('/api/v1/users/me');
  expect(JSON.parse(String(fetcher.mock.calls[0][1]?.body)).analytics_consent).toBe(true);
  client.clear();
});
