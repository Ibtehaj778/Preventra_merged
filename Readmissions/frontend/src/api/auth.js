// Shared-login token handling.
//
// This app does not sign anyone in. The portal does that, then redirects here
// with the token attached. All this module does is catch it on arrival, keep it
// for the session, and hand it to the API client.
//
// The token arrives in the URL *fragment* (`#token=...`), not the query string.
// A fragment is never sent to the server, so it stays out of access logs, proxy
// logs and Referer headers. It is stripped from the address bar immediately, so
// it cannot be copied off a shared screen or saved into a bookmark.

const STORAGE_KEY = 'shared_auth_token';

// sessionStorage, not localStorage: the token dies with the tab. A demo laptop
// left open does not stay signed in, and there is no sign-out flow yet to undo
// it if it did.
const store = () => {
  try {
    return window.sessionStorage;
  } catch {
    return null; // private mode, or a blocked origin - degrade, do not throw
  }
};

/** Read a `token` value out of the URL fragment, if one is there. */
function tokenFromFragment() {
  const hash = window.location.hash || '';
  if (!hash.includes('token=')) return null;
  const value = new URLSearchParams(hash.replace(/^#/, '')).get('token');
  return value && value.trim() ? value.trim() : null;
}

/**
 * Capture a token handed over by the portal. Call once, before the app renders.
 *
 * Returns true when a token was captured on this load, so a caller can tell a
 * fresh hand-off from an existing session if it ever needs to.
 */
export function captureTokenFromUrl() {
  const token = tokenFromFragment();
  if (!token) return false;

  store()?.setItem(STORAGE_KEY, token);

  // Drop the fragment without adding a history entry, so Back does not walk the
  // user onto a URL that still carries their credential.
  const { pathname, search } = window.location;
  window.history.replaceState(null, '', `${pathname}${search}`);
  return true;
}

/** The token for this session, or null when nobody arrived through the portal. */
export function getToken() {
  return store()?.getItem(STORAGE_KEY) || null;
}

export function clearToken() {
  store()?.removeItem(STORAGE_KEY);
}

/**
 * Claims carried by the current token, without verifying it.
 *
 * Read-only convenience for the UI - to greet someone by name, or to hide a
 * control they cannot use. It proves nothing: the payload is base64, not
 * ciphertext, and anyone can edit it. Every decision that matters is made by
 * the backend, which checks the signature. Never gate anything real on this.
 */
export function readClaims() {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
  } catch {
    return null;
  }
}
