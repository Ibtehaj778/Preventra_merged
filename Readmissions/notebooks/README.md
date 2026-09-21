# notebooks

One folder per dataset phase. Previously split across `Notebooks/` and `notebooks/`, which
differed only in capitalisation.

| Folder | Contents |
|---|---|
| `diabetic/` | The UCI baseline — EDA and the original readmission model |
| `cms/` | CMS DE-SynPUF — extraction, preprocessing, feature engineering, analysis, and the Phase 1 model |
| `mimic/` | MIMIC-IV — data acquisition, the discharge model, EDA, and the ICD analysis and feature experiment |

`mimic/phase1_discharge_risk_mimic.ipynb` builds the model the application actually serves. The
`solved-*` notebooks are completed runs with their outputs kept.
