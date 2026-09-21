"""Hand-written prose for the MongoDB data dictionary.

Kept apart from scripts/build_mongo_dictionary.py so that the generator holds no numbers
and this file holds no measurements. Every figure in the output is computed at run time.
"""

COLLECTION_ORDER = [
    "patient_worklist", "risk_registry", "weekly_monitoring", "clinical_alerts",
    "notifications", "doctors", "care_actions", "executive_summary", "users",
]

NOTES = {
 "__preamble__": """
## How the collections relate

```
patient_worklist ──patient_id──┬── weekly_monitoring   (one document per patient per week)
   one row per patient,        ├── clinical_alerts     (forecast alerts raised at week 4)
   the dashboard worklist      └── care_actions        (coordinator notes)

risk_registry        scored discharges, one row per hospital stay — the history behind the worklist
clinical_alerts ──alert_id── notifications ──doctor_id── doctors
executive_summary    one row per batch, cohort-level counts
users                login accounts
```

`patient_id` is the join key almost everywhere, `hadm_id` appears nowhere in MongoDB — the
parquet tables hold that. `alert_id` joins alerts to notifications one-to-one.

## Before you query

Five things in here will produce wrong answers if you do not know about them.

### `patient_id` is not one type

**HIGH** — In `patient_worklist` and `risk_registry` the field is an `int` on some documents and
a `MIMIC-`-prefixed `str` on others, because two intakes wrote to the same collection. A query
for `{"patient_id": 85299696}` and one for `{"patient_id": "85299696"}` return different
documents, and `$lookup` between collections silently drops the mismatched side. Normalise to
string before joining.

### `patient_worklist` holds two cohorts with different schemas

**HIGH** — Filter on `batch_date` or `source`. The larger batch carries the current schema;
the smaller one is earlier manual-entry data and is the only place `raw_inputs.*` exists,
which is why those sub-fields read as present on about 1% of documents. Its `raw_inputs` keys
(`A1Cresult`, `admission_type_id`, `diabetesMed`, …) come from a different source dataset
entirely and do not correspond to any other field here. Its `discharge_date` is the batch date
rather than a real discharge date.

### `risk_registry` mixes two model versions

**MED** — Check `model_version` before comparing scores. The two versions were produced by
different models on different feature sets, so their `risk_score` values are not on a
comparable scale and pooling them will blur any distribution.

### Almost every alert is still unactioned

**MED** — `clinical_alerts.status` is `pending` on all but one document and
`notifications.read` is false on all but one, so any dashboard metric over these collections
is currently measuring an empty queue, not clinician behaviour. `response` and
`acknowledged_at` are null on everything except that single worked example.

### Scores are clipped at both ends

**LOW** — `current_score` bottoms out at exactly 1.0 for several hundred documents and
`clinical_alerts.forecast.projected_score` tops out at exactly 100.0 for a few dozen. Both are
the floor and ceiling of the scale, not measurements, so treat them as censored when fitting
anything to these columns.
""",

 "patient_worklist": {
  "one_line": "One document per patient — the dashboard worklist",
  "intro": ("The table the dashboard renders. One document per patient, carrying the discharge "
            "score, the latest weekly score, the trend between them, the monitoring group and the "
            "three ranked drivers. The `*_rank` fields exist purely so MongoDB can sort by band "
            "and status without a client-side pass, which is why this collection has far more "
            "indexes than any other."),
 },
 "risk_registry": {
  "one_line": "One document per scored discharge — the history",
  "intro": ("Every hospital stay that has been scored, which is why it is larger than the "
            "worklist: a patient with several admissions appears once per admission. This is the "
            "history the worklist summarises, and the only collection where `admit_date` and "
            "`discharge_date` carry real de-shifted MIMIC dates spanning 2009 onwards."),
 },
 "weekly_monitoring": {
  "one_line": "One document per patient per week — the post-discharge series",
  "intro": ("The post-discharge series behind the risk trend. **Week 0 is the discharge baseline** "
            "and carries a `discharge_baseline` sub-document instead of `monitoring`; weeks 1 to 4 "
            "carry `monitoring` and no baseline. That split is why both sub-documents read as "
            "present on a fixed fraction of rows rather than all of them.\n\n"
            "Within `monitoring`, seven signals are collected for everyone and the rest only for "
            "the clinical groups they are meaningful to. A low presence figure on those rows means "
            "*not applicable to this patient's group*, not missing data."),
 },
 "clinical_alerts": {
  "one_line": "One document per forecast alert raised for a doctor",
  "intro": ("An alert raised when the early-warning forecast crosses a severity threshold, with "
            "the whole forecast embedded so the alert is readable without re-running anything. "
            "Every alert in the collection was raised from the same forecast week, which is why "
            "`week_number` and `forecast.as_of_week` are single-valued.\n\n"
            "`forecast.triggers` is the list of individual rules that fired; `forecast.streams` "
            "names which of the three evidence streams (trajectory, condition-specific red flags, "
            "engagement) contributed. `forecast.corroborated` is true when two or more streams "
            "independently reached high severity."),
 },
 "notifications": {
  "one_line": "One document per alert, per recipient doctor",
  "intro": ("The doctor-facing delivery record for each alert, one-to-one with `clinical_alerts` "
            "on `alert_id`. Separate from the alert so that read state belongs to the recipient "
            "rather than to the clinical record."),
 },
 "doctors": {
  "one_line": "Registered clinicians and what they cover",
  "intro": ("The clinician roster. `email` is the natural key — re-registering an existing address "
            "updates the record rather than adding one. `clinical_groups` is what a doctor "
            "explicitly claims; routing also falls back to `specialty`, so a doctor with an empty "
            "`clinical_groups` still receives alerts for the conditions their specialty maps to."),
  "after": ("**One data-entry issue, left as it is because it is a record about a person:** a name "
            "is spelt `Dr. Partrick Jane`, with an extra `r`. Visible in the values above."),
 },
 "care_actions": {
  "one_line": "Coordinator notes against a patient",
  "intro": ("Free-text care-coordination notes, appended as items in a `notes` array rather than as "
            "separate documents so a patient's history stays in one place. Written both by the "
            "coordinator UI and by a doctor responding to an alert, which is what each note's "
            "`source` records."),
 },
 "executive_summary": {
  "one_line": "One document per batch — cohort-level counts",
  "intro": ("Band counts for a whole batch, pre-aggregated so the dashboard header does not "
            "recount the cohort on every page load. One document per `batch_date`."),
 },
 "users": {
  "one_line": "Login accounts",
  "intro": ("Authentication records. `role` separates a patient account, which is scoped to the "
            "single `patient_id` it carries, from a hospital account, which has no `patient_id` "
            "and sees the whole worklist."),
  "after": ("**Sensitive.** `password_hash` holds PBKDF2-SHA256 digests. They are hashes, not "
            "recoverable passwords, but they are credential material: do not copy this collection "
            "into a notebook, a fixture, an export or a bug report."),
 },
}

# Field-level meanings. Anything omitted renders with an empty Meaning cell rather than a guess.
_UNIVERSAL = {
 "patient_id": "Dashboard patient identifier. Prefixed `MIMIC-` and derived from the MIMIC `subject_id` for the current cohort; a bare integer on earlier manual-entry records.",
 "batch_date": "The scoring batch this document belongs to. The practical way to separate cohorts.",
 "risk_score": "Readmission risk, 0 to 100.",
 "risk_band": "`Low` below 20, `Medium` 20 to under 40, `High` 40 and above. Fixed product bands, not quantiles.",
 "model_version": "Identifier of the model that produced the score. Compare only within one version.",
 "driver_1": "Top contributing factor, as a sentence carrying the value and why it matters.",
 "driver_2": "Second contributing factor, same format.",
 "driver_3": "Third contributing factor, same format.",
 "primary_diagnosis": "Long-form text of the principal discharge diagnosis.",
 "primary_icd_code": "ICD code for the principal diagnosis, without punctuation. Mixed ICD-9 and ICD-10 — the cohort spans the transition.",
 "n_diagnoses_coded": "How many diagnoses were coded for the stay.",
 "n_prior_adm": "Count of the patient's earlier admissions in the dataset. 0 on a first appearance.",
 "los_days": "Length of stay in days. A few negatives come from source records where discharge precedes admission.",
 "admit_date": "Admission date, de-shifted to the real calendar.",
 "discharge_date": "Discharge date, de-shifted to the real calendar.",
 "anchor_age": "Patient age. Capped at 91 for de-identification, so 91 means 89 or older.",
 "gender": "Recorded sex.",
 "clinical_group": "Monitoring group the patient was routed to, derived from their diagnoses.",
 "group_label": "Human-readable name of `clinical_group`, as shown in the dashboard.",
 "group_confidence": "`high` matched an ICD code, `moderate` matched diagnosis text only, `default` nothing matched and the patient fell back to general monitoring.",
 "group_evidence": "Which diagnosis placed the patient in the group.",
 "severity": "Forecast severity that justified the alert.",
 "doctor_id": "Identifier of the clinician, derived from their name at registration.",
 "created_at": "When the document was written.",
 "updated_at": "When the document was last changed.",
 "alert_id": "Alert identifier. Joins `clinical_alerts` to `notifications` one-to-one.",
 "source": "Which intake wrote the document.",
}

DESCRIPTIONS = {
 "patient_worklist": {**_UNIVERSAL,
  "discharge_score": "The model's calibrated risk at discharge — the starting point of the trend.",
  "current_score": "Latest weekly risk score. Floors at 1.0.",
  "current_band": "Band of `current_score`, on the same fixed thresholds as `risk_band`.",
  "trend_delta": "`current_score` minus `discharge_score`. Positive means deteriorating.",
  "monitoring_status": "Derived trend label driving the worklist sort: `action_required`, `deteriorating`, `stable` or `improving`.",
  "status_rank": "Numeric rank of `monitoring_status`, so MongoDB can sort by urgency server-side.",
  "band_rank": "Numeric rank of `current_band`, for the same reason.",
  "weeks_tracked": "How many weekly documents exist for this patient.",
  "age_is_censored": "True when `anchor_age` hit the de-identification cap, so the age is a floor rather than a value.",
  "clinical_groups": "Every monitoring group the patient's diagnoses matched, not just the primary one.",
  "group_matches": "One entry per matched group, carrying what it matched on and with what confidence.",
  "secondary_diagnoses": "Text of the secondary diagnoses carried for this patient.",
  "primary_driver_label": "Copy of `driver_1`, denormalised so the worklist can sort and filter on it.",
  "summary_refreshed": "When the derived worklist fields were last recomputed.",
  "raw_inputs": "Original model inputs, kept verbatim. **Earlier manual-entry records only** — the keys below come from a different source dataset and do not map onto any other field in this database.",
 },
 "risk_registry": {**_UNIVERSAL},
 "weekly_monitoring": {**_UNIVERSAL,
  "week_number": "**Week 0 is the discharge baseline**; weeks 1 to 4 are the post-discharge series. A patient logging their own week can push their series past week 4, which is the only reason any document reads higher.",
  "days_after_discharge": "Days since discharge — 0 at week 0, then 7 per week.",
  "week_date": "Calendar date the week's observations belong to.",
  "observed": "Whether observations exist for the week. False means the week was not reported.",
  "scored_by": "`model` at week 0, `monitoring_rules` from week 1. The cleanest way to tell a model score from a rule-adjusted one.",
  "rule_adjustment": "Points the rule layer added or removed this week, before the carry term.",
  "note": "Free-text note from a patient-logged week.",
  "logged_at": "Timestamp of a patient-logged week.",
  "logged_by": "Account that logged the week.",
  "reported_fields": "Which fields the patient actually supplied on a self-logged week.",
  "monitoring": "The week's observations. Absent at week 0.",
  "monitoring.weight_change_kg": "Weight change since discharge, kg. A gain over 2 kg in a week is the classic fluid-retention signal in heart failure. **Universal.**",
  "monitoring.adherence_pct": "Percentage of prescribed doses covered this week. **Universal.**",
  "monitoring.refill_status": "Whether the prescription due this week was collected. **Universal.**",
  "monitoring.followup_status": "Whether the scheduled follow-up was attended. **Universal.**",
  "monitoring.sbp": "Systolic blood pressure, mmHg. **Universal.**",
  "monitoring.heart_rate": "Resting heart rate, bpm. **Universal.**",
  "monitoring.spo2": "Oxygen saturation, percent. **Universal.**",
  "monitoring.walk_distance_pct": "Walking distance as a percentage of the patient's usual distance at discharge. *Mobility groups.*",
  "monitoring.temperature_c": "Body temperature, Celsius. *Infection groups.*",
  "monitoring.wound_status": "Surgical wound appearance. *Surgical and injury.*",
  "monitoring.pain_trend": "Direction of pain since last week. *Surgical and injury.*",
  "monitoring.orthopnoea_pillows": "Pillows needed to sleep without breathlessness. *Heart failure.*",
  "monitoring.ankle_swelling": "Ankle oedema. *Heart failure.*",
  "monitoring.rescue_inhaler_uses": "Rescue inhaler actuations this week. *Respiratory.*",
  "monitoring.sputum_change": "Change in sputum volume or character. *Respiratory.*",
  "monitoring.antibiotic_course": "Progress through a prescribed antibiotic course. *Sepsis and infection.*",
  "monitoring.new_confusion": "New-onset confusion — a red flag for sepsis in older patients. *Sepsis and infection.*",
  "discharge_baseline": "The patient's discharge reference values. Week 0 only; every later week is compared against these.",
  "discharge_baseline.dry_weight_kg": "Weight at discharge, the reference `weight_change_kg` is measured against.",
  "discharge_baseline.baseline_spo2": "Oxygen saturation at discharge.",
  "discharge_baseline.baseline_sbp": "Systolic blood pressure at discharge.",
  "discharge_baseline.baseline_hr": "Resting heart rate at discharge.",
  "discharge_baseline.usual_walk_metres": "Usual walking distance at discharge, the reference `walk_distance_pct` is measured against.",
  "discharge_baseline.baseline_pain": "Pain score at discharge, 0 to 10.",
  "discharge_baseline.group": "Clinical group the baseline was derived for.",
 },
 "clinical_alerts": {**_UNIVERSAL,
  "week_number": "Monitoring week the alert was raised from.",
  "status": "`pending`, `acknowledged` or `responded`. Both of the first two count as open.",
  "doctor_name": "Name of the routed clinician, denormalised so the alert reads without a join.",
  "routing_reason": "Why this doctor received it — a claimed condition, their specialty on call, or the internal-medicine fallback.",
  "acknowledged_at": "When the doctor acknowledged the alert.",
  "acknowledged_by": "Which doctor acknowledged it.",
  "response": "The doctor's response. Null until they reply.",
  "response.recommendation": "Free-text clinical recommendation.",
  "response.actions": "Recommended action codes chosen from the fixed list.",
  "response.action_labels": "Human-readable labels for those codes.",
  "response.urgency": "How soon the doctor wants the action taken.",
  "response.specialty": "Specialty of the responding doctor, as recorded at response time.",
  "response.doctor_id": "Responding doctor.",
  "response.doctor_name": "Responding doctor's name.",
  "response.responded_at": "When the response was written.",
  "forecast": "The whole forecast that produced the alert, embedded so the alert is self-contained.",
  "forecast.as_of_week": "Week the forecast was computed from.",
  "forecast.weeks_observed": "How many weekly observations fed the forecast.",
  "forecast.horizon_weeks": "How far ahead the projection runs.",
  "forecast.current_score": "Risk score at the forecast week.",
  "forecast.current_band": "Band of `current_score`.",
  "forecast.projected_score": "Projected score at the horizon. Ceilings at 100.0.",
  "forecast.projected_band": "Band the projection lands in.",
  "forecast.velocity_per_week": "Least-squares slope of the patient's weekly scores — points per week.",
  "forecast.acceleration": "Change in that slope. Only treated as a warning while the trend is already going the wrong way.",
  "forecast.band_crossing": "The projected band change, or null if the patient is not projected to cross.",
  "forecast.band_crossing.from_band": "Band the patient is in now.",
  "forecast.band_crossing.to_band": "Band they are projected to reach.",
  "forecast.band_crossing.crosses_at_week": "Week the crossing is projected for.",
  "forecast.band_crossing.lead_time_days": "Days of warning before that crossing.",
  "forecast.triggers": "Every rule that fired, each with its stream, severity and rationale.",
  "forecast.streams": "Which evidence streams contributed: trajectory, condition-specific red flags, engagement.",
  "forecast.corroborated": "True when two or more streams independently reached high severity.",
  "forecast.severity": "Overall severity after combining the triggers.",
  "forecast.recommended_review_by": "How soon the forecast says the patient should be reviewed.",
  "forecast.confidence": "Confidence in the forecast, from how much history and how many signals were available.",
  "forecast.confidence_reason": "The weeks-of-history and signal count behind that confidence.",
  "forecast.status": "`ok` when the forecast ran; anything else records why it could not.",
  "forecast.basis": "Plain-language statement of what the projection is and is not. Worth reading before quoting a projected score.",
  "forecast.clinical_group": "Group whose condition-specific thresholds were applied.",
  "patient": "Patient context at alert time, denormalised so the alert needs no join.",
  "patient.anchor_age": "Age, capped at 91 for de-identification.",
  "patient.gender": "Recorded sex.",
  "patient.current_score": "Risk score at alert time.",
  "patient.current_band": "Band at alert time.",
  "patient.clinical_group": "Monitoring group.",
  "patient.group_label": "Human-readable group name.",
  "patient.primary_diagnosis": "Principal discharge diagnosis.",
  "patient.discharge_date": "Discharge date.",
 },
 "notifications": {**_UNIVERSAL,
  "notification_id": "Notification identifier.",
  "kind": "What happened. `new_alert` is the only kind currently written.",
  "channel": "Delivery channel. `in_app` only — no email or SMS transport is wired up.",
  "read": "Whether the doctor has opened it.",
  "delivered": "Whether delivery to the channel succeeded.",
 },
 "doctors": {**_UNIVERSAL,
  "name": "Clinician's display name, as entered at registration.",
  "email": "Contact address, and the natural key — re-registering the same address updates the record.",
  "specialty": "Declared specialty. Used as the routing fallback when `clinical_groups` is empty.",
  "clinical_groups": "Conditions the doctor explicitly claims. May be empty, in which case routing uses `specialty`.",
  "active": "Whether the doctor is in the routing rota.",
  "registered_at": "When they registered.",
 },
 "care_actions": {**_UNIVERSAL,
  "coordinator_name": "Care coordinator assigned to the patient, or null if unassigned.",
  "assigned_at": "When they were assigned.",
  "notes": "Appended notes. Each carries its text, author, source, urgency and the alert it came from, if any.",
 },
 "executive_summary": {**_UNIVERSAL,
  "total_patients": "Patients in the batch.",
  "high_count": "Patients in the High band.",
  "medium_count": "Patients in the Medium band.",
  "low_count": "Patients in the Low band.",
  "pct_high": "High-band patients as a percentage of the batch.",
  "wow_change": "Week-on-week change. `N/A` until two comparable batches exist.",
 },
 "users": {**_UNIVERSAL,
  "username": "Login name.",
  "password_hash": "PBKDF2-SHA256 digest. **Credential material — do not export.**",
  "display_name": "Name shown in the UI.",
  "role": "`patient` scopes the account to its own `patient_id`; `hospital` sees the whole worklist.",
  "patient_id": "The single patient a `patient` account may see. Absent on hospital accounts.",
 },
}
