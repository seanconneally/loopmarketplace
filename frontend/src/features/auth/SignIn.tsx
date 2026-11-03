import { useState, type FormEvent } from 'react';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { mutation, request, type AuthResult, type User } from '../../api/client';
import { useAuth } from '../../shared/Auth';
import { Modal } from '../../shared/Modal';
import { BrandMark } from '../../shared/Brand';

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
    <Modal
      title={challenge === null ? 'Welcome to Loop Marketplace.' : 'Verify your number.'}
      close={close}
    >
      <div className="auth-intro">
        <BrandMark />
        <div>
          <span className="eyebrow">
            {challenge === null ? 'MAKE YOURSELF AT HOME' : 'ONE MORE STEP'}
          </span>
          <p>
            {challenge === null
              ? 'Save the ones you love. Speak to the seller. Find your next find.'
              : 'Enter your code and tell us a little about yourself.'}
          </p>
        </div>
      </div>
      <div className="auth-progress" aria-label={`Step ${challenge === null ? 1 : 2} of 2`}>
        <span className="complete" />
        <span className={challenge === null ? '' : 'complete'} />
      </div>
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
            autoComplete="tel"
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
                autoFocus
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
              Personalise my feed using watch time and interactions.
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
      <p className="auth-privacy">
        <ShieldCheck size={15} />
        Your number stays private. No public contact details.
      </p>
      {challenge !== null && (
        <button
          type="button"
          className="text-button"
          disabled={busy}
          onClick={() => {
            setChallenge(null);
            setCode('');
            setError('');
          }}
        >
          Use a different phone number
        </button>
      )}
    </Modal>
  );
}
