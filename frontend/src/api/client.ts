import createClient from 'openapi-fetch';
import type { components, paths } from './generated';

export type Listing = components['schemas']['ListingView'];
export type User = components['schemas']['UserView'];
export type Conversation = components['schemas']['ConversationView'];
export type Message = components['schemas']['MessageView'];
export type Viewing = components['schemas']['ViewingView'];
export type FeedPage = components['schemas']['FeedPage'];
export type AuthResult = components['schemas']['AuthView'];
export type ListingInput = components['schemas']['ListingCreate'];
export type SellerListing = components['schemas']['SellerListingView'];
export type SellerListingPage = components['schemas']['SellerListingPage'];
export type UploadSession = components['schemas']['UploadView'];

let token: string | null = null;
let refreshing: Promise<AuthResult | null> | null = null;
let sessionVersion = 0;
export const setToken = (value: string | null) => {
  sessionVersion += 1;
  token = value;
};

export const generatedClient = createClient<paths>({ baseUrl: '', credentials: 'include' });
export type FeedQuery = NonNullable<paths['/api/v1/feed']['get']['parameters']['query']>;
generatedClient.use({
  onRequest({ request }) {
    if (token) request.headers.set('Authorization', `Bearer ${token}`);
    return request;
  },
});

export async function restoreSession(): Promise<AuthResult | null> {
  if (!refreshing) {
    const version = sessionVersion;
    refreshing = fetch('/api/v1/auth/refresh', {
      method: 'POST',
      credentials: 'include',
      signal: AbortSignal.timeout(10000),
    })
      .then(async (response) => {
        if (version !== sessionVersion) return null;
        if (response.status === 401 || response.status === 403) {
          token = null;
          return null;
        }
        if (!response.ok) throw new Error('We couldn’t check your session. Please try again.');
        const data = (await response.json()) as AuthResult;
        if (version !== sessionVersion) return null;
        token = data.access_token;
        return data;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

export async function fetchFeed(query: FeedQuery, retry = true): Promise<FeedPage> {
  const usedToken = token;
  const result = await generatedClient.GET('/api/v1/feed', { params: { query } });
  if (result.data) return result.data;
  if (
    result.response.status === 401 &&
    retry &&
    ((token && token !== usedToken) || (await restoreSession()))
  )
    return fetchFeed(query, false);
  throw new Error(result.error?.error.message || 'Could not load the local feed.');
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const usedToken = token;
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { ...options, headers, credentials: 'include' });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new Error(
      navigator.onLine === false
        ? 'You’re offline. Reconnect and try again.'
        : 'Couldn’t reach Loop Marketplace. Check your connection and try again.',
    );
  }
  if (response.status === 401 && retry && !path.startsWith('/auth/')) {
    if ((token && token !== usedToken) || (await restoreSession()))
      return request<T>(path, options, false);
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { error?: { message?: string } };
    throw new Error(body.error?.message || `Request failed (${response.status})`);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export function mutation(body: unknown, key: string = crypto.randomUUID()): RequestInit {
  return { method: 'POST', body: JSON.stringify(body), headers: { 'Idempotency-Key': key } };
}

export const euros = (cents: number) =>
  new Intl.NumberFormat('en-IE', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(cents / 100);

export async function downloadCalendar(viewingId: string) {
  const fetchCalendar = () =>
    fetch(`/api/v1/viewings/${viewingId}/calendar`, {
      credentials: 'include',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  const usedToken = token;
  let response = await fetchCalendar();
  if (response.status === 401 && ((token && token !== usedToken) || (await restoreSession())))
    response = await fetchCalendar();
  if (!response.ok) throw new Error('Could not export this viewing.');
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'viewing.ics';
  anchor.click();
  URL.revokeObjectURL(url);
}
