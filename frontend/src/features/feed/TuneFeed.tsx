import { clearSignals } from './signals';
import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { request, type User } from '../../api/client';
import { useAuth } from '../../shared/Auth';
import { Modal } from '../../shared/Modal';
import { useOnlineStatus } from '../../shared/useOnlineStatus';

export function TuneFeed({ requireAuth }: { requireAuth: () => void }) {
  const auth = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        className="text-button tune-feed"
        onClick={() => (auth.user ? setOpen(true) : requireAuth())}
      >
        <Sparkles size={16} />
        {auth.user?.analytics_consent ? 'Your personal loop' : 'Tune your loop'}
      </button>
      {open && auth.user && <FeedSettings close={() => setOpen(false)} />}
    </>
  );
}

function FeedSettings({ close }: { close: () => void }) {
  const auth = useAuth();
  const client = useQueryClient();
  const online = useOnlineStatus();
  const [enabled, setEnabled] = useState(!!auth.user?.analytics_consent);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  async function save() {
    if (!auth.user || busy || !online) return;
    setBusy(true);
    setError('');
    try {
      const user = await request<User>('/users/me', {
        method: 'PATCH',
        body: JSON.stringify({
          name: auth.user.name,
          adult_declared: auth.user.adult_declared,
          analytics_consent: enabled,
        }),
      });
      clearSignals();
      auth.updateUser(user);
      await client.resetQueries({ queryKey: ['feed'] });
      close();
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Make the loop yours." close={close}>
      <p className="muted">More of what catches your eye, with something fresh mixed in.</p>
      <form
        className="form-stack"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <label className="checkbox">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
          />
          Personalise my feed using watch time, skips, saves and conversations.
        </label>
        <p className="tiny muted">
          Optional. Your budget and search filters always come first. Turning this off stops new
          interest tracking and clears the learned starting point. Hidden adverts stay hidden.
        </p>
        <button className="button dark" disabled={busy || !online}>
          {busy ? 'Saving…' : 'Save feed preferences'}
        </button>
        <button
          className="text-button"
          type="button"
          disabled={busy || !online}
          onClick={() => {
            setBusy(true);
            setError('');
            clearSignals();
            void request('/feed/preferences', { method: 'DELETE' })
              .then(async () => {
                await client.resetQueries({ queryKey: ['feed'] });
                setNotice(
                  'Your learned interests have been reset. Your saved listings and hidden adverts are unchanged.',
                );
              })
              .catch((problem: Error) => setError(problem.message))
              .finally(() => setBusy(false));
          }}
        >
          Reset learned interests
        </button>
        {notice && (
          <p className="notice" role="status">
            {notice}
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </form>
    </Modal>
  );
}
