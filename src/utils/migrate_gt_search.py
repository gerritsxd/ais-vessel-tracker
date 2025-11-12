"""
Database migration for GT search scraper
Ensures the gross_tonnage column can handle text values (NA/NF)
"""

import sqlite3
from pathlib import Path

DB_NAME = "vessel_static_data.db"


def migrate_gt_column():
    """Update gross_tonnage column to handle text values."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    print("="*60)
    print("GT SEARCH SCRAPER DATABASE MIGRATION")
    print("="*60)
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        # Check if eu_mrv_emissions table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='eu_mrv_emissions'
        """)
        
        if not cursor.fetchone():
            print("❌ eu_mrv_emissions table does not exist")
            print("Run import_mrv_data.py first to create the emissions table.")
            return False
        
        # Check if gross_tonnage column exists
        cursor.execute("PRAGMA table_info(eu_mrv_emissions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        if 'gross_tonnage' not in columns:
            print("Adding gross_tonnage column...")
            cursor.execute("""
                ALTER TABLE eu_mrv_emissions 
                ADD COLUMN gross_tonnage TEXT
            """)
            conn.commit()
            print("✓ gross_tonnage column added (TEXT type)")
        else:
            print(f"✓ gross_tonnage column exists (type: {columns['gross_tonnage']})")
            
            # If it's REAL type, we need to recreate it as TEXT
            if columns['gross_tonnage'] == 'REAL':
                print("Converting gross_tonnage from REAL to TEXT...")
                
                # Create backup of existing data
                cursor.execute("""
                    CREATE TABLE eu_mrv_emissions_backup AS 
                    SELECT * FROM eu_mrv_emissions
                """)
                
                # Drop original table
                cursor.execute("DROP TABLE eu_mrv_emissions")
                
                # Recreate with TEXT column
                cursor.execute('''
                    CREATE TABLE eu_mrv_emissions (
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
                        
                        -- Vessel Specifications
                        gross_tonnage TEXT,

                        -- Econowind Fit Score
                        econowind_fit_score INTEGER DEFAULT 0,

                        -- Metadata
                        last_updated TEXT NOT NULL
                    )
                ''')
                
                # Restore data
                cursor.execute("""
                    INSERT INTO eu_mrv_emissions 
                    SELECT * FROM eu_mrv_emissions_backup
                """)
                
                # Drop backup
                cursor.execute("DROP TABLE eu_mrv_emissions_backup")
                
                # Recreate indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_imo ON eu_mrv_emissions(imo)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_company ON eu_mrv_emissions(company_name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_period ON eu_mrv_emissions(reporting_period)')
                
                conn.commit()
                print("✓ gross_tonnage column converted to TEXT type")
        
        # Show current statistics
        cursor.execute("SELECT COUNT(*) FROM eu_mrv_emissions")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM eu_mrv_emissions WHERE gross_tonnage IS NOT NULL")
        with_data = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM eu_mrv_emissions WHERE gross_tonnage IN ('NA', 'NF')")
        with_na_nf = cursor.fetchone()[0]
        
        print(f"\nDatabase Statistics:")
        print(f"  Total vessels: {total:,}")
        print(f"  With GT data: {with_data:,}")
        print(f"  With NA/NF: {with_na_nf:,}")
        print(f"  Missing GT: {total - with_data:,}")
        
        print("\n" + "="*60)
        print("✓ Migration complete! Ready for GT search scraper.")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    success = migrate_gt_column()
    exit(0 if success else 1)
