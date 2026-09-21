# GLP-1 Adherence Platform — Extension Roadmap

> **Purpose.** This document lays out proposed directions for extending the GLP-1 Adherence & Cost Intelligence Platform beyond its current state. It is organised as sequenced tracks (not calendar phases) so leadership can decide scope, ordering, and resourcing separately.
>
> **Framing.** Today the platform is a rigorously-built end-to-end demo running on public data with a simulated adherence label. The proposals below evolve it into a production-grade payer-facing product: real longitudinal claims data replaces the synthetic target, the model layer grows from single-shot Gradient Boosting into a stack of predictive + causal + agentic components, and the dashboard becomes a **case-manager operating system** that closes the loop from prediction → intervention → measured outcome.
>
> **Reading order.** Start with [Where we are today](#where-we-are-today) and [North Star](#north-star) for the "why." Then jump to any of the tracks — they are written to be resource-planned independently, with explicit dependencies called out.

---

## Table of contents

1. [Where we are today](#where-we-are-today)
2. [North Star — the product we're building toward](#north-star--the-product-were-building-toward)
3. [Market context](#market-context)
4. [Proposed extension tracks (overview)](#proposed-extension-tracks-overview)
5. [Track A — Real data acquisition & schema evolution](#track-a--real-data-acquisition--schema-evolution)
6. [Track B — Advanced predictive modelling](#track-b--advanced-predictive-modelling)
7. [Track C — Causal inference & uplift modelling](#track-c--causal-inference--uplift-modelling)
8. [Track D — LLM & agentic features](#track-d--llm--agentic-features)
9. [Track E — Payer analytics expansion](#track-e--payer-analytics-expansion)
10. [Track F — Case-manager workflow OS](#track-f--case-manager-workflow-os)
11. [Track G — Platform, infra & MLOps](#track-g--platform-infra--mlops)
12. [Track H — Security, compliance & data governance](#track-h--security-compliance--data-governance)
13. [Success metrics](#success-metrics)
14. [Risks & open questions](#risks--open-questions)
15. [Appendix — mapping current limitations to tracks](#appendix--mapping-current-limitations-to-tracks)

---

## Where we are today

Snapshot as of the current commit (Phases 0–4 of the original implementation plan complete; Phase 5 validation/docs pending):

| Layer | Status | Notes |
|---|---|---|
| **Data pipeline** | ✅ NHANES + MEPS + FAERS + ClinicalTrials + CMS Part D fused across 3 layers into a 7,566 × 15 training table | Public-only. `is_adherent` is simulated from a transparent behavioral equation (see limitation #1 in [DATA_AND_MODEL_DOCUMENTATION.md](docs/DATA_AND_MODEL_DOCUMENTATION.md) §7). |
| **Predictive model** | ✅ Gradient Boosting v2 (AUC ~0.89), SHAP per-patient drivers, K-Means k=4 segmentation, Kaplan-Meier survival | Single 80/20 split. No cross-validation, no calibration, no uncertainty quantification. |
| **Consequence model** | ✅ 6-state annual Markov, rebound engine, Payer ROI synthesizer with break-even α + intervention headroom | 73 unit tests. Parameter registry with ~40 constants sourced to registry.csv. Two flagged as ASSUMED-NOT-SOURCED. |
| **Backend** | ✅ FastAPI + MongoDB Atlas, ~12 collections, ~10 routers | No auth, no multi-tenant, no rate limiting. Mongo-native since commit 51dba85. |
| **Frontend** | ✅ React 19 + Vite 7, 8 screens, role toggle (case_manager / insurer), payer-type override toggle on Cost of Inaction | No user accounts. Mock-data fallback on every hook. |
| **Docs** | ✅ ~10 markdown docs consolidated under `docs/`, evidence registry, phase-by-phase progress notes | Very high — arguably the strongest asset for a diligence or procurement conversation. |

**Assets that carry forward regardless of direction:**
1. The **parameter registry pattern** (layered CSVs + override folder) — this generalises beyond GLP-1 to any chronic-disease program.
2. The **consequence-model architecture** — Markov + rebound + ROI is re-usable across statins, DOACs, SGLT2s, biologics.
3. The **documentation discipline** — a due-diligence winner.
4. The **evidence-based framing** ("negative ROI is the honest answer, here's when it flips under Medicare 2028 and post-generic pricing") — this is a differentiated narrative most incumbents avoid.

**Load-bearing gaps to close before the platform can be sold or deployed in a real setting:**
1. Simulated target → **real claims data**.
2. Segments (k=4) are the *only* patient-level cohorting story → need **per-patient actionable predictions** with confidence intervals.
3. Prediction only → **prescriptive** (which patients + which intervention).
4. No feedback loop from real interventions → **no learning system**.
5. Single-tenant, no auth → **multi-tenant with RBAC + audit log**.

---

## North Star — the product we're building toward

**One-sentence product statement:** *A platform that helps payers and health-plan case managers keep patients on GLP-1 therapy long enough for the drug to pay for itself — through a triage-plus-intervention system that quantifies both who is at risk of dropping and which intervention will change that risk for that specific patient.*

**Three product pillars:**

1. **Predict** — Per-patient adherence risk at 30/90/180/365 days, molecule-specific, with calibrated uncertainty and per-patient SHAP drivers. Refreshed on a regular cadence from real claims data.
2. **Prescribe** — Uplift-model-based recommendations: for each at-risk patient, which of {financial-assist referral, side-effect coaching call, care-navigator outreach, molecule switch suggestion, mail-order pharmacy migration} has the largest expected reduction in dropout probability. Powered by causal inference on the payer's own historical intervention history.
3. **Prove** — Automated payer ROI attribution: real-time budget-impact tracking, cohort A/B analytics comparing intervened vs. matched-control patients, defensible real-world-evidence dossiers for pharma partnerships and CMS negotiations.

**Wrapping all three:**
- An **LLM copilot** for case managers ("draft an outreach script for this patient in their preferred language, referencing their top-3 SHAP drivers") and analysts ("show me clusters where financial pressure is the dominant driver *and* generic pricing would flip ROI positive within 3 years").
- **Agentic workflows** that don't just recommend but act — auto-drafting outreach messages, scheduling follow-ups, pre-filling PA forms — always with a human approval gate.

---

## Market context

Why this direction matters and why now:

- GLP-1 spend is the fastest-growing line item on almost every commercial payer's book. Payers project 4–6% of total spend on this class going forward.
- Discontinuation rates are the striking number: **~60–70% of commercially-insured GLP-1 starters are off therapy within 12 months** (Prime Therapeutics, Blue Health Intelligence, and others). Roughly two-thirds of every GLP-1 dollar today does not deliver its evidence-based benefit.
- Payers are actively procuring adherence interventions. PBMs (Express Scripts, CVS Caremark) launched GLP-1 management programs recently. Standalone startups (Sempre Health, Wellth, Waltz) are funded. **The category is validated but not saturated** — the differentiated angle is a payer-side analytics + intervention-attribution layer, not another patient-facing app.

**Where the current platform is already differentiated:**

The dashboard's "Cost of Inaction" panel tells the honest ROI story that most competitors dodge — "GLP-1 doesn't pay for itself under today's pricing on a pure cost-avoidance basis, but here's when it does under Medicare negotiation and post-generic pricing." That discipline (showing negative ROI honestly with the trajectory to positive) is a real trust signal in payer conversations.

**Adjacent categories to be aware of:**

| Category | Examples | Their angle | Our differentiation |
|---|---|---|---|
| Patient adherence tech (B2B2C) | Wellth, Sempre Health, AdhereTech | Nudge patients directly | We sit *upstream* of intervention: triage + attribution, integrating with any downstream vendor |
| RWE / claims analytics | Komodo Health, Prognos, HealthVerity, Truveta | Sell data + general analytics | We are opinionated about a specific clinical problem (adherence + ROI) |
| Payer-side utilization management | Cotiviti, Zelis, Milliman | Retrospective analytics | We are prospective + causal + intervention-attributing |
| PBM-embedded programs | Express Scripts GLP-1, CVS WeightWise | Bundled with the PBM | We are BYO-PBM, work across the payer + PBM boundary |
| DTC weight-loss | Ro, Noom Med, Sequence, Hims | Own the patient, sell the drug | We don't touch the patient — we help the payer manage the risk of paying for it |

---

## Proposed extension tracks (overview)

The tracks below can be resourced independently, though several have dependencies (called out per-track). Leadership can pick any subset in any order.

| Track | Focus | Key dependency |
|---|---|---|
| **A** | Real data acquisition & schema evolution | — (this is the enabler for B and C) |
| **B** | Advanced predictive modelling | Track A (needs real data for meaningful lift) |
| **C** | Causal inference & uplift modelling | Track A + real intervention-history data |
| **D** | LLM & agentic features | Independent; deeper value with Track A |
| **E** | Payer analytics expansion | Independent |
| **F** | Case-manager workflow OS | Independent |
| **G** | Platform, infra & MLOps | Independent; scales with data volume |
| **H** | Security, compliance & data governance | Prerequisite for any real-data work |

Tracks A, G, and H form the **infrastructure floor** — nothing production-grade ships without them. Tracks B, C, D, E, F are the **product/ML surface** — the value creation.

---

## Track A — Real data acquisition & schema evolution

The single most important workstream. Everything predictive and causal downstream depends on it.

### Sub-track A.1 — Data sourcing options

Sequenced in order of preference:

1. **Direct payer partnership (preferred).**
   - Ask: 12–24 months retrospective GLP-1 pharmacy + medical claims, de-identified to Safe Harbor.
   - What we give back: joint whitepaper, retrospective ROI analysis, pilot access.
   - Where to source: regional Blue Cross Blue Shield affiliates, progressive self-insured employers via Purchaser Business Group on Health / Employers Health, TPA-run books (Meritain, Luminare, HealthComp).
   - Realistic friction: legal (BAA) is the slow part, not tech.

2. **RWE data vendors** (parallel or fallback):
   - **Truveta** — health-system claims + EHR, subscription pricing.
   - **Optum Clinformatics** — de-identified administrative data, ~80M lives.
   - **IQVIA** — the incumbent, enterprise pricing.
   - **HealthVerity** — best for closed-claims + open-claims linkages.
   - **Merative MarketScan** — the academic-defensible reference dataset.

3. **Health system / IDN partnership** (Kaiser, Geisinger, Intermountain, Providence) — usually via research-collaboration IRB rather than commercial contract. Slower to revenue, faster to publishable evidence.

### Sub-track A.2 — Schema layer

- Build a canonical patient schema and per-source adapters, so onboarding a second data source doesn't rewrite the model layer.
- Adapters handle: field mapping, code-system translation (ICD-9 → ICD-10, NDC → generic name), PDC/MPR computation from raw pharmacy claims, gap-day definitions.
- Version the schema; every ingested dataset carries its schema version for reproducibility.

### Sub-track A.3 — Real target definition

- **PDC (Proportion of Days Covered) ≥ 0.8** over 180-day and 365-day windows is the standard. Support MPR and gap-based definitions too — different payers prefer different measures.
- **Time-to-dropout** = first gap of 30+ days (configurable). Removes the biggest simulated-data limitation (§7 #7).

### Sub-track A.4 — Feature enrichment from real data

Feature classes that real data unlocks and public data does not:
- Prior-drug history (was patient on metformin / SGLT2 / insulin before GLP-1 initiation?)
- Comorbidity flags from ICD codes (not just BMI/HbA1c-derived)
- Specialty of prescriber (endocrinology vs. primary care vs. weight-management clinic — huge adherence signal)
- Pharmacy channel (retail vs. mail-order vs. specialty)
- Plan formulary tier + prior authorization events
- Concomitant medications (side-effect-mitigating, DDI risks)

**Deliverable:** an "onboarded data source" is a validated ingestion pipeline + canonical schema mapping + refreshed model artifacts.

---

## Track B — Advanced predictive modelling

**Current state:** single Gradient Boosting classifier, StandardScaler on 7 continuous features, 80/20 split, no calibration.

### Sub-track B.1 — Modern tabular models (benchmark, don't blindly adopt)

- Benchmark on real data (Track A): **XGBoost, LightGBM, CatBoost** (near-certain wins on tabular healthcare data), then **FT-Transformer** and **TabNet** as stretch options.
- Expected outcome: GBM family wins on tabular. Transformer variants shine only with sequential/temporal features (fill sequences, event timelines) or free-text (clinical notes). Don't force deep learning where trees dominate.
- Ensemble top 2–3 with stacking if time-to-decision permits.

### Sub-track B.2 — Modern survival analysis

Replace Kaplan-Meier (population-level, non-personalized) with:
- **Random Survival Forest (RSF)** or **DeepSurv** — per-patient time-to-dropout with covariates.
- **DeepHit** — for competing risks (dropout vs. switch-molecule vs. death).
- **Cox proportional hazards** — as baseline / interpretability tool.
- Time-varying covariates matter: a patient's cost pressure at month 3 differs from month 1. Landmark analysis or joint models handle this.

**Payoff:** the Payer ROI layer's α(t) becomes a real time-varying quantity (resolves limitation #22).

### Sub-track B.3 — Calibrated uncertainty

- Isotonic regression on validation-set probabilities → well-calibrated risk scores.
- **Conformal prediction** for prediction intervals (`crepes` or `MAPIE`). Case-manager gets "risk 0.72 [0.61–0.83], drop within 90 days" instead of a naked point estimate.
- This is a genuine credibility differentiator in clinical contexts.

### Sub-track B.4 — Temporal validation

- Never random-split real longitudinal data. Split by **payer-quarter or index-date** — train on one period, validate on the next. Catches feature and prescriber-behavior drift.
- Report both random-split and temporal-split metrics. A gap between them is honest information about generalizability.

### Sub-track B.5 — Model validation upgrade (needed regardless of Track A)

Additions to the existing `Model/model.ipynb` — worth doing now, before real data:
- 5-fold stratified cross-validation with per-fold AUC / PR-AUC / Brier score / calibration curve.
- Bootstrap confidence intervals on all headline metrics.
- Replace threshold-tuning with a calibrated probability (isotonic or Platt).
- Move training out of the notebook into a proper script (`Model/train.py`) — notebooks stay for exploration.

### Sub-track B.6 — Scale-friendly SHAP

- `shap.TreeExplainer` on every prediction is fine at 7k patients, not fine at 500k+. Precompute SHAP for modal-cohort archetypes, use `shap.KernelExplainer` batches nightly, cache. Add a "why?" endpoint that returns cached top-drivers with a freshness timestamp.

---

## Track C — Causal inference & uplift modelling

The workstream that graduates the platform from analytics to **prescriptive action**. Requires real intervention-history data (Track A), so it starts after that.

### Sub-track C.1 — Retrospective ATE (Average Treatment Effect)

- Question: does an existing case-management intervention reduce dropout, and by how much?
- Method: propensity-score matching + doubly-robust estimation (AIPW). Sensitivity analysis with Rosenbaum bounds.
- Libraries: **EconML** (Microsoft) or **DoWhy** — both production-grade.
- Output: a defensible "current intervention program produces a Y% reduction in dropout at 180 days, 95% CI [X, Z]." Payers value this as a standalone deliverable.

### Sub-track C.2 — Heterogeneous Treatment Effects (uplift models)

Not every patient benefits equally from outreach. A pre-committed adherent patient gains nothing; a wavering patient gains a lot. **This is the entire economic case for triage.**

- Methods: **X-learner** (best for imbalanced treatment groups), **causal forest** (interpretable, handles many features), **DR-learner** (theoretically strongest).
- Ranking metrics: **Qini curve** and **AUUC (Area Under Uplift Curve)** — causal-inference equivalents of AUC.
- Product surface: the "Prescribe" pillar. Every at-risk patient gets a ranked list of interventions with predicted uplift + confidence band.

### Sub-track C.3 — Off-policy evaluation & contextual bandits

- Once we have deployed interventions and logged outcomes, evaluate new policies **without deploying them** using IPS / SNIPS / DR estimators.
- Natural next step: **contextual bandit** for online intervention selection. Safety-first — never explore into "no intervention" when observational data suggests intervention is warranted.

### Sub-track C.4 — Agent-based patient simulator

- Re-fit the current behavioral simulator (`final.py`) against real data as an agent-based simulator — every patient is an agent with realistic dropout hazards, cost pressures, and response to intervention.
- Enables pre-training of intervention-policy models offline before touching real patients (standard technique in healthcare RL — cf. Komorowski et al. 2018 sepsis).

---

## Track D — LLM & agentic features

Three progressively-ambitious surfaces. Each is independently valuable and can ship on its own dependency chain.

### Sub-track D.1 — RAG-powered natural-language querying

- **Case-manager on the Patient Detail page:** "summarize this patient's history for a colleague" → LLM composes a 3-sentence summary from structured records + intervention log.
- **Analyst on Executive Summary:** "which segments have the highest projected downstream cost under Medicare 2028 pricing" → LLM emits a structured query, chart renders.
- Architecture: text-to-Mongo agent with schema-in-context, guardrailed by allow-list of query patterns. Claude Sonnet 4.6 or Claude Haiku 4.5 handle this comfortably with tools + structured outputs.
- **Non-negotiable:** every LLM-generated action is logged and audit-traceable.

### Sub-track D.2 — LLM-generated case-manager artifacts

- Draft outreach scripts (multi-language, patient-preferred channel), pre-visit summary notes, PA form pre-fills, intervention follow-up templates.
- Anchored on the patient's actual data — SHAP drivers, adherence history, prior contact log — not generic templates.
- Human-in-the-loop always: case manager reviews, edits, sends. Never autonomous send.

### Sub-track D.3 — Agentic intervention workflow

The stretch surface. An agent that, given a case-manager directive ("outreach these 200 Cluster-1 patients this week"), plans and executes sub-tasks: draft messages, schedule sends, book follow-up calls, log outcomes, escalate exceptions.

- Built on Claude Agent SDK or a comparable framework. Sandboxed, auditable, human-approval gates on any patient-facing action.
- Business impact: the "reduces case-manager time per patient by X%" metric that anchors ROI conversations with payer procurement.

### Sub-track D.4 — Clinical-note ingestion (opportunistic)

- Where a data partner provides EHR access (rare in payer-only pilots, common with health-system partners), extract signals from free-text notes: side-effect complaints, patient-stated barriers, physician sentiment.
- Few-shot or fine-tuned classifier converts notes into structured features that feed the tabular model. Meaningful lift over claims-only data is well-documented in the literature.

### Sub-track D.5 — LLM-specific compliance stack (prerequisite for anything patient-adjacent)

- **Zero data retention** enterprise agreement with the LLM provider.
- **PHI minimization in prompts** — de-identify or tokenize patient identifiers before sending; detokenize on response before display.
- **BAA** with the LLM provider (Anthropic and OpenAI both offer HIPAA BAAs on enterprise/API tiers).
- **Prompt logging** for audit + evaluation (log structured references, never PHI values).
- **Output evaluation** — every LLM-generated clinical artifact reviewed by a human before delivery.

---

## Track E — Payer analytics expansion

Building on the existing 8 screens, in rough priority order (independent of each other; pick any subset).

1. **Real-time cohort tracker** — this-week vs. last-week vs. YTD adherence, PMPM cost trend, new-start volume, drop-off rate. The "Monday morning" operational dashboard.
2. **Intervention ROI attribution** — retrospective "our case-management program saved $X last quarter, computed as (intervened cohort dropout rate × avoided downstream cost) vs. matched-control cohort." Directly answers the CFO question.
3. **Formulary & contract simulator** — slider-driven scenario tool: change formulary tier / PA requirement / rebate contract terms → projected fill volume, adherence, and net-cost change. Natural extension of the existing payer-type override registry.
4. **Actuarial forecast** — 3/5-year budget-impact projection with confidence intervals, GLP-1-specific pricing scenarios (current, Medicare, generic), sensitivity to adherence-intervention program adoption.
5. **Prescriber network analytics** — which prescribers in the network have the best/worst adherence outcomes. Actionable at the plan level for prescriber education, at the PBM level for network design.
6. **Real-world evidence dossier generator** — auto-generated RWE reports for pharma partnerships (HEOR teams pay real money for defensible real-world adherence + effectiveness studies). Same real-data ingestion + consequence model, packaged as a repeatable analytical product.
7. **Cross-class extensibility** — same platform applied to statins / SGLT2 / DOACs / biologics. Reuses the parameter registry pattern — new disease = new evidence CSV, not new code. This is the strongest defensibility story for the platform architecture.

---

## Track F — Case-manager workflow OS

The current case-manager view is essentially a read-only version of the analyst view. Turning it into a **workflow tool** is what makes the platform sticky beyond analytics.

1. **Patient work queue** — filtered list of high-risk patients assigned to me, with SLA aging, last-contact date, next-recommended-action.
2. **Intervention playbook editor** — payer configures its own menu of interventions (financial-assist referral, coaching call, molecule-switch conversation, etc.). Each has eligibility criteria, expected cost, expected uplift (from Track C).
3. **Outreach templating & sending** — templates + LLM copilot for personalization. Send via integrated channels (SMS, email, in-portal) — vendor-agnostic, calling the payer's existing comms stack.
4. **Outcome logging** — one-click "contacted / responded / continued therapy / dropped." Feeds the uplift model (closes the loop).
5. **Supervisor / team lead views** — team performance, intervention effectiveness by team member, coaching-opportunity flags.
6. **Mobile-friendly view** — case managers are often on-the-go or at prescriber offices. Progressive-web-app at minimum.

---

## Track G — Platform, infra & MLOps

Current state is *demo-appropriate* infrastructure. To become production-ready:

### Sub-track G.1 — Backend & infra hardening

- **Containerization** — Dockerize backend + frontend. `docker-compose` for local dev.
- **CI/CD** — GitHub Actions: lint, type check, run pytest, run frontend build. Deploy to staging on merge; manual promote to prod.
- **Environments** — `dev / staging / prod`, isolated Mongo databases, feature-flagged rollouts.
- **Auth & multi-tenancy** — Auth0 / Clerk. Every request scoped by `org_id`. Row-level authorization on Mongo queries.
- **API gateway** — rate limiting, per-tenant quotas, request logging.
- **Async job queue** — Celery / Dramatiq / Prefect for retraining, batch prediction, RWE report generation. Not in the request path.
- **Database scaling** — Mongo Atlas M30+, or consider Postgres (with Timescale) for analytical tables if time-series dominates.
- **Observability** — Sentry (errors), Datadog / Grafana Cloud (metrics + logs), OpenTelemetry throughout.

### Sub-track G.2 — MLOps

- **Experiment tracking** — MLflow or W&B from the first real-data training run.
- **Model registry & versioning** — every deployed model tagged with data version, code commit, evaluation metrics. Rollback should be a single command.
- **Feature store** — Feast (open-source) or Tecton (managed) once >2 models share features. Defer until real; adds complexity.
- **Batch prediction pipeline** — nightly (or real-time-on-fill-event) scoring for all patients. Airflow / Prefect / Dagster orchestration.
- **Model monitoring in production** — data drift (Evidently, WhyLabs), prediction drift, per-cohort calibration. Alert on drift > threshold.
- **Feedback pipeline** — case-manager outcome logs → training data pipeline → retrain trigger → validation gate → deploy.

### Sub-track G.3 — Code organization

- Monorepo split: `packages/core` (registry, consequence models, shared types), `packages/api` (FastAPI), `packages/web` (React), `packages/ml` (training + evaluation pipelines).
- Type-safe end-to-end: OpenAPI/Pydantic → generated TypeScript client.
- Move `model.ipynb` into production training scripts.

---

## Track H — Security, compliance & data governance

Non-negotiable stack for handling real claims data. Everything here is a **prerequisite** for Tracks A / B / C / D at production scale.

### Sub-track H.1 — HIPAA baseline

- **BAA** with all data sources and infrastructure vendors (AWS/GCP, Mongo Atlas, Auth0, LLM provider).
- **Encryption** — TLS 1.2+ in transit, AES-256 at rest.
- **Access control** — SSO/SAML, role-based access, least-privilege by default.
- **Audit logging** — every read/write of PHI logged with user, timestamp, patient ID, action. Append-only. WORM storage after 90 days.
- **Backup & restore** — daily automated backups, tested restore quarterly.
- **Incident response plan** — written, tested, includes breach-notification procedure (60 days per HIPAA).
- **Business continuity / disaster recovery** plan.

### Sub-track H.2 — LLM-specific compliance (covered under Track D.5)

### Sub-track H.3 — Certifications to target

- **SOC 2 Type I** — table stakes for enterprise sales. Vanta / Drata + auditor engagement.
- **SOC 2 Type II** — requires 6-month observation window. Do before serious payer sales conversations.
- **HITRUST** — only if a specific customer requires it. Expensive but a real payer-sales unlock at scale.

### Sub-track H.4 — Data governance

- **Data use agreements (DUA)** with every source — retention limits, publication rights, allowed use cases.
- **IRB review** if publishing.
- **De-identification standard** — Safe Harbor by default, expert-determination where a critical feature (e.g. prescriber NPI) would otherwise be lost.
- **Data lineage** — every derived dataset traceable to source dataset + code version.

---

## Success metrics

Not tied to timeline; use as targets for whichever tracks are chosen.

### Product / ML metrics

- **Model performance on real data** — AUC ≥ 0.75 on temporal-split held-out data; calibration ECE ≤ 0.05; Brier ≤ 0.20. (Lower than the 0.89 on simulated target because real is harder — this is expected.)
- **Uplift model performance** — Qini ≥ 2× random baseline; top-decile uplift ≥ 3× population baseline.
- **Intervention attribution defensibility** — matched-cohort adherence delta of 3–8 percentage points, p<0.05, negative-control tests passed.
- **LLM copilot adoption** — ≥ 60% of case-manager sessions invoke the copilot; time-per-patient reduction ≥ 20%.

### Operational metrics

- **Case-manager retention on the tool** — daily active usage, sessions per week, patients touched per case manager per week.
- **Data freshness** — model scored ≤ 24h after new claim fills land.
- **SLA** — 99.5% uptime, p95 API latency < 500ms.
- **Model retraining cadence** — quarterly, or auto-triggered on drift.
- **Security incidents** — 0 breaches, 0 PHI exposures, all detected drift/vuln issues resolved within SLA.

---

## Risks & open questions

### Product risk

- **What if a data partner shows *no measurable uplift* from their current intervention program?** Real risk — many payer case-management programs don't beat control. Mitigation: frame the deliverable as *diagnostic* (which patients would benefit from what) not *validating* (proving the current program works). If the answer is "current program is untargeted, here's a better targeting model" — that's still a saleable story.
- **What if case managers reject the LLM copilot?** Change management is real. Mitigation: co-design with 2–3 case managers before shipping. Ship narrow (summarization only) before ambitious (autonomous drafting).

### Data risk

- **Partner data is smaller than expected.** A regional plan may only have 5k–15k GLP-1 patients. Not enough for some deep-learning approaches; plenty for GBM + causal work. Mitigation: architect for pooling across partners (federated / cross-payer benchmark) as soon as we have >1 partner.
- **De-identification breaks a critical feature.** If Safe Harbor de-id strips prescriber NPI, prescriber-level features die. Mitigation: negotiate for expert-determination de-id upfront, or accept the feature loss.

### ML risk

- **Uplift models are notoriously unstable.** Small data + heavy heterogeneity = high variance. Mitigation: use robust methods (X-learner over T-learner), cross-fitted causal forests, always report confidence intervals. Never present a point-estimate uplift without a band.
- **LLM hallucinations in a clinical context.** Non-negotiable: human-in-the-loop for anything reaching a patient. All LLM outputs traceable back to specific structured fields or documented sources.

### Business risk

- **Big-payer procurement is glacial.** 12–18 months from first conversation to purchase order is realistic. Mitigation: start with self-insured employers or regional Blues (much faster procurement).
- **The market gets crowded.** New GLP-1 adherence tools launch regularly. Mitigation: our moat is the closed-loop ML + causal-inference + real-data pipeline. Ship those before copycats.
- **Novo/Lilly launch their own dashboards.** They might. Mitigation: they can't be payer-neutral. A payer won't adopt a Lilly-branded ROI dashboard.

### Open questions requiring an early decision

- **Cloud choice.** AWS (broadest HIPAA-eligible service set) vs. GCP (better AI/ML tooling) vs. Azure (best for hospital IT integrations). Recommendation: AWS unless a partner mandates otherwise.
- **Frontend framework.** Stay React/Vite or migrate to Next.js for SSR + easier auth? Recommendation: Next.js migration is worth the effort — simpler auth, better SEO for marketing pages, easier server-side data fetching.
- **LLM provider.** Claude Sonnet 4.6 / Opus 4.7 for reasoning-heavy copilot; Haiku 4.5 for high-volume drafting. Multi-provider abstraction from day 1 so we can price-shop.
- **Feature-store adoption.** Feast (self-host, free) vs. Tecton (managed). Recommendation: defer until >2 models share features.

---

## Appendix — mapping current limitations to tracks

Cross-reference with the 23 documented limitations in [DATA_AND_MODEL_DOCUMENTATION.md](docs/DATA_AND_MODEL_DOCUMENTATION.md) §7 and §10.4. Every currently-documented limitation has at least one mapped resolution track:

| # | Limitation | Resolved by |
|---|---|---|
| 1 | Simulated `is_adherent` target | Track A (real fill data) |
| 2 | Random molecule assignment | Track A (real prescribing) |
| 3 | Coarse `system_refill_score` | Track A (prescriber-level real features) |
| 4 | Low-variance `bio_friction` | Track A (real AE data at patient level) |
| 5 | Dead `has_hypertension` | Track A (real ICD codes in claims) |
| 6 | MEPS demographic imputation of cost | Track A (patient-level real cost) |
| 7 | Synthetic `time_to_dropout` | Track A (real gap-day timestamps) |
| 8 | CMS 2023 vintage | Track A (ongoing refresh, or replaced by real payer data) |
| 9 | Upsampled class balance | Track B.5 (proper class weighting on real data) |
| 10 | No cross-validation | Track B.5 (add CV to validation) |
| 11 | European-trial rebound calibration | Track A + Track B (calibrate to real trajectories) |
| 12 | Linear-to-plateau rebound shape | Track B (config-flag exponential option) |
| 13 | HbA1c floor at 5.0 | Documented as-is; refine when real data enables |
| 14 | No patient-level random effects on rebound | Track B (per-patient variability layer) |
| 15 | Population-level Markov transitions | Track B (stratified transitions from registry) |
| 16 | 10-yr projections illustrative | Sensitivity analyses in Track B |
| 17 | Dialysis cost defaults FFS | Track E (already partly covered by override registry) |
| 18 | CV recurrence not modeled | Track B (extended Markov) |
| 19 | Rebate fraction ASSUMED | Track E (make configurable per data partner) |
| 20 | QALY not modeled | Track E (add QoL layer for HTA-grade dossiers) |
| 21 | Population-average RCT modifiers | Track C (heterogeneous treatment effects) |
| 22 | Constant adherence α across horizon | Track B (time-varying α(t) from real survival) |
| 23 | No on-therapy mortality reduction | Track B (SUSTAIN-6 / LEADER-derived HR into Markov) |

The technical debt burn-down is fully mapped — every gap has a home in the extension plan.

---

*Roadmap: technical extension proposals. Owner: project lead. Update on any major direction change.*
