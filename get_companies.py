import sqlite3
import sys
import io

# Set UTF-8 encoding for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to database
conn = sqlite3.connect('data/vessel_static_data.db')
cursor = conn.cursor()

print('=== SIGNATORY COMPANIES FROM AIS DATA ===')
cursor.execute('SELECT DISTINCT signatory_company FROM vessels_static WHERE signatory_company IS NOT NULL AND signatory_company != "" ORDER BY signatory_company')
companies = cursor.fetchall()
for i, company in enumerate(companies):
    print(f'{i+1:3d}. {company[0]}')

print(f'\nTotal AIS companies: {len(companies)}')

print('\n=== COMPANY NAMES FROM EU MRV EMISSIONS ===')
cursor.execute('SELECT DISTINCT company_name FROM eu_mrv_emissions WHERE company_name IS NOT NULL AND company_name != "" ORDER BY company_name')
companies = cursor.fetchall()
for i, company in enumerate(companies):
    print(f'{i+1:3d}. {company[0]}')

print(f'\nTotal MRV companies: {len(companies)}')

conn.close()
