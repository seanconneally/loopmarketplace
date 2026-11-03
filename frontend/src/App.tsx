import { useState, type FormEvent } from 'react';
import { Link, NavLink, Route, Routes, useNavigate } from 'react-router-dom';
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
} from 'lucide-react';
import { mutation, request, type Conversation, type Listing, type User } from './api/client';
import { useAuth } from './shared/Auth';
import { useRealtime } from './shared/useRealtime';
import { Modal } from './shared/Modal';
import { SignIn } from './features/auth/SignIn';
import { Feed } from './features/feed/Feed';
import { Upload } from './features/listing/Upload';
import { Saved } from './features/listing/Saved';
import { SellerDashboard } from './features/listing/SellerDashboard';
import { Chat } from './features/chat/Chat';
import { Dealer } from './features/listing/Dealer';
import { Moderation } from './features/moderation/Moderation';

export default function App() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [signIn, setSignIn] = useState(false);
  const [upload, setUpload] = useState(false);
  const [profile, setProfile] = useState(false);
  const [conversation, setConversation] = useState<string | null>(null);
  const [error, setError] = useState('');
  useRealtime(auth.user?.id);
  const requireAuth = () => setSignIn(true);
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
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" to="/" aria-label="Motorloop home">
          <span className="brand-symbol">
            m<ArrowUpRight size={19} />
          </span>
          motorloop<span className="brand-period">.</span>
        </Link>
        <div className="sidebar-section-label">FIND YOUR NEXT DRIVE</div>
        <nav className="main-nav">
          <NavLink to="/" end>
            <Compass size={20} />
            Discover
            <span className="nav-indicator" />
          </NavLink>
          <NavLink
            to="/saved"
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
            <NavLink to="/dealer">
              <Plus size={20} />
              Dealer studio
            </NavLink>
          )}
          {auth.user && (
            <NavLink to="/my-cars">
              <Sparkles size={20} />
              My cars
            </NavLink>
          )}
          {auth.user?.role === 'admin' && (
            <NavLink to="/moderation">
              <ShieldCheck size={20} />
              Review queue
            </NavLink>
          )}
        </nav>
        <div className="sidebar-sell">
          <span className="sell-card-icon">
            <Sparkles size={22} />
          </span>
          <h3>
            Ready for a<br />
            new chapter?
          </h3>
          <p>
            Your car has a story.
            <br />
            Show it in a short video.
          </p>
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
            <ShieldCheck size={16} />A safer way to meet
          </Link>
          <p>
            Made for the road ahead.
            <br />© 2026 Motorloop
          </p>
          <span className="development-label">LOCAL DEVELOPMENT</span>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            Marketplace <span>/</span>
            <strong>Cars</strong>
          </div>
          <div className="topbar-actions">
            <span className="region">
              <MapPin size={15} />
              Dublin, IE
            </span>
            <div className="topbar-divider" />
            {auth.user ? (
              <>
                <button className="account-button" onClick={() => setProfile(true)}>
                  <span>{auth.user.name.slice(0, 1)}</span>
                  {auth.user.name}
                </button>
                <button
                  className="icon-button logout"
                  aria-label="Sign out"
                  onClick={() =>
                    void auth.signOut().then(() => {
                      queryClient.clear();
                      navigate('/');
                    })
                  }
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
        <main className="page-content">
          {error && (
            <div className="notice error" role="alert">
              {error}
              <button className="text-button" onClick={() => setError('')}>
                Dismiss
              </button>
            </div>
          )}
          <Routes>
            <Route
              path="/my-cars"
              element={
                auth.user ? (
                  <SellerDashboard
                    create={() => (auth.user?.adult_declared ? setUpload(true) : setProfile(true))}
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
                auth.user?.role === 'admin' ? <Moderation /> : <SignedOut signIn={requireAuth} />
              }
            />
            <Route path="/safety" element={<Safety />} />
            <Route
              path="*"
              element={
                <div className="empty-card">
                  <h1>That road doesn’t lead anywhere.</h1>
                  <Link className="button dark" to="/">
                    Back to discover
                  </Link>
                </div>
              }
            />
          </Routes>
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
        <button onClick={() => (auth.user ? setProfile(true) : requireAuth())}>
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
            <Sparkles size={16} />
            My cars · Manage your adverts
          </Link>
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
              You can withdraw optional analytics consent at any time. Export and deletion workflows
              are specified in the project privacy plan and require implementation before public
              launch.
            </p>
          </form>
        </Modal>
      )}
    </div>
  );
}

function SignedOut({ signIn }: { signIn: () => void }) {
  return (
    <div className="empty-card">
      <UserRound size={38} />
      <h1>A little introduction first.</h1>
      <p>Sign in with your phone to continue.</p>
      <button className="button dark" onClick={signIn}>
        Sign in
      </button>
    </div>
  );
}
function Safety() {
  return (
    <article className="safety-page">
      <div className="eyebrow">A SAFER WAY TO MEET</div>
      <h1>
        Good instincts.
        <br />
        Better viewings.
      </h1>
      <p className="intro">
        Finding a car should feel exciting. A few simple habits help keep it that way.
      </p>
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
