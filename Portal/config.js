/*
 * LOCAL DEVELOPMENT ONLY.
 *
 * Deployments do not use this file. build.js generates dist/config.js from
 * environment variables (PORTAL_AUTH_BASE_URL, PORTAL_GLP1_URL,
 * PORTAL_READMISSIONS_URL) at build time - see Portal/.env.example - so no
 * deployed origin is committed here.
 *
 * `npx serve Portal` serves this file, pointed at the local stack.
 *
 * AUTH_BASE_URL is the Readmissions API — it is the single issuer of tokens for
 * both products. This portal's own origin must appear in that service's
 * ALLOWED_ORIGINS, or the browser blocks the sign-in call and it looks like the
 * service is down.
 *
 * `key` MUST match the string the auth service puts in the token's `app_access`
 * list, or the tile never appears.
 */
window.__PORTAL_CONFIG__ = {
  AUTH_BASE_URL: 'http://localhost:8001',

  APPS: [
    {
      key: 'glp1',
      name: 'GLP-1 Analytics',
      blurb: 'Treatment response, adherence and payer return on investment.',
      // Origin only - no path, no trailing slash. Leave blank and the tile
      // reports itself as not configured instead of navigating nowhere.
      url: 'http://localhost:5173',
      handoff: 'fragment',        // 'fragment' -> #token=...   'query' -> ?token=...
    },
    {
      key: 'readmissions',
      name: 'Readmission Risk',
      blurb: 'Discharge risk scoring, weekly monitoring and the clinician console.',
      url: 'http://localhost:5174',
      handoff: 'fragment',
    },
  ],
};
