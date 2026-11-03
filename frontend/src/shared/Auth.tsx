import { setSignalOwner } from '../features/feed/signals';
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { request, restoreSession, setToken, type AuthResult, type User } from '../api/client';
import { useOnlineStatus } from './useOnlineStatus';
import { clearMemberDrafts } from './draftStorage';

type AuthState = {
  user: User | null;
  status: 'checking' | 'authenticated' | 'signed-out' | 'unavailable';
  retrySession: () => void;
  signIn: (data: AuthResult) => void;
  updateUser: (user: User) => void;
  signOut: () => Promise<void>;
};
const Context = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, updateUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthState['status']>('checking');
  const [attempt, retry] = useState(0);
  const version = useRef(0);
  const online = useOnlineStatus();
  useEffect(() => {
    let mounted = true;
    const initialVersion = version.current;
    if (!online) {
      setStatus((current) => (current === 'authenticated' ? current : 'unavailable'));
      return;
    }
    setStatus((current) => (current === 'authenticated' ? current : 'checking'));
    void restoreSession()
      .then((data) => {
        if (mounted && initialVersion === version.current) {
          updateUser(data?.user || null);
          setStatus(data ? 'authenticated' : 'signed-out');
        }
      })
      .catch(() => {
        if (mounted && initialVersion === version.current)
          setStatus((current) => (current === 'authenticated' ? current : 'unavailable'));
      });
    return () => {
      mounted = false;
    };
  }, [attempt, online]);
  useEffect(() => {
    setSignalOwner(user?.analytics_consent ? user.id : null);
  }, [user?.id, user?.analytics_consent]);
  const signIn = (data: AuthResult) => {
    version.current++;
    setSignalOwner(data.user.analytics_consent ? data.user.id : null);
    setToken(data.access_token);
    updateUser(data.user);
    setStatus('authenticated');
  };
  const signOut = async () => {
    await request('/auth/logout', { method: 'POST' });
    version.current++;
    if (user) clearMemberDrafts(user.id);
    setSignalOwner(null);
    setToken(null);
    updateUser(null);
    setStatus('signed-out');
  };
  return (
    <Context.Provider
      value={{
        user,
        status,
        retrySession: () => retry((value) => value + 1),
        signIn,
        signOut,
        updateUser: (member) => {
          setSignalOwner(member.analytics_consent ? member.id : null);
          updateUser(member);
        },
      }}
    >
      {children}
    </Context.Provider>
  );
}

export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error('AuthProvider missing');
  return value;
}
