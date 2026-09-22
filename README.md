# Preventra — combined monorepo

Three products, one login:

| Folder | What it is | Stack |
|---|---|---|
| [`GLP1/`](GLP1/) | GLP-1 adherence, cost-effectiveness and payer-ROI analytics | FastAPI (`GLP1/Backend`) + React/Vite (`GLP1/Frontend`) |
| [`Readmissions/`](Readmissions/) | 30-day readmission risk scoring, weekly monitoring, clinician console — **and the shared auth service** | FastAPI (`Readmissions/api`) + React/Vite (`Readmissions/frontend`) |
| [`Portal/`](Portal/) | Single sign-in / sign-up page that hands a token to either app | Static `index.html`; a 40-line build step injects per-environment URLs |

---

## 1. How the pieces fit together

```
                         ┌─────────────────────────────┐
                         │   MongoDB (one cluster)     │
                         │  glp1_analytics             │
                         │  neuroshield                │
                         │  shared_identity  ← accounts│
                         └──────▲───────────────▲──────┘
                                │               │
                  ┌─────────────┴───┐     ┌─────┴──────────────────┐
                  │ GLP-1 API       │     │ Readmissions API       │
                  │ :8000           │     │ :8001                  │
                  │ /api/*          │     │ /api/*                 │
                  │ VERIFIES only   │     │ /auth/*  ← ISSUES JWT  │
                  └─────────▲───────┘     └────▲──────────▲────────┘
                            │                  │          │
             ┌──────────────┴───┐   ┌──────────┴──────┐   │ login/signup
             │ GLP-1 UI :5173   │   │ Readmit UI :5174│   │ (both UIs and
             └──────────▲───────┘   └────────▲────────┘   │  the portal)
                        │  #token=...        │ #token=... │
                        └──────────┬─────────┘            │
                                   │                      │
                            ┌──────┴──────────────────────┴─┐
                            │      Portal :5175             │
                            └───────────────────────────────┘
```

**One issuer, two verifiers.** [`Readmissions/api/auth.py`](Readmissions/api/auth.py) is the only
place a token is minted. It writes accounts to the `shared_identity.users` database and signs an
HS256 JWT. Both backends verify that token independently with the **same** `SHARED_SECRET_KEY` —
GLP-1 in [`GLP1/Backend/core/security.py`](GLP1/Backend/core/security.py). Neither backend calls the
other, so they stay separately deployable.

Claims (fixed contract between both products):

```json
{"sub": "<mongo _id>", "email": "...", "role": "...", "org_id": "...",
 "app_access": ["glp1", "readmissions"], "exp": 1700000000}
```

The Portal signs a user in, reads `app_access` out of the (unverified) payload to decide which tiles
to show, then redirects to the chosen app with `#token=<jwt>` on the URL fragment — a fragment is
never sent to a server, so the token stays out of access logs and `Referer` headers. Both frontends
pick it off the fragment on load and strip it from the address bar
([`Readmissions/frontend/src/api/auth.js`](Readmissions/frontend/src/api/auth.js),
[`GLP1/Frontend/src/context/AuthContext.jsx`](GLP1/Frontend/src/context/AuthContext.jsx)).

Each frontend also has its own sign-in screen, which posts straight to the same auth service —
`VITE_AUTH_URL`, not `VITE_API_URL`. The Portal is the front door, not the only door.

---

## 2. Prerequisites

- **Python 3.10+** (both services are built and deployed on 3.10)
- **Node 18+** (Node 22 works)
- **MongoDB** — an Atlas cluster, or local: `docker run -d -p 27017:27017 --name preventra-mongo mongo:7`
- Optional: a **Google Gemini API key** for the chatbot / narrative endpoints in both products

Three databases on one cluster: `glp1_analytics`, `neuroshield`, `shared_identity`. All are created
on first write — no manual setup.

---

## 3. Port map (local)

| Process | Port | Run from |
|---|---|---|
| GLP-1 API | `8000` | `GLP1/Backend` |
| Readmissions API + auth | `8001` | `Readmissions` |
| GLP-1 frontend | `5173` | `GLP1/Frontend` |
| Readmissions frontend | `5174` | `Readmissions/frontend` |
| Portal (static) | `5175` | `Portal` |

Both backends default to 8000, so **the port split is not optional** — pass `--port` explicitly.

---

## 4. One-time setup

### 4.1 Generate the shared secret

Generate it **once** and paste the identical value into both backend `.env` files. Two different
secrets means a token minted at login is rejected by the other product with a 401 that looks like a
frontend bug.

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4.2 Copy the four env templates

Every service ships a `.env.example` documenting exactly what it reads:

```bash
cp GLP1/Backend/.env.example        GLP1/Backend/.env
cp GLP1/Frontend/.env.example       GLP1/Frontend/.env
cp Readmissions/.env.example        Readmissions/.env
cp Readmissions/frontend/.env.example Readmissions/frontend/.env
```

Then fill in, at minimum:

| File | Must set |
|---|---|
| `GLP1/Backend/.env` | `MONGODB_URI`, `SHARED_SECRET_KEY` |
| `GLP1/Frontend/.env` | defaults are already correct for local |
| `Readmissions/.env` | `MONGO_URI`, `API_KEY`, `SHARED_SECRET_KEY` (same value) |
| `Readmissions/frontend/.env` | `VITE_API_KEY` (same value as `API_KEY`) |

Two things that catch people out:

- `CORS_ORIGINS` in the GLP-1 backend is parsed by pydantic-settings as a **JSON list** — keep the
  brackets and the double quotes. `ALLOWED_ORIGINS` in Readmissions is plain **comma-separated**.
- `VITE_*` values are read at **build** time. Changing one means restarting the dev server (or
  redeploying), not just reloading the page.

### 4.3 Portal config

The Portal reads its three URLs from `window.__PORTAL_CONFIG__`. Locally that comes from the
committed [`Portal/config.js`](Portal/config.js), which already points at the local stack — nothing
to change. Deployments do not use that file at all: `Portal/build.js` regenerates it from
environment variables at build time ([§8](#8-frontend-deployment--vercel)), so no deployed origin is
committed. For reference, the local file is:

```js
window.__PORTAL_CONFIG__ = {
  AUTH_BASE_URL: 'http://localhost:8001',
  APPS: [
    { key: 'glp1',         name: 'GLP-1 Analytics',  blurb: '…', url: 'http://localhost:5173', handoff: 'fragment' },
    { key: 'readmissions', name: 'Readmission Risk', blurb: '…', url: 'http://localhost:5174', handoff: 'fragment' },
  ],
};
```

`key` must match the string the auth service puts in `app_access`, or the tile never appears.
If `config.js` is missing, `index.html` falls back to built-in defaults and reports the tiles as
unconfigured rather than rendering a blank page.

### 4.4 Install dependencies

```bash
cd GLP1/Backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

```bash
cd Readmissions && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
npm --prefix GLP1/Frontend install && npm --prefix Readmissions/frontend install
```

For GLP-1, `requirements.txt` is the lean runtime set and `requirements-dev.txt` adds pandas,
lifelines and the notebook/test tooling — the seeder needs it, the API does not. Readmissions splits
the same way: `requirements-api.txt` is what the container installs, `requirements.txt` is the full
development environment the loader scripts need.

---

## 5. Seed the databases (one time, order matters)

Both apps read precomputed data out of MongoDB. An empty database renders empty dashboards, not
errors.

### 5.1 GLP-1 → `glp1_analytics`

The 15 CSVs plus `final_gb_model.pkl` and `shap_values_test.npy` are committed under
[`GLP1/Backend/data/`](GLP1/Backend/data/), so a fresh clone can seed immediately.

```bash
cd GLP1/Backend && .venv/bin/python -m scripts.migrate_csv_to_mongo
```

Expect 12 collections and ~7,566 patients, all ✅. The script drops and reinserts each collection,
so it is safe to re-run.

### 5.2 Readmissions → `neuroshield`

The model bundle and parquet inputs are committed under
`Readmissions/data/mimic/model/results/`. Run all four, in this order:

```bash
cd Readmissions
.venv/bin/python scripts/load_mimic_to_mongo.py --limit 4000
.venv/bin/python scripts/simulate_weekly_monitoring.py --weeks 4
.venv/bin/python scripts/backfill_group_membership.py
.venv/bin/python scripts/refresh_worklist_summary.py
```

Step 1 runs SHAP over the cohort and takes a few minutes; `--limit 2000` is quicker for a first run.
All of these honour `MONGO_DB`, so if you change the database name, change it before seeding.

### 5.3 `shared_identity`

Nothing to seed. The unique index on `users.email` is created at boot by the auth service; the first
account is created through the Portal or either sign-in screen.

---

## 6. Run it — five terminals

```bash
# 1 — GLP-1 API
cd GLP1/Backend && .venv/bin/uvicorn main:app --reload --port 8000
```

```bash
# 2 — Readmissions API + shared auth
cd Readmissions && .venv/bin/uvicorn api.main:app --reload --port 8001
```

```bash
# 3 — GLP-1 frontend
npm --prefix GLP1/Frontend run dev -- --port 5173
```

```bash
# 4 — Readmissions frontend
npm --prefix Readmissions/frontend run dev -- --port 5174
```

```bash
# 5 — Portal (any static server)
npx serve Portal -l 5175
```

`uvicorn main:app` for GLP-1 must run **from inside `GLP1/Backend/`** — its imports are `core.*` /
`routers.*`, relative to that directory. Readmissions is the opposite: run `api.main:app` from the
`Readmissions/` root.

### First run, end to end

1. Open **http://localhost:5175** (Portal).
2. Switch to **Sign up** — email, password (≥8 chars), role, organisation. That POSTs to
   `http://localhost:8001/auth/signup`, creates the account in `shared_identity.users` and returns a
   token immediately.
3. Two tiles appear (one per entry in `app_access`). Click one — you land in that app already signed
   in, with the token stripped from the URL.
4. Move between apps with the app switcher in each sidebar; the token travels on the fragment.

### Health checks

| Check | URL |
|---|---|
| GLP-1 API | http://localhost:8000/health |
| GLP-1 Swagger | http://localhost:8000/docs |
| Readmissions API | http://localhost:8001/healthz |
| Auth wiring (reports *whether* a secret is set, never the secret) | http://localhost:8001/auth/config |

`/auth/config` is the fastest way to diagnose a broken login: `secret_configured: false` means the
`.env` was not picked up.

---

## 7. First backend deployment — step by step

This is the walkthrough for getting **both FastAPI services onto Railway for the first time**, with
MongoDB Atlas behind them. Frontends come after ([§8](#8-frontend-deployment--vercel)); they cannot
be configured until these URLs exist.

Everything Railway needs is already committed:

| Service | Root directory | Config | Builder |
|---|---|---|---|
| Readmissions API + auth | `Readmissions` | [`railway.json`](Readmissions/railway.json) | [`Dockerfile`](Readmissions/Dockerfile) |
| GLP-1 API | `GLP1/Backend` | [`railway.json`](GLP1/Backend/railway.json) | [`Dockerfile`](GLP1/Backend/Dockerfile) |

### Step 0 — Rotate the secrets first

`Readmissions/.env` currently holds live values in the working tree. Before anything is deployed:
rotate the Mongo password, the Gemini key, the `API_KEY` and the `SHARED_SECRET_KEY`. Production
values should exist **only** in Railway and Vercel variables, never in a file in the repo.

### Step 1 — MongoDB Atlas

1. [cloud.mongodb.com](https://cloud.mongodb.com) → **Create Project** → **Build a Database** →
   free **M0** tier. One cluster is enough; the three databases separate the data.
2. **Database Access** → add a user with *Read and write to any database*. Note the password and
   **URL-encode it** if it contains `@ : / ? # [ ] %` — an unencoded password produces an
   authentication failure that reads like a wrong password.
3. **Network Access** → Railway does not publish fixed egress IPs on standard plans, so add
   `0.0.0.0/0` and rely on the credentials. (With a static-egress plan, allow that IP instead.)
4. Copy the SRV connection string:
   `mongodb+srv://<user>:<encoded-pw>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
5. Seed both databases from your workstation now, using that URI — see [§5](#5-seed-the-databases-one-time-order-matters).
   Deploying against an empty cluster gives you two services that boot cleanly and render nothing.

### Step 2 — Create the Railway project

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → pick this
   repository.
2. Railway creates one service. You will end up with **two services in this one project**, both
   pointed at the same repo, each with a different **Root Directory**. That setting is the whole
   trick to deploying a monorepo — without it, Railway builds from the repo root and finds nothing
   to run.

### Step 3 — Service 1: `readmissions-api` (deploy this one first)

It carries the auth service, so nothing else can be verified until it is up.

1. **Settings → Service Name**: `readmissions-api`.
2. **Settings → Source → Root Directory**: `Readmissions`.
3. Leave the builder alone. `railway.json` already selects the Dockerfile, sets the healthcheck to
   `/healthz` with a 120s timeout, and declares `watchPatterns` so a push that only touches
   notebooks does not trigger a rebuild.
4. **Variables** → add:

   | Variable | Value |
   |---|---|
   | `MONGO_URI` | the Atlas SRV string from step 1 |
   | `MONGO_DB` | `neuroshield` |
   | `API_KEY` | a fresh random string |
   | `SHARED_SECRET_KEY` | the signing secret (generate once — see [§4.1](#41-generate-the-shared-secret)) |
   | `SHARED_IDENTITY_DB` | `shared_identity` |
   | `SHARED_AUTH_DEFAULT_APPS` | `glp1,readmissions` |
   | `ALLOWED_ORIGINS` | `*` **for now** — you will pin it in step 6 |
   | `MANUAL_ENTRY_ENABLED` | `false` |
   | `GEMINI_API_KEY` | optional |

   Do **not** set `PORT`. Railway injects it, and the Dockerfile binds `${PORT}`.
5. **Settings → Networking → Generate Domain**. Note the URL.
6. Verify:

   ```bash
   curl https://<readmissions-api>.up.railway.app/healthz
   curl https://<readmissions-api>.up.railway.app/auth/config
   ```

   The first must return `{"status":"ok"}`; the second must report
   `"secret_configured": true`. If it reports `false`, `SHARED_SECRET_KEY` did not reach the
   container — re-check the variable name and redeploy.
7. Prove the database is reachable *and* that the issuer works, in one call:

   ```bash
   curl -X POST https://<readmissions-api>.up.railway.app/auth/signup \
     -H 'Content-Type: application/json' \
     -d '{"email":"you@example.com","password":"changeme123","role":"Doctor","org_name":"City Hospital"}'
   ```

   A token in the response means Atlas, the secret and the identity database are all wired
   correctly. A **503** with "check that this machine's IP address is on the MongoDB Atlas access
   list" means step 1.3 is wrong — that is network configuration, not code.

### Step 4 — Service 2: `glp1-api`

1. In the same project: **New** → **GitHub Repo** → the same repository.
2. **Settings → Service Name**: `glp1-api`.
3. **Settings → Source → Root Directory**: `GLP1/Backend`.
4. `railway.json` there selects the Dockerfile and sets the healthcheck to `/health` — note the
   singular, unlike Readmissions' `/healthz`.
5. **Variables** → add:

   | Variable | Value |
   |---|---|
   | `MONGODB_URI` | the same Atlas SRV string (note: `MONGODB_`, not `MONGO_`) |
   | `MONGODB_DB_NAME` | `glp1_analytics` |
   | `SHARED_SECRET_KEY` | **byte-identical** to the value on `readmissions-api` |
   | `SHARED_IDENTITY_DB_NAME` | `shared_identity` |
   | `CORS_ORIGINS` | `["*"]` **for now** — pinned in step 6. JSON list, brackets required. |
   | `GOOGLE_API_KEY`, `GEMINI_MODEL`, `CHATBOT_ENABLED` | optional |

   The two services deliberately use different variable *names* for the same things — they were
   built separately. Copy carefully; a `MONGO_URI` set on the GLP-1 service is simply ignored and
   the container fails to boot with `mongodb_uri field required`.
6. **Generate Domain**, then verify:

   ```bash
   curl https://<glp1-api>.up.railway.app/health
   ```

### Step 5 — Prove the two services share one identity

Take the token from step 3.7 and call a protected GLP-1 route with it:

```bash
TOKEN=<paste the token>
curl -H "Authorization: Bearer $TOKEN" "https://<glp1-api>.up.railway.app/api/patients?limit=1"
```

- **200** — the two services agree on the secret. The shared login works.
- **401 "Invalid or expired token"** — the secrets differ. Re-paste `SHARED_SECRET_KEY` on both
  services; a trailing newline or a stray space is enough to break it.
- **403 "This account doesn't have access to GLP-1"** — the account's `app_access` is missing
  `glp1`; check `SHARED_AUTH_DEFAULT_APPS` on the auth service.

That 200 is the real milestone. Everything after it is configuration.

### Step 6 — Pin the origins (do not skip)

Once the Vercel frontends exist ([§8](#8-frontend-deployment--vercel)), come back and replace the
wildcards:

- `readmissions-api` → `ALLOWED_ORIGINS` = `https://<glp1>.vercel.app,https://<readmissions>.vercel.app,https://<portal>.vercel.app`
  (all three — the portal calls `/auth/*` from its own origin, and so does each frontend's login screen)
- `glp1-api` → `CORS_ORIGINS` = `["https://<glp1>.vercel.app","https://<portal>.vercel.app"]`

This is not cosmetic. The Readmissions `API_KEY` ships inside the public frontend bundle, so while
CORS is `*` any page on the internet can read patient data through a visitor's browser. The API key
is only a meaningful gate in combination with a pinned origin list.

### Step 7 — Optional: the separate auth service from the architecture diagram

The diagram shows auth as its own Railway box. In the code it is a module inside the Readmissions
API, and you do **not** need to split it to ship. If you want that topology anyway, the cheap way is
to add a **third service from the same repo with the same root directory and the same variables**,
name it `auth`, and point the Portal's `AUTH_BASE_URL` at it. Zero code change, and login traffic
stops competing with dashboard traffic. Extracting `api/auth.py` into its own FastAPI app is a later
refactor, not a prerequisite.

### Operational notes

- Railway sleeps free-tier services. The first request after a sleep pays GLP-1's startup cost — it
  unpickles the model and warms caches in its lifespan handler. Keep both on a paid plan for a demo.
- Both services are stateless except `Readmissions`' `/api/pipeline/upload`, which writes to the
  container filesystem. That is ephemeral and lost on redeploy; attach a volume if uploads must
  survive.
- Deploy logs are the first place to look. A missing required setting fails loudly at boot
  (`mongodb_uri field required`), which is a much better failure than a service that starts and
  returns 500s.

---

## 8. Frontend deployment — Vercel

Deploy order: Railway backends (you need their URLs) → the two frontends → the Portal last (it needs
the frontend URLs) → then [§7 step 6](#step-6--pin-the-origins-do-not-skip).

Vercel projects are per-root-directory, so this is three separate projects against the same repo.
Set **Root Directory** in project settings; do not use a build command that `cd`s.

| Project | Root Directory | Framework | Output |
|---|---|---|---|
| `preventra-glp1` | `GLP1/Frontend` | Vite | `dist` |
| `preventra-readmissions` | `Readmissions/frontend` | Vite | `dist` |
| `preventra-portal` | `Portal` | Other | `dist` |

Both React apps use `BrowserRouter`, so a deep link like `/patients/123` is a request for a file that
does not exist. The SPA fallback is already committed as `vercel.json` in each frontend folder —
without it every route except `/` 404s after a refresh, and the `#token=` handoff looks like it
"loses" the login.

Environment variables (Production scope; `VITE_*` is read at **build** time, so changing one
requires a redeploy):

*`preventra-glp1`*
```
VITE_API_URL=https://<glp1-api>.up.railway.app
VITE_AUTH_URL=https://<readmissions-api>.up.railway.app
VITE_READMISSIONS_URL=https://<readmissions-frontend>.vercel.app
```

*`preventra-readmissions`*
```
VITE_USE_MOCK=false
VITE_API_BASE_URL=https://<readmissions-api>.up.railway.app
VITE_API_KEY=<same as Railway API_KEY>
VITE_MANUAL_ENTRY_ENABLED=false
VITE_GLP1_URL=https://<glp1-frontend>.vercel.app
VITE_PORTAL_URL=https://<portal>.vercel.app
```

*`preventra-portal`* — Build Command `npm run build`, Output Directory `dist`, and three env vars:
```
PORTAL_AUTH_BASE_URL=https://<readmissions-api>.up.railway.app
PORTAL_GLP1_URL=https://<glp1-frontend>.vercel.app
PORTAL_READMISSIONS_URL=https://<readmissions-frontend>.vercel.app
```

The portal is a static page with no framework, so it cannot read environment variables at runtime —
by the time the browser has the page, the build environment is gone.
[`Portal/build.js`](Portal/build.js) bridges that: it copies the static files into `dist/` and writes
`config.js` from the environment, which puts the portal's URLs in the same place as every other
service's instead of in a committed file. An unset variable warns in the build log and leaves that
tile marked unconfigured rather than pointing it somewhere wrong.

### Post-deploy smoke test

Portal → sign up → land in GLP-1 → app switcher → Readmissions. If the switch lands you back on a
login screen, the two services do not share the same `SHARED_SECRET_KEY`.

---

## 9. Defects fixed in this pass

Each of these was a real fault found while documenting the merge, and each is now fixed in the code.

1. **GLP-1's "Create account" was broken.** The frontend posted to `/api/auth/register`, an endpoint
   that did not exist. It now posts to the shared auth service's `/auth/signup`, and the form
   collects the `role` and `org_name` that endpoint requires.
   — [`api.js`](GLP1/Frontend/src/data/api.js), [`Login.jsx`](GLP1/Frontend/src/pages/Login.jsx),
   [`AuthContext.jsx`](GLP1/Frontend/src/context/AuthContext.jsx)

2. **There were two token issuers.** GLP-1 minted its own tokens against the same
   `shared_identity.users` collection, deriving `app_access` from `ROLE_APP_ACCESS[role]` while
   Readmissions used `SHARED_AUTH_DEFAULT_APPS` — so the same person could see different tiles
   depending on where they signed up. GLP-1's issuer is removed (`routers/auth.py`,
   `schemas/user.py`, and the stale `tests/test_auth.py` that imported a class that no longer
   existed). GLP-1 now only verifies, in `core/security.py`. `bcrypt` and `email-validator` are gone
   from its runtime requirements as a result.

3. **The GLP-1 frontend never sent its bearer token.** `/api/patients*` verifies a token, but the
   API client attached no `Authorization` header — so the patient panel silently fell back to mock
   data. It now sends the token on every call.

4. **`MONGO_DB` was documented but ignored.** `api/main.py` hardcoded `neuroshield`, as did seven
   loader scripts, so setting the variable moved nothing. All of them now go through
   `get_db_name()` in [`api/db_utils.py`](Readmissions/api/db_utils.py) — one place, and the API and
   the seeders cannot drift apart.

5. **`GLP1/README.md` documented the wrong secret.** It said `SECRET_KEY`; the settings field is
   `shared_secret_key`, so following it verbatim produced `shared_secret_key field required` at
   boot. Both GLP-1 READMEs now name `SHARED_SECRET_KEY` and explain why it must match the other
   service.

6. **The Portal's config was hardcoded in the markup.** It now comes from
   `window.__PORTAL_CONFIG__`, with the built-in defaults in `index.html` as a fallback. Deployed
   values are injected at build time by [`Portal/build.js`](Portal/build.js) from
   `PORTAL_AUTH_BASE_URL` / `PORTAL_GLP1_URL` / `PORTAL_READMISSIONS_URL`, matching how the two Vite
   apps take their `VITE_*` variables — so no environment's URLs are committed. The checked-in
   [`Portal/config.js`](Portal/config.js) is the local-development copy and points at localhost.

7. **No env templates existed.** All five services now ship a commented `.env.example`
   ([GLP-1 API](GLP1/Backend/.env.example), [GLP-1 UI](GLP1/Frontend/.env.example),
   [Readmissions API](Readmissions/.env.example), [Readmissions UI](Readmissions/frontend/.env.example),
   [Portal](Portal/.env.example)).

8. **No deployment config for the GLP-1 backend.** Added
   [`Dockerfile`](GLP1/Backend/Dockerfile), [`.dockerignore`](GLP1/Backend/.dockerignore) and
   [`railway.json`](GLP1/Backend/railway.json), matching how Readmissions is already set up. The
   image installs `requirements.txt` only and copies the two binary artifacts `core/loader.py` reads
   at startup, not the seeder CSVs. SPA rewrites added for both Vercel frontends.

### Still outstanding — needs a human

**Rotate the credentials in `Readmissions/.env`.** The file is correctly gitignored and was never
committed, but a live Mongo URI, a Gemini key, the API key and the shared signing secret are sitting
in the working tree. Rotate all four before this repo is shared, and keep production values in
Railway and Vercel variables only.

---

## 10. Per-project documentation

- [`GLP1/README.md`](GLP1/README.md) — pipeline, model, endpoint reference, rebuild instructions
- [`GLP1/Backend/README.md`](GLP1/Backend/README.md) — data artifacts and endpoint table
- [`Readmissions/README.md`](Readmissions/README.md) — data lineage (UCI → CMS → MIMIC-IV), the
  94-feature model, monitoring rules, risk bands, cost model, full runbook
