import os
import pandas as pd
import json
from pathlib import Path
import sys

def identify_college_name_column(df: pd.DataFrame) -> str:
    """Identify the column that contains college names."""
    possible_columns = ['college_name', 'name', 'institute', 'college', 'institution']
    for col in possible_columns:
        if col in df.columns:
            return col
    
    # If none of the expected columns are found, use the first column
    # that's not a round, quota, or category
    for col in df.columns:
        if not col.startswith('cr_') and col not in ['quota', 'category', 'state']:
            return col
    
    # Fallback to the first column
    return df.columns[0] if not df.empty else None

def extract_state_name(filename: str) -> str:
    """Extract state name from filename."""
    parts = filename.split('_')
    if len(parts) >= 4:
        return parts[3].replace('.xlsx', '')
    return "unknown"

def analyze_files():
    """Analyze all Excel files in the data directory."""
    DATA_DIR = Path("cleaned-data 2")
    METADATA_FILE = Path("metadata.json")
    
    print(f"Analyzing Excel files in {DATA_DIR}...")
    
    if not DATA_DIR.exists():
        print(f"Error: Directory '{DATA_DIR}' does not exist.")
        sys.exit(1)
    
    files = list(DATA_DIR.glob("*.xlsx"))
    if not files:
        print(f"Error: No Excel files found in '{DATA_DIR}'.")
        sys.exit(1)
    
    print(f"Found {len(files)} Excel files to analyze.")
    
    metadata = []
    for i, file in enumerate(files):
        try:
            print(f"Processing file {i+1}/{len(files)}: {file.name}")
            
            # Read first row to get column structure
            df_head = pd.read_excel(file, nrows=1)
            columns = df_head.columns.tolist()
            
            # Load full data for quota and category extraction
            df = pd.read_excel(file)
            
            # Extract rounds (columns starting with 'cr_')
            rounds = [col for col in columns if col.startswith('cr_')]
            
            # Extract quotas and categories (assuming these columns exist)
            quotas = []
            categories = []
            
            if 'quota' in columns:
                quotas = df['quota'].dropna().unique().tolist()
            
            if 'category' in columns:
                categories = df['category'].dropna().unique().tolist()
            
            state = extract_state_name(file.name)
            
            # Identify college name column
            college_name_col = identify_college_name_column(df)
            
            file_metadata = {
                "filename": file.name,
                "state": state,
                "columns": columns,
                "rounds": rounds,
                "quotas": quotas,
                "categories": categories,
                "college_name_column": college_name_col
            }
            
            metadata.append(file_metadata)
            
            print(f"  Identified state: {state}")
            print(f"  Found {len(rounds)} rounds, {len(quotas)} quotas, {len(categories)} categories")
            print(f"  College name column: {college_name_col}")
            
        except Exception as e:
            print(f"Error analyzing {file}: {e}")
    
    # Save metadata to file
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Metadata saved to {METADATA_FILE}")
    print(f"Total files processed: {len(metadata)}")
    print("\nInitialization complete! You can now run the application.")

if __name__ == "__main__":
    analyze_files() 