"""
Database Schema Normalization: Add DWT and GT columns to vessels_static table.

This script:
1. Adds dwt and gt columns to vessels_static table
2. Adds metadata columns (source tracking, timestamps)
3. Copies existing data from wind_propulsion_mmsi and eu_mrv_emissions
4. Creates normalization tracking table
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_NAME = "vessel_static_data.db"


def get_db_path():
    """Get database path."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        # Try root directory
        db_path = project_root / DB_NAME
    return db_path


def check_column_exists(cursor, table, column):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def add_columns_if_not_exists(conn):
    """Add DWT/GT columns to vessels_static if they don't exist."""
    cursor = conn.cursor()
    
    columns_to_add = [
        ('dwt', 'INTEGER DEFAULT NULL'),
        ('gt', 'INTEGER DEFAULT NULL'),
        ('dwt_source', 'TEXT DEFAULT NULL'),
        ('gt_source', 'TEXT DEFAULT NULL'),
        ('dwt_updated_at', 'TIMESTAMP DEFAULT NULL'),
        ('gt_updated_at', 'TIMESTAMP DEFAULT NULL'),
    ]
    
    for column_name, column_type in columns_to_add:
        if not check_column_exists(cursor, 'vessels_static', column_name):
            try:
                cursor.execute(f'''
                    ALTER TABLE vessels_static 
                    ADD COLUMN {column_name} {column_type}
                ''')
                print(f"✅ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                print(f"⚠️  Could not add {column_name}: {e}")
        else:
            print(f"⏭️  Column {column_name} already exists")
    
    conn.commit()


def create_normalization_table(conn):
    """Create normalization tracking table."""
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vessel_normalization_status (
            mmsi INTEGER PRIMARY KEY,
            has_dwt BOOLEAN DEFAULT 0,
            has_gt BOOLEAN DEFAULT 0,
            dwt_attempts INTEGER DEFAULT 0,
            gt_attempts INTEGER DEFAULT 0,
            last_dwt_attempt TIMESTAMP,
            last_gt_attempt TIMESTAMP,
            dwt_source TEXT,
            gt_source TEXT,
            FOREIGN KEY (mmsi) REFERENCES vessels_static(mmsi)
        )
    ''')
    
    conn.commit()
    print("✅ Created vessel_normalization_status table")


def copy_wasp_data(conn):
    """Copy DWT/GT from wind_propulsion_mmsi to vessels_static."""
    cursor = conn.cursor()
    
    # Check if wind_propulsion_mmsi table exists
    cursor.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='wind_propulsion_mmsi'
    ''')
    
    if not cursor.fetchone():
        print("⚠️  wind_propulsion_mmsi table not found, skipping WASP data copy")
        return 0
    
    # Copy DWT and GT from WASP table
    # SQLite doesn't support table aliases in UPDATE, so we use subqueries
    cursor.execute('''
        UPDATE vessels_static
        SET 
            dwt = (SELECT dwt FROM wind_propulsion_mmsi WHERE wind_propulsion_mmsi.mmsi = vessels_static.mmsi),
            gt = (SELECT gt FROM wind_propulsion_mmsi WHERE wind_propulsion_mmsi.mmsi = vessels_static.mmsi),
            dwt_source = 'wasp',
            gt_source = 'wasp',
            dwt_updated_at = datetime('now'),
            gt_updated_at = datetime('now')
        WHERE EXISTS (
            SELECT 1 FROM wind_propulsion_mmsi WHERE wind_propulsion_mmsi.mmsi = vessels_static.mmsi
        )
        AND (dwt IS NULL OR gt IS NULL)
    ''')
    
    count = cursor.rowcount
    conn.commit()
    
    if count > 0:
        print(f"✅ Copied DWT/GT from WASP table: {count} vessels updated")
    else:
        print("⏭️  No WASP vessels to update (may already be copied)")
    
    return count


def copy_mrv_gt_data(conn):
    """Copy GT from eu_mrv_emissions to vessels_static."""
    cursor = conn.cursor()
    
    # Check if eu_mrv_emissions table exists
    cursor.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='eu_mrv_emissions'
    ''')
    
    if not cursor.fetchone():
        print("⚠️  eu_mrv_emissions table not found, skipping MRV data copy")
        return 0
    
    # Check if gross_tonnage column exists
    if not check_column_exists(cursor, 'eu_mrv_emissions', 'gross_tonnage'):
        print("⚠️  gross_tonnage column not found in eu_mrv_emissions, skipping")
        return 0
    
    # Copy GT from MRV table (only if not already set)
    # SQLite doesn't support FROM clause in UPDATE, so we use a subquery
    cursor.execute('''
        UPDATE vessels_static
        SET 
            gt = CAST((SELECT gross_tonnage FROM eu_mrv_emissions WHERE eu_mrv_emissions.imo = vessels_static.imo) AS INTEGER),
            gt_source = CASE 
                WHEN gt_source IS NULL THEN 'mrv'
                WHEN gt_source = 'wasp' THEN 'wasp'  -- Keep WASP source if already set
                ELSE 'mrv'
            END,
            gt_updated_at = datetime('now')
        WHERE imo IN (
            SELECT imo FROM eu_mrv_emissions 
            WHERE gross_tonnage IS NOT NULL
              AND gross_tonnage != ''
              AND gross_tonnage != 'N/A'
        )
        AND gt IS NULL
    ''')
    
    count = cursor.rowcount
    conn.commit()
    
    if count > 0:
        print(f"✅ Copied GT from MRV table: {count} vessels updated")
    else:
        print("⏭️  No MRV vessels to update (may already be copied)")
    
    return count


def update_normalization_status(conn):
    """Update normalization status table."""
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO vessel_normalization_status (mmsi, has_dwt, has_gt, dwt_source, gt_source)
        SELECT 
            mmsi,
            CASE WHEN dwt IS NOT NULL THEN 1 ELSE 0 END as has_dwt,
            CASE WHEN gt IS NOT NULL THEN 1 ELSE 0 END as has_gt,
            dwt_source,
            gt_source
        FROM vessels_static
        WHERE mmsi IS NOT NULL
    ''')
    
    conn.commit()
    print("✅ Updated normalization status table")


def print_statistics(conn):
    """Print normalization statistics."""
    cursor = conn.cursor()
    
    # Overall coverage
    cursor.execute('''
        SELECT 
            COUNT(*) as total_vessels,
            COUNT(dwt) as vessels_with_dwt,
            COUNT(gt) as vessels_with_gt,
            COUNT(CASE WHEN dwt IS NOT NULL AND gt IS NOT NULL THEN 1 END) as vessels_with_both,
            ROUND(100.0 * COUNT(dwt) / COUNT(*), 2) as dwt_coverage_pct,
            ROUND(100.0 * COUNT(gt) / COUNT(*), 2) as gt_coverage_pct
        FROM vessels_static
        WHERE mmsi IS NOT NULL
    ''')
    
    stats = cursor.fetchone()
    print("\n" + "="*60)
    print("NORMALIZATION STATISTICS")
    print("="*60)
    print(f"Total vessels: {stats[0]:,}")
    print(f"Vessels with DWT: {stats[1]:,} ({stats[4]}%)")
    print(f"Vessels with GT: {stats[2]:,} ({stats[5]}%)")
    print(f"Vessels with both: {stats[3]:,}")
    
    # Source distribution for DWT
    cursor.execute('''
        SELECT 
            dwt_source,
            COUNT(*) as count
        FROM vessels_static
        WHERE dwt IS NOT NULL
        GROUP BY dwt_source
        ORDER BY count DESC
    ''')
    
    print("\nDWT Source Distribution:")
    for source, count in cursor.fetchall():
        print(f"  {source or 'NULL'}: {count:,}")
    
    # Source distribution for GT
    cursor.execute('''
        SELECT 
            gt_source,
            COUNT(*) as count
        FROM vessels_static
        WHERE gt IS NOT NULL
        GROUP BY gt_source
        ORDER BY count DESC
    ''')
    
    print("\nGT Source Distribution:")
    for source, count in cursor.fetchall():
        print(f"  {source or 'NULL'}: {count:,}")
    
    print("="*60 + "\n")


def main():
    """Main normalization function."""
    db_path = get_db_path()
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print(f"📊 Normalizing vessel data in: {db_path}")
    print(f"⏰ Started at: {datetime.now()}\n")
    
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute('PRAGMA journal_mode=WAL')
    
    try:
        # Step 1: Add columns
        print("Step 1: Adding DWT/GT columns...")
        add_columns_if_not_exists(conn)
        
        # Step 2: Create normalization table
        print("\nStep 2: Creating normalization tracking table...")
        create_normalization_table(conn)
        
        # Step 3: Copy WASP data
        print("\nStep 3: Copying WASP vessel data...")
        wasp_count = copy_wasp_data(conn)
        
        # Step 4: Copy MRV data
        print("\nStep 4: Copying MRV vessel data...")
        mrv_count = copy_mrv_gt_data(conn)
        
        # Step 5: Update normalization status
        print("\nStep 5: Updating normalization status...")
        update_normalization_status(conn)
        
        # Step 6: Print statistics
        print_statistics(conn)
        
        print("✅ Normalization complete!")
        
    except Exception as e:
        print(f"❌ Error during normalization: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()

