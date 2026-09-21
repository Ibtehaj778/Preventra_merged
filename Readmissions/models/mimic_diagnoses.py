"""
Admission diagnoses for the MIMIC-IV Phase 1 dashboard.

Attaches "what was this patient actually diagnosed with on this admission" to
each scored row, so a risk score sits next to a clinical reason rather than
next to a bare number.

Source tables (MIMIC-IV `hosp`):
  diagnoses_icd     subject_id, hadm_id, seq_num, icd_code, icd_version
  d_icd_diagnoses   icd_code, icd_version, long_title

seq_num is the billing sequence: seq_num == 1 is the PRINCIPAL diagnosis, the
condition chiefly responsible for the admission. That is the one shown as the
headline; the next few are kept as secondary context.

JOIN KEY WARNING
----------------
The lookup is keyed on `hadm_id`. `phase1_matrix.parquet` does NOT carry
hadm_id - the Phase 1 notebook lists it in DROP and saves only
["subject_id", "readmit_30d"] + FEATURES - so diagnoses cannot be attached to
the current matrix at all.

Recovering the key by matching the 48 lab columns back to phase1_labs.parquet
was measured and rejected: 32% of rows match more than one hadm_id, which would
silently label patients with another patient's diagnosis.

The fix is one line in the Phase 1 notebook's final cell:

    save_cache(X[["subject_id", "hadm_id", "readmit_30d"] + FEATURES],
               "phase1_matrix")

hadm_id stays out of FEATURES, so the model and its inputs are unchanged; it
just travels with the row as an identifier.
"""

from __future__ import annotations

import os

import pandas as pd

# ICD-9 and ICD-10 both appear in MIMIC-IV and their code spaces overlap - the
# same string can be a valid code in either version and mean different things -
# so every join must use the pair, never icd_code alone.
_ICD_KEY = ["icd_code", "icd_version"]

# How many secondary diagnoses to carry alongside the principal one. Three is
# what the driver cards have room for without becoming a wall of text.
N_SECONDARY = 3


def load_diagnosis_index(diagnoses_path: str,
                         dictionary_path: str,
                         hadm_ids=None) -> pd.DataFrame:
    """
    Build a per-admission diagnosis table.

    Returns one row per hadm_id with:
        primary_diagnosis        long_title of the seq_num == 1 diagnosis
        primary_icd              "<code> (ICD-<version>)"
        secondary_diagnoses      list of the next N_SECONDARY long_titles
        n_diagnoses_coded        how many diagnoses were coded for the stay

    `hadm_ids` optionally restricts the read to the admissions actually being
    loaded, which matters because diagnoses_icd is ~6M rows.
    """
    for path, what in ((diagnoses_path, "diagnoses_icd"),
                       (dictionary_path, "d_icd_diagnoses")):
        if not os.path.exists(path):
            raise FileNotFoundError(f"{what} not found at {path}")

    dx = pd.read_csv(diagnoses_path,
                     usecols=["hadm_id", "seq_num", "icd_code", "icd_version"])
    if hadm_ids is not None:
        dx = dx[dx.hadm_id.isin(set(hadm_ids))]

    dic = pd.read_csv(dictionary_path, usecols=_ICD_KEY + ["long_title"])

    # Codes are zero-padded/whitespace-inconsistent between the two tables in
    # some MIMIC releases; normalising both sides prevents silent join misses.
    for frame in (dx, dic):
        frame["icd_code"] = frame["icd_code"].astype(str).str.strip().str.upper()
        frame["icd_version"] = pd.to_numeric(frame["icd_version"], errors="coerce")

    dic = dic.drop_duplicates(subset=_ICD_KEY)
    dx = dx.merge(dic, on=_ICD_KEY, how="left")

    # An unmapped code is shown as the raw code rather than dropped - a missing
    # diagnosis row would misrepresent the admission as having fewer problems.
    dx["long_title"] = dx["long_title"].fillna(
        dx["icd_code"].map(lambda c: f"Unmapped ICD code {c}"))

    dx = dx.sort_values(["hadm_id", "seq_num"])

    principal = (dx[dx.seq_num == 1]
                 .drop_duplicates(subset="hadm_id")
                 .set_index("hadm_id"))

    out = pd.DataFrame(index=pd.Index(sorted(dx.hadm_id.unique()), name="hadm_id"))
    out["primary_diagnosis"] = principal["long_title"]
    out["primary_icd"] = (principal["icd_code"].astype(str)
                          + " (ICD-" + principal["icd_version"].astype("Int64").astype(str) + ")")

    secondary = (dx[dx.seq_num > 1]
                 .groupby("hadm_id")["long_title"]
                 .apply(lambda s: list(s.head(N_SECONDARY))))
    out["secondary_diagnoses"] = secondary
    out["secondary_diagnoses"] = out["secondary_diagnoses"].apply(
        lambda v: v if isinstance(v, list) else [])

    out["n_diagnoses_coded"] = dx.groupby("hadm_id").size()

    # Some admissions have secondary codes but no seq_num == 1 row at all.
    # Saying so is better than leaving a blank that reads as "not sick".
    out["primary_diagnosis"] = out["primary_diagnosis"].fillna(
        "No principal diagnosis coded for this admission")
    out["primary_icd"] = out["primary_icd"].fillna("")

    return out.reset_index()


def attach_to_matrix(M: pd.DataFrame,
                     diagnoses_path: str,
                     dictionary_path: str) -> pd.DataFrame:
    """
    Left-join the diagnosis index onto a scored matrix.

    Raises if the matrix has no hadm_id, rather than guessing - see the JOIN KEY
    WARNING at the top of this module for why guessing was rejected.
    """
    if "hadm_id" not in M.columns:
        raise KeyError(
            "phase1_matrix.parquet has no hadm_id column, so diagnoses cannot be "
            "linked to scored rows. Re-export the matrix from the Phase 1 notebook "
            'with: save_cache(X[["subject_id","hadm_id","readmit_30d"] + FEATURES], '
            '"phase1_matrix")'
        )

    idx = load_diagnosis_index(diagnoses_path, dictionary_path,
                               hadm_ids=M["hadm_id"].unique())
    return M.merge(idx, on="hadm_id", how="left")
