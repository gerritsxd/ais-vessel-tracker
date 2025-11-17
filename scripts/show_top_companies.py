#!/usr/bin/env python3
"""Show top companies from database"""
import sqlite3
import sys
import io

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('data/vessel_static_data.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT company_name, COUNT(*) as vessels 
    FROM eu_mrv_emissions 
    WHERE company_name IS NOT NULL AND company_name != "" 
    GROUP BY company_name 
    ORDER BY vessels DESC 
    LIMIT 50
''')

print("\n" + "="*80)
print("TOP 50 COMPANIES IN YOUR DATABASE (Sorted by vessel count)")
print("="*80 + "\n")

for i, row in enumerate(cursor.fetchall(), 1):
    print(f"{i:2d}. {row[0]:50s} - {row[1]:3d} vessels")

print("\n" + "="*80)
print(f"V3 will scrape these companies IN THIS ORDER")
print("="*80)
