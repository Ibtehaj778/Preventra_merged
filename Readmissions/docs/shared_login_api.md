# Shared login — API for the Portal

One account works across GLP-1 and Readmissions. These endpoints are the only
place tokens are issued; each product verifies them independently with the same
secret and never calls back here.

**Base URL:** the deployed Readmissions backend.
**No API key needed.** `/auth/*` is deliberately exempt from the service
`X-API-Key`, so the Portal can call it from its own origin without embedding a
key in the browser.
**CORS:** open (`*`) by default, so no configuration is needed on your side.

---

## `POST /auth/signup`

Creates an account and returns a token for it, so signup lands the user inside a
product rather than back at the login form. No email verification, no domain
checks.

```json
{ "email": "someone@hospital.org", "password": "at-least-8-chars",
  "role": "Doctor", "org_name": "City Hospital" }
```

`org_name` is optional. It is slugified into `org_id` (`City Hospital` →
`city-hospital`), which is what the token carries.

| Code | Meaning |
|---|---|
| `200` | created — body as below |
| `409` | that email already has an account |
| `422` | malformed email, password under 8 characters, or blank role |

## `POST /auth/login`

```json
{ "email": "someone@hospital.org", "password": "at-least-8-chars" }
```

| Code | Meaning |
|---|---|
| `200` | body as below |
| `401` | `{"detail": "Incorrect email or password"}` |

A wrong password and an unregistered email return exactly the same response, on
purpose — anything else lets someone enumerate which accounts exist.

## Response body (both endpoints)

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 43200,
  "user": {
    "sub": "6aacf23f9088e24368c49583",
    "email": "someone@hospital.org",
    "role": "Doctor",
    "org_id": "city-hospital",
    "org_name": "City Hospital",
    "app_access": ["glp1", "readmissions"]
  }
}
```

The `user` object is a convenience — everything in it is also inside the token,
so you can render the tile screen straight from the login response without
decoding anything.

## `GET /auth/me`

`Authorization: Bearer <token>` → the same `user` object, read back from the
database rather than from the token, so a role or access change takes effect
without re-issuing. `401` if the token is invalid, expired, or its account is
gone.

## `GET /auth/config`

No auth. Reports whether a secret is configured, the algorithm, the token
lifetime and the default app access — never the secret itself. Use it to check a
deploy is wired up before blaming the code.

---

## The token

HS256, signed with the shared secret. Claims:

```json
{ "sub": "<account id>", "email": "...", "role": "...",
  "org_id": "...", "app_access": ["glp1", "readmissions"],
  "exp": 1789880957 }
```

Valid for **12 hours**. There is no refresh flow, so that is also the session
length.

**For the tile screen:** read `app_access`. Show the GLP-1 tile if it contains
`glp1`, the Readmissions tile if it contains `readmissions`. New accounts get
both by default.

You can read the claims in the browser without the secret — the payload is
base64, not encrypted:

```js
const claims = JSON.parse(atob(token.split('.')[1]));
```

That is fine for deciding which tiles to draw. It proves nothing, because anyone
can edit a payload; every real decision is made by a backend checking the
signature.

## Handing the token to a product

Redirect with the token in the URL **fragment**, not the query string — a
fragment is never sent to the server, so it stays out of access logs, proxy logs
and `Referer` headers:

```
https://<readmissions-frontend>/#token=<jwt>
```

The receiving app reads it on load, stores it, and strips it from the address
bar.

---

## Notes

- **Signup is open.** Anyone who can reach the endpoint can create an account.
  That is the intended demo behaviour; it is not suitable for real patient data.
- **Passwords** are bcrypt, cost 12 — the same scheme as the accounts already in
  `shared_identity.users`, so existing accounts keep working.
- **The secret is symmetric.** Holding it means being able to mint tokens, not
  just verify them. It must never reach a browser bundle or a commit.

## Configuration (server side)

| Variable | Default | Purpose |
|---|---|---|
| `SHARED_SECRET_KEY` | — | signing secret; required |
| `SHARED_AUTH_TOKEN_TTL` | `43200` | token lifetime, seconds |
| `SHARED_AUTH_DEFAULT_APPS` | `glp1,readmissions` | `app_access` for new accounts |
| `SHARED_IDENTITY_DB` | `shared_identity` | database holding accounts |
