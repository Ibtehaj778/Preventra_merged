# **Access Control & Hospital Dashboard Framework**

## **The short version**

The two tasks become one piece of work built on one rule: **every account belongs to one hospital and has exactly one role.** The one exception is the superadmin, which is us.

* **Superadmin** \= our team. It oversees everything across every hospital and can bypass every restriction.  
* **Hospital** \= who a user works for. Every hospital only ever sees its own patients, never another hospital's.  
* **Role** \= what a user does there: hospital admin, doctor, nurse or case manager. An admin assigns it; the user never picks it.  
* **Two filters decide what hospital users see.** First, only data from their own hospital. Second, doctors and nurses only see the patients assigned to them.  
* **Hospital admins see the big picture first.** Counts, lists and flags are always visible. Clinical detail (vitals, drugs, notes) opens on click, with a reason, and the access is logged.  
* **No new app.** GLP-1 and Readmissions each get a hospital dashboard. After signing in on the Portal, you pick an app and see that app's hospital view.

Talha's ticket supplies the plumbing: roles stored on the account, admin-managed, and surviving a refresh. Sir's task supplies the first real use for it, the hospital dashboards. Build the plumbing first, then the dashboards on top.

## **How the two tasks fit together**

Most of Talha's ticket carries over unchanged. Four points clash with the hospital idea. Each one is settled below so nobody builds the same thing twice.

| Topic | GLP-1's ticket  | Hospital task needs | Unified decision |
| ----- | ----- | ----- | ----- |
| Roles | admin, insurer, case\_manager | Doctors, nurses and the hospital itself | superadmin, hospital\_admin, doctor, nurse and case\_manager now. Insurer comes back later with its own organisation. |
| Who is "admin" | One admin who manages every user | Each hospital manages its own people | Split in two. **superadmin** (only our team) oversees and can change everything, everywhere. **hospital\_admin** manages only their own hospital's staff and patients. |
| New signups | Default to case\_manager | People must not join a hospital by typing its name | Accounts are mainly created by an admin (see Onboarding). If someone does sign up themselves, they get case\_manager with status **pending** and see no patients until an admin approves them. |
| "clinician" vs "case\_manager" | Pick one name | Doctors and nurses are now separate roles | Use `case_manager` in code everywhere: database, token, role context and nav config. The nav badge "Clinician" is renamed **"Care team"**, so labels match the roles behind them. |

Kept as-is from Talha's ticket: exactly one role per user, role returned on login and signup, role survives a refresh, the toggle is removed, Settings shows your role read-only, a User Management list for admins, backfilling old accounts, and the first-admin bootstrap (a script that creates the first superadmin).

## **What the code does today**

The pieces for hospitals half exist already, but nothing enforces them. From the Preventra\_merged repo:

| Area | Today | Gap |
| ----- | ----- | ----- |
| Hospital on the account | Every account and token already carries `org_id` (for example `city-hospital`). | It comes from whatever hospital name the user types at signup. Anyone can join any hospital. |
| Role on the account | Stored, but as free text the user types at signup (for example "Doctor"). | Not a fixed list and not admin-controlled. |
| GLP-1 role toggle | `RoleContext` holds insurer or case\_manager in page memory. | Anyone can switch, it resets on refresh and it gates nothing (Talha's point). |
| Patient data per hospital | Readmissions `/api/patients` and GLP-1 routes return every patient. | No endpoint filters by `org_id`, so every signed-in user sees every patient. |
| New patient data | Readmissions has CSV upload and manual entry. | Nothing records which hospital an uploaded or entered patient belongs to. |
| Doctors | Readmissions has a doctor registry (`doctor_id`, specialty, email), and patients have `assigned_doctor_id`. | Doctors are not linked to login accounts or to a hospital. |
| Nurses | Not modelled. | Needs a role and a patient assignment, like doctors. |
| Insurer per patient | Readmissions patients have an `insurance` field. GLP-1 has payer-level ROI tables. | GLP-1 patients have no insurer name. |
| Drugs and vitals | GLP-1 has drug, drug generation, BMI and HbA1c. Readmissions has clinical features. | No pharmacy name per patient, and no single "latest vitals" view. |

## **Organisations and roles**

There are five roles, and every account has exactly one. The role name in the code is the same everywhere: database, token, backend and both frontends.

flowchart TD  
  S\["superadmin\<br/\>(our team, sees everything)"\] \--\> H1\["Hospital A"\]  
  S \--\> H2\["Hospital B"\]  
  H1 \--\> HA\["hospital\_admin"\]  
  H1 \--\> D\["doctor"\]  
  H1 \--\> N\["nurse"\]  
  H1 \--\> CM\["case\_manager"\]  
  D \--\> PT\["their patients"\]  
  N \--\> PT

| Role | Belongs to | In plain words | Replaces |
| ----- | ----- | ----- | ----- |
| superadmin | Our team only | Oversees everything in every hospital and can bypass every restriction. Creates hospitals, hospital admins, staff and patients, and changes anyone's role. | Talha's `admin`, and the "first admin" problem |
| hospital\_admin | One hospital | Runs that hospital's dashboards. Adds and manages its doctors, nurses, case managers and patients, or sends a list to us to add. Sees counts and lists; opens clinical detail on click, with a reason. | Talha's `admin`, limited to one hospital |
| doctor | One hospital | Sees and acts on the patients assigned to them. | "Doctor" typed at signup today |
| nurse | One hospital | Sees and follows up on the patients assigned to them. **Caretakers count as nurses for now**, which may change later. | New |
| case\_manager | One hospital | Sees all the hospital's patients for risk and follow-up, but cannot manage users. | Talha's `case_manager`. Also the default for self-signups. |
| insurer *(later)* | An insurer organisation | Sees only its own members, across hospitals, from the cost and ROI side. | Talha's `insurer`, moved to a later phase |

Rules that apply to every role:

* A patient belongs to exactly one hospital.  
* A patient can have one doctor and several nurses.  
* **One role per account.** Someone who is both a doctor and an admin uses two accounts, one per role.  
* **Superadmin accounts are only for our team.** No hospital admin can create one or promote anyone to it.

## **Who can see what**

The backend enforces every row of this table, not the frontend. Hiding a button is a courtesy. Refusing the API call is the control. Everything except the superadmin column is limited to the user's own hospital.

| What | superadmin | hospital\_admin | doctor | nurse | case\_manager |
| ----- | ----- | ----- | ----- | ----- | ----- |
| Patient list (name/ID, doctor, nurses, insurer, risk level) | All hospitals | Yes | Own patients only | Own patients only | Yes |
| Counts, trends and flags | All hospitals | Yes | Own patients | Own patients | Yes |
| Vitals, drugs, pharmacy and notes | All hospitals, no prompt | On click, with a reason (logged) | Own patients | Own patients | Yes |
| Risk drivers (why a patient is high-risk) | All hospitals, no prompt | On click, with a reason (logged) | Own patients | Own patients | Yes |
| Staff list with each person's patients | All hospitals | Yes | No | No | Yes |
| Add doctors, nurses, case managers | Any hospital | Own hospital | No | No | No |
| Add patients (one by one or CSV) | Any hospital | Own hospital | No | No | No |
| Assign patients to doctors and nurses | Any hospital | Yes | No | No | Yes |
| Add notes and care actions | Yes | No | Yes | Yes | Yes |
| Hospital cost and ROI screens (GLP-1) | All hospitals | Own hospital | No | No | No |
| User Management (approve, change roles) | Everyone | Own hospital | No | No | No |
| Create hospitals and hospital admins | Yes | No | No | No | No |
| View the access log | All hospitals | Own hospital | No | No | No |

"Own patients" means patients whose assigned doctor or nurse is that user.

### **How hospital admins open clinical detail**

A hospital admin needs to know exactly what is going on, but rarely needs every patient's lab values. So their access works in two layers:

1. **Overview layer (always on).** Counts, lists, risk levels, staff workload, insurer mix and alerts. No vitals, drugs or notes appear in lists or tables.  
2. **Detail layer (on click).** On a patient row, "View clinical details" opens a short prompt asking why, with options such as *care coordination*, *complaint / incident review*, *audit* and *billing query*. After they choose, the vitals, drugs, pharmacy, notes and risk drivers open for that patient.

The rules behind it:

* Each detail view is written to the **access log** with who opened it, which patient, when and the reason given.  
* The access lasts for that patient for the rest of the session, so admins aren't asked again on every click.  
* The backend refuses detail calls from a hospital\_admin that don't carry a reason. The prompt is not only in the frontend.  
* The hospital admin can review their hospital's access log, so misuse is visible.

### **What "bypass everything" means for the superadmin**

The superadmin skips every filter and prompt: any hospital, any patient, any action, with no reason asked. We recommend one safeguard: **superadmin actions are still written to the access log.** It costs nothing day to day. If a hospital ever asks who looked at their patient's data, we can answer.

## **Onboarding hospitals, staff and patients**

Hospitals don't sign themselves up. We create them, and each hospital then fills in its people either directly or through us.

flowchart TD  
  A\["Hospital agrees to join"\] \--\> B\["Superadmin creates hospital\<br/\>+ its hospital\_admin"\]  
  B \--\> C{"Who adds staff\<br/\>and patients?"}  
  C \--\>|"Hospital does it"| D\["hospital\_admin adds them\<br/\>one by one or by CSV"\]  
  C \--\>|"Hospital sends a list"| E\["Superadmin imports\<br/\>the list for them"\]  
  D \--\> F\["Staff log in and see\<br/\>only this hospital"\]  
  E \--\> F

1. **We create the hospital.** The superadmin enters the hospital's name and creates its first hospital\_admin account.  
2. **Staff get added.** The hospital\_admin adds doctors, nurses and case managers in User Management. Alternatively, the hospital sends us a list (name, email, role) and the superadmin imports it. Each new person gets a login invite or a temporary password.  
3. **Patients get added.** The hospital\_admin uploads a patient CSV or enters patients manually, or sends the file to us to upload. Every patient added this way is stamped with that hospital automatically. Nobody types a hospital name.  
4. **Patients get assigned.** The hospital\_admin or a case manager assigns each patient a doctor and nurses.

Self-signup on the Portal can stay, but it only creates a **pending** case\_manager with no patient access until an admin approves it and attaches it to a hospital.

## **The hospital dashboards**

There is no new app. GLP-1 and Readmissions each get a hospital view in their own app, built from the same four page types. You sign in on the Portal, pick an app and land on that app's hospital view. The superadmin sees the same pages with a hospital picker at the top, including an "All hospitals" option.

| Page | Question it answers | In GLP-1 | In Readmissions |
| ----- | ----- | ----- | ----- |
| Overview | How is my hospital doing? | Patients on GLP-1 therapy, adherent vs non-adherent, dropout risk, drug spend | Admissions, high readmission risk count, open alerts, patients with no doctor assigned |
| Patients | Who are my patients? | One row per patient: doctor, nurses, insurer, drug, pharmacy, adherence risk | One row per patient: doctor, nurses, insurer, readmission risk, last discharge |
| Patient detail *(on click; hospital admins give a reason)* | Everything about one patient | BMI and HbA1c over time, drug and refill history, pharmacy, risk drivers | Vitals, diagnoses, discharge details, risk drivers, care actions and notes |
| Staff | Who looks after whom? | Doctors and nurses with patient counts and non-adherent counts | Doctors and nurses with patient counts, high-risk counts and open alerts |

GLP-1 also keeps its cost pages (Budget Simulator, Cost of Inaction), which the hospital admin sees for their own hospital.

**User Management is built once.** Accounts are shared by both apps, so the API lives once in the shared auth service. Both apps' Settings pages show the same User Management section with email, role, hospital, signup date and status. It has add, approve, change-role and CSV import actions. Hospital admins see only their own hospital there; the superadmin sees every hospital and can also create hospitals.

Doctors and nurses see the same Patients and Patient detail pages, filtered to their own patients and without the reason prompt. The Overview, Staff and User Management pages are hidden for them, and their API calls are refused.

## **Scope: keep, add, cut**

Sir's list is the right core. Two items shrink to data fields, and a few small things are added.

| Item | Decision | Why |
| ----- | ----- | ----- |
| Patients | Keep | The centre of both dashboards |
| Insurers | Keep, as a patient field | The hospital needs to see who pays for each patient. Insurer logins wait for a later phase. |
| Vitals and drugs | Keep, in the on-click detail layer for hospital admins | Already in the data (BMI, HbA1c, drug, drug generation) |
| Doctors and their patients | Keep | The doctor registry and `assigned_doctor_id` already exist |
| Nurses/caretakers and their patients | Keep, with caretakers treated as nurses | Decided for now; may change later |
| Pharmacy | Cut to a field | Store the pharmacy name and refill dates on the patient. No pharmacy logins or pharmacy pages. |
| Superadmin role | Add | We oversee and can fix anything, across all hospitals |
| Hospital admin role | Add | Each hospital manages its own staff and patients |
| Staff and patient CSV import | Add | Lets hospitals, or we on their behalf, onboard a whole list at once |
| Access log \+ reason prompt | Add (small) | Records who opened which patient's details and why. Health data normally needs this. |
| Departments, multi-hospital staff, several roles per person | Cut | One role per account; a doctor-admin uses two accounts |

## **Demo data split**

The current datasets don't belong to any hospital, so for testing we split them across three made-up hospitals:

| Test hospital | GLP-1 patients | Readmissions patients | Staff |
| ----- | ----- | ----- | ----- |
| Demo Hospital A | Every third patient, starting with the 1st | Every third patient, starting with the 1st | 1 hospital\_admin, 2–3 doctors, 2 nurses, 1 case\_manager |
| Demo Hospital B | Every third patient, starting with the 2nd | Every third patient, starting with the 2nd | Same |
| Demo Hospital C | Every third patient, starting with the 3rd | Every third patient, starting with the 3rd | Same |

* The split goes by patient ID, so it's repeatable: re-running the seed script gives the same result.  
* Existing doctors in the Readmissions registry are shared out across the three hospitals, and their current patient assignments are kept where the hospital matches.  
* The test that matters: sign in as Hospital A's admin, doctor and nurse in turn, and confirm that no Hospital B or C patient ever appears, whether through a page, the API or the chatbot.

Real hospitals never use this split. Their data comes in through the onboarding steps above.

## **Build order**

There are six steps, and each one is shippable on its own. Steps 1 and 2 are Talha's ticket, widened for hospitals. Everything after them depends on those two.

1. **Roles become real** (Talha's ticket, after FT-4 merges)  
   * Fixed role list: superadmin, hospital\_admin, doctor, nurse, case\_manager  
   * A script creates the first superadmin account for our team  
   * Self-signups get case\_manager with status `pending`. Existing accounts are backfilled to case\_manager with status `active`.  
   * Role, status and hospital come back on login, signup and `/auth/me`, and in the token  
   * Remove the GLP-1 role toggle from the sidebar and Settings. Settings shows your role read-only.  
   * Use `case_manager` in code everywhere in place of `clinician`, and rename the "Clinician" badge to "Care team"  
2. **Hospitals become real**  
   * A `hospitals` collection with id and name. Only the superadmin can create a hospital and its first hospital\_admin.  
   * User Management API in the shared auth service: add a user, approve, change role, and import a CSV of staff  
   * The User Management section in both apps' Settings, scoped to one hospital for hospital\_admin and to all hospitals for superadmin  
3. **Data belongs to a hospital**  
   * Add `hospital_id` to patients, doctors and nurses  
   * Patient CSV upload and manual entry stamp the uploader's hospital on every new patient; the superadmin picks the hospital when uploading for one  
   * Seed script: the three demo hospitals and the patient split above  
   * Link each doctor record to a login account; add patient-to-nurse assignment next to `assigned_doctor_id`  
   * Every patient API filters by the hospital in the token. The superadmin skips the filter. A pending account gets nothing.  
4. **Hospital dashboards in GLP-1 and Readmissions**: Overview, Patients, Patient detail and Staff in each app, with the reason prompt and access log for hospital admins and a hospital picker for the superadmin  
5. **Own-patients rule and role gating** (FT-6)  
   * Doctors and nurses get only their assigned patients, from every API  
   * Nav items for other roles are hidden, not dimmed  
6. **Later**  
   * Chatbot reads the role and hospital from the token, not from the request (FT-7)  
   * Insurer organisations and the insurer role  
   * Deactivate and delete users

flowchart LR  
  A\["FT-4 user record"\] \--\> B\["1 Roles real"\]  
  B \--\> C\["2 Hospitals real"\]  
  C \--\> D\["3 Data per hospital"\]  
  D \--\> E\["4 Dashboards in both apps"\]  
  D \--\> F\["5 FT-6 own patients"\]  
  F \--\> G\["6 FT-7, insurers"\]

Steps 4 and 5 can run in parallel once step 3 lands.

## **Decisions and open questions**

**Decided (25 Sep):**

* \[x\] Hospital dashboards live inside GLP-1 and Readmissions, not as a third app  
* \[x\] A superadmin role for our team only, which oversees everything and can bypass every restriction  
* \[x\] hospital\_admin manages its own hospital's staff and patients, or sends lists to the superadmin to add  
* \[x\] We create hospitals. Staff and patients come in manually, by CSV, or by a list sent to us.  
* \[x\] Hospital admins get counts and lists by default, with clinical detail on click (reason prompt \+ access log)  
* \[x\] Caretakers are treated as nurses for now  
* \[x\] Self-signups wait as pending until approved  
* \[x\] `case_manager` in code everywhere; the badge reads "Care team"  
* \[x\] One role per account; a doctor who is also an admin uses two accounts  
* \[x\] Each hospital sees only its own patients; demo data is split across three test hospitals

**Still open:**

* \[ \] **Team:** Confirm the role list and the superadmin / hospital\_admin split replace the `admin` in his ticket  
* \[ \] **Team:** Is the reason list right (care coordination, complaint / incident review, audit, billing query)?  
* \[ \] **Team:** Do superadmin actions get logged? (Recommended: yes.)  
* \[ \] **Team:** New staff logins: email invite link, or a temporary password the admin hands over?

