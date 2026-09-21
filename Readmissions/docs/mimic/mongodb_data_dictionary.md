# Preventra MongoDB — data dictionary

Every collection in the `neuroshield` database, measured by a full scan. **9 collections · 33,644 documents.**

> Built by `scripts/build_mongo_dictionary.py`. Do not edit by hand — re-run it after any change to the data.

| Collection | Documents | Field paths | What it holds |
|---|---|---|---|
| [`patient_worklist`](#patient-worklist) | 4,047 | 52 | One document per patient — the dashboard worklist |
| [`risk_registry`](#risk-registry) | 7,945 | 16 | One document per scored discharge — the history |
| [`weekly_monitoring`](#weekly-monitoring) | 20,002 | 51 | One document per patient per week — the post-discharge series |
| [`clinical_alerts`](#clinical-alerts) | 817 | 56 | One document per forecast alert raised for a doctor |
| [`notifications`](#notifications) | 817 | 11 | One document per alert, per recipient doctor |
| [`doctors`](#doctors) | 5 | 9 | Registered clinicians and what they cover |
| [`care_actions`](#care-actions) | 2 | 5 | Coordinator notes against a patient |
| [`executive_summary`](#executive-summary) | 5 | 8 | One document per batch — cohort-level counts |
| [`users`](#users) | 4 | 8 | Login accounts |


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


## patient_worklist

The table the dashboard renders. One document per patient, carrying the discharge score, the latest weekly score, the trend between them, the monitoring group and the three ranked drivers. The `*_rank` fields exist purely so MongoDB can sort by band and status without a client-side pass, which is why this collection has far more indexes than any other.

**4,047 documents · 52 field paths · 13 indexes:** `{_id: 1}`, `{batch_date: 1, risk_score: -1}`, `{batch_date: 1, clinical_group: 1}`, `{patient_id: 1}`, `{batch_date: 1, current_score: -1}`, `{batch_date: 1, current_band: 1}`, `{batch_date: 1, monitoring_status: 1}`, `{batch_date: 1, status_rank: -1}`, `{batch_date: 1, band_rank: -1}`, `{batch_date: 1, trend_delta: -1}`, `{batch_date: 1, discharge_date: -1}`, `{batch_date: 1, primary_diagnosis: 1}`, `{batch_date: 1, clinical_groups: 1}`

| Field | Type | Present | Range / values | Meaning |
|---|---|---|---|---|
| `admit_date` | str | 98.84% | 80+ distinct | Admission date, de-shifted to the real calendar. |
| `age_is_censored` | bool | 98.84% | `False` (3,871), `True` (129) | True when `anchor_age` hit the de-identification cap, so the age is a floor rather than a value. |
| `anchor_age` | int | 98.84% | 18 to 91; 73 distinct; most common `91` (129), `63` (89), `62` (83) | Patient age. Capped at 91 for de-identification, so 91 means 89 or older. |
| `band_rank` | int | 98.84% | `1` (2,758), `3` (660), `2` (582) | Numeric rank of `current_band`, for the same reason. |
| `batch_date` | str | all | `2026-09-08` (4,000), `2026-04-22` (47) | The scoring batch this document belongs to. The practical way to separate cohorts. |
| `clinical_group` | str | all | 11 distinct; most common `general` (1,365), `surgical_injury` (430), `heart_failure` (413) | Monitoring group the patient was routed to, derived from their diagnoses. |
| `clinical_groups` | list | all | 1 to 4 items | Every monitoring group the patient's diagnoses matched, not just the primary one. |
| `current_band` | str | 98.84% | `Low` (2,758), `High` (660), `Medium` (582) | Band of `current_score`, on the same fixed thresholds as `risk_band`. |
| `current_score` | float | 98.84% | 1 to 96; 80+ distinct | Latest weekly risk score. Floors at 1.0. |
| `discharge_date` | str | all | 80+ distinct | Discharge date, de-shifted to the real calendar. |
| `discharge_score` | float | 98.84% | 0 to 66.7; 58 distinct; most common `10.8` (282), `6.9` (251), `16.2` (248) | The model's calibrated risk at discharge — the starting point of the trend. |
| `driver_1` | str | all | 80+ distinct | Top contributing factor, as a sentence carrying the value and why it matters. |
| `driver_2` | str | all | 80+ distinct | Second contributing factor, same format. |
| `driver_3` | str | all | 80+ distinct | Third contributing factor, same format. |
| `gender` | str | 98.84% | `F` (2,134), `M` (1,866) | Recorded sex. |
| `group_confidence` | str | all | `moderate` (1,546), `default` (1,365), `high` (1,136) | `high` matched an ICD code, `moderate` matched diagnosis text only, `default` nothing matched and the patient fell back to general monitoring. |
| `group_evidence` | str | all | 80+ distinct | Which diagnosis placed the patient in the group. |
| `group_label` | str | all | 11 distinct; most common `General recovery` (1,365), `Surgery or injury recovery` (430), `Heart failure` (413) | Human-readable name of `clinical_group`, as shown in the dashboard. |
| `group_matches` | list | all | 0 to 4 items; item keys: `confidence`, `evidence`, `group`, `label`, `matched_on` | One entry per matched group, carrying what it matched on and with what confidence. |
| `los_days` | float | 98.84% | -0.1 to 223.7; 80+ distinct | Length of stay in days. A few negatives come from source records where discharge precedes admission. |
| `monitoring_status` | str | 98.84% | `stable` (2,984), `deteriorating` (750), `improving` (170), `action_required` (96) | Derived trend label driving the worklist sort: `action_required`, `deteriorating`, `stable` or `improving`. |
| `n_diagnoses_coded` | int | 98.84% | 0 to 39; 40 distinct; most common `8` (270), `7` (259), `4` (244) | How many diagnoses were coded for the stay. |
| `n_prior_adm` | int | 98.84% | 0 to 94; 34 distinct; most common `0` (2,132), `1` (791), `2` (389) | Count of the patient's earlier admissions in the dataset. 0 on a first appearance. |
| `patient_id` | str / int | all | 196,758 to 113,626,674; 80+ distinct | Dashboard patient identifier. Prefixed `MIMIC-` and derived from the MIMIC `subject_id` for the current cohort; a bare integer on earlier manual-entry records. |
| `primary_diagnosis` | str | 98.84% | 80+ distinct | Long-form text of the principal discharge diagnosis. |
| `primary_driver_label` | str | 98.84% | 80+ distinct | Copy of `driver_1`, denormalised so the worklist can sort and filter on it. |
| `primary_icd_code` | str | 98.84% | 80+ distinct | ICD code for the principal diagnosis, without punctuation. Mixed ICD-9 and ICD-10 — the cohort spans the transition. |
| `raw_inputs` | dict | 99.88% | — | Original model inputs, kept verbatim. **Earlier manual-entry records only** — the keys below come from a different source dataset and do not map onto any other field in this database. |
| `raw_inputs.A1Cresult` | str | 1.04% | `None` (35), `>8` (4), `Norm` (2), `>7` (1) |  |
| `raw_inputs.admission_type_id` | int | 1.04% | 1 to 8; `1` (27), `3` (6), `2` (5), `5` (2), `6` (1), `8` (1) |  |
| `raw_inputs.age` | str | 1.04% | 8 distinct; most common `[80-90)` (14), `[70-80)` (9), `[50-60)` (8) |  |
| `raw_inputs.change` | str | 1.04% | `No` (24), `Ch` (18) |  |
| `raw_inputs.diabetesMed` | str | 1.04% | `Yes` (34), `No` (8) |  |
| `raw_inputs.discharge_disposition_id` | int | 1.04% | 1 to 23; 7 distinct; most common `1` (27), `6` (6), `3` (4) |  |
| `raw_inputs.gender` | str | 1.04% | `Female` (22), `Male` (20) |  |
| `raw_inputs.insulin` | str | 1.04% | `Steady` (18), `No` (15), `Down` (6), `Up` (3) |  |
| `raw_inputs.max_glu_serum` | str | 1.04% | `None` (40), `>200` (1), `Norm` (1) |  |
| `raw_inputs.num_medications` | int | 1.04% | 6 to 42; 24 distinct; most common `20` (5), `10` (4), `12` (3) |  |
| `raw_inputs.number_diagnoses` | int | 1.04% | `9` (23), `5` (5), `6` (5), `8` (5), `7` (4) |  |
| `raw_inputs.number_emergency` | int | 1.04% | 0 to 7; `0` (28), `2` (5), `1` (4), `3` (3), `6` (1), `7` (1) |  |
| `raw_inputs.number_inpatient` | int | 1.04% | 0 to 7; 7 distinct; most common `0` (22), `2` (8), `1` (5) |  |
| `raw_inputs.race` | str | 1.04% | `Caucasian` (30), `AfricanAmerican` (9), `?` (2), `Other` (1) |  |
| `raw_inputs.time_in_hospital` | int | 1.04% | 1 to 14; 13 distinct; most common `2` (10), `3` (7), `1` (4) |  |
| `risk_band` | str | all | `Low` (2,814), `Medium` (1,066), `High` (167) | `Low` below 20, `Medium` 20 to under 40, `High` 40 and above. Fixed product bands, not quantiles. |
| `risk_score` | float | all | 0 to 90.4; 80+ distinct | Readmission risk, 0 to 100. |
| `secondary_diagnoses` | list | 98.84% | 0 to 3 items | Text of the secondary diagnoses carried for this patient. |
| `source` | str | 98.94% | `mimic` (4,000), `manual` (4) | Which intake wrote the document. |
| `status_rank` | int | 98.84% | `2` (2,984), `3` (750), `1` (170), `4` (96) | Numeric rank of `monitoring_status`, so MongoDB can sort by urgency server-side. |
| `summary_refreshed` | str | 98.84% | `2026-09-10 08:17:16` | When the derived worklist fields were last recomputed. |
| `trend_delta` | float | 98.84% | -9.1 to 51.1; 80+ distinct | `current_score` minus `discharge_score`. Positive means deteriorating. |
| `weeks_tracked` | int | 98.84% | `5` (3,999), `7` (1) | How many weekly documents exist for this patient. |

## risk_registry

Every hospital stay that has been scored, which is why it is larger than the worklist: a patient with several admissions appears once per admission. This is the history the worklist summarises, and the only collection where `admit_date` and `discharge_date` carry real de-shifted MIMIC dates spanning 2009 onwards.

**7,945 documents · 16 field paths · 1 index:** `{_id: 1}`

| Field | Type | Present | Range / values | Meaning |
|---|---|---|---|---|
| `admit_date` | str | 99.46% | 80+ distinct | Admission date, de-shifted to the real calendar. |
| `batch_date` | str | all | 80+ distinct | The scoring batch this document belongs to. The practical way to separate cohorts. |
| `discharge_date` | str | 99.46% | 80+ distinct | Discharge date, de-shifted to the real calendar. |
| `driver_1` | str | all | 80+ distinct | Top contributing factor, as a sentence carrying the value and why it matters. |
| `driver_2` | str | all | 80+ distinct | Second contributing factor, same format. |
| `driver_3` | str | all | 80+ distinct | Third contributing factor, same format. |
| `los_days` | float | 99.46% | 0 to 223.7; 80+ distinct | Length of stay in days. A few negatives come from source records where discharge precedes admission. |
| `model_version` | str | all | `mimic-hgb-calibrated-v1` (7,902), `readmission-dt-balanced-importa…` (43) | Identifier of the model that produced the score. Compare only within one version. |
| `n_diagnoses_coded` | int | 99.46% | 0 to 39; 40 distinct; most common `8` (515), `7` (491), `9` (466) | How many diagnoses were coded for the stay. |
| `n_prior_adm` | int | 99.46% | 0 to 94; 62 distinct; most common `0` (3,424), `1` (1,550), `2` (833) | Count of the patient's earlier admissions in the dataset. 0 on a first appearance. |
| `patient_id` | str / int | all | 196,758 to 114,314,355; 80+ distinct | Dashboard patient identifier. Prefixed `MIMIC-` and derived from the MIMIC `subject_id` for the current cohort; a bare integer on earlier manual-entry records. |
| `primary_diagnosis` | str | 99.46% | 80+ distinct | Long-form text of the principal discharge diagnosis. |
| `primary_icd_code` | str | 99.46% | 80+ distinct | ICD code for the principal diagnosis, without punctuation. Mixed ICD-9 and ICD-10 — the cohort spans the transition. |
| `risk_band` | str | all | `Low` (4,617), `Medium` (2,689), `High` (639) | `Low` below 20, `Medium` 20 to under 40, `High` 40 and above. Fixed product bands, not quantiles. |
| `risk_score` | float | all | 0 to 90.4; 80+ distinct | Readmission risk, 0 to 100. |

## weekly_monitoring

The post-discharge series behind the risk trend. **Week 0 is the discharge baseline** and carries a `discharge_baseline` sub-document instead of `monitoring`; weeks 1 to 4 carry `monitoring` and no baseline. That split is why both sub-documents read as present on a fixed fraction of rows rather than all of them.

Within `monitoring`, seven signals are collected for everyone and the rest only for the clinical groups they are meaningful to. A low presence figure on those rows means *not applicable to this patient's group*, not missing data.

**20,002 documents · 51 field paths · 2 indexes:** `{_id: 1}`, `{patient_id: 1, week_number: 1}`

| Field | Type | Present | Range / values | Meaning |
|---|---|---|---|---|
| `clinical_group` | str | 99.99% | 11 distinct; most common `general` (6,590), `surgical_injury` (2,150), `heart_failure` (2,065) | Monitoring group the patient was routed to, derived from their diagnoses. |
| `days_after_discharge` | int | all | 0 to 42; 7 distinct; most common `0` (4,000), `14` (4,000), `21` (4,000) | Days since discharge — 0 at week 0, then 7 per week. |
| `discharge_baseline` | dict | 20% | — | The patient's discharge reference values. Week 0 only; every later week is compared against these. |
| `discharge_baseline.baseline_hr` | float | 20% | 67.3 to 93.7; 80+ distinct | Resting heart rate at discharge. |
| `discharge_baseline.baseline_pain` | int | 20% | 1 to 6; `2` (1,937), `3` (844), `1` (834), `5` (173), `4` (170), `6` (42) | Pain score at discharge, 0 to 10. |
| `discharge_baseline.baseline_sbp` | float | 20% | 116.2 to 153.3; 80+ distinct | Systolic blood pressure at discharge. |
| `discharge_baseline.baseline_spo2` | float | 20% | 89.6 to 98.2; 80+ distinct | Oxygen saturation at discharge. |
| `discharge_baseline.dry_weight_kg` | float | 20% | 57.1 to 101.1; 80+ distinct | Weight at discharge, the reference `weight_change_kg` is measured against. |
| `discharge_baseline.group` | str | 20% | 11 distinct; most common `general` (1,318), `surgical_injury` (430), `heart_failure` (413) | Clinical group the baseline was derived for. |
| `discharge_baseline.usual_walk_metres` | float | 20% | 97.8 to 674.9; 80+ distinct | Usual walking distance at discharge, the reference `walk_distance_pct` is measured against. |
| `driver_1` | str | all | 80+ distinct | Top contributing factor, as a sentence carrying the value and why it matters. |
| `driver_2` | str | all | 80+ distinct | Second contributing factor, same format. |
| `driver_3` | str | all | 80+ distinct | Third contributing factor, same format. |
| `group_confidence` | str | 99.99% | `moderate` (7,730), `default` (6,590), `high` (5,680) | `high` matched an ICD code, `moderate` matched diagnosis text only, `default` nothing matched and the patient fell back to general monitoring. |
| `group_evidence` | str | 99.99% | 80+ distinct | Which diagnosis placed the patient in the group. |
| `group_label` | str | 99.99% | 11 distinct; most common `General recovery` (6,590), `Surgery or injury recovery` (2,150), `Heart failure` (2,065) | Human-readable name of `clinical_group`, as shown in the dashboard. |
| `logged_at` | str | 0.01% | `2026-09-04 16:02:20` (1), `2026-09-04 16:02:21` (1) | Timestamp of a patient-logged week. |
| `logged_by` | str | 0.01% | `pt10006029` | Account that logged the week. |
| `model_version` | str | all | `mimic-hgb-calibrated-v1` | Identifier of the model that produced the score. Compare only within one version. |
| `monitoring` | dict | 80% | — | The week's observations. Absent at week 0. |
| `monitoring.adherence_pct` | int / float | 80% | 9 to 100; 80+ distinct | Percentage of prescribed doses covered this week. **Universal.** |
| `monitoring.ankle_swelling` | str | 8.26% | `none` (1,091), `mild` (398), `marked` (163) | Ankle oedema. *Heart failure.* |
| `monitoring.antibiotic_course` | str | 2.26% | `completed` (190), `ongoing` (142), `not_prescribed` (73), `stopped_early` (47) | Progress through a prescribed antibiotic course. *Sepsis and infection.* |
| `monitoring.followup_status` | str | 80% | `attended` (9,593), `not due` (4,765), `missed` (1,644) | Whether the scheduled follow-up was attended. **Universal.** |
| `monitoring.heart_rate` | int / float | 80% | 46 to 136; 80+ distinct | Resting heart rate, bpm. **Universal.** |
| `monitoring.new_confusion` | str | 2.26% | `no` (396), `yes` (56) | New-onset confusion — a red flag for sepsis in older patients. *Sepsis and infection.* |
| `monitoring.orthopnoea_pillows` | int | 8.26% | `1` (729), `0` (599), `2` (202), `3` (103), `4` (19) | Pillows needed to sleep without breathlessness. *Heart failure.* |
| `monitoring.pain_trend` | str | 8.6% | `improving` (1,173), `unchanged` (405), `worse` (142) | Direction of pain since last week. *Surgical and injury.* |
| `monitoring.refill_status` | str | 80% | `collected` (11,216), `not due` (1,755), `late` (1,638), `missed` (1,393) | Whether the prescription due this week was collected. **Universal.** |
| `monitoring.rescue_inhaler_uses` | int | 6.42% | 0 to 26; 26 distinct; most common `0` (393), `1` (193), `2` (185) | Rescue inhaler actuations this week. *Respiratory.* |
| `monitoring.sbp` | int / float | 80% | 95 to 201; 80+ distinct | Systolic blood pressure, mmHg. **Universal.** |
| `monitoring.spo2` | int / float | 80% | 85 to 100; 18 distinct; most common `96` (3,916), `97` (3,636), `95` (2,503) | Oxygen saturation, percent. **Universal.** |
| `monitoring.sputum_change` | str | 6.42% | `none` (908), `volume` (201), `purulent` (106), `both` (69) | Change in sputum volume or character. *Respiratory.* |
| `monitoring.temperature_c` | float | 10.86% | 35.3 to 39.2; 37 distinct; most common `36.9` (222), `36.6` (203), `36.8` (193) | Body temperature, Celsius. *Infection groups.* |
| `monitoring.walk_distance_pct` | int | 23.28% | 5 to 130; 80+ distinct | Walking distance as a percentage of the patient's usual distance at discharge. *Mobility groups.* |
| `monitoring.weight_change_kg` | float | 80% | -2.8 to 5.6; 80+ distinct | Weight change since discharge, kg. A gain over 2 kg in a week is the classic fluid-retention signal in heart failure. **Universal.** |
| `monitoring.wound_status` | str | 8.6% | `clean` (1,315), `red` (236), `discharge` (131), `opening` (38) | Surgical wound appearance. *Surgical and injury.* |
| `note` | str / null | 0.01% | `None` (1), `more breathless on stairs` (1) | Free-text note from a patient-logged week. |
| `observed` | bool | all | `True` (18,079), `False` (1,923) | Whether observations exist for the week. False means the week was not reported. |
| `patient_id` | str | all | 80+ distinct | Dashboard patient identifier. Prefixed `MIMIC-` and derived from the MIMIC `subject_id` for the current cohort; a bare integer on earlier manual-entry records. |
| `reported_fields` | list | 0.01% | 6 to 7 items | Which fields the patient actually supplied on a self-logged week. |
| `risk_band` | str | all | `Low` (14,049), `Medium` (4,071), `High` (1,882) | `Low` below 20, `Medium` 20 to under 40, `High` 40 and above. Fixed product bands, not quantiles. |
| `risk_score` | float | all | 0 to 96; 80+ distinct | Readmission risk, 0 to 100. |
| `rule_adjustment` | float | 0.01% | `-6.3` (1), `29.5` (1) | Points the rule layer added or removed this week, before the carry term. |
| `scored_by` | str | all | `monitoring_rules` (16,002), `model` (4,000) | `model` at week 0, `monitoring_rules` from week 1. The cleanest way to tell a model score from a rule-adjusted one. |
| `week_date` | str | all | 80+ distinct | Calendar date the week's observations belong to. |
| `week_number` | int | all | 0 to 6; 7 distinct; most common `0` (4,000), `1` (4,000), `2` (4,000) | **Week 0 is the discharge baseline**; weeks 1 to 4 are the post-discharge series. A patient logging their own week can push their series past week 4, which is the only reason any document reads higher. |

## clinical_alerts

An alert raised when the early-warning forecast crosses a severity threshold, with the whole forecast embedded so the alert is readable without re-running anything. Every alert in the collection was raised from the same forecast week, which is why `week_number` and `forecast.as_of_week` are single-valued.

`forecast.triggers` is the list of individual rules that fired; `forecast.streams` names which of the three evidence streams (trajectory, condition-specific red flags, engagement) contributed. `forecast.corroborated` is true when two or more streams independently reached high severity.

**817 documents · 56 field paths · 1 index:** `{_id: 1}`

| Field | Type | Present | Range / values | Meaning |
|---|---|---|---|---|
| `acknowledged_at` | str | 0.12% | `2026-09-16 11:20:06` | When the doctor acknowledged the alert. |
| `acknowledged_by` | str | 0.12% | `DR-dr-sarah-whitfield-0a8a9c` | Which doctor acknowledged it. |
| `alert_id` | str | all | 80+ distinct | Alert identifier. Joins `clinical_alerts` to `notifications` one-to-one. |
| `created_at` | str | all | `2026-09-16 11:19:23` | When the document was written. |
| `doctor_id` | str | all | `DR-dr-amir-haddad-a2c294` (486), `DR-dr-sarah-whitfield-0a8a9c` (165), `DR-dr-priya-raman-e0d761` (88), `DR-dr-elena-kova-0db722` (78) | Identifier of the clinician, derived from their name at registration. |
| `doctor_name` | str | all | `Dr. Amir Haddad` (486), `Dr. Sarah Whitfield` (165), `Dr. Priya Raman` (88), `Dr. Elena Kovač` (78) | Name of the routed clinician, denormalised so the alert reads without a join. |
| `forecast` | dict | all | — | The whole forecast that produced the alert, embedded so the alert is self-contained. |
| `forecast.acceleration` | float | all | -17.2 to 14.25; 80+ distinct | Change in that slope. Only treated as a warning while the trend is already going the wrong way. |
| `forecast.as_of_week` | int | all | `4` | Week the forecast was computed from. |
| `forecast.band_crossing` | null / dict | all | `None` | The projected band change, or null if the patient is not projected to cross. |
| `forecast.band_crossing.crosses_at_week` | int | 18.6% | `5` (126), `6` (26) | Week the crossing is projected for. |
| `forecast.band_crossing.from_band` | str | 18.6% | `Medium` (136), `Low` (16) | Band the patient is in now. |
| `forecast.band_crossing.lead_time_days` | int | 18.6% | 1 to 14; 14 distinct; most common `9` (18), `2` (17), `1` (16) | Days of warning before that crossing. |
| `forecast.band_crossing.to_band` | str | 18.6% | `High` (136), `Medium` (16) | Band they are projected to reach. |
| `forecast.basis` | str | all | `Linear projection of this patie…` | Plain-language statement of what the projection is and is not. Worth reading before quoting a projected score. |
| `forecast.clinical_group` | str | all | 11 distinct; most common `general` (154), `heart_failure` (125), `sepsis_infection` (112) | Group whose condition-specific thresholds were applied. |
| `forecast.confidence` | str | all | `high` | Confidence in the forecast, from how much history and how many signals were available. |
| `forecast.confidence_reason` | str | all | `5 weeks of history and 7 signal…` (427), `5 weeks of history and 10 signa…` (325), `5 weeks of history and 11 signa…` (65) | The weeks-of-history and signal count behind that confidence. |
| `forecast.corroborated` | bool | all | `False` (409), `True` (408) | True when two or more streams independently reached high severity. |
| `forecast.current_band` | str | all | `High` (516), `Medium` (213), `Low` (88) | Band of `current_score`. |
| `forecast.current_score` | float | all | 1 to 96; 80+ distinct | Risk score at the forecast week. |
| `forecast.horizon_weeks` | int | all | `2` | How far ahead the projection runs. |
| `forecast.projected_band` | str | all | `High` (649), `Medium` (91), `Low` (77) | Band the projection lands in. |
| `forecast.projected_score` | float | all | 0 to 100; 80+ distinct | Projected score at the horizon. Ceilings at 100.0. |
| `forecast.recommended_review_by` | str | all | `same day` (559), `within 48 hours` (258) | How soon the forecast says the patient should be reviewed. |
| `forecast.severity` | str | all | `critical` (559), `high` (258) | Overall severity after combining the triggers. |
| `forecast.status` | str | all | `ok` | `ok` when the forecast ran; anything else records why it could not. |
| `forecast.streams` | list | all | 1 to 4 items | Which evidence streams contributed: trajectory, condition-specific red flags, engagement. |
| `forecast.triggers` | list | all | 1 to 8 items; item keys: `code`, `detail`, `rationale`, `severity`, `stream`, `title` | Every rule that fired, each with its stream, severity and rationale. |
| `forecast.velocity_per_week` | float | all | -5.5 to 23.1; 80+ distinct | Least-squares slope of the patient's weekly scores — points per week. |
| `forecast.weeks_observed` | int | all | `5` | How many weekly observations fed the forecast. |
| `patient` | dict | all | — | Patient context at alert time, denormalised so the alert needs no join. |
| `patient.anchor_age` | int | all | 19 to 91; 72 distinct; most common `68` (28), `91` (26), `64` (25) | Age, capped at 91 for de-identification. |
| `patient.clinical_group` | str | all | 11 distinct; most common `general` (154), `heart_failure` (125), `sepsis_infection` (112) | Monitoring group. |
| `patient.current_band` | str | all | `High` (516), `Medium` (213), `Low` (88) | Band at alert time. |
| `patient.current_score` | float | all | 1 to 96; 80+ distinct | Risk score at alert time. |
| `patient.discharge_date` | str | all | 80+ distinct | Discharge date. |
| `patient.gender` | str | all | `M` (447), `F` (370) | Recorded sex. |
| `patient.group_label` | str | all | 11 distinct; most common `General recovery` (154), `Heart failure` (125), `Sepsis or serious infection` (112) | Human-readable group name. |
| `patient.primary_diagnosis` | str | all | 80+ distinct | Principal discharge diagnosis. |
| `patient_id` | str | all | 80+ distinct | Dashboard patient identifier. Prefixed `MIMIC-` and derived from the MIMIC `subject_id` for the current cohort; a bare integer on earlier manual-entry records. |
| `response` | null / dict | all | `None` | The doctor's response. Null until they reply. |
| `response.action_labels` | list | 0.12% | 3 to 3 items | Human-readable labels for those codes. |
| `response.actions` | list | 0.12% | 3 to 3 items | Recommended action codes chosen from the fixed list. |
| `response.doctor_id` | str | 0.12% | `DR-dr-sarah-whitfield-0a8a9c` | Responding doctor. |
| `response.doctor_name` | str | 0.12% | `Dr. Sarah Whitfield` | Responding doctor's name. |
| `response.recommendation` | str | 0.12% | `Increase furosemide to 80mg dai…` | Free-text clinical recommendation. |
| `response.responded_at` | str | 0.12% | `2026-09-16 11:20:07` | When the response was written. |
| `response.specialty` | str | 0.12% | `Cardiology` | Specialty of the responding doctor, as recorded at response time. |
| `response.urgency` | str | 0.12% | `urgent` | How soon the doctor wants the action taken. |
| `routing_reason` | str | all | 7 distinct; most common `no specialist registered, route…` (299), `covers general` (154), `covers heart failure` (125) | Why this doctor received it — a claimed condition, their specialty on call, or the internal-medicine fallback. |
| `severity` | str | all | `critical` (559), `high` (258) | Forecast severity that justified the alert. |
| `status` | str | all | `pending` (816), `responded` (1) | `pending`, `acknowledged` or `responded`. Both of the first two count as open. |
| `updated_at` | str | all | `2026-09-17 11:25:03` | When the document was last changed. |
| `week_number` | int | all | `4` | Monitoring week the alert was raised from. |

## notifications

The doctor-facing delivery record for each alert, one-to-one with `clinical_alerts` on `alert_id`. Separate from the alert so that read state belongs to the recipient rather than to the clinical record.

**817 documents · 11 field paths · 1 index:** `{_id: 1}`

| Field | Type | Present | Range / values | Meaning |
|---|---|---|---|---|
| `alert_id` | str | all | 80+ distinct | Alert identifier. Joins `clinical_alerts` to `notifications` one-to-one. |
| `channel` | str | all | `in_app` | Delivery channel. `in_app` only — no email or SMS transport is wired up. |
| `created_at` | str | all | `2026-09-16 11:19:23` | When the document was written. |
| `delivered` | bool | all | `True` | Whether delivery to the channel succeeded. |
| `doctor_id` | str | all | `DR-dr-amir-haddad-a2c294` (486), `DR-dr-sarah-whitfield-0a8a9c` (165), `DR-dr-priya-raman-e0d761` (88), `DR-dr-elena-kova-0db722` (78) | Identifier of the clinician, derived from their name at registration. |
| `kind` | str | all | `new_alert` | What happened. `new_alert` is the only kind currently written. |
| `notification_id` | str | all | 80+ distinct | Notification identifier. |
| `patient_id` | str | all | 80+ distinct | Dashboard patient identifier. Prefixed `MIMIC-` and derived from the MIMIC `subject_id` for the current cohort; a bare integer on earlier manual-entry records. |
| `read` | bool | all | `False` (816), `True` (1) | Whether the doctor has opened it. |
| `severity` | str | all | `critical` (559), `high` (258) | Forecast severity that justified the alert. |

## doctors

The clinician roster. `email` is the natural key — re-registering an existing address updates the record rather than adding one. `clinical_groups` is what a doctor explicitly claims; routing also falls back to `specialty`, so a doctor with an empty `clinical_groups` still receives alerts for the conditions their specialty maps to.

**5 documents · 9 field paths · 1 index:** `{_id: 1}`

| Field | Type | Present | Range / values | Meaning |
|---|---|---|---|---|
| `active` | bool | all | `True` | Whether the doctor is in the routing rota. |
| `clinical_groups` | list | all | 0 to 2 items | Conditions the doctor explicitly claims. May be empty, in which case routing uses `specialty`. |
| `doctor_id` | str | all | `DR-dr-amir-haddad-a2c294` (1), `DR-dr-elena-kova-0db722` (1), `DR-dr-partrick-jane-9edb46` (1), `DR-dr-priya-raman-e0d761` (1), `DR-dr-sarah-whitfield-0a8a9c` (1) | Identifier of the clinician, derived from their name at registration. |
| `email` | str | all | 5 distinct — **values withheld** | Contact address, and the natural key — re-registering the same address updates the record. |
| `name` | str | all | `Dr. Amir Haddad` (1), `Dr. Elena Kovač` (1), `Dr. Partrick Jane` (1), `Dr. Priya Raman` (1), `Dr. Sarah Whitfield` (1) | Clinician's display name, as entered at registration. |
| `registered_at` | str | all | `2026-09-16 10:50:07` (3), `2026-09-16 10:53:55` (1), `2026-09-16 15:48:46` (1) | When they registered. |
| `specialty` | str | all | `Cardiology` (1), `Internal Medicine` (1), `Oncology` (1), `Psychiatry` (1), `Pulmonology` (1) | Declared specialty. Used as the routing fallback when `clinical_groups` is empty. |
| `updated_at` | str | 60% | `2026-09-16 10:53:55` (2), `2026-09-16 10:53:54` (1) | When the document was last changed. |

**One data-entry issue, left as it is because it is a record about a person:** a name is spelt `Dr. Partrick Jane`, with an extra `r`. Visible in the values above.

## care_actions

Free-text care-coordination notes, appended as items in a `notes` array rather than as separate documents so a patient's history stays in one place. Written both by the coordinator UI and by a doctor responding to an alert, which is what each note's `source` records.

**2 documents · 5 field paths · 1 index:** `{_id: 1}`

| Field | Type | Present | Range / values | Meaning |
|---|---|---|---|---|
| `assigned_at` | str / null | all | `2026-07-29 23:53:54` (1), `None` (1) | When they were assigned. |
| `coordinator_name` | str / null | all | `Jane Doe` (1), `None` (1) | Care coordinator assigned to the patient, or null if unassigned. |
| `notes` | list | all | 1 to 1 items; item keys: `alert_id`, `author`, `created_at`, `source`, `text`, `urgency` | Appended notes. Each carries its text, author, source, urgency and the alert it came from, if any. |
| `patient_id` | str | all | `85299696` (1), `MIMIC-10057218` (1) | Dashboard patient identifier. Prefixed `MIMIC-` and derived from the MIMIC `subject_id` for the current cohort; a bare integer on earlier manual-entry records. |

## executive_summary

Band counts for a whole batch, pre-aggregated so the dashboard header does not recount the cohort on every page load. One document per `batch_date`.

**5 documents · 8 field paths · 1 index:** `{_id: 1}`

| Field | Type | Present | Range / values | Meaning |
|---|---|---|---|---|
| `batch_date` | str | all | `2026-04-22` (1), `2026-08-27` (1), `2026-08-31` (1), `2026-09-01` (1), `2026-09-08` (1) | The scoring batch this document belongs to. The practical way to separate cohorts. |
| `high_count` | int | all | `460` (3), `30` (1), `660` (1) | Patients in the High band. |
| `low_count` | int | all | `1107` (3), `2758` (1), `3` (1) | Patients in the Low band. |
| `medium_count` | int | all | `433` (3), `14` (1), `582` (1) | Patients in the Medium band. |
| `pct_high` | float | all | `23.0` (3), `16.5` (1), `63.83` (1) | High-band patients as a percentage of the batch. |
| `total_patients` | int | all | `2000` (3), `4000` (1), `47` (1) | Patients in the batch. |
| `wow_change` | str | all | `N/A` | Week-on-week change. `N/A` until two comparable batches exist. |

## users

Authentication records. `role` separates a patient account, which is scoped to the single `patient_id` it carries, from a hospital account, which has no `patient_id` and sees the whole worklist.

**4 documents · 8 field paths · 2 indexes:** `{_id: 1}`, `{username: 1}`

| Field | Type | Present | Range / values | Meaning |
|---|---|---|---|---|
| `created_at` | str | all | `2026-09-04 15:57:25` (2), `2026-09-04 15:57:26` (2) | When the document was written. |
| `display_name` | str | all | `Care Coordination Team` (1), `Patient MIMIC-10006029` (1), `Patient MIMIC-10008077` (1), `Patient MIMIC-10013569` (1) | Name shown in the UI. |
| `password_hash` | str | all | 4 distinct — **values withheld** | PBKDF2-SHA256 digest. **Credential material — do not export.** |
| `patient_id` | str | 75% | `MIMIC-10006029` (1), `MIMIC-10008077` (1), `MIMIC-10013569` (1) | The single patient a `patient` account may see. Absent on hospital accounts. |
| `role` | str | all | `patient` (3), `hospital` (1) | `patient` scopes the account to its own `patient_id`; `hospital` sees the whole worklist. |
| `updated_at` | str | all | `2026-09-04 15:57:25` (2), `2026-09-04 15:57:26` (2) | When the document was last changed. |
| `username` | str | all | `carecoord` (1), `pt10006029` (1), `pt10008077` (1), `pt10013569` (1) | Login name. |

**Sensitive.** `password_hash` holds PBKDF2-SHA256 digests. They are hashes, not recoverable passwords, but they are credential material: do not copy this collection into a notebook, a fixture, an export or a bug report.
