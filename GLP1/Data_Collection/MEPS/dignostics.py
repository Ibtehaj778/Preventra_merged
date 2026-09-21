import pandas as pd

# Update these to your actual file names
PMED_FILE = "H248A.xlsx" 
CONS_FILE = "H251.xlsx"

def diagnose_meps():
    print("--- DIAGNOSING PMED FILE ---")
    df_pmed_peek = pd.read_excel(PMED_FILE, nrows=5)
    print("Columns found in PMED:", df_pmed_peek.columns.tolist())
    
    # Get a sample of drug names to see the format
    df_pmed_names = pd.read_excel(PMED_FILE, usecols=[df_pmed_peek.columns[1]]) # Usually 2nd or 3rd col
    print("\nSample Drug Names in file:")
    print(df_pmed_names.iloc[:,0].dropna().unique()[:15])

    print("\n--- DIAGNOSING CONSOLIDATED FILE ---")
    df_cons_peek = pd.read_excel(CONS_FILE, nrows=5)
    print("Columns found in Consolidated:", df_cons_peek.columns.tolist())

if __name__ == "__main__":
    diagnose_meps()