import { useState, type FormEvent } from 'react';
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  ArrowUpRight,
  Bookmark,
  Compass,
  LogOut,
  MapPin,
  MessageCircle,
  Plus,
  ShieldCheck,
  Sparkles,
  UserRound,
  ChevronDown,
  CarFront,
  LoaderCircle,
} from 'lucide-react';
import { mutation, request, type Conversation, type Listing, type User } from './api/client';
import { useAuth } from './shared/Auth';
import { useRealtime } from './shared/useRealtime';
import { Modal } from './shared/Modal';
import { BrandMark, LoopArtwork } from './shared/Brand';
import { PageHeading } from './shared/PageHeading';
import { ErrorBoundary } from './shared/ErrorBoundary';
import { ConnectionStatus } from './shared/ConnectionStatus';
import { useOnlineStatus } from './shared/useOnlineStatus';
import { SignIn } from './features/auth/SignIn';
import { Feed } from './features/feed/Feed';
import { Upload } from './features/listing/Upload';
import { Saved } from './features/listing/Saved';
import { ListingPage } from './features/listing/ListingPage';
import { SellerDashboard } from './features/listing/SellerDashboard';
import { Chat } from './features/chat/Chat';
import { Dealer } from './features/listing/Dealer';
import { Moderation } from './features/moderation/Moderation';

export default function App() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const online = useOnlineStatus();
  const sessionPending = auth.status === 'checking' || auth.status === 'unavailable';
  const privatePage = ['/my-cars', '/saved', '/messages', '/dealer', '/moderation'].includes(
    location.pathname,
  );
  const section = location.pathname.startsWith('/cars/')
    ? 'Advert details'
    : {
        '/': 'Discover',
        '/saved': 'Saved cars',
        '/my-cars': 'My cars',
        '/messages': 'Messages',
        '/dealer': 'Dealer studio',
        '/moderation': 'Review queue',
        '/safety': 'Safety centre',
      }[location.pathname] || 'Marketplace';
  const [signIn, setSignIn] = useState(false);
  const [upload, setUpload] = useState(false);
  const [profile, setProfile] = useState(false);
  const [conversation, setConversation] = useState<string | null>(null);
  const [error, setError] = useState('');
  useRealtime(auth.user?.id);
  const requireAuth = () => {
    if (auth.status === 'checking') return;
    if (auth.status === 'unavailable') {
      auth.retrySession();
      return;
    }
    setSignIn(true);
  };
  async function message(listing: Listing) {
    if (!auth.user) {
      requireAuth();
      return;
    }
    try {
      const result = await request<Conversation>(
        '/conversations',
        mutation({ listing_id: listing.id }),
      );
      setConversation(result.id);
      await queryClient.invalidateQueries({ queryKey: ['conversations'] });
      navigate('/messages');
    } catch (problem) {
      setError((problem as Error).message);
    }
  }
  async function updateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const user = await request<User>('/users/me', {
        method: 'PATCH',
        body: JSON.stringify({
          name: String(form.get('name')),
          adult_declared: form.get('adult') === 'on',
          analytics_consent: form.get('analytics') === 'on',
        }),
      });
      auth.updateUser(user);
      setProfile(false);
    } catch (problem) {
      setError((problem as Error).message);
    }
  }
  async function signOut() {
    try {
      await auth.signOut();
      setProfile(false);
      queryClient.clear();
      navigate('/');
    } catch (problem) {
      setProfile(false);
      setError((problem as Error).message);
    }
  }
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link className="brand" to="/" aria-label="Motorloop home">
          <BrandMark className="brand-symbol" />
          <span className="brand-word">
            motorloop<span className="brand-period">.</span>
          </span>
        </Link>
        <div className="sidebar-section-label">YOUR MARKETPLACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          <NavLink to="/" end title="Discover">
            <Compass size={20} />
            Discover
            <span className="nav-indicator" />
          </NavLink>
          <NavLink
            to="/saved"
            title="Saved cars"
            onClick={(event) => {
              if (!auth.user) {
                event.preventDefault();
                requireAuth();
              }
            }}
          >
            <Bookmark size={20} />
            Saved cars
          </NavLink>
          <NavLink
            to="/messages"
            title="Messages"
            onClick={(event) => {
              if (!auth.user) {
                event.preventDefault();
                requireAuth();
              }
            }}
          >
            <MessageCircle size={20} />
            Messages
          </NavLink>
          {auth.user?.role === 'dealer' && (
            <NavLink to="/dealer" title="Dealer studio">
              <Plus size={20} />
              Dealer studio
            </NavLink>
          )}
          {auth.user && (
            <NavLink to="/my-cars" title="My cars">
              <CarFront size={20} />
              My cars
            </NavLink>
          )}
          {auth.user?.role === 'admin' && (
            <NavLink to="/moderation" title="Review queue">
              <ShieldCheck size={20} />
              Review queue
            </NavLink>
          )}
        </nav>
        <div className="sidebar-sell">
          <LoopArtwork />
          <span className="sell-card-icon">
            <Sparkles size={22} />
          </span>
          <h3>
            Your car.
            <br />
            In the loop.
          </h3>
          <p>One walkaround. A better first impression.</p>
          <button
            onClick={() => {
              if (!auth.user) requireAuth();
              else if (!auth.user.adult_declared) setProfile(true);
              else setUpload(true);
            }}
          >
            Sell your car <ArrowUpRight size={16} />
          </button>
        </div>
        <div className="sidebar-bottom">
          <Link to="/safety">
            <ShieldCheck size={17} />
            Safety centre <ArrowUpRight size={14} />
          </Link>
          <span className="development-label">
            <span />
            Local development
          </span>
          <p>© 2026 Motorloop</p>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <Link to="/" className="mobile-brand" aria-label="Motorloop home">
            <BrandMark />
            motorloop<span>.</span>
          </Link>
          <div className="breadcrumb">
            <span className="breadcrumb-home">Marketplace</span>
            <span>/</span>
            <strong>{section}</strong>
          </div>
          <div className="topbar-actions">
            <span className="region">
              <MapPin size={15} />
              Dublin, IE
            </span>
            <div className="topbar-divider" />
            {auth.status === 'checking' ? (
              <span className="session-indicator" role="status">
                <LoaderCircle size={17} className="spinning" /> Checking your session…
              </span>
            ) : auth.status === 'unavailable' ? (
              <button
                className="text-button session-indicator"
                onClick={auth.retrySession}
                disabled={!online}
              >
                Retry session
              </button>
            ) : auth.user ? (
              <>
                <button className="account-button" onClick={() => setProfile(true)}>
                  <span>{auth.user.name.slice(0, 1)}</span>
                  {auth.user.name}
                  <ChevronDown size={14} />
                </button>
                <button
                  className="icon-button logout"
                  aria-label="Sign out"
                  onClick={() => void signOut()}
                >
                  <LogOut size={17} />
                </button>
              </>
            ) : (
              <button className="signin-button" onClick={requireAuth}>
                <UserRound size={17} />
                Sign in
              </button>
            )}
            <button
              className="button dark top-sell"
              disabled={sessionPending}
              onClick={() => {
                if (!auth.user) requireAuth();
                else if (!auth.user.adult_declared) setProfile(true);
                else setUpload(true);
              }}
            >
              <Plus size={16} />
              Sell a car
            </button>
          </div>
        </header>
        <ConnectionStatus />
        <main className="page-content" id="main-content" tabIndex={-1}>
          {error && (
            <div className="notice error" role="alert">
              {error}
              <button className="text-button" onClick={() => setError('')}>
                Dismiss
              </button>
            </div>
          )}
          <ErrorBoundary
            resetKey={location.pathname}
            onReset={() => void queryClient.resetQueries()}
          >
            {privatePage && sessionPending ? (
              <div className="empty-card session-state" role="status">
                {auth.status === 'checking' ? (
                  <>
                    <LoaderCircle size={36} className="spinning" />
                    <h1>Checking your session…</h1>
                    <p>Getting your account ready.</p>
                  </>
                ) : (
                  <>
                    <UserRound size={36} />
                    <h1>Your session is temporarily unavailable.</h1>
                    <p>
                      {online
                        ? 'We couldn’t check your account. Please try again.'
                        : 'Reconnect to check your account. This does not mean you have been signed out.'}
                    </p>
                    <button className="button dark" disabled={!online} onClick={auth.retrySession}>
                      Retry session
                    </button>
                  </>
                )}
              </div>
            ) : (
              <Routes>
                <Route
                  path="/cars/:id"
                  element={
                    <ListingPage
                      requireAuth={requireAuth}
                      message={(listing) => void message(listing)}
                    />
                  }
                />
                <Route
                  path="/my-cars"
                  element={
                    auth.user ? (
                      <SellerDashboard
                        create={() =>
                          auth.user?.adult_declared ? setUpload(true) : setProfile(true)
                        }
                      />
                    ) : (
                      <SignedOut signIn={requireAuth} />
                    )
                  }
                />
                <Route
                  path="/"
                  element={
                    <Feed requireAuth={requireAuth} message={(listing) => void message(listing)} />
                  }
                />
                <Route
                  path="/saved"
                  element={
                    auth.user ? (
                      <Saved message={(listing) => void message(listing)} />
                    ) : (
                      <SignedOut signIn={requireAuth} />
                    )
                  }
                />
                <Route
                  path="/messages"
                  element={
                    auth.user ? (
                      <Chat initialConversation={conversation} />
                    ) : (
                      <SignedOut signIn={requireAuth} />
                    )
                  }
                />
                <Route
                  path="/dealer"
                  element={
                    auth.user?.role === 'dealer' ? <Dealer /> : <SignedOut signIn={requireAuth} />
                  }
                />
                <Route
                  path="/moderation"
                  element={
                    auth.user?.role === 'admin' ? (
                      <Moderation />
                    ) : (
                      <SignedOut signIn={requireAuth} />
                    )
                  }
                />
                <Route path="/safety" element={<Safety />} />
                <Route
                  path="*"
                  element={
                    <div className="empty-card">
                      <Compass size={38} />
                      <span className="eyebrow">PAGE NOT FOUND</span>
                      <h1>Let’s get you back on track.</h1>
                      <p>This link may have changed. There’s plenty more to discover.</p>
                      <Link className="button dark" to="/">
                        Back to discover
                      </Link>
                    </div>
                  }
                />
              </Routes>
            )}
          </ErrorBoundary>
        </main>
      </div>
      <nav className="mobile-nav">
        <NavLink to="/" end aria-label="Discover">
          <Compass size={22} />
          <span>Discover</span>
        </NavLink>
        <NavLink to="/saved" aria-label="Saved cars">
          <Bookmark size={22} />
          <span>Saved</span>
        </NavLink>
        <button
          onClick={() => {
            if (!auth.user) requireAuth();
            else if (!auth.user.adult_declared) setProfile(true);
            else setUpload(true);
          }}
        >
          <Plus size={23} />
          <span>Sell</span>
        </button>
        <NavLink to="/messages" aria-label="Messages">
          <MessageCircle size={22} />
          <span>Inbox</span>
        </NavLink>
        <button
          disabled={sessionPending}
          onClick={() => (auth.user ? setProfile(true) : requireAuth())}
        >
          <UserRound size={22} />
          <span>Account</span>
        </button>
      </nav>
      {signIn && (
        <SignIn
          close={() => {
            setSignIn(false);
            void queryClient.invalidateQueries({ queryKey: ['feed'] });
          }}
        />
      )}
      {upload && (
        <Upload
          close={() => setUpload(false)}
          complete={() => {
            void queryClient.invalidateQueries({ queryKey: ['feed'] });
            void queryClient.invalidateQueries({ queryKey: ['seller-listings'] });
          }}
        />
      )}
      {profile && auth.user && (
        <Modal title="Your Motorloop profile" close={() => setProfile(false)}>
          <Link
            className="button dark profile-cars"
            to="/my-cars"
            onClick={() => setProfile(false)}
          >
            <CarFront size={18} />
            Manage your adverts
          </Link>
          <p className="muted">Your profile, preferences and permissions. All in one place.</p>
          <form className="form-stack" onSubmit={(event) => void updateProfile(event)}>
            <label>
              Your name
              <input
                name="name"
                defaultValue={auth.user.name}
                minLength={2}
                maxLength={80}
                required
              />
            </label>
            <label className="checkbox">
              <input name="adult" type="checkbox" defaultChecked={auth.user.adult_declared} />I am
              18 or older and can advertise my own car.
            </label>
            <label className="checkbox">
              <input
                name="analytics"
                type="checkbox"
                defaultChecked={auth.user.analytics_consent}
              />
              Allow optional feed analytics.
            </label>
            <button className="button primary">Save profile</button>
            <p className="tiny muted">
              Analytics are optional and can be switched off at any time. This local preview does
              not yet support account export or deletion.
            </p>
          </form>
          <button className="button profile-signout" onClick={() => void signOut()}>
            <LogOut size={16} />
            Sign out
          </button>
        </Modal>
      )}
    </div>
  );
}

function SignedOut({ signIn }: { signIn: () => void }) {
  return (
    <div className="empty-card">
      <UserRound size={38} />
      <span className="eyebrow">YOUR MOTORLOOP</span>
      <h1>Make yourself at home.</h1>
      <p>Sign in to save cars, contact sellers and manage your adverts.</p>
      <button className="button dark" onClick={signIn}>
        Sign in
      </button>
    </div>
  );
}
function Safety() {
  return (
    <article className="safety-page">
      <div className="safety-hero">
        <div className="safety-hero-icon">
          <ShieldCheck size={38} />
        </div>
        <PageHeading
          eyebrow="THE SAFETY CENTRE"
          title={
            <>
              A little care.
              <br />
              <span>A better experience.</span>
            </>
          }
          description="Practical advice for meeting, inspecting and buying with confidence."
        />
        <LoopArtwork />
      </div>
      {[
        [
          'Meet somewhere public.',
          'Choose a busy, well-lit place during the day. Bring someone with you and tell a friend where you are going.',
        ],
        [
          'See the car before you pay.',
          'Never send a deposit to reserve an unseen car. Inspect the vehicle, its identity and the seller’s documents before agreeing a sale.',
        ],
        [
          'Keep the conversation here.',
          'Be cautious of payment links, urgent requests and courier stories. Your phone number and email stay private unless you choose to share them.',
        ],
        [
          'Trust the pause.',
          'If something feels wrong, step back. You can report a listing or block a member from the conversation.',
        ],
      ].map(([title, body], index) => (
        <section key={title}>
          <span>0{index + 1}</span>
          <div>
            <h2>{title}</h2>
            <p>{body}</p>
          </div>
        </section>
      ))}
      <div className="notice">
        <ShieldCheck size={20} />
        Motorloop helps you connect. Payments, inspections and ownership transfers happen between
        you and the seller in person.
      </div>
    </article>
  );
}
