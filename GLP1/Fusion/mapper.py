import pandas as pd

# Define the Mapping Dictionary
# This links Brands (CMS) and Trial Prefixes (CT) to their Generic Molecule
MOLECULE_MAPPER = {
    # Semaglutide Group
    'OZEMPIC': 'SEMAGLUTIDE',
    'WEGOVY': 'SEMAGLUTIDE',
    'RYBELSUS': 'SEMAGLUTIDE',
    'STEP': 'SEMAGLUTIDE',
    'SUSTAIN': 'SEMAGLUTIDE',
    
    # Tirzepatide Group
    'MOUNJARO': 'TIRZEPATIDE',
    'ZEPBOUND': 'TIRZEPATIDE',
    'SURMOUNT': 'TIRZEPATIDE',
    
    # Dulaglutide Group
    'TRULICITY': 'DULAGLUTIDE',
    'AWARD': 'DULAGLUTIDE',
    
    # Liraglutide Group
    'VICTOZA': 'LIRAGLUTIDE',
    'SAXENDA': 'LIRAGLUTIDE',
    'LEAD': 'LIRAGLUTIDE'
}

def standardize_drug_names(df, column_name):
    """
    Cleans a column and maps it to the unified molecule name.
    """
    # 1. Standardize formatting: Uppercase, strip whitespace, remove ' 2-PAK' etc.
    df[column_name] = df[column_name].astype(str).str.upper().str.strip()
    
    # 2. Extract the core name (e.g., 'OZEMPIC 0.5MG' -> 'OZEMPIC')
    # and map it using our dictionary
    def map_molecule(name):
        # Check if any key in our mapper is inside the string
        for key in MOLECULE_MAPPER:
            if key in name:
                return MOLECULE_MAPPER[key]
        return "OTHER" # For non-GLP1s or mixed drugs

    return df[column_name].apply(map_molecule)

# Example of how we will use this in the next steps:
# df_cms['unified_molecule'] = standardize_drug_names(df_cms, 'Brnd_Name')
# df_meps['unified_molecule'] = standardize_drug_names(df_meps, 'RXDRGNAM_STR')