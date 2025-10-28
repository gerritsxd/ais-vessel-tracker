"""
Import EU MRV (Monitoring, Reporting and Verification) emissions data into SQLite database.
This creates a new table with CO2 emissions and company information linked by IMO number.
"""

import pandas as pd
import sqlite3
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB_NAME = "vessel_static_data.db"
MRV_FILE = "2024-v99-22102025-EU MRV Publication of information.xlsx"


def create_mrv_table(conn):
    """Create the EU MRV emissions table."""
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eu_mrv_emissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imo INTEGER NOT NULL UNIQUE,
            vessel_name TEXT,
            ship_type TEXT,
            reporting_period INTEGER,
            company_name TEXT,
            company_imo INTEGER,
            doc_issuer TEXT,
            verifier_name TEXT,
            
            -- CO2 Emissions
            total_co2_emissions REAL,
            co2_emissions_from_all_voyages REAL,
            co2_emissions_within_ets REAL,
            co2_emissions_from_laden_voyages REAL,
            co2_emissions_at_berth REAL,
            
            -- CO2 Equivalent Emissions  
            total_co2eq_emissions REAL,
            
            -- Fuel Consumption
            total_fuel_consumption REAL,
            
            -- Distance and Time
            total_distance_travelled REAL,
            distance_travelled_laden REAL,
            total_time_at_sea REAL,
            time_spent_at_sea_laden REAL,
            
            -- Transport Work
            transport_work_mass REAL,
            transport_work_volume REAL,
            transport_work_dwt REAL,
            transport_work_pax REAL,
            
            -- Average Efficiency Indicators
            avg_co2_per_distance REAL,
            avg_co2_per_transport_work_mass REAL,
            avg_fuel_consumption_per_distance REAL,
            
            -- Technical Efficiency
            technical_efficiency TEXT,
            
            -- Metadata
            last_updated TEXT NOT NULL,
            
            FOREIGN KEY (imo) REFERENCES vessels_static(imo)
        )
    ''')
    
    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_imo ON eu_mrv_emissions(imo)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_company ON eu_mrv_emissions(company_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_period ON eu_mrv_emissions(reporting_period)')
    
    conn.commit()
    print("✓ EU MRV emissions table created")


def import_mrv_data(conn):
    """Import EU MRV data from Excel file."""
    print(f"\nReading {MRV_FILE}...")
    
    # Read Excel with multi-level headers
    df = pd.read_excel(MRV_FILE, header=[0, 1, 2])
    
    # Flatten column names
    df.columns = ['_'.join(str(i) for i in col).strip() for col in df.columns.values]
    
    print(f"✓ Loaded {len(df)} records")
    
    # Map the complex column names to simpler ones
    column_mapping = {
        'Ship_Unnamed: 0_level_1_IMO Number': 'imo',
        'Ship_Unnamed: 1_level_1_Name': 'vessel_name',
        'Ship_Unnamed: 2_level_1_Ship type': 'ship_type',
        'Ship_Unnamed: 3_level_1_Reporting Period': 'reporting_period',
        'Ship_Unnamed: 4_level_1_Technical efficiency': 'technical_efficiency',
        'Company_Unnamed: 8_level_1_IMO Number': 'company_imo',
        'Company_Unnamed: 9_level_1_Name': 'company_name',
        'DoC_Unnamed: 10_level_1_Issuing Authority': 'doc_issuer',
        'Verifier_Unnamed: 12_level_1_Name': 'verifier_name',
    }
    
    # Find CO2 and fuel columns (only those defined in table schema)
    co2_columns = {
        'Annual monitoring results_CO₂ Emissions_Total CO₂ emissions [m tonnes]': 'total_co2_emissions',
        'Annual monitoring results_CO₂ Emissions_CO₂ emissions from all voyages between ports under a MS jurisdiction [m tonnes]': 'co2_emissions_from_all_voyages',
        'Annual monitoring results_CO₂ Emissions_CO₂ emissions from all voyages which departed from ports under a MS jurisdiction [m tonnes]': 'co2_emissions_within_ets',
        'Annual monitoring results_CO₂ Emissions_CO₂ emissions which occurred within ports under a MS jurisdiction at berth [m tonnes]': 'co2_emissions_at_berth',
        'Annual monitoring results_CO₂ Emissions_CO₂ emissions assigned to On laden voyages [m tonnes]': 'co2_emissions_from_laden_voyages',
        'Annual monitoring results_CO₂eq Emissions_Total CO₂eq emissions [m tonnes]': 'total_co2eq_emissions',
        'Annual monitoring results_Fuel consumption_Total fuel consumption [m tonnes]': 'total_fuel_consumption',
    }
    
    # Distance and time columns
    distance_columns = {
        'Annual monitoring results_Distance travelled_Total distance travelled [n miles]': 'total_distance_travelled',
        'Annual monitoring results_Distance travelled_Distance travelled on laden voyages [n miles]': 'distance_travelled_laden',
        'Annual monitoring results_Time spent at sea_Total time spent at sea [hours]': 'total_time_at_sea',
        'Annual monitoring results_Time spent at sea_Time spent at sea on laden voyages [hours]': 'time_spent_at_sea_laden',
    }
    
    # Transport work columns
    transport_columns = {
        'Annual monitoring results_Transport work_Transport work (mass) [m tonnes · n miles]': 'transport_work_mass',
        'Annual monitoring results_Transport work_Transport work (volume) [m³ · n miles]': 'transport_work_volume',
        'Annual monitoring results_Transport work_Transport work (dwt) [dwt carried · n miles]': 'transport_work_dwt',
        'Annual monitoring results_Transport work_Transport work (pax) [pax · n miles]': 'transport_work_pax',
    }
    
    # Efficiency indicators
    efficiency_columns = {
        'Annual monitoring results_Average energy efficiency_CO₂ emissions per distance [kg CO₂ / n mile]': 'avg_co2_per_distance',
        'Annual monitoring results_Average energy efficiency_CO₂ emissions per transport work (mass) [g CO₂ / m tonnes · n miles]': 'avg_co2_per_transport_work_mass',
        'Annual monitoring results_Average energy efficiency_Fuel consumption per distance [kg / n mile]': 'avg_fuel_consumption_per_distance',
    }
    
    # Combine all mappings
    all_mappings = {**column_mapping, **co2_columns, **distance_columns, **transport_columns, **efficiency_columns}
    
    # Select and rename columns
    available_cols = [col for col in all_mappings.keys() if col in df.columns]
    df_clean = df[available_cols].copy()
    df_clean.columns = [all_mappings[col] for col in available_cols]
    
    # Add timestamp
    from datetime import datetime
    df_clean['last_updated'] = datetime.utcnow().isoformat()
    
    # Clean data
    print("\nCleaning data...")
    
    # Remove rows with invalid IMO
    df_clean = df_clean[df_clean['imo'].notna()]
    df_clean = df_clean[df_clean['imo'] > 0]
    
    # Convert numeric columns
    numeric_cols = [col for col in df_clean.columns if col not in ['imo', 'vessel_name', 'ship_type', 'company_name', 'doc_issuer', 'verifier_name', 'technical_efficiency', 'last_updated']]
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    print(f"✓ Cleaned data: {len(df_clean)} valid records")
    
    # Insert into database
    print("\nInserting into database...")
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    errors = 0
    
    for idx, row in df_clean.iterrows():
        try:
            # Check if record exists
            cursor.execute('SELECT id FROM eu_mrv_emissions WHERE imo = ?', (int(row['imo']),))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                update_cols = [f"{col} = ?" for col in df_clean.columns if col != 'imo']
                update_values = [row[col] for col in df_clean.columns if col != 'imo']
                update_values.append(int(row['imo']))
                
                cursor.execute(f'''
                    UPDATE eu_mrv_emissions 
                    SET {', '.join(update_cols)}
                    WHERE imo = ?
                ''', update_values)
                updated += 1
            else:
                # Insert new record
                placeholders = ', '.join(['?' for _ in df_clean.columns])
                columns = ', '.join(df_clean.columns)
                values = [row[col] for col in df_clean.columns]
                
                cursor.execute(f'''
                    INSERT INTO eu_mrv_emissions ({columns})
                    VALUES ({placeholders})
                ''', values)
                inserted += 1
            
            if (inserted + updated) % 1000 == 0:
                conn.commit()
                print(f"  Progress: {inserted + updated}/{len(df_clean)} records processed...")
                
        except Exception as e:
            errors += 1
            if errors <= 5:  # Only print first 5 errors
                print(f"  Error processing IMO {row['imo']}: {e}")
    
    conn.commit()
    
    print(f"\n{'='*80}")
    print("IMPORT COMPLETE")
    print(f"{'='*80}")
    print(f"✓ Inserted: {inserted} new records")
    print(f"✓ Updated: {updated} existing records")
    if errors > 0:
        print(f"✗ Errors: {errors} records failed")
    print(f"{'='*80}\n")


def show_statistics(conn):
    """Show statistics about imported data."""
    cursor = conn.cursor()
    
    print(f"{'='*80}")
    print("EU MRV DATA STATISTICS")
    print(f"{'='*80}")
    
    # Total records
    cursor.execute('SELECT COUNT(*) FROM eu_mrv_emissions')
    total = cursor.fetchone()[0]
    print(f"Total vessels with emissions data: {total}")
    
    # Unique companies
    cursor.execute('SELECT COUNT(DISTINCT company_name) FROM eu_mrv_emissions WHERE company_name IS NOT NULL')
    companies = cursor.fetchone()[0]
    print(f"Unique companies: {companies}")
    
    # Total CO2 emissions
    cursor.execute('SELECT SUM(total_co2_emissions) FROM eu_mrv_emissions WHERE total_co2_emissions IS NOT NULL')
    total_co2 = cursor.fetchone()[0]
    if total_co2:
        print(f"Total CO2 emissions: {total_co2:,.0f} tonnes")
    
    # Average emissions per vessel
    cursor.execute('SELECT AVG(total_co2_emissions) FROM eu_mrv_emissions WHERE total_co2_emissions IS NOT NULL')
    avg_co2 = cursor.fetchone()[0]
    if avg_co2:
        print(f"Average CO2 per vessel: {avg_co2:,.0f} tonnes")
    
    # Top 10 emitters
    print(f"\nTop 10 CO2 Emitters:")
    cursor.execute('''
        SELECT vessel_name, company_name, total_co2_emissions 
        FROM eu_mrv_emissions 
        WHERE total_co2_emissions IS NOT NULL
        ORDER BY total_co2_emissions DESC 
        LIMIT 10
    ''')
    for i, (name, company, co2) in enumerate(cursor.fetchall(), 1):
        print(f"  {i:2}. {name[:30]:30} ({company[:30]:30}): {co2:,.0f} tonnes")
    
    # Vessels in both databases
    cursor.execute('''
        SELECT COUNT(*) 
        FROM vessels_static v
        INNER JOIN eu_mrv_emissions e ON v.imo = e.imo
    ''')
    matched = cursor.fetchone()[0]
    print(f"\nVessels matched with AIS data: {matched}")
    
    print(f"{'='*80}\n")


def main():
    """Main import process."""
    script_dir = Path(__file__).parent
    db_path = script_dir / DB_NAME
    
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        print("Run ais_collector.py first to create the database.")
        return
    
    mrv_path = script_dir / MRV_FILE
    if not mrv_path.exists():
        print(f"Error: MRV file not found: {mrv_path}")
        return
    
    print(f"{'='*80}")
    print("EU MRV EMISSIONS DATA IMPORT")
    print(f"{'='*80}\n")
    
    conn = sqlite3.connect(db_path)
    
    try:
        create_mrv_table(conn)
        import_mrv_data(conn)
        show_statistics(conn)
        
        print("✓ Import successful!")
        print(f"✓ Database updated: {db_path}")
        
    except Exception as e:
        print(f"\n✗ Error during import: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
