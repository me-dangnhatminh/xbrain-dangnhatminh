/**
 * useAuth — global authentication state hook.
 *
 * Wraps the Cognito service and provides:
 *  - `user`      — current AuthUser or null
 *  - `loading`   — true while restoring session on boot
 *  - `login()`   — sign in with Cognito
 *  - `logout()`  — sign out and clear state
 */

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { AuthUser, signIn, signOut, getCurrentSession } from '@/lib/cognito';

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore session from localStorage on boot
  useEffect(() => {
    getCurrentSession()
      .then((session) => setUser(session))
      .finally(() => setLoading(false));
  }, []);

  const login = async (username: string, password: string) => {
    const authUser = await signIn(username, password);
    setUser(authUser);
  };

  const logout = () => {
    signOut();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
