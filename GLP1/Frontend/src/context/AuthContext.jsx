import { createContext, useContext, useState, useCallback } from 'react';
import { api } from '../data/api';

const AuthContext = createContext(null);

const TOKEN_KEY = 'glp1_token';
const USER_KEY  = 'glp1_user';

// The portal is the shared sign-in surface. When it is configured, it is where
// people arrive from and where signing out sends them. Left unset (local
// development), this app falls back to its own /login screen.
export const PORTAL_URL = (import.meta.env.VITE_PORTAL_URL || '').replace(/\/$/, '');

function readIncomingToken() {
  const hash = window.location.hash || '';
  if (!hash.includes('token=')) return null;

  const token = new URLSearchParams(hash.replace(/^#/, '')).get('token');
  if (!token) return null;

  history.replaceState(null, '', window.location.pathname + window.location.search);
  return token;
}

function decodeClaims(token) {
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch {
    return null;
  }
}

/** A token past its expiry is not a session. Treating it as one gives you a
 *  dashboard that renders and then 401s on every request - and, once signing
 *  out redirects to the portal, an app that bounces back and forth. */
function isUsable(token) {
  if (!token) return false;
  const exp = decodeClaims(token)?.exp;
  return typeof exp !== 'number' || exp * 1000 > Date.now();
}

const _incomingToken = readIncomingToken();

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => {
    if (_incomingToken) return _incomingToken;
    const stored = localStorage.getItem(TOKEN_KEY);
    if (isUsable(stored)) return stored;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    return null;
    });
  const [user, setUser] = useState(() => {
    if (_incomingToken) {
        const claims = decodeClaims(_incomingToken);
        if (claims) {
        const incomingUser = {
            id:         claims.sub,
            email:      claims.email,
            role:       claims.role,
            org_id:     claims.org_id,
            app_access: claims.app_access || [],
        };
        localStorage.setItem(TOKEN_KEY, _incomingToken);
        localStorage.setItem(USER_KEY, JSON.stringify(incomingUser));
        return incomingUser;
        }
    }
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch {
        localStorage.removeItem(USER_KEY);
        return null;
    }
    });

  const _persist = (accessToken, userObj) => {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(USER_KEY, JSON.stringify(userObj));
    setToken(accessToken);
    setUser(userObj);
  };

  const login = useCallback(async (email, password) => {
    const data = await api.login({ email, password });
    _persist(data.access_token, data.user);
    return data;
  }, []);

  // The auth service requires a role and an organisation at signup - they go
  // into the account and into the token's claims, so they cannot be defaulted
  // here without silently mislabelling every account created from this screen.
  const register = useCallback(async (email, password, role, orgName) => {
    const data = await api.signup({
      email,
      password,
      role,
      org_name: orgName ?? '',
    });
    _persist(data.access_token, data.user);
    return data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
    // Back to the shared sign-in page, and deliberately without a token on the
    // URL - arriving at the portal still signed in is not signing out. Falls
    // through to this app's own /login when no portal is configured.
    // `#signout` tells the portal to drop its own copy of the session too; it
    // keeps a separate one per tab, and a tile screen right after signing out
    // reads as the sign-out having done nothing.
    if (PORTAL_URL) window.location.href = `${PORTAL_URL}/#signout=1`;
  }, []);

  return (
    <AuthContext.Provider
      value={{ token, user, isAuthenticated: !!token, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}