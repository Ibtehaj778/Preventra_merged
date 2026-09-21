# The disease landscape of MIMIC-IV

A plain-English guide to what the diagnoses in this project actually are — how many there are,
how they are organised, how many a single patient carries, and how much of that Preventra
currently uses.

**Every number here was measured on the complete MIMIC-IV dataset**: 6,364,488 diagnosis rows
across 545,497 hospital admissions and 223,291 patients. The analysis that produced them is
[`notebooks/mimic/solved-mimic-icd-analysis.ipynb`](../notebooks/mimic/solved-mimic-icd-analysis.ipynb),
run on Kaggle where the raw data lives.

---

## The short version

If you read nothing else:

- **A diagnosis code is a label, not a description.** It says *what* condition, not how bad it
  is or when it started.
- **There are 28,562 different codes** in MIMIC, organised into **20 broad families** called
  chapters.
- **Almost nobody has one disease.** The typical admission carries **10 diagnoses**; only 2.6%
  have a single one, and one admission has 57.
- **Those diagnoses scatter across the body.** 96% of admissions touch **two or more** chapters,
  and the average touches **six**.
- **A handful of codes do most of the work.** 250 codes — under 1% of them — account for half
  of every diagnosis ever recorded. Meanwhile 6,160 codes were used exactly once.
- **Preventra currently reduces all of this to two numbers**, and its weekly monitoring ignores
  diagnosis entirely. Section 6 is about what that costs.

---

## 1. What is an ICD code?

Think of ICD as a **catalogue system for illness**, in the way a library has a catalogue number
for every book. When a patient is discharged, a trained medical coder reads the notes and
assigns a code to every condition documented during the stay. `I50.23` is not shorthand a doctor
invented — it is an entry in an international dictionary that means one specific thing
everywhere in the world.

MIMIC stores those assignments in a table called `diagnoses_icd`, one row per code per
admission. Each row carries four useful things:

| Field | The question it answers | Example |
|---|---|---|
| `icd_code` | **What** condition | `I50.23` |
| `icd_version` | **Which edition** of the dictionary, 9 or 10 | `10` |
| `seq_num` | **How central** it was to this stay | `1` = the main reason for admission |
| `hadm_id` | **Which hospital stay** it belongs to | codes attach to a stay, not to a person |

`seq_num` matters more than it looks. **Exactly one code per admission has `seq_num = 1`** —
that is the *principal diagnosis*, the condition chiefly responsible for the patient being
there. Everything after it is a *secondary*: existing chronic conditions, complications that
developed, and anything else treated along the way.

### Three things a code deliberately does not tell you

- **How severe it is.** `I50.23` is acute-on-chronic systolic heart failure whether the patient
  walked in complaining of tiredness or arrived on a ventilator. The code is identical.
- **When it started.** A code on this admission might be a condition of twenty years' standing
  or something that appeared overnight. Discharge coding does not separate them.
- **Whether it was actually treated.** A coded condition is one the stay *documented*. Some are
  actively managed; some are noted in passing because they exist.

### A trap worth knowing about

MIMIC spans the 2015 US switch from ICD-9 to ICD-10, so **both editions are in the data**:
45.7% of rows are ICD-9, 54.3% ICD-10. The same string can be a valid code in both and mean
completely different things — `E66.01` is morbid obesity in ICD-10, while in ICD-9 the `E` block
is external causes of injury. Any code lookup must use the **code *and* the version together**,
which is why `models/mimic_diagnoses.py` always joins on the pair.

There is a knock-on effect: **1,332 diagnosis titles appear under both editions**. The same
clinical concept, split across two different codes purely because of when the patient was
admitted. Anything counting codes must handle that or it will treat one condition as two.

---

## 2. How the codes are organised

ICD is a tree. Each step to the right narrows the meaning:

```
Chapter      Diseases of the circulatory system     I00–I99     20 of these exist
  Block      Other forms of heart disease           I30–I52     a named grouping
    Category Heart failure                          I50         the 3-character stem
      Code   Acute on chronic systolic HF           I50.23      what actually gets recorded
```

Reading the code string itself, left to right:

```
I        the chapter letter    circulatory system
I50      category              heart failure
I50.2    subcategory           systolic heart failure
I50.23   full code             acute on chronic systolic heart failure
```

Here is the circulatory chapter as it actually appears in MIMIC — 486,103 diagnosis rows using
1,059 distinct ICD-10 codes, which fall into just 76 categories:

| Block | Meaning | Codes used | Rows |
|---|---|---:|---:|
| I00–I02 | Acute rheumatic fever | 3 | 19 |
| I05–I09 | Chronic rheumatic heart disease | 25 | 6,677 |
| I10–I16 | Hypertensive diseases | 17 | 139,717 |
| I20–I25 | Ischaemic heart diseases | 63 | 83,035 |
| I26–I28 | Pulmonary heart disease | 25 | 15,206 |
| I30–I52 | Other forms of heart disease | 132 | 144,593 |
| I60–I69 | Cerebrovascular diseases | 319 | 27,324 |
| I70–I79 | Arteries and capillaries | 199 | 21,410 |
| I80–I89 | Veins and lymphatics | 226 | 22,617 |
| I95–I99 | Other circulatory disorders | 49 | 25,359 |

Notice the imbalance. **Hypertension gets 17 codes and 139,717 uses; strokes get 319 codes and
27,324 uses.** Common conditions are described bluntly, rare ones in fine detail — a pattern
that runs through the whole system and matters enormously for any model built on it.

### One condition, twenty-three codes

Drill into category `I50`, heart failure, and it splits into 23 separate codes:

| Code | Rows | Meaning |
|---|---:|---|
| `I50.32` | 10,787 | Chronic **diastolic** heart failure |
| `I50.33` | 8,118 | **Acute on chronic** diastolic |
| `I50.22` | 7,507 | Chronic **systolic** |
| `I50.23` | 5,685 | Acute on chronic systolic |
| `I50.9` | 3,824 | Heart failure, **unspecified** |
| `I50.30` | 1,646 | Unspecified diastolic |
| `I50.21` | 1,503 | **Acute** systolic |
| … | | 16 further variants down to 11 rows |

Four things are being encoded at once: the **mechanism** (systolic, diastolic, combined, right,
left), the **acuity** (acute, chronic, or acute-on-chronic), the **severity** (`I50.84` is end
stage), and how confident the coder was (`I50.9` unspecified).

This is the single most important structural fact in this document. **Clinically these are one
disease. To a computer they are 23 unrelated labels** — plus another dozen ICD-9 equivalents.
Anything that treats codes as independent categories throws away the fact that they are the same
illness.

---

## 3. How many diseases are in MIMIC?

**28,562 distinct codes**, in **2,622 categories**, across **20 chapters**.

| Chapter | Distinct codes | Admissions touching it | % of admissions |
|---|---:|---:|---:|
| Factors influencing health status | 1,626 | 396,656 | 72.7% |
| Circulatory system | 1,513 | 353,086 | 64.7% |
| Endocrine, nutritional and metabolic | 807 | 342,417 | 62.8% |
| Symptoms, signs and abnormal findings | 921 | 264,215 | 48.4% |
| Mental, behavioural and neurodevelopmental | 948 | 238,565 | 43.7% |
| Digestive system | 1,105 | 230,998 | 42.3% |
| Nervous system and sense organs | 2,425 | 203,215 | 37.3% |
| Genitourinary system | 855 | 190,389 | 34.9% |
| Blood and immune mechanism | 362 | 171,117 | 31.4% |
| Musculoskeletal and connective tissue | 2,652 | 160,528 | 29.4% |
| Respiratory system | 535 | 159,122 | 29.2% |
| External causes of morbidity | 1,779 | 150,534 | 27.6% |
| Injury and poisoning | 7,486 | 140,711 | 25.8% |
| Infectious and parasitic diseases | 932 | 104,035 | 19.1% |
| Neoplasms (cancers) | 1,808 | 97,090 | 17.8% |
| Skin and subcutaneous tissue | 784 | 59,486 | 10.9% |
| Pregnancy and childbirth | 1,376 | 26,549 | 4.9% |
| Congenital malformations | 650 | 14,205 | 2.6% |
| Special purposes (COVID-19) | 3 | 4,087 | 0.7% |
| Perinatal conditions | 16 | 73 | 0.0% |

Three things jump out of this table.

**The biggest chapter is not a disease chapter.** "Factors influencing health status" touches
**72.7% of all admissions** — more than heart disease. These are the `Z` codes: *personal
history of nicotine dependence* (62,803 admissions), *long-term use of anticoagulants* (30,956),
*long-term use of insulin* (27,640). They record circumstances and treatments, not illnesses.
Add "Symptoms, signs" (chest pain, ascites — findings without a diagnosis) and "External causes"
(largely administrative, e.g. *patient room in hospital as the place of occurrence*), and
**roughly 28% of all diagnosis rows are not diseases at all.**

That is not a flaw to correct. Several of those codes are among the *most* useful things in the
data — "long-term use of anticoagulants" tells you something a diagnosis code cannot. But
counting rows as "number of diseases" quietly counts them, which is worth knowing.

**Code count and patient count are unrelated.** Injury and poisoning has 7,486 codes for
140,711 admissions; the endocrine chapter has 807 codes for 342,417. Injuries are described in
obsessive detail (which bone, which side, displaced or not, first visit or follow-up); metabolic
disease is described bluntly.

**Cancer is smaller than it feels.** 17.8% of admissions carry a neoplasm code, well behind
mental health at 43.7%.

---

## 4. Does a patient have one disease or many?

**Many.** Overwhelmingly, and this is the answer that matters most for the project.

| Diagnoses on one admission | Admissions | Share |
|---|---:|---:|
| exactly 1 | 13,955 | 2.6% |
| 2 or more | 531,542 | 97.4% |
| 5 or more | 452,718 | 83.0% |
| 10 or more | 292,770 | 53.7% |
| 15 or more | 163,065 | 29.9% |
| 20 or more | 81,456 | 14.9% |
| 30 or more | 16,768 | 3.1% |

Average **11.7**, median **10**, maximum **57**. One admission in seven carries twenty or more.

### The rare single-diagnosis stay — admission 20004705

```
PRINCIPAL   42731  Atrial fibrillation                 → Circulatory system
```

One code, one chapter. This is 2.6% of admissions.

### The typical stay — admission 20000024, ten diagnoses

```
PRINCIPAL   D50.0     Iron deficiency anaemia from chronic blood loss → Blood
seq 2       K52.1     Toxic gastroenteritis and colitis              → Digestive
seq 3       I10       Essential hypertension                         → Circulatory
seq 4       E53.8     Vitamin B deficiency                           → Endocrine
seq 5       M81.0     Age-related osteoporosis                       → Musculoskeletal
seq 6       R27.0     Ataxia (loss of coordination)                  → Symptoms
seq 7       Z91.81    History of falling                             → Health status
seq 8       H54.8     Legal blindness                                → Nervous/senses
seq 9       T47.4X5A  Adverse effect of laxatives                    → Injury/poisoning
seq 10      Y92.099   Place of occurrence: private residence         → External causes
```

**Ten diagnoses, ten different chapters.** And look at what the list actually describes: an
older person who is anaemic, unsteady, blind, osteoporotic, has a history of falls, and had a
bad reaction to a laxative at home. The principal diagnosis — anaemia — tells you almost nothing
about that. This single example is the strongest argument in this document for using more than
the principal code.

### The most complex stay in MIMIC — admission 27635276, 57 diagnoses

Peripheral arterial disease with ulceration *and* sepsis as joint principals, then end-stage
renal disease, bowel perforation, hypertensive kidney disease, diabetes with renal
complications, coronary disease, awaiting an organ transplant — 57 codes in all.

This one also exposes a data quirk worth knowing: it has **two `seq_num = 1` rows**, one ICD-9
and one ICD-10, because the stay was coded in both editions. Any code that assumes one principal
diagnosis per admission needs to handle that.

### How far one admission spreads across the body

| Distinct chapters on one admission | Admissions | Share |
|---|---:|---:|
| 1 | 21,403 | 3.9% |
| 2–4 | 162,933 | 29.9% |
| 5–7 | 189,917 | 34.8% |
| 8–10 | 126,589 | 23.2% |
| 11 or more | 44,655 | 8.2% |

**96.1% span two or more chapters. 66.2% span five or more.** The average admission touches
**6.1 chapters** and 10.8 distinct categories.

There is no such thing as "a cardiology patient" in this data.

### And across a patient's whole history

Codes belong to stays, so a patient with several admissions accumulates more:

| | Mean | Median | 90th percentile | Max |
|---|---:|---:|---:|---:|
| Admissions | 2.4 | 1 | 5 | 238 |
| Distinct codes | 20.2 | 13 | 45 | **477** |
| Distinct chapters | 7.0 | 6 | 13 | 19 |

**68% of patients touch five or more chapters** across their history. One patient carries 477
distinct diagnosis codes.

---

## 5. Which diseases travel together

Comorbidity is not random. Counting how often two chapters appear on the same admission:

| Admissions with both | Pair |
|---:|---|
| 284,651 | Circulatory + Health-status factors |
| 280,483 | Circulatory + Endocrine |
| 280,480 | Endocrine + Health-status factors |
| 201,862 | Health-status + Symptoms |
| 188,238 | Circulatory + Symptoms |

At the individual code level the pattern is even clearer — these are the pairs a care programme
would design around:

| Admissions | Pair |
|---:|---|
| 13,633 | High cholesterol + High blood pressure |
| 9,062 | High cholesterol + History of smoking |
| 8,487 | Type 2 diabetes + High blood pressure |
| 7,182 | High cholesterol + Coronary artery disease |
| 5,306 | Major depression + Anxiety disorder |
| 4,984 | Hypertensive kidney disease + Chronic kidney disease |
| 4,951 | Atrial fibrillation + Congestive heart failure |

The last two are the interesting ones clinically: **cardiorenal disease** and **AF with heart
failure** are recognised syndromes where the combination is more dangerous than either part.
A model that sees only "14 diagnoses" cannot know either pairing occurred.

---

## 6. The long tail, and why models ignore individual codes

| | |
|---|---:|
| Distinct codes | 28,562 |
| Used on exactly **one** admission | 6,160 (21.6%) |
| Used on **ten or fewer** | 16,157 (56.6%) |
| Used on **1% or more** of admissions | **207** |

And the concentration from the other end:

- the top **250** codes (0.9% of them) cover **50%** of all diagnosis rows
- the top **1,293** (4.5%) cover **80%**
- the top **2,719** (9.5%) cover **90%**

The most common codes are unglamorous:

| Admissions | % | Code | Meaning |
|---:|---:|---|---|
| 102,362 | 18.8% | `4019` | High blood pressure (ICD-9) |
| 84,568 | 15.5% | `E78.5` | High cholesterol |
| 83,773 | 15.4% | `I10` | High blood pressure (ICD-10) |
| 67,288 | 12.3% | `2724` | High cholesterol (ICD-9) |
| 62,803 | 11.5% | `Z87.891` | History of smoking |
| 56,155 | 10.3% | `K21.9` | Acid reflux |
| 43,076 | 7.9% | `25000` | Type 2 diabetes, uncomplicated |

Note rows 1 and 3, and rows 2 and 4: **the same condition, twice, split by ICD edition.**

**What this means practically.** If you turned each code into a model input — a column that is 1
when the patient has it and 0 otherwise — you would add 28,562 columns, of which 6,160 have a
single example. No model can learn anything from a column with one positive case; it will either
ignore it or memorise that one patient. This is why models built on MIMIC almost universally
**collapse diagnoses into groups or counts** rather than using codes directly.

Preventra does exactly that. Whether it collapses them *far enough down* is the subject of
[`docs/mimic/icd_feature_engineering.md`](icd_feature_engineering.md).

---

## 7. What Preventra does with all this today

Short answer: **much less than the data contains.**

### The model sees 19 diagnosis features, not 2

**Corrected.** An earlier version of this section said the model had only `n_diagnoses` and
`charlson_score`. In fact **19 of the 94 features are diagnosis-derived**: those two plus all
**17 Charlson condition flags** — `congestive_heart_failure`, `renal_disease`,
`metastatic_cancer` and the rest — each as its own column.

So the model can already tell a heart failure patient from a kidney patient from a cancer
patient. What it cannot see:

- **Any condition outside Charlson's 17.** Sepsis, atrial fibrillation, fractures and mental
  health conditions have no feature at all. A sepsis admission and a hip fracture with the same
  count and Charlson score genuinely do look identical to it.
- **The reason for admission.** `seq_num = 1` — the coder's judgement about why the patient was
  there — is discarded entirely, despite a 3× spread in readmission rate across its chapters.
- **The shape of the list**: how many body systems are involved, how much of the list is social
  rather than medical, whether anything went wrong during the stay.

Burden does move the score — measured across the 2,000-patient cohort loaded into the app:

| Charlson score | Patients | Mean risk at discharge |
|---|---:|---:|
| 0 | 788 | 10.7% |
| 1 | 399 | 13.6% |
| 2 | 281 | 17.6% |
| 3–4 | 289 | 21.4% |
| 5–7 | 193 | 27.3% |
| 8+ | 50 | 32.3% |

Correlation between Charlson score and discharge risk: **0.55**. So the model does know sicker
patients are riskier. It just cannot say *sick with what*.

### Storage keeps one code and three titles

`models/mimic_diagnoses.py` sets `N_SECONDARY = 3`, so each patient record holds:

| Field | Contents |
|---|---|
| `primary_diagnosis` | the principal diagnosis title |
| `primary_icd_code` | its code — **the only code kept** |
| `secondary_diagnoses` | up to 3 further titles, **no codes** |
| `n_diagnoses_coded` | the true total, typically 10 |

With a median of 10 diagnoses per admission, that means **roughly 6 are counted and discarded**,
and the 3 that survive have lost their codes — so they cannot be placed anywhere in the
hierarchy without guesswork.

### The screens show one diagnosis to clinicians, four to patients

> **Superseded.** This was the state when the audit ran. The patient detail page now renders the
> full diagnosis list (`components/shared/DiagnosisList.jsx`), and the patient portal has since
> been removed along with sign-in. The finding below is kept because it is what prompted that work.

| Screen | What it shows |
|---|---|
| Patient worklist | principal diagnosis + code |
| Weekly trend panel | principal diagnosis + code |
| **Patient portal (`MyHealth`)** | principal + code, **plus the secondaries** under "Also being managed" |
| Patient detail page | no diagnosis at all |

The API already returns the secondaries to every screen. **The patient's own portal is the only
place in the application where comorbidities are visible** — every clinical view shows the one
principal diagnosis and stops.

### Weekly monitoring ignores diagnosis completely

Searching `models/monitoring_rules.py` and the weekly simulator for any mention of diagnosis,
ICD or Charlson returns **nothing**. A 2 kg weekly weight gain adds **+7 points** whether the
patient has heart failure or has just had a knee replaced.

That is wrong in both directions. Two kilos in a week is *the* warning sign in heart failure and
close to meaningless after orthopaedic surgery; an oxygen saturation of 91% is alarming after a
fresh pulmonary embolism and near-normal in advanced COPD.

The diagnosis does reach the weekly screen — it is displayed, and passed to Gemini so the
written explanation mentions it. But it is **commentary on the score, never an input to it**.

---

## 8. Where this goes next

The gap between sections 4 and 7 is the opportunity: the data describes patients with ten
conditions across six body systems, and the application uses two numbers and one label.

[`docs/mimic/icd_feature_engineering.md`](icd_feature_engineering.md) sets out what can be built from
the codes — features for the discharge model, better explanations on the driver cards, and
disease-specific weekly monitoring rules — with what is possible today and what needs data that
is not yet on hand.

---

### Reproducing these numbers

Run [`notebooks/mimic/solved-mimic-icd-analysis.ipynb`](../notebooks/mimic/solved-mimic-icd-analysis.ipynb)
on Kaggle with a MIMIC-IV dataset attached. It finds the files itself, prints every table above,
and exports four CSVs including a full 28,583-row code index and a 14,222-row principal-diagnosis
index.
