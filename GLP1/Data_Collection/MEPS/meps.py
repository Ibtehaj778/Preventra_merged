
import pandas as pd
meps = pd.read_csv("MEPS/meps_glp1_cost_analysis.csv")
print(meps["RXDRGNAM_STR"].unique())
import pandas as pd


"""
GLP-1 Analytics Platform — MEPS Cost Analysis (Corrected)
Produces meps_glp1_cost_analysis.csv for use in Fusion Layer 1.

FIX FROM ORIGINAL:
  - Added molecule column to output using str.contains() brand matching.
    The fusion script was trying to do an exact brand name lookup which
    failed because MEPS stores names like "OZEMPIC 0.5MG/DOSE INJECTIO"
    not clean "OZEMPIC". Moving the mapping here with str.contains()
    means the fusion lookup tables will actually populate (not 0 rows).

  - Added avg_oop_by_molecule summary printout so you can confirm
    real MEPS cost data is flowing through before running fusion.
"""

"""
GLP-1 Analytics Platform — MEPS Cost Analysis (Corrected v2)
Produces meps_glp1_cost_analysis.csv for use in Fusion Layer 1.

FIX FROM v1:
  - MEPS file uses GENERIC molecule names (SEMAGLUTIDE, TIRZEPATIDE etc.)
    not brand names (OZEMPIC, WEGOVY etc.). Updated GLP1_DRUGS filter
    and NAME_TO_MOLECULE mapping accordingly. Previous version was
    filtering for brand names and finding 0 rows even though the data
    was present under generic names.
"""

import pandas as pd

# ── CONFIG ────────────────────────────────────────────────────────────────────
PMED_EXCEL  = "MEPS/H248A.xlsx"
CONS_EXCEL  = "MEPS/H251.xlsx"
OUTPUT_FILE = "MEPS/meps_glp1_cost_analysis.csv"

# MEPS stores generic names — search for these
GLP1_GENERICS = [
    'SEMAGLUTIDE',
    'TIRZEPATIDE',
    'DULAGLUTIDE',
    'LIRAGLUTIDE',
    'EXENATIDE',
    'LIXISENATIDE',
    'ALBIGLUTIDE',
]

# Since MEPS already uses generic names, this mapping is now trivial
# but kept explicit so fusion Layer 1 gets a clean 'molecule' column
NAME_TO_MOLECULE = {
    'SEMAGLUTIDE':  'SEMAGLUTIDE',
    'TIRZEPATIDE':  'TIRZEPATIDE',
    'DULAGLUTIDE':  'DULAGLUTIDE',
    'LIRAGLUTIDE':  'LIRAGLUTIDE',
    'EXENATIDE':    'LIRAGLUTIDE',   # group with liraglutide (same generation)
    'LIXISENATIDE': 'LIRAGLUTIDE',
    'ALBIGLUTIDE':  'DULAGLUTIDE',
}

def map_to_molecule(drug_name: str) -> str | None:
    drug_upper = str(drug_name).upper().strip()
    for name, molecule in NAME_TO_MOLECULE.items():
        if name in drug_upper:
            return molecule
    return None


def process_meps():
    print("=" * 60)
    print("Loading MEPS files...")
    print("=" * 60)

    df_pmed = pd.read_excel(PMED_EXCEL)
    print(f"  Prescribed medicines rows : {len(df_pmed):,}")

    # ── DRUG NAME NORMALISATION ───────────────────────────────────────────────
    if 'RXDRGNAM' in df_pmed.columns:
        df_pmed['RXDRGNAM_STR'] = df_pmed['RXDRGNAM'].astype(str).str.strip().str.upper()
        name_col = 'RXDRGNAM_STR'
    elif 'RXNAME' in df_pmed.columns:
        df_pmed['RXDRGNAM_STR'] = df_pmed['RXNAME'].astype(str).str.strip().str.upper()
        name_col = 'RXDRGNAM_STR'
    else:
        raise ValueError("Neither RXDRGNAM nor RXNAME found. Print df_pmed.columns to inspect.")

    print(f"  Using drug name column : {name_col}")

    # ── FILTER FOR GLP-1 DRUGS ────────────────────────────────────────────────
    # Now filtering on generic names which is what MEPS actually contains
    df_glp1 = df_pmed[
        df_pmed[name_col].str.contains('|'.join(GLP1_GENERICS), na=False)
    ].copy()

    print(f"\n  GLP-1 rows found : {len(df_glp1):,}")
    print(f"  Unique drug names found:")
    for name in sorted(df_glp1[name_col].unique()):
        print(f"    {name}")

    if df_glp1.empty:
        # Last resort diagnostic — print every unique name containing
        # fragments that might be GLP-1 related
        print("\n  Still empty. Searching for partial matches...")
        fragments = ['GLUC', 'SEMAG', 'TIRZE', 'DULAG', 'LIRAG', 'EXENA']
        candidates = df_pmed[
            df_pmed[name_col].str.contains('|'.join(fragments), na=False)
        ][name_col].unique()
        print(f"  Possible GLP-1 related names in file: {candidates}")
        raise ValueError("No GLP-1 drugs found. Check candidates above and update GLP1_GENERICS.")

    # ── ADD MOLECULE COLUMN ───────────────────────────────────────────────────
    df_glp1['molecule'] = df_glp1[name_col].apply(map_to_molecule)

    mapped   = df_glp1['molecule'].notna().sum()
    unmapped = df_glp1['molecule'].isna().sum()
    print(f"\n  Molecule mapping:")
    print(f"    Mapped   : {mapped:,}")
    print(f"    Unmapped : {unmapped:,}")
    if unmapped > 0:
        print(f"    Unmapped names: {df_glp1[df_glp1['molecule'].isna()][name_col].unique()}")

    print(f"\n  Molecule distribution:")
    print(df_glp1['molecule'].value_counts().to_string())

    # ── LOAD CONSOLIDATED DEMOGRAPHICS ────────────────────────────────────────
    demo_cols = ['DUPERSID', 'INSCOV23', 'POVCAT23', 'AGELAST', 'SEX', 'RACETHX']
    df_cons   = pd.read_excel(CONS_EXCEL, usecols=demo_cols)
    print(f"\n  Consolidated demo rows : {len(df_cons):,}")

    # ── COST COLUMN MAPPING ───────────────────────────────────────────────────
    # Try X-suffix first (most common), fall back to non-X
    cost_candidates = [
        {'RXSF23X': 'out_of_pocket', 'RXPV23X': 'insurance_paid', 'RXXP23X': 'total_drug_cost'},
        {'RXSF23':  'out_of_pocket', 'RXPV23':  'insurance_paid', 'RXXP23':  'total_drug_cost'},
    ]
    cost_mapping = {}
    for candidate in cost_candidates:
        found = {k: v for k, v in candidate.items() if k in df_glp1.columns}
        if found:
            cost_mapping = found
            break

    if not cost_mapping:
        rx_cols = [c for c in df_glp1.columns if c.upper().startswith('RX')]
        print(f"\n  WARNING: No cost columns found. All RX columns: {rx_cols}")
    else:
        print(f"\n  Cost columns mapped: {cost_mapping}")

    # ── MERGE ─────────────────────────────────────────────────────────────────
    df_final = df_glp1.merge(df_cons, on='DUPERSID', how='left')
    df_final = df_final.rename(columns=cost_mapping)

    # ── DERIVED COST FEATURES ─────────────────────────────────────────────────
    if 'out_of_pocket' in df_final.columns and 'total_drug_cost' in df_final.columns:
        df_final['patient_pay_ratio'] = (
            df_final['out_of_pocket'] /
            df_final['total_drug_cost'].replace(0, float('nan'))
        ).round(4)
        df_final['high_cost_burden'] = (df_final['out_of_pocket'] > 50).astype(int)

    # ── SAVE ──────────────────────────────────────────────────────────────────
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"\n  Saved {len(df_final):,} rows → {OUTPUT_FILE}")
    print(f"  Columns: {list(df_final.columns)}")

    # ── VERIFICATION ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("VERIFICATION — Average OOP cost by molecule")
    print("(Confirm real dollar values before running fusion Layer 1)")
    print("=" * 60)
    if 'out_of_pocket' in df_final.columns and 'molecule' in df_final.columns:
        summary = (
            df_final[df_final['molecule'].notna()]
            .groupby('molecule')['out_of_pocket']
            .agg(['mean', 'median', 'count'])
            .round(2)
        )
        print(summary.to_string())
    else:
        rx_cols = [c for c in df_final.columns if 'RX' in c.upper() or 'COST' in c.upper()]
        print(f"  out_of_pocket column missing. Candidate columns: {rx_cols}")

    return df_final


if __name__ == "__main__":
    process_meps()

meps = pd.read_csv('MEPS/meps_glp1_cost_analysis.csv')
print(meps[['molecule','out_of_pocket','AGELAST','SEX']].head(20))