"""
Diagnostic: Inspect all data sources to plan the unified schema merge.
"""
import pandas as pd
import os

root = r"c:\Users\Talha\Desktop\GLP"

sources = {
    "CMS_clean": os.path.join(root, "Medicare Part D Prescribers - by Provider and Drug", "2023", "glp1_outputs_v2", "glp1_cms_clean_v2.csv"),
    "CMS_drug_summary": os.path.join(root, "Medicare Part D Prescribers - by Provider and Drug", "2023", "glp1_outputs_v2", "summary_by_drug.csv"),
    "CMS_specialty": os.path.join(root, "Medicare Part D Prescribers - by Provider and Drug", "2023", "glp1_outputs_v2", "summary_by_specialty.csv"),
    "CMS_state_drug": os.path.join(root, "Medicare Part D Prescribers - by Provider and Drug", "2023", "glp1_outputs_v2", "summary_by_state_and_drug.csv"),
    "CMS_low_refill": os.path.join(root, "Medicare Part D Prescribers - by Provider and Drug", "2023", "glp1_outputs_v2", "low_refill_prescribers.csv"),
    "NHANES": os.path.join(root, "NHANES", "nhanes_clinical_baseline.csv"),
    "MEPS": os.path.join(root, "MEPS", "meps_glp1_cost_analysis.csv"),
    "FAERS": os.path.join(root, "FARES", "faers_glp1_side_effects.csv"),
    "CT_metadata": os.path.join(root, "ClinicalTrials", "trial_metadata.csv"),
    "CT_outcomes": os.path.join(root, "ClinicalTrials", "trial_outcomes.csv"),
    "CT_adverse": os.path.join(root, "ClinicalTrials", "trial_adverse_events.csv"),
    "CT_baselines": os.path.join(root, "ClinicalTrials", "trial_baselines.csv"),
}

for name, path in sources.items():
    print(f"\n{'='*60}")
    print(f"SOURCE: {name}")
    print(f"{'='*60}")
    if not os.path.exists(path):
        print("  FILE NOT FOUND")
        continue
    
    if name == "CMS_clean":
        df = pd.read_csv(path, nrows=5)
    else:
        df = pd.read_csv(path)
    
    print(f"  Rows: {len(df) if name != 'CMS_clean' else '~351K (sampled)'}")
    print(f"  Columns ({df.shape[1]}): {list(df.columns)}")
    print(f"  Missing rates:")
    miss = df.isnull().mean()
    for col in miss[miss > 0].index:
        print(f"    {col}: {miss[col]*100:.1f}%")
    if miss[miss > 0].empty:
        print(f"    (none)")

# Drug name alignment check
print(f"\n{'='*60}")
print("DRUG NAME ALIGNMENT CHECK")
print(f"{'='*60}")

cms_drugs = pd.read_csv(sources["CMS_drug_summary"])
print(f"\nCMS brand names: {sorted(cms_drugs.iloc[:,0].unique())}")

meps = pd.read_csv(sources["MEPS"])
col = "RXDRGNAM_STR" if "RXDRGNAM_STR" in meps.columns else "RXNAME_STR"
print(f"\nMEPS drug names ({col}): {sorted(meps[col].unique())}")

faers = pd.read_csv(sources["FAERS"])
print(f"\nFAERS drug names: {sorted(faers['drug'].unique())}")

ct_meta = pd.read_csv(sources["CT_metadata"])
print(f"\nClinicalTrials trial names: {sorted(ct_meta['trial_name'].unique())}")
