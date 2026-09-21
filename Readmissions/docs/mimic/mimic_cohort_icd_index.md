# ICD index of the loaded MIMIC cohort

Every distinct **principal** diagnosis code across the 2,000 patients in `patient_worklist`, grouped by ICD chapter and ordered by how many patients carry it.

## What this is and is not

- **Principal diagnoses only.** MIMIC codes a median of 11 diagnoses per admission, but the loader stores the principal one plus three secondaries (`N_SECONDARY = 3` in `models/mimic_diagnoses.py`). The remaining diagnoses exist in MIMIC's `diagnoses_icd` table but were never loaded here.
- **The three stored secondaries have titles but no codes**, so they cannot be placed in a chapter. They are listed at the end by title.
- **The cohort is 2,000 patients**, not the 296,760-admission training set.
- **ICD version is inferred from the code shape**, because the worklist stores a bare code with no version field. Numeric codes are read as ICD-9, letter-led codes as ICD-10, with `E8xx`/`E9xx` and `Vnn` treated as ICD-9. The ICD-9/ICD-10 boundary is genuinely ambiguous for a handful of `V` codes.

**1,062 distinct principal codes** (566 ICD-9, 495 ICD-10) across 20 chapters.

## Summary by chapter

| Chapter | Distinct codes | Patients |
|---|---:|---:|
| Diseases of the circulatory system | 151 | 404 |
| Injury and poisoning | 194 | 281 |
| Diseases of the digestive system | 145 | 256 |
| Pregnancy, childbirth and the puerperium | 86 | 185 |
| Neoplasms | 99 | 148 |
| Diseases of the musculoskeletal system and connective tissue | 55 | 103 |
| Mental, behavioural and neurodevelopmental disorders | 52 | 91 |
| Infectious and parasitic diseases | 35 | 89 |
| Diseases of the genitourinary system | 37 | 81 |
| Diseases of the respiratory system | 41 | 77 |
| Endocrine, nutritional and metabolic diseases | 36 | 71 |
| Diseases of the nervous system and sense organs | 45 | 63 |
| Symptoms, signs and abnormal clinical findings | 34 | 61 |
| Diseases of the skin and subcutaneous tissue | 17 | 30 |
| Factors influencing health status and contact with health services | 7 | 15 |
| Diseases of the blood and immune mechanism | 11 | 14 |
| Congenital malformations and chromosomal abnormalities | 9 | 11 |
| Codes for special purposes, including COVID-19 | 1 | 11 |
| External causes of morbidity | 6 | 6 |
| Not coded | 1 | 3 |

## Full listing

### Diseases of the circulatory system  
*151 codes, 404 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `41401` | ICD-9 | Coronary atherosclerosis of native coronary artery | 28 |
| `41071` | ICD-9 | Subendocardial infarction, initial episode of care | 20 |
| `4241` | ICD-9 | Aortic valve disorders | 19 |
| `I214` | ICD-10 | Non-ST elevation (NSTEMI) myocardial infarction | 17 |
| `I671` | ICD-10 | Cerebral aneurysm, nonruptured | 14 |
| `42833` | ICD-9 | Acute on chronic diastolic heart failure | 11 |
| `43411` | ICD-9 | Cerebral embolism with cerebral infarction | 11 |
| `41519` | ICD-9 | Other pulmonary embolism and infarction | 9 |
| `I2510` | ICD-10 | Atherosclerotic heart disease of native coronary artery without angina pectoris | 9 |
| `43491` | ICD-9 | Cerebral artery occlusion, unspecified with cerebral infarction | 8 |
| `42731` | ICD-9 | Atrial fibrillation | 7 |
| `42823` | ICD-9 | Acute on chronic systolic heart failure | 7 |
| `I130` | ICD-10 | Hypertensive heart and chronic kidney disease with heart failure and stage 1 through stage 4 chronic kidney disease, or unspecified chronic kidney disease | 7 |
| `43310` | ICD-9 | Occlusion and stenosis of carotid artery without mention of cerebral infarction | 6 |
| `I25110` | ICD-10 | Atherosclerotic heart disease of native coronary artery with unstable angina pectoris | 6 |
| `I350` | ICD-10 | Nonrheumatic aortic (valve) stenosis | 6 |
| `42732` | ICD-9 | Atrial flutter | 5 |
| `430` | ICD-9 | Subarachnoid hemorrhage | 5 |
| `431` | ICD-9 | Intracerebral hemorrhage | 5 |
| `I110` | ICD-10 | Hypertensive heart disease with heart failure | 5 |
| `I25119` | ICD-10 | Atherosclerotic heart disease of native coronary artery with unspecified angina pectoris | 5 |
| `I340` | ICD-10 | Nonrheumatic mitral (valve) insufficiency | 5 |
| `4240` | ICD-9 | Mitral valve disorders | 4 |
| `4260` | ICD-9 | Atrioventricular block, complete | 4 |
| `42781` | ICD-9 | Sinoatrial node dysfunction | 4 |
| `44024` | ICD-9 | Atherosclerosis of native arteries of the extremities with gangrene | 4 |
| `I611` | ICD-10 | Nontraumatic intracerebral hemorrhage in hemisphere, cortical | 4 |
| `I714` | ICD-10 | Abdominal aortic aneurysm, without rupture | 4 |
| `3962` | ICD-9 | Mitral valve insufficiency and aortic valve stenosis | 3 |
| `4010` | ICD-9 | Malignant essential hypertension | 3 |
| `41041` | ICD-9 | Acute myocardial infarction of other inferior wall, initial episode of care | 3 |
| `41513` | ICD-9 | Saddle embolus of pulmonary artery | 3 |
| `44021` | ICD-9 | Atherosclerosis of native arteries of the extremities with intermittent claudication | 3 |
| `44101` | ICD-9 | Dissection of aorta, thoracic | 3 |
| `45341` | ICD-9 | Acute venous embolism and thrombosis of deep vessels of proximal lower extremity | 3 |
| `I2699` | ICD-10 | Other pulmonary embolism without acute cor pulmonale | 3 |
| `I639` | ICD-10 | Cerebral infarction, unspecified | 3 |
| `4254` | ICD-9 | Other primary cardiomyopathies | 2 |
| `42843` | ICD-9 | Acute on chronic combined systolic and diastolic heart failure | 2 |
| `4321` | ICD-9 | Subdural hemorrhage | 2 |
| `43311` | ICD-9 | Occlusion and stenosis of carotid artery with cerebral infarction | 2 |
| `4359` | ICD-9 | Unspecified transient cerebral ischemia | 2 |
| `44031` | ICD-9 | Atherosclerosis of autologous vein bypass graft of the extremities | 2 |
| `4414` | ICD-9 | Abdominal aneurysm without mention of rupture | 2 |
| `4417` | ICD-9 | Thoracoabdominal aneurysm, without mention of rupture | 2 |
| `4465` | ICD-9 | Giant cell arteritis | 2 |
| `I080` | ICD-10 | Rheumatic disorders of both mitral and aortic valves | 2 |
| `I081` | ICD-10 | Rheumatic disorders of both mitral and tricuspid valves | 2 |
| `I2109` | ICD-10 | ST elevation (STEMI) myocardial infarction involving other coronary artery of anterior wall | 2 |
| `I2119` | ICD-10 | ST elevation (STEMI) myocardial infarction involving other coronary artery of inferior wall | 2 |
| `I213` | ICD-10 | ST elevation (STEMI) myocardial infarction of unspecified site | 2 |
| `I25118` | ICD-10 | Atherosclerotic heart disease of native coronary artery with other forms of angina pectoris | 2 |
| `I2694` | ICD-10 | Multiple subsegmental pulmonary emboli without acute cor pulmonale | 2 |
| `I313` | ICD-10 | Pericardial effusion (noninflammatory) | 2 |
| `I319` | ICD-10 | Disease of pericardium, unspecified | 2 |
| `I5023` | ICD-10 | Acute on chronic systolic (congestive) heart failure | 2 |
| `I6201` | ICD-10 | Nontraumatic acute subdural hemorrhage | 2 |
| `I63311` | ICD-10 | Cerebral infarction due to thrombosis of right middle cerebral artery | 2 |
| `I63312` | ICD-10 | Cerebral infarction due to thrombosis of left middle cerebral artery | 2 |
| `I63411` | ICD-10 | Cerebral infarction due to embolism of right middle cerebral artery | 2 |
| `I81` | ICD-10 | Portal vein thrombosis | 2 |
| `3940` | ICD-9 | Mitral stenosis | 1 |
| `4019` | ICD-9 | Unspecified essential hypertension | 1 |
| `41001` | ICD-9 | Acute myocardial infarction of anterolateral wall, initial episode of care | 1 |
| `41011` | ICD-9 | Acute myocardial infarction of other anterior wall, initial episode of care | 1 |
| `41072` | ICD-9 | Subendocardial infarction, subsequent episode of care | 1 |
| `41091` | ICD-9 | Acute myocardial infarction of unspecified site, initial episode of care | 1 |
| `41400` | ICD-9 | Coronary atherosclerosis of unspecified type of vessel, native or graft | 1 |
| `41511` | ICD-9 | Iatrogenic pulmonary embolism and infarction | 1 |
| `4168` | ICD-9 | Other chronic pulmonary heart diseases | 1 |
| `42091` | ICD-9 | Acute idiopathic pericarditis | 1 |
| `4231` | ICD-9 | Adhesive pericarditis | 1 |
| `42511` | ICD-9 | Hypertrophic obstructive cardiomyopathy | 1 |
| `42652` | ICD-9 | Right bundle branch block and left anterior fascicular block | 1 |
| `4275` | ICD-9 | Cardiac arrest | 1 |
| `42789` | ICD-9 | Other specified cardiac dysrhythmias | 1 |
| `4280` | ICD-9 | Congestive heart failure, unspecified | 1 |
| `42821` | ICD-9 | Acute systolic heart failure | 1 |
| `42831` | ICD-9 | Acute diastolic heart failure | 1 |
| `43321` | ICD-9 | Occlusion and stenosis of vertebral artery with cerebral infarction | 1 |
| `43401` | ICD-9 | Cerebral thrombosis with cerebral infarction | 1 |
| `4373` | ICD-9 | Cerebral aneurysm, nonruptured | 1 |
| `4377` | ICD-9 | Transient global amnesia | 1 |
| `44023` | ICD-9 | Atherosclerosis of native arteries of the extremities with ulceration | 1 |
| `44102` | ICD-9 | Dissection of aorta, abdominal | 1 |
| `4422` | ICD-9 | Aneurysm of iliac artery | 1 |
| `4423` | ICD-9 | Aneurysm of artery of lower extremity | 1 |
| `44321` | ICD-9 | Dissection of carotid artery | 1 |
| `4439` | ICD-9 | Peripheral vascular disease, unspecified | 1 |
| `44422` | ICD-9 | Arterial embolism and thrombosis of lower extremity | 1 |
| `4460` | ICD-9 | Polyarteritis nodosa | 1 |
| `4478` | ICD-9 | Other specified disorders of arteries and arterioles | 1 |
| `4510` | ICD-9 | Phlebitis and thrombophlebitis of superficial vessels of lower extremities | 1 |
| `45340` | ICD-9 | Acute venous embolism and thrombosis of unspecified deep vessels of lower extremity | 1 |
| `45342` | ICD-9 | Acute venous embolism and thrombosis of deep vessels of distal lower extremity | 1 |
| `4552` | ICD-9 | Internal hemorrhoids with other complication | 1 |
| `4568` | ICD-9 | Varices of other sites | 1 |
| `4580` | ICD-9 | Orthostatic hypotension | 1 |
| `4588` | ICD-9 | Other specified hypotension | 1 |
| `4589` | ICD-9 | Hypotension, unspecified | 1 |
| `4592` | ICD-9 | Compression of vein | 1 |
| `I161` | ICD-10 | Hypertensive emergency | 1 |
| `I2102` | ICD-10 | ST elevation (STEMI) myocardial infarction involving left anterior descending coronary artery | 1 |
| `I2129` | ICD-10 | ST elevation (STEMI) myocardial infarction involving other sites | 1 |
| `I25710` | ICD-10 | Atherosclerosis of autologous vein coronary artery bypass graft(s) with unstable angina pectoris | 1 |
| `I2692` | ICD-10 | Saddle embolus of pulmonary artery without acute cor pulmonale | 1 |
| `I2720` | ICD-10 | Pulmonary hypertension, unspecified | 1 |
| `I288` | ICD-10 | Other diseases of pulmonary vessels | 1 |
| `I309` | ICD-10 | Acute pericarditis, unspecified | 1 |
| `I341` | ICD-10 | Nonrheumatic mitral (valve) prolapse | 1 |
| `I351` | ICD-10 | Nonrheumatic aortic (valve) insufficiency | 1 |
| `I421` | ICD-10 | Obstructive hypertrophic cardiomyopathy | 1 |
| `I442` | ICD-10 | Atrioventricular block, complete | 1 |
| `I480` | ICD-10 | Paroxysmal atrial fibrillation | 1 |
| `I481` | ICD-10 | Persistent atrial fibrillation | 1 |
| `I4819` | ICD-10 | Other persistent atrial fibrillation | 1 |
| `I4891` | ICD-10 | Unspecified atrial fibrillation | 1 |
| `I5082` | ICD-10 | Biventricular heart failure | 1 |
| `I5181` | ICD-10 | Takotsubo syndrome | 1 |
| `I6011` | ICD-10 | Nontraumatic subarachnoid hemorrhage from right middle cerebral artery | 1 |
| `I602` | ICD-10 | Nontraumatic subarachnoid hemorrhage from anterior communicating artery | 1 |
| `I604` | ICD-10 | Nontraumatic subarachnoid hemorrhage from basilar artery | 1 |
| `I607` | ICD-10 | Nontraumatic subarachnoid hemorrhage from unspecified intracranial artery | 1 |
| `I609` | ICD-10 | Nontraumatic subarachnoid hemorrhage, unspecified | 1 |
| `I614` | ICD-10 | Nontraumatic intracerebral hemorrhage in cerebellum | 1 |
| `I618` | ICD-10 | Other nontraumatic intracerebral hemorrhage | 1 |
| `I63431` | ICD-10 | Cerebral infarction due to embolism of right posterior cerebral artery | 1 |
| `I63433` | ICD-10 | Cerebral infarction due to embolism of bilateral posterior cerebral arteries | 1 |
| `I63511` | ICD-10 | Cerebral infarction due to unspecified occlusion or stenosis of right middle cerebral artery | 1 |
| `I63512` | ICD-10 | Cerebral infarction due to unspecified occlusion or stenosis of left middle cerebral artery | 1 |
| `I6522` | ICD-10 | Occlusion and stenosis of left carotid artery | 1 |
| `I675` | ICD-10 | Moyamoya disease | 1 |
| `I69992` | ICD-10 | Facial weakness following unspecified cerebrovascular disease | 1 |
| `I70221` | ICD-10 | Atherosclerosis of native arteries of extremities with rest pain, right leg | 1 |
| `I70245` | ICD-10 | Atherosclerosis of native arteries of left leg with ulceration of other part of foot | 1 |
| `I7101` | ICD-10 | Dissection of thoracic aorta | 1 |
| `I7102` | ICD-10 | Dissection of abdominal aorta | 1 |
| `I712` | ICD-10 | Thoracic aortic aneurysm, without rupture | 1 |
| `I713` | ICD-10 | Abdominal aortic aneurysm, ruptured | 1 |
| `I715` | ICD-10 | Thoracoabdominal aortic aneurysm, ruptured | 1 |
| `I716` | ICD-10 | Thoracoabdominal aortic aneurysm, without rupture | 1 |
| `I724` | ICD-10 | Aneurysm of artery of lower extremity | 1 |
| `I725` | ICD-10 | Aneurysm of other precerebral arteries | 1 |
| `I7300` | ICD-10 | Raynaud's syndrome without gangrene | 1 |
| `I7789` | ICD-10 | Other specified disorders of arteries and arterioles | 1 |
| `I82412` | ICD-10 | Acute embolism and thrombosis of left femoral vein | 1 |
| `I82421` | ICD-10 | Acute embolism and thrombosis of right iliac vein | 1 |
| `I8501` | ICD-10 | Esophageal varices with bleeding | 1 |
| `I952` | ICD-10 | Hypotension due to drugs | 1 |
| `I959` | ICD-10 | Hypotension, unspecified | 1 |
| `I9789` | ICD-10 | Other postprocedural complications and disorders of the circulatory system, not elsewhere classified | 1 |

### Injury and poisoning  
*194 codes, 281 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `99859` | ICD-9 | Other postoperative infection | 10 |
| `T814XXA` | ICD-10 | Infection following a procedure, initial encounter | 6 |
| `8082` | ICD-9 | Closed fracture of pubis | 5 |
| `80121` | ICD-9 | Closed fracture of base of skull with subarachnoid, subdural, and extradural hemorrhage, with no loss of consciousness | 4 |
| `80126` | ICD-9 | Closed fracture of base of skull with subarachnoid, subdural, and extradural hemorrhage, with loss of consciousness of unspecified duration | 4 |
| `8054` | ICD-9 | Closed fracture of lumbar vertebra without mention of spinal cord injury | 4 |
| `81342` | ICD-9 | Other closed fractures of distal end of radius (alone) | 4 |
| `82300` | ICD-9 | Closed fracture of upper end of tibia alone | 4 |
| `85221` | ICD-9 | Subdural hemorrhage following injury without mention of open intracranial wound, with no loss of consciousness | 3 |
| `9654` | ICD-9 | Poisoning by aromatic analgesics, not elsewhere classified | 3 |
| `99649` | ICD-9 | Other mechanical complication of other internal orthopedic device, implant, and graft | 3 |
| `99662` | ICD-9 | Infection and inflammatory reaction due to other vascular device, implant, and graft | 3 |
| `9974` | ICD-9 | Digestive system complications, not elsewhere classified | 3 |
| `99812` | ICD-9 | Hematoma complicating a procedure | 3 |
| `9982` | ICD-9 | Accidental puncture or laceration during a procedure, not elsewhere classified | 3 |
| `99932` | ICD-9 | Bloodstream infection due to central venous catheter | 3 |
| `S065X0A` | ICD-10 | Traumatic subdural hemorrhage without loss of consciousness, initial encounter | 3 |
| `S2242XA` | ICD-10 | Multiple fractures of ribs, left side, initial encounter for closed fracture | 3 |
| `T8579XA` | ICD-10 | Infection and inflammatory reaction due to other internal prosthetic devices, implants and grafts, initial encounter | 3 |
| `80222` | ICD-9 | Closed fracture of mandible, subcondylar | 2 |
| `80502` | ICD-9 | Closed fracture of second cervical vertebra | 2 |
| `8052` | ICD-9 | Closed fracture of dorsal [thoracic] vertebra without mention of spinal cord injury | 2 |
| `80702` | ICD-9 | Closed fracture of two ribs | 2 |
| `81321` | ICD-9 | Closed fracture of shaft of radius (alone) | 2 |
| `82021` | ICD-9 | Closed fracture of intertrochanteric section of neck of femur | 2 |
| `8208` | ICD-9 | Closed fracture of unspecified part of neck of femur | 2 |
| `82101` | ICD-9 | Closed fracture of shaft of femur | 2 |
| `82320` | ICD-9 | Closed fracture of shaft of tibia alone | 2 |
| `82322` | ICD-9 | Closed fracture of shaft of fibula with tibia | 2 |
| `8248` | ICD-9 | Unspecified fracture of ankle, closed | 2 |
| `85182` | ICD-9 | Other and unspecified cerebral laceration and contusion, without mention of open intracranial wound, with brief [less than one hour] loss of consciousness | 2 |
| `86503` | ICD-9 | Injury to spleen without mention of open wound into cavity, laceration extending into parenchyma | 2 |
| `86803` | ICD-9 | Injury to other intra-abdominal organs without mention of open wound into cavity, peritoneum | 2 |
| `8730` | ICD-9 | Open wound of scalp, without mention of complication | 2 |
| `96501` | ICD-9 | Poisoning by heroin | 2 |
| `99642` | ICD-9 | Dislocation of prosthetic joint | 2 |
| `99664` | ICD-9 | Infection and inflammatory reaction due to indwelling urinary catheter | 2 |
| `99667` | ICD-9 | Infection and inflammatory reaction due to other internal orthopedic device, implant, and graft | 2 |
| `99672` | ICD-9 | Other complications due to other cardiac device, implant, and graft | 2 |
| `99674` | ICD-9 | Other complications due to other vascular device, implant, and graft | 2 |
| `99681` | ICD-9 | Complications of transplanted kidney | 2 |
| `99749` | ICD-9 | Other digestive system complications | 2 |
| `99832` | ICD-9 | Disruption of external operation (surgical) wound | 2 |
| `S065X9A` | ICD-10 | Traumatic subdural hemorrhage with loss of consciousness of unspecified duration, initial encounter | 2 |
| `S7221XA` | ICD-10 | Displaced subtrochanteric fracture of right femur, initial encounter for closed fracture | 2 |
| `S82141A` | ICD-10 | Displaced bicondylar fracture of right tibia, initial encounter for closed fracture | 2 |
| `S82142A` | ICD-10 | Displaced bicondylar fracture of left tibia, initial encounter for closed fracture | 2 |
| `S82872A` | ICD-10 | Displaced pilon fracture of left tibia, initial encounter for closed fracture | 2 |
| `T8203XA` | ICD-10 | Leakage of heart valve prosthesis, initial encounter | 2 |
| `T82855A` | ICD-10 | Stenosis of coronary artery stent, initial encounter | 2 |
| `T84622A` | ICD-10 | Infection and inflammatory reaction due to internal fixation device of right tibia, initial encounter | 2 |
| `80102` | ICD-9 | Closed fracture of base of skull without mention of intra cranial injury, with brief [less than one hour] loss of consciousness | 1 |
| `80112` | ICD-9 | Closed fracture of base of skull with cerebral laceration and contusion, with brief [less than one hour] loss of consciousness | 1 |
| `80115` | ICD-9 | Closed fracture of base of skull with cerebral laceration and contusion, with prolonged [more than 24 hours] loss of consciousness, without return to pre-existing conscious level | 1 |
| `8024` | ICD-9 | Closed fracture of malar and maxillary bones | 1 |
| `80506` | ICD-9 | Closed fracture of sixth cervical vertebra | 1 |
| `80639` | ICD-9 | Open fracture of T7-T12 level with other specified spinal cord injury | 1 |
| `80703` | ICD-9 | Closed fracture of three ribs | 1 |
| `8072` | ICD-9 | Closed fracture of sternum | 1 |
| `8080` | ICD-9 | Closed fracture of acetabulum | 1 |
| `8088` | ICD-9 | Closed unspecified fracture of pelvis | 1 |
| `81002` | ICD-9 | Closed fracture of shaft of clavicle | 1 |
| `81201` | ICD-9 | Closed fracture of surgical neck of humerus | 1 |
| `81221` | ICD-9 | Closed fracture of shaft of humerus | 1 |
| `81241` | ICD-9 | Closed supracondylar fracture of humerus | 1 |
| `81243` | ICD-9 | Closed fracture of medial condyle of humerus | 1 |
| `81305` | ICD-9 | Closed fracture of head of radius | 1 |
| `81315` | ICD-9 | Open fracture of head of radius | 1 |
| `81344` | ICD-9 | Closed fracture of lower end of radius with ulna | 1 |
| `82009` | ICD-9 | Other closed transcervical fracture of neck of femur | 1 |
| `82022` | ICD-9 | Closed fracture of subtrochanteric section of neck of femur | 1 |
| `82111` | ICD-9 | Open fracture of shaft of femur | 1 |
| `82122` | ICD-9 | Closed fracture of epiphysis, lower (separation) of femur | 1 |
| `82123` | ICD-9 | Closed supracondylar fracture of femur | 1 |
| `82302` | ICD-9 | Closed fracture of upper end of fibula with tibia | 1 |
| `82332` | ICD-9 | Open fracture of shaft of fibula with tibia | 1 |
| `82392` | ICD-9 | Open fracture of unspecified part of fibula with tibia | 1 |
| `8242` | ICD-9 | Fracture of lateral malleolus, closed | 1 |
| `8246` | ICD-9 | Trimalleolar fracture, closed | 1 |
| `83651` | ICD-9 | Anterior dislocation of tibia, proximal end, closed | 1 |
| `85102` | ICD-9 | Cortex (cerebral) contusion without mention of open intracranial wound, with brief [less than one hour] loss of consciousness | 1 |
| `85181` | ICD-9 | Other and unspecified cerebral laceration and contusion, without mention of open intracranial wound, with no loss of consciousness | 1 |
| `85186` | ICD-9 | Other and unspecified cerebral laceration and contusion, without mention of open intracranial wound, with loss of consciousness of unspecified duration | 1 |
| `85200` | ICD-9 | Subarachnoid hemorrhage following injury without mention of open intracranial wound, unspecified state of consciousness | 1 |
| `85201` | ICD-9 | Subarachnoid hemorrhage following injury without mention of open intracranial wound, with no loss of consciousness | 1 |
| `85202` | ICD-9 | Subarachnoid hemorrhage following injury without mention of open intracranial wound, with brief [less than one hour] loss of consciousness | 1 |
| `85203` | ICD-9 | Subarachnoid hemorrhage following injury without mention of open intracranial wound, with moderate [1-24 hours] loss of consciousness | 1 |
| `85211` | ICD-9 | Subarachnoid hemorrhage following injury with open intracranial wound, with no loss of consciousness | 1 |
| `85226` | ICD-9 | Subdural hemorrhage following injury without mention of open intracranial wound, with loss of consciousness of unspecified duration | 1 |
| `85302` | ICD-9 | Other and unspecified intracranial hemorrhage following injury without mention of open intracranial wound, with brief [less than one hour] loss of consciousness | 1 |
| `86400` | ICD-9 | Injury to liver without mention of open wound into cavity, unspecified injury | 1 |
| `86403` | ICD-9 | Injury to liver without mention of open wound into cavity, laceration, moderate | 1 |
| `86404` | ICD-9 | Injury to liver without mention of open wound into cavity, laceration, major | 1 |
| `86810` | ICD-9 | Injury to other intra-abdominal organs with open wound into cavity, unspecified intra-abdominal organ | 1 |
| `87343` | ICD-9 | Open wound of lip, without mention of complication | 1 |
| `87353` | ICD-9 | Open wound of lip, complicated | 1 |
| `87361` | ICD-9 | Open wound of buccal mucosa, without mention of complication | 1 |
| `8748` | ICD-9 | Open wound of other and unspecified parts of neck, without mention of complication | 1 |
| `8760` | ICD-9 | Open wound of back, without mention of complication | 1 |
| `8901` | ICD-9 | Open wound of hip and thigh, complicated | 1 |
| `8911` | ICD-9 | Open wound of knee, leg [except thigh], and ankle, complicated | 1 |
| `8912` | ICD-9 | Open wound of knee, leg [except thigh], and ankle, with tendon involvement | 1 |
| `90442` | ICD-9 | Injury to popliteal vein | 1 |
| `9222` | ICD-9 | Contusion of abdominal wall | 1 |
| `9224` | ICD-9 | Contusion of genital organs | 1 |
| `92720` | ICD-9 | Crushing injury of hand(s) | 1 |
| `9582` | ICD-9 | Secondary and recurrent hemorrhage | 1 |
| `9623` | ICD-9 | Poisoning by insulins and antidiabetic agents | 1 |
| `9651` | ICD-9 | Poisoning by salicylates | 1 |
| `96909` | ICD-9 | Poisoning by other antidepressants | 1 |
| `9712` | ICD-9 | Poisoning by sympathomimetics [adrenergics] | 1 |
| `9729` | ICD-9 | Poisoning by other and unspecified agents primarily affecting the cardiovascular system | 1 |
| `9828` | ICD-9 | Toxic effect of other nonpetroleum-based solvents | 1 |
| `9911` | ICD-9 | Frostbite of hand | 1 |
| `9951` | ICD-9 | Angioneurotic edema, not elsewhere classified | 1 |
| `99601` | ICD-9 | Mechanical complication due to cardiac pacemaker (electrode) | 1 |
| `99640` | ICD-9 | Unspecified mechanical complication of internal orthopedic device, implant, and graft | 1 |
| `99659` | ICD-9 | Mechanical complication due to other implant and internal device, not elsewhere classified | 1 |
| `99665` | ICD-9 | Infection and inflammatory reaction due to other genitourinary device, implant, and graft | 1 |
| `99669` | ICD-9 | Infection and inflammatory reaction due to other internal prosthetic device, implant, and graft | 1 |
| `99678` | ICD-9 | Other complications due to other internal orthopedic device, implant, and graft | 1 |
| `99679` | ICD-9 | Other complications due to other internal prosthetic device, implant, and graft | 1 |
| `99685` | ICD-9 | Complications of transplanted bone marrow | 1 |
| `9971` | ICD-9 | Cardiac complications, not elsewhere classified | 1 |
| `9972` | ICD-9 | Peripheral vascular complications, not elsewhere classified | 1 |
| `99779` | ICD-9 | Vascular complications of other vessels | 1 |
| `99813` | ICD-9 | Seroma complicating a procedure | 1 |
| `99851` | ICD-9 | Infected postoperative seroma | 1 |
| `9992` | ICD-9 | Other vascular complications of medical care, not elsewhere classified | 1 |
| `S062X0A` | ICD-10 | Diffuse traumatic brain injury without loss of consciousness, initial encounter | 1 |
| `S06329A` | ICD-10 | Contusion and laceration of left cerebrum with loss of consciousness of unspecified duration, initial encounter | 1 |
| `S064X9A` | ICD-10 | Epidural hemorrhage with loss of consciousness of unspecified duration, initial encounter | 1 |
| `S065X1A` | ICD-10 | Traumatic subdural hemorrhage with loss of consciousness of 30 minutes or less, initial encounter | 1 |
| `S066X0A` | ICD-10 | Traumatic subarachnoid hemorrhage without loss of consciousness, initial encounter | 1 |
| `S1194XA` | ICD-10 | Puncture wound with foreign body of unspecified part of neck, initial encounter | 1 |
| `S12110A` | ICD-10 | Anterior displaced Type II dens fracture, initial encounter for closed fracture | 1 |
| `S14122A` | ICD-10 | Central cord syndrome at C2 level of cervical spinal cord, initial encounter | 1 |
| `S14154A` | ICD-10 | Other incomplete lesion at C4 level of cervical spinal cord, initial encounter | 1 |
| `S22078A` | ICD-10 | Other fracture of T9-T10 vertebra, initial encounter for closed fracture | 1 |
| `S2232XA` | ICD-10 | Fracture of one rib, left side, initial encounter for closed fracture | 1 |
| `S2243XA` | ICD-10 | Multiple fractures of ribs, bilateral, initial encounter for closed fracture | 1 |
| `S32011A` | ICD-10 | Stable burst fracture of first lumbar vertebra, initial encounter for closed fracture | 1 |
| `S32432A` | ICD-10 | Displaced fracture of anterior column [iliopubic] of left acetabulum, initial encounter for closed fracture | 1 |
| `S32592A` | ICD-10 | Other specified fracture of left pubis, initial encounter for closed fracture | 1 |
| `S36031A` | ICD-10 | Moderate laceration of spleen, initial encounter | 1 |
| `S36591A` | ICD-10 | Other injury of transverse colon, initial encounter | 1 |
| `S36898A` | ICD-10 | Other injury of other intra-abdominal organs, initial encounter | 1 |
| `S37051A` | ICD-10 | Moderate laceration of right kidney, initial encounter | 1 |
| `S37062A` | ICD-10 | Major laceration of left kidney, initial encounter | 1 |
| `S52021B` | ICD-10 | Displaced fracture of olecranon process without intraarticular extension of right ulna, initial encounter for open fracture type I or II | 1 |
| `S71051A` | ICD-10 | Open bite, right hip, initial encounter | 1 |
| `S72001A` | ICD-10 | Fracture of unspecified part of neck of right femur, initial encounter for closed fracture | 1 |
| `S72002A` | ICD-10 | Fracture of unspecified part of neck of left femur, initial encounter for closed fracture | 1 |
| `S72142A` | ICD-10 | Displaced intertrochanteric fracture of left femur, initial encounter for closed fracture | 1 |
| `S72351A` | ICD-10 | Displaced comminuted fracture of shaft of right femur, initial encounter for closed fracture | 1 |
| `S72402A` | ICD-10 | Unspecified fracture of lower end of left femur, initial encounter for closed fracture | 1 |
| `S72455A` | ICD-10 | Nondisplaced supracondylar fracture without intracondylar extension of lower end of left femur, initial encounter for closed fracture | 1 |
| `S72492A` | ICD-10 | Other fracture of lower end of left femur, initial encounter for closed fracture | 1 |
| `S82101A` | ICD-10 | Unspecified fracture of upper end of right tibia, initial encounter for closed fracture | 1 |
| `S82252A` | ICD-10 | Displaced comminuted fracture of shaft of left tibia, initial encounter for closed fracture | 1 |
| `S82862A` | ICD-10 | Displaced Maisonneuve's fracture of left leg, initial encounter for closed fracture | 1 |
| `S82892K` | ICD-10 | Other fracture of left lower leg, subsequent encounter for closed fracture with nonunion | 1 |
| `T17990A` | ICD-10 | Other foreign object in respiratory tract, part unspecified in causing asphyxiation, initial encounter | 1 |
| `T184XXA` | ICD-10 | Foreign body in colon, initial encounter | 1 |
| `T391X1A` | ICD-10 | Poisoning by 4-Aminophenol derivatives, accidental (unintentional), initial encounter | 1 |
| `T391X2A` | ICD-10 | Poisoning by 4-Aminophenol derivatives, intentional self-harm, initial encounter | 1 |
| `T401X1A` | ICD-10 | Poisoning by heroin, accidental (unintentional), initial encounter | 1 |
| `T426X1A` | ICD-10 | Poisoning by other antiepileptic and sedative-hypnotic drugs, accidental (unintentional), initial encounter | 1 |
| `T43012A` | ICD-10 | Poisoning by tricyclic antidepressants, intentional self-harm, initial encounter | 1 |
| `T794XXA` | ICD-10 | Traumatic shock, initial encounter | 1 |
| `T80211A` | ICD-10 | Bloodstream infection due to central venous catheter, initial encounter | 1 |
| `T8029XA` | ICD-10 | Infection following other infusion, transfusion and therapeutic injection, initial encounter | 1 |
| `T8119XA` | ICD-10 | Other postprocedural shock, initial encounter | 1 |
| `T8141XA` | ICD-10 | Infection following a procedure, superficial incisional surgical site, initial encounter | 1 |
| `T8144XA` | ICD-10 | Sepsis following a procedure, initial encounter | 1 |
| `T8149XA` | ICD-10 | Infection following a procedure, other surgical site, initial encounter | 1 |
| `T82538A` | ICD-10 | Leakage of other cardiac and vascular devices and implants, initial encounter | 1 |
| `T82838A` | ICD-10 | Hemorrhage due to vascular prosthetic devices, implants and grafts, initial encounter | 1 |
| `T82857A` | ICD-10 | Stenosis of other cardiac prosthetic devices, implants and grafts, initial encounter | 1 |
| `T82868A` | ICD-10 | Thrombosis due to vascular prosthetic devices, implants and grafts, initial encounter | 1 |
| `T84010A` | ICD-10 | Broken internal right hip prosthesis, initial encounter | 1 |
| `T84028A` | ICD-10 | Dislocation of other internal joint prosthesis, initial encounter | 1 |
| `T84033A` | ICD-10 | Mechanical loosening of internal left knee prosthetic joint, initial encounter | 1 |
| `T84090A` | ICD-10 | Other mechanical complication of internal right hip prosthesis, initial encounter | 1 |
| `T8501XA` | ICD-10 | Breakdown (mechanical) of ventricular intracranial (communicating) shunt, initial encounter | 1 |
| `T85520A` | ICD-10 | Displacement of bile duct prosthesis, initial encounter | 1 |
| `T85614A` | ICD-10 | Breakdown (mechanical) of insulin pump, initial encounter | 1 |
| `T85628A` | ICD-10 | Displacement of other specified internal prosthetic devices, implants and grafts, initial encounter | 1 |
| `T85734A` | ICD-10 | Infection and inflammatory reaction due to implanted electronic neurostimulator, generator, initial encounter | 1 |
| `T85898A` | ICD-10 | Other specified complication of other internal prosthetic devices, implants and grafts, initial encounter | 1 |
| `T8611` | ICD-10 | Kidney transplant rejection | 1 |
| `T8641` | ICD-10 | Liver transplant rejection | 1 |
| `T8649` | ICD-10 | Other complications of liver transplant | 1 |
| `T888XXA` | ICD-10 | Other specified complications of surgical and medical care, not elsewhere classified, initial encounter | 1 |

### Diseases of the digestive system  
*145 codes, 256 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `5770` | ICD-9 | Acute pancreatitis | 15 |
| `5609` | ICD-9 | Unspecified intestinal obstruction | 10 |
| `56211` | ICD-9 | Diverticulitis of colon (without mention of hemorrhage) | 9 |
| `5409` | ICD-9 | Acute appendicitis without mention of peritonitis | 8 |
| `55321` | ICD-9 | Incisional hernia without mention of obstruction or gangrene | 6 |
| `56081` | ICD-9 | Intestinal or peritoneal adhesions with obstruction (postoperative) (postinfection) | 5 |
| `5761` | ICD-9 | Cholangitis | 5 |
| `5789` | ICD-9 | Hemorrhage of gastrointestinal tract, unspecified | 5 |
| `57400` | ICD-9 | Calculus of gallbladder with acute cholecystitis, without mention of obstruction | 4 |
| `5589` | ICD-9 | Other and unspecified noninfectious gastroenteritis and colitis | 3 |
| `56212` | ICD-9 | Diverticulosis of colon with hemorrhage | 3 |
| `57410` | ICD-9 | Calculus of gallbladder with other cholecystitis, without mention of obstruction | 3 |
| `K430` | ICD-10 | Incisional hernia with obstruction, without gangrene | 3 |
| `K432` | ICD-10 | Incisional hernia without obstruction or gangrene | 3 |
| `K56600` | ICD-10 | Partial intestinal obstruction, unspecified as to cause | 3 |
| `K7031` | ICD-10 | Alcoholic cirrhosis of liver with ascites | 3 |
| `K7200` | ICD-10 | Acute and subacute hepatic failure without coma | 3 |
| `K8000` | ICD-10 | Calculus of gallbladder with acute cholecystitis without obstruction | 3 |
| `K8050` | ICD-10 | Calculus of bile duct without cholangitis or cholecystitis without obstruction | 3 |
| `K9189` | ICD-10 | Other postprocedural complications and disorders of digestive system | 3 |
| `K922` | ICD-10 | Gastrointestinal hemorrhage, unspecified | 3 |
| `53010` | ICD-9 | Esophagitis, unspecified | 2 |
| `53081` | ICD-9 | Esophageal reflux | 2 |
| `53240` | ICD-9 | Chronic or unspecified duodenal ulcer with hemorrhage, without mention of obstruction | 2 |
| `53551` | ICD-9 | Unspecified gastritis and gastroduodenitis, with hemorrhage | 2 |
| `5400` | ICD-9 | Acute appendicitis with generalized peritonitis | 2 |
| `5401` | ICD-9 | Acute appendicitis with peritoneal abscess | 2 |
| `5569` | ICD-9 | Ulcerative colitis, unspecified | 2 |
| `566` | ICD-9 | Abscess of anal and rectal regions | 2 |
| `56969` | ICD-9 | Other colostomy and enterostomy complication | 2 |
| `5711` | ICD-9 | Acute alcoholic hepatitis | 2 |
| `5715` | ICD-9 | Cirrhosis of liver without mention of alcohol | 2 |
| `57431` | ICD-9 | Calculus of bile duct with acute cholecystitis, with obstruction | 2 |
| `57451` | ICD-9 | Calculus of bile duct without mention of cholecystitis, with obstruction | 2 |
| `5750` | ICD-9 | Acute cholecystitis | 2 |
| `5762` | ICD-9 | Obstruction of bile duct | 2 |
| `K264` | ICD-10 | Chronic or unspecified duodenal ulcer with hemorrhage | 2 |
| `K2971` | ICD-10 | Gastritis, unspecified, with bleeding | 2 |
| `K449` | ICD-10 | Diaphragmatic hernia without obstruction or gangrene | 2 |
| `K529` | ICD-10 | Noninfective gastroenteritis and colitis, unspecified | 2 |
| `K5732` | ICD-10 | Diverticulitis of large intestine without perforation or abscess without bleeding | 2 |
| `K7011` | ICD-10 | Alcoholic hepatitis with ascites | 2 |
| `K7290` | ICD-10 | Hepatic failure, unspecified without coma | 2 |
| `K7469` | ICD-10 | Other cirrhosis of liver | 2 |
| `K7689` | ICD-10 | Other specified diseases of liver | 2 |
| `K831` | ICD-10 | Obstruction of bile duct | 2 |
| `K8510` | ICD-10 | Biliary acute pancreatitis without necrosis or infection | 2 |
| `K852` | ICD-10 | Alcohol induced acute pancreatitis | 2 |
| `K9171` | ICD-10 | Accidental puncture and laceration of a digestive system organ or structure during a digestive system procedure | 2 |
| `K91840` | ICD-10 | Postprocedural hemorrhage of a digestive system organ or structure following a digestive system procedure | 2 |
| `5225` | ICD-9 | Periapical abscess without sinus | 1 |
| `52801` | ICD-9 | Mucositis (ulcerative) due to antineoplastic therapy | 1 |
| `5283` | ICD-9 | Cellulitis and abscess of oral soft tissues | 1 |
| `5285` | ICD-9 | Diseases of lips | 1 |
| `5303` | ICD-9 | Stricture and stenosis of esophagus | 1 |
| `5304` | ICD-9 | Perforation of esophagus | 1 |
| `53100` | ICD-9 | Acute gastric ulcer with hemorrhage, without mention of obstruction | 1 |
| `53110` | ICD-9 | Acute gastric ulcer with perforation, without mention of obstruction | 1 |
| `53140` | ICD-9 | Chronic or unspecified gastric ulcer with hemorrhage, without mention of obstruction | 1 |
| `53190` | ICD-9 | Gastric ulcer, unspecified as acute or chronic, without mention of hemorrhage or perforation, without mention of obstruction | 1 |
| `53200` | ICD-9 | Acute duodenal ulcer with hemorrhage, without mention of obstruction | 1 |
| `53340` | ICD-9 | Chronic or unspecified peptic ulcer of unspecified site with hemorrhage, without mention of obstruction | 1 |
| `53541` | ICD-9 | Other specified gastritis, with hemorrhage | 1 |
| `53550` | ICD-9 | Unspecified gastritis and gastroduodenitis, without mention of hemorrhage | 1 |
| `53560` | ICD-9 | Duodenitis, without mention of hemorrhage | 1 |
| `53784` | ICD-9 | Dieulafoy lesion (hemorrhagic) of stomach and duodenum | 1 |
| `542` | ICD-9 | Other appendicitis | 1 |
| `55010` | ICD-9 | Inguinal hernia, with obstruction, without mention of gangrene, unilateral or unspecified (not specified as recurrent) | 1 |
| `55090` | ICD-9 | Inguinal hernia, without mention of obstruction or gangrene, unilateral or unspecified (not specified as recurrent) | 1 |
| `55220` | ICD-9 | Ventral, unspecified, hernia with obstruction | 1 |
| `55221` | ICD-9 | Incisional ventral hernia with obstruction | 1 |
| `5523` | ICD-9 | Diaphragmatic hernia with obstruction | 1 |
| `5550` | ICD-9 | Regional enteritis of small intestine | 1 |
| `5563` | ICD-9 | Ulcerative (chronic) proctosigmoiditis | 1 |
| `5570` | ICD-9 | Acute vascular insufficiency of intestine | 1 |
| `5601` | ICD-9 | Paralytic ileus | 1 |
| `56200` | ICD-9 | Diverticulosis of small intestine (without mention of hemorrhage) | 1 |
| `5641` | ICD-9 | Irritable bowel syndrome | 1 |
| `56722` | ICD-9 | Peritoneal abscess | 1 |
| `56782` | ICD-9 | Sclerosing mesenteritis | 1 |
| `5692` | ICD-9 | Stenosis of rectum and anus | 1 |
| `56962` | ICD-9 | Mechanical complication of colostomy and enterostomy | 1 |
| `5712` | ICD-9 | Alcoholic cirrhosis of liver | 1 |
| `57142` | ICD-9 | Autoimmune hepatitis | 1 |
| `57149` | ICD-9 | Other chronic hepatitis | 1 |
| `5720` | ICD-9 | Abscess of liver | 1 |
| `5722` | ICD-9 | Hepatic encephalopathy | 1 |
| `5723` | ICD-9 | Portal hypertension | 1 |
| `5733` | ICD-9 | Hepatitis, unspecified | 1 |
| `57401` | ICD-9 | Calculus of gallbladder with acute cholecystitis, with obstruction | 1 |
| `57490` | ICD-9 | Calculus of gallbladder and bile duct without cholecystitis, without mention of obstruction | 1 |
| `57511` | ICD-9 | Chronic cholecystitis | 1 |
| `5771` | ICD-9 | Chronic pancreatitis | 1 |
| `5778` | ICD-9 | Other specified diseases of pancreas | 1 |
| `5779` | ICD-9 | Unspecified disease of pancreas | 1 |
| `5781` | ICD-9 | Blood in stool | 1 |
| `K1121` | ICD-10 | Acute sialoadenitis | 1 |
| `K210` | ICD-10 | Gastro-esophageal reflux disease with esophagitis | 1 |
| `K219` | ICD-10 | Gastro-esophageal reflux disease without esophagitis | 1 |
| `K220` | ICD-10 | Achalasia of cardia | 1 |
| `K2210` | ICD-10 | Ulcer of esophagus without bleeding | 1 |
| `K226` | ICD-10 | Gastro-esophageal laceration-hemorrhage syndrome | 1 |
| `K250` | ICD-10 | Acute gastric ulcer with hemorrhage | 1 |
| `K269` | ICD-10 | Duodenal ulcer, unspecified as acute or chronic, without hemorrhage or perforation | 1 |
| `K285` | ICD-10 | Chronic or unspecified gastrojejunal ulcer with perforation | 1 |
| `K2921` | ICD-10 | Alcoholic gastritis with bleeding | 1 |
| `K311` | ICD-10 | Adult hypertrophic pyloric stenosis | 1 |
| `K3580` | ICD-10 | Unspecified acute appendicitis | 1 |
| `K420` | ICD-10 | Umbilical hernia with obstruction, without gangrene | 1 |
| `K433` | ICD-10 | Parastomal hernia with obstruction, without gangrene | 1 |
| `K436` | ICD-10 | Other and unspecified ventral hernia with obstruction, without gangrene | 1 |
| `K50012` | ICD-10 | Crohn's disease of small intestine with intestinal obstruction | 1 |
| `K50014` | ICD-10 | Crohn's disease of small intestine with abscess | 1 |
| `K50913` | ICD-10 | Crohn's disease, unspecified, with fistula | 1 |
| `K51011` | ICD-10 | Ulcerative (chronic) pancolitis with rectal bleeding | 1 |
| `K5180` | ICD-10 | Other ulcerative colitis without complications | 1 |
| `K51911` | ICD-10 | Ulcerative colitis, unspecified with rectal bleeding | 1 |
| `K5289` | ICD-10 | Other specified noninfective gastroenteritis and colitis | 1 |
| `K5641` | ICD-10 | Fecal impaction | 1 |
| `K5650` | ICD-10 | Intestinal adhesions [bands], unspecified as to partial versus complete obstruction | 1 |
| `K567` | ICD-10 | Ileus, unspecified | 1 |
| `K5720` | ICD-10 | Diverticulitis of large intestine with perforation and abscess without bleeding | 1 |
| `K5731` | ICD-10 | Diverticulosis of large intestine without perforation or abscess with bleeding | 1 |
| `K5733` | ICD-10 | Diverticulitis of large intestine without perforation or abscess with bleeding | 1 |
| `K5780` | ICD-10 | Diverticulitis of intestine, part unspecified, with perforation and abscess without bleeding | 1 |
| `K5900` | ICD-10 | Constipation, unspecified | 1 |
| `K644` | ICD-10 | Residual hemorrhoidal skin tags | 1 |
| `K648` | ICD-10 | Other hemorrhoids | 1 |
| `K649` | ICD-10 | Unspecified hemorrhoids | 1 |
| `K7010` | ICD-10 | Alcoholic hepatitis without ascites | 1 |
| `K7040` | ICD-10 | Alcoholic hepatic failure without coma | 1 |
| `K7041` | ICD-10 | Alcoholic hepatic failure with coma | 1 |
| `K743` | ICD-10 | Primary biliary cirrhosis | 1 |
| `K8012` | ICD-10 | Calculus of gallbladder with acute and chronic cholecystitis without obstruction | 1 |
| `K8062` | ICD-10 | Calculus of gallbladder and bile duct with acute cholecystitis without obstruction | 1 |
| `K8070` | ICD-10 | Calculus of gallbladder and bile duct without cholecystitis without obstruction | 1 |
| `K810` | ICD-10 | Acute cholecystitis | 1 |
| `K819` | ICD-10 | Cholecystitis, unspecified | 1 |
| `K8309` | ICD-10 | Other cholangitis | 1 |
| `K8520` | ICD-10 | Alcohol induced acute pancreatitis without necrosis or infection | 1 |
| `K8581` | ICD-10 | Other acute pancreatitis with uninfected necrosis | 1 |
| `K859` | ICD-10 | Acute pancreatitis, unspecified | 1 |
| `K9130` | ICD-10 | Postprocedural intestinal obstruction, unspecified as to partial versus complete | 1 |
| `K921` | ICD-10 | Melena | 1 |
| `K9412` | ICD-10 | Enterostomy infection | 1 |

### Pregnancy, childbirth and the puerperium  
*86 codes, 185 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `O99824` | ICD-10 | Streptococcus B carrier state complicating childbirth | 11 |
| `64511` | ICD-9 | Post term pregnancy, delivered, with or without mention of antepartum condition | 8 |
| `65421` | ICD-9 | Previous cesarean delivery, delivered, with or without mention of antepartum condition | 8 |
| `O34211` | ICD-10 | Maternal care for low transverse scar from previous cesarean delivery | 8 |
| `64231` | ICD-9 | Transient hypertension of pregnancy, delivered , with or without mention of antepartum condition | 6 |
| `O4202` | ICD-10 | Full-term premature rupture of membranes, onset of labor within 24 hours of rupture | 6 |
| `O480` | ICD-10 | Post-term pregnancy | 6 |
| `64891` | ICD-9 | Other current conditions classifiable elsewhere of mother, delivered, with or without mention of antepartum condition | 5 |
| `O700` | ICD-10 | First degree perineal laceration during delivery | 5 |
| `O701` | ICD-10 | Second degree perineal laceration during delivery | 5 |
| `65971` | ICD-9 | Abnormality in fetal heart rate or rhythm, delivered, with or without mention of antepartum condition | 4 |
| `O365930` | ICD-10 | Maternal care for other known or suspected poor fetal growth, third trimester, not applicable or unspecified | 4 |
| `65651` | ICD-9 | Poor fetal growth, affecting management of mother, delivered, with or without mention of antepartum condition | 3 |
| `65951` | ICD-9 | Elderly primigravida, delivered, with or without mention of antepartum condition | 3 |
| `65961` | ICD-9 | Elderly multigravida, delivered with or without mention of antepartum condition | 3 |
| `67484` | ICD-9 | Other complications of puerperium, postpartum condition or complication | 3 |
| `O1414` | ICD-10 | Severe pre-eclampsia complicating childbirth | 3 |
| `O2662` | ICD-10 | Liver and biliary tract disorders in childbirth | 3 |
| `O321XX0` | ICD-10 | Maternal care for breech presentation, not applicable or unspecified | 3 |
| `O4212` | ICD-10 | Full-term premature rupture of membranes, onset of labor more than 24 hours following rupture | 3 |
| `O4593` | ICD-10 | Premature separation of placenta, unspecified, third trimester | 3 |
| `O76` | ICD-10 | Abnormality in fetal heart rate and rhythm complicating labor and delivery | 3 |
| `O9902` | ICD-10 | Anemia complicating childbirth | 3 |
| `64421` | ICD-9 | Early onset of delivery, delivered, with or without mention of antepartum condition | 2 |
| `64843` | ICD-9 | Mental disorders of mother, antepartum condition or complication | 2 |
| `64893` | ICD-9 | Other current conditions classifiable elsewhere of mother, antepartum condition or complication | 2 |
| `650` | ICD-9 | Normal delivery | 2 |
| `65661` | ICD-9 | Excessive fetal growth, affecting management of mother, delivered, with or without mention of antepartum condition | 2 |
| `66381` | ICD-9 | Other umbilical cord complications complicating labor and delivery, delivered, with or without mention of antepartum condition | 2 |
| `O134` | ICD-10 | Gestational [pregnancy-induced] hypertension without significant proteinuria, complicating childbirth | 2 |
| `O1415` | ICD-10 | Severe pre-eclampsia, complicating the puerperium | 2 |
| `O24424` | ICD-10 | Gestational diabetes mellitus in childbirth, insulin controlled | 2 |
| `O4403` | ICD-10 | Complete placenta previa NOS or without hemorrhage, third trimester | 2 |
| `O6981X0` | ICD-10 | Labor and delivery complicated by cord around neck, without compression, not applicable or unspecified | 2 |
| `O7589` | ICD-10 | Other specified complications of labor and delivery | 2 |
| `O99344` | ICD-10 | Other mental disorders complicating childbirth | 2 |
| `64111` | ICD-9 | Hemorrhage from placenta previa, delivered, with or without mention of antepartum condition | 1 |
| `64241` | ICD-9 | Mild or unspecified pre-eclampsia, delivered, with or without mention of antepartum condition | 1 |
| `64251` | ICD-9 | Severe pre-eclampsia, delivered, with or without mention of antepartum condition | 1 |
| `64271` | ICD-9 | Pre-eclampsia or eclampsia superimposed on pre-existing hypertension, delivered, with or without mention of antepartum condition | 1 |
| `64303` | ICD-9 | Mild hyperemesis gravidarum, antepartum condition or complication | 1 |
| `64841` | ICD-9 | Mental disorders of mother, delivered, with or without mention of antepartum condition | 1 |
| `64864` | ICD-9 | Other cardiovascular diseases of mother, postpartum condition or complication | 1 |
| `64881` | ICD-9 | Abnormal glucose tolerance of mother, delivered, with or without mention of antepartum condition | 1 |
| `64943` | ICD-9 | Epilepsy complicating pregnancy, childbirth, or the puerperium, antepartum condition or complication | 1 |
| `65261` | ICD-9 | Multiple gestation with malpresentation of one fetus or more, delivered, with or without mention of antepartum condition | 1 |
| `65451` | ICD-9 | Cervical incompetence, delivered, with or without mention of antepartum condition | 1 |
| `65571` | ICD-9 | Decreased fetal movements, affecting management of mother, delivered, with or without mention of antepartum condition | 1 |
| `65811` | ICD-9 | Premature rupture of membranes, delivered, with or without mention of antepartum condition | 1 |
| `66041` | ICD-9 | Shoulder (girdle) dystocia, delivered, with or without mention of antepartum condition | 1 |
| `66101` | ICD-9 | Primary uterine inertia, delivered, with or without mention of antepartum condition | 1 |
| `66331` | ICD-9 | Other and unspecified cord entanglement, without mention of compression, complicating labor and delivery, delivered, with or without mention of antepartum condition | 1 |
| `66351` | ICD-9 | Vasa previa complicating labor and delivery, delivered, with or without mention of antepartum condition | 1 |
| `66401` | ICD-9 | First-degree perineal laceration, delivered, with or without mention of antepartum condition | 1 |
| `66411` | ICD-9 | Second-degree perineal laceration, delivered, with or without mention of antepartum condition | 1 |
| `66431` | ICD-9 | Fourth-degree perineal laceration, delivered, with or without mention of antepartum condition | 1 |
| `66541` | ICD-9 | High vaginal laceration, delivered, with or without mention of antepartum condition | 1 |
| `67024` | ICD-9 | Puerperal sepsis, postpartum condition or complication | 1 |
| `67401` | ICD-9 | Cerebrovascular disorders in the puerperium, delivered, with or without mention of antepartum condition | 1 |
| `O164` | ICD-10 | Unspecified maternal hypertension, complicating childbirth | 1 |
| `O219` | ICD-10 | Vomiting of pregnancy, unspecified | 1 |
| `O2672` | ICD-10 | Subluxation of symphysis (pubis) in childbirth | 1 |
| `O26893` | ICD-10 | Other specified pregnancy related conditions, third trimester | 1 |
| `O339` | ICD-10 | Maternal care for disproportion, unspecified | 1 |
| `O3421` | ICD-10 | Maternal care for scar from previous cesarean delivery | 1 |
| `O34219` | ICD-10 | Maternal care for unspecified type scar from previous cesarean delivery | 1 |
| `O358XX0` | ICD-10 | Maternal care for other (suspected) fetal abnormality and damage, not applicable or unspecified | 1 |
| `O364XX0` | ICD-10 | Maternal care for intrauterine death, not applicable or unspecified | 1 |
| `O3663X0` | ICD-10 | Maternal care for excessive fetal growth, third trimester, not applicable or unspecified | 1 |
| `O368930` | ICD-10 | Maternal care for other specified fetal problems, third trimester, not applicable or unspecified | 1 |
| `O411230` | ICD-10 | Chorioamnionitis, third trimester, not applicable or unspecified | 1 |
| `O4200` | ICD-10 | Premature rupture of membranes, onset of labor within 24 hours of rupture, unspecified weeks of gestation | 1 |
| `O42913` | ICD-10 | Preterm premature rupture of membranes, unspecified as to length of time between rupture and onset of labor, third trimester | 1 |
| `O4292` | ICD-10 | Full-term premature rupture of membranes, unspecified as to length of time between rupture and onset of labor | 1 |
| `O6014X1` | ICD-10 | Preterm labor third trimester with preterm delivery third trimester, fetus 1 | 1 |
| `O620` | ICD-10 | Primary inadequate contractions | 1 |
| `O628` | ICD-10 | Other abnormalities of forces of labor | 1 |
| `O716` | ICD-10 | Obstetric damage to pelvic joints and ligaments | 1 |
| `O770` | ICD-10 | Labor and delivery complicated by meconium in amniotic fluid | 1 |
| `O9832` | ICD-10 | Other infections with a predominantly sexual mode of transmission complicating childbirth | 1 |
| `O98513` | ICD-10 | Other viral diseases complicating pregnancy, third trimester | 1 |
| `O9852` | ICD-10 | Other viral diseases complicating childbirth | 1 |
| `O99214` | ICD-10 | Obesity complicating childbirth | 1 |
| `O9952` | ICD-10 | Diseases of the respiratory system complicating childbirth | 1 |
| `O99613` | ICD-10 | Diseases of the digestive system complicating pregnancy, third trimester | 1 |
| `O9A213` | ICD-10 | Injury, poisoning and certain other consequences of external causes complicating pregnancy, third trimester | 1 |

### Neoplasms  
*99 codes, 148 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `1983` | ICD-9 | Secondary malignant neoplasm of brain and spinal cord | 8 |
| `1985` | ICD-9 | Secondary malignant neoplasm of bone and bone marrow | 6 |
| `193` | ICD-9 | Malignant neoplasm of thyroid gland | 4 |
| `2189` | ICD-9 | Leiomyoma of uterus, unspecified | 4 |
| `C250` | ICD-10 | Malignant neoplasm of head of pancreas | 4 |
| `C679` | ICD-10 | Malignant neoplasm of bladder, unspecified | 4 |
| `C7931` | ICD-10 | Secondary malignant neoplasm of brain | 4 |
| `2252` | ICD-9 | Benign neoplasm of cerebral meninges | 3 |
| `C61` | ICD-10 | Malignant neoplasm of prostate | 3 |
| `D320` | ICD-10 | Benign neoplasm of cerebral meninges | 3 |
| `1520` | ICD-9 | Malignant neoplasm of duodenum | 2 |
| `1550` | ICD-9 | Malignant neoplasm of liver, primary | 2 |
| `1890` | ICD-9 | Malignant neoplasm of kidney, except pelvis | 2 |
| `1977` | ICD-9 | Malignant neoplasm of liver, secondary | 2 |
| `1978` | ICD-9 | Secondary malignant neoplasm of other digestive organs and spleen | 2 |
| `2113` | ICD-9 | Benign neoplasm of colon | 2 |
| `2127` | ICD-9 | Benign neoplasm of heart | 2 |
| `2181` | ICD-9 | Intramural leiomyoma of uterus | 2 |
| `2254` | ICD-9 | Benign neoplasm of spinal meninges | 2 |
| `C50911` | ICD-10 | Malignant neoplasm of unspecified site of right female breast | 2 |
| `C541` | ICD-10 | Malignant neoplasm of endometrium | 2 |
| `C711` | ICD-10 | Malignant neoplasm of frontal lobe | 2 |
| `C713` | ICD-10 | Malignant neoplasm of parietal lobe | 2 |
| `C7989` | ICD-10 | Secondary malignant neoplasm of other specified sites | 2 |
| `D251` | ICD-10 | Intramural leiomyoma of uterus | 2 |
| `D469` | ICD-10 | Myelodysplastic syndrome, unspecified | 2 |
| `1419` | ICD-9 | Malignant neoplasm of tongue, unspecified | 1 |
| `1505` | ICD-9 | Malignant neoplasm of lower third of esophagus | 1 |
| `1510` | ICD-9 | Malignant neoplasm of cardia | 1 |
| `1533` | ICD-9 | Malignant neoplasm of sigmoid colon | 1 |
| `1534` | ICD-9 | Malignant neoplasm of cecum | 1 |
| `1536` | ICD-9 | Malignant neoplasm of ascending colon | 1 |
| `1539` | ICD-9 | Malignant neoplasm of colon, unspecified site | 1 |
| `1551` | ICD-9 | Malignant neoplasm of intrahepatic bile ducts | 1 |
| `1560` | ICD-9 | Malignant neoplasm of gallbladder | 1 |
| `1561` | ICD-9 | Malignant neoplasm of extrahepatic bile ducts | 1 |
| `1611` | ICD-9 | Malignant neoplasm of supraglottis | 1 |
| `1625` | ICD-9 | Malignant neoplasm of lower lobe, bronchus or lung | 1 |
| `1629` | ICD-9 | Malignant neoplasm of bronchus and lung, unspecified | 1 |
| `1712` | ICD-9 | Malignant neoplasm of connective and other soft tissue of upper limb, including shoulder | 1 |
| `1742` | ICD-9 | Malignant neoplasm of upper-inner quadrant of female breast | 1 |
| `1749` | ICD-9 | Malignant neoplasm of breast (female), unspecified | 1 |
| `1820` | ICD-9 | Malignant neoplasm of corpus uteri, except isthmus | 1 |
| `185` | ICD-9 | Malignant neoplasm of prostate | 1 |
| `1911` | ICD-9 | Malignant neoplasm of frontal lobe | 1 |
| `1912` | ICD-9 | Malignant neoplasm of temporal lobe | 1 |
| `1913` | ICD-9 | Malignant neoplasm of parietal lobe | 1 |
| `1918` | ICD-9 | Malignant neoplasm of other parts of brain | 1 |
| `1976` | ICD-9 | Secondary malignant neoplasm of retroperitoneum and peritoneum | 1 |
| `20023` | ICD-9 | Burkitt's tumor or lymphoma, intra-abdominal lymph nodes | 1 |
| `2116` | ICD-9 | Benign neoplasm of pancreas, except islets of Langerhans | 1 |
| `2250` | ICD-9 | Benign neoplasm of brain | 1 |
| `226` | ICD-9 | Benign neoplasm of thyroid glands | 1 |
| `2273` | ICD-9 | Benign neoplasm of pituitary gland and craniopharyngeal duct | 1 |
| `2330` | ICD-9 | Carcinoma in situ of breast | 1 |
| `2374` | ICD-9 | Neoplasm of uncertain behavior of other and unspecified endocrine glands | 1 |
| `2381` | ICD-9 | Neoplasm of uncertain behavior of connective and other soft tissue | 1 |
| `C01` | ICD-10 | Malignant neoplasm of base of tongue | 1 |
| `C155` | ICD-10 | Malignant neoplasm of lower third of esophagus | 1 |
| `C169` | ICD-10 | Malignant neoplasm of stomach, unspecified | 1 |
| `C170` | ICD-10 | Malignant neoplasm of duodenum | 1 |
| `C180` | ICD-10 | Malignant neoplasm of cecum | 1 |
| `C181` | ICD-10 | Malignant neoplasm of appendix | 1 |
| `C184` | ICD-10 | Malignant neoplasm of transverse colon | 1 |
| `C186` | ICD-10 | Malignant neoplasm of descending colon | 1 |
| `C189` | ICD-10 | Malignant neoplasm of colon, unspecified | 1 |
| `C20` | ICD-10 | Malignant neoplasm of rectum | 1 |
| `C221` | ICD-10 | Intrahepatic bile duct carcinoma | 1 |
| `C240` | ICD-10 | Malignant neoplasm of extrahepatic bile duct | 1 |
| `C3412` | ICD-10 | Malignant neoplasm of upper lobe, left bronchus or lung | 1 |
| `C3431` | ICD-10 | Malignant neoplasm of lower lobe, right bronchus or lung | 1 |
| `C3490` | ICD-10 | Malignant neoplasm of unspecified part of unspecified bronchus or lung | 1 |
| `C3492` | ICD-10 | Malignant neoplasm of unspecified part of left bronchus or lung | 1 |
| `C4921` | ICD-10 | Malignant neoplasm of connective and soft tissue of right lower limb, including hip | 1 |
| `C49A3` | ICD-10 | Gastrointestinal stromal tumor of small intestine | 1 |
| `C539` | ICD-10 | Malignant neoplasm of cervix uteri, unspecified | 1 |
| `C55` | ICD-10 | Malignant neoplasm of uterus, part unspecified | 1 |
| `C562` | ICD-10 | Malignant neoplasm of left ovary | 1 |
| `C641` | ICD-10 | Malignant neoplasm of right kidney, except renal pelvis | 1 |
| `C642` | ICD-10 | Malignant neoplasm of left kidney, except renal pelvis | 1 |
| `C678` | ICD-10 | Malignant neoplasm of overlapping sites of bladder | 1 |
| `C700` | ICD-10 | Malignant neoplasm of cerebral meninges | 1 |
| `C718` | ICD-10 | Malignant neoplasm of overlapping sites of brain | 1 |
| `C73` | ICD-10 | Malignant neoplasm of thyroid gland | 1 |
| `C7801` | ICD-10 | Secondary malignant neoplasm of right lung | 1 |
| `C786` | ICD-10 | Secondary malignant neoplasm of retroperitoneum and peritoneum | 1 |
| `C787` | ICD-10 | Secondary malignant neoplasm of liver and intrahepatic bile duct | 1 |
| `C7951` | ICD-10 | Secondary malignant neoplasm of bone | 1 |
| `C7952` | ICD-10 | Secondary malignant neoplasm of bone marrow | 1 |
| `C7B02` | ICD-10 | Secondary carcinoid tumors of liver | 1 |
| `C8333` | ICD-10 | Diffuse large B-cell lymphoma, intra-abdominal lymph nodes | 1 |
| `C946` | ICD-10 | Myelodysplastic disease, not elsewhere classified | 1 |
| `D125` | ICD-10 | Benign neoplasm of sigmoid colon | 1 |
| `D135` | ICD-10 | Benign neoplasm of extrahepatic bile ducts | 1 |
| `D3615` | ICD-10 | Benign neoplasm of peripheral nerves and autonomic nervous system of abdomen | 1 |
| `D374` | ICD-10 | Neoplasm of uncertain behavior of colon | 1 |
| `D3A8` | ICD-10 | Other benign neuroendocrine tumors | 1 |
| `D430` | ICD-10 | Neoplasm of uncertain behavior of brain, supratentorial | 1 |
| `D46Z` | ICD-10 | Other myelodysplastic syndromes | 1 |

### Diseases of the musculoskeletal system and connective tissue  
*55 codes, 103 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `M48062` | ICD-10 | Spinal stenosis, lumbar region with neurogenic claudication | 8 |
| `71536` | ICD-9 | Osteoarthrosis, localized, not specified whether primary or secondary, lower leg | 7 |
| `M1711` | ICD-10 | Unilateral primary osteoarthritis, right knee | 7 |
| `M4802` | ICD-10 | Spinal stenosis, cervical region | 7 |
| `71535` | ICD-9 | Osteoarthrosis, localized, not specified whether primary or secondary, pelvic region and thigh | 4 |
| `72210` | ICD-9 | Displacement of lumbar intervertebral disc without myelopathy | 4 |
| `71596` | ICD-9 | Osteoarthrosis, unspecified whether generalized or localized, lower leg | 3 |
| `72402` | ICD-9 | Spinal stenosis, lumbar region, without neurogenic claudication | 3 |
| `M1712` | ICD-10 | Unilateral primary osteoarthritis, left knee | 3 |
| `M4712` | ICD-10 | Other spondylosis with myelopathy, cervical region | 3 |
| `72271` | ICD-9 | Intervertebral disc disorder with myelopathy, cervical region | 2 |
| `73382` | ICD-9 | Nonunion of fracture | 2 |
| `M1612` | ICD-10 | Unilateral primary osteoarthritis, left hip | 2 |
| `M1651` | ICD-10 | Unilateral post-traumatic osteoarthritis, right hip | 2 |
| `M179` | ICD-10 | Osteoarthritis of knee, unspecified | 2 |
| `M4722` | ICD-10 | Other spondylosis with radiculopathy, cervical region | 2 |
| `M48061` | ICD-10 | Spinal stenosis, lumbar region without neurogenic claudication | 2 |
| `M5116` | ICD-10 | Intervertebral disc disorders with radiculopathy, lumbar region | 2 |
| `M8008XA` | ICD-10 | Age-related osteoporosis with current pathological fracture, vertebra(e), initial encounter for fracture | 2 |
| `71616` | ICD-9 | Traumatic arthropathy, lower leg | 1 |
| `71842` | ICD-9 | Contracture of joint, upper arm | 1 |
| `71852` | ICD-9 | Ankylosis of joint, upper arm | 1 |
| `71909` | ICD-9 | Effusion of joint, multiple sites | 1 |
| `7201` | ICD-9 | Spinal enthesopathy | 1 |
| `7210` | ICD-9 | Cervical spondylosis without myelopathy | 1 |
| `7213` | ICD-9 | Lumbosacral spondylosis without myelopathy | 1 |
| `72141` | ICD-9 | Spondylosis with myelopathy, thoracic region | 1 |
| `7220` | ICD-9 | Displacement of cervical intervertebral disc without myelopathy | 1 |
| `72211` | ICD-9 | Displacement of thoracic intervertebral disc without myelopathy | 1 |
| `7224` | ICD-9 | Degeneration of cervical intervertebral disc | 1 |
| `72252` | ICD-9 | Degeneration of lumbar or lumbosacral intervertebral disc | 1 |
| `7231` | ICD-9 | Cervicalgia | 1 |
| `7245` | ICD-9 | Backache, unspecified | 1 |
| `7260` | ICD-9 | Adhesive capsulitis of shoulder | 1 |
| `72619` | ICD-9 | Other specified disorders of bursae and tendons in shoulder region | 1 |
| `72741` | ICD-9 | Ganglion of joint | 1 |
| `72999` | ICD-9 | Other disorders of soft tissue | 1 |
| `73027` | ICD-9 | Unspecified osteomyelitis, ankle and foot | 1 |
| `73313` | ICD-9 | Pathologic fracture of vertebrae | 1 |
| `73315` | ICD-9 | Pathologic fracture of other specified part of femur | 1 |
| `M069` | ICD-10 | Rheumatoid arthritis, unspecified | 1 |
| `M109` | ICD-10 | Gout, unspecified | 1 |
| `M1611` | ICD-10 | Unilateral primary osteoarthritis, right hip | 1 |
| `M272` | ICD-10 | Inflammatory conditions of jaws | 1 |
| `M311` | ICD-10 | Thrombotic microangiopathy | 1 |
| `M3213` | ICD-10 | Lung involvement in systemic lupus erythematosus | 1 |
| `M3214` | ICD-10 | Glomerular disease in systemic lupus erythematosus | 1 |
| `M4126` | ICD-10 | Other idiopathic scoliosis, lumbar region | 1 |
| `M4316` | ICD-10 | Spondylolisthesis, lumbar region | 1 |
| `M4622` | ICD-10 | Osteomyelitis of vertebra, cervical region | 1 |
| `M50022` | ICD-10 | Cervical disc disorder at C5-C6 level with myelopathy | 1 |
| `M5117` | ICD-10 | Intervertebral disc disorders with radiculopathy, lumbosacral region | 1 |
| `M7981` | ICD-10 | Nontraumatic hematoma of soft tissue | 1 |
| `M84551A` | ICD-10 | Pathological fracture in neoplastic disease, right femur, initial encounter for fracture | 1 |
| `M87851` | ICD-10 | Other osteonecrosis, right femur | 1 |

### Mental, behavioural and neurodevelopmental disorders  
*52 codes, 91 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `29620` | ICD-9 | Major depressive affective disorder, single episode, unspecified | 7 |
| `29690` | ICD-9 | Unspecified episodic mood disorder | 7 |
| `F312` | ICD-10 | Bipolar disorder, current episode manic severe with psychotic features | 5 |
| `29532` | ICD-9 | Paranoid type schizophrenia, chronic | 3 |
| `29644` | ICD-9 | Bipolar I disorder, most recent episode (or current) manic, severe, specified as with psychotic behavior | 3 |
| `2989` | ICD-9 | Unspecified psychosis | 3 |
| `311` | ICD-9 | Depressive disorder, not elsewhere classified | 3 |
| `F332` | ICD-10 | Major depressive disorder, recurrent severe without psychotic features | 3 |
| `29181` | ICD-9 | Alcohol withdrawal | 2 |
| `2948` | ICD-9 | Other persistent mental disorders due to conditions classified elsewhere | 2 |
| `29570` | ICD-9 | Schizoaffective disorder, unspecified | 2 |
| `29574` | ICD-9 | Schizoaffective disorder, chronic with acute exacerbation | 2 |
| `29624` | ICD-9 | Major depressive affective disorder, single episode, severe, specified as with psychotic behavior | 2 |
| `29633` | ICD-9 | Major depressive affective disorder, recurrent episode, severe, without mention of psychotic behavior | 2 |
| `29640` | ICD-9 | Bipolar I disorder, most recent episode (or current) manic, unspecified | 2 |
| `3071` | ICD-9 | Anorexia nervosa | 2 |
| `F250` | ICD-10 | Schizoaffective disorder, bipolar type | 2 |
| `F29` | ICD-10 | Unspecified psychosis not due to a substance or known physiological condition | 2 |
| `F319` | ICD-10 | Bipolar disorder, unspecified | 2 |
| `F339` | ICD-10 | Major depressive disorder, recurrent, unspecified | 2 |
| `F458` | ICD-10 | Other somatoform disorders | 2 |
| `29281` | ICD-9 | Drug-induced delirium | 1 |
| `29284` | ICD-9 | Drug-induced mood disorder | 1 |
| `29514` | ICD-9 | Disorganized type schizophrenia, chronic with acute exacerbation | 1 |
| `29622` | ICD-9 | Major depressive affective disorder, single episode, moderate | 1 |
| `29632` | ICD-9 | Major depressive affective disorder, recurrent episode, moderate | 1 |
| `29634` | ICD-9 | Major depressive affective disorder, recurrent episode, severe, specified as with psychotic behavior | 1 |
| `29635` | ICD-9 | Major depressive affective disorder, recurrent episode, in partial or unspecified remission | 1 |
| `29643` | ICD-9 | Bipolar I disorder, most recent episode (or current) manic, severe, without mention of psychotic behavior | 1 |
| `29650` | ICD-9 | Bipolar I disorder, most recent episode (or current) depressed, unspecified | 1 |
| `3004` | ICD-9 | Dysthymic disorder | 1 |
| `3017` | ICD-9 | Antisocial personality disorder | 1 |
| `30500` | ICD-9 | Alcohol abuse, unspecified | 1 |
| `3094` | ICD-9 | Adjustment disorder with mixed disturbance of emotions and conduct | 1 |
| `F0391` | ICD-10 | Unspecified dementia, unspecified severity, with behavioral disturbance | 1 |
| `F10129` | ICD-10 | Alcohol abuse with intoxication, unspecified | 1 |
| `F10231` | ICD-10 | Alcohol dependence with withdrawal delirium | 1 |
| `F1114` | ICD-10 | Opioid abuse with opioid-induced mood disorder | 1 |
| `F1914` | ICD-10 | Other psychoactive substance abuse with psychoactive substance-induced mood disorder | 1 |
| `F200` | ICD-10 | Paranoid schizophrenia | 1 |
| `F202` | ICD-10 | Catatonic schizophrenia | 1 |
| `F209` | ICD-10 | Schizophrenia, unspecified | 1 |
| `F259` | ICD-10 | Schizoaffective disorder, unspecified | 1 |
| `F3113` | ICD-10 | Bipolar disorder, current episode manic without psychotic features, severe | 1 |
| `F3181` | ICD-10 | Bipolar II disorder | 1 |
| `F322` | ICD-10 | Major depressive disorder, single episode, severe without psychotic features | 1 |
| `F329` | ICD-10 | Major depressive disorder, single episode, unspecified | 1 |
| `F39` | ICD-10 | Unspecified mood [affective] disorder | 1 |
| `F410` | ICD-10 | Panic disorder [episodic paroxysmal anxiety] | 1 |
| `F419` | ICD-10 | Anxiety disorder, unspecified | 1 |
| `F4310` | ICD-10 | Post-traumatic stress disorder, unspecified | 1 |
| `F5001` | ICD-10 | Anorexia nervosa, restricting type | 1 |

### Infectious and parasitic diseases  
*35 codes, 89 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `A419` | ICD-10 | Sepsis, unspecified organism | 18 |
| `0389` | ICD-9 | Unspecified septicemia | 14 |
| `00845` | ICD-9 | Intestinal infection due to Clostridium difficile | 6 |
| `0380` | ICD-9 | Streptococcal septicemia | 4 |
| `03842` | ICD-9 | Septicemia due to escherichia coli [E. coli] | 4 |
| `A4151` | ICD-10 | Sepsis due to Escherichia coli [E. coli] | 4 |
| `A4189` | ICD-10 | Other specified sepsis | 4 |
| `0090` | ICD-9 | Infectious colitis, enteritis, and gastroenteritis | 2 |
| `03811` | ICD-9 | Methicillin susceptible Staphylococcus aureus septicemia | 2 |
| `03812` | ICD-9 | Methicillin resistant Staphylococcus aureus septicemia | 2 |
| `0479` | ICD-9 | Unspecified viral meningitis | 2 |
| `08881` | ICD-9 | Lyme Disease | 2 |
| `A408` | ICD-10 | Other streptococcal sepsis | 2 |
| `A4181` | ICD-10 | Sepsis due to Enterococcus | 2 |
| `0020` | ICD-9 | Typhoid fever | 1 |
| `00843` | ICD-9 | Intestinal infection due to campylobacter | 1 |
| `0088` | ICD-9 | Intestinal infection due to other organism, not elsewhere classified | 1 |
| `0310` | ICD-9 | Pulmonary diseases due to other mycobacteria | 1 |
| `03843` | ICD-9 | Septicemia due to pseudomonas | 1 |
| `03849` | ICD-9 | Other septicemia due to gram-negative organisms | 1 |
| `042` | ICD-9 | Human immunodeficiency virus [HIV] disease | 1 |
| `0529` | ICD-9 | Varicella without mention of complication | 1 |
| `0539` | ICD-9 | Herpes zoster without mention of complication | 1 |
| `0661` | ICD-9 | Tick-borne fever | 1 |
| `0949` | ICD-9 | Neurosyphilis, unspecified | 1 |
| `0979` | ICD-9 | Syphilis, unspecified | 1 |
| `11284` | ICD-9 | Candidal esophagitis | 1 |
| `A021` | ICD-10 | Salmonella sepsis | 1 |
| `A4101` | ICD-10 | Sepsis due to Methicillin susceptible Staphylococcus aureus | 1 |
| `A4159` | ICD-10 | Other Gram-negative sepsis | 1 |
| `A5149` | ICD-10 | Other secondary syphilitic conditions | 1 |
| `A849` | ICD-10 | Tick-borne viral encephalitis, unspecified | 1 |
| `B029` | ICD-10 | Zoster without complications | 1 |
| `B04` | ICD-10 | Monkeypox | 1 |
| `B2709` | ICD-10 | Gammaherpesviral mononucleosis with other complications | 1 |

### Diseases of the genitourinary system  
*37 codes, 81 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `5990` | ICD-9 | Urinary tract infection, site not specified | 13 |
| `5849` | ICD-9 | Acute kidney failure, unspecified | 11 |
| `N179` | ICD-10 | Acute kidney failure, unspecified | 8 |
| `5921` | ICD-9 | Calculus of ureter | 5 |
| `N390` | ICD-10 | Urinary tract infection, site not specified | 5 |
| `5920` | ICD-9 | Calculus of kidney | 3 |
| `5845` | ICD-9 | Acute kidney failure with lesion of tubular necrosis | 2 |
| `60001` | ICD-9 | Hypertrophy (benign) of prostate with urinary obstruction and other lower urinary tract symptoms (LUTS) | 2 |
| `6200` | ICD-9 | Follicular cyst of ovary | 2 |
| `N12` | ICD-10 | Tubulo-interstitial nephritis, not specified as acute or chronic | 2 |
| `N401` | ICD-10 | Benign prostatic hyperplasia with lower urinary tract symptoms | 2 |
| `5934` | ICD-9 | Other ureteric obstruction | 1 |
| `5961` | ICD-9 | Intestinovesical fistula | 1 |
| `6010` | ICD-9 | Acute prostatitis | 1 |
| `60490` | ICD-9 | Orchitis and epididymitis, unspecified | 1 |
| `6111` | ICD-9 | Hypertrophy of breast | 1 |
| `6120` | ICD-9 | Deformity of reconstructed breast | 1 |
| `6142` | ICD-9 | Salpingitis and oophoritis not specified as acute, subacute, or chronic | 1 |
| `61801` | ICD-9 | Cystocele, midline | 1 |
| `6185` | ICD-9 | Prolapse of vaginal vault after hysterectomy | 1 |
| `61889` | ICD-9 | Other specified genital prolapse | 1 |
| `6210` | ICD-9 | Polyp of corpus uteri | 1 |
| `62135` | ICD-9 | Endometrial intraepithelial neoplasia [EIN] | 1 |
| `6253` | ICD-9 | Dysmenorrhea | 1 |
| `6262` | ICD-9 | Excessive or frequent menstruation | 1 |
| `N048` | ICD-10 | Nephrotic syndrome with other morphologic changes | 1 |
| `N132` | ICD-10 | Hydronephrosis with renal and ureteral calculous obstruction | 1 |
| `N136` | ICD-10 | Pyonephrosis | 1 |
| `N170` | ICD-10 | Acute kidney failure with tubular necrosis | 1 |
| `N201` | ICD-10 | Calculus of ureter | 1 |
| `N2889` | ICD-10 | Other specified disorders of kidney and ureter | 1 |
| `N492` | ICD-10 | Inflammatory disorders of scrotum | 1 |
| `N710` | ICD-10 | Acute inflammatory disease of uterus | 1 |
| `N800` | ICD-10 | Endometriosis of uterus | 1 |
| `N813` | ICD-10 | Complete uterovaginal prolapse | 1 |
| `N920` | ICD-10 | Excessive and frequent menstruation with regular cycle | 1 |
| `N99840` | ICD-10 | Postprocedural hematoma of a genitourinary system organ or structure following a genitourinary system procedure | 1 |

### Diseases of the respiratory system  
*41 codes, 77 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `486` | ICD-9 | Pneumonia, organism unspecified | 13 |
| `49121` | ICD-9 | Obstructive chronic bronchitis with (acute) exacerbation | 5 |
| `5070` | ICD-9 | Pneumonitis due to inhalation of food or vomitus | 5 |
| `J189` | ICD-10 | Pneumonia, unspecified organism | 5 |
| `51881` | ICD-9 | Acute respiratory failure | 3 |
| `47819` | ICD-9 | Other disease of nasal cavity and sinuses | 2 |
| `4829` | ICD-9 | Bacterial pneumonia, unspecified | 2 |
| `4871` | ICD-9 | Influenza with other respiratory manifestations | 2 |
| `49322` | ICD-9 | Chronic obstructive asthma with (acute) exacerbation | 2 |
| `51181` | ICD-9 | Malignant pleural effusion | 2 |
| `515` | ICD-9 | Postinflammatory pulmonary fibrosis | 2 |
| `51631` | ICD-9 | Idiopathic pulmonary fibrosis | 2 |
| `51889` | ICD-9 | Other diseases of lung, not elsewhere classified | 2 |
| `J439` | ICD-10 | Emphysema, unspecified | 2 |
| `J982` | ICD-10 | Interstitial emphysema | 2 |
| `4660` | ICD-9 | Acute bronchitis | 1 |
| `49390` | ICD-9 | Asthma, unspecified type, unspecified | 1 |
| `49392` | ICD-9 | Asthma, unspecified type, with (acute) exacerbation | 1 |
| `5110` | ICD-9 | Pleurisy without mention of effusion or current tuberculosis | 1 |
| `5119` | ICD-9 | Unspecified pleural effusion | 1 |
| `5120` | ICD-9 | Spontaneous tension pneumothorax | 1 |
| `5121` | ICD-9 | Iatrogenic pneumothorax | 1 |
| `51883` | ICD-9 | Chronic respiratory failure | 1 |
| `51884` | ICD-9 | Acute and chronic respiratory failure | 1 |
| `J0100` | ICD-10 | Acute maxillary sinusitis, unspecified | 1 |
| `J1008` | ICD-10 | Influenza due to other identified influenza virus with other specified pneumonia | 1 |
| `J101` | ICD-10 | Influenza due to other identified influenza virus with other respiratory manifestations | 1 |
| `J1082` | ICD-10 | Influenza due to other identified influenza virus with myocarditis | 1 |
| `J13` | ICD-10 | Pneumonia due to Streptococcus pneumoniae | 1 |
| `J441` | ICD-10 | Chronic obstructive pulmonary disease with (acute) exacerbation | 1 |
| `J45901` | ICD-10 | Unspecified asthma with (acute) exacerbation | 1 |
| `J45909` | ICD-10 | Unspecified asthma, uncomplicated | 1 |
| `J8410` | ICD-10 | Pulmonary fibrosis, unspecified | 1 |
| `J853` | ICD-10 | Abscess of mediastinum | 1 |
| `J90` | ICD-10 | Pleural effusion, not elsewhere classified | 1 |
| `J9381` | ICD-10 | Chronic pneumothorax | 1 |
| `J9382` | ICD-10 | Other air leak | 1 |
| `J939` | ICD-10 | Pneumothorax, unspecified | 1 |
| `J9503` | ICD-10 | Malfunction of tracheostomy stoma | 1 |
| `J9601` | ICD-10 | Acute respiratory failure with hypoxia | 1 |
| `J9622` | ICD-10 | Acute and chronic respiratory failure with hypercapnia | 1 |

### Endocrine, nutritional and metabolic diseases  
*36 codes, 71 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `E6601` | ICD-10 | Morbid (severe) obesity due to excess calories | 11 |
| `27801` | ICD-9 | Morbid obesity | 7 |
| `E1010` | ICD-10 | Type 1 diabetes mellitus with ketoacidosis without coma | 6 |
| `E1151` | ICD-10 | Type 2 diabetes mellitus with diabetic peripheral angiopathy without gangrene | 5 |
| `25013` | ICD-9 | Diabetes with ketoacidosis, type I [juvenile type], uncontrolled | 3 |
| `2761` | ICD-9 | Hyposmolality and/or hyponatremia | 3 |
| `E222` | ICD-10 | Syndrome of inappropriate secretion of antidiuretic hormone | 3 |
| `2411` | ICD-9 | Nontoxic multinodular goiter | 2 |
| `25080` | ICD-9 | Diabetes with other specified manifestations, type II or unspecified type, not stated as uncontrolled | 2 |
| `27651` | ICD-9 | Dehydration | 2 |
| `2767` | ICD-9 | Hyperpotassemia | 2 |
| `24201` | ICD-9 | Toxic diffuse goiter with mention of thyrotoxic crisis or storm | 1 |
| `24290` | ICD-9 | Thyrotoxicosis without mention of goiter or other cause, and without mention of thyrotoxic crisis or storm | 1 |
| `24900` | ICD-9 | Secondary diabetes mellitus without mention of complication, not stated as uncontrolled, or unspecified | 1 |
| `25012` | ICD-9 | Diabetes with ketoacidosis, type II or unspecified type, uncontrolled | 1 |
| `25040` | ICD-9 | Diabetes with renal manifestations, type II or unspecified type, not stated as uncontrolled | 1 |
| `25060` | ICD-9 | Diabetes with neurological manifestations, type II or unspecified type, not stated as uncontrolled | 1 |
| `25062` | ICD-9 | Diabetes with neurological manifestations, type II or unspecified type, uncontrolled | 1 |
| `25072` | ICD-9 | Diabetes with peripheral circulatory disorders, type II or unspecified type, uncontrolled | 1 |
| `25082` | ICD-9 | Diabetes with other specified manifestations, type II or unspecified type, uncontrolled | 1 |
| `25201` | ICD-9 | Primary hyperparathyroidism | 1 |
| `2536` | ICD-9 | Other disorders of neurohypophysis | 1 |
| `2631` | ICD-9 | Malnutrition of mild degree | 1 |
| `27542` | ICD-9 | Hypercalcemia | 1 |
| `27652` | ICD-9 | Hypovolemia | 1 |
| `2768` | ICD-9 | Hypopotassemia | 1 |
| `27800` | ICD-9 | Obesity, unspecified | 1 |
| `E1042` | ICD-10 | Type 1 diabetes mellitus with diabetic polyneuropathy | 1 |
| `E1110` | ICD-10 | Type 2 diabetes mellitus with ketoacidosis without coma | 1 |
| `E1122` | ICD-10 | Type 2 diabetes mellitus with diabetic chronic kidney disease | 1 |
| `E1152` | ICD-10 | Type 2 diabetes mellitus with diabetic peripheral angiopathy with gangrene | 1 |
| `E11649` | ICD-10 | Type 2 diabetes mellitus with hypoglycemia without coma | 1 |
| `E1165` | ICD-10 | Type 2 diabetes mellitus with hyperglycemia | 1 |
| `E162` | ICD-10 | Hypoglycemia, unspecified | 1 |
| `E43` | ICD-10 | Unspecified severe protein-calorie malnutrition | 1 |
| `E65` | ICD-10 | Localized adiposity | 1 |

### Diseases of the nervous system and sense organs  
*45 codes, 63 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `3241` | ICD-9 | Intraspinal abscess | 4 |
| `3310` | ICD-9 | Alzheimer's disease | 3 |
| `34590` | ICD-9 | Epilepsy, unspecified, without mention of intractable epilepsy | 3 |
| `G20` | ICD-10 | Parkinson's disease | 3 |
| `33818` | ICD-9 | Other acute postoperative pain | 2 |
| `3383` | ICD-9 | Neoplasm related pain (acute) (chronic) | 2 |
| `34982` | ICD-9 | Toxic encephalopathy | 2 |
| `3510` | ICD-9 | Bell's palsy | 2 |
| `38612` | ICD-9 | Vestibular neuronitis | 2 |
| `G40209` | ICD-10 | Localization-related (focal) (partial) symptomatic epilepsy and epileptic syndromes with complex partial seizures, not intractable, without status epilepticus | 2 |
| `G40401` | ICD-10 | Other generalized epilepsy and epileptic syndromes, not intractable, with status epilepticus | 2 |
| `G40909` | ICD-10 | Epilepsy, unspecified, not intractable, without status epilepticus | 2 |
| `G92` | ICD-10 | Toxic encephalopathy | 2 |
| `325` | ICD-9 | Phlebitis and thrombophlebitis of intracranial venous sinuses | 1 |
| `33182` | ICD-9 | Dementia with lewy bodies | 1 |
| `3321` | ICD-9 | Secondary parkinsonism | 1 |
| `33390` | ICD-9 | Unspecified extrapyramidal disease and abnormal movement disorder | 1 |
| `34500` | ICD-9 | Generalized nonconvulsive epilepsy, without mention of intractable epilepsy | 1 |
| `34550` | ICD-9 | Localization-related (focal) (partial) epilepsy and epileptic syndromes with simple partial seizures, without mention of intractable epilepsy | 1 |
| `34620` | ICD-9 | Variants of migraine, not elsewhere classified, without mention of intractable migraine without mention of status migrainosus | 1 |
| `3480` | ICD-9 | Cerebral cysts | 1 |
| `34839` | ICD-9 | Other encephalopathy | 1 |
| `3490` | ICD-9 | Reaction to spinal or lumbar puncture | 1 |
| `3543` | ICD-9 | Lesion of radial nerve | 1 |
| `3569` | ICD-9 | Unspecified hereditary and idiopathic peripheral neuropathy | 1 |
| `3570` | ICD-9 | Acute infective polyneuritis | 1 |
| `35781` | ICD-9 | Chronic inflammatory demyelinating polyneuritis | 1 |
| `3599` | ICD-9 | Myopathy, unspecified | 1 |
| `3682` | ICD-9 | Diplopia | 1 |
| `37630` | ICD-9 | Exophthalmos, unspecified | 1 |
| `38611` | ICD-9 | Benign paroxysmal positional vertigo | 1 |
| `3868` | ICD-9 | Other disorders of labyrinth | 1 |
| `G061` | ICD-10 | Intraspinal abscess and granuloma | 1 |
| `G312` | ICD-10 | Degeneration of nervous system due to alcohol | 1 |
| `G371` | ICD-10 | Central demyelination of corpus callosum | 1 |
| `G40109` | ICD-10 | Localization-related (focal) (partial) symptomatic epilepsy and epileptic syndromes with simple partial seizures, not intractable, without status epilepticus | 1 |
| `G4089` | ICD-10 | Other seizures | 1 |
| `G40901` | ICD-10 | Epilepsy, unspecified, not intractable, with status epilepticus | 1 |
| `G510` | ICD-10 | Bell's palsy | 1 |
| `G610` | ICD-10 | Guillain-Barre syndrome | 1 |
| `G6289` | ICD-10 | Other specified polyneuropathies | 1 |
| `G911` | ICD-10 | Obstructive hydrocephalus | 1 |
| `G935` | ICD-10 | Compression of brain | 1 |
| `G9389` | ICD-10 | Other specified disorders of brain | 1 |
| `H8301` | ICD-10 | Labyrinthitis, right ear | 1 |

### Symptoms, signs and abnormal clinical findings  
*34 codes, 61 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `78659` | ICD-9 | Other chest pain | 10 |
| `7802` | ICD-9 | Syncope and collapse | 9 |
| `78060` | ICD-9 | Fever, unspecified | 4 |
| `78039` | ICD-9 | Other convulsions | 2 |
| `78097` | ICD-9 | Altered mental status | 2 |
| `7856` | ICD-9 | Enlargement of lymph nodes | 2 |
| `7907` | ICD-9 | Bacteremia | 2 |
| `79092` | ICD-9 | Abnormal coagulation profile | 2 |
| `R55` | ICD-10 | Syncope and collapse | 2 |
| `R7881` | ICD-10 | Bacteremia | 2 |
| `7804` | ICD-9 | Dizziness and giddiness | 1 |
| `7812` | ICD-9 | Abnormality of gait | 1 |
| `78194` | ICD-9 | Facial weakness | 1 |
| `7820` | ICD-9 | Disturbance of skin sensation | 1 |
| `7823` | ICD-9 | Edema | 1 |
| `7837` | ICD-9 | Adult failure to thrive | 1 |
| `78442` | ICD-9 | Dysphonia | 1 |
| `7854` | ICD-9 | Gangrene | 1 |
| `78650` | ICD-9 | Chest pain, unspecified | 1 |
| `78651` | ICD-9 | Precordial pain | 1 |
| `78701` | ICD-9 | Nausea with vomiting | 1 |
| `78720` | ICD-9 | Dysphagia, unspecified | 1 |
| `78791` | ICD-9 | Diarrhea | 1 |
| `78829` | ICD-9 | Other specified retention of urine | 1 |
| `78902` | ICD-9 | Abdominal pain, left upper quadrant | 1 |
| `78907` | ICD-9 | Abdominal pain, generalized | 1 |
| `79439` | ICD-9 | Other nonspecific abnormal results of function study of cardiovascular system | 1 |
| `R109` | ICD-10 | Unspecified abdominal pain | 1 |
| `R188` | ICD-10 | Other ascites | 1 |
| `R1909` | ICD-10 | Other intra-abdominal and pelvic swelling, mass and lump | 1 |
| `R319` | ICD-10 | Hematuria, unspecified | 1 |
| `R569` | ICD-10 | Unspecified convulsions | 1 |
| `R911` | ICD-10 | Solitary pulmonary nodule | 1 |
| `R918` | ICD-10 | Other nonspecific abnormal finding of lung field | 1 |

### Diseases of the skin and subcutaneous tissue  
*17 codes, 30 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `6826` | ICD-9 | Cellulitis and abscess of leg, except foot | 8 |
| `6823` | ICD-9 | Cellulitis and abscess of upper arm and forearm | 4 |
| `6822` | ICD-9 | Cellulitis and abscess of trunk | 2 |
| `6824` | ICD-9 | Cellulitis and abscess of hand, except fingers and thumb | 2 |
| `6827` | ICD-9 | Cellulitis and abscess of foot, except toes | 2 |
| `6820` | ICD-9 | Cellulitis and abscess of face | 1 |
| `6825` | ICD-9 | Cellulitis and abscess of buttock | 1 |
| `6930` | ICD-9 | Dermatitis due to drugs and medicines taken internally | 1 |
| `70583` | ICD-9 | Hidradenitis | 1 |
| `70706` | ICD-9 | Pressure ulcer, ankle | 1 |
| `70724` | ICD-9 | Pressure ulcer, stage IV | 1 |
| `7092` | ICD-9 | Scar conditions and fibrosis of skin | 1 |
| `L02413` | ICD-10 | Cutaneous abscess of right upper limb | 1 |
| `L02612` | ICD-10 | Cutaneous abscess of left foot | 1 |
| `L03113` | ICD-10 | Cellulitis of right upper limb | 1 |
| `L03115` | ICD-10 | Cellulitis of right lower limb | 1 |
| `L732` | ICD-10 | Hidradenitis suppurativa | 1 |

### Factors influencing health status and contact with health services  
*7 codes, 15 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `Z5111` | ICD-10 | Encounter for antineoplastic chemotherapy | 5 |
| `V707` | ICD-9 | Examination of participant in clinical trial | 3 |
| `Z432` | ICD-10 | Encounter for attention to ileostomy | 3 |
| `V071` | ICD-9 | Need for desensitization to allergens | 1 |
| `Z421` | ICD-10 | Encounter for breast reconstruction following mastectomy | 1 |
| `Z4733` | ICD-10 | Aftercare following explantation of knee joint prosthesis | 1 |
| `Z5112` | ICD-10 | Encounter for antineoplastic immunotherapy | 1 |

### Diseases of the blood and immune mechanism  
*11 codes, 14 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `28800` | ICD-9 | Neutropenia, unspecified | 2 |
| `D62` | ICD-10 | Acute posthemorrhagic anemia | 2 |
| `D6832` | ICD-10 | Hemorrhagic disorder due to extrinsic circulating anticoagulants | 2 |
| `2851` | ICD-9 | Acute posthemorrhagic anemia | 1 |
| `28529` | ICD-9 | Anemia of other chronic disease | 1 |
| `2875` | ICD-9 | Thrombocytopenia, unspecified | 1 |
| `D500` | ICD-10 | Iron deficiency anemia secondary to blood loss (chronic) | 1 |
| `D61818` | ICD-10 | Other pancytopenia | 1 |
| `D619` | ICD-10 | Aplastic anemia, unspecified | 1 |
| `D693` | ICD-10 | Immune thrombocytopenic purpura | 1 |
| `D709` | ICD-10 | Neutropenia, unspecified | 1 |

### Congenital malformations and chromosomal abnormalities  
*9 codes, 11 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `Q231` | ICD-10 | Congenital insufficiency of aortic valve | 3 |
| `7455` | ICD-9 | Ostium secundum type atrial septal defect | 1 |
| `75162` | ICD-9 | Congenital cystic disease of liver | 1 |
| `75612` | ICD-9 | Spondylolisthesis | 1 |
| `Q018` | ICD-10 | Encephalocele of other sites | 1 |
| `Q211` | ICD-10 | Atrial septal defect | 1 |
| `Q244` | ICD-10 | Congenital subaortic stenosis | 1 |
| `Q2739` | ICD-10 | Arteriovenous malformation, other site | 1 |
| `Q341` | ICD-10 | Congenital cyst of mediastinum | 1 |

### Codes for special purposes, including COVID-19  
*1 codes, 11 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `U071` | ICD-10 | COVID-19 | 11 |

### External causes of morbidity  
*6 codes, 6 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `E854` | ICD-9 | Organ-limited amyloidosis | 1 |
| `E871` | ICD-9 | Hypo-osmolality and hyponatremia | 1 |
| `E872` | ICD-9 | Acidosis | 1 |
| `E875` | ICD-9 | Hyperkalemia | 1 |
| `E8881` | ICD-9 | Metabolic syndrome | 1 |
| `V5841` | ICD-10 | Encounter for planned post-operative wound closure | 1 |

### Not coded  
*1 codes, 3 patients*

| ICD code | Ver | Diagnosis | Patients |
|---|---|---|---:|
| `—` | — | Diagnosis not coded | 3 |

## Secondary diagnoses (titles only, no codes stored)

1,869 distinct titles across the three secondaries kept per patient.

| Diagnosis | Patients |
|---|---:|
| Acute kidney failure, unspecified | 142 |
| Unspecified essential hypertension | 119 |
| Acute posthemorrhagic anemia | 99 |
| Essential (primary) hypertension | 94 |
| Urinary tract infection, site not specified | 76 |
| Other and unspecified hyperlipidemia | 63 |
| Single live birth | 62 |
| Acidosis | 46 |
| Atrial fibrillation | 43 |
| Diabetes mellitus without mention of complication, type II or unspecified type, not stated as uncontrolled | 41 |
| Hyperlipidemia, unspecified | 39 |
| Cerebral edema | 37 |
| Congestive heart failure, unspecified | 37 |
| Coronary atherosclerosis of native coronary artery | 37 |
| Acute respiratory failure | 36 |
| Acute respiratory failure with hypoxia | 36 |
| End stage renal disease | 35 |
| Pneumonia, organism unspecified | 35 |
| Outcome of delivery, single liveborn | 31 |
| Esophageal reflux | 27 |
| Unspecified acquired hypothyroidism | 26 |
| Pneumonia, unspecified organism | 25 |
| Severe sepsis with septic shock | 25 |
| Contact with and (suspected) exposure to COVID-19 | 25 |
| Hyposmolality and/or hyponatremia | 24 |
| Chronic systolic heart failure | 24 |
| Hypo-osmolality and hyponatremia | 23 |
| Obesity, unspecified | 23 |
| Asthma, unspecified type, unspecified | 23 |
| Obstruction of bile duct | 21 |
| Thrombocytopenia, unspecified | 21 |
| Hypotension, unspecified | 21 |
| Anemia, unspecified | 20 |
| Tobacco use disorder | 19 |
| Chronic diastolic heart failure | 19 |
| Unspecified severe protein-calorie malnutrition | 19 |
| Toxic encephalopathy | 18 |
| Type 2 diabetes mellitus without complications | 18 |
| Acute on chronic diastolic (congestive) heart failure | 18 |
| Atherosclerotic heart disease of native coronary artery without angina pectoris | 17 |
| Gastro-esophageal reflux disease without esophagitis | 17 |
| Depressive disorder, not elsewhere classified | 17 |
| Suicidal ideation | 17 |
| Chronic airway obstruction, not elsewhere classified | 16 |
| Obstructive sleep apnea (adult) (pediatric) | 16 |
| Personal history of nicotine dependence | 16 |
| Anxiety state, unspecified | 16 |
| Pure hypercholesterolemia | 16 |
| Chronic systolic (congestive) heart failure | 15 |
| Delirium due to conditions classified elsewhere | 15 |
| Metabolic encephalopathy | 15 |
| Body mass index [BMI] 40.0-44.9, adult | 15 |
| Atrial flutter | 15 |
| Intermediate coronary syndrome | 15 |
| Chronic diastolic (congestive) heart failure | 14 |
| Acute on chronic diastolic heart failure | 14 |
| Fall from other slipping, tripping, or stumbling | 14 |
| Human immunodeficiency virus [HIV] disease | 14 |
| Hypertensive chronic kidney disease, unspecified, with chronic kidney disease stage V or end stage renal disease | 14 |
| Septic shock | 14 |
| Second-degree perineal laceration, delivered, with or without mention of antepartum condition | 14 |
| Other primary cardiomyopathies | 14 |
| Aphasia | 14 |
| 40 weeks gestation of pregnancy | 14 |
| Unspecified pleural effusion | 13 |
| Major depressive disorder, single episode, unspecified | 13 |
| Pneumonitis due to inhalation of food and vomit | 13 |
| Personal history of malignant neoplasm of breast | 13 |
| Anxiety disorder, unspecified | 12 |
| Other immediate postpartum hemorrhage | 12 |
| 39 weeks gestation of pregnancy | 12 |
| Hypothyroidism, unspecified | 12 |
| Unspecified protein-calorie malnutrition | 12 |
| Hypertensive chronic kidney disease, unspecified, with chronic kidney disease stage I through stage IV, or unspecified | 12 |
| Unspecified asthma, uncomplicated | 12 |
| Cardiogenic shock | 11 |
| Chronic obstructive pulmonary disease, unspecified | 11 |
| Hypertensive heart and chronic kidney disease with heart failure and stage 1 through stage 4 chronic kidney disease, or unspecified chronic kidney disease | 11 |
| Secondary malignant neoplasm of lung | 11 |
| Secondary malignant neoplasm of bone and bone marrow | 11 |
| Bacteremia | 11 |
| Unspecified fall | 11 |
| Suicidal ideations | 11 |
| Streptococcus B carrier state complicating childbirth | 11 |
| Dehydration | 11 |
| Malignant neoplasm of liver, secondary | 10 |
| Myocardial infarction type 2 | 10 |
| Acute on chronic systolic heart failure | 10 |
| Paroxysmal ventricular tachycardia | 10 |
| Compression of brain | 10 |
| Pneumonitis due to inhalation of food or vomitus | 10 |
| Delirium due to known physiological condition | 10 |
| Encephalopathy, unspecified | 10 |
| Sepsis, unspecified organism | 10 |
| Obstructive sleep apnea (adult)(pediatric) | 10 |
| Hypertensive heart disease with heart failure | 10 |
| Elderly multigravida, delivered with or without mention of antepartum condition | 9 |
| Atelectasis | 9 |
| Other specified surgical operations and procedures causing abnormal patient reaction, or later complication, without mention of misadventure at time of operation | 9 |
| Abnormality in fetal heart rate and rhythm complicating labor and delivery | 9 |
| Morbid obesity | 9 |
| Intestinal infection due to Clostridium difficile | 9 |
| Hyperosmolality and/or hypernatremia | 9 |
| Peritoneal adhesions (postoperative) (postinfection) | 9 |
| Acute kidney failure with tubular necrosis | 9 |
| Other ascites | 9 |
| Pressure ulcer, lower back | 9 |
| Acute kidney failure with lesion of tubular necrosis | 9 |
| Chronic kidney disease, Stage IV (severe) | 9 |
| Peritoneal abscess | 9 |
| Respiratory failure, unspecified with hypoxia | 9 |
| Regional enteritis of unspecified site | 9 |
| Migraine, unspecified, without mention of intractable migraine without mention of status migrainosus | 9 |
| Other specified cardiac dysrhythmias | 8 |
| Acquired coagulation factor deficiency | 8 |
| Asymptomatic human immunodeficiency virus [HIV] infection status | 8 |
| Cirrhosis of liver without mention of alcohol | 8 |
| Traumatic subdural hemorrhage without loss of consciousness, initial encounter | 8 |
| Polyneuropathy in diabetes | 8 |
| Iron deficiency anemia, unspecified | 8 |
| Opioid dependence, uncomplicated | 8 |
| Encounter for immunization | 8 |
| Chorioamnionitis, third trimester, not applicable or unspecified | 8 |
| Second degree perineal laceration during delivery | 8 |
| Old myocardial infarction | 8 |
| Ostium secundum type atrial septal defect | 8 |
| Other shock | 8 |
| Paralytic ileus | 8 |
| Other viral pneumonia | 8 |
| Ventricular tachycardia | 8 |
| Constipation, unspecified | 8 |
| Multiple sclerosis | 8 |
| COVID-19 | 7 |
| Intracerebral hemorrhage | 7 |
| Accidental fall on or from other stairs or steps | 7 |
| Cardiac complications, not elsewhere classified | 7 |
| Nutritional marasmus | 7 |
| Migraine, unspecified, not intractable, without status migrainosus | 7 |
| Nicotine dependence, cigarettes, uncomplicated | 7 |
| Secondary and unspecified malignant neoplasm of intra-abdominal lymph nodes | 7 |
| Hydronephrosis | 7 |
| Other disorders of neurohypophysis | 7 |
| 38 weeks gestation of pregnancy | 7 |
| Other pulmonary embolism and infarction | 7 |
| Subendocardial infarction, initial episode of care | 7 |
| Alcohol abuse, unspecified | 7 |
| Retention of urine, unspecified | 7 |
| Bariatric surgery status | 7 |
| Acute on chronic systolic (congestive) heart failure | 7 |
| Alcoholic cirrhosis of liver | 7 |
| Other infections with a predominantly sexual mode of transmission complicating childbirth | 7 |
| Polyneuropathy, unspecified | 7 |
| Other current conditions classifiable elsewhere of mother, delivered, with or without mention of antepartum condition | 7 |
| Other pancytopenia | 7 |
| Body mass index [BMI] 50.0-59.9, adult | 7 |
| Mitral valve disorders | 7 |
| Hypovolemia | 7 |
| Early onset of delivery, delivered, with or without mention of antepartum condition | 7 |
| Unspecified atrial fibrillation | 7 |
| Jaundice, unspecified, not of newborn | 7 |
| Body mass index [BMI] 45.0-49.9, adult | 7 |
| Ulcer of heel and midfoot | 7 |
| Portal vein thrombosis | 6 |
| Pleural effusion, not elsewhere classified | 6 |
| Cholangitis | 6 |
| Unspecified septicemia | 6 |
| Other surgical procedures as the cause of abnormal reaction of the patient, or of later complication, without mention of misadventure at the time of the procedure | 6 |
| Alcohol withdrawal | 6 |
| Sepsis | 6 |
| Contusion of lung without mention of open wound into thorax | 6 |
| Methicillin resistant Staphylococcus aureus in conditions classified elsewhere and of unspecified site | 6 |
| Age-related osteoporosis without current pathological fracture | 6 |
| Ileus, unspecified | 6 |
| Chronic kidney disease, Stage III (moderate) | 6 |
| Spinal stenosis, cervical region | 6 |
| Paralysis agitans | 6 |
| Acute and chronic respiratory failure with hypoxia | 6 |
| Atrioventricular block, complete | 6 |
| Systemic lupus erythematosus | 6 |
| Aortocoronary bypass status | 6 |
| Hemorrhage complicating a procedure | 6 |
| Secondary malignant neoplasm of liver and intrahepatic bile duct | 6 |
| Chronic kidney disease, stage 4 (severe) | 6 |
| First degree perineal laceration during delivery | 6 |
| Fatty (change of) liver, not elsewhere classified | 6 |
| Atherosclerotic heart disease of native coronary artery with unstable angina pectoris | 6 |
| Blood in stool | 6 |
| 37 weeks gestation of pregnancy | 6 |
| Crohn's disease, unspecified, without complications | 6 |
| Pulmonary collapse | 6 |
| Primary hypercoagulable state | 6 |
| Hemiplegia, unspecified affecting left nondominant side | 6 |
| Labor and delivery complicated by meconium in amniotic fluid | 6 |
| Organ-limited amyloidosis | 6 |
| Ulcer of other part of foot | 6 |
| Other chronic pulmonary heart diseases | 6 |
| Type 2 diabetes mellitus with diabetic chronic kidney disease | 6 |
| Other chest pain | 5 |
| Multiple myeloma not having achieved remission | 5 |
| Iron deficiency anemia secondary to blood loss (chronic) | 5 |
| Abscess of liver | 5 |
| Other chronic nonalcoholic liver disease | 5 |
| Hypertensive chronic kidney disease with stage 1 through stage 4 chronic kidney disease, or unspecified chronic kidney disease | 5 |
| Acute pulmonary edema | 5 |
| Labor and delivery complicated by cord around neck, without compression, not applicable or unspecified | 5 |
| Unspecified viral infection | 5 |
| Other and unspecified angina pectoris | 5 |
| Secondary malignant neoplasm of other specified sites | 5 |
| Tachycardia, unspecified | 5 |
| Secondary malignant neoplasm of brain and spinal cord | 5 |
| Personal history of other malignant neoplasm of skin | 5 |
| Closed fracture of pubis | 5 |
| Other and unspecified alcohol dependence, continuous | 5 |
| Hepatorenal syndrome | 5 |
| Personal history of tobacco use | 5 |
| Other encephalopathy | 5 |
| Rhabdomyolysis | 5 |
| Unspecified atrial flutter | 5 |
| Other amyloidosis | 5 |
| Hypertensive chronic kidney disease with stage 5 chronic kidney disease or end stage renal disease | 5 |
| Long-term (current) use of insulin | 5 |
| Severe sepsis | 5 |
| Syncope and collapse | 5 |
| Chronic combined systolic and diastolic heart failure | 5 |
| Type 2 diabetes mellitus with hyperglycemia | 5 |
| Other disorders of phosphorus metabolism | 5 |
| Acute and subacute necrosis of liver | 5 |
| Other postoperative infection | 5 |
| Heart failure, unspecified | 5 |
| Long-term (current) use of anticoagulants | 5 |
| Accidents occurring in unspecified place | 5 |
| Moderate protein-calorie malnutrition | 5 |
| Acute pancreatitis | 5 |
| Body Mass Index less than 19, adult | 5 |
| Hemiplegia, unspecified affecting right dominant side | 5 |
| Acute respiratory failure following trauma and surgery | 5 |
| Ulcerative colitis, unspecified | 5 |
| Aortic valve disorders | 5 |
| Bipolar disorder, unspecified | 5 |
| Diabetes mellitus without mention of complication, type I [juvenile type], not stated as uncontrolled | 5 |
| Dizziness and giddiness | 5 |
| Other convulsions | 5 |
| Surgical operation with implant of artificial internal device causing abnormal patient reaction, or later complication,without mention of misadventure at time of operation | 5 |
| Obstructive hydrocephalus | 5 |
| Syndrome of inappropriate secretion of antidiuretic hormone | 5 |
| Chronic kidney disease, unspecified | 5 |
| Irritable bowel syndrome | 5 |
| Cachexia | 5 |
| Portal hypertension | 5 |
| Personal history of other venous thrombosis and embolism | 5 |
| Cellulitis and abscess of trunk | 5 |
| Morbid (severe) obesity due to excess calories | 5 |
| Other, mixed, or unspecified drug abuse, unspecified | 4 |
| Injury to bladder and urethra, without mention of open wound into cavity | 4 |
| Congenital insufficiency of aortic valve | 4 |
| Hypertensive heart and chronic kidney disease with heart failure and with stage 5 chronic kidney disease, or end stage renal disease | 4 |
| Other dependence on machines, supplemental oxygen | 4 |
| Acute alcoholic intoxication in alcoholism, continuous | 4 |
| Diseases of the nervous system complicating childbirth | 4 |
| Traumatic pneumothorax without mention of open wound into thorax | 4 |
| Closed fracture of multiple ribs, unspecified | 4 |
| Hypovolemic shock | 4 |
| Supraventricular tachycardia | 4 |
| Chronic lymphoid leukemia, without mention of having achieved remission | 4 |
| Personal history of pulmonary embolism | 4 |
| Other viral diseases complicating childbirth | 4 |
| Personal history of COVID-19 | 4 |
| Secondary malignant neoplasm of retroperitoneum and peritoneum | 4 |
| Infection of amniotic cavity, delivered, with or without mention of antepartum condition | 4 |
| Cellulitis and abscess of leg, except foot | 4 |
| Long-term (current) use of aspirin | 4 |
| Insomnia, unspecified | 4 |
| Shock, unspecified | 4 |
| Other specified noninflammatory disorders of uterus | 4 |
| Secondary malignant neoplasm of bone | 4 |
| Acute and subacute bacterial endocarditis | 4 |
| Non-ST elevation (NSTEMI) myocardial infarction | 4 |
| Other pulmonary embolism without acute cor pulmonale | 4 |
| Other cholangitis | 4 |
| Hypopotassemia | 4 |
| Cerebral artery occlusion, unspecified with cerebral infarction | 4 |
| Hyperpotassemia | 4 |
| Epilepsy, unspecified, not intractable, without status epilepticus | 4 |
| Mental disorders of mother, delivered, with or without mention of antepartum condition | 4 |
| Leukocytosis, unspecified | 4 |
| Acute respiratory failure, unspecified whether with hypoxia or hypercapnia | 4 |
| Chronic total occlusion of coronary artery | 4 |
| Other digestive system complications | 4 |
| Chronic pancreatitis | 4 |
| Closed fracture of lumbar vertebra without mention of spinal cord injury | 4 |
| Contact with and (suspected) exposure to other viral communicable diseases | 4 |
| Permanent atrial fibrillation | 4 |
| Carrier or suspected carrier of group B streptococcus | 4 |
| Dysthymic disorder | 4 |
| Cervical spondylosis with myelopathy | 4 |
| Alkalosis | 4 |
| Body Mass Index 40.0-44.9, adult | 4 |
| Pancytopenia | 4 |
| Rheumatoid arthritis | 4 |
| Other complications due to other cardiac device, implant, and graft | 4 |
| Myasthenia gravis without (acute) exacerbation | 4 |
| Other accidental fall from one level to another | 4 |
| Long term (current) use of anticoagulants | 4 |
| Unspecified dementia, unspecified severity, without behavioral disturbance, psychotic disturbance, mood disturbance, and anxiety | 4 |
| Body Mass Index 40 and over, adult | 4 |
| Unspecified bacterial pneumonia | 4 |
| Other alteration of consciousness | 4 |
| Lumbosacral spondylosis without myelopathy | 4 |
| Open wound of forehead, without mention of complication | 4 |
| Other acute and subacute forms of ischemic heart disease, other | 4 |
| Pulmonary insufficiency following trauma and surgery | 4 |
| Diabetes with neurological manifestations, type II or unspecified type, not stated as uncontrolled | 4 |
| Spontaneous bacterial peritonitis | 4 |
| Diverticulosis of colon (without mention of hemorrhage) | 4 |
| Headache | 4 |
| Post-term pregnancy | 4 |
| Ventricular fibrillation | 4 |
| Nonalcoholic steatohepatitis (NASH) | 4 |
| Paroxysmal atrial fibrillation | 4 |
| Other postprocedural status | 4 |
| Chronic atrial fibrillation | 3 |
| Cardiac arrest | 3 |
| Escherichia coli [E. coli] infection in conditions classified elsewhere and of unspecified site | 3 |
| Malignant neoplasm of other parts of bronchus or lung | 3 |
| Leiomyoma of uterus, unspecified | 3 |
| Thyroid dysfunction of mother, delivered, with or without mention of antepartum condition | 3 |
| Long term (current) use of insulin | 3 |
| Candidal stomatitis | 3 |
| Unspecified vitamin D deficiency | 3 |
| Unspecified Escherichia coli [E. coli] as the cause of diseases classified elsewhere | 3 |
| Secondary malignant neoplasm of genital organs | 3 |
| Closed fracture of orbital floor (blow-out) | 3 |
| Cocaine dependence, continuous | 3 |
| Closed fracture of acetabulum | 3 |
| Abnormal glucose tolerance of mother, delivered, with or without mention of antepartum condition | 3 |
| Other mental disorders complicating childbirth | 3 |
| Accidental fall on or from sidewalk curb | 3 |
| Cannabis abuse, unspecified | 3 |
| Anomalies of pancreas | 3 |
| Hypogammaglobulinemia, unspecified | 3 |
| Liver transplant status | 3 |
| Other and unspecified cord entanglement, without mention of compression, complicating labor and delivery, delivered, with or without mention of antepartum condition | 3 |
| Abnormality in fetal heart rate or rhythm, delivered, with or without mention of antepartum condition | 3 |
| Acute and chronic respiratory failure with hypercapnia | 3 |
| Closed fracture of one rib | 3 |
| Cardiac tamponade | 3 |
| Major depressive affective disorder, single episode, unspecified | 3 |
| Diseases of the respiratory system complicating childbirth | 3 |
| Hyperparathyroidism, unspecified | 3 |
| Dependence on supplemental oxygen | 3 |
| Cervicalgia | 3 |
| Personal history of non-Hodgkin lymphomas | 3 |
| Unarmed fight or brawl | 3 |
| Respiratory failure, unspecified with hypercapnia | 3 |
| Malignant neoplasm of upper lobe, bronchus or lung | 3 |
| Unspecified viral hepatitis C without hepatic coma | 3 |
| Endocrine, nutritional and metabolic diseases complicating childbirth | 3 |
| Lack of housing | 3 |
| Diaphragmatic hernia without obstruction or gangrene | 3 |
| Need for prophylactic vaccination and inoculation against influenza | 3 |
| Other specified complications of pregnancy, delivered, with or without mention of antepartum condition | 3 |
| Traumatic pneumohemothorax without mention of open wound into thorax | 3 |
| Subarachnoid hemorrhage | 3 |
| Unspecified osteomyelitis, ankle and foot | 3 |
| Unspecified intestinal obstruction | 3 |
| Personal history of suicidal behavior | 3 |
| Laparoscopic surgical procedure converted to open procedure | 3 |
| Infection and inflammatory reaction due to other internal orthopedic device, implant, and graft | 3 |
| Other secondary thrombocytopenia | 3 |
| Urinary complications, not elsewhere classified | 3 |
| Personal history of noncompliance with medical treatment, presenting hazards to health | 3 |
| Eosinophilia | 3 |
| Unspecified pre-existing hypertension complicating childbirth | 3 |
| Stem cells transplant status | 3 |
| Calculus of gallbladder without mention of cholecystitis, without mention of obstruction | 3 |
| Calculus of kidney | 3 |
| Chronic kidney disease, stage 3 (moderate) | 3 |
| Personal history of malignant melanoma of skin | 3 |
| Hypertrophy (benign) of prostate without urinary obstruction and other lower urinary tract symptom (LUTS) | 3 |
| Late effect of fracture of upper extremities | 3 |
| Accidental puncture or laceration of dura during a procedure | 3 |
| Calculus of gallbladder with other cholecystitis, without mention of obstruction | 3 |
| Coronary artery dissection | 3 |
| Unspecified gastritis and gastroduodenitis, without mention of hemorrhage | 3 |
| Chronic viral hepatitis B without mention of hepatic coma without mention of hepatitis delta | 3 |
| Methicillin susceptible Staphylococcus aureus in conditions classified elsewhere and of unspecified site | 3 |
| Diabetes with ketoacidosis, type II or unspecified type, uncontrolled | 3 |
| Peritoneal adhesions (postprocedural) (postinfection) | 3 |
| Unspecified diastolic (congestive) heart failure | 3 |
| Dementia, unspecified, without behavioral disturbance | 3 |
| Acute systolic heart failure | 3 |
| Cerebral atherosclerosis | 3 |
| Acute diastolic heart failure | 3 |
| Arthropathy, unspecified, site unspecified | 3 |
| Obesity complicating childbirth | 3 |
| Disorder of bone and cartilage, unspecified | 3 |
| Acute venous embolism and thrombosis of deep vessels of proximal lower extremity | 3 |
| Subdural hemorrhage | 3 |
| Kidney transplant status | 3 |
| Obesity hypoventilation syndrome | 3 |
| Body Mass Index 50.0-59.9, adult | 3 |
| Paraplegia | 3 |
| Rupture of chordae tendineae, not elsewhere classified | 3 |
| Other immediate postpartum hemorrhage, delivered, with mention of postpartum complication | 3 |
| Anemia of mother, delivered, with mention of postpartum complication | 3 |
| Other chronic pain | 3 |
| Abscess of intestine | 3 |
| Opioid type dependence, continuous | 3 |
| Diabetes mellitus of mother, complicating pregnancy, childbirth, or the puerperium, delivered, with or without mention of antepartum condition | 3 |
| Other forms of acute ischemic heart disease | 3 |
| Unspecified glaucoma | 3 |
| Personal history of malignant neoplasm of large intestine | 3 |
| Pure hypercholesterolemia, unspecified | 3 |
| Chronic obstructive asthma, unspecified | 3 |
| Unspecified osteoarthritis, unspecified site | 3 |
| Generalized anxiety disorder | 3 |
| Peripheral autonomic neuropathy in disorders classified elsewhere | 3 |
| Home accidents | 3 |
| Other diseases of lung, not elsewhere classified | 3 |
| Hemoptysis | 3 |
| Personal history of malignant neoplasm of kidney | 3 |
| Open wound of scalp, without mention of complication | 3 |
| Immune thrombocytopenic purpura | 3 |
| Other specified intestinal obstruction | 3 |
| Facial weakness | 3 |
| Hemiplegia and hemiparesis following cerebral infarction affecting right dominant side | 3 |
| Precipitous drop in hematocrit | 3 |
| Hemiplegia, unspecified, affecting unspecified side | 3 |
| Fever, unspecified | 3 |
| Other postprocedural complications and disorders of the circulatory system, not elsewhere classified | 3 |
| Kidney replaced by transplant | 3 |
| Tobacco use | 3 |
| Cord around neck, with compression, complicating labor and delivery, delivered, with or without mention of antepartum condition | 3 |
| Other postprocedural shock, initial encounter | 3 |
| Barrett's esophagus | 3 |
| Unspecified place in unspecified non-institutional (private) residence as the place of occurrence of the external cause | 3 |
| Pneumonia due to coronavirus disease 2019 | 3 |
| Osteoporosis, unspecified | 3 |
| Gangrene | 3 |
| Other complications due to other vascular device, implant, and graft | 3 |
| Personal history of other malignant neoplasm of kidney | 3 |
| Anorexia | 3 |
| Hemiplegia, unspecified, affecting dominant side | 3 |
| Ulcerative colitis, unspecified, without complications | 3 |
| Peripheral vascular disease, unspecified | 3 |
| Motor vehicle traffic accident involving collision with pedestrian injuring pedestrian | 3 |
| Oliguria and anuria | 3 |
| Umbilical hernia without mention of obstruction or gangrene | 3 |
| Pulmonary hypertension, unspecified | 3 |
| Acquired absence of breast and nipple | 3 |
| Other specified diseases of pancreas | 3 |
| Premature rupture of membranes, delivered, with or without mention of antepartum condition | 3 |
| Esophageal varices in diseases classified elsewhere, without mention of bleeding | 3 |
| Family history of ischemic heart disease | 3 |
| Borderline personality disorder | 3 |
| Acute vascular insufficiency of intestine | 3 |
| Cardiomyopathy, unspecified | 3 |
| Malignant neoplasm of brain, unspecified | 3 |
| Gestational diabetes mellitus in childbirth, insulin controlled | 3 |
| Malignant neoplasm of breast (female), unspecified | 3 |
| Post-traumatic stress disorder, unspecified | 3 |
| Vitamin D deficiency, unspecified | 3 |
| Localization-related (focal) (partial) epilepsy and epileptic syndromes with simple partial seizures, without mention of intractable epilepsy | 3 |
| Personal history of malignant neoplasm of prostate | 3 |
| Polymyalgia rheumatica | 2 |
| Opioid abuse, unspecified | 2 |
| Cocaine abuse, unspecified | 2 |
| Anesthesia of skin | 2 |
| Premature separation of placenta, unspecified, third trimester | 2 |
| Other specified coagulation defects | 2 |
| Atherosclerotic heart disease of native coronary artery with other forms of angina pectoris | 2 |
| Ischemic cardiomyopathy | 2 |
| Abrasion or friction burn of face, neck, and scalp except eye, without mention of infection | 2 |
| Chronic atrial fibrillation, unspecified | 2 |
| Postsurgical hypothyroidism | 2 |
| Secondary malignant neoplasm of brain | 2 |
| Chronic hepatitis C with hepatic coma | 2 |
| Body mass index [BMI] 60.0-69.9, adult | 2 |
| Myelopathy in other diseases classified elsewhere | 2 |
| Closed fracture of two ribs | 2 |
| Acute pyelonephritis | 2 |
| Nontoxic multinodular goiter | 2 |
| Anuria and oliguria | 2 |
| Fetopelvic disproportion, delivered, with or without mention of antepartum condition | 2 |
| Acute cholecystitis | 2 |
| Accidents occurring in other specified places | 2 |
| Unspecified analgesic and antipyretic causing adverse effects in therapeutic use | 2 |
| Secondary and unspecified malignant neoplasm of intrapelvic lymph nodes | 2 |
| Enterocolitis due to Clostridium difficile, not specified as recurrent | 2 |
| Parastomal hernia without obstruction or gangrene | 2 |
| Osteophyte, vertebrae | 2 |
| Diabetes mellitus without mention of complication, type II or unspecified type, uncontrolled | 2 |
| Celiac disease | 2 |
| Pulmonary congestion and hypostasis | 2 |
| Other pulmonary insufficiency, not elsewhere classified, following trauma and surgery | 2 |
| Hypocalcemia | 2 |
| Acute on chronic combined systolic (congestive) and diastolic (congestive) heart failure | 2 |
| Sixth or abducens nerve palsy | 2 |
| Other postprocedural cardiac functional disturbances following cardiac surgery | 2 |
| Gout, unspecified | 2 |
| Alcohol dependence with withdrawal, unspecified | 2 |
| Acquired hypertrophic pyloric stenosis | 2 |
| Pericardial effusion (noninflammatory) | 2 |
| Cervical disc disorder with myelopathy, high cervical region | 2 |
| Other and unspecified alcohol dependence, episodic | 2 |
| Chronic vascular insufficiency of intestine | 2 |
| Attention-deficit hyperactivity disorder, unspecified type | 2 |
| Personal history of self-harm | 2 |
| 41 weeks gestation of pregnancy | 2 |
| Cellulitis of left lower limb | 2 |
| Maternal care for cervical incompetence, third trimester | 2 |
| Unspecified psychosis | 2 |
| Chronic obstructive pulmonary disease with (acute) exacerbation | 2 |
| Type 2 diabetes mellitus with diabetic polyneuropathy | 2 |
| Chronic viral hepatitis B without delta-agent | 2 |
| Bloodstream infection due to central venous catheter, initial encounter | 2 |
| Pyelonephritis, unspecified | 2 |
| Unilateral paralysis of vocal cords or larynx, partial | 2 |
| Unspecified place or not applicable | 2 |
| Closed fracture of nasal bones | 2 |
| Dysphagia, unspecified | 2 |
| Other spondylosis with myelopathy, cervical region | 2 |
| Peripheral vascular complications, not elsewhere classified | 2 |
| Benign prostatic hyperplasia without lower urinary tract symptoms | 2 |
| Family history of malignant neoplasm of digestive organs | 2 |
| Postprocedural hypothyroidism | 2 |
| Primary pulmonary hypertension | 2 |
| Swelling of limb | 2 |
| Maternal care for unspecified type scar from previous cesarean delivery | 2 |
| Other fall on same level, initial encounter | 2 |
| Malignant neoplasm of prostate | 2 |
| Backache, unspecified | 2 |
| Scoliosis [and kyphoscoliosis], idiopathic | 2 |
| Other specified complications of labor and delivery | 2 |
| Late effects of motor vehicle accident | 2 |
| Alcoholic hepatitis without ascites | 2 |
| Non-pressure chronic ulcer of left heel and midfoot with unspecified severity | 2 |
| Helicobacter pylori [H. pylori] | 2 |
| Transient hypertension of pregnancy, delivered , with or without mention of antepartum condition | 2 |
| Other specified places as the place of occurrence of the external cause | 2 |
| Spinal stenosis, lumbar region, without neurogenic claudication | 2 |
| Intervertebral disc disorders with radiculopathy, lumbar region | 2 |
| Stress incontinence, female | 2 |
| Ulcer of other part of lower limb | 2 |
| Dementia in conditions classified elsewhere without behavioral disturbance | 2 |
| Mixed acid-base balance disorder | 2 |
| Chronic and other pulmonary manifestations due to radiation | 2 |
| Obstructive hypertrophic cardiomyopathy | 2 |
| Labor and delivery complicated by other cord complications, not applicable or unspecified | 2 |
| Essential and other specified forms of tremor | 2 |
| Acute (reversible) ischemia of intestine, part and extent unspecified | 2 |
| Diabetes insipidus | 2 |
| Ulcer of ankle | 2 |
| Acute osteomyelitis, lower leg | 2 |
| Non-healing surgical wound | 2 |
| Other specified disorders of kidney and ureter | 2 |
| Secondary and unspecified malignant neoplasm of intrathoracic lymph nodes | 2 |
| Sickle-cell trait | 2 |
| Cardiac catheterization as the cause of abnormal reaction of patient, or of later complication, without mention of misadventure at time of procedure | 2 |
| Localization-related (focal) (partial) symptomatic epilepsy and epileptic syndromes with complex partial seizures, not intractable, without status epilepticus | 2 |
| Other fall | 2 |
| Antineoplastic chemotherapy induced pancytopenia | 2 |
| Migraine with aura, without mention of intractable migraine without mention of status migrainosus | 2 |
| Dementia with lewy bodies | 2 |
| Occlusion and stenosis of multiple and bilateral precerebral arteries without mention of cerebral infarction | 2 |
| Oligohydramnios, delivered, with or without mention of antepartum condition | 2 |
| Breech presentation without mention of version, delivered, with or without mention of antepartum condition | 2 |
| Other specified diseases of gallbladder | 2 |
| Chronic viral hepatitis C | 2 |
| Neoplasm related pain (acute) (chronic) | 2 |
| Subacute cutaneous lupus erythematosus | 2 |
| Glomerular disease in systemic lupus erythematosus | 2 |
| Other forms of epilepsy and recurrent seizures, without mention of intractable epilepsy | 2 |
| Anomalies of cerebrovascular system | 2 |
| Acute systolic (congestive) heart failure | 2 |
| Malignant neoplasm of upper lobe, right bronchus or lung | 2 |
| Primary sclerosing cholangitis | 2 |
| Mucositis (ulcerative) due to antineoplastic therapy | 2 |
| Type 2 diabetes mellitus with hypoglycemia without coma | 2 |
| Von Willebrand disease | 2 |
| Other chronic pancreatitis | 2 |
| Long term (current) use of antithrombotics/antiplatelets | 2 |
| Enlargement of lymph nodes | 2 |
| Attention deficit disorder without mention of hyperactivity | 2 |
| Polymyositis | 2 |
| Traumatic subarachnoid hemorrhage with loss of consciousness of unspecified duration, initial encounter | 2 |
| Malignant pleural effusion | 2 |
| Pressure ulcer, buttock | 2 |
| Obesity complicating pregnancy, childbirth, or the puerperium, delivered, with or without mention of antepartum condition | 2 |
| Other optic neuritis | 2 |
| Disruption of internal operation (surgical) wound, not elsewhere classified, initial encounter | 2 |
| Candidiasis of other urogenital sites | 2 |
| Diabetes with renal manifestations, type II or unspecified type, uncontrolled | 2 |
| Diabetes with ophthalmic manifestations, type II or unspecified type, uncontrolled | 2 |
| Compression of vein | 2 |
| Sterilization | 2 |
| Atrial septal defect | 2 |
| Personal history of peptic ulcer disease | 2 |
| Unspecified visual disturbance | 2 |
| Encounter for examination for normal comparison and control in clinical research program | 2 |
| Late effect of intracranial injury without mention of skull fracture | 2 |
| Chronic osteomyelitis, ankle and foot | 2 |
| Pressure ulcer of sacral region, stage 4 | 2 |
| Other acute kidney failure | 2 |
| Malignant neoplasm of lower lobe, bronchus or lung | 2 |
| Other ill-defined cerebrovascular disease | 2 |
| Homelessness | 2 |
| Acute edema of lung, unspecified | 2 |
| Excessive or frequent menstruation | 2 |
| Opioid dependence with withdrawal | 2 |
| Pressure ulcer of sacral region, stage 3 | 2 |
| Other respiratory abnormalities | 2 |
| Other postablative hypothyroidism | 2 |
| Malignant ascites | 2 |
| Cerebral embolism with cerebral infarction | 2 |
| Septic pulmonary embolism | 2 |
| Allergic rhinitis, unspecified | 2 |
| Type 1 diabetes mellitus with diabetic autonomic (poly)neuropathy | 2 |
| Gastroparesis | 2 |
| Acute (reversible) ischemia of small intestine, extent unspecified | 2 |
| Sarcoidosis | 2 |
| Closed fracture of metatarsal bone(s) | 2 |
| Body mass index [BMI] 19.9 or less, adult | 2 |
| Percutaneous transluminal coronary angioplasty status | 2 |
| Other toxic encephalopathy | 2 |
| Hypokalemia | 2 |
| Calculus of bile duct without mention of cholecystitis, without mention of obstruction | 2 |
| Edema | 2 |
| Other nonspecific findings on examination of urine | 2 |
| Other and unspecified anticonvulsants causing adverse effects in therapeutic use | 2 |
| Surgical operation with anastomosis, bypass, or graft, with natural or artificial tissues used as implant causing abnormal patient reaction, or later complication, without mention of misadventure at time of operation | 2 |
| Contusion of face, scalp, and neck except eye(s) | 2 |
| Infection following a procedure, other surgical site, initial encounter | 2 |
| Pleural effusion in other conditions classified elsewhere | 2 |
| Pure hyperglyceridemia | 2 |
| Other specified diseases of anus and rectum | 2 |
| Spondylolisthesis, lumbar region | 2 |
| Presence of coronary angioplasty implant and graft | 2 |
| Cerebral infarction due to embolism of bilateral cerebellar arteries | 2 |
| Examination of participant in clinical trial | 2 |
| Other disorders of lung | 2 |
| Obstructive chronic bronchitis with (acute) exacerbation | 2 |
| Hematoma complicating a procedure | 2 |
| Pathologic fracture of vertebrae | 2 |
| Elderly primigravida, delivered, with or without mention of antepartum condition | 2 |
| Disruption of external operation (surgical) wound | 2 |
| Personal history of other malignant neoplasm of large intestine | 2 |
| Late effects of accidental fall | 2 |
| Alcohol abuse, in remission | 2 |
| Infection and inflammatory reaction due to indwelling urethral catheter, initial encounter | 2 |
| Other specified complication of cardiac prosthetic devices, implants and grafts, initial encounter | 2 |
| Other late effects of cerebrovascular disease | 2 |
| Anoxic brain damage, not elsewhere classified | 2 |
| Restless legs syndrome (RLS) | 2 |
| Atherosclerotic heart disease of native coronary artery with unspecified angina pectoris | 2 |
| Intrahepatic bile duct carcinoma | 2 |
| Secondary malignant neoplasm of adrenal gland | 2 |
| Occlusion and stenosis of carotid artery without mention of cerebral infarction | 2 |
| Hereditary hemolytic anemia, unspecified | 2 |
| Chronic lymphocytic leukemia of B-cell type not having achieved remission | 2 |
| Cellulitis and abscess of foot, except toes | 2 |
| Dysarthria | 2 |
| Secondary malignant neoplasm of other digestive organs | 2 |
| Hepatic encephalopathy | 2 |
| Adult hypertrophic pyloric stenosis | 2 |
| Polycystic kidney, unspecified type | 2 |
| Asthma, unspecified type, with (acute) exacerbation | 2 |
| Vomiting alone | 2 |
| Osteoarthrosis, unspecified whether generalized or localized, site unspecified | 2 |
| Nontraumatic intracerebral hemorrhage, unspecified | 2 |
| Alcoholic cirrhosis of liver with ascites | 2 |
| Hepatic failure, unspecified without coma | 2 |
| History of falling | 2 |
| Other spondylosis, cervical region | 2 |
| Perforation of gallbladder | 2 |
| Malignant neoplasm of liver, primary | 2 |
| Bipolar I disorder, most recent episode (or current) depressed, unspecified | 2 |
| Abnormal coagulation profile | 2 |
| Oligohydramnios, third trimester, not applicable or unspecified | 2 |
| Personal history of irradiation | 2 |
| Hemoperitoneum (nontraumatic) | 2 |
| Unspecified convulsions | 2 |
| Chronic hepatitis C without mention of hepatic coma | 2 |
| Pneumonia due to other Gram-negative bacteria | 2 |
| Assault by cutting and piercing instrument | 2 |
| Quadriplegia, unspecified | 2 |
| Body mass index [BMI] 39.0-39.9, adult | 2 |
| Previous cesarean delivery, delivered, with or without mention of antepartum condition | 2 |
| Hydrocephalus, unspecified | 2 |
| Maternal pyrexia during labor, unspecified, delivered, with or without mention of antepartum condition | 2 |
| Neurologic neglect syndrome | 2 |
| Nausea alone | 2 |
| Personal history of transient ischemic attack (TIA), and cerebral infarction without residual deficits | 2 |
| Anemia in neoplastic disease | 2 |
| Twin pregnancy, delivered, with or without mention of antepartum condition | 2 |
| Other persistent atrial fibrillation | 2 |
| Viral hepatitis B without mention of hepatic coma, acute or unspecified, without mention of hepatitis delta | 2 |
| Posttraumatic stress disorder | 2 |
| Other musculoskeletal symptoms referable to limbs | 2 |
| Other and unspecified alcohol dependence, unspecified | 2 |
| Anemia complicating childbirth | 2 |
| Nontoxic uninodular goiter | 2 |
| Guillain-Barre syndrome | 2 |
| Accidents occurring in residential institution | 2 |
| Nontraumatic chronic subdural hemorrhage | 2 |
| Herpesviral infection, unspecified | 2 |
| Postinflammatory pulmonary fibrosis | 2 |
| Amniotic fluid embolism in childbirth | 2 |
| Congenital deficiency of other clotting factors | 2 |
| Alcohol abuse, uncomplicated | 2 |
| Other secondary pulmonary hypertension | 2 |
| Diseases of tricuspid valve | 2 |
| Diabetes with renal manifestations, type II or unspecified type, not stated as uncontrolled | 2 |
| Eating disorder, unspecified | 2 |
| Personal history of other diseases of the circulatory system | 2 |
| Empyema without mention of fistula | 2 |
| Methicillin susceptible Staphylococcus aureus septicemia | 2 |
| Other specified diseases and conditions complicating pregnancy, childbirth and the puerperium | 2 |
| Stenosis of coronary artery stent, initial encounter | 2 |
| Hepatitis, unspecified | 2 |
| Suicide and self-inflicted poisoning by analgesics, antipyretics, and antirheumatics | 2 |
| Nonrheumatic aortic (valve) stenosis | 2 |
| Malignant neoplasm of rectosigmoid junction | 2 |
| Enterocolitis due to Clostridium difficile | 2 |
| Body Mass Index 45.0-49.9, adult | 2 |
| Other and unspecified coagulation defects | 2 |
| Iatrogenic pulmonary embolism and infarction | 2 |
| Supervision of elderly multigravida, third trimester | 2 |
| Ileostomy status | 2 |
| Presence of aortocoronary bypass graft | 2 |
| Other cardiomyopathies | 2 |
| Other closed fractures of distal end of radius (alone) | 2 |
| Lack of coordination | 2 |
| Homicidal ideation | 2 |
| Communicating hydrocephalus | 2 |
| Hyperosmolality and hypernatremia | 2 |
| Acute upper respiratory infection, unspecified | 2 |
| Nausea with vomiting | 2 |
| Traumatic shock, initial encounter | 2 |
| Cannabis use, unspecified, uncomplicated | 2 |
| Cellulitis and abscess of face | 2 |
| Anemia in other chronic diseases classified elsewhere | 2 |
| Leukocytopenia, unspecified | 2 |
| Coronary atherosclerosis of autologous vein bypass graft | 2 |
| Cyst and pseudocyst of pancreas | 2 |
| Secondary and unspecified malignant neoplasm of lymph nodes of axilla and upper limb | 2 |
| Coronary atherosclerosis of unspecified type of vessel, native or graft | 2 |
| Atherosclerosis of native arteries of the extremities with ulceration | 2 |
| Diarrhea | 2 |
| Localized adiposity | 2 |
| Acute postprocedural respiratory failure | 2 |
| Closed fracture of dorsal [thoracic] vertebra without mention of spinal cord injury | 2 |
| Parkinson's disease | 2 |
| Ventilator associated pneumonia | 2 |
| Surgical procedure, unspecified as the cause of abnormal reaction of the patient, or of later complication, without mention of misadventure at the time of the procedure | 2 |
| Dementia in conditions classified elsewhere with behavioral disturbance | 2 |
| Delusional disorders | 2 |
| Nausea | 2 |
| Type 2 diabetes mellitus with diabetic neuropathy, unspecified | 2 |
| Anemia of mother, delivered, with or without mention of antepartum condition | 2 |
| Obstructive chronic bronchitis without exacerbation | 2 |
| Acquired absence of intestine (large) (small) | 2 |
| Acquired absence of other specified parts of digestive tract | 2 |
| Osteoarthrosis, localized, not specified whether primary or secondary, pelvic region and thigh | 2 |
| Cellulitis and abscess of mouth | 2 |
| Hypoxemia | 2 |
| Liver cell carcinoma | 2 |
| Fluid overload, unspecified | 2 |
| Radiculopathy, cervical region | 2 |
| Antirheumatics [antiphlogistics] causing adverse effects in therapeutic use | 2 |
| Other motor vehicle traffic accident involving collision with motor vehicle injuring driver of motor vehicle other than motorcycle | 2 |
| Acute venous embolism and thrombosis of deep vessels of distal lower extremity | 2 |
| Other shock without mention of trauma | 2 |
| NIHSS score 0 | 1 |
| Traumatic subdural hemorrhage with loss of consciousness of unspecified duration, subsequent encounter | 1 |
| Twin pregnancy, dichorionic/diamniotic, third trimester | 1 |
| Twins, both liveborn | 1 |
| Traumatic compartment syndrome of left lower extremity, initial encounter | 1 |
| Unspecified fracture of shaft of left fibula, initial encounter for closed fracture | 1 |
| Cerebral infarction due to embolism of unspecified cerebral artery | 1 |
| Acute and subacute hepatic failure without coma | 1 |
| Type 1 diabetes mellitus with ketoacidosis without coma | 1 |
| Presence of insulin pump (external) (internal) | 1 |
| Pathological fracture, pelvis, initial encounter for fracture | 1 |
| Abdominal aneurysm without mention of rupture | 1 |
| Retained cholelithiasis following cholecystectomy | 1 |
| Transient visual loss | 1 |
| Malignant neoplasm of bone and articular cartilage, unspecified | 1 |
| Arthrodesis status | 1 |
| Type 2 diabetes mellitus with diabetic nephropathy | 1 |
| Closed fracture of base of skull with subarachnoid, subdural, and extradural hemorrhage, with loss of consciousness of unspecified duration | 1 |
| Closed fracture of unspecified part of fibula with tibia | 1 |
| Acute alcoholic intoxication in alcoholism, unspecified | 1 |
| Pneumonia due to Methicillin resistant Staphylococcus aureus | 1 |
| Personal history of other malignant neoplasm of bronchus and lung | 1 |
| Personal history of malignant neoplasm of soft tissue | 1 |
| Personal history of venous thrombosis and embolism | 1 |
| Vascular disorder of intestine, unspecified | 1 |
| Obstruction by bony pelvis during labor, delivered, with or without mention of antepartum condition | 1 |
| Long term (current) use of oral hypoglycemic drugs | 1 |
| Conjunctival hemorrhage, left eye | 1 |
| Atherosclerosis of autologous vein coronary artery bypass graft(s) with unspecified angina pectoris | 1 |
| Other malformation of placenta, third trimester | 1 |
| Personal history of other complications of pregnancy, childbirth and the puerperium | 1 |
| Other specified sepsis | 1 |
| Paraplegia, unspecified | 1 |
| Other postprocedural complications and disorders of nervous system | 1 |
| Activities involving roller skating (inline) and skateboarding | 1 |
| Exposure to other specified factors, subsequent encounter | 1 |
| Malignant neoplasm of stomach, unspecified site | 1 |
| Acquired absence of organ, stomach | 1 |
| Chronic or unspecified gastric ulcer with hemorrhage, without mention of obstruction | 1 |
| Age-related osteoporosis with current pathological fracture, other site, initial encounter for fracture | 1 |
| Presence of right artificial knee joint | 1 |
| Secondary malignant neoplasm of right ovary | 1 |
| Unspecified hydronephrosis | 1 |
| Toxic myopathy | 1 |
| Gestational diabetes mellitus in childbirth, diet controlled | 1 |
| Lyme disease, unspecified | 1 |
| Third [oculomotor] nerve palsy, unspecified eye | 1 |
| Other dysphagia | 1 |
| Assault by unspecified means | 1 |
| Nonspecific elevation of levels of transaminase or lactic acid dehydrogenase [LDH] | 1 |
| Nausea with vomiting, unspecified | 1 |
| Other vitamin B12 deficiency anemia | 1 |
| Inclusion body myositis | 1 |
| Underdosing of other antipsychotics and neuroleptics, initial encounter | 1 |
| Patient's intentional underdosing of medication regimen for other reason | 1 |
| Unspecified place in other non-institutional residence as the place of occurrence of the external cause | 1 |
| Type 1 diabetes mellitus with hyperglycemia | 1 |
| Diplopia | 1 |
| High vaginal laceration, delivered, with or without mention of antepartum condition | 1 |
| Other selective immunoglobulin deficiencies | 1 |
| Unspecified fracture of upper end of left humerus, initial encounter for closed fracture | 1 |
| Burkitt lymphoma, lymph nodes of head, face, and neck | 1 |
| Cerebrospinal fluid leak from spinal puncture | 1 |
| Unspecified fall, initial encounter | 1 |
| Late effect of burn of other extremities | 1 |
| Delayed delivery after spontaneous or unspecified rupture of membranes, delivered, with or without mention of antepartum condition | 1 |
| Other specified trauma to perineum and vulva, delivered, with or without mention of antepartum condition | 1 |
| Other motor vehicle nontraffic accident while boarding and alighting injuring motorcyclist | 1 |
| Polyhydramnios, third trimester, not applicable or unspecified | 1 |
| Osteonecrosis, unspecified | 1 |
| Other acute osteomyelitis, left ankle and foot | 1 |
| Unspecified drug or medicinal substance causing adverse effects in therapeutic use | 1 |
| Retropharyngeal and parapharyngeal abscess | 1 |
| Cutaneous abscess of neck | 1 |
| Type 1 diabetes mellitus without complications | 1 |
| Cerebral infarction due to embolism of right posterior cerebral artery | 1 |
| Postprocedural cerebrovascular infarction following cardiac surgery | 1 |
| Pressure ulcer, unspecified stage | 1 |
| Other malignant lymphomas, unspecified site, extranodal and solid organ sites | 1 |
| Thoracic aneurysm without mention of rupture | 1 |
| Sciatica | 1 |
| Collapsed vertebra, not elsewhere classified, cervical region, initial encounter for fracture | 1 |
| Foreign body in larynx | 1 |
| Other diseases of pharynx, not elsewhere classified | 1 |
| Estrogen receptor negative status [ER-] | 1 |
| Infection following a procedure, initial encounter | 1 |
| Other infectious disease | 1 |
| Acquired absence of other genital organ(s) | 1 |
| Dysmenorrhea, unspecified | 1 |
| Amaurosis fugax | 1 |
| Spondylosis without myelopathy or radiculopathy, cervical region | 1 |
| Post term pregnancy, delivered, with or without mention of antepartum condition | 1 |
| First-degree perineal laceration, delivered, with or without mention of antepartum condition | 1 |
| Shortness of breath | 1 |
| Cyst of pancreas | 1 |
| Occlusion and stenosis of unspecified carotid artery | 1 |
| Mental and behavioral disorders associated with the puerperium, not elsewhere classified | 1 |
| Hypothermia, not associated with low environmental temperature | 1 |
| Rheumatic tricuspid insufficiency | 1 |
| Other reduction deformities of brain | 1 |
| Allergic rhinitis, cause unspecified | 1 |
| Closed fracture of sacrum and coccyx without mention of spinal cord injury | 1 |
| Closed fracture of ilium | 1 |
| Cough | 1 |
| Unspecified viral hepatitis C with hepatic coma | 1 |
| Intussusception | 1 |
| Pressure ulcer, stage III | 1 |
| Streptococcus infection in conditions classified elsewhere and of unspecified site, streptococcus, group D [Enterococcus] | 1 |
| Cellulitis of groin | 1 |
| Cutaneous abscess of groin | 1 |
| Malignant neoplasm of vulva, unspecified | 1 |
| Pain in limb | 1 |
| Multiple cranial nerve palsies | 1 |
| Unspecified reduction deformity of lower limb | 1 |
| Long term (current) use of non-steroidal anti-inflammatories (NSAID) | 1 |
| Hydrocele, unspecified | 1 |
| Hypertensive chronic kidney disease, benign, with chronic kidney disease stage V or end stage renal disease | 1 |
| Diverticulitis of colon (without mention of hemorrhage) | 1 |
| Other problems related to lifestyle | 1 |
| Displaced comminuted fracture of shaft of left fibula, initial encounter for closed fracture | 1 |
| Activity, volleyball (beach) (court) | 1 |
| Spina bifida with hydrocephalus, unspecified region | 1 |
| Secondary hypercoagulable state | 1 |
| Unspecified B-cell lymphoma, unspecified site | 1 |
| Other postherpetic nervous system involvement | 1 |
| Other and unspecified alcohol dependence, in remission | 1 |
| Late effect of crushing | 1 |
| Other and unspecified ovarian cyst | 1 |
| Severe pre-eclampsia, third trimester | 1 |
| Maternal care for other rhesus isoimmunization, third trimester, not applicable or unspecified | 1 |
| Preterm premature rupture of membranes, unspecified as to length of time between rupture and onset of labor, third trimester | 1 |
| Syringomyelia and syringobulbia | 1 |
| Umbilical hernia without obstruction or gangrene | 1 |
| Family history of malignant neoplasm of prostate | 1 |
| Schizoaffective disorder, bipolar type | 1 |
| Idiopathic myocarditis | 1 |
| Type 1 diabetes mellitus with diabetic polyneuropathy | 1 |
| Closed fracture of four ribs | 1 |
| Other tear of lateral meniscus, current injury, left knee, initial encounter | 1 |
| Activity, snow (alpine) (downhill) skiing, snowboarding, sledding, tobogganing and snow tubing | 1 |
| External hemorrhoids with other complication | 1 |
| Rectal prolapse | 1 |
| Personal history of physical and sexual abuse in childhood | 1 |
| Adverse effect of selective serotonin reuptake inhibitors, initial encounter | 1 |
| Body Mass Index 37.0-37.9, adult | 1 |
| Acute appendicitis without mention of peritonitis | 1 |
| Elderly multigravida, antepartum condition or complication | 1 |
| Presence of left artificial hip joint | 1 |
| Malignant neoplasm of pancreas, unspecified | 1 |
| Insulin pump status | 1 |
| Other persistent mental disorders due to conditions classified elsewhere | 1 |
| Muscle weakness (generalized) | 1 |
| Other artificial openings of gastrointestinal tract status | 1 |
| Ulcerative (chronic) pancolitis without complications | 1 |
| Hydroureter | 1 |
| Body mass index [BMI] 33.0-33.9, adult | 1 |
| Streptococcus B carrier state complicating pregnancy | 1 |
| Glycogenosis | 1 |
| Other motor vehicle traffic accident involving collision on the highway injuring driver of motor vehicle other than motorcycle | 1 |
| Acute kidney failure with other specified pathological lesion in kidney | 1 |
| Dissection of vertebral artery | 1 |
| Other specified intracranial injury with loss of consciousness of unspecified duration, initial encounter | 1 |
| Transient paralysis | 1 |
| Striking against other object with subsequent fall, initial encounter | 1 |
| Supermarket, store or market as the place of occurrence of the external cause | 1 |
| Other frontotemporal dementia | 1 |
| Unspecified deficiency anemia | 1 |
| Other atopic dermatitis and related conditions | 1 |
| Drug induced fever | 1 |
| Adverse effect of penicillins, initial encounter | 1 |
| Traumatic brain compression without herniation, initial encounter | 1 |
| Traumatic cerebral edema with loss of consciousness of unspecified duration, initial encounter | 1 |
| Car occupant (driver) (passenger) injured in other specified transport accidents, initial encounter | 1 |
| Tracheoesophageal fistula, esophageal atresia and stenosis | 1 |
| Other diseases of the blood and blood-forming organs and certain disorders involving the immune mechanism complicating childbirth | 1 |
| Chronic osteomyelitis, other specified sites | 1 |
| Presence of prosthetic heart valve | 1 |
| Prolonged first stage (of labor) | 1 |
| Orthostatic hypotension | 1 |
| Polycystic kidney, unspecified | 1 |
| Complication of other artery following a procedure, not elsewhere classified, initial encounter | 1 |
| Lichen planus | 1 |
| Wrist drop (acquired) | 1 |
| Dissection of carotid artery | 1 |
| Pedal cycle accident injuring other specified person | 1 |
| Malignant neoplasm of cervical esophagus | 1 |
| Mechanical complication of other vascular device, implant, and graft | 1 |
| Abdominal pain, epigastric | 1 |
| Personal history of hodgkin's disease | 1 |
| Acute pancreatitis without necrosis or infection, unspecified | 1 |
| Dysarthria and anarthria | 1 |
| Other closed fracture of lower end of femur | 1 |
| Closed fracture of sternum | 1 |
| Closed fracture of five ribs | 1 |
| Body Mass Index 70 and over, adult | 1 |
| Pyonephrosis | 1 |
| Displaced fracture of greater trochanter of left femur, initial encounter for closed fracture | 1 |
| Fall from bed, initial encounter | 1 |
| Nondisplaced fracture of left radial styloid process, initial encounter for closed fracture | 1 |
| Malignant neoplasm of lower lobe, right bronchus or lung | 1 |
| Calculus of bile duct with acute cholangitis with obstruction | 1 |
| Acute myeloblastic leukemia, in relapse | 1 |
| Arthropathic psoriasis, unspecified | 1 |
| Postoperative shock, cardiogenic | 1 |
| Thrombosis due to vascular prosthetic devices, implants and grafts, initial encounter | 1 |
| Closed fracture of intertrochanteric section of neck of femur | 1 |
| Hemiplegia and hemiparesis following cerebral infarction affecting left non-dominant side | 1 |
| Supervision of high-risk pregnancy with other poor reproductive history | 1 |
| Bitten by cat, initial encounter | 1 |
| Other acute postoperative pain | 1 |
| Other and unspecified nonspecific immunological findings | 1 |
| Chemical pneumonitis due to anesthesia | 1 |
| Esophageal hemorrhage | 1 |
| Cardiac arrest due to underlying cardiac condition | 1 |
| Periprosthetic fracture around internal prosthetic left hip joint, initial encounter | 1 |
| Body mass index [BMI] 35.0-35.9, adult | 1 |
| Pneumonia due to Streptococcus, group A | 1 |
| Cellulitis and abscess of upper arm and forearm | 1 |
| Infective myositis | 1 |
| Other closed fracture of upper end of humerus | 1 |
| Unspecified personality disorder | 1 |
| Primary biliary cirrhosis | 1 |
| Raynaud's syndrome without gangrene | 1 |
| Peripheral T cell lymphoma, unspecified site, extranodal and solid organ sites | 1 |
| Abscess of prostate | 1 |
| Friedländer's bacillus infection in conditions classified elsewhere and of unspecified site | 1 |
| Unspecified immunity deficiency | 1 |
| Immunodeficiency due to drugs | 1 |
| Acute upper respiratory infections of unspecified site | 1 |
| Unspecified osteomyelitis, shoulder region | 1 |
| Synovitis and tenosynovitis, unspecified | 1 |
| Cerebral aneurysm, nonruptured | 1 |
| Cryptogenic organizing pneumonia | 1 |
| Ulcer of esophagus without bleeding | 1 |
| Chronic pain syndrome | 1 |
| Right upper quadrant pain | 1 |
| Phlebitis and thrombophlebitis of unspecified site | 1 |
| Obstructive chronic bronchitis with acute bronchitis | 1 |
| Other specified disorders of bone density and structure, multiple sites | 1 |
| Gestational diabetes mellitus in the puerperium, diet controlled | 1 |
| Personal history of malignant neoplasm of liver | 1 |
| Body mass index [BMI] 36.0-36.9, adult | 1 |
| First degree atrioventricular block | 1 |
| Right bundle branch block and left anterior fascicular block | 1 |
| Lupus anticoagulant syndrome | 1 |
| Diabetes with neurological manifestations, type II or unspecified type, uncontrolled | 1 |
| Cerebral infarction due to embolism of other cerebral artery | 1 |
| Other malignant lymphomas, intra-abdominal lymph nodes | 1 |
| Drug induced neutropenia | 1 |
| Antineoplastic and immunosuppressive drugs causing adverse effects in therapeutic use | 1 |
| Drug use complicating childbirth | 1 |
| Dependence on respirator, status | 1 |
| Unspecified accident | 1 |
| Systemic inflammatory response syndrome, unspecified | 1 |
| Homonymous bilateral field defects | 1 |
| Vesicointestinal fistula | 1 |
| Chronic or unspecified parametritis and pelvic cellulitis | 1 |
| Encounter for sterilization | 1 |
| Triplet pregnancy, trichorionic/triamniotic, third trimester | 1 |
| LeFort III fracture, initial encounter for closed fracture | 1 |
| Malignant neoplasm of bronchus and lung, unspecified | 1 |
| Chorioretinitis, unspecified | 1 |
| Hyperplasia of renal artery | 1 |
| Hypertensive retinopathy | 1 |
| Pervasive developmental disorder, unspecified | 1 |
| Cocaine dependence, in remission | 1 |
| Tobacco abuse counseling | 1 |
| Pyothorax without fistula | 1 |
| Tachypnea | 1 |
| Infection following a procedure, organ and space surgical site, initial encounter | 1 |
| Mild cognitive impairment of uncertain or unknown etiology | 1 |
| Vascular parkinsonism | 1 |
| Other specified forms of effusion, except tuberculous | 1 |
| Personal history of malignant neoplasm of bladder | 1 |
| Rhesus isoimmunization, delivered, with or without mention of antepartum condition | 1 |
| Need for prophylactic immunotherapy | 1 |
| Vascular dementia, uncomplicated | 1 |
| Other specified disorders of brain | 1 |
| 33 weeks gestation of pregnancy | 1 |
| Other specified disorders of liver | 1 |
| Deficiency of other specified B group vitamins | 1 |
| Digestive-genital tract fistula, female | 1 |
| Secondary and unspecified malignant neoplasm of lymph nodes of multiple sites | 1 |
| Postprocedural hematoma of skin and subcutaneous tissue following other procedure | 1 |
| Localization-related (focal) (partial) epilepsy and epileptic syndromes with complex partial seizures, with intractable epilepsy | 1 |
| Spastic hemiplegia and hemiparesis affecting unspecified side | 1 |
| Open bite of abdominal wall, right lower quadrant without penetration into peritoneal cavity, initial encounter | 1 |
| Open bite of right shoulder, initial encounter | 1 |
| Open bite of right buttock, initial encounter | 1 |
| Other anomalies of gallbladder, bile ducts, and liver | 1 |
| Mycosis fungoides, unspecified site, extranodal and solid organ sites | 1 |
| Sepsis due to other specified staphylococcus | 1 |
| Other partial intestinal obstruction | 1 |
| Immunodeficiency due to conditions classified elsewhere | 1 |
| Chronic kidney disease, stage 3 unspecified | 1 |
| Acute lymphoblastic leukemia, in relapse | 1 |
| Pressure ulcer, heel | 1 |
| Other osteoporosis with current pathological fracture, left femur, initial encounter for fracture | 1 |
| Pedal cycle driver injured in noncollision transport accident in traffic accident, initial encounter | 1 |
| Malignant neoplasm of head of pancreas | 1 |
| Unspecified psychosis not due to a substance or known physiological condition | 1 |
| Other emphysema | 1 |
| Hemorrhage into bladder wall | 1 |
| Pelvic peritoneal adhesions, female (postoperative) (postinfection) | 1 |
| Cocaine dependence with withdrawal | 1 |
| Postprocedural fever | 1 |
| Mechanical complication due to cardiac pacemaker (electrode) | 1 |
| Torticollis, unspecified | 1 |
| Endometriosis of uterus | 1 |
| Diarrhea, unspecified | 1 |
| Accidental fall from other furniture | 1 |
| Closed fracture of mandible, body, other and unspecified | 1 |
| Other intraoperative complications of the circulatory system, not elsewhere classified | 1 |
| Postprocedural hypotension | 1 |
| Dependent personality disorder | 1 |
| Arthropod-borne viral encephalitis, unspecified | 1 |
| Presence of left artificial knee joint | 1 |
| Other fracture of sacrum, initial encounter for closed fracture | 1 |
| Unspecified fracture of fifth lumbar vertebra, initial encounter for closed fracture | 1 |
| Accidents occurring in public building | 1 |
| Atherosclerosis of native arteries of the extremities with intermittent claudication | 1 |
| Intraspinal abscess | 1 |
| Submucous leiomyoma of uterus | 1 |
| Corpus luteum cyst of right ovary | 1 |
| Other noninflammatory disorders of ovary, fallopian tube and broad ligament | 1 |
| Personal history of other diseases of the digestive system | 1 |
| Gastrointestinal hemorrhage, unspecified | 1 |
| Unspecified transient mental disorder in conditions classified elsewhere | 1 |
| Disease of spinal cord, unspecified | 1 |
| Closed fracture of lower end of radius with ulna | 1 |
| Subdural hemorrhage following injury without mention of open intracranial wound, with no loss of consciousness | 1 |
| Disorder of the autonomic nervous system, unspecified | 1 |
| Localized swelling, mass and lump, left upper limb | 1 |
| Pouchitis | 1 |
| Other complications of enterostomy | 1 |
| Cardiac arrest due to other underlying condition | 1 |
| Unspecified sleep apnea | 1 |
| Secondary malignant neoplasm of unspecified site | 1 |
| Cellulitis of right lower limb | 1 |
| Atherosclerosis of native arteries of extremities with rest pain, right leg | 1 |
| Other cervical disc displacement at C6-C7 level | 1 |
| Other appendicitis | 1 |
| Gastro-esophageal laceration-hemorrhage syndrome | 1 |
| Chronic obstructive pulmonary disease with (acute) lower respiratory infection | 1 |
| Lumbago | 1 |
| Infarction of spleen | 1 |
| Ulcer of calf | 1 |
| Acquired spondylolisthesis | 1 |
| Conversion disorder | 1 |
| Thyroid dysfunction of mother, antepartum condition or complication | 1 |
| Acute embolism and thrombosis of unspecified deep veins of left distal lower extremity | 1 |
| Injury to spleen without mention of open wound into cavity, capsular tears, without major disruption of parenchyma | 1 |
| Closed fracture of six ribs | 1 |
| Closed fracture of navicular [scaphoid], foot | 1 |
| Closed fracture of astragalus | 1 |
| Anorexia nervosa, unspecified | 1 |
| Obsessive-compulsive disorder, unspecified | 1 |
| Persistent atrial fibrillation | 1 |
| Acute myeloid leukemia, without mention of having achieved remission | 1 |
| Chronic pulmonary embolism | 1 |
| Other chronic osteomyelitis, left ankle and foot | 1 |
| Endocarditis, valve unspecified, unspecified cause | 1 |
| Opioid abuse, continuous | 1 |
| Panic disorder without agoraphobia | 1 |
| Hypertonicity of bladder | 1 |
| Urinary hesitancy | 1 |
| Closed fracture of rib(s), unspecified | 1 |
| Retropharyngeal abscess | 1 |
| Other osteomyelitis, lower leg | 1 |
| Radiological procedure and radiotherapy as the cause of abnormal reaction of the patient, or of later complication, without mention of misadventure at the time of the procedure | 1 |
| Pneumonia due to Hemophilus influenzae [H. influenzae] | 1 |
| Pyogenic arthritis, lower leg | 1 |
| Mild cognitive impairment, so stated | 1 |
| Acute pharyngitis, unspecified | 1 |
| Toxic diffuse goiter without mention of thyrotoxic crisis or storm | 1 |
| Traumatic subarachnoid hemorrhage without loss of consciousness, initial encounter | 1 |
| Scoliosis, unspecified | 1 |
| Acute myocardial infarction of unspecified site, subsequent episode of care | 1 |
| Infection and inflammatory reaction due to other vascular device, implant, and graft | 1 |
| Sympatholytics [antiadrenergics] causing adverse effects in therapeutic use | 1 |
| Hemorrhage of gastrointestinal tract, unspecified | 1 |
| Unspecified disturbances of skin sensation | 1 |
| Dysmetabolic syndrome X | 1 |
| Epilepsy complicating pregnancy, childbirth, or the puerperium, delivered, with or without mention of antepartum condition | 1 |
| Metrorrhagia | 1 |
| Cerebral infarction due to embolism of left middle cerebral artery | 1 |
| Other diseases of pulmonary vessels | 1 |
| Personal history of tuberculosis | 1 |
| Chronic atrophic gastritis without bleeding | 1 |
| Unspecified psychophysiological malfunction | 1 |
| Injury to popliteal artery | 1 |
| Injury to anterior tibial artery | 1 |
| Traumatic compartment syndrome of lower extremity | 1 |
| Neoplasm of uncertain behavior of retroperitoneum | 1 |
| Dissection of coronary artery | 1 |
| Asplenia (congenital) | 1 |
| Obsessive-compulsive disorder | 1 |
| Mild intellectual disabilities | 1 |
| Duodenal ulcer, unspecified as acute or chronic, without hemorrhage or perforation | 1 |
| Degeneration of lumbar or lumbosacral intervertebral disc | 1 |
| Dislocation of prosthetic joint | 1 |
| Other artificial openings of urinary tract status | 1 |
| Cerebral infarction due to thrombosis of basilar artery | 1 |
| Cannabis abuse, episodic | 1 |
| Carrier or suspected carrier of Methicillin resistant Staphylococcus aureus | 1 |
| Diabetes with renal manifestations, type I [juvenile type], not stated as uncontrolled | 1 |
| Cutaneous abscess of left upper limb | 1 |
| Other giant cell arteritis | 1 |
| Closed fracture of head of radius | 1 |
| Other stimulant abuse with stimulant-induced mood disorder | 1 |
| Injury to other intra-abdominal organs without mention of open wound into cavity, peritoneum | 1 |
| Striking against or struck accidentally by object in sports with subsequent fall | 1 |
| Activities involving american tackle football | 1 |
| Contusion of abdominal wall | 1 |
| Myelopathy in diseases classified elsewhere | 1 |
| Ehlers-Danlos syndrome, unspecified | 1 |
| Migraine with aura, not intractable, without status migrainosus | 1 |
| Miscellaneous gastroenterology and urology devices associated with adverse incidents, not elsewhere classified | 1 |
| Opioid use, unspecified with withdrawal | 1 |
| Pathological fracture, left shoulder, initial encounter for fracture | 1 |
| Fracture of orbital roof, right side, initial encounter for closed fracture | 1 |
| Septicemia due to escherichia coli [E. coli] | 1 |
| Acute appendicitis with generalized peritonitis | 1 |
| Hydronephrosis with renal and ureteral calculous obstruction | 1 |
| Cervical disc disorder at C6-C7 level with myelopathy | 1 |
| Disturbances in tooth eruption | 1 |
| Other spontaneous pneumothorax | 1 |
| Nonspecific low blood pressure reading | 1 |
| Other malaise and fatigue | 1 |
| Syphilis, unspecified | 1 |
| Other specified anemias | 1 |
| Babesiosis | 1 |
| Hemiplegia, unspecified affecting left dominant side | 1 |
| Herpes simplex without mention of complication | 1 |
| Knee joint replacement | 1 |
| Other respiratory complications | 1 |
| Coagulation defect, unspecified | 1 |
| Left ventricular failure, unspecified | 1 |
| Nontoxic goiter, unspecified | 1 |
| Flaccid hemiplegia and hemiparesis affecting dominant side | 1 |
| Infection and inflammatory reaction due to other internal prosthetic devices, implants and grafts, initial encounter | 1 |
| Herpesviral gingivostomatitis and pharyngotonsillitis | 1 |
| Spondylolysis, lumbosacral region | 1 |
| Traumatic shock | 1 |
| Mechanical complication of nervous system device, implant, and graft | 1 |
| Other specified acquired deformity of head | 1 |
| Cervical shortening, delivered, with or without mention of antepartum condition | 1 |
| Excessive and frequent menstruation with regular cycle | 1 |
| Third-stage postpartum hemorrhage, delivered, with mention of postpartum complication | 1 |
| Opioid type dependence, unspecified | 1 |
| Other iatrogenic hypotension | 1 |
| Bacterial pneumonia, unspecified | 1 |
| Acute glomerulonephritis with other specified pathological lesion in kidney | 1 |
| Staphylococcus infection in conditions classified elsewhere and of unspecified site, other staphylococcus | 1 |
| Other specified bacterial infections in conditions classified elsewhere and of unspecified site, other gram-negative organisms | 1 |
| Nonspecific abnormal results of function study of liver | 1 |
| Crushing injury of thigh | 1 |
| Crushing injury of other specified sites of trunk | 1 |
| Methicillin susceptible pneumonia due to Staphylococcus aureus | 1 |
| Physical restraint status | 1 |
| Other intestinal obstruction unspecified as to partial versus complete obstruction | 1 |
| Closed fracture of lumbar spine with spinal cord injury | 1 |
| Fall from skis | 1 |
| Erythema intertrigo | 1 |
| Lymphedema, not elsewhere classified | 1 |
| Secondary malignant neoplasm of small intestine including duodenum | 1 |
| Stricture and stenosis of cervix uteri | 1 |
| Sepsis due to Methicillin resistant Staphylococcus aureus | 1 |
| Acute and subacute infective endocarditis | 1 |
| Other motor vehicle nontraffic accident while boarding and alighting injuring passenger in motor vehicle other than motorcycle | 1 |
| Amphetamine or related acting sympathomimetic abuse, continuous | 1 |
| Acute embolism and thrombosis of right internal jugular vein | 1 |
| Other thrombophilia | 1 |
| Activities involving ice skating | 1 |
| Hairy cell leukemia, in remission | 1 |
| Malignant neoplasm of cervix uteri, unspecified site | 1 |
| Frostbite of foot | 1 |
| Accident due to excessive cold due to weather conditions | 1 |
| Neoplasm of unspecified nature of bone, soft tissue, and skin | 1 |
| Other abnormal blood chemistry | 1 |
| Pneumonia due to escherichia coli [E. coli] | 1 |
| Open wound of cheek, without mention of complication | 1 |
| Open wound of face, unspecified site, without mention of complication | 1 |
| Dog bite | 1 |
| Mobitz (type) II atrioventricular block | 1 |
| Calculus of bile duct without mention of cholecystitis, with obstruction | 1 |
| Weakness | 1 |
| Major depressive disorder, recurrent severe without psychotic features | 1 |
| 36 weeks gestation of pregnancy | 1 |
| Calculus of gallbladder with other cholecystitis, with obstruction | 1 |
| Chest pain, unspecified | 1 |
| Coronary atherosclerosis of unspecified bypass graft | 1 |
| Collapsed vertebra, not elsewhere classified, thoracic region, initial encounter for fracture | 1 |
| Closed fracture of clavicle, unspecified part | 1 |
| Calculus of gallbladder with acute cholecystitis, without mention of obstruction | 1 |
| Other current conditions classifiable elsewhere of mother, postpartum condition or complication | 1 |
| Loss of weight | 1 |
| Suicide and self-inflicted poisoning by other specified drugs and medicinal substances | 1 |
| Polyarticular juvenile rheumatoid arthritis, chronic or unspecified | 1 |
| Subdural hemorrhage following injury without mention of open intracranial wound, with brief [less than one hour] loss of consciousness | 1 |
| Duodenal ulcer, unspecified as acute or chronic, without hemorrhage or perforation, without mention of obstruction | 1 |
| Diverticulosis of small intestine (without mention of hemorrhage) | 1 |
| Occlusion and stenosis of carotid artery with cerebral infarction | 1 |
| Cocaine dependence, uncomplicated | 1 |
| Bladder neck obstruction | 1 |
| Hypertrophy (benign) of prostate with urinary obstruction and other lower urinary tract symptoms (LUTS) | 1 |
| Sprain of tibiofibular (ligament), distal of ankle | 1 |
| Altered mental status | 1 |
| Closed fracture of shaft of radius (alone) | 1 |
| Proteus (mirabilis) (morganii) infection in conditions classified elsewhere and of unspecified site | 1 |
| Critical illness myopathy | 1 |
| Tracheoesophageal fistula | 1 |
| Diseases of the circulatory system complicating childbirth | 1 |
| Sickle-cell disease, unspecified | 1 |
| Other vascular myelopathies | 1 |
| Other specified diseases of spinal cord | 1 |
| Postpartum acute kidney failure | 1 |
| Pneumonia due to Klebsiella pneumoniae | 1 |
| Open wound of chest (wall), without mention of complication | 1 |
| Monoclonal gammopathy | 1 |
| Grand mal status | 1 |
| Chronic respiratory failure | 1 |
| Spinal stenosis, lumbosacral region | 1 |
| Other spondylosis with radiculopathy, lumbar region | 1 |
| Disseminated due to other mycobacteria | 1 |
| Closed fracture of other facial bones | 1 |
| Aspiration of fluid as the cause of abnormal reaction of patient, or of later complication, without mention of misadventure at time of procedure | 1 |
| Toxic liver disease with hepatic necrosis, without coma | 1 |
| Other drug-induced pancytopenia | 1 |
| Malignant neoplasm of pancreatic duct | 1 |
| Benign neoplasm of ovary | 1 |
| Subserosal leiomyoma of uterus | 1 |
| Secondary dysmenorrhea | 1 |
| Other mechanical complication of other internal orthopedic device, implant, and graft | 1 |
| Unspecified cataract | 1 |
| Bipolar II disorder | 1 |
| Unspecified mood [affective] disorder | 1 |
| Poisoning by benzodiazepines, accidental (unintentional), initial encounter | 1 |
| Poisoning by methadone, accidental (unintentional), initial encounter | 1 |
| Struck accidentally by falling object | 1 |
| Mantle cell lymphoma, intra-abdominal lymph nodes | 1 |
| Polyhydramnios, delivered, with or without mention of antepartum condition | 1 |
| Osteoarthrosis, unspecified whether generalized or localized, hand | 1 |
| Selective deficiency of immunoglobulin A [IgA] | 1 |
| Secondary and unspecified malignant neoplasm of inguinal and lower limb lymph nodes | 1 |
| Hyperprolactinemia | 1 |
| Cutaneous abscess of buttock | 1 |
| Methicillin susceptible Staphylococcus aureus infection as the cause of diseases classified elsewhere | 1 |
| Disorders of magnesium metabolism | 1 |
| Resistance to multiple antimicrobial drugs | 1 |
| Delayed and secondary postpartum hemorrhage, delivered, with mention of postpartum complication | 1 |
| Cardiac pacemaker in situ | 1 |
| Secondary malignant neoplasm of other digestive organs and spleen | 1 |
| Malignant neoplasm of heart | 1 |
| Overexertion from sudden strenuous movement | 1 |
| Unspecified fracture of T9-T10 vertebra, initial encounter for closed fracture | 1 |
| Unspecified laceration of spleen, initial encounter | 1 |
| Unspecified transient cerebral ischemia | 1 |
| Dilated cardiomyopathy | 1 |
| Nonrheumatic mitral (valve) insufficiency | 1 |
| Other otorrhea | 1 |
| Other noncollision motor vehicle traffic accident injuring passenger in motor vehicle other than motorcycle | 1 |
| Diffuse large B-cell lymphoma, lymph nodes of multiple sites | 1 |
| Anemia due to antineoplastic chemotherapy | 1 |
| Calculus of gallbladder with chronic cholecystitis without obstruction | 1 |
| Outcome of delivery, twins, both liveborn | 1 |
| Nutritional and metabolic cardiomyopathy | 1 |
| Other nonspecific abnormal finding of lung field | 1 |
| Awaiting organ transplant status | 1 |
| Abnormal weight loss | 1 |
| Esophageal varices in diseases classified elsewhere, with bleeding | 1 |
| Anemia of other chronic disease | 1 |
| Nonunion of fracture | 1 |
| Chronic osteomyelitis, pelvic region and thigh | 1 |
| Pain in right lower leg | 1 |
| Calculus of ureter | 1 |
| Cerebral ischemia | 1 |
| Polycystic ovaries | 1 |
| Diverticulosis of large intestine without perforation or abscess with bleeding | 1 |
| Other specified disorders of intestine | 1 |
| Acute or unspecified pelvic peritonitis, female | 1 |
| Digestive system complications, not elsewhere classified | 1 |
| Other intervertebral disc degeneration, lumbar region | 1 |
| Drug withdrawal | 1 |
| Antisocial personality disorder | 1 |
| Dependence on respirator [ventilator] status | 1 |
| Body mass index [BMI] 38.0-38.9, adult | 1 |
| Duodenitis without bleeding | 1 |
| Cyst of kidney, acquired | 1 |
| Pancreas transplant status | 1 |
| Other transplanted tissue rejection | 1 |
| Lobar pneumonia, unspecified organism | 1 |
| Other retention of urine | 1 |
| Malignant carcinoid tumor of unspecified site | 1 |
| Chronic gout, unspecified, with tophus (tophi) | 1 |
| Other cirrhosis of liver | 1 |
| Third-stage hemorrhage | 1 |
| Epilepsy, unspecified, intractable, without status epilepticus | 1 |
| Marfan syndrome | 1 |
| Sicca syndrome | 1 |
| Multiple myeloma, in relapse | 1 |
| Pneumonia due to Pseudomonas | 1 |
| Flail chest, initial encounter for closed fracture | 1 |
| Viral intestinal infection, unspecified | 1 |
| Anti-parkinsonism drugs causing adverse effects in therapeutic use | 1 |
| Type 2 diabetes mellitus with ketoacidosis without coma | 1 |
| Meningitis in other bacterial diseases classified elsewhere | 1 |
| Cardiac arrest, cause unspecified | 1 |
| Thromboembolism in childbirth | 1 |
| Esophageal varices without mention of bleeding | 1 |
| Spondylosis of unspecified site, without mention of myelopathy | 1 |
| Osteoarthrosis involving, or with mention of more than one site, but not specified as generalized, multiple sites | 1 |
| Intentional self-harm by other specified means, initial encounter | 1 |
| Suicide attempt, initial encounter | 1 |
| Patient's other noncompliance with medication regimen | 1 |
| Rheumatoid arthritis, unspecified | 1 |
| Bariatric surgery status complicating pregnancy, childbirth, or the puerperium, delivered, with or without mention of antepartum condition | 1 |
| Cerebral infarction due to unspecified occlusion or stenosis of unspecified cerebral artery | 1 |
| Mixed disorder of acid-base balance | 1 |
| Other postprocedural cardiac functional disturbances following other surgery | 1 |
| Exposure of implanted vaginal mesh and other prosthetic materials into vagina | 1 |
| Dermatophytosis of the body | 1 |
| Unspecified inflammatory disease of uterus | 1 |
| Personal history of malignant neoplasm of larynx | 1 |
| Nontraumatic intracerebral hemorrhage in cerebellum | 1 |
| Kidney transplant failure | 1 |
| Acute respiratory failure with hypercapnia | 1 |
| Abrasion or friction burn of elbow, forearm, and wrist, without mention of infection | 1 |
| Abscess of mediastinum | 1 |
| Psychophysical visual disturbances | 1 |
| Paranoid schizophrenia | 1 |
| Major depressive disorder, recurrent, moderate | 1 |
| Sciatica, unspecified side | 1 |
| Other and unspecified postsurgical nonabsorption | 1 |
| Unspecified procedure as the cause of abnormal reaction of patient, or of later complication, without mention of misadventure at time of procedure | 1 |
| Cellulitis and abscess of neck | 1 |
| Cellulitis and abscess of oral soft tissues | 1 |
| Diagnostic and monitoring cardiovascular devices associated with adverse incidents | 1 |
| Operating room of hospital as the place of occurrence of the external cause | 1 |
| Personal history of allergy to penicillin | 1 |
| Benign neoplasm of thyroid glands | 1 |
| Other diseases of trachea and bronchus | 1 |
| Other forms of scoliosis, lumbar region | 1 |
| Family history of malignant neoplasm of breast | 1 |
| Osteoarthrosis, localized, not specified whether primary or secondary, lower leg | 1 |
| Muscular dystrophy | 1 |
| Acute bronchitis | 1 |
| Crohn's disease of small intestine with abscess | 1 |
| Cutaneous abscess of abdominal wall | 1 |
| Paroxysmal nocturnal hemoglobinuria [Marchiafava-Micheli] | 1 |
| Homonymous bilateral field defects, left side | 1 |
| Nontoxic single thyroid nodule | 1 |
| Hereditary hemochromatosis | 1 |
| Bipolar I disorder, most recent episode (or current) manic, severe, specified as with psychotic behavior | 1 |
| Adult physical abuse | 1 |
| Other ureteric obstruction | 1 |
| Acute myocardial infarction of other lateral wall, initial episode of care | 1 |
| Postprocedural aspiration pneumonia | 1 |
| Maternal care for breech presentation, not applicable or unspecified | 1 |
| 32 weeks gestation of pregnancy | 1 |
| Radiculopathy, lumbar region | 1 |
| Malignant neoplasm of kidney, except pelvis | 1 |
| Dorsalgia, unspecified | 1 |
| Primary adrenocortical insufficiency | 1 |
| Chronic combined systolic (congestive) and diastolic (congestive) heart failure | 1 |
| Opioid use, unspecified, uncomplicated | 1 |
| Unspecified adverse effect of other drug, medicinal and biological substance | 1 |
| Primary thunderclap headache | 1 |
| Other specified hypoglycemia | 1 |
| Condyloma acuminatum | 1 |
| Dissection of cerebral arteries, nonruptured | 1 |
| Need for prophylactic vaccination and inoculation against tetanus toxoid alone | 1 |
| Pressure ulcer, other site | 1 |
| Accidental fall from chair | 1 |
| Cervical spondylosis without myelopathy | 1 |
| Other known or suspected fetal abnormality, not elsewhere classified, affecting management of mother, delivered, with or without mention of antepartum condition | 1 |
| Ulcer of lower limb, unspecified | 1 |
| Venous (peripheral) insufficiency, unspecified | 1 |
| Influenza due to unidentified influenza virus with other respiratory manifestations | 1 |
| (Idiopathic) normal pressure hydrocephalus | 1 |
| Hypertensive emergency | 1 |
| Giant cell arteritis | 1 |
| Accidental cut, puncture, perforation or hemorrhage during endoscopic examination | 1 |
| Albinism, unspecified | 1 |
| Follicular lymphoma grade II, lymph nodes of inguinal region and lower limb | 1 |
| Follicular lymphoma grade IIIa, lymph nodes of inguinal region and lower limb | 1 |
| Cerebral infarction due to embolism of right middle cerebral artery | 1 |
| Lipoma of other specified sites | 1 |
| Thyrotoxicosis without mention of goiter or other cause, and without mention of thyrotoxic crisis or storm | 1 |
| Traumatic subcutaneous emphysema | 1 |
| Fracture of lateral malleolus, closed | 1 |
| Presence of right artificial hip joint | 1 |
| Hemorrhage of rectum and anus | 1 |
| Other mechanical complication of internal fixation device of bone of left lower leg, initial encounter | 1 |
| Bipolar disorder, current episode manic without psychotic features, unspecified | 1 |
| Personal history of other diseases of digestive system | 1 |
| Unspecified intracranial injury without loss of consciousness, initial encounter | 1 |
| Displaced fracture of anterior column [iliopubic] of right acetabulum, initial encounter for closed fracture | 1 |
| Goiter, unspecified | 1 |
| Nontraumatic extradural hemorrhage | 1 |
| Family history of ischemic heart disease and other diseases of the circulatory system | 1 |
| Other epilepsy, not intractable, without status epilepticus | 1 |
| Secondary and unspecified malignant neoplasm of axilla and upper limb lymph nodes | 1 |
| Alcohol abuse with intoxication, unspecified | 1 |
| Unspecified extrapyramidal disease and abnormal movement disorder | 1 |
| Hypercalcemia | 1 |
| Blood alcohol level of 40-59 mg/100 ml | 1 |
| Late effect of fracture of lower extremities | 1 |
| Late effects of unspecified accident | 1 |
| Cutaneous abscess of left lower limb | 1 |
| Other osteonecrosis, right femur | 1 |
| Fracture of one rib, left side, initial encounter for closed fracture | 1 |
| Assault by strike against or bumped into by another person, initial encounter | 1 |
| Paroxysmal supraventricular tachycardia | 1 |
| Other specified bacterial agents as the cause of diseases classified elsewhere | 1 |
| Idiopathic normal pressure hydrocephalus (INPH) | 1 |
| Psoas muscle abscess | 1 |
| Mechanical complication due to other implant and internal device, not elsewhere classified | 1 |
| Accidents caused by other specified cutting and piercing instruments or objects | 1 |
| Injury to peroneal nerve | 1 |
| Phlebitis of portal vein | 1 |
| Laceration of left kidney, unspecified degree, initial encounter | 1 |
| Puncture wound without foreign body of abdominal wall, left lower quadrant with penetration into peritoneal cavity, initial encounter | 1 |
| Gastric ulcer, unspecified as acute or chronic, without hemorrhage or perforation | 1 |
| Malignant neoplasm of anus, unspecified site | 1 |
| Intestinal infection due to other organism, not elsewhere classified | 1 |
| Other malignant neoplasm without specification of site | 1 |
| Third degree perineal laceration during delivery, unspecified | 1 |
| Other fluid overload | 1 |
| Bacterial infection, unspecified, in conditions classified elsewhere and of unspecified site | 1 |
| Opioid abuse with opioid-induced mood disorder | 1 |
| Other pulmonary collapse | 1 |
| Concussion, with loss of consciousness of 30 minutes or less | 1 |
| Open wound of knee, leg [except thigh], and ankle, complicated | 1 |
| Seroma complicating a procedure | 1 |
| Unspecified intellectual disabilities | 1 |
| Nonspecific abnormal findings in amniotic fluid | 1 |
| Pneumonia due to Legionnaires' disease | 1 |
| Defibrination syndrome | 1 |
| Phlebitis and thrombophlebitis of superficial veins of upper extremities | 1 |
| Hematemesis | 1 |
| Secondary esophageal varices without bleeding | 1 |
| Activity, bike riding | 1 |
| Pneumocystosis | 1 |
| Pulmonary diseases due to other mycobacteria | 1 |
| Other megacolon | 1 |
| Unspecified fracture of ankle, closed | 1 |
| Attention to tracheostomy | 1 |
| Acute osteomyelitis, ankle and foot | 1 |
| Family history of malignant neoplasm of bladder | 1 |
| Other opiates and related narcotics causing adverse effects in therapeutic use | 1 |
| Type 2 diabetes mellitus with foot ulcer | 1 |
| Osteomyelitis, unspecified | 1 |
| Unspecified fracture of left pubis, initial encounter for closed fracture | 1 |
| Bradycardia, unspecified | 1 |
| Other acquired hemolytic anemias | 1 |
| Peri-prosthetic fracture around prosthetic joint | 1 |
| Herpes zoster with other nervous system complications | 1 |
| Other specified peritonitis | 1 |
| Electrolyte and fluid disorders not elsewhere classified | 1 |
| Low back pain | 1 |
| Calculus in bladder | 1 |
| Disorders of bursae and tendons in shoulder region, unspecified | 1 |
| Late effect of unspecified injury | 1 |
| Benign neoplasm of other specified sites | 1 |
| Pressure ulcer of sacral region, unstageable | 1 |
| Acute pulmonary insufficiency following nonthoracic surgery | 1 |
| Unspecified fracture of lower end of right tibia, subsequent encounter for closed fracture with nonunion | 1 |
| Resistance to multiple antibiotics | 1 |
| Unspecified fall, subsequent encounter | 1 |
| Agranulocytosis secondary to cancer chemotherapy | 1 |
| Other abnormal glucose | 1 |
| Premature separation of placenta, delivered, with or without mention of antepartum condition | 1 |
| Ulcerative (chronic) proctitis | 1 |
| Decreased fetal movements, affecting management of mother, delivered, with or without mention of antepartum condition | 1 |
| Mental disorders of mother, antepartum condition or complication | 1 |
| Schizophrenic disorders, residual type, chronic | 1 |
| Unspecified toxic encephalopathy | 1 |
| Anaphylactic reaction due to adverse effect of correct drug or medicament properly administered, initial encounter | 1 |
| Third or oculomotor nerve palsy, total | 1 |
| Unspecified disorder of autonomic nervous system | 1 |
| Acute myocardial infarction, unspecified | 1 |
| Epistaxis | 1 |
| Closed dislocation of radioulnar (joint), distal | 1 |
| Other accidents | 1 |
| Endometriosis, site unspecified | 1 |
| Pressure ulcer, hip | 1 |
| Periprosthetic fracture around internal prosthetic right hip joint, initial encounter | 1 |
| Acquired absence of kidney | 1 |
| Hydrops of gallbladder | 1 |
| Fall on same level from slipping, tripping and stumbling without subsequent striking against object, initial encounter | 1 |
| Activities involving walking, marching and hiking | 1 |
| Major depressive disorder, single episode, severe with psychotic features | 1 |
| Epilepsy, unspecified, without mention of intractable epilepsy | 1 |
| Cervical disc disorder at C5-C6 level with myelopathy | 1 |
| Concussion and edema of lumbar spinal cord, initial encounter | 1 |
| Unspecified nondisplaced fracture of seventh cervical vertebra, initial encounter for closed fracture | 1 |
| Unspecified hereditary and idiopathic peripheral neuropathy | 1 |
| Anomaly of aorta, unspecified | 1 |
| Cardiomyopathy in diseases classified elsewhere | 1 |
| Concussion with loss of consciousness of unspecified duration | 1 |
| Macular degeneration (senile), unspecified | 1 |
| Calculus of bile duct with other cholecystitis, with obstruction | 1 |
| Other specified disorders of penis | 1 |
| Attention deficit disorder with hyperactivity | 1 |
| Postprocedural cardiogenic shock, initial encounter | 1 |
| Presence of heart assist device | 1 |
| Disruption of external operation (surgical) wound, not elsewhere classified, initial encounter | 1 |
| Secondary malignant neoplasm of left lung | 1 |
| Acute diastolic (congestive) heart failure | 1 |
| Acute viral hepatitis, unspecified | 1 |
| Pyrexia of unknown origin following delivery | 1 |
| Mononeuritis of unspecified site | 1 |
| Allergic rhinitis due to pollen | 1 |
| Other dystonia | 1 |
| Herpes zoster without mention of complication | 1 |
| Personal history of malignant neoplasm of other parts of uterus | 1 |
| Long-term (current) use of antiplatelet/antithrombotic | 1 |
| Plantar fascial fibromatosis | 1 |
| Unspecified contact dermatitis, unspecified cause | 1 |
| Angiodysplasia of stomach and duodenum with hemorrhage | 1 |
| Subendocardial infarction, subsequent episode of care | 1 |
| Other transfusion reaction | 1 |
| Fever presenting with conditions classified elsewhere | 1 |
| Gastritis, unspecified, without bleeding | 1 |
| Pathological fracture in neoplastic disease, other specified site, initial encounter for fracture | 1 |
| Malignant neoplasm of cauda equina | 1 |
| Other cord compression | 1 |
| Other postprocedural complications and disorders of digestive system | 1 |
| Type 2 diabetes mellitus with diabetic peripheral angiopathy without gangrene | 1 |
| Palpitations | 1 |
| Cellulitis and abscess of buttock | 1 |
| Anal fistula | 1 |
| Foreign body in anus and rectum | 1 |
| Malignant neoplasm of main bronchus | 1 |
| Anaerobic meningitis | 1 |
| Mediastinal (thymic) large B-cell lymphoma, lymph nodes of multiple sites | 1 |
| Vitamin B12 deficiency anemia, unspecified | 1 |
| Neutropenia, unspecified | 1 |
| Obstructed labor due to other abnormalities of fetus | 1 |
| Cellulitis and abscess of hand, except fingers and thumb | 1 |
| Heart valve replaced by other means | 1 |
| Benign essential hypertension complicating pregnancy, childbirth, and the puerperium, delivered, with or without mention of antepartum condition | 1 |
| Dissection of aorta, thoracoabdominal | 1 |
| Anorexia nervosa | 1 |
| Body Mass Index between 19-24, adult | 1 |
| Other obstetric injury to pelvic organs | 1 |
| Maternal care for benign tumor of corpus uteri, third trimester | 1 |
| Other ill-defined heart diseases | 1 |
| Supraglottitis unspecified, with obstruction | 1 |
| Other acute postprocedural pain | 1 |
| Grand multiparity, delivered, with or without mention of antepartum condition | 1 |
| Other umbilical cord complications complicating labor and delivery, delivered, with or without mention of antepartum condition | 1 |
| Contact with or exposure to tuberculosis | 1 |
| Postprocedural pneumothorax | 1 |
| Localization-related (focal) (partial) epilepsy and epileptic syndromes with complex partial seizures, without mention of intractable epilepsy | 1 |
| Retained portions of placenta or membranes, without hemorrhage, delivered, with mention of postpartum complication | 1 |
| Hemoperitoneum | 1 |
| Non-pressure chronic ulcer of left ankle with bone involvement without evidence of necrosis | 1 |
| Stenosis of peripheral vascular stent, initial encounter | 1 |
| Secondary hyperparathyroidism (of renal origin) | 1 |
| Postprocedural septic shock, initial encounter | 1 |
| Acute respiratory distress syndrome | 1 |
| Respiratory syncytial virus pneumonia | 1 |
| Other specified disorders of stomach and duodenum | 1 |
| Disease of pericardium, unspecified | 1 |
| Unspecified inflammatory disease of female pelvic organs and tissues | 1 |
| Pleurisy without mention of effusion or current tuberculosis | 1 |
| Acute on chronic combined systolic and diastolic heart failure | 1 |
| Post traumatic seizures | 1 |
| Injury to other specified intrathoracic organs without mention of open wound into cavity | 1 |
| Injury of other specified blood vessels at neck level, initial encounter | 1 |
| Other foreign body or object entering through skin, initial encounter | 1 |
| Other spondylosis with radiculopathy, cervical region | 1 |
| Arterial embolism and thrombosis of lower extremity | 1 |
| Cerebrospinal fluid leak | 1 |
| NIHSS score 1 | 1 |
| Other muscle spasm | 1 |
| Other nonspecific abnormal results of function study of cardiovascular system | 1 |
| Tietze's disease | 1 |
| Chronic respiratory failure, unspecified whether with hypoxia or hypercapnia | 1 |
| Superficial foreign body (splinter) of finger(s), without major open wound and without mention of infection | 1 |
| Hip joint replacement | 1 |
| Cytomegaloviral disease | 1 |
| Other immunoproliferative neoplasms, without mention of having achieved remission | 1 |
| Surgical operation with anastomosis, bypass or graft as the cause of abnormal reaction of the patient, or of later complication, without mention of misadventure at the time of the procedure | 1 |
| Other and unspecified intracranial hemorrhage following injury without mention of open intracranial wound, with loss of consciousness of unspecified duration | 1 |
| Streptococcal septicemia | 1 |
| Budd-chiari syndrome | 1 |
| Depression, unspecified | 1 |
| Myelofibrosis | 1 |
| Alzheimer's disease | 1 |
| Tracheostomy status | 1 |
| Other generalized epilepsy and epileptic syndromes, not intractable, without status epilepticus | 1 |
| Autoimmune hepatitis | 1 |
| Other synovitis and tenosynovitis | 1 |
| Diabetes with other specified manifestations, type II or unspecified type, not stated as uncontrolled | 1 |
| Benign neoplasm of colon | 1 |
| Occlusion and stenosis of vertebral artery with cerebral infarction | 1 |
| Diabetes with other specified manifestations, type II or unspecified type, uncontrolled | 1 |
| Other staphylococcal septicemia | 1 |
| Secondary malignant neoplasm of unspecified lung | 1 |
| Diastolic heart failure, unspecified | 1 |
| Open wound of jaw, without mention of complication | 1 |
| Pedal cycle accident injuring pedal cyclist | 1 |
| Candidiasis of mouth | 1 |
| Long QT syndrome | 1 |
| Secondary uterine inertia, delivered, with or without mention of antepartum condition | 1 |
| Failed medical or unspecified induction of labor, delivered, with or without mention of antepartum condition | 1 |
| Family history of malignant neoplasm of gastrointestinal tract | 1 |
| Other vascular complications of medical care, not elsewhere classified | 1 |
| Senile dementia, uncomplicated | 1 |
| Sedative, hypnotic or anxiolytic dependence, continuous | 1 |
| Fracture of medial malleolus, closed | 1 |
| Accid from overexertion | 1 |
| Maternal care for scar from previous cesarean delivery | 1 |
| Alcoholic polyneuropathy | 1 |
| Unspecified vascular insufficiency of intestine | 1 |
| Hyperglycemia, unspecified | 1 |
| Other specified causes of urethral stricture | 1 |
| Other specified retention of urine | 1 |
| Mild intermittent asthma, uncomplicated | 1 |
| Unspecified disorder of kidney and ureter | 1 |
| Unspecified fracture of upper end of right humerus, initial encounter for closed fracture | 1 |
| Other fracture of upper and lower end of right fibula, initial encounter for closed fracture | 1 |
| Sick sinus syndrome | 1 |
| Diseases of the digestive system complicating childbirth | 1 |
| Choleperitonitis | 1 |
| Removal of other organ (partial) (total) causing abnormal patient reaction, or later complication, without mention of misadventure at time of operation | 1 |
| Benign essential hypertension | 1 |
| Disruption of wound, unspecified, initial encounter | 1 |
| Other generalized epilepsy and epileptic syndromes, intractable, without status epilepticus | 1 |
| Body mass index [BMI] 37.0-37.9, adult | 1 |
| Perforation of esophagus | 1 |
| Interstitial emphysema | 1 |
| Mononeuritis of lower limb, unspecified | 1 |
| Residual hemorrhoidal skin tags | 1 |
| Stenosis of rectum and anus | 1 |
| Atherosclerosis of native arteries of the extremities, unspecified | 1 |
| Other autoimmune hemolytic anemias | 1 |
| Gastrostomy status | 1 |
| Persistent vomiting | 1 |
| Other injury of abdomen | 1 |
| Intestinal bypass and anastomosis status | 1 |
| Closed fracture of sixth cervical vertebra | 1 |
| Other inflammatory disorders of male genital organs | 1 |
| Unspecified disease of pericardium | 1 |
| Other infection carrier state complicating childbirth | 1 |
| Neuromuscular dysfunction of bladder, unspecified | 1 |
| Poisoning by propionic acid derivatives | 1 |
| Diabetes with ophthalmic manifestations, type II or unspecified type, not stated as uncontrolled | 1 |
| Personal history of other lymphatic and hematopoietic neoplasms | 1 |
| Personal history of antineoplastic chemotherapy | 1 |
| Fracture of orbital floor, right side, initial encounter for closed fracture | 1 |
| Maxillary fracture, right side, initial encounter for closed fracture | 1 |
| Driver injured in collision with other motor vehicles in traffic accident, initial encounter | 1 |
| Abnormal immunological finding in serum, unspecified | 1 |
| Fall on same level from slipping, tripping and stumbling with subsequent striking against unspecified object, initial encounter | 1 |
| Eosinophilic esophagitis | 1 |
| Encounter for removal of intrauterine contraceptive device | 1 |
| Chronic inflammatory diseases of uterus, except cervix | 1 |
| Other foreign object in bronchus causing asphyxiation, initial encounter | 1 |
| Paralysis of vocal cords and larynx, unilateral | 1 |
| Aftercare for healing traumatic fracture of vertebrae | 1 |
| Aftercare for healing traumatic fracture of other bone | 1 |
| Multiple fractures of ribs, right side, initial encounter for closed fracture | 1 |
| Food in other parts of respiratory tract causing asphyxiation, initial encounter | 1 |
| Malignant neoplasm of sigmoid colon | 1 |
| Legal blindness, as defined in U.S.A. | 1 |
| Emphysema, unspecified | 1 |
| Injury to liver without mention of open wound into cavity, hematoma and contusion | 1 |
| Other specified injury caused by animal | 1 |
| Pneumococcal septicemia [Streptococcus pneumoniae septicemia] | 1 |
| Nontraffic accident involving motor-driven snow vehicle injuring driver of motor vehicle other than motorcycle | 1 |
| Resistance to penicillins | 1 |
| Other instability, right hip | 1 |
| Surgical operation with implant of artificial internal device as the cause of abnormal reaction of the patient, or of later complication, without mention of misadventure at the time of the procedure | 1 |
| Other place in single-family (private) house as the place of occurrence of the external cause | 1 |
| Hepatitis E without mention of hepatic coma | 1 |
| Body Mass Index 38.0-38.9, adult | 1 |
| Late effect of complications of surgical and medical care | 1 |
| Other specified procedures as the cause of abnormal reaction of patient, or of later complication, without mention of misadventure at time of procedure | 1 |
| Other specified disorders resulting from impaired renal function | 1 |
| Other displaced fracture of upper end of right humerus, initial encounter for closed fracture | 1 |
| Unspecified rotator cuff tear or rupture of right shoulder, not specified as traumatic | 1 |
| Other disorders of bone and cartilage | 1 |
| Dissection of thoracoabdominal aorta | 1 |
| Obstetric high vaginal laceration alone | 1 |
| Amyloidosis, unspecified | 1 |
| Body Mass Index 39.0-39.9, adult | 1 |
| Other specified disorders of bone density and structure, unspecified site | 1 |
| Intervertebral disc disorders with myelopathy, thoracic region | 1 |
| Conus medullaris syndrome | 1 |
| Infection and inflammatory reaction due to indwelling urinary catheter | 1 |
| Bulimia nervosa | 1 |
| Adjustment disorder with anxiety | 1 |
| Traumatic cerebral edema without loss of consciousness, initial encounter | 1 |
| Sequelae of inflammatory diseases of central nervous system | 1 |
| Systemic lupus erythematosus, unspecified | 1 |
| Localization-related (focal) (partial) symptomatic epilepsy and epileptic syndromes with simple partial seizures, not intractable, without status epilepticus | 1 |
| Other disorders of plasma protein metabolism | 1 |
| Ulcerative (chronic) enterocolitis | 1 |
| Other B-complex deficiencies | 1 |
| Acute parametritis and pelvic cellulitis | 1 |
| Infertility, female, of unspecified origin | 1 |
| Unspecified cirrhosis of liver | 1 |
| Acute pancreatitis, unspecified | 1 |
| Malignant neoplasm of unspecified kidney, except renal pelvis | 1 |
| Delusional disorder | 1 |
| Recurrent pregnancy loss, delivered, with or without mention of antepartum condition | 1 |
| Selective deficiency of immunoglobulin G [IgG] subclasses | 1 |
| Liver replaced by transplant | 1 |
| Alcohol dependence, uncomplicated | 1 |
| Other osteomyelitis, other site | 1 |
| Specific reading disorder | 1 |
| Subarachnoid hemorrhage following injury without mention of open intracranial wound, with no loss of consciousness | 1 |
| Other noncollision motor vehicle traffic accident injuring pedestrian | 1 |
| Malignant neoplasm of left kidney, except renal pelvis | 1 |
| Elevated prostate specific antigen [PSA] | 1 |
| Elevated white blood cell count, unspecified | 1 |
| Hemorrhage of anus and rectum | 1 |
| Status post administration of tPA (rtPA) in a different facility within the last 24 hours prior to admission to current facility | 1 |
| Multiple fractures of ribs, left side, initial encounter for closed fracture | 1 |
| Drug-induced delirium | 1 |
| Late effects of cerebrovascular disease, hemiplegia affecting unspecified side | 1 |
| Thrombosis of atrium, auricular appendage, and ventricle as current complications following acute myocardial infarction | 1 |
| Complications of transplanted bone marrow | 1 |
| Unspecified cord compression | 1 |
| Chronic venous embolism and thrombosis of subclavian veins | 1 |
| Brachial plexus lesions | 1 |
| Panic disorder [episodic paroxysmal anxiety] | 1 |
| Secondary malignant neoplasm of left ovary | 1 |
| Mild protein-calorie malnutrition | 1 |
| Chronic total occlusion of artery of the extremities | 1 |
| Diabetes with peripheral circulatory disorders, type II or unspecified type, not stated as uncontrolled | 1 |
| Hypertrophy of labia | 1 |
| Skeletal muscle relaxants causing adverse effects in therapeutic use | 1 |
| Obsessive-compulsive disorders | 1 |
| Tourette's disorder | 1 |
| Lack of normal physiological development, unspecified | 1 |
| Nephrotic syndrome with unspecified pathological lesion in kidney | 1 |
| Spinal stenosis in cervical region | 1 |
| Other activity | 1 |
| Unspecified external cause status | 1 |
| Unspecified vitamin deficiency | 1 |
| Nonspecific abnormal results of function study of thyroid | 1 |
| Pressure ulcer of other site, stage 3 | 1 |
| Non-Hodgkin lymphoma, unspecified, unspecified site | 1 |
| Non-Hodgkin lymphoma, unspecified, extranodal and solid organ sites | 1 |
| Postprocedural air leak | 1 |
| Accidental fall from ladder | 1 |
| Interstitial pulmonary disease, unspecified | 1 |
| Angiodysplasia of intestine with hemorrhage | 1 |
| Bipolar I disorder, single manic episode, unspecified | 1 |
| Alopecia, unspecified | 1 |
| Malignant neoplasm of frontal lobe | 1 |
| Other specified acute viral hepatitis | 1 |
| Unspecified asthma with (acute) exacerbation | 1 |
| Other bipolar disorders | 1 |
| Dermatomyositis | 1 |
| Displacement of infusion catheter, initial encounter | 1 |
| Other injury into spleen without mention of open wound into cavity | 1 |
| Other noncollision motor vehicle traffic accident injuring driver of motor vehicle other than motorcycle | 1 |
| Personal history of other malignant neoplasm of rectum, rectosigmoid junction, and anus | 1 |
| Congenital abnormalities of uterus, delivered, with or without mention of antepartum condition | 1 |
| Polyp of corpus uteri | 1 |
| Mucous polyp of cervix | 1 |
| Endometriosis of ovary | 1 |
| Dissection of thoracic aorta | 1 |
| Melena | 1 |
| Supervision of elderly primigravida, third trimester | 1 |
| REM sleep behavior disorder | 1 |
| Mild to moderate pre-eclampsia, complicating childbirth | 1 |
| Unspecified systolic (congestive) heart failure | 1 |
| Viral hepatitis complicating childbirth | 1 |
| Gestational diabetes mellitus in childbirth, unspecified control | 1 |
| Diffuse large B-cell lymphoma, intrapelvic lymph nodes | 1 |
| Drug-induced polyneuropathy | 1 |
| Other seizures | 1 |
| Wild-type transthyretin-related (ATTR) amyloidosis | 1 |
| Other primary thrombophilia | 1 |
| Pregnant state, incidental | 1 |
| Pedestrian on foot injured in collision with car, pick-up truck or van, unspecified whether traffic or nontraffic accident, initial encounter | 1 |
| Unspecified street and highway as the place of occurrence of the external cause | 1 |
| Encounter for insertion of intrauterine contraceptive device | 1 |
| Accidents occurring in industrial places and premises | 1 |
| Pathological fracture, right shoulder, initial encounter for fracture | 1 |
| Phantom limb (syndrome) | 1 |
| Dissection of other artery | 1 |
| Accidental puncture or laceration during a procedure, not elsewhere classified | 1 |
| Accident involving animal being ridden injuring rider of animal | 1 |
| Adult failure to thrive | 1 |
| Diseases of the nervous system complicating the puerperium | 1 |
| Sepsis due to Enterococcus | 1 |
| Stenosis of other cardiac prosthetic devices, implants and grafts, initial encounter | 1 |
| Fall on same level, unspecified, initial encounter | 1 |
