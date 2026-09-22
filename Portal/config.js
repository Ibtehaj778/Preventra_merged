/*
 * Portal configuration — the only file that differs between environments.
 *
 * index.html reads this and falls back to its own built-in defaults if the file
 * is missing, so the portal still renders (and says what is unconfigured)
 * rather than showing a blank page.
 *
 * Local development: copy this file, change the three URLs, and do not commit
 * the change. Deployment: set the values below to the deployed origins.
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
  AUTH_BASE_URL: 'https://preventra-cms-mimic-production.up.railway.app',

  APPS: [
    {
      key: 'glp1',
      name: 'GLP-1 Analytics',
      blurb: 'Treatment response, adherence and payer return on investment.',
      // Origin only - no path, no trailing slash. Leave blank and the tile
      // reports itself as not configured instead of navigating nowhere.
      url: 'https://glp-1-adherence.vercel.app',
      handoff: 'fragment',        // 'fragment' -> #token=...   'query' -> ?token=...
    },
    {
      key: 'readmissions',
      name: 'Readmission Risk',
      blurb: 'Discharge risk scoring, weekly monitoring and the clinician console.',
      url: 'https://preventra-cms-mimic.vercel.app',
      handoff: 'fragment',
    },
  ],
};
