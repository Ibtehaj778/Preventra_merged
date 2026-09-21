# data

| Folder | Contents |
|---|---|
| `diabetic/` | UCI Diabetes 130-US Hospitals — source CSV, engineered feature sets, scored test splits, confusion matrices, model card |
| `cms/` | CMS DE-SynPUF — the sample claim files and the merged extracts |
| `mimic/` | MIMIC-IV — sample tables, the trained model bundle under `model/results/`, the feature matrices, and the transfer-test result |
| `reference/` | Public datasets used for comparison or testing, not part of the three phases |
| `runtime/` | What the running application reads and writes — the risk registry, batch `input/` and `output/`, and exported samples |

## Paths the code depends on

| Path | Read by |
|---|---|
| `mimic/model/results/phase1_model.joblib` | `api/mimic_scoring.py`, the loader, the simulator |
| `mimic/model/results/phase1_matrix.parquet` | the loader and the simulator |
| `runtime/input/`, `runtime/output/` | `pipeline/batch_flow.py` |

Moving anything in that table means updating the reference alongside it.

MIMIC-IV is credentialed data. Only small samples are committed here; the full tables require
PhysioNet approval and a signed data use agreement.
