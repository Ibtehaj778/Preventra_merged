# Early Warning and the Clinician Loop

How the dashboard spots a patient deteriorating *before* their score crosses a
band, who it tells, and what comes back.

**Files**

| File | Role |
|---|---|
| `models/early_warning.py` | The forecast. Pure functions, no database |
| `api/doctor_service.py` | Registry, routing, alert lifecycle |
| `api/main.py` | HTTP surface and the bulk-loading `ForecastContext` |
| `frontend/src/pages/DoctorConsole.jsx` | The clinician's inbox |
| `frontend/src/components/dashboard/ForecastPanel.jsx` | The forecast on a patient's page |
| `tests/units/test_early_warning.py` | 47 tests |
| `tests/units/test_doctor_service.py` | 42 tests |

---

## 1. The loop

```
weekly monitoring
      │
      ├─ forecast()          project the trend, check condition-specific red flags
      │
      ├─ severity high or critical?
      │        │
      │        └─ create_alert()   one per patient per monitoring week
      │                 │
      │                 ├─ route()         by condition → specialty → a named doctor
      │                 └─ notification    in-app, unread count on the console
      │
      └─ doctor acknowledges, then replies
               │
               ├─ recommendation + structured actions + urgency  → the alert
               └─ the same reply as a note                       → care_actions
```

That last fork matters. The coordinator who actually telephones the patient does
not work out of the consultant's inbox, so the reply is written to the patient's
care record as well as to the alert.

---

## 2. What the forecast is

> Linear projection of the patient's own weekly scores, plus condition-specific
> clinical thresholds. **Not a trained predictor.**

That wording is on the panel, in the API response (`basis`), and in the module
docstring, because it is the claim that has to survive review. No public dataset
carries weekly post-discharge observations against readmission outcomes at this
cadence — `scripts/mimic_feasibility.py` measures exactly that against MIMIC's
`omr` table and prints the verdict. Fitting a model to simulated weeks would
learn the simulator and nothing else.

What it does instead, in three independent streams:

**Trajectory.** A least-squares slope over the last 3 weeks, projected 2 weeks
forward. Weeks are the x-axis, not the row index, so a patient who skipped two
weeks gets a flatter slope rather than a fabricated one.

**Condition-specific red flags.** The week's observations against published
thresholds for *that patient's discharge diagnosis*. This is the part that makes
the forecast diagnosis-aware rather than generic.

**Engagement.** Adherence, refills, follow-up attendance. Individually
administrative; together they describe a patient who has come off the plan.

### Why the flags are keyed by condition

The direction of a signal is not universal. A 2 kg weekly weight **gain** is the
classic heart-failure decompensation signal. The same 2 kg as a **loss** is what
you chase in an oncology patient, and it means very little after surgery.

```
weight_change_kg = -2.5
  oncology       → "Weight loss over 2 kg in one week"    (high)
  heart_failure  → no flag
```

Each group carries its own table — fluid balance for heart failure, saturation
and reliever use for respiratory, temperature and confusion after sepsis, blood
pressure after stroke, wound state after surgery, contact for mental health.

Every flag carries a `rationale` explaining why it fired, so a clinician can
disagree with one rule without discarding the system.

### The lead time is the product

The existing `alerts` collection is reactive: it fires once a score has already
crossed a band. This fires while the patient is still Medium and heading for
High:

```
Week 1  24.0  Medium
Week 2  29.0  Medium
Week 3  34.0  Medium   → "On track to reach High risk in about 8 days"
```

Because of that, **a projection is never `critical` on its own**, however steep.
Critical means *review today*, and a forecast carrying a week of lead time is by
definition not that. Only an observed red flag — saturation at 88%, systolic
under 90, new confusion after sepsis — is critical by itself.

---

## 3. Severity, and how it was tuned

| Severity | Meaning | Reaches an inbox |
|---|---|---|
| `critical` | Review same day | yes |
| `high` | Review within 48 hours | yes |
| `moderate` | Mention at next scheduled contact | no — patient page only |
| `none` | Nothing found | no |

`moderate` deliberately does not page anyone. Alerting a consultant about every
patient drifting a few points a week is how an alerting system gets switched off
within a fortnight.

### Corroboration

Two independent streams agreeing is itself evidence, so severity escalates one
step when it happens — but **both streams must carry a trigger of at least
`high`**. Counting a mild finding as corroboration turned any small trend plus
any borderline vital into a critical alert.

### What the first sweep taught us

The first full run over 4,000 monitored patients raised **1,546 alerts (39%)**
against a cohort where 21% are actually flagged deteriorating. Three causes,
found by counting which rules fired:

| Problem | Fix |
|---|---|
| `accelerating` fired 928 times, including on patients who were *improving, more slowly* — a positive second derivative with a negative slope | Require the trend to be rising before acceleration can fire, and raise the threshold to 5.0. It is the difference of two slopes, so it carries the noise of both |
| Borderline hypoxia (SpO2 ≤ 92) fired `high` 551 times, though 92% is often that patient's baseline and no baseline is recorded | Demoted to `moderate`. The respiratory profile still escalates its own ≤ 90 threshold to critical, where the diagnosis makes it meaningful |
| Any moderate finding corroborated any moderate trend into `critical` | Corroboration now requires two `high`+ streams |

The middle one was a tuning call. The first was a **bug**: "deterioration is
accelerating" was factually wrong about a recovering patient.

After the fix: **817 alerts (20%)**, which tracks the cohort's actual
deterioration rate, and every `critical` now traces to a named clinical red flag
rather than to an escalation chain:

```
severe_hypoxia               186
hf_fluid_overload            113
sepsis_confusion             112
resp_desaturation             38
sepsis_fever_return           22
renal_overload_hypertensive   18
```

Note that this rate is a property of the **simulated** monitoring data, which
deteriorates more often than a real programme would. The thresholds are the
tuning surface when real data arrives.

---

## 4. Routing

Most specific wins:

1. A doctor named on the patient (`care_actions.assigned_doctor_id`)
2. A doctor who has claimed that condition (`clinical_groups`)
3. The specialty the condition maps to — heart failure → Cardiology, renal →
   Nephrology, and so on
4. Internal Medicine
5. **Nobody** — and that is a real outcome, not a failure

An alert with no doctor gets `status: "unrouted"` and appears in its own queue on
the console. Silently dropping it would be the worst thing this code could do. A
stale assignment — a doctor who has left — falls through to the condition rather
than black-holing that patient's alerts.

---

## 5. Deduplication

**One alert per patient per monitoring week.** A nightly sweep must not produce
seven copies of the same warning by Sunday.

- Same week, same severity → the forecast is refreshed in place
- Same week, **worse** severity → reopened, and the doctor is notified again
- Same week, but already answered → left alone; a reply is not undone by a sweep
- A new monitoring week → a genuinely new alert

`create_alert` returns `(alert, created)` so the sweep can report the difference
without a second query.

---

## 6. Performance

The first implementation read three collections per patient. Over 4,000 patients
that is 12,000 round trips, and against this Atlas tier — measured at roughly 290
documents per second — it did not finish.

| Change | Effect |
|---|---|
| `ForecastContext` bulk-loads the three collections once | 12,000 round trips → 3 |
| Project only the 4 fields a forecast reads | The stored week also holds three driver sentences; pulling all 20,000 in full timed the cursor out |
| Drop the server-side sort | `week_number` has no index, so sorting the whole collection is a blocking in-memory sort — and `forecast()` re-establishes the order per patient anyway |
| `bulk_write` the alerts, `insert_many` the notifications | The write phase went from minutes to **11 s** |

Loading still takes ~75 s, which is past the point where an HTTP client gives up,
so the sweep runs on a thread and the caller polls:

```bash
curl -s -X POST localhost:8000/api/forecast/scan -H 'Content-Type: application/json' -d '{}'
```

```bash
curl -s localhost:8000/api/forecast/scan/SCAN-XXXXXXXX
```

A sweep that dies is marked `Failed` with the error. Left as `Running` it would
look merely slow, and nobody would go looking for the alerts that were never
raised.

---

## 7. API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/doctors` | Register (email is the key — re-registering updates) |
| `GET` | `/api/doctors` | Directory, specialties, condition→specialty map |
| `DELETE` | `/api/doctors/{id}` | Deactivate, keeping their answered alerts intact |
| `GET` | `/api/patients/{id}/forecast` | Forecast for one patient |
| `POST` | `/api/forecast/scan` | Start a sweep, returns `scan_id` |
| `GET` | `/api/forecast/scan/{scan_id}` | Progress |
| `GET` | `/api/doctors/{id}/alerts` | Inbox (`?status=open`) |
| `GET` | `/api/doctors/{id}/notifications` | Unread counts for the badge |
| `GET` | `/api/clinical-alerts/unrouted` | Alerts nobody owns |
| `GET` | `/api/patients/{id}/clinical-alerts` | History, including replies |
| `POST` | `/api/clinical-alerts/{id}/acknowledge` | Seen |
| `POST` | `/api/clinical-alerts/{id}/respond` | Recommendation + actions + urgency |
| `POST` | `/api/clinical-alerts/{id}/dismiss` | Close with a reason, no advice |
| `GET` | `/api/clinical-alerts/actions` | The structured action vocabulary |

### Dismissal is not a recommendation

A forecast can be right about the numbers and wrong about the patient — the
weight gain was a new steroid, the low saturation was a faulty meter. Dismissing
records the reason on the alert and deliberately writes **nothing** to the
patient's care record, because a dismissal is not clinical advice and must not
read like it. A pile of dismissals sharing a cause is also how a wrong threshold
gets found.

---

## 8. Known limitations

**Identity is a directory, not authentication.** Sign-in was removed from this
build, so the console picks a clinician and nothing verifies that the person
clicking is who they selected. The console says so on screen. Every action is
already recorded against `doctor_id`, so adding real auth means checking the
caller at the endpoint — the data model does not need to change.

**Notifications are in-app only.** There is no mail or SMS transport. Writing one
that silently no-ops would be worse than not having it: a clinician would believe
they had been paged. The notification document carries `channel` and `delivered`
so a real transport has a place to report success or failure.

**The monitoring data underneath is simulated.** The discharge score and its
drivers are real model output; the weekly observations are not. See
`docs/chatbot_implementation.md` and the feasibility probe for the full position.
This feature does not change that, and does not claim to.

**No baseline vitals.** SpO2 of 92% is scored the same for a marathon runner and
someone with long-standing lung disease, because no pre-discharge saturation is
recorded to compare against. Capturing a baseline at discharge is the single
highest-value improvement to the red-flag rules.

---

## 9. Testing

```bash
.venv/bin/python -m pytest tests/units/test_early_warning.py tests/units/test_doctor_service.py -v
```

**89 tests, no network.** The forecast tests are pure — a list of weeks in, a
verdict out — and cover the projection arithmetic, every condition-specific rule,
the direction inversion between oncology and heart failure, and the honesty
cases: no data, one week, and a red flag firing with no trend behind it.

The service tests use `mongomock` and pin the things that would stay invisible
until they hurt: an alert duplicated on every sweep, an alert routed to nobody,
a reply that never reaches the coordinator, and a sweep that stops because one
patient's document was malformed.
