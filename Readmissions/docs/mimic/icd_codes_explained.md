# Disease codes in MIMIC, explained

A plain-English guide to how illness is recorded in this data. No medical or statistical
background assumed.

Every number here was measured on the full MIMIC-IV dataset: 6,364,488 diagnosis records across
545,497 hospital stays and 223,291 patients.

---

## How this document is arranged

The data comes first, the explanation second — because the numbers are what people usually want,
and they make more sense once you have seen them.

| | |
|---|---|
| **1. The patients** | who they are, how many conditions each one has |
| **2. The codes** | how many exist, which are common, how they are grouped |
| **3–6. How coding works** | what an ICD code is, which editions are here, what a code does and does not tell you, and how to read one character by character |
| **7. Why it matters here** | what all of this means for the project |

---

## 1. Who these patients are, and how many conditions they carry

Start with the people, because every code in the rest of this document is attached to one of
them.

### The population, in one table

| | |
|---|---:|
| Patients | **223,291** in the full database |
| Patients in the model's training group | 148,669 |
| Hospital stays in the training group | 296,760 |
| Stays per patient | 2.00 on average |
| Patients who came in **once** and never returned | **61.1%** |
| Patients with **two or more** stays | 38.9% |
| Patients with **five or more** stays | 7.2% |
| Readmitted within 30 days | 19.6% of stays |

### How old are they?

Counting each patient once:

| Age | Patients | Share of patients | Average stays each |
|---|---:|---:|---:|
| 18–39 | 35,181 | 24% | 1.73 |
| 40–54 | 28,422 | 19% | 2.13 |
| 55–64 | 27,263 | 18% | 2.18 |
| 65–74 | 25,923 | 17% | 2.08 |
| 75–84 | 20,244 | 14% | 2.02 |
| 85 and over | 11,636 | 8% | 1.83 |

It is a broad adult population, not an elderly one — a quarter of patients are under 40. The
people who come back most often are in **middle age**, not at either extreme.

---

### How many diseases does one patient have?

This is the question the whole project turns on. **Almost nobody has one.**

| Diagnoses on a single hospital stay | Stays | Share | Readmitted within 30 days |
|---|---:|---:|---:|
| Exactly **1** | 3,627 | **1.2%** | 8.5% |
| 2 to 4 | 32,094 | 10.8% | 10.4% |
| 5 to 9 | 88,333 | 29.8% | 15.4% |
| 10 to 14 | 77,565 | 26.1% | 20.8% |
| 15 to 19 | 49,109 | 16.5% | 24.4% |
| **20 or more** | 45,705 | **15.4%** | **28.2%** |

Reading down the table: only about **one stay in a hundred** involves a single condition, while
**one in six** involves twenty or more. The average is 11.7 and the middle of the pack is 10.

The right-hand column is the reason this matters. Readmission climbs steadily with the number of
conditions — from **8.5%** for a single-diagnosis stay to **28.2%** for twenty or more. More than
three times the risk, from the same hospital, over the same 30 days.

### Long-term illness, counted properly

Counting *diagnoses* mixes together a chronic disease and a one-off symptom. The **Charlson
score** counts only 17 serious long-term conditions, and weights the more severe ones higher —
so it is a cleaner measure of how much lasting illness someone carries.

| Charlson score | Stays | Share | Readmitted within 30 days |
|---|---:|---:|---:|
| **0** — none of the 17 | 94,713 | 31.9% | 12.5% |
| 1 | 54,842 | 18.5% | 16.5% |
| 2 | 47,209 | 15.9% | 22.0% |
| 3 to 4 | 53,487 | 18.0% | 25.2% |
| 5 to 7 | 39,117 | 13.2% | 28.6% |
| **8 or more** | 7,392 | 2.5% | **32.3%** |

Nearly a third of stays carry none of the 17 long-term conditions. At the other end, the 2.5% who
score 8 or more are readmitted at **32.3%** — well over twice the rate of those carrying none.

### And they are scattered across the body

Conditions do not cluster tidily in one organ system. Counting how many of the twenty chapters a
single stay touches:

| Body systems involved in one stay | Stays | Share |
|---|---:|---:|
| Just 1 | 21,403 | 3.9% |
| 2 to 4 | 162,933 | 29.9% |
| 5 to 7 | 189,917 | **34.8%** |
| 8 to 10 | 126,589 | 23.2% |
| 11 or more | 44,655 | 8.2% |

**96.1% of stays involve two or more body systems**, and the average touches **6.1**. There is no
such thing as "a heart patient" or "a lung patient" in this data — there are people with several
things wrong at once. (The twenty body systems, and what is in each, are listed in section 2.)

Here is what that looks like for one real, entirely typical stay — ten diagnoses, one from each
of ten different chapters:

```
principal   Iron deficiency anaemia from chronic blood loss   → Blood
seq 2       Toxic gastroenteritis and colitis                 → Digestive
seq 3       High blood pressure                               → Circulatory
seq 4       Vitamin B deficiency                              → Endocrine
seq 5       Age-related osteoporosis                          → Musculoskeletal
seq 6       Ataxia (loss of coordination)                     → Symptoms
seq 7       History of falling                                → Health status
seq 8       Legal blindness                                   → Nervous/senses
seq 9       Adverse effect of laxatives                       → Injury/poisoning
seq 10      Place of occurrence: private residence            → External causes
```

Read only the principal diagnosis and you have "anaemia". Read the whole list and you have an
older person who is anaemic, unsteady, blind, osteoporotic, has a history of falls, and reacted
badly to a laxative at home. The second description is the patient. The first is a filing label.

---

### Diagnosis burden rises with age — readmission does not follow it

| Age at the stay | Stays | Average diagnoses | Average Charlson | Readmitted |
|---|---:|---:|---:|---:|
| 18–39 | 60,814 | 8.1 | 0.68 | 15.1% |
| 40–54 | 60,453 | 11.3 | 1.94 | **21.4%** |
| 55–64 | 59,377 | 13.0 | 2.50 | **21.5%** |
| 65–74 | 54,006 | 14.2 | 2.76 | 20.8% |
| 75–84 | 40,867 | 14.8 | 2.80 | 20.0% |
| 85 and over | 21,243 | 14.8 | 2.60 | 18.8% |

Diagnosis count almost doubles from the youngest band to the oldest. **Readmission does not.** It
peaks in middle age around 21.5% and then *falls* to 18.8% among the over-85s, who carry the
heaviest burden of anyone.

Treat that as something observed, not something explained. Several ordinary things could produce
it — patients who die after leaving hospital cannot be readmitted, and neither can those who move
into residential care. It is a reminder that a rate measured in one hospital's records is not the
same as a rate in the world.

### Men carry more, and return more often

| | Stays | Average diagnoses | Average Charlson | Readmitted |
|---|---:|---:|---:|---:|
| Female | 158,153 | 11.6 | 1.82 | 18.2% |
| Male | 138,607 | 12.9 | 2.44 | **21.4%** |

### Which long-term conditions are most common

Share of stays carrying each of the 17 Charlson conditions:

| Condition | Share of stays | | Condition | Share of stays |
|---|---:|---|---|---:|
| Chronic lung disease | 20.3% | | Metastatic cancer | 5.4% |
| Heart failure | 16.8% | | Rheumatic disease | 3.1% |
| Kidney disease | 16.7% | | Severe liver disease | 2.6% |
| Diabetes, uncomplicated | 16.6% | | Dementia | 2.4% |
| Cancer | 10.0% | | Paralysis | 1.9% |
| Prior heart attack | 9.1% | | Peptic ulcer | 1.5% |
| Diabetes with complications | 8.7% | | HIV/AIDS | 0.7% |
| Peripheral vascular disease | 8.1% | | | |
| Stroke | 7.7% | | | |
| Mild liver disease | 5.9% | | | |

### Conditions travel together

The pairs that most often appear on the same stay:

| Stays with both | Pair |
|---:|---|
| 13,633 | High cholesterol + high blood pressure |
| 9,062 | High cholesterol + history of smoking |
| 8,487 | Type 2 diabetes + high blood pressure |
| 5,306 | Major depression + anxiety |
| 4,984 | Hypertensive kidney disease + chronic kidney disease |
| 4,951 | Irregular heartbeat + heart failure |

The last two are not coincidences. Kidney and heart disease together, and an irregular heartbeat
alongside heart failure, are recognised combinations where each condition makes the other harder
to treat — the pair is more dangerous than either part on its own.

---

## 2. What is in the data: the codes themselves

Now the labels. Those 11.7 diagnoses on an average stay are recorded as short codes, and the
first question is simply how many different ones exist.

### The scale

| | |
|---|---:|
| Diagnosis records | 6,364,488 |
| Hospital stays | 545,497 |
| Patients | 223,291 |
| Distinct codes used | **28,562** |
| Distinct 3-character categories | 2,622 |
| Chapters present | 20 |

### The twenty chapters

Ordered by how many stays touch them:

| Chapter | Distinct codes | Stays touching it | Share |
|---|---:|---:|---:|
| Factors affecting health status | 1,626 | 396,656 | **72.7%** |
| Circulatory system | 1,513 | 353,086 | 64.7% |
| Endocrine, nutritional, metabolic | 807 | 342,417 | 62.8% |
| Symptoms and abnormal findings | 921 | 264,215 | 48.4% |
| Mental and behavioural | 948 | 238,565 | 43.7% |
| Digestive system | 1,105 | 230,998 | 42.3% |
| Nervous system and senses | 2,425 | 203,215 | 37.3% |
| Genitourinary system | 855 | 190,389 | 34.9% |
| Blood and immune system | 362 | 171,117 | 31.4% |
| Musculoskeletal system | 2,652 | 160,528 | 29.4% |
| Respiratory system | 535 | 159,122 | 29.2% |
| External causes | 1,779 | 150,534 | 27.6% |
| Injury and poisoning | 7,486 | 140,711 | 25.8% |
| Infectious diseases | 932 | 104,035 | 19.1% |
| Cancers | 1,808 | 97,090 | 17.8% |
| Skin | 784 | 59,486 | 10.9% |
| Pregnancy and childbirth | 1,376 | 26,549 | 4.9% |
| Congenital conditions | 650 | 14,205 | 2.6% |
| COVID-19 and special codes | 3 | 4,087 | 0.7% |
| Newborn conditions | 16 | 73 | 0.0% |

**Three things worth pausing on.**

**The largest chapter is not a disease chapter.** "Factors affecting health status" touches
**72.7% of all stays** — more than heart disease. These are the `Z` codes: *history of smoking*
(62,803 stays), *long-term use of anticoagulants* (30,956), *long-term use of insulin* (27,640).
They record circumstances and treatments, not illnesses. Add symptoms and external causes, and
**about 28% of all diagnosis records are not diseases at all.**

**Detail runs opposite to how common something is.** Hypertension gets 17 codes and 139,717 uses;
strokes get 319 codes and 27,324 uses. Injury has 7,486 codes while the endocrine chapter has 807
for twice as many stays. Common conditions are described bluntly; rare ones in obsessive detail.

**Cancer is smaller than it feels** — 17.8% of stays, well behind mental health at 43.7%.

### Most codes are almost never used

| | |
|---|---:|
| Codes used on exactly **one** stay | 6,160 (21.6%) |
| Codes used on **ten or fewer** stays | 16,157 (56.6%) |
| Codes used on **10 or more** of stays | **207** |

And from the other end: the top **250 codes — under 1% of them — cover half of every diagnosis
record ever written.** The top 1,293 cover 80%.

The most common codes are unglamorous:

| Stays | Share | Code | Meaning |
|---:|---:|---|---|
| 102,362 | 18.8% | `4019` | High blood pressure (ICD-9) |
| 84,568 | 15.5% | `E78.5` | High cholesterol |
| 83,773 | 15.4% | `I10` | High blood pressure (ICD-10) |
| 67,288 | 12.3% | `2724` | High cholesterol (ICD-9) |
| 62,803 | 11.5% | `Z87.891` | History of smoking |
| 56,155 | 10.3% | `K21.9` | Acid reflux |

Rows 1 and 3, and rows 2 and 4, are the same condition twice — split only by which edition was in
use.

---

## 3. So what is an ICD code?

The tables above have been full of things like `I50.23` and `4019`. Here is what they are.

When a patient leaves hospital, a trained medical coder reads the notes and assigns a short code
to every condition the stay documented. `I50.23` is one of those codes. It means *acute on
chronic systolic heart failure* — and it means that in every hospital in every country that uses
the system.

Think of it as a **catalogue number for illness**, in the way a library has a catalogue number
for every book. Two things follow from that:

- The code is a **label**, not a description. It identifies a condition from a fixed list; it
  does not describe this particular patient's version of it.
- The list is **agreed internationally**. ICD stands for the *International Classification of
  Diseases*, maintained by the World Health Organization. A hospital in Boston and a hospital in
  Karachi assign the same code to the same condition.

Codes exist mainly for administrative reasons — billing, statistics, public health reporting —
which explains some of their odder properties later on. They were not designed for building
predictive models, and it shows.

---

## 4. Which version does MIMIC use? Both.

There are two editions in circulation. The United States switched from the ninth to the tenth in
2015, and MIMIC spans that changeover, so **both are present**:

| Edition | Looks like | Diagnosis records | Share | Distinct codes used |
|---|---|---:|---:|---:|
| **ICD-9** | all digits — `42833`, `4019` | 2,908,741 | 45.7% | 9,143 |
| **ICD-10** | a letter, then digits — `I50.33`, `I10` | 3,455,747 | 54.3% | 19,440 |

### A note on that ratio, because two different numbers are both correct

You will also see the split quoted as **62 / 38** — in the project deck, for instance. That is not
a contradiction. The two numbers count different things:

| Measured over | ICD-9 | ICD-10 |
|---|---:|---:|
| **The whole database** — all 545,497 stays, 6.36 million diagnosis records | **45.7%** | **54.3%** |
| **The model's training group only** — 296,760 stays, 3.63 million records | **61.8%** | **38.2%** |

The training group is a filtered subset. Building it removed patients who died in hospital
(11,801), those discharged to hospice (17,118) and short observation stays (235,639) — nearly a
quarter of a million stays in that last category alone. Those exclusions did not fall evenly
across the two coding eras, which is why the surviving group leans more heavily ICD-9.

Neither figure is wrong. Just always check **which group** a percentage is describing before
comparing it with another.

This matters more than it sounds, for two reasons.

**The same condition appears twice.** High blood pressure is `4019` in older records and `I10` in
newer ones. They are the same illness recorded in two different alphabets. **1,332 diagnosis
names in MIMIC appear under both editions** — so anything that counts codes without accounting
for this will treat one condition as two.

**The same string can mean different things.** `E66.01` is *morbid obesity* in ICD-10. In ICD-9,
codes beginning with `E` are external causes of injury. A lookup that uses the code alone, without
also checking which edition it belongs to, will silently return the wrong answer. Everything in
this project therefore looks up codes by the **pair** — code *and* version — never the code
alone.

---

## 5. What a code tells you, and what it does not

Each record in MIMIC's diagnosis table carries four useful pieces of information:

| Field | The question it answers | Example |
|---|---|---|
| `icd_code` | **What** the condition is | `I50.23` |
| `icd_version` | **Which edition** — 9 or 10 | `10` |
| `seq_num` | **How central** it was to this stay | `1` = the main reason for admission |
| `hadm_id` | **Which hospital stay** it belongs to | codes attach to a stay, not to a person |

`seq_num` deserves attention. **Exactly one code per stay is numbered 1** — the *principal
diagnosis*, the condition chiefly responsible for the patient being there. Everything numbered
after it is a *secondary*: long-standing conditions the patient already had, complications that
developed during the stay, and anything else treated along the way. The numbering after 1 is the
coder's working order, not a ranking by severity.

### Three things a code deliberately withholds

- **How severe it is.** `I50.23` is the same code whether the patient walked into the clinic
  short of breath or arrived on a ventilator.
- **When it started.** A code on this stay might be a condition of twenty years' standing or
  something that appeared overnight. The coding does not distinguish them.
- **Whether it was treated.** A coded condition is one the stay *documented*. Some were actively
  managed; some were noted in passing because they exist.

---

## 6. Reading a code, character by character

Codes are not arbitrary strings. Each character to the right narrows the meaning, like a postal
address going from country to street to house number.

### The four levels

```
Chapter      Diseases of the circulatory system     I00–I99     20 of these exist
  Block      Other forms of heart disease           I30–I52     a named grouping
    Category Heart failure                          I50         the 3-character stem
      Code   Acute on chronic systolic HF           I50.23      what actually gets recorded
```

### An ICD-10 code, position by position

Take `I50.23`, which appears 5,685 times in MIMIC:

| Position | Value | What it says |
|---|---|---|
| 1 | `I` | **Chapter letter** — the circulatory system |
| 2–3 | `50` | **Category** — heart failure |
| 4 | `2` | *Systolic* heart failure, rather than diastolic |
| 5 | `3` | *Acute on chronic*, rather than acute or chronic alone |

Two more characters can follow, and in the injury chapter they usually do. The **sixth** is often
which side of the body, and the **seventh** is which visit this is.

Here are two real codes from this cohort that differ by a single character:

```
S72.001A   Fracture of unspecified part of neck of RIGHT femur, initial encounter
S72.002A   Fracture of unspecified part of neck of LEFT femur, initial encounter
             │ │  │ │
             │ │  │ └── 7th character: A = the first visit for this injury
             │ │  └──── 6th character: 1 = right, 2 = left
             │ └─────── neck of the femur
             └───────── S72 = fracture of the femur, in the injury chapter
```

And the same idea in the joint chapter:

```
M16.11   Unilateral primary osteoarthritis, RIGHT hip
M16.12   Unilateral primary osteoarthritis, LEFT hip
```

### ICD-9 works the same way, with digits instead

```
428      Heart failure
428.3    Diastolic heart failure
428.33   Acute on chronic diastolic heart failure
```

ICD-9 also has two special ranges that are not diseases at all:

- **`V` codes** — circumstances rather than illnesses. `V15.82` is *personal history of tobacco
  use*.
- **`E` codes** — external causes. What caused an injury, rather than what the injury is.

ICD-10 replaced these with the `Z` chapter (factors affecting health) and the `V`–`Y` chapters
(external causes).

### Why one illness needs so many codes

Heart failure occupies **23 separate ICD-10 codes** in MIMIC. Not because there are 23 diseases,
but because four different things are being recorded at once:

| Dimension | Options |
|---|---|
| Mechanism | systolic, diastolic, combined, right-sided, left-sided |
| Timing | acute, chronic, or acute-on-chronic |
| Cause | with or without hypertension, with or without kidney disease |
| Certainty | specified, or "unspecified" when the notes did not say |

The most common of the 23:

| Code | Times used | Meaning |
|---|---:|---|
| `I50.32` | 10,787 | Chronic diastolic heart failure |
| `I50.33` | 8,118 | Acute on chronic diastolic |
| `I50.22` | 7,507 | Chronic systolic |
| `I50.23` | 5,685 | Acute on chronic systolic |
| `I50.9` | 3,824 | Heart failure, unspecified |

To a clinician these are one condition. **To a computer they are 23 unrelated labels** — plus a
dozen more ICD-9 equivalents. That single fact shapes most of the modelling decisions in this
project.

---

## 7. What this means for the project

Three consequences follow directly from the numbers above.

**Individual codes cannot be model inputs.** With 28,562 codes and 6,160 of them used exactly
once, turning each into a column would produce a table that is 99.96% empty. The model therefore
uses diagnoses in grouped form: a count, a comorbidity score, and 17 named condition flags.

**The principal diagnosis is not the patient.** Since 96% of stays span several body systems,
showing only the admitting diagnosis on a screen describes a fraction of what is going on. This
is why the monitoring side of the application groups patients by their whole diagnosis list
rather than by the one code at the top of it.

**Two editions must always be handled together.** Every code lookup in this project joins on the
code *and* the version, and every count of "distinct conditions" is an overcount until the
editions are reconciled.

---

### Where to go deeper

| For | See |
|---|---|
| Full analysis, chapter by chapter | `docs/mimic_disease_landscape.md` |
| Every code in the loaded cohort | `docs/mimic_cohort_icd_index.md` and `.csv` |
| The analysis that produced these figures | `notebooks/solved-mimic-icd-analysis.ipynb` |
| Whether ICD features improve the model | `docs/icd_feature_engineering.md` |
