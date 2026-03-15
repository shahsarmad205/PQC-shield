import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { api, TOKEN_KEY } from './api';

const EXPIRY_BUFFER_MINUTES = 5;

/** Decode JWT payload (client-side only; used for expiry check). */
function getTokenExpiry(token: string): number | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const decoded = JSON.parse(atob(payload)) as { exp?: number };
    return typeof decoded.exp === 'number' ? decoded.exp : null;
  } catch {
    return null;
  }
}

/** True if token is expired or expires within `withinMinutes`. */
function isTokenExpiredOrExpiringSoon(
  token: string,
  withinMinutes: number
): boolean {
  const exp = getTokenExpiry(token);
  if (exp == null) return true;
  const nowSec = Math.floor(Date.now() / 1000);
  const bufferSec = withinMinutes * 60;
  return exp <= nowSec + bufferSec;
}

export type User = {
  id: string;
  email: string;
  full_name: string;
  organization: { id: string; name: string } | null;
};

type AuthContextValue = {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [fetchedUser, setFetchedUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY)
  );

  const user = token ? fetchedUser : null;

  const fetchMe = useCallback(async (authToken: string) => {
    const { data } = await api.get<{
      id: string;
      email: string;
      full_name: string;
      organization: { id: string; name: string } | null;
    }>('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    setFetchedUser({
      id: data.id,
      email: data.email,
      full_name: data.full_name,
      organization: data.organization ?? null,
    });
  }, []);

  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setFetchedUser(null);
  }, []);

  // On load: validate stored token with GET /me; clear if expired or within 5 min of expiry
  useEffect(() => {
    if (!token) return;
    if (isTokenExpiredOrExpiringSoon(token, EXPIRY_BUFFER_MINUTES)) {
      setTimeout(() => clearAuth(), 0);
      return;
    }
    fetchMe(token).catch(() => setTimeout(() => clearAuth(), 0));
  }, [token, fetchMe, clearAuth]);

  const login = useCallback(
    async (email: string, password: string) => {
      const form = new URLSearchParams();
      form.set('username', email);
      form.set('password', password);
      const { data } = await api.post<{ access_token: string }>(
        '/api/v1/auth/login',
        form,
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      );
      localStorage.setItem(TOKEN_KEY, data.access_token);
      setToken(data.access_token);
      await fetchMe(data.access_token);
    },
    [fetchMe]
  );

  const logout = useCallback(() => {
    clearAuth();
    window.location.href = '/login';
  }, [clearAuth]);

  const isAuthenticated =
    !!token &&
    !!user &&
    !isTokenExpiredOrExpiringSoon(token, EXPIRY_BUFFER_MINUTES);

  const value: AuthContextValue = {
    user,
    token,
    login,
    logout,
    isAuthenticated,
  };

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
