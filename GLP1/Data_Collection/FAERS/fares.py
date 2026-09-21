import requests
import pandas as pd
import time

# --- CONFIG ---
DRUGS = ['SEMAGLUTIDE', 'TIRZEPATIDE', 'LIRAGLUTIDE', 'DULAGLUTIDE']
BASE_URL = "https://api.fda.gov/drug/event.json"
# We want to count the most frequent 'reactions'
# API Syntax: count=patient.reaction.reactionmeddrapt.exact
LIMIT = 1000 

def fetch_faers_data():
    all_drug_data = []

    for drug in DRUGS:
        print(f"Querying FDA for {drug}...")
        
        # We use a 'count' query to get the most frequent side effects immediately
        query = f'?search=patient.drug.medicinalproduct:"{drug}"&count=patient.reaction.reactionmeddrapt.exact'
        
        try:
            response = requests.get(BASE_URL + query)
            data = response.json()
            
            if 'results' in data:
                df = pd.DataFrame(data['results'])
                df['drug'] = drug
                all_drug_data.append(df)
            else:
                print(f"No results for {drug}")
                
            # Pause to respect API limits
            time.sleep(1) 
            
        except Exception as e:
            print(f"Error fetching {drug}: {e}")

    # Combine all results
    master_df = pd.concat(all_drug_data)
    
    # Clean up column names (term = side effect, count = frequency)
    master_df.columns = ['side_effect', 'frequency', 'drug']
    
    # Save the Side Effect Map
    master_df.to_csv("faers_glp1_side_effects.csv", index=False)
    print("\nSuccess! Saved Side Effect Map to faers_glp1_side_effects.csv")
    
    # Show top 5 for the most popular drug
    print("\nTop Side Effects (Sample):")
    print(master_df.head(10))
    
    return master_df

if __name__ == "__main__":
    df_faers = fetch_faers_data()