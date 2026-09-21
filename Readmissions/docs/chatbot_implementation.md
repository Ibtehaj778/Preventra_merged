# Dashboard Chatbot — Implementation

How the Preventra chatbot answers questions about the patient cohort, why it is
built this way, and what it deliberately refuses to do.

**Files**

| File | Lines | Role |
|---|---|---|
| `api/chatbot_gemini.py` | 558 | Tool declarations, and the Gemini calls |
| `api/chatbot_queries.py` | 881 | Every query that may run. The security boundary |
| `api/chatbot_service.py` | 211 | Routing, dispatch, history handling, error handling |
| `tests/units/test_chatbot_queries.py` | 615 | 75 tests, no network, `mongomock` only |
| `tests/units/test_chatbot_service.py` | 191 | 21 tests of routing, history and guardrail wording |

---

## 1. The shape of a turn

A question about the data goes through three stages. A question with no data
behind it takes a shorter route, and a question about neither is refused.

```
question + recent transcript
   │
   ├─ 1. SELECT   Gemini reads the question and returns one of three things:
   │              a tool + arguments, GENERAL, or NONE.
   │              It is given tool schemas, not data. It cannot see MongoDB.
   │
   ├── tool ──────┬─ 2. EXECUTE  The backend runs that tool against MongoDB
   │              │              itself. Arguments are validated here before
   │              │              any query is built.
   │              │
   │              └─ 3. PHRASE   Gemini turns the returned rows into bullets.
   │                             It is given only the rows that came back.
   │
   ├── GENERAL ───── Answered from knowledge, under a separate instruction
   │                 that forbids clinical advice and any figure about this
   │                 cohort. No database call happens on this path at all.
   │
   └── NONE ──────── The capability list. Nothing is sent anywhere.
```

Measured, locally:

| Stage | Time |
|---|---|
| Select the function | ~1.1 s |
| Execute the query | 0.4 – 2.1 s |
| Phrase the answer | ~1.1 s |
| **Total** | **~3 – 4 s** |

Two LLM round trips are the floor for a data question; a general question
costs one. Expect roughly a second more on Railway.

**The per-minute quota is the real constraint.** Two calls per turn against a
free-tier limit of 15 requests per minute means roughly seven questions a
minute before Gemini starts returning `RESOURCE_EXHAUSTED`. That is reported as
its own message — *"I'm being rate-limited right now"* — rather than the generic
failure, because the generic one sends people hunting for a bug that clears
itself in sixty seconds. Worth knowing before a live demo.

### Why two calls rather than one

A single call that both chose and answered would have to be handed the data up
front, which means either sending the whole cohort or guessing what is needed.
Splitting it means stage 2 fetches exactly what stage 3 needs, and stage 3 can
only talk about rows that actually came back from the database.

---

## 2. The rule that makes this safe

> **The model never writes query syntax.**

It names a tool and supplies arguments. Every argument is validated against an
allow-list before a query is constructed, and the pipeline is built by our code.

The obvious alternative — let the model emit MongoDB queries — would answer more
questions and would hand it `$where`, unbounded collection scans, access to
fields nobody vetted, and a route around every limit below. The question is not
whether the model is well-behaved; it is that a prompt injected through any
field it reads should not be able to reach the database.

---

## 3. The seventeen tools

Six answer a fixed question. Six answer a fixed question about a *group*. Two
are general-purpose: one for questions about a group, one for questions about
the individuals in it. Three answer questions about the clinicians rather than
the patients.

### Single patient, or a list

| Tool | Answers |
|---|---|
| `get_patient_drivers` | Why is patient X at risk? |
| `get_patient_details` | Show me patient X's record |
| `get_top_risk_patients` | Who are the highest-risk patients? |
| `list_patients_by_risk_threshold` | List patients scoring above N |
| `count_patients_by_risk_band` | How many are in each band? |
| `get_risk_trend_over_time` | How has risk moved across batches? |

### Cohort analytics

All four take the same filter — `band`, `min_score`, `max_score` — so
"patients above 80" means the same thing whichever is asked.

| Tool | Answers |
|---|---|
| `count_patients` | How many patients match this filter? |
| `get_common_conditions` | Most common conditions in this group |
| `get_common_diagnoses` | Most common principal diagnoses |
| `get_common_drivers` | Risk factors recurring across this group |
| `get_condition_overlap` | Who has several conditions, and which co-occur |
| `get_risk_change_since_discharge` | Who has moved materially since discharge |

### The clinician directory

Staff, not patients, so none of the small-cell suppression in §8 applies — "one
cardiologist is registered" discloses nothing that needs protecting.

| Tool | Answers |
|---|---|
| `list_registered_doctors` | Who is registered, and what do they cover? |
| `get_doctor_workload` | How many alerts are waiting, and how many are critical? |
| `get_alert_routing` | Who would an alert for this condition reach, and why? |

**No contact details.** Email is in the directory because routing needs a unique
key, not so the chatbot can read staff addresses aloud on request. Nothing here
returns one, and a test asserts it. The internal `doctor_id` is withheld too —
for a different reason: when it was returned the phrasing step led every bullet
with `DR-dr-amir-haddad-a2c294`, which answers nothing anyone asked.

`get_doctor_workload` counts **alerts, not patients**, and says so in the
result. A patient can raise one alert per monitoring week, so reporting "486
patients" would overstate a 486-alert inbox. `distinct_patients` is returned
alongside for when the difference matters.

`get_alert_routing` re-runs the real `route()` rather than describing the rules
from memory, so the answer reflects who is actually registered right now.

### Anything else

`run_cohort_query` (§4) for questions about a group, `list_patients` (§5) for
questions about the individuals in it.

---

## 4. `run_cohort_query`, the dynamic layer

Fixed tools mean a question nobody anticipated gets refused even when the data
is sitting right there. This one takes a *description of a query* instead.

```json
{
  "filters":  [{"field": "current_band", "op": "eq", "value": "High"}],
  "group_by": "anchor_age",
  "bucket_size": 10,
  "metric": "count",
  "top_n": 5
}
```

Compiled by the backend into a `$match` → optional `$unwind` → `$group` →
`$sort` → `$limit` pipeline. Nothing in the spec reaches MongoDB unchecked.

### The 16 queryable fields

Each field declares what may be done to it — grouped, aggregated, unwound —
so "average a diagnosis" fails as a type error rather than returning nonsense.

**Numeric** — filterable, groupable, aggregatable:
`current_score`, `discharge_score`, `trend_delta`, `anchor_age`, `los_days`,
`n_prior_adm`, `n_diagnoses_coded`, `weeks_tracked`

**Text** — filterable and groupable, never aggregated:
`current_band`, `risk_band`, `gender`, `group_label`, `primary_diagnosis`,
`monitoring_status`, `group_confidence`, and `clinical_groups` (an array,
`$unwind`-ed before grouping)

**Operators** `eq · ne · gt · gte · lt · lte · in`
**Metrics** `count · avg · min · max`

### What it refuses, and why each matters

| Attempt | Refused because |
|---|---|
| `field: "password"` | Not on the allow-list. Only these 16 fields exist to it |
| `op: "$where"` | Not in the operator map. Mongo syntax never passes through |
| `group_by: "_id"` | Not groupable. Internal fields are invisible |
| `group_by: "driver_1"` | Not listed — raw driver sentences are per-patient text |
| `gender > "M"` | Text compared with an ordering operator |
| `avg` of `primary_diagnosis` | Averaging text |
| `bucket_size` on `gender` | Bucketing a non-number |
| `bucket_size: -5` | Non-positive bucket |
| `metric: "exfiltrate"` | Not a metric |

---

## 5. `list_patients`, the row-level layer

`run_cohort_query` answers *what is true of this group*. It cannot answer *who
is in it, and what does each of them look like* — and no amount of aggregation
gets there. Before this tool existed, **"what is the primary diagnosis of the
top 5 patients?"** was refused: the only ranked list available returned a
patient id and a score and nothing else, and the chatbot could answer the
question one patient at a time but not as one question.

```
list_patients(
  filters = [{field, op, value}, ...]   same vocabulary as run_cohort_query
  sort_by = "current_score"             which field ranks the list
  order   = "desc" | "asc"
  fields  = ["primary_diagnosis", ...]  what to show for each patient
  limit   = 5
)
```

Anything in `FIELDS` can be filtered on, sorted by, or displayed. Three fields
are displayable but not queryable — `driver_1`, `driver_2`, `driver_3`, the
sentences explaining an individual's risk. They are explanations, not columns,
which is exactly why they must never be groupable: every group would hold one
person.

Two details that came out of testing it:

- **The ranking field is always shown**, even when the question did not ask for
  it. A "top 5 by risk" list that omits the risk is not a readable answer.
- **`count_matching` is reported alongside `returned`.** The list is capped; the
  number of patients matching the filter is not. Conflating the two is how the
  chatbot used to answer "84" as "50" (§11).

| Bound | Value | Why |
|---|---|---|
| `LIST_PATIENTS_DEFAULT` | 5 | What "the top patients" means when unqualified |
| `LIST_PATIENTS_MAX` | 25 | Beyond this a chat bubble is the wrong surface |
| `MAX_LIST_COLUMNS` | 6 | Readability, not safety — the answer stops scanning |

### Why no small-cell suppression here

§8 suppresses aggregates over fewer than five patients. This tool is exempt,
deliberately. Suppression exists to stop an *aggregate* quietly naming the
people inside it. A list that is openly a list is not that failure mode, and it
returns the same rows, identified the same way, that the worklist screen
already shows on load.

---

## 6. Conversation memory

The chat is no longer stateless. Each request carries the last few turns, and
the backend passes them to both Gemini calls as conversation content.

```
POST /api/chatbot/query
{ "question": "and their ages?",
  "history": [{"role": "user", "text": "..."}, {"role": "bot", "text": "..."}] }
```

What this buys, measured against the live API:

| Turn | Resolves to |
|---|---|
| *"What is the primary diagnosis of the top 5 patients?"* | `list_patients(fields=[primary_diagnosis], limit=5)` |
| *"What about the top 10?"* | same call, `limit=10` |
| *"and their ages?"* | same call, `anchor_age` added to `fields` |
| *"what is the most common condition among them?"* after *"how many score above 85?"* | `get_common_conditions(min_score=85)` |

Filters the user has not changed are carried forward. That instruction lives in
the selection prompt, not in code — the history is what the model reads, and
the tool it lands on is still checked against the same allow-list.

### The history is untrusted input

It is replayed by the browser, so every message in it is user-controlled —
including the ones labelled as the assistant speaking. Three things keep that
from mattering:

- It is passed as **conversation content, never as instruction**. The system
  prompt is a separate field and is the only thing with authority.
- Whatever a transcript claims, the selection step can still only return a tool
  declared in `chatbot_gemini.py`, and the backend still executes it.
- It is **trimmed at the service layer**, not the edge: last 8 messages, 1,500
  characters each. Every caller of `answer_question` gets those bounds, so a
  client that sends a megabyte of transcript cannot grow the prompt.

The phrasing step is told explicitly that earlier turns show what the user is
referring to and are *not* a source of facts — every number in an answer comes
from the function result in front of it.

---

## 7. Questions with no query behind them

Asking a clinical dashboard *"why do heart failure patients get readmitted so
often?"* is a reasonable thing to do, and answering it with a capability list is
a bad response to a good question. The selection step now returns one of three
things, not two:

| Verdict | Meaning | Route |
|---|---|---|
| a tool call | The database can answer it | §1 stages 2 and 3 |
| `GENERAL` | Any medical question, or how the dashboard works | Answered from knowledge |
| `NONE` | Nothing to do with health or this tool | The capability list |

An ambiguous reply is treated as `GENERAL`. A stray word should not become a
refusal, and the general path is the more constrained of the two — it cannot
reach the database at all.

### The scope is medicine, not just readmission

Drawn too tightly, this path refuses questions it should obviously answer.
*"What is acute myeloid leukemia?"* was refused on the first cut with *"I only
cover patient risk and readmission"* — a bad answer to a fair question, and
absurd given AML is a coded diagnosis sitting in the worklist.

So the scope is **any medical or health question**: conditions, diagnoses,
symptoms, labs, medications, procedures, terminology. The instruction says so
explicitly, names that example, and states that being asked to explain a disease
is never grounds to refuse. Where a condition bears on readmission risk it says
so briefly, without forcing the connection. `NONE` is reserved for sport,
politics, writing code — things with no relation to health at all.

### What bounds the general path

It runs under its own system instruction, separate from the phrasing one, and
the limits in it are stated as non-negotiable regardless of what the question or
the transcript says:

- **No clinical advice.** No diagnosis, treatment plan, drug or dose, or
  decision about an individual — real or hypothetical. It names the decision as
  the treating clinician's, then answers the general part of the question.
- **No figures about this cohort.** It has no data in front of it, so it must
  not state a count or proportion about these patients — *including one quoted
  earlier in the same conversation*. It points at the question to ask instead.
- **No borrowed certainty.** Say when something varies by population or is
  contested.

Asked *"patient 10004235 has a high potassium, what medication should I stop?"*
it opens by naming that as the clinician's decision, then covers which drug
classes affect potassium in general — useful, and not a prescription.

### The same limit belongs on the data path

That guardrail was written for the general path, and for a while it only lived
there. Asked *"should I discharge patient MIMIC-12892273 today?"*, the router
did the sensible thing and fetched the patient's record — and the phrasing step,
which had no such instruction, replied **"discharge today is not recommended."**

A correct risk score, turned into a clinical recommendation about a named
patient. The phrasing instruction now carries the limit too: report what the
data says, never convert it into a decision, and never write that something is
advisable, recommended, safe or unsafe for a patient. The same question now
opens by naming the decision as the clinician's and then gives the figures —
which is the useful half of the answer, and the only half this system is
entitled to give.

It is worth stating the general principle, because it will come up again when
someone adds a tool: **a guardrail that lives on one route is not a guardrail.**
Both Gemini calls can produce user-facing prose, so both need it.

---

## 8. Privacy and limits

### Small-cell suppression

Aggregates below **5 patients** are withheld:

> *Only 1 patient matches that filter — too few to summarise without
> effectively identifying them. Widen the filter.*

"The most common diagnosis among the 2 patients above 95%" names those two
patients' diagnoses. That is a disclosure dressed as a statistic, and it is
standard practice in health reporting to suppress it.

**It applies to breakdowns and aggregates, not to headcounts.** *"6 patients
are above 90"* says nothing about who they are; breaking those 6 down by sex
does. Suppressing plain counts would make the chatbot refuse exactly the small,
urgent groups a coordinator most needs to know about.

### Result caps

| Limit | Value | Guards against |
|---|---|---|
| `MIN_COHORT_FOR_AGGREGATE` | 5 | Re-identification through aggregation |
| `TOP_N_LIMIT` | 20 | A ranked grouping returning hundreds of rows |
| `MAX_GROUPS` | 25 | A pathological `bucket_size` on a distribution |
| `LIST_MAX_LIMIT` | 200 | Bulk extraction through the list tool |

The tighter ceiling wins: `TOP_N_LIMIT` bounds a ranked grouping, `MAX_GROUPS`
bounds a bucketed distribution, which ignores `top_n` — see below.

### Distributions are never truncated

A ranked grouping honours `top_n`. A **bucketed** one does not: cutting age
bands at five hides everyone over 60, and half a distribution misleads more
than no distribution. Buckets return in full up to `MAX_GROUPS`, ordered by
bucket rather than by size.

### What is not in the database to leak

No names, dates of birth, addresses or MRNs. `patient_id` is a de-identified
MIMIC subject id. Race and insurance exist in the training data and were
deliberately **not** carried into the serving collection — the cohort is too
imbalanced for the subgroup comparisons they would invite.

---

## 9. Answer formatting

The chat window renders plain text with preserved whitespace and **has no
markdown parser** (`whitespace-pre-wrap`, `Chatbot.jsx:68`). Markdown would
display as literal asterisks, so the answer instruction requires real bullet
characters:

```
Across the 660 high-risk patients:
• 292 patients (44.2%) — Gap before this admission
• 178 patients (27.0%) — Discharged home
```

One opening sentence stating what was counted, then one finding per line,
number first, at most six bullets — except distributions, which list in full.
No closing summary and no follow-up offers.

---

## 10. Failure handling

Every stage is wrapped. Stack traces never reach the user.

| Failure | Response |
|---|---|
| Question is out of scope entirely | The capability list, as bullets |
| Gemini quota exhausted (`429`) | *"I'm being rate-limited right now — wait about a minute."* |
| Gemini unreachable or times out | *"Sorry, I couldn't process that question."* |
| Arguments fail validation | Generic error; the real reason is logged |
| Patient id not found | *"No patient found with patient_id X."* |
| MongoDB unreachable | *"Something went wrong while retrieving that data."* |

A quota refusal is separated from a real fault on purpose. It is the failure
most likely to show up mid-demo, it clears itself, and calling it a generic
error sends someone looking for a bug that is not there.

Gemini is called with **one attempt and a 15-second timeout**. The SDK's default
exponential backoff turns a rate limit into a multi-minute hang; failing fast
and answering cleanly is better than a chat window that appears frozen.

---

## 11. Bugs this replaced

**Counting by listing.** *"How many patients have risk above 70?"* used to call
`list_patients_by_risk_threshold`, which caps at 50 rows by default, and the
answer counted what came back — so it replied **50** regardless of the truth.
The real figure is **84**. `count_patients` uses `count_documents` and has no
cap.

**A test suite that tested nothing.** Every fixture seeded `risk_score` and
`risk_band`, while every query reads `current_score` and `current_band`. All 12
filters matched nothing and the assertions had been passing over empty results.
Fixed, and the suite now covers the guardrails explicitly.

**Refusing questions it had the data for.** *"What is the primary diagnosis of
the top 5 patients?"*, *"why do heart failure patients bounce back?"* and *"what
about the top 10?"* were all refused — the first for want of a row-level tool,
the second because anything without a query behind it was out of scope, the
third because each turn started from nothing. §5, §7 and §6 respectively.

---

## 12. Against the text-to-SQL reference architecture

A five-layer architecture is widely cited for making LLM analytics reliable:
schema pruning and a semantic layer, static guardrails and AST validation,
execution with a self-correction loop, hybrid SQL/Python computation, and
grounded synthesis. It is sound, and it is worth being precise about which of
its problems we have.

**It hardens generated SQL. We never generate query syntax.** The model picks a
function name and arguments; the pipeline is built by our code from an
allow-list. That removes three of the five layers' central risks rather than
mitigating them — and adopting those layers anyway would mean building the
attack surface first in order to defend it.

| Layer | Position |
|---|---|
| Dynamic schema linking (vector store, top-*k* tables) | **Not applicable.** One collection, 16 queryable fields. The whole schema is smaller than the retrieval prompt would be |
| Metric catalog / semantic layer | **Already the core of the design.** `FIELDS`, the cohort functions, `MIN_COHORT_FOR_AGGREGATE`, `SHARP_CHANGE_POINTS`. The model maps intent to vetted definitions and never composes the arithmetic |
| Allowed categorical values in the prompt | **Was missing. Now implemented** — see below |
| Golden few-shot examples | Present, inline in `run_cohort_query`'s description |
| AST validation (`sqlglot`), block mutations | **Not applicable, and weaker than what we have.** There is no syntax to parse. `_validate_filters` is an allow-list, not a parse-and-reject, and no mutating function exists to call |
| Injected non-negotiable clauses (`LIMIT 100`) | **Already enforced** — `batch_date`, `TOP_N_LIMIT`, `MAX_GROUPS`, `LIST_PATIENTS_MAX` |
| Pre-flight `EXPLAIN` cost analysis | **Not implemented.** Every query is bounded to one batch of 4,000 documents by construction. Revisit if the chatbot is ever pointed at the 296,760-stay matrix |
| Read replica | **Not available** on this Atlas tier, and there is no write path to isolate |
| Transaction timeout | **Was missing. Now implemented** — `MAX_QUERY_MS` |
| Self-correction loop | **Was missing. Now implemented** — the largest real gap |
| Hybrid SQL → Python computation | **Already the shape.** Aggregation reduces, Python derives percentages. There is no fragile multi-CTE equivalent because the model writes no computation |
| Grounded synthesis | Instruction-level already. **Now also verified** — see below |

### The three gaps that were real

**A wrong categorical value returned a confident zero.** This was the worst
failure in the system, because it did not look like one:

```
monitoring_status = "declining"   →   "No patients match that filter."
```

The true answer was **750**. The data says `deteriorating`; nothing told the
model that, and nothing checked. Now the vocabulary of every low-cardinality
field is read from the data, injected into the selection prompt, and enforced in
`_validate_filters`. A near-miss is an error naming the valid values instead of
an empty result that reads like an answer. Asked *"how many patients are
declining?"* the chatbot now answers 750 first time.

`primary_diagnosis` is deliberately excluded — thousands of coded strings, no
vocabulary to state. The catalog is cached with a TTL and
`reset_vocabulary_cache()` exists for the ETL, because a batch introducing a new
condition would otherwise have its values rejected for ten minutes.

**The correcting error went only to the log.** The validator already produced
exactly what was needed:

> `'age' is not a queryable field. Available: anchor_age, clinical_groups, …`

and the user got *"Sorry, I couldn't process that question."* That message now
goes back to the model as a correction turn, capped at **one** retry — a second
failure after an explicit correction means the question does not map to
anything we have, and looping only costs latency. A `LookupError` is not
retried: a missing patient id is a fact about the data, not a fixable argument.

**Nothing bounded a query's runtime.** `MAX_QUERY_MS = 5000` on every
aggregation. The Gemini call around it gives up at fifteen seconds anyway; the
point is that an accidental collection scan is killed at the server rather than
holding a connection from the same small pool the dashboard uses.

### Grounded synthesis: detection, not prevention

`_report_ungrounded` checks that every figure quoted in an answer appears in the
payload it came from, and logs the ones that do not. It deliberately does not
block: the phrasing step is already instructed never to invent a number, and
rejecting answers on a regular expression would reject correct ones.

Percentages are skipped. `750 patients (100%)` is arithmetic on a count the
payload does carry, and an ungrouped count returns no percentage at all — the
first version flagged every one of them and buried the counts that matter. A
fabricated percentage is still caught, because the count behind it would be
wrong.

---

## 13. Extending it

**A new fixed question** — add the query to `chatbot_queries.py`, a
`FunctionDeclaration` to `chatbot_gemini.py`, and a branch in `_dispatch`.

**A new displayable-but-not-queryable field** — add it to `DRIVER_FIELDS`. It
becomes available to `list_patients` for display without becoming groupable,
which is the right treatment for anything unique per patient.

**A new queryable field** — add one entry to `FIELDS`. That is the whole change;
`run_cohort_query` picks it up for filtering, grouping and aggregation
automatically, and the validator starts enforcing its type.

Before adding a field, check it is safe to group by. Free text that is unique
per patient — a driver sentence, a care note — should not be groupable: every
group would contain one person and the answer would be a list of individuals.

### Deliberately not done

**Precomputed analytics.** Aggregations run in 0.4–1.5 s over 4,000 patients,
so materialising them buys little and introduces staleness: a cached "most
common condition" is wrong the moment a batch loads. Revisit at six figures.

---

## 14. Testing

```bash
.venv/bin/python -m pytest tests/units/test_chatbot_queries.py tests/units/test_chatbot_service.py -v
```

**136 tests, no network.** 104 cover the query layer with `mongomock` — no Gemini,
no Atlas — because that is where the security boundary is. The other 32 cover
the service layer with Gemini stubbed: which of the four routes a question
takes, what happens to a transcript that is oversized, malformed, or claims a
role it does not have, and whether the clinical limits are still present in both
prompts. That last group asserts on prompt text, which is unusual — but the two
guardrail failures so far were both wording, not logic, and wording is the part
nothing else catches.

What is not unit-tested is Gemini's judgement — whether it picks the right tool
for a given sentence. That is exercised end to end against the live API, and the
routing table in §6 is the record of that run, not an aspiration.
