# Portal — what you need from me, and what I need back

Shared login is deployed and working on the Readmissions backend. It is the only
service that issues tokens now, so **the auth service on your side is no longer
needed** — running two issuers puts us back to two logins.

Your existing `doc@test.com` account works against it unchanged. Same bcrypt
scheme, so nobody has to reset a password.

---

## URLs I'm giving you

| What | URL |
|---|---|
| **Auth + Readmissions API** | `https://preventra-cms-mimic-production.up.railway.app` |
| **Readmissions frontend** (redirect target) | `<FILL IN>` |

Verify the API is up before you build anything:

```bash
curl -s https://preventra-cms-mimic-production.up.railway.app/auth/config
```

Expect `"secret_configured": true`. If it says `false`, tell me — nothing will
work until I fix it.

---

## Before you start — send me your Portal origin

**This will block you on step 1 if we skip it.** My API only accepts browser
requests from origins I have allow-listed. Until yours is on the list, your
login call fails with a CORS error in the console that looks like my service is
down.

Send me both:

- your local dev origin, e.g. `http://localhost:5173`
- the deployed Portal origin once you have it, e.g. `https://portal-xyz.vercel.app`

Scheme + host + port only — no path, no trailing slash. I'll add them and
confirm. You can check it worked:

```bash
curl -s -D - -o /dev/null -X OPTIONS \
  https://preventra-cms-mimic-production.up.railway.app/auth/login \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" | grep -i access-control-allow-origin
```

Your origin echoed back means you're clear. No such header means you're still
blocked.

---

## Step 1 — Login

`POST /auth/login`, no API key, no auth header.

```js
const res = await fetch(`${API}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password }),
});
if (res.status === 401) { /* show "incorrect email or password" */ }
const { token, user } = await res.json();
```

Response:

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 43200,
  "user": {
    "sub": "6aacf23f9088e24368c49583",
    "email": "doc@test.com",
    "role": "Doctor",
    "org_id": "city-hospital",
    "org_name": "City Hospital",
    "app_access": ["glp1", "readmissions"]
  }
}
```

A wrong password and an unregistered email both return `401` with the same
message, deliberately — showing different errors lets anyone enumerate which
accounts exist.

## Step 2 — Signup (same shape)

`POST /auth/signup` returns the identical body, so signup can drop the user
straight into the tile screen rather than bouncing them back to login.

```json
{ "email": "...", "password": "at least 8 chars",
  "role": "Doctor", "org_name": "City Hospital" }
```

`409` if the email is taken, `422` if the email is malformed, the password is
under 8 characters, or the role is blank. `org_name` is optional and gets
slugified into `org_id` (`City Hospital` → `city-hospital`).

## Step 3 — Tile screen

Read `app_access` off the login response. Show the GLP-1 tile if it contains
`glp1`, the Readmissions tile if it contains `readmissions`. New accounts get
both.

You can also read it out of the token without the secret — the payload is
base64, not encrypted:

```js
const claims = JSON.parse(atob(token.split('.')[1]));
```

Fine for deciding which tiles to draw. It proves nothing — anyone can edit a
payload — so every real decision stays with the backends, which check the
signature.

## Step 4 — Redirect

Put the token in the URL **fragment**, not the query string. A fragment is never
sent to the server, so it stays out of access logs, proxy logs and `Referer`
headers.

```js
window.location.href = `${READMISSIONS_URL}/#token=${token}`;
window.location.href = `${GLP1_URL}/#token=${token}`;
```

Same mechanism for both apps, so there is one thing to get right rather than
two.

## Step 5 — Deploy the Portal

Vercel or Netlify, a few minutes. **It has to be hosted** — if it only runs on
your laptop there is no end-to-end demo. Send me the deployed origin the moment
it exists so I can add it.

---

## What I need back from you

1. **Your Portal origin** — localhost now, deployed as soon as you have it.
   Blocks everything else.
2. **The GLP-1 frontend URL**, so the Portal has a second redirect target.
3. **Confirmation GLP-1 is deployed**, or that the demo runs locally. Mine is
   hosted; if GLP-1 is on your laptop the click-through breaks on the day.
4. **Confirmation you've stopped issuing tokens** on your side.

---

## Reference

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /auth/signup` | none | create account, returns a token |
| `POST /auth/login` | none | returns a token |
| `GET /auth/me` | `Bearer` | current account, read from the database |
| `GET /auth/config` | none | is the service configured; carries no secret |

Token: HS256, valid **12 hours**, no refresh flow — so that's also the session
length. Claims:

```json
{ "sub": "<account id>", "email": "...", "role": "...",
  "org_id": "...", "app_access": ["glp1", "readmissions"], "exp": 1789945409 }
```

`sub` is the `_id` of the `shared_identity.users` document, as a string.

## If something breaks

| Symptom | Cause |
|---|---|
| CORS error in the console | your origin isn't allow-listed — send it to me |
| `404` | wrong path; there is no `/api` prefix on `/auth/*` |
| `401 Invalid or missing API key` | you hit an `/api/*` route, not `/auth/*` |
| `500` | secret missing on my side — send me `/auth/config` output |
| `503` | my backend can't reach MongoDB — my problem, tell me |
| Works in curl, fails in browser | CORS. Always CORS. |

Signup is open by design for the demo — anyone reaching the endpoint can create
an account. Not suitable for real patient data.
