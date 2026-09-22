import { createContext, useContext, useState, useCallback } from 'react';
import { api } from '../data/api';

const AuthContext = createContext(null);

const TOKEN_KEY = 'glp1_token';
const USER_KEY  = 'glp1_user';

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

const _incomingToken = readIncomingToken();

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => {
    if (_incomingToken) return _incomingToken;
    return localStorage.getItem(TOKEN_KEY);
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