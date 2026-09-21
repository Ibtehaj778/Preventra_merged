# NeuroShield ("Preventra") — New-Hire Feature Roadmap

This is a catalog of concrete features and improvements for a new hire to work on. **Items are
not ordered, sequenced, or prioritized** — pick up whichever one makes sense to start with. Each
item is scoped from the current, real state of the codebase (see [docs/HANDOVER.md](HANDOVER.md)
for full architecture context), not generic advice — every "why this matters" is grounded in an
actual gap or file in this repo, and sub-tasks reference the real modules you'll touch.

This document covers new features only. It does not include cleanup/tech-debt items (those are
tracked separately in `docs/HANDOVER.md` §8 if you want them, but they're out of scope here).

---

## 1. Authentication, signup, and role-based access control

**Why this matters:** there is currently **no authentication system at all**. The entire API is
gated by one optional, shared secret — `require_api_key` in `api/main.py` checks a static
`X-API-Key` header against a single value in `.env`, with no notion of identity or role. There is
no user store. Every route in `frontend/src/App.jsx` is public, and `Sidebar.jsx` renders every
nav item — including "Manual Entry" and the clinical worklist — to anyone who loads the app.

A username/password implementation with `hospital` and `patient` roles was built and then removed
before deployment, along with the patient portal it served. It is recoverable from git history if
any of it is worth reusing, but nothing below assumes it.

An investor role has real precedent already: the
existing `docs/deliverables/` files (`preventra_progress_update.pptx`, `presentation_script.docx`)
show an established manual investor-reporting workflow this role would eventually plug into.

Three roles are needed: **patient** (their own health summary only), **investor** (read-only
aggregate/analytics access), and **care provider** (today's full-access clinical user — worklist,
patient detail, manual entry, patient update, care coordination).

### Needed regardless of which path you choose
- Design a `users` collection: `role` (`patient` | `investor` | `care_provider`), and for
  `patient` role, a link to their `patient_id` in `patient_worklist`.
- Replace/extend `require_api_key` in `api/main.py` with an identity-resolving dependency
  (`Depends(get_current_user)`) that yields the caller's role (and linked `patient_id` if a
  patient).
- Add per-route authorization: worklist/patient-detail/manual-entry/update endpoints restricted
  to `care_provider`; `GET /api/patients/{id}` restricted for `patient` role to their own linked
  id; `investor` limited to read-only aggregate endpoints (`/api/summary`, `/api/summary/history`,
  `/api/analytics/top-drivers`, `/api/model/metrics`).
- Add route guards in `frontend/src/App.jsx` (redirect unauthenticated users to `/login`;
  redirect unauthorized roles to a forbidden page).
- Make `Sidebar.jsx` role-aware — hide "Manual Entry"/clinical worklist links from
  `patient`/`investor` roles; show only "My Health Summary" to a `patient`.
- Rebuild a patient-facing view, and resolve the patient from the session rather than from a URL
  parameter — a patient must only ever load their own linked record.
- Logout, session-expiry handling, and a forbidden/role-mismatch UI state.

### Path A — Custom-built
- `users` collection with hashed passwords (bcrypt/argon2, e.g. via `passlib` — not currently in
  `requirements.txt`).
- `POST /api/auth/register`, `/login`, `/refresh`, `/logout` endpoints + Pydantic request models.
- JWT access/refresh token issuance (`python-jose` or `pyjwt` — neither is in `requirements.txt`
  today).
- Email verification and password-reset flows (needs an email-sending dependency — none exists in
  the repo currently).
- Login-endpoint rate limiting (no brute-force protection exists anywhere in the API today).
- Frontend: login/signup pages, token storage strategy (httpOnly cookie vs. localStorage), and a
  fetch interceptor for attaching/refreshing tokens.

### Path B — Managed provider (e.g. Auth0, Clerk, Firebase Auth)
- Evaluate providers, weighing cost/self-host tradeoffs against a clinical-data-appropriate
  compliance posture (e.g. HIPAA-eligible plans).
- Backend: verify provider-issued JWTs via JWKS in a dependency that replaces `require_api_key`.
- Map provider roles/custom claims to the 3 app roles — decide whether role lives in provider
  user metadata or in a local `users` collection keyed by the provider's user id.
- Frontend: install the provider's React SDK; replace bespoke login/signup UI with provider
  components.
- Configure a post-signup webhook to create the corresponding `users` record. For the `patient`
  role specifically, this needs a linking step — patients don't self-register with a known
  `patient_id`, so an invite/registration-code flow is required.
- Secrets/env management for provider API keys.

### Real tradeoffs to decide
- Custom build (full control, but you own more security surface for PHI-adjacent data) vs.
  managed provider (faster, likely a better compliance story, but vendor lock-in/cost).
- How a `patient` login gets tied to a `patient_id` — there's no self-registration flow today, so
  this needs an explicit invite/linking mechanism.
- The exact investor read-only boundary — aggregate endpoints only, or something that also
  surfaces `docs/deliverables/`-style reporting through the app (see item 8 below).
- Whether the existing shared `X-API-Key` mechanism should stay for machine-to-machine writes
  (e.g. pipeline ingestion) even after user auth ships, or whether everything moves to user
  tokens.
- Where role lives: JWT claims (stateless, but a role change requires reissuing the token) vs. a
  DB lookup per request (always fresh, extra round trip).

---

## 2. Dataset acquisition & multi-disease generalization

**Why this matters:** the model currently only works for diabetic patients, and the pipeline is
built tightly around one specific dataset's schema. `ingestion/` is empty (just `.gitkeep`) — no
data-fetching code exists anywhere. Notably, `data/reference/heart_failure_clinical_records_dataset.csv` and
`data/reference/hospital_readmissions_30k.csv` are **already sitting in the repo, unused, with no documented
provenance** — an earlier, abandoned attempt at exactly this goal.

Generalization assessment (already done, so you don't have to re-derive it): `features/cci.py`
(Charlson Comorbidity Index) is disease-agnostic and reusable as-is. `features/label.py`'s
mechanism is reusable, but hardcodes the UCI diabetic dataset's exact `readmitted` values
(`'<30'`, `'>30'`, `'NO'`). `features/clean.py` is mostly generic but hardcodes its drop-column
list and CSV path. The real effort is `features/engineer.py` (466 lines) — it hardcodes UCI-schema
column names throughout (`number_inpatient`, `num_medications`, `insulin`,
`admission_type_id`...), a 23-item hardcoded medication list, age-bracket strings like
`"[70-80)"`, and `add_probabilistic_no_show` hardcodes ICD-9 `"250"` as the diabetes marker.
`features/build_features.py`'s validation gate also hardcodes `EXPECTED_ROWS=101766` and a 9-14%
positive-rate assertion, both specific to the UCI dataset.

### Sub-tasks
- Build real `ingestion/` scripts to fetch/refresh datasets programmatically (e.g. `kagglehub`,
  or documented direct-download scripts for UCI/CMS/Synthea-style sources) instead of ad-hoc CSV
  drops with no provenance.
- Add the needed dataset-API SDKs to `requirements.txt` (none exist today).
- Design a per-dataset schema-adapter config — a `DatasetConfig`/column-mapping object capturing:
  raw CSV path, column-name → canonical-feature mapping, label column + positive-value set
  (generalizing `features/label.py`), disease-marker ICD prefix (generalizing
  `add_probabilistic_no_show`'s hardcoded `"250"`), and expected-row-count/positive-rate
  validation bounds (generalizing `build_features.py`'s gate).
- Refactor `features/engineer.py` to read column names, the medication list, and age-bracket
  parsing from the adapter rather than inline constants — this is introducing the abstraction
  layer, not rewriting every feature function from scratch.
- Prove the adapter works end-to-end against one of the two datasets already sitting unused in
  `data/`, rather than only designing it on paper.
- Research and identify a genuine **post-discharge/follow-up-outcome** dataset (not just
  index-admission features) — the current engagement signal
  (`features/engineer.py::add_probabilistic_no_show`) is a fully synthetic single-feature proxy,
  not real post-discharge data.
- Decide and document how the model-registry naming convention
  (`readmission-dt-balanced-importance`, etc.) and `docs/band_thresholds_*.json` extend to a
  second disease — new registered model names, new threshold files, and whether
  `pipeline/batch_flow.py` becomes parameterized or a second disease gets its own flow (mirroring
  the existing 4-parallel-training-track pattern already in `models/`).
- Add a lightweight provenance/licensing checklist for any dataset landing in `data/` — the two
  already-present unused CSVs have none today.

### Real tradeoffs to decide
- A column-mapping adapter layer (more reusable, more upfront design) vs. a fully parallel
  pipeline per disease (faster to ship one new disease, but repeats the "which track is actually
  production" documentation gap already called out in `docs/HANDOVER.md` §5).
- How much of `engineer.py`'s logic is genuinely diabetes-specific clinical signal
  (insulin/A1C/glucose flags) vs. generic hospital-utilization signal (admission counts, length
  of stay, CCI) that belongs in a disease-agnostic core — a modeling judgment call, not just a
  refactor.
- Whether "multi-disease" means one model + registry + worklist per disease (fits the current
  architecture cleanly) vs. one shared model with a disease dimension (more novel, more invasive).

---

## 3. A more capable AI chatbot

**Why this matters:** the current chatbot (`api/chatbot_gemini.py`, `api/chatbot_queries.py`,
`api/chatbot_service.py`) is intentionally narrow for safety — Gemini either selects exactly one
of 6 predefined MongoDB query functions or phrases a natural-language answer from an
already-computed result; it never writes raw query syntax. That safety property is worth keeping
as you expand scope. Confirmed hard limits in the current design: it's fully stateless (no
conversation history, by design per the code's own docstring), exactly one function call per
question (no chaining/multi-step reasoning), and it can only see `patient_worklist` — it has no
access to `alerts`, `care_actions`, `executive_summary`, or `risk_registry`, so questions like
"which high-risk patients have unacknowledged alerts" are impossible today. It also only supports
population-level trend data (`get_risk_trend_over_time`), not per-patient score history — even
though `risk_registry` already backs exactly that data for the REST API (`GET /api/patients/{id}`)
without the chatbot being able to use it.

### Sub-tasks
- Add conversation state: extend `POST /api/chatbot/query` to accept/return history (decide
  storage — in-memory per session, similar to the existing `_pipeline_runs` pattern in
  `api/main.py`, vs. a new `chat_sessions` Mongo collection).
- Add multi-step/agentic function chaining: extend `chatbot_gemini.select_function_call` /
  `chatbot_service._dispatch` from "pick exactly one function" to a bounded loop (explicit
  max-step cap) that lets Gemini request a follow-up function call after seeing a result — while
  still never letting it emit raw query syntax.
- Add new predefined, validated functions in `api/chatbot_queries.py` for the other 4
  collections (e.g. `get_unacknowledged_alerts`, `get_care_actions_for_patient`,
  `get_executive_summary_trend`, `get_patients_without_care_coordinator`), each registered as a
  `FunctionDeclaration` in `chatbot_gemini.py` exactly like the existing 6.
- Decide and implement how cross-collection questions get answered — either a dedicated
  join-function, or via the multi-step chaining above composing two existing functions. Pick one
  approach explicitly rather than half-doing both.
- Add per-patient time-series queries (e.g. `get_patient_score_history(db, patient_id)`) using
  `risk_registry`, which already has this data but isn't exposed to the chatbot.
- Frontend: `Chatbot.jsx` currently sends one-shot questions with no history UI — add
  conversation display and pass prior turns to the backend.
- Document the safety-property decision explicitly: recommend keeping "LLM never writes raw
  queries" as the rule, by adding more named+validated functions rather than exposing a generic
  aggregation-builder function to the LLM.

### Real tradeoffs to decide
- Every new cross-collection join as its own named, validated Python function (more code per new
  question type, fully auditable) vs. a constrained query-builder DSL exposed to the LLM (less
  code to add per question, but a materially different, harder-to-audit safety posture).
- Conversation state as session-scoped/in-memory (simple, doesn't survive restarts or scale past
  one API process) vs. persisted per logged-in user in Mongo (durable, but requires the identity
  work from item 1 — these two roadmap items are coupled if conversations should persist per
  user).
- Multi-step chaining needs an explicit step/latency budget (each step is a Gemini round trip) —
  decide a concrete cap (e.g. 3 chained calls) up front.

---

## 4. Synthetic data generation (fallback for missing real data)

**Why this matters:** this is fully greenfield — there are no synthetic-data libraries in
`requirements.txt` (no SDV, CTGAN, Faker, ydata-synthetic) and no synthetic-data script anywhere
in the codebase. The only related precedent is
`features/engineer.py::add_probabilistic_no_show`, which trains a small `LogisticRegression` on
`data/reference/noshow.csv` as a narrow single-feature transfer-learning imputation trick — worth citing as
prior art/inspiration, but it's not true synthetic row generation and shouldn't be extended
directly. Because the source is real patient data, this has real correctness and privacy
implications, not just a modeling nicety.

### Sub-tasks
- Library selection spike: SDV (CTGAN/TVAE/GaussianCopula) vs. ydata-synthetic vs. a lighter
  approach (Faker is for demo-only data, a fundamentally different use case than
  distribution-preserving synthetic generation). Add the chosen library to `requirements.txt`.
- Build a generation script/module that trains a synthesizer on `data/diabetic/features.csv` (or the
  pre-feature-engineering cleaned CSV) and emits N synthetic rows in the same schema.
- Define the actual "fallback" trigger condition — e.g. training-time augmentation for the
  minority (readmitted) class, or a rule for when a dataset is "too small" (relevant given
  `data/reference/hospital_readmissions_30k.csv` is already much smaller than the 101,766-row UCI source).
  "Fallback" implies a decision rule, not just an on-demand generator.
- Build a fidelity/validation harness: per-feature distribution comparisons and
  correlation-matrix comparison (e.g. via SDV's own quality-report tooling), gated before any
  synthetic data is allowed into a training run.
- Build privacy/re-identification checks: nearest-neighbor distance-to-real-data checks, since a
  synthetic row that's too close to a real patient row is effectively a data leak.
- Decide the integration scope explicitly: training-only augmentation
  (`features/build_features.py` / `models/train_*.py`) vs. also seeding demo/dev/staging
  environments — these have very different rigor requirements.
- Tag synthetic rows at the source, mirroring the existing `"source": "manual"` field pattern
  already used in `patient_worklist` documents (`api/main.py:901`), so synthetic rows are never
  silently conflated with real patient data.
- Produce a per-run synthetic-data validation report, following the existing
  `docs/diabetic/model_validation_report*.md` convention, so provenance stays auditable.

### Real tradeoffs to decide
- Training-time augmentation (higher-stakes, needs the full fidelity+privacy gate) vs.
  demo/dev-only use (lower-risk, could ship first and defer the harder validation work).
- Even synthetic data can leak real patient information if the generator overfits/memorizes
  near-duplicate rows — this needs an explicit go/no-go gate, not just a visual "looks plausible"
  check.
- Choice of synthesizer trades fidelity against training cost (CTGAN is heavier/slower;
  GaussianCopula is lighter but less expressive) — decide based on the actual dataset size in
  play.

---

## Additional proposed features

These weren't requested but are natural extensions of systems that already exist in the repo.

### 5. Alert escalation & notification delivery
Today, alerts are created on a 15-point/band-jump score change
(`SCORE_JUMP_ALERT_THRESHOLD = 15.0`, `api/main.py:946`) and only surface passively via
`GET /api/alerts` + `AlertsBell.jsx` — visible only if someone happens to be looking at the
dashboard. Sub-tasks: add `notified_at`/`escalated_at` fields to the alert schema; dispatch a
notification (email/SMS) to the patient's assigned `care_actions.coordinator_name` when an alert
fires; add a scheduled job (Prefect, alongside `pipeline/batch_flow.py`) that escalates alerts
unacknowledged after a threshold; select and add an email/SMS provider (e.g. SendGrid/Twilio) to
`requirements.txt`.

### 6. Model monitoring & drift detection
There are 4 parallel training tracks (see `docs/HANDOVER.md` §5) but no ongoing production
monitoring of score or feature drift between batches. Sub-tasks: add a scheduled job that compares
each new batch's feature/risk-score distributions against the training-time baseline documented
in `docs/diabetic/model_validation_report_balanced_importance.md`; write drift reports to a new collection
or `docs/`; extend the existing `/api/model/metrics` endpoint (currently a static read of
`data/diabetic/model_card.json`) with a time series; reuse the `alerts` collection/pattern to flag drift
crossing a threshold.

### 7. Care-coordination workflow depth
`care_actions` today is just `{coordinator_name, notes[]}` (`assign_coordinator`/`add_care_note`
in `api/main.py`). Sub-tasks: add structured task/reminder tracking (e.g. "follow up by X date"
with completion state) instead of free-text notes only; add a "my assigned patients" worklist
view for care coordinators in the frontend (a natural pairing with the `care_provider` role from
item 1); track whether an intervention correlates with the patient's next `risk_registry` score
trending down, closing the loop between care coordination and the model's own predictions.

### 8. Automated investor/executive reporting
`docs/deliverables/` shows an existing manual investor-facing progress-deck workflow
(`preventra_progress_update.pptx`, `presentation_script.docx`). Sub-tasks: build a scheduled
job/endpoint that auto-generates a periodic executive summary export (PDF or slide-ready data)
from the `executive_summary` and `get_risk_trend_over_time` data already computed, reducing
manual deck-building; expose it as a self-serve "download latest report" behind the new
`investor` role from item 1.

### 9. Patient engagement feedback loop
There is no patient-facing view today (see item 1). Once one exists, it needs to be interactive
rather than a static action list per risk band.
Sub-tasks: let a patient acknowledge guidance / mark action items complete via a lightweight
engagement-tracking collection; feed that real engagement signal back into
`features/engineer.py`'s `no_show_proxy` in a future retrain — replacing the currently
fully-synthetic `add_probabilistic_no_show` proxy with real patient data over time. This directly
links the `patient` role from item 1 to the model's weakest existing feature.

### 10. Audit trail / activity log for clinical data changes
Every write path that mutates patient risk data — `predict-update`, `commit_patient_update`,
`assign_coordinator`, `add_care_note`, `acknowledge_alert` — is currently anonymous (no actor
recorded). Sub-tasks: add an `audit_log` collection recording who changed what, when, and the
before/after values; instrument each write endpoint in `api/main.py` to log to it. This becomes
straightforward and high-value once item 1 (auth/identity) exists — each write can then be
attributed to a real user instead of nothing.
