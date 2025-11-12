"""
Quick fix for GT column migration - handles the last_updated constraint issue
"""

import sqlite3
from pathlib import Path

DB_NAME = "vessel_static_data.db"


def fix_gt_column():
    """Fix gross_tonnage column to handle text values without breaking existing data."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    print("="*60)
    print("FIXING GT COLUMN MIGRATION")
    print("="*60)
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        # Check current column type
        cursor.execute("PRAGMA table_info(eu_mrv_emissions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        if 'gross_tonnage' not in columns:
            print("❌ gross_tonnage column doesn't exist - this shouldn't happen")
            return False
        
        print(f"Current gross_tonnage type: {columns['gross_tonnage']}")
        
        if columns['gross_tonnage'] != 'TEXT':
            print("Converting gross_tonnage to TEXT type...")
            
            # Simple approach: Add new column, copy data, drop old, rename
            cursor.execute("ALTER TABLE eu_mrv_emissions ADD COLUMN gross_tonnage_new TEXT")
            
            # Copy data from old to new column
            cursor.execute("""
                UPDATE eu_mrv_emissions 
                SET gross_tonnage_new = CAST(gross_tonnage AS TEXT)
                WHERE gross_tonnage IS NOT NULL
            """)
            
            # Drop old column
            cursor.execute("ALTER TABLE eu_mrv_emissions DROP COLUMN gross_tonnage")
            
            # Rename new column
            cursor.execute("ALTER TABLE eu_mrv_emissions RENAME COLUMN gross_tonnage_new TO gross_tonnage")
            
            conn.commit()
            print("✓ gross_tonnage column converted to TEXT type")
        else:
            print("✓ gross_tonnage column is already TEXT type")
        
        # Show statistics
        cursor.execute("SELECT COUNT(*) FROM eu_mrv_emissions")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM eu_mrv_emissions WHERE gross_tonnage IS NOT NULL")
        with_data = cursor.fetchone()[0]
        
        print(f"\nDatabase Statistics:")
        print(f"  Total vessels: {total:,}")
        print(f"  With GT data: {with_data:,}")
        print(f"  Missing GT: {total - with_data:,}")
        
        print("\n" + "="*60)
        print("✓ GT column fix complete! Ready for search scraper.")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        # If we get an error about DROP COLUMN not supported, try alternative
        if "DROP COLUMN" in str(e):
            print("SQLite doesn't support DROP COLUMN - using alternative method...")
            return alternative_migration(conn)
        return False
        
    finally:
        if conn:
            conn.close()


def alternative_migration(conn):
    """Alternative migration for SQLite versions that don't support DROP COLUMN."""
    try:
        cursor = conn.cursor()
        
        print("Using alternative migration method...")
        
        # Create new table with TEXT column
        cursor.execute('''
            CREATE TABLE eu_mrv_emissions_new (
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
                
                -- Vessel Specifications (TEXT now!)
                gross_tonnage TEXT,

                -- Econowind Fit Score
                econowind_fit_score INTEGER DEFAULT 0,

                -- Metadata
                last_updated TEXT NOT NULL
            )
        ''')
        
        # Copy data from old to new table
        cursor.execute('''
            INSERT INTO eu_mrv_emissions_new 
            SELECT * FROM eu_mrv_emissions
        ''')
        
        # Drop old table
        cursor.execute("DROP TABLE eu_mrv_emissions")
        
        # Rename new table
        cursor.execute("ALTER TABLE eu_mrv_emissions_new RENAME TO eu_mrv_emissions")
        
        # Recreate indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_imo ON eu_mrv_emissions(imo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_company ON eu_mrv_emissions(company_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_period ON eu_mrv_emissions(reporting_period)')
        
        conn.commit()
        print("✓ Alternative migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Alternative migration failed: {e}")
        return False


if __name__ == "__main__":
    success = fix_gt_column()
    exit(0 if success else 1)
