import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from './Auth';
import { ErrorBoundary } from './ErrorBoundary';
import { clearMemberDrafts, readTextDraft, writeDraft } from './draftStorage';
import { setToken } from '../api/client';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  sessionStorage.clear();
  setToken(null);
});
function SessionProbe() {
  const auth = useAuth();
  return (
    <>
      <p>{auth.status}</p>
      <p>{auth.user?.name}</p>
      <button onClick={auth.retrySession}>Retry session</button>
      <button
        onClick={() =>
          auth.signIn({
            access_token: 'new',
            token_type: 'bearer',
            user: {
              id: 'member',
              name: 'New member',
              role: 'member',
              adult_declared: false,
              analytics_consent: false,
            },
          })
        }
      >
        New login
      </button>
    </>
  );
}

test('session checking stays distinct from signed-out while a refresh is pending', async () => {
  let finish!: (response: Response) => void;
  vi.stubGlobal(
    'fetch',
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          finish = resolve;
        }),
    ),
  );
  render(
    <AuthProvider>
      <SessionProbe />
    </AuthProvider>,
  );
  expect(screen.getByText('checking')).toBeInTheDocument();
  expect(screen.queryByText('signed-out')).not.toBeInTheDocument();
  finish(new Response('{}', { status: 401 }));
  await screen.findByText('signed-out');
});

test('a server failure offers recovery instead of claiming the member is signed out', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(new Response('{}', { status: 503 }))
      .mockResolvedValueOnce(new Response('{}', { status: 401 })),
  );
  render(
    <AuthProvider>
      <SessionProbe />
    </AuthProvider>,
  );
  await screen.findByText('unavailable');
  expect(screen.queryByText('signed-out')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Retry session' }));
  await screen.findByText('signed-out');
});

test('a pending startup result cannot undo a newer sign-in', async () => {
  let finish!: (response: Response) => void;
  vi.stubGlobal(
    'fetch',
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          finish = resolve;
        }),
    ),
  );
  render(
    <AuthProvider>
      <SessionProbe />
    </AuthProvider>,
  );
  fireEvent.click(screen.getByRole('button', { name: 'New login' }));
  finish(new Response('{}', { status: 401 }));
  await waitFor(() => expect(screen.getByText('authenticated')).toBeInTheDocument());
  expect(screen.getByText('New member')).toBeInTheDocument();
});

test('render crashes show recovery controls and retry can restore the page', () => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
  let broken = true;
  function Page() {
    if (broken) throw new Error('Internal details must not appear');
    return <h1>Recovered page</h1>;
  }
  render(
    <ErrorBoundary>
      <Page />
    </ErrorBoundary>,
  );
  expect(
    screen.getByRole('heading', { name: 'Something went wrong on this page.' }),
  ).toBeInTheDocument();
  expect(screen.queryByText('Internal details must not appear')).not.toBeInTheDocument();
  broken = false;
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
  expect(screen.getByRole('heading', { name: 'Recovered page' })).toBeInTheDocument();
});

test('tab drafts tolerate damaged storage, report write failure and clear only the signed-out member', () => {
  sessionStorage.setItem('bad', '{invalid');
  expect(readTextDraft('bad')).toEqual({});
  sessionStorage.setItem('bad', JSON.stringify({ title: 'Keep this', bogus: 42 }));
  expect(readTextDraft('bad')).toEqual({ title: 'Keep this' });
  writeDraft('motorloop.chat-draft.member', { a: 'Private draft' });
  writeDraft('motorloop.advert-draft.member', { title: 'Unfinished advert' });
  writeDraft('motorloop.chat-draft.other', { a: 'Other member' });
  clearMemberDrafts('member');
  expect(readTextDraft('motorloop.chat-draft.member')).toEqual({});
  expect(readTextDraft('motorloop.chat-draft.other')).toEqual({ a: 'Other member' });
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('Full');
  });
  expect(writeDraft('full', {})).toBe(false);
});
