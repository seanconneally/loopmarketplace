import { useState, type FormEvent } from 'react';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { mutation, request, type AuthResult, type User } from '../../api/client';
import { useAuth } from '../../shared/Auth';
import { Modal } from '../../shared/Modal';

export function SignIn({ close }: { close: () => void }) {
  const auth = useAuth();
  const [phone, setPhone] = useState('+353');
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [adult, setAdult] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [challenge, setChallenge] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (challenge === null) {
        const data = await request<{ development_code?: string }>(
          '/auth/otp/request',
          mutation({ phone }),
        );
        setChallenge(data.development_code || '');
      } else {
        const result = await request<AuthResult>('/auth/otp/verify', mutation({ phone, code }));
        auth.signIn(result);
        if (name.trim()) {
          const user = await request<User>('/users/me', {
            method: 'PATCH',
            body: JSON.stringify({ name, adult_declared: adult, analytics_consent: analytics }),
          });
          auth.updateUser(user);
        }
        close();
      }
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Your next drive starts here." close={close}>
      <p className="muted">
        Verify your phone to save favourites, chat with sellers and post a car.
      </p>
      <form onSubmit={(event) => void submit(event)} className="form-stack">
        <label>
          Phone number
          <input
            aria-label="Phone number"
            type="tel"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            required
            placeholder="+353871234567"
            disabled={challenge !== null}
          />
        </label>
        {challenge !== null && (
          <>
            <div className="notice">
              <ShieldCheck size={18} />
              <span>
                Local development — SMS is simulated. Use code{' '}
                <strong>{challenge || 'from your provider'}</strong>.
              </span>
            </div>
            <label>
              Verification code
              <input
                aria-label="Verification code"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                value={code}
                onChange={(event) => setCode(event.target.value)}
                required
                autoComplete="one-time-code"
              />
            </label>
            <label>
              Your name
              <input
                aria-label="Your name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                minLength={2}
                maxLength={80}
                placeholder="What should we call you?"
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={adult}
                onChange={(event) => setAdult(event.target.checked)}
              />{' '}
              I am 18 or older (required to sell).
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={analytics}
                onChange={(event) => setAnalytics(event.target.checked)}
              />{' '}
              Allow optional viewing analytics to improve the feed.
            </label>
          </>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="button primary" disabled={busy}>
          {busy ? 'One moment…' : challenge === null ? 'Continue with phone' : 'Verify & continue'}
          <ArrowRight size={18} />
        </button>
      </form>
      <p className="tiny muted">Your number stays private. Buying and selling happen in person.</p>
    </Modal>
  );
}
