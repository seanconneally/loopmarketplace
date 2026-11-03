import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { request, restoreSession, setToken, type AuthResult, type User } from '../api/client';

type AuthState = {
  user: User | null;
  signIn: (data: AuthResult) => void;
  updateUser: (user: User) => void;
  signOut: () => Promise<void>;
};
const Context = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, updateUser] = useState<User | null>(null);
  useEffect(() => {
    let mounted = true;
    void restoreSession().then((data) => {
      if (mounted && data) updateUser(data.user);
    });
    return () => {
      mounted = false;
    };
  }, []);
  const signIn = (data: AuthResult) => {
    setToken(data.access_token);
    updateUser(data.user);
  };
  const signOut = async () => {
    await request('/auth/logout', { method: 'POST' });
    setToken(null);
    updateUser(null);
  };
  return (
    <Context.Provider value={{ user, signIn, signOut, updateUser }}>{children}</Context.Provider>
  );
}

export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error('AuthProvider missing');
  return value;
}
