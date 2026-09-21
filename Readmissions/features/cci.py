"""
features/cci.py
---------------
Computes the Charlson Comorbidity Index (CCI) from ICD-9 diagnosis codes.

Each patient row in the Diabetes dataset has up to three diagnosis columns:
  diag_1, diag_2, diag_3

This module maps those ICD-9 codes to CCI category weights using the
standard Charlson mapping and sums the weights per patient row.

Reference: Charlson et al. (1987). A new method of classifying prognostic
comorbidity in longitudinal studies.
"""

import pandas as pd
import re

# ---------------------------------------------------------------------------
# ICD-9 to CCI weight mapping
# Each entry: (regex_pattern_or_prefix, weight)
# Patterns are matched against the numeric part of the ICD-9 code.
# ---------------------------------------------------------------------------
CCI_MAP: list[tuple[str, int]] = [
    # Weight 1
    (r"^410|^412",                          1),  # Myocardial infarction
    (r"^428",                               1),  # Congestive heart failure
    (r"^4[45]",                             1),  # Peripheral vascular disease
    (r"^43[0-8]",                           1),  # Cerebrovascular disease
    (r"^290",                               1),  # Dementia
    (r"^49[0-6]|^500|^505|^5064",          1),  # Chronic pulmonary disease
    (r"^710[01]|^7140|^7141|^7142|^7148",  1),  # Connective tissue disease
    (r"^53[1-4]",                           1),  # Peptic ulcer disease
    (r"^571",                               1),  # Mild liver disease
    (r"^250[0-3]",                          1),  # Diabetes without complications
    # Weight 6 (must be checked BEFORE weight-2 tumor pattern to avoid overlap)
    (r"^196|^197|^198|^199",               6),  # Metastatic solid tumor
    (r"^042|^043|^044",                    6),  # AIDS/HIV
    # Weight 3
    (r"^572[2-8]",                          3),  # Moderate/severe liver disease
    # Weight 2
    (r"^342|^344[01]",                      2),  # Hemiplegia
    (r"^58[2-3]|^585|^586|^5880",          2),  # Moderate/severe renal disease
    (r"^250[4-9]",                          2),  # Diabetes with end-organ damage
    (r"^1[4-9][0-9]|^20[0-8]",            2),  # Tumor (non-metastatic)
    (r"^204[1]|^205[3]|^206[3]|^207[12]", 2),  # Leukemia
    (r"^200|^201|^202",                    2),  # Lymphoma
]

# Pre-compiled for performance
_COMPILED_CCI = [(re.compile(pat), w) for pat, w in CCI_MAP]


def _icd9_to_weight(code: str) -> int:
    """Return the CCI weight for a single ICD-9 code string, or 0."""
    if not isinstance(code, str):
        return 0
    code = code.strip().upper()
    # Strip decimal suffix (e.g. '250.01' -> '25001' for matching)
    code_clean = code.replace(".", "")
    for pattern, weight in _COMPILED_CCI:
        if pattern.match(code_clean):
            return weight
    return 0


def compute_cci(row: pd.Series) -> int:
    """
    Compute the Charlson Comorbidity Index for a single patient row.

    Reads diag_1, diag_2, diag_3 columns and returns the sum of
    CCI weights across all three diagnoses (duplicates counted once).

    Parameters
    ----------
    row : pd.Series
        A single row from the patient DataFrame.

    Returns
    -------
    int
        CCI score (0 or higher).
    """
    seen_weights: set[int] = set()
    total = 0
    for col in ("diag_1", "diag_2", "diag_3"):
        code = row.get(col, None)
        weight = _icd9_to_weight(code)
        if weight > 0 and weight not in seen_weights:
            total += weight
            seen_weights.add(weight)
    return total


def add_cci_feature(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply compute_cci across the DataFrame and add 'charlson_comorbidity_index'.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame with diag_1, diag_2, diag_3 columns present.

    Returns
    -------
    pd.DataFrame
        DataFrame with new 'charlson_comorbidity_index' integer column.
    """
    df["charlson_comorbidity_index"] = df.apply(compute_cci, axis=1)
    print(f"[cci] CCI computed. Value counts:\n{df['charlson_comorbidity_index'].value_counts().head(10)}")
    return df


if __name__ == "__main__":
    from features.clean import load_and_clean

    df = load_and_clean()
    df = add_cci_feature(df)
    print(df["charlson_comorbidity_index"].describe())