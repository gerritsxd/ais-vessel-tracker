"""
Quick script to check if the 2023 EU MRV file has Gross Tonnage data.
"""

import pandas as pd
from pathlib import Path

# Path to the downloaded file
file_path = Path(__file__).parent / "2023-v80-18102025-EU MRV Publication of information.xlsx"

print("="*80)
print("CHECKING 2023 EU MRV FILE FOR GROSS TONNAGE")
print("="*80)

if not file_path.exists():
    print(f"\nX File not found: {file_path}")
    print("\nPlease move the downloaded Excel file to:")
    print(f"   {file_path.parent}/")
    print("\nOr update the file_path in this script.")
    exit()

print(f"\nOK File found: {file_path.name}")
print("\nReading Excel file (this may take a moment)...")

try:
    # Read Excel with multi-level headers
    df = pd.read_excel(str(file_path), header=[0, 1, 2])
    
    # Flatten column names
    df.columns = ['_'.join(str(i) for i in col).strip() for col in df.columns.values]
    
    print(f"\n{'='*80}")
    print("FILE STATISTICS")
    print(f"{'='*80}")
    print(f"Total rows: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    
    # Search for Gross Tonnage column
    print(f"\n{'='*80}")
    print("SEARCHING FOR GROSS TONNAGE COLUMN")
    print(f"{'='*80}")
    
    gt_cols = [col for col in df.columns if 'gross' in col.lower() or 'tonnage' in col.lower()]
    
    if gt_cols:
        print(f"OK FOUND {len(gt_cols)} column(s) with 'gross' or 'tonnage':")
        for col in gt_cols:
            print(f"  - {col}")
            
            # Check how many non-null values
            non_null = df[col].notna().sum()
            print(f"    -> {non_null:,} vessels with data ({non_null/len(df)*100:.1f}%)")
    else:
        print("X NO columns found with 'gross' or 'tonnage'!")
    
    # Show first 10 column names
    print(f"\n{'='*80}")
    print("FIRST 10 COLUMNS IN FILE")
    print(f"{'='*80}")
    for i, col in enumerate(df.columns[:10]):
        print(f"  [{i}] {col}")
    
    # Show sample data
    print(f"\n{'='*80}")
    print("SAMPLE DATA (First 3 rows)")
    print(f"{'='*80}")
    
    # Show IMO, Name, and GT columns if they exist
    sample_cols = []
    for col in df.columns:
        if 'imo' in col.lower() and 'number' in col.lower():
            sample_cols.append(col)
        if 'name' in col.lower() and len(sample_cols) < 3:
            sample_cols.append(col)
        if gt_cols and len(sample_cols) < 4:
            sample_cols.append(gt_cols[0])
    
    if sample_cols:
        print(df[sample_cols].head(3).to_string())
    
    print(f"\n{'='*80}")
    print("CONCLUSION")
    print(f"{'='*80}")
    
    if gt_cols and len(df) > 1000:
        print("OK THIS FILE HAS GROSS TONNAGE DATA!")
        print(f"OK {len(df):,} vessels with GT column")
        print("\n=> This file can be used to populate GT data!")
    elif gt_cols:
        print("WARNING File has GT column but only a few rows")
        print(f"   Only {len(df)} vessels - might not be complete")
    else:
        print("X This file does NOT have Gross Tonnage data")
        print("   Need to find a different data source")
    
    print(f"\n{'='*80}\n")

except Exception as e:
    print(f"\nX Error reading file: {e}")
    import traceback
    traceback.print_exc()
