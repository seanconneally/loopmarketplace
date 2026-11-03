import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AuthProvider } from '../../shared/Auth';
import { SignIn } from './SignIn';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test('phone verification sends the OTP and records explicit seller declaration', async () => {
  const close = vi.fn();
  const user = {
    id: 'member',
    name: 'Test buyer',
    role: 'member',
    adult_declared: false,
    analytics_consent: false,
  };
  const fetcher = vi.fn(async (url: string, options?: RequestInit) => {
    if (url.endsWith('/refresh')) return new Response('{}', { status: 401 });
    if (url.endsWith('/otp/request')) return Response.json({ development_code: '123456' });
    if (url.endsWith('/otp/verify'))
      return Response.json({ access_token: 'test-token', token_type: 'bearer', user });
    if (url.endsWith('/users/me'))
      return Response.json({ ...user, ...JSON.parse(String(options?.body)) });
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher);
  render(
    <AuthProvider>
      <SignIn close={close} />
    </AuthProvider>,
  );
  fireEvent.change(screen.getByLabelText('Phone number'), { target: { value: '+353871234567' } });
  fireEvent.click(screen.getByRole('button', { name: /Continue with phone/ }));
  await screen.findByLabelText('Verification code');
  fireEvent.change(screen.getByLabelText('Verification code'), { target: { value: '123456' } });
  fireEvent.change(screen.getByLabelText('Your name'), { target: { value: 'Test seller' } });
  fireEvent.click(screen.getByLabelText(/I am 18/));
  fireEvent.click(screen.getByRole('button', { name: /Verify & continue/ }));
  await waitFor(() => expect(close).toHaveBeenCalledOnce());
  const profileCall = fetcher.mock.calls.find(([url]) => url.endsWith('/users/me'));
  expect(JSON.parse(String(profileCall?.[1]?.body))).toEqual({
    name: 'Test seller',
    adult_declared: true,
    analytics_consent: false,
  });
});
