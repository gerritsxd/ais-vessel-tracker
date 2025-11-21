import sqlite3

conn = sqlite3.connect('data/vessel_static_data.db')
cursor = conn.cursor()

print('TOP 30 COMPANIES BY VESSEL COUNT:\n')
cursor.execute('''
    SELECT company_name, COUNT(*) as vessel_count 
    FROM eu_mrv_emissions 
    WHERE company_name IS NOT NULL 
      AND company_name != "" 
      AND company_name NOT LIKE '"%'
    GROUP BY company_name 
    ORDER BY vessel_count DESC 
    LIMIT 30
''')

results = cursor.fetchall()
for i, (company, count) in enumerate(results, 1):
    print(f'{i:2d}. {company:60s} ({count:3d} vessels)')

print(f'\n✅ These are the companies that will be prioritized for ML training')
conn.close()
